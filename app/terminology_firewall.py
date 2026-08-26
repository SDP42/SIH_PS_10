"""
Terminology Firewall — Phase 3C.

"A clinical terminology quality gateway for existing EMRs." Deliberately
not a new validation engine: every check here is a call into logic that
already exists and is already tested (app.fhir_extra's structural coding
extraction and dual-coding translate, app.v1_router's code-existence
table, app.who_sync's drift registry). The firewall's only real
contribution is composing those into one verdict an EMR integration can
act on without knowing this service's internals.

Verdicts:
  ACCEPTED         every Condition's NAMASTE coding exists, is current
                    (not WHO-retired per who_drift), and resolves to at
                    least one validated ICD-11 mapping.
  REVIEW_REQUIRED   the code exists but its ICD-11 mapping is uncertain
                    (AI decision NEEDS_CONTEXT/EXPERT_REVIEW) or the code
                    appears in who_drift as retitled/retired — a human
                    should look at this before it's trusted, not a machine.
  REJECTED          structurally invalid input, or the coding does not
                    exist in any known system at all.

This never invents a verdict the underlying checks don't support: a code
this service cannot resolve is REJECTED, not silently waved through, and
an ambiguous mapping is REVIEW_REQUIRED, never auto-accepted. Nothing here
writes to concept_map, review_queue, or the source Bundle — a firewall
check is advisory, not a mutation.
"""
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app import fhir_extra, v1_router, who_sync

DB_PATH = "db/ayush_icd11_combined.db"

VERDICT_ACCEPTED = "ACCEPTED"
VERDICT_REVIEW = "REVIEW_REQUIRED"
VERDICT_REJECTED = "REJECTED"

_REQUIRED_CONDITION_FIELDS = ["clinicalStatus", "subject"]

DISCLAIMER = (
    "The firewall composes this service's existing code-existence check, WHO drift registry, and "
    "dual-coding translate logic into one verdict — it does not implement ICD-11 postcoordination/axis "
    "validation. A REJECTED or REVIEW_REQUIRED verdict should be treated as 'this service could not "
    "confirm the coding,' not as a definitive clinical judgment."
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema() -> None:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS firewall_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_ref TEXT,
            verdict TEXT NOT NULL,
            reasons TEXT NOT NULL,
            checked_conditions INTEGER NOT NULL DEFAULT 0,
            decided_at TEXT NOT NULL,
            decided_by TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_firewall_decided ON firewall_decisions(decided_at DESC)")
    conn.commit()
    conn.close()


def _is_code_retired_or_stale(cur, code: str) -> Optional[str]:
    """Checks who_drift for a known drift finding against this exact target code."""
    cur.execute(
        "SELECT drift_type, who_title FROM who_drift WHERE code = ? ORDER BY detected_at DESC LIMIT 1",
        (code,),
    )
    row = cur.fetchone()
    if not row:
        return None
    if row["drift_type"] == who_sync.CMP_NOT_IN_RELEASE:
        return f"WHO no longer lists this code in its current release (checked via WHO Sync)."
    if row["drift_type"] == who_sync.CMP_TITLE_DRIFT:
        return f"WHO has retitled this code since our snapshot (now: \"{row['who_title']}\") — confirm the mapping still applies."
    return None


def _check_one_condition(cur, resource: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[str] = []
    verdict = VERDICT_ACCEPTED

    missing = [f for f in _REQUIRED_CONDITION_FIELDS if f not in resource]
    if missing:
        issues.append(f"Condition is missing required field(s): {', '.join(missing)}.")
        verdict = VERDICT_REJECTED

    coding = fhir_extra._extract_namaste_coding(resource)
    if not coding or not coding.get("code"):
        issues.append("No NAMASTE coding found on this Condition.")
        return {"resource_id": resource.get("id"), "verdict": VERDICT_REJECTED, "issues": issues, "source_code": None}

    normalized_code = re.sub(r"\s+", " ", coding["code"]).strip()
    source_system = fhir_extra._resolve_system(coding.get("system", ""))

    table_info = v1_router._VALIDATE_TABLES.get(source_system.upper())
    if not table_info:
        issues.append(f"Unrecognized source system '{source_system}'.")
        return {"resource_id": resource.get("id"), "verdict": VERDICT_REJECTED, "issues": issues, "source_code": normalized_code}

    table, code_col, _ = table_info
    cur.execute(f"SELECT 1 FROM {table} WHERE {code_col} = ? LIMIT 1", (normalized_code,))
    if not cur.fetchone():
        issues.append(f"Code '{normalized_code}' does not exist in {source_system}.")
        return {"resource_id": resource.get("id"), "verdict": VERDICT_REJECTED, "issues": issues, "source_code": normalized_code}

    match_parts, unknown_message = fhir_extra.dual_translate_match_parts(
        normalized_code, ["ICD-11 TM2", "ICD-11 Biomedicine"], source_system
    )
    if unknown_message and not match_parts:
        issues.append(unknown_message)
        return {"resource_id": resource.get("id"), "verdict": VERDICT_REJECTED, "issues": issues, "source_code": normalized_code}

    any_matched = False
    any_uncertain = False
    drifted_targets: List[str] = []
    for part in match_parts:
        fields = {p["name"]: p for p in part["part"]}
        equivalence = fields["equivalence"]["valueCode"]
        if equivalence == "unmatched":
            continue
        any_matched = True
        target_code = fields["concept"]["valueCoding"]["code"]
        drift_note = _is_code_retired_or_stale(cur, target_code)
        if drift_note:
            drifted_targets.append(f"{target_code}: {drift_note}")
        if "provenance" in fields:
            decision = next(
                (e["valueString"] for e in fields["provenance"]["resource"].get("extension", [])
                 if e["url"].endswith("mapping-decision")),
                None,
            )
            if decision in ("NEEDS_CONTEXT", "EXPERT_REVIEW"):
                any_uncertain = True

    mapping_verdict = VERDICT_ACCEPTED
    if not any_matched:
        issues.append("No validated ICD-11 equivalent (NAMASTE code is real, but no confident mapping exists).")
        mapping_verdict = VERDICT_REVIEW
    elif any_uncertain:
        issues.append("Mapping was produced by the AI engine at a confidence tier that requires expert confirmation.")
        mapping_verdict = VERDICT_REVIEW
    elif drifted_targets:
        issues.extend(drifted_targets)
        mapping_verdict = VERDICT_REVIEW

    # A structural failure (missing required Condition fields, caught above)
    # is always at least as severe as a mapping-quality finding — take the
    # worse of the two rather than letting the later check silently
    # overwrite an earlier REJECTED with a milder REVIEW_REQUIRED.
    final_verdict = max(verdict, mapping_verdict, key=lambda v: _VERDICT_RANK[v])
    return {"resource_id": resource.get("id"), "verdict": final_verdict, "issues": issues, "source_code": normalized_code}


_VERDICT_RANK = {VERDICT_ACCEPTED: 0, VERDICT_REVIEW: 1, VERDICT_REJECTED: 2}


def check_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs every Condition in a Bundle through the firewall and returns the
    worst verdict across all of them (REJECTED > REVIEW_REQUIRED >
    ACCEPTED), plus a per-resource breakdown. Never modifies the Bundle,
    concept_map, or review_queue.
    """
    if bundle.get("resourceType") != "Bundle":
        return {
            "verdict": VERDICT_REJECTED,
            "checked_conditions": 0,
            "results": [],
            "reasons": ["resourceType must be 'Bundle'."],
            "disclaimer": DISCLAIMER,
        }

    conn = _conn()
    cur = conn.cursor()
    try:
        results = []
        for entry in bundle.get("entry", []):
            resource = entry.get("resource") or {}
            if resource.get("resourceType") != "Condition":
                continue
            results.append(_check_one_condition(cur, resource))
    finally:
        conn.close()

    if not results:
        return {
            "verdict": VERDICT_REJECTED,
            "checked_conditions": 0,
            "results": [],
            "reasons": ["Bundle contains no Condition resource with a NAMASTE coding to check."],
            "disclaimer": DISCLAIMER,
        }

    overall = max((r["verdict"] for r in results), key=lambda v: _VERDICT_RANK[v])
    all_reasons = [issue for r in results for issue in r["issues"]]

    return {
        "verdict": overall,
        "checked_conditions": len(results),
        "results": results,
        "reasons": all_reasons,
        "disclaimer": DISCLAIMER,
    }


def record_decision(bundle_ref: Optional[str], result: Dict[str, Any], decided_by: str) -> int:
    import json as _json
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO firewall_decisions (bundle_ref, verdict, reasons, checked_conditions, decided_at, decided_by)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (bundle_ref, result["verdict"], _json.dumps(result["reasons"]), result["checked_conditions"],
         datetime.now(timezone.utc).isoformat(), decided_by),
    )
    decision_id = cur.lastrowid
    conn.commit()
    conn.close()
    return decision_id


def history(limit: int = 20) -> List[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM firewall_decisions ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
