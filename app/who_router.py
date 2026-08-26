"""
WHO ICD-11 synchronisation API — mounted under /api/who.

Read endpoints are open (they only ever expose terminology metadata).
POST /sync is guarded by the same ABHA Demo Mode dependency the other write
paths use, because it makes outbound calls on WHO credentials and writes to
the drift registry — that is an operator action, not an anonymous one.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app import audit, who_sync
from app.auth import require_demo_auth

router = APIRouter(prefix="/api/who", tags=["WHO ICD-11 Sync"])


@router.get("/status")
def get_status():
    """Live-vs-snapshot posture: credentials, last sync, cache coverage, open drift."""
    return who_sync.status()


@router.get("/releases")
def get_releases():
    """ICD-11 MMS releases WHO currently publishes, and whether our snapshot is the latest."""
    return who_sync.list_releases()


@router.get("/code/{code:path}")
def get_code(
    code: str,
    release: Optional[str] = Query(None, description="ICD-11 release id, e.g. 2025-01"),
    force: bool = Query(False, description="Bypass the local WHO cache and re-fetch"),
):
    """
    Resolve one ICD-11 code against WHO, with explicit provenance
    (WHO_LIVE / WHO_CACHE / LOCAL_SNAPSHOT). Degrades to the offline
    snapshot instead of failing when WHO is unreachable.
    """
    return who_sync.fetch_code(code, release_id=release, force=force)


@router.get("/drift")
def get_drift(limit: int = Query(100, ge=1, le=500)):
    """Codes whose WHO title no longer matches our snapshot, or that left the release."""
    return {"items": who_sync.drift_items(limit), "disclaimer": who_sync.DISCLAIMER}


@router.get("/history")
def get_history(limit: int = Query(20, ge=1, le=100)):
    """Past sync runs — the audit trail for 'when did we last talk to WHO?'."""
    return {"runs": who_sync.history(limit)}


class SyncRequest(BaseModel):
    limit: int = Field(25, ge=1, le=who_sync.MAX_SYNC_BATCH)
    release: Optional[str] = None


@router.post("/sync")
def run_sync(body: SyncRequest = SyncRequest(), operator: Dict[str, Any] = Depends(require_demo_auth)):
    """Requires ABHA Demo Mode auth — the operator identity is stamped on the sync log."""
    actor = f"{operator.get('name')} ({operator.get('role')})"
    result = who_sync.run_sync(limit=body.limit, release_id=body.release, actor=actor)

    audit.log(
        action=f"WHO_SYNC_{result['mode']}",
        actor=actor,
        target=f"ICD-11 release {result['release_id']}",
        details=(
            f"{result['codes_checked']} codes checked — "
            f"{result.get('confirmed', 0)} confirmed, {result.get('drifted', 0)} drifted, "
            f"{result.get('missing', 0)} missing. {result['detail']}"
        ),
    )
    return result
