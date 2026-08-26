"""
Versioned public API surface for external EMR integration — mounted under
/api/v1. Every write-adjacent or search/translate endpoint here requires an
API key (app/apikey_auth.require_api_key) with the matching scope; the
CapabilityStatement is the one open, unauthenticated endpoint, since a
client needs to be able to discover what this server supports before it has
a key at all.

This is the "an EMR vendor could actually integrate against this" surface
named in the platform strategy doc's developer-portal workflow: create a
sandbox key -> call /api/v1/terminology/search -> /api/v1/translate ->
/api/v1/validate-code.
"""
import re
import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app import fhir_extra
from app.apikey_auth import require_api_key
from app.fhir_common import build_capability_statement, operation_outcome

router = APIRouter(prefix="/api/v1", tags=["Public API v1"])

DB_PATH = "db/ayush_icd11_combined.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/CapabilityStatement")
def capability_statement():
    """No API key required — a client must be able to discover this before it has one."""
    return build_capability_statement()


@router.get("/terminology/search")
def terminology_search(
    q: str = Query(..., min_length=1),
    system: Optional[str] = Query(None, description="namaste | icd11 | both"),
    page_size: int = Query(20, ge=1, le=100),
    key: Dict[str, Any] = Depends(require_api_key("search:read")),
):
    """Same search machinery as GET /api/search, gated behind an API key for external callers."""
    from app.api import search_concepts  # local import avoids a circular import at module load
    return search_concepts(q=q, system=system, page=1, page_size=page_size)


@router.get("/translate")
def translate(
    system: str = Query(...),
    code: str = Query(...),
    target_system: str = Query("BOTH"),
    key: Dict[str, Any] = Depends(require_api_key("translate:read")),
):
    """Same real double-coding logic as GET /ConceptMap/$translate, gated behind an API key."""
    return fhir_extra.translate(system=system, code=code, target_system=target_system)


_VALIDATE_TABLES = {
    "NAM": ("nam", "namc_code", "namc_term"),
    "NSM": ("nsm", "namc_code", "namc_term"),
    "NUM": ("num", "numc_code", "numc_term"),
    "AST": ("ast", "code", "word"),
    "ICD11": ("icd11", "code", "title"),
    "ICD-11": ("icd11", "code", "title"),
}


@router.post("/validate-code")
def validate_code(
    body: Dict[str, Any] = Body(..., examples=[{"system": "NAM", "code": "AAA-2.1"}]),
    key: Dict[str, Any] = Depends(require_api_key("validate:read")),
):
    """
    FHIR-style $validate-code: does this code genuinely exist in this
    system's table, right now? This is real code-existence validation —
    it does not (yet) check ICD-11 postcoordination/axis rules; see the
    platform strategy doc §16 for why that's deliberately not invented here.
    """
    system = str(body.get("system", "")).upper().strip()
    code = re.sub(r"\s+", " ", str(body.get("code", ""))).strip()

    if system not in _VALIDATE_TABLES:
        raise HTTPException(
            status_code=400,
            detail=operation_outcome("error", "invalid", f"Unknown system '{system}'. Known: {sorted(_VALIDATE_TABLES)}"),
        )
    if not code:
        raise HTTPException(status_code=400, detail=operation_outcome("error", "invalid", "code is required"))

    table, code_col, display_col = _VALIDATE_TABLES[system]
    conn = _conn()
    cur = conn.cursor()
    cur.execute(f"SELECT {display_col} FROM {table} WHERE {code_col} = ? LIMIT 1", (code,))
    row = cur.fetchone()
    conn.close()

    if row:
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "result", "valueBoolean": True},
                {"name": "display", "valueString": row[display_col]},
                {"name": "system", "valueString": system},
                {"name": "code", "valueString": code},
            ],
        }
    return {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "result", "valueBoolean": False},
            {"name": "message", "valueString": f"Code '{code}' was not found in {system}."},
        ],
    }
