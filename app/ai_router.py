"""
Ambiguity-aware AI mapping API.

Additive alongside the existing /ConceptMap and /api/* routes — mounted
under /api/ai in app/main.py.
"""
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query

from app import ai_mapping, governance

router = APIRouter(prefix="/api/ai", tags=["AI Mapping Engine"])


def _not_ready_response(e: Exception):
    raise HTTPException(
        status_code=503,
        detail={
            "error": "AI_ENGINE_NOT_READY",
            "message": str(e),
            "action": "Run: python scripts/build_embeddings.py",
        },
    )


@router.get("/suggest/{namaste_code:path}")
def suggest(namaste_code: str, source_system: Optional[str] = Query(None), top_k: int = Query(5, ge=1, le=20)):
    """Ambiguity-aware AI suggestion for a single NAMASTE-family code."""
    try:
        result = ai_mapping.get_candidates(namaste_code, source_system=source_system, top_k=top_k)
    except ai_mapping.EngineNotReadyError as e:
        _not_ready_response(e)
        return
    except ai_mapping.SourceConceptNotFoundError as e:
        raise HTTPException(status_code=404, detail={"error": "SOURCE_NOT_FOUND", "message": str(e)})

    if result["decision"] in ("NEEDS_CONTEXT", "EXPERT_REVIEW"):
        governance.enqueue_from_suggestion(result)
    return result


@router.get("/unmapped")
def unmapped(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200), source_system: Optional[str] = Query(None)):
    """Paginated list of NAMASTE-family codes with no curated concept_map row — the real mapping gap."""
    try:
        return ai_mapping.list_unmapped(page=page, page_size=page_size, source_system=source_system)
    except ai_mapping.EngineNotReadyError as e:
        _not_ready_response(e)


@router.get("/model-info")
def model_info():
    try:
        return ai_mapping.get_model_info()
    except ai_mapping.EngineNotReadyError as e:
        _not_ready_response(e)


class BatchSuggestRequest(BaseModel):
    codes: Optional[List[str]] = None
    all_unmapped: bool = False
    limit: int = 50
    source_system: Optional[str] = None


@router.post("/batch_suggest")
def batch_suggest(body: BatchSuggestRequest):
    """Run the AI suggestion engine over a batch of codes, or the next N unmapped codes."""
    codes = body.codes or []
    if body.all_unmapped:
        try:
            page = ai_mapping.list_unmapped(page=1, page_size=body.limit, source_system=body.source_system)
        except ai_mapping.EngineNotReadyError as e:
            _not_ready_response(e)
            return
        codes = [c["code"] for c in page["concepts"]]

    if not codes:
        raise HTTPException(status_code=400, detail={"error": "NO_CODES", "message": "Provide codes or all_unmapped=true."})

    results = []
    for code in codes[: body.limit]:
        try:
            suggestion = ai_mapping.get_candidates(code, source_system=body.source_system)
            if suggestion["decision"] in ("NEEDS_CONTEXT", "EXPERT_REVIEW"):
                governance.enqueue_from_suggestion(suggestion)
            results.append(suggestion)
        except ai_mapping.SourceConceptNotFoundError as e:
            results.append({"namaste_code": code, "error": str(e)})
        except ai_mapping.EngineNotReadyError as e:
            _not_ready_response(e)

    return {"requested": len(codes), "results": results}
