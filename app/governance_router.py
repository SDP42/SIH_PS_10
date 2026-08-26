"""Governance / expert-review API — mounted under /api/governance."""
from typing import Any, Dict, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query

from app import governance, audit
from app.auth import require_demo_auth

router = APIRouter(prefix="/api/governance", tags=["Governance"])


@router.get("/queue")
def get_queue(
    status: Optional[str] = Query(None, description="pending | approved | rejected | needs_info"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    if status and status not in governance.VALID_STATUSES:
        raise HTTPException(status_code=400, detail={"error": "INVALID_STATUS", "message": f"status must be one of {sorted(governance.VALID_STATUSES)}"})
    return governance.list_queue(status=status, page=page, page_size=page_size)


class DecideRequest(BaseModel):
    status: str
    note: Optional[str] = None


@router.post("/{item_id}/decide")
def decide_item(item_id: int, body: DecideRequest, reviewer: Dict[str, Any] = Depends(require_demo_auth)):
    """Requires ABHA Demo Mode auth (see app/auth.py) — a real reviewer identity is stamped from the token."""
    try:
        note = f"[{reviewer.get('name')}, {reviewer.get('role')}] {body.note or ''}".strip()
        result = governance.decide(item_id=item_id, status=body.status, note=note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "INVALID_DECISION", "message": str(e)})
    except LookupError as e:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})

    audit.log(
        action=f"REVIEW_{body.status.upper()}",
        actor=f"{reviewer.get('name')} ({reviewer.get('role')})",
        target=f"review_queue/{item_id} -> {result.get('source_code')}",
        details=(
            f"Decided '{body.status}' on {result.get('flag_type', 'ai_suggestion')} item "
            f"(decision={result.get('decision')}); "
            + (f"wrote concept_map#{result['new_concept_mapping_id']}" if result.get("new_concept_mapping_id") else "no registry write")
        ),
    )
    return result
