"""
FHIR R4 $translate / CodeSystem / ValueSet/$expand — additive alongside the
existing app/conceptmap.py (GET /ConceptMap, GET /ConceptMap/{code}).

Scope for this pass (see README "What's real vs demo-mode"):
  REAL: $translate (curated-first, AI-fallback via app/ai_mapping.py),
        CodeSystem (content="not-present" + real count), ValueSet/$expand
        (real FTS5 search wrapped in FHIR expansion shape).
  NOT BUILT: POST /Bundle ingestion, Consent resource, ICD-11 Biomedicine
        dual-coding (no Biomedicine data source exists in this repo).
"""
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from app import ai_mapping

DB_PATH = "db/ayush_icd11_combined.db"
AGENT_NAME = "NAMASTE-ICD11 AI Mapping Engine v0.1"

SYSTEM_URIS = {
    "NAM": "http://namaste.terminology/CodeSystem/ayurveda-morbidity",
    "NSM": "http://namaste.terminology/CodeSystem/siddha-morbidity",
    "NUM": "http://namaste.terminology/CodeSystem/unani-morbidity",
    "AST": "http://namaste.terminology/CodeSystem/ayurveda-standard",
    "NAMASTE": "http://namaste.terminology/CodeSystem",
    "ICD11": "http://id.who.int/icd/release/11/mms",
}
URI_TO_SYSTEM = {v: k for k, v in SYSTEM_URIS.items()}

RELATIONSHIP_TO_EQUIVALENCE = {"equivalent": "equivalent", "relatedto": "inexact"}

router = APIRouter(tags=["FHIR Extended"])


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_system(system: str) -> str:
    return URI_TO_SYSTEM.get(system, system.upper())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/ConceptMap/$translate")
def translate(
    system: str = Query(..., description="Source system URI or code (e.g. NAM, NAMASTE)"),
    code: str = Query(...),
    target_system: str = Query("ICD11"),
):
    """
    FHIR R4 ConceptMap $translate. Curated concept_map row wins if present;
    otherwise falls back to the AI decision engine. NO_VALIDATED_EQUIVALENT
    returns result:false/equivalence:"unmatched" explicitly, never omitted.
    """
    source_system = _resolve_system(system)
    normalized_code = re.sub(r"\s+", " ", code).strip()

    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_code, target_code, equivalence FROM concept_map
        WHERE source_code = ? OR source_code LIKE ? OR source_code LIKE ?
        """,
        (normalized_code, f"{normalized_code}(%", f"{normalized_code} %"),
    )
    curated_rows = cur.fetchall()

    if curated_rows:
        match_parts = []
        for row in curated_rows:
            cur.execute("SELECT title FROM icd11 WHERE code = ? LIMIT 1", (row["target_code"],))
            target_row = cur.fetchone()
            match_parts.append({
                "name": "match",
                "part": [
                    {"name": "equivalence", "valueCode": RELATIONSHIP_TO_EQUIVALENCE.get(row["equivalence"], "inexact")},
                    {"name": "concept", "valueCoding": {
                        "system": SYSTEM_URIS["ICD11"],
                        "code": row["target_code"],
                        "display": target_row["title"] if target_row else row["target_code"],
                    }},
                    {"name": "source", "valueUri": "curated-registry"},
                ],
            })
        conn.close()
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "result", "valueBoolean": True},
                {"name": "message", "valueString": "Matched against the curated (rule-based/reviewed) mapping registry."},
                *match_parts,
            ],
        }
    conn.close()

    try:
        suggestion = ai_mapping.get_candidates(normalized_code)
    except ai_mapping.EngineNotReadyError as e:
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "result", "valueBoolean": False},
                {"name": "message", "valueString": f"No curated mapping, and AI engine not ready: {e}"},
                {"name": "match", "part": [{"name": "equivalence", "valueCode": "unmatched"}]},
            ],
        }
    except ai_mapping.SourceConceptNotFoundError:
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "result", "valueBoolean": False},
                {"name": "message", "valueString": f"Unknown source code {source_system}/{normalized_code}"},
                {"name": "match", "part": [{"name": "equivalence", "valueCode": "unmatched"}]},
            ],
        }

    if suggestion["decision"] == "NO_VALIDATED_EQUIVALENT" or not suggestion["candidates"]:
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "result", "valueBoolean": False},
                {"name": "message", "valueString": suggestion["rationale"]},
                {"name": "match", "part": [{"name": "equivalence", "valueCode": "unmatched"}]},
            ],
        }

    top = suggestion["candidates"][0]
    provenance_resource = {
        "resourceType": "Provenance",
        "recorded": _now_iso(),
        "agent": [{"who": {"display": AGENT_NAME}}],
        "extension": [
            {"url": "http://namaste.terminology/fhir/StructureDefinition/mapping-decision", "valueString": suggestion["decision"]},
            {"url": "http://namaste.terminology/fhir/StructureDefinition/mapping-confidence", "valueDecimal": top["similarity"]},
        ],
    }
    return {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "result", "valueBoolean": True},
            {"name": "message", "valueString": f"No curated mapping — AI suggestion only ({suggestion['decision']}). Not a validated clinical mapping."},
            {"name": "match", "part": [
                {"name": "equivalence", "valueCode": "inexact"},
                {"name": "concept", "valueCoding": {
                    "system": SYSTEM_URIS.get(target_system.upper(), target_system),
                    "code": top["icd11_code"],
                    "display": top["icd11_title"],
                }},
                {"name": "source", "valueUri": "ai-mapping-engine"},
            ]},
            {"name": "provenance", "resource": provenance_resource},
        ],
    }


_CODE_SYSTEM_TABLES = {"NAM": "nam", "NSM": "nsm", "NUM": "num", "AST": "ast", "ICD11": "icd11"}


@router.get("/CodeSystem/{system_code}")
def get_code_system(system_code: str):
    system_code = system_code.upper()
    if system_code not in _CODE_SYSTEM_TABLES:
        raise HTTPException(status_code=404, detail={"error": "UNKNOWN_SYSTEM", "message": f"Unknown system: {system_code}"})

    conn = _conn()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {_CODE_SYSTEM_TABLES[system_code]}")
    count = cur.fetchone()[0]
    conn.close()

    return {
        "resourceType": "CodeSystem",
        "url": SYSTEM_URIS.get(system_code, system_code),
        "name": system_code,
        "status": "active",
        "content": "not-present",
        "count": count,
        "description": (
            "Content mode 'not-present' with a real live count; concept lookup is served "
            "via $translate/$expand rather than embedding the full concept list here."
        ),
    }


@router.get("/ValueSet/$expand")
def expand_valueset(
    filter: str = Query("", alias="filter"),
    system: str = Query("both", description="namaste | icd11 | both"),
    count: int = Query(20, ge=1, le=100),
):
    conn = _conn()
    cur = conn.cursor()
    safe_q = filter.replace('"', "").strip()
    contains = []

    if safe_q:
        fts_query = f'"{safe_q}"' if " " in safe_q else f"{safe_q}*"

        if system.lower() in ("namaste", "both"):
            try:
                cur.execute(
                    "SELECT namc_code, namc_term FROM nam_fts WHERE nam_fts MATCH ? LIMIT ?",
                    (fts_query, count),
                )
                for r in cur.fetchall():
                    contains.append({"system": SYSTEM_URIS["NAM"], "code": r["namc_code"], "display": r["namc_term"]})
            except sqlite3.OperationalError:
                pass

        if system.lower() in ("icd11", "both"):
            remaining = count - len(contains)
            if remaining > 0:
                try:
                    cur.execute(
                        """
                        SELECT i.code, i.title FROM icd11_fts f
                        JOIN icd11 i ON f.rowid = i.rowid
                        WHERE f MATCH ? LIMIT ?
                        """,
                        (fts_query, remaining),
                    )
                    for r in cur.fetchall():
                        contains.append({"system": SYSTEM_URIS["ICD11"], "code": r["code"], "display": r["title"]})
                except sqlite3.OperationalError:
                    pass

    conn.close()

    return {
        "resourceType": "ValueSet",
        "status": "active",
        "expansion": {
            "timestamp": _now_iso(),
            "total": len(contains),
            "contains": contains[:count],
        },
    }
