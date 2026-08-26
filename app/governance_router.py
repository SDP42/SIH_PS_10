"""Governance / expert-review API — mounted under /api/governance."""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query

from app import governance

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
def decide_item(item_id: int, body: DecideRequest):
    try:
        return governance.decide(item_id=item_id, status=body.status, note=body.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "INVALID_DECISION", "message": str(e)})
    except LookupError as e:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})
