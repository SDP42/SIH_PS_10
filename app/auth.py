"""
Demo-mode ABHA-style authentication.

*** THIS IS NOT REAL ABHA OAuth 2.0. *** The spec (DJS_26_SW_10) names
"ABHA-linked OAuth 2.0 authentication" as a requirement. Real ABHA requires
registering with India's Ayushman Bharat Digital Mission gateway — out of
reach for an offline hackathon build. Instead this module exercises a REAL
code path with the SAME shape as the real thing (a signed bearer token, a
FastAPI dependency that 401s without one, an expiry) so the write-path
security story is genuinely enforced, not just claimed — it just issues
tokens itself instead of delegating to the actual ABHA identity gateway.
Every response and doc string here says "ABHA Demo Mode" for exactly this
reason; never present this as production ABHA integration.

Token format: base64url(json payload).hex(HMAC-SHA256 signature). The HMAC
key is read from DEMO_AUTH_SECRET if set, otherwise a fixed development
default — fine for a demo, would need a real secret-management story before
this token scheme could be trusted for anything beyond a hackathon demo.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

SECRET = os.environ.get("DEMO_AUTH_SECRET", "namaste-icd11-demo-secret-not-for-production")
TOKEN_TTL_SECONDS = 60 * 60 * 4  # 4 hours

router = APIRouter(prefix="/api/auth", tags=["Auth (ABHA Demo Mode)"])


def _sign(payload: Dict[str, Any]) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    signature = hmac.new(SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def _verify(token: str) -> Dict[str, Any]:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        raise ValueError("malformed token")

    expected = hmac.new(SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("bad signature")

    payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
    if payload.get("exp", 0) < time.time():
        raise ValueError("token expired")
    return payload


class DemoLoginRequest(BaseModel):
    name: str
    role: str = "AYUSH Clinician"


@router.post("/demo-login")
def demo_login(body: DemoLoginRequest):
    """
    Issues a demo bearer token for the given name/role — no password, no
    real identity check. This is the ABHA Demo Mode entry point; label every
    UI surface built on top of it accordingly.
    """
    now = int(time.time())
    payload = {
        "name": body.name,
        "role": body.role,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "mode": "ABHA_DEMO",
    }
    return {
        "access_token": _sign(payload),
        "token_type": "bearer",
        "expires_in": TOKEN_TTL_SECONDS,
        "identity": {"name": body.name, "role": body.role},
        "mode": "ABHA_DEMO",
        "disclaimer": "Demo-mode token — not real ABHA OAuth 2.0. No password or identity verification performed.",
    }


def require_demo_auth(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    FastAPI dependency guarding write endpoints (governance decide, Bundle
    upload). Real 401s without a valid, unexpired token — the enforcement
    is real even though the identity provider behind it is a demo stub.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "MISSING_TOKEN", "message": "Authorization: Bearer <token> required (ABHA Demo Mode — see POST /api/auth/demo-login)"},
        )
    token = authorization[len("Bearer "):].strip()
    try:
        return _verify(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail={"error": "INVALID_TOKEN", "message": str(e)})


@router.get("/whoami")
def whoami(identity: Dict[str, Any] = Depends(require_demo_auth)):
    """Convenience endpoint for the frontend to check/refresh session identity."""
    return identity
