"""
Terminology "What-If" Simulator — Phase 3.

Answers a question this project's live WHO sync (app/who_sync.py) can
already partially answer for exactly one pair of releases (our shipped
snapshot vs whatever WHO currently publishes), generalised to ANY two
releases: "if the terminology moved from release X to release Y, what in
*our* mapping registry breaks, goes ambiguous, or needs a human to look at
it again?"

Deliberately built as a thin layer over app/who_sync.py, not a parallel
download/parsing engine — fetch_release_table() already does the real work
(download, cache, parse WHO's Simple Tabulation format). This module only
adds: diffing two arbitrary releases against each other (who_sync only ever
diffs the current release against our local `icd11` snapshot), and joining
that diff against our own concept_map / review_queue to answer "so what
does this mean for us," which who_sync does not do at all.

Historical-record safety: running a simulation NEVER touches concept_map,
review_queue, or any FHIR resource. It only reads and writes to its own
terminology_simulations / simulation_affected_mappings tables, until an
operator explicitly calls escalate() — which inserts new review_queue rows
(never mutates concept_map), the same non-destructive discipline
app/governance.py already applies everywhere else in this project.
"""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app import who_sync

DB_PATH = "db/ayush_icd11_combined.db"

CHANGE_NEW = "NEW_CONCEPT"
CHANGE_DEPRECATED = "DEPRECATED_CONCEPT"
CHANGE_RETITLED = "RETITLED_CONCEPT"

# A mapping target that vanished between releases is an outright break; one
# that merely changed title is "ambiguous" — the code still exists, but a
# reviewer needs to confirm the mapping still means what it used to mean.
IMPACT_BROKEN = "BROKEN_MAPPING"
IMPACT_AMBIGUOUS = "AMBIGUOUS_MAPPING"

RISK_LOW, RISK_MEDIUM, RISK_HIGH = "LOW", "MEDIUM", "HIGH"

DISCLAIMER = (
    "A simulation only compares two ICD-11 release files and diffs them against this "
    "service's own mapping registry — it never modifies concept_map, review_queue, or any "
    "FHIR resource. Escalating a simulation's findings inserts new review_queue rows for a "
    "human to look at; it never rewrites or deletes an existing curated mapping."
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema() -> None:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS terminology_simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_release TEXT NOT NULL,
            to_release TEXT NOT NULL,
            run_at TEXT NOT NULL,
            run_by TEXT,
            new_count INTEGER NOT NULL DEFAULT 0,
            deprecated_count INTEGER NOT NULL DEFAULT 0,
            retitled_count INTEGER NOT NULL DEFAULT 0,
            broken_mapping_count INTEGER NOT NULL DEFAULT 0,
            ambiguous_mapping_count INTEGER NOT NULL DEFAULT 0,
            from_release_concept_count INTEGER,
            to_release_concept_count INTEGER,
            risk_score TEXT NOT NULL,
            escalated_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS simulation_affected_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            simulation_id INTEGER NOT NULL REFERENCES terminology_simulations(id),
            concept_map_id INTEGER,
            source_system TEXT,
            source_code TEXT,
            target_code TEXT NOT NULL,
            impact_type TEXT NOT NULL,
            old_title TEXT,
            new_title TEXT,
            review_queue_id INTEGER
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sim_affected_sim ON simulation_affected_mappings(simulation_id)")
    conn.commit()
    conn.close()


def _risk_score(broken: int, ambiguous: int, total_mappings: int) -> str:
    if total_mappings == 0:
        return RISK_LOW
    broken_pct = broken / total_mappings
    if broken > 0 and broken_pct >= 0.02:
        return RISK_HIGH
    if broken > 0 or ambiguous / total_mappings >= 0.05:
        return RISK_MEDIUM
    return RISK_LOW


def run_simulation(from_release: str, to_release: str, run_by: str = "system") -> Dict[str, Any]:
    """
    Downloads (or reuses the cached copy of) both release files via
    who_sync.fetch_release_table, diffs them, and joins the diff against our
    own concept_map to find real impact. Raises who_sync.WhoApiError if
    either release can't be fetched — the caller decides how to surface that.
    """
    from_table = who_sync.fetch_release_table(from_release)["table"]
    to_table = who_sync.fetch_release_table(to_release)["table"]

    from_codes = set(from_table)
    to_codes = set(to_table)

    new_codes = to_codes - from_codes
    deprecated_codes = from_codes - to_codes
    retitled_codes = {
        c for c in (from_codes & to_codes)
        if who_sync.normalize_title(from_table[c]) != who_sync.normalize_title(to_table[c])
    }

    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, source_system, source_code, target_code FROM concept_map WHERE TRIM(COALESCE(target_code,'')) != ''"
        )
        mapping_rows = cur.fetchall()

        affected: List[Dict[str, Any]] = []
        for row in mapping_rows:
            target = row["target_code"]
            if target in deprecated_codes:
                affected.append({
                    "concept_map_id": row["id"], "source_system": row["source_system"], "source_code": row["source_code"],
                    "target_code": target, "impact_type": IMPACT_BROKEN,
                    "old_title": who_sync._display_title(from_table.get(target)), "new_title": None,
                })
            elif target in retitled_codes:
                affected.append({
                    "concept_map_id": row["id"], "source_system": row["source_system"], "source_code": row["source_code"],
                    "target_code": target, "impact_type": IMPACT_AMBIGUOUS,
                    "old_title": who_sync._display_title(from_table.get(target)),
                    "new_title": who_sync._display_title(to_table.get(target)),
                })

        broken_count = sum(1 for a in affected if a["impact_type"] == IMPACT_BROKEN)
        ambiguous_count = sum(1 for a in affected if a["impact_type"] == IMPACT_AMBIGUOUS)
        risk = _risk_score(broken_count, ambiguous_count, len(mapping_rows))

        run_at = datetime.now(timezone.utc).isoformat()
        cur.execute(
            """INSERT INTO terminology_simulations
                 (from_release, to_release, run_at, run_by, new_count, deprecated_count, retitled_count,
                  broken_mapping_count, ambiguous_mapping_count, from_release_concept_count, to_release_concept_count, risk_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (from_release, to_release, run_at, run_by, len(new_codes), len(deprecated_codes), len(retitled_codes),
             broken_count, ambiguous_count, len(from_codes), len(to_codes), risk),
        )
        sim_id = cur.lastrowid

        cur.executemany(
            """INSERT INTO simulation_affected_mappings
                 (simulation_id, concept_map_id, source_system, source_code, target_code, impact_type, old_title, new_title)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(sim_id, a["concept_map_id"], a["source_system"], a["source_code"], a["target_code"],
              a["impact_type"], a["old_title"], a["new_title"]) for a in affected],
        )
        conn.commit()

        return {
            "id": sim_id,
            "from_release": from_release,
            "to_release": to_release,
            "run_at": run_at,
            "run_by": run_by,
            "new_concepts": len(new_codes),
            "deprecated_concepts": len(deprecated_codes),
            "retitled_concepts": len(retitled_codes),
            "broken_mappings": broken_count,
            "ambiguous_mappings": ambiguous_count,
            "total_mappings_checked": len(mapping_rows),
            "from_release_concept_count": len(from_codes),
            "to_release_concept_count": len(to_codes),
            "risk_score": risk,
            "disclaimer": DISCLAIMER,
        }
    finally:
        conn.close()


def get_simulation(sim_id: int) -> Optional[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM terminology_simulations WHERE id = ?", (sim_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def affected_mappings(sim_id: int, impact_type: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    if impact_type:
        cur.execute(
            "SELECT * FROM simulation_affected_mappings WHERE simulation_id = ? AND impact_type = ? ORDER BY id",
            (sim_id, impact_type),
        )
    else:
        cur.execute("SELECT * FROM simulation_affected_mappings WHERE simulation_id = ? ORDER BY id", (sim_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def escalate_to_review(sim_id: int, actor: str) -> Dict[str, Any]:
    """
    Pushes every affected mapping from this simulation into review_queue as
    a fresh EXPERT_REVIEW item, flagged distinctly (flag_type=
    'terminology_drift') from AI suggestions and the legacy-reclassification
    flag governance.py already uses — a reviewer should be able to tell at a
    glance *why* something is in their queue. Never touches concept_map.
    Idempotent: re-escalating a simulation that already has queue rows
    referenced just returns them rather than duplicating.
    """
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(review_queue)")
        cols = {r[1] for r in cur.fetchall()}
        if "flag_type" not in cols or "concept_map_id" not in cols:
            raise RuntimeError("review_queue schema out of date — run app.governance.ensure_schema() first")

        cur.execute("SELECT * FROM simulation_affected_mappings WHERE simulation_id = ?", (sim_id,))
        rows = cur.fetchall()
        now = datetime.now(timezone.utc).isoformat()
        created_ids = []

        for row in rows:
            if row["review_queue_id"]:
                created_ids.append(row["review_queue_id"])
                continue
            rationale = (
                f"Terminology simulation #{sim_id}: target code {row['target_code']} "
                f"{'no longer exists' if row['impact_type'] == IMPACT_BROKEN else 'was retitled'} "
                f"in the simulated release. "
                + (f"Old: \"{row['old_title']}\" -> New: \"{row['new_title']}\"." if row["new_title"] else f"Was: \"{row['old_title']}\".")
            )
            cur.execute(
                """INSERT INTO review_queue
                     (source_system, source_code, ai_suggested_code, ai_suggested_title, confidence, decision,
                      rationale, status, created_at, flag_type, concept_map_id, target_system)
                   VALUES (?, ?, ?, NULL, NULL, 'EXPERT_REVIEW', ?, 'pending', ?, 'terminology_drift', ?, NULL)""",
                (row["source_system"], row["source_code"], row["target_code"], rationale, now, row["concept_map_id"]),
            )
            rq_id = cur.lastrowid
            cur.execute("UPDATE simulation_affected_mappings SET review_queue_id = ? WHERE id = ?", (rq_id, row["id"]))
            created_ids.append(rq_id)

        cur.execute("UPDATE terminology_simulations SET escalated_at = ? WHERE id = ?", (now, sim_id))
        conn.commit()
        return {"simulation_id": sim_id, "review_queue_ids": created_ids, "count": len(created_ids)}
    finally:
        conn.close()


def available_releases() -> Dict[str, Any]:
    """Delegates to who_sync's credential-free release index — same source the What-If picker uses."""
    return who_sync.discover_releases()


def history(limit: int = 20) -> List[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM terminology_simulations ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
