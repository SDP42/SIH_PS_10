"""
API key / developer-platform management — mounted under /api/v1/api-keys.

Creating, listing, rotating, and revoking keys are administrative actions
gated behind the existing ABHA Demo Mode dependency (app/auth.py) — the same
boundary that already guards governance decisions and Bundle uploads. This
is deliberately NOT gated by an API key itself: a key can't be used to mint
other keys, which would make a leaked key self-propagating.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app import apikeys, audit
from app.auth import require_demo_auth

router = APIRouter(prefix="/api/v1/api-keys", tags=["API Key Platform"])


class CreateClientRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    organization: Optional[str] = None


@router.post("/clients")
def create_client(body: CreateClientRequest, operator: Dict[str, Any] = Depends(require_demo_auth)):
    """Register a new API client (e.g. an EMR vendor) before issuing it any keys."""
    actor = f"{operator.get('name')} ({operator.get('role')})"
    client = apikeys.create_client(body.name, body.organization, created_by=actor)
    audit.log(action="API_CLIENT_CREATED", actor=actor, target=f"client/{client['id']}", details=body.name)
    return client


class CreateKeyRequest(BaseModel):
    client_id: int
    key_type: str = Field(..., description=f"One of {sorted(apikeys.VALID_KEY_TYPES)}")
    label: Optional[str] = None
    scopes: Optional[List[str]] = Field(None, description="Override the key type's default scopes")
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650)


@router.post("")
def create_key(body: CreateKeyRequest, operator: Dict[str, Any] = Depends(require_demo_auth)):
    """
    Issues a new key. The response's `secret` field is shown exactly once —
    store it now, it cannot be retrieved again (only its hash is kept).
    """
    actor = f"{operator.get('name')} ({operator.get('role')})"
    try:
        key = apikeys.create_key(
            client_id=body.client_id, key_type=body.key_type, created_by=actor,
            label=body.label, scopes=body.scopes, expires_in_days=body.expires_in_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "INVALID_REQUEST", "message": str(e)})

    audit.log(
        action="API_KEY_CREATED", actor=actor, target=f"api_key/{key['id']} ({key['key_prefix']}...)",
        details=f"type={body.key_type}, scopes={','.join(key['scopes'])}",
    )
    return key


@router.get("")
def list_keys(client_id: Optional[int] = Query(None), operator: Dict[str, Any] = Depends(require_demo_auth)):
    """Lists keys with metadata only — the secret is never retrievable after creation."""
    return {"keys": apikeys.list_keys(client_id)}


@router.post("/{key_id}/rotate")
def rotate_key(key_id: int, operator: Dict[str, Any] = Depends(require_demo_auth)):
    """Revokes the old secret and issues a new one under the same client, same type/scopes, no gap."""
    actor = f"{operator.get('name')} ({operator.get('role')})"
    try:
        new_key = apikeys.rotate_key(key_id, created_by=actor)
    except LookupError as e:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})

    audit.log(
        action="API_KEY_ROTATED", actor=actor,
        target=f"api_key/{key_id} -> api_key/{new_key['id']}", details=f"new prefix {new_key['key_prefix']}...",
    )
    return new_key


@router.post("/{key_id}/revoke")
def revoke_key(key_id: int, operator: Dict[str, Any] = Depends(require_demo_auth)):
    actor = f"{operator.get('name')} ({operator.get('role')})"
    try:
        result = apikeys.revoke_key(key_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})

    audit.log(action="API_KEY_REVOKED", actor=actor, target=f"api_key/{key_id} ({result['key_prefix']}...)")
    return result


@router.get("/{key_id}/usage")
def key_usage(key_id: int, hours: int = Query(24, ge=1, le=720), operator: Dict[str, Any] = Depends(require_demo_auth)):
    if not apikeys.get_key(key_id):
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"No API key with id {key_id}"})
    return apikeys.usage_summary(key_id, hours)


@router.get("/scopes")
def list_scopes():
    """Reference: every scope this service recognises, and each key type's default grant."""
    return {"all_scopes": apikeys.ALL_SCOPES, "defaults_by_key_type": apikeys.DEFAULT_SCOPES_BY_TYPE,
            "rate_limits_by_key_type": apikeys.DEFAULT_RATE_LIMIT_BY_TYPE}
