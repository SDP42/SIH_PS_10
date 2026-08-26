"""
Population Health Demo API — mounted under /api/analytics/population-demo,
deliberately namespaced apart from /api/analytics/overview (the real
governance dashboard, app/analytics.py). Every response here describes
SYNTHETIC, fabricated data — see app/population_analytics.py's docstring.
"""
from fastapi import APIRouter

from app import population_analytics as pop

router = APIRouter(prefix="/api/analytics/population-demo", tags=["Population Health Demo (Synthetic)"])


@router.get("")
def get_population_demo():
    """Single-call payload for the Population Health Demo page. Always synthetic — see `disclaimer`."""
    return pop.full_demo_payload()
