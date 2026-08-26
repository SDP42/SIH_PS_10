"""Governance & interoperability analytics — mounted under /api/analytics. Read-only, open."""
from fastapi import APIRouter, Query

from app import analytics

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/overview")
def get_overview():
    """
    Single-call payload for the analytics dashboard: corpus/coverage per
    tradition, mapping registry composition, review-queue throughput, WHO
    sync posture, and real audit activity.
    """
    return analytics.overview()


@router.get("/audit-activity")
def get_audit_activity(days: int = Query(30, ge=1, le=180)):
    """Real audit-log volume per day, for a standalone activity chart."""
    return {"days": days, "activity": analytics._audit_activity(days)}
