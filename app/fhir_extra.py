"""
FHIR R4 $translate / CodeSystem / ValueSet/$expand — additive alongside the
existing app/conceptmap.py (GET /ConceptMap, GET /ConceptMap/{code}).

Scope for this pass (see README "What's real vs demo-mode"):
  REAL: $translate — real double-coding, returns independent TM2 AND
        Biomedicine match groups in one response (curated-first per system,
        AI-fallback via app/ai_mapping.py's dual-pool engine); CodeSystem,
        split into ICD11-TM2 (~1,246 concepts) and ICD11-BIOMEDICINE
        (~35,536 concepts) with real counts; ValueSet/$expand (real FTS5
        search wrapped in FHIR expansion shape).
  NOT BUILT: Consent is a stub (see app/consent.py); WHO International
        Terminology of Ayurveda is unverified (the `ast` table may not be
        that exact vocabulary — see README).
"""
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app import ai_mapping, audit
from app.auth import require_demo_auth

DB_PATH = "db/ayush_icd11_combined.db"
AGENT_NAME = "NAMASTE-ICD11 AI Mapping Engine v0.1"

SYSTEM_URIS = {
    "NAM": "http://namaste.terminology/CodeSystem/ayurveda-morbidity",
    "NSM": "http://namaste.terminology/CodeSystem/siddha-morbidity",
    "NUM": "http://namaste.terminology/CodeSystem/unani-morbidity",
    "AST": "http://namaste.terminology/CodeSystem/ayurveda-standard",
    "NAMASTE": "http://namaste.terminology/CodeSystem",
    # WHO's ICD-11 MMS linearization is one URI space — TM2 (chapter 26) and
    # Biomedicine (chapters 01-25) are both part of it; we distinguish them
    # by resource name/count in this service, not by a different WHO URI.
    "ICD11": "http://id.who.int/icd/release/11/mms",
    "ICD-11 TM2": "http://id.who.int/icd/release/11/mms",
    "ICD-11 Biomedicine": "http://id.who.int/icd/release/11/mms",
}
URI_TO_SYSTEM = {v: k for k, v in SYSTEM_URIS.items() if k not in ("ICD-11 TM2", "ICD-11 Biomedicine")}

RELATIONSHIP_TO_EQUIVALENCE = {"equivalent": "equivalent", "relatedto": "inexact"}

_TARGET_SYSTEM_ALIASES = {
    "BOTH": ["ICD-11 TM2", "ICD-11 Biomedicine"],
    "ALL": ["ICD-11 TM2", "ICD-11 Biomedicine"],
    "ICD11": ["ICD-11 TM2", "ICD-11 Biomedicine"],
    "ICD11-TM2": ["ICD-11 TM2"],
    "TM2": ["ICD-11 TM2"],
    "ICD11-BIOMEDICINE": ["ICD-11 Biomedicine"],
    "BIOMEDICINE": ["ICD-11 Biomedicine"],
}
_SYSTEM_TO_POOL = {"ICD-11 TM2": "TM2", "ICD-11 Biomedicine": "BIOMEDICINE"}

router = APIRouter(tags=["FHIR Extended"])


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_system(system: str) -> str:
    return URI_TO_SYSTEM.get(system, system.upper())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _curated_rows_for(cur, normalized_code: str, systems: List[str]) -> List[sqlite3.Row]:
    placeholders = ",".join("?" for _ in systems)
    cur.execute(
        f"""
        SELECT source_code, target_code, target_system, equivalence FROM concept_map
        WHERE (source_code = ? OR source_code LIKE ? OR source_code LIKE ?)
          AND target_system IN ({placeholders})
        """,
        (normalized_code, f"{normalized_code}(%", f"{normalized_code} %", *systems),
    )
    return cur.fetchall()


def _match_part_for_curated(cur, row: sqlite3.Row) -> Dict[str, Any]:
    cur.execute("SELECT title FROM icd11 WHERE code = ? LIMIT 1", (row["target_code"],))
    target_row = cur.fetchone()
    return {
        "name": "match",
        "part": [
            {"name": "equivalence", "valueCode": RELATIONSHIP_TO_EQUIVALENCE.get(row["equivalence"], "inexact")},
            {"name": "concept", "valueCoding": {
                "system": SYSTEM_URIS[row["target_system"]],
                "code": row["target_code"],
                "display": target_row["title"] if target_row else row["target_code"],
            }},
            {"name": "source", "valueUri": "curated-registry"},
            {"name": "targetSystemGroup", "valueString": row["target_system"]},
        ],
    }


def _match_part_for_ai(target_system_label: str, suggestion: Dict[str, Any]) -> Dict[str, Any]:
    if suggestion["decision"] == "NO_VALIDATED_EQUIVALENT" or not suggestion["candidates"]:
        return {
            "name": "match",
            "part": [
                {"name": "equivalence", "valueCode": "unmatched"},
                {"name": "targetSystemGroup", "valueString": target_system_label},
                {"name": "message", "valueString": suggestion["rationale"]},
            ],
        }
    top = suggestion["candidates"][0]
    provenance_resource = {
        "resourceType": "Provenance",
        "recorded": _now_iso(),
        "agent": [{"who": {"display": AGENT_NAME}}],
        # Provenance.target is a REQUIRED field in FHIR R4 (1..*) — this was
        # missing before, so every AI-sourced Provenance emitted by
        # $translate silently failed schema validation against the
        # fhir.resources Provenance model, even though it looked fine as
        # plain JSON. At translate-time there is no persisted resource yet
        # (this is a preview, not a stored Condition), so target references
        # the target concept itself by display rather than a resolvable URL
        # — a display-only Reference is valid FHIR, and the caller
        # (app/problem_list.py, app/fhir_extra.upload_bundle) overwrites
        # this with a real resource reference once one actually exists.
        "target": [{"display": f"{target_system_label} {top['icd11_code']}: {top['icd11_title']}"}],
        "extension": [
            {"url": "http://namaste.terminology/fhir/StructureDefinition/mapping-decision", "valueString": suggestion["decision"]},
            {"url": "http://namaste.terminology/fhir/StructureDefinition/mapping-confidence", "valueDecimal": top["similarity"]},
        ],
    }
    return {
        "name": "match",
        "part": [
            {"name": "equivalence", "valueCode": "inexact"},
            {"name": "concept", "valueCoding": {
                "system": SYSTEM_URIS[target_system_label],
                "code": top["icd11_code"],
                "display": top["icd11_title"],
            }},
            {"name": "source", "valueUri": "ai-mapping-engine"},
            {"name": "targetSystemGroup", "valueString": target_system_label},
            {"name": "provenance", "resource": provenance_resource},
        ],
    }


def dual_translate_match_parts(normalized_code: str, requested_systems: List[str], source_system: str = ""):
    """
    Core double-coding logic, reused by both GET /ConceptMap/$translate and
    POST /Bundle: curated-first per requested target system, AI dual-pool
    fallback otherwise. Returns (match_parts, source_unknown_message) — the
    latter is set (and match_parts left empty) when the source code itself
    isn't recognized at all, regardless of target system.
    """
    conn = _conn()
    cur = conn.cursor()
    curated_rows = _curated_rows_for(cur, normalized_code, requested_systems)
    matched_systems = {row["target_system"] for row in curated_rows}
    match_parts = [_match_part_for_curated(cur, row) for row in curated_rows]
    conn.close()

    missing_systems = [s for s in requested_systems if s not in matched_systems]
    source_unknown_message = None

    for system_label in missing_systems:
        pool = _SYSTEM_TO_POOL[system_label]
        try:
            suggestion = ai_mapping.get_candidates(normalized_code, target_pool=pool)
        except ai_mapping.EngineNotReadyError as e:
            match_parts.append({
                "name": "match",
                "part": [
                    {"name": "equivalence", "valueCode": "unmatched"},
                    {"name": "targetSystemGroup", "valueString": system_label},
                    {"name": "message", "valueString": f"AI engine not ready: {e}"},
                ],
            })
            continue
        except ai_mapping.SourceConceptNotFoundError:
            source_unknown_message = f"Unknown source code {source_system}/{normalized_code}".strip()
            break
        match_parts.append(_match_part_for_ai(system_label, suggestion))

    return match_parts, source_unknown_message


@router.get("/ConceptMap/$translate")
def translate(
    system: str = Query(..., description="Source system URI or code (e.g. NAM, NAMASTE)"),
    code: str = Query(...),
    target_system: str = Query(
        "BOTH", description="ICD11-TM2 | ICD11-BIOMEDICINE | BOTH (default) — real double-coding when BOTH"
    ),
):
    """
    FHIR R4 ConceptMap $translate — real double-coding: by default returns
    one match group for TM2 and one for Biomedicine, each independently
    curated-first / AI-fallback. NO_VALIDATED_EQUIVALENT for a given system
    returns equivalence:"unmatched" for that system's match group explicitly,
    never silently omitted — even if the *other* system did match.
    """
    source_system = _resolve_system(system)
    normalized_code = re.sub(r"\s+", " ", code).strip()
    requested_systems = _TARGET_SYSTEM_ALIASES.get(target_system.upper(), _TARGET_SYSTEM_ALIASES["BOTH"])

    match_parts, source_unknown_message = dual_translate_match_parts(normalized_code, requested_systems, source_system)

    if source_unknown_message and not match_parts:
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "result", "valueBoolean": False},
                {"name": "message", "valueString": source_unknown_message},
                {"name": "match", "part": [{"name": "equivalence", "valueCode": "unmatched"}]},
            ],
        }

    any_real_match = any(
        p["part"][0]["valueCode"] != "unmatched" for p in match_parts
    )
    message = (
        "Matched against the curated registry and/or the AI mapping engine — "
        "see each match's targetSystemGroup and source for provenance."
        if any_real_match
        else "No validated equivalent in any requested target system."
    )

    return {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "result", "valueBoolean": any_real_match},
            {"name": "message", "valueString": message},
            *match_parts,
        ],
    }


_CODE_SYSTEM_TABLES = {"NAM": "nam", "NSM": "nsm", "NUM": "num", "AST": "ast"}
# ICD11-TM2 / ICD11-BIOMEDICINE are counted via a chapter-filtered query
# rather than a plain table count (see _CODE_SYSTEM_TABLES above), since
# they're both subsets of the single icd11 table split by chapterno.
_ICD11_CHAPTER_QUERIES = {
    "ICD11-TM2": "SELECT COUNT(*) FROM icd11 WHERE chapterno = '26' AND title LIKE '%(TM2)%'",
    "ICD11-BIOMEDICINE": "SELECT COUNT(*) FROM icd11 WHERE chapterno NOT IN ('26', 'V', 'X') AND chapterno != ''",
}


@router.get("/CodeSystem/{system_code}")
def get_code_system(system_code: str):
    system_code = system_code.upper()

    conn = _conn()
    cur = conn.cursor()

    if system_code in _CODE_SYSTEM_TABLES:
        cur.execute(f"SELECT COUNT(*) FROM {_CODE_SYSTEM_TABLES[system_code]}")
        count = cur.fetchone()[0]
        url = SYSTEM_URIS.get(system_code, system_code)
        description = (
            "Content mode 'not-present' with a real live count; concept lookup is served "
            "via $translate/$expand rather than embedding the full concept list here."
        )
        if system_code == "AST":
            description += (
                " NOTE: labeled 'Ayurveda Standard Terminology' — this has NOT been verified "
                "against WHO's official 'International Terminologies of Ayurveda' publication; "
                "treat as best-available data, not a confirmed match to that specific standard."
            )
    elif system_code in _ICD11_CHAPTER_QUERIES:
        cur.execute(_ICD11_CHAPTER_QUERIES[system_code])
        count = cur.fetchone()[0]
        url = SYSTEM_URIS["ICD-11 TM2" if system_code == "ICD11-TM2" else "ICD-11 Biomedicine"]
        description = (
            "Chapter 26 Traditional Medicine Module 2 codes only (excludes TM1)."
            if system_code == "ICD11-TM2"
            else "WHO ICD-11 MMS chapters 01-25 (excludes TM2/TM1 chapter 26 and extension chapters V/X)."
        )
    else:
        conn.close()
        raise HTTPException(status_code=404, detail={"error": "UNKNOWN_SYSTEM", "message": f"Unknown system: {system_code}"})

    conn.close()
    return {
        "resourceType": "CodeSystem",
        "url": url,
        "name": system_code,
        "status": "active",
        "content": "not-present",
        "count": count,
        "description": description,
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
                        WHERE icd11_fts MATCH ? LIMIT ?
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


_NAMASTE_SYSTEM_URIS = {SYSTEM_URIS[k] for k in ("NAM", "NSM", "NUM", "AST", "NAMASTE")}
MAPPING_EQUIVALENCE_EXT_URL = "http://namaste.terminology/fhir/StructureDefinition/mapping-equivalence"


def _extract_namaste_coding(condition: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    codings = ((condition.get("code") or {}).get("coding")) or []
    for c in codings:
        if c.get("system") in _NAMASTE_SYSTEM_URIS:
            return c
    return codings[0] if codings else None


@router.post("/Bundle")
def upload_bundle(body: Dict[str, Any] = Body(...), identity: Dict[str, Any] = Depends(require_demo_auth)):
    """
    Secure* FHIR Bundle upload for double-coding: accepts a Bundle containing
    one or more Condition resources with a NAMASTE coding, resolves each
    independently against TM2 AND Biomedicine (curated-first, AI-fallback —
    same logic as $translate), and returns the Bundle with
    Condition.code.coding[] enriched with both codes plus inline Provenance
    entries for any AI-sourced addition.

    *"Secure": gated behind demo-mode ABHA auth (app/auth.py) — see that
    module's docstring for exactly what "secure" does and doesn't mean here.
    """
    if body.get("resourceType") != "Bundle":
        raise HTTPException(status_code=400, detail={"error": "NOT_A_BUNDLE", "message": "resourceType must be 'Bundle'"})

    entries = body.get("entry") or []
    provenance_entries = []
    conditions_processed = 0

    for entry in entries:
        resource = entry.get("resource") or {}
        if resource.get("resourceType") != "Condition":
            continue

        coding = _extract_namaste_coding(resource)
        if not coding or not coding.get("code"):
            continue

        normalized_code = re.sub(r"\s+", " ", coding["code"]).strip()
        match_parts, unknown_message = dual_translate_match_parts(
            normalized_code, ["ICD-11 TM2", "ICD-11 Biomedicine"]
        )
        conditions_processed += 1

        existing_codings = resource.setdefault("code", {}).setdefault("coding", [])
        for part in match_parts:
            fields = {p["name"]: p for p in part["part"]}
            equivalence = fields["equivalence"]["valueCode"]
            if equivalence == "unmatched":
                continue
            concept = dict(fields["concept"]["valueCoding"])
            concept["extension"] = [{"url": MAPPING_EQUIVALENCE_EXT_URL, "valueCode": equivalence}]
            existing_codings.append(concept)

            if "provenance" in fields:
                prov = dict(fields["provenance"]["resource"])
                prov["target"] = [{"reference": f"Condition/{resource.get('id', 'unknown')}"}]
                provenance_entries.append({"resource": prov})

        if unknown_message:
            resource.setdefault("extension", []).append(
                {"url": "http://namaste.terminology/fhir/StructureDefinition/translate-note", "valueString": unknown_message}
            )

    if conditions_processed == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "NO_NAMASTE_CONDITION",
                "message": "Bundle must contain at least one Condition resource with a NAMASTE coding.",
            },
        )

    body["entry"] = entries + provenance_entries
    body.setdefault("meta", {})["lastUpdated"] = _now_iso()

    audit.log(
        action="BUNDLE_UPLOAD",
        actor=f"{identity.get('name')} ({identity.get('role')})",
        target=f"Bundle ({conditions_processed} Condition(s) double-coded)",
        details=f"{len(provenance_entries)} AI-sourced Provenance entr{'y' if len(provenance_entries) == 1 else 'ies'} added",
    )
    return body
