"""
WHO ICD-11 synchronisation API — mounted under /api/who.

Two independent WHO sources are exposed here, with different reach:

  * POST /sync            — release-file diff (app/who_sync.run_release_sync).
                             No WHO credentials needed; checks every mapping
                             target in one pass against WHO's own published
                             release CDN. This is the default, primary path.
  * POST /sync/api         — ICD-API per-code sweep (app/who_sync.run_api_sync).
                             Needs ICD_API_CLIENT_ID/SECRET; adds definitions
                             and browser links, batched to respect the API.

GET /code resolves a single code and automatically prefers a cached ICD-API
answer, falls back to the API live, then to the release file, then to the
local snapshot — see app/who_sync.fetch_code for the exact order.

Read endpoints are open (they only ever expose terminology metadata). Both
POST endpoints are guarded by the same ABHA Demo Mode dependency the other
write paths use, since they make outbound calls and write to the drift
registry — that is an operator action, not an anonymous one.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app import audit, who_sync
from app.auth import require_demo_auth

router = APIRouter(prefix="/api/who", tags=["WHO ICD-11 Sync"])


def _log_sync_audit(result: Dict[str, Any], actor: str) -> None:
    audit.log(
        action=f"WHO_SYNC_{result['mode']}",
        actor=actor,
        target=f"ICD-11 release {result['release_id']} (source={result.get('source')})",
        details=(
            f"{result['codes_checked']} codes checked — "
            f"{result.get('confirmed', 0)} confirmed, {result.get('drifted', 0)} drifted, "
            f"{result.get('missing', 0)} missing. {result['detail']}"
        ),
    )


@router.get("/status")
def get_status():
    """Live-vs-snapshot posture: credentials, last sync (both sources), coverage, open drift."""
    return who_sync.status()


@router.get("/releases")
def get_releases():
    """
    ICD-11 MMS releases WHO currently publishes (from the credential-free
    release index), and whether our snapshot is the latest.
    """
    return who_sync.list_releases()


@router.get("/code/{code:path}")
def get_code(
    code: str,
    release: Optional[str] = Query(None, description="ICD-11 release id, e.g. 2025-01"),
    force: bool = Query(False, description="Bypass the local WHO cache and re-fetch"),
):
    """
    Resolve one ICD-11 code against WHO, with explicit provenance
    (WHO_LIVE / WHO_CACHE / WHO_RELEASE_FILE / LOCAL_SNAPSHOT). Degrades
    through that order instead of failing when a source is unavailable.
    """
    return who_sync.fetch_code(code, release_id=release, force=force)


@router.get("/drift")
def get_drift(limit: int = Query(100, ge=1, le=500)):
    """Codes whose WHO title no longer matches our snapshot, or that left the release."""
    return {"items": who_sync.drift_items(limit), "disclaimer": who_sync.DISCLAIMER}


@router.get("/history")
def get_history(limit: int = Query(20, ge=1, le=100)):
    """Past sync runs from both sources — the audit trail for 'when did we last talk to WHO?'."""
    return {"runs": who_sync.history(limit)}


class ReleaseSyncRequest(BaseModel):
    release: Optional[str] = None


@router.post("/sync")
def run_release_sync(body: ReleaseSyncRequest = ReleaseSyncRequest(), operator: Dict[str, Any] = Depends(require_demo_auth)):
    """
    Diff every mapping-target code against WHO's official release file — the
    default, credential-free synchronisation path. Requires ABHA Demo Mode
    auth (it writes to the drift registry); the operator identity is stamped
    on the sync log.
    """
    actor = f"{operator.get('name')} ({operator.get('role')})"
    result = who_sync.run_release_sync(release_id=body.release, actor=actor)
    _log_sync_audit(result, actor)
    return result


class ApiSyncRequest(BaseModel):
    limit: int = Field(25, ge=1, le=who_sync.MAX_SYNC_BATCH)
    release: Optional[str] = None


@router.post("/sync/api")
def run_api_sync(body: ApiSyncRequest = ApiSyncRequest(), operator: Dict[str, Any] = Depends(require_demo_auth)):
    """
    Sweep a batch of codes through the ICD-API for per-code definitions and
    browser links. Needs ICD_API_CLIENT_ID/SECRET — reports
    SKIPPED_NO_CREDENTIALS rather than failing when they are absent.
    Requires ABHA Demo Mode auth.
    """
    actor = f"{operator.get('name')} ({operator.get('role')})"
    result = who_sync.run_api_sync(limit=body.limit, release_id=body.release, actor=actor)
    _log_sync_audit(result, actor)
    return result
