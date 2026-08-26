"""
Terminology "What-If" Simulator API — mounted under /api/v1/terminology.

Running a simulation is read-only against concept_map/review_queue (it only
writes to its own terminology_simulations tables), so GET-shaped reads are
open; escalating findings into the real review queue is a governance action
and requires the same ABHA Demo Mode auth as approving a mapping.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app import audit, terminology_simulator as sim, who_sync
from app.auth import require_demo_auth

router = APIRouter(prefix="/api/v1/terminology", tags=["What-If Simulator"])


@router.get("/releases")
def list_releases():
    """Same credential-free WHO release index the What-If picker draws from."""
    return sim.available_releases()


class SimulateRequest(BaseModel):
    from_release: str
    to_release: str


@router.post("/simulate")
def simulate(body: SimulateRequest, operator: Dict[str, Any] = Depends(require_demo_auth)):
    """
    Diffs two ICD-11 releases and reports the impact on our own mapping
    registry. Read-only against concept_map/review_queue — nothing is
    modified until a separate, explicit /escalate call.
    """
    actor = f"{operator.get('name')} ({operator.get('role')})"
    try:
        result = sim.run_simulation(body.from_release, body.to_release, run_by=actor)
    except who_sync.WhoApiError as e:
        raise HTTPException(status_code=502, detail={"error": "WHO_FETCH_FAILED", "message": str(e)})

    audit.log(
        action="TERMINOLOGY_SIMULATION_RUN", actor=actor,
        target=f"simulation/{result['id']} ({body.from_release} -> {body.to_release})",
        details=f"risk={result['risk_score']}, broken={result['broken_mappings']}, ambiguous={result['ambiguous_mappings']}",
    )
    return result


@router.get("/simulate/{sim_id}")
def get_simulation(sim_id: int):
    result = sim.get_simulation(sim_id)
    if not result:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"No simulation with id {sim_id}"})
    return result


@router.get("/simulate/{sim_id}/affected-mappings")
def get_affected_mappings(sim_id: int, impact_type: Optional[str] = Query(None)):
    if not sim.get_simulation(sim_id):
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"No simulation with id {sim_id}"})
    return {"items": sim.affected_mappings(sim_id, impact_type)}


@router.post("/simulate/{sim_id}/escalate")
def escalate(sim_id: int, operator: Dict[str, Any] = Depends(require_demo_auth)):
    """Pushes every affected mapping into the real expert review queue. Requires ABHA Demo Mode auth."""
    if not sim.get_simulation(sim_id):
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"No simulation with id {sim_id}"})

    actor = f"{operator.get('name')} ({operator.get('role')})"
    result = sim.escalate_to_review(sim_id, actor)

    audit.log(
        action="TERMINOLOGY_SIMULATION_ESCALATED", actor=actor,
        target=f"simulation/{sim_id}", details=f"{result['count']} mappings pushed to review_queue",
    )
    return result


@router.get("/simulations")
def list_history(limit: int = Query(20, ge=1, le=100)):
    return {"simulations": sim.history(limit)}
