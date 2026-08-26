"""
Terminology governance & interoperability analytics.

This is the screen built for a Ministry-of-AYUSH-style oversight view:
corpus size and mapping coverage per tradition, review-queue throughput,
confidence-tier distribution, WHO synchronisation posture, and real audit
activity over time.

Every number here is computed from tables this service actually writes to
(nam/nsm/num/ast, concept_map, review_queue, audit_log, who_sync_log) —
there is no encounter-volume, patient-count, or usage-trend panel, because
no encounter/patient data is ever persisted anywhere in this codebase. A
dashboard that invented that number to look more impressive would break the
project's own "real vs demo-mode" honesty posture; leaving it out is the
honest choice; if patient-level EMR usage is wired in later, add it here as
its own clearly-sourced panel rather than backfilling a plausible-looking
number now.
"""
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List

from app import ai_mapping, who_sync

DB_PATH = "db/ayush_icd11_combined.db"

# Tradition metadata — the only place that maps the internal system code to
# a human label, so the dashboard and any future consumer stay in sync.
TRADITIONS = [
    {"system": "NAM", "table": "nam", "label": "Ayurveda", "code_column": "namc_code"},
    {"system": "NSM", "table": "nsm", "label": "Siddha", "code_column": "namc_code"},
    {"system": "NUM", "table": "num", "label": "Unani", "code_column": "numc_code"},
    {"system": "AST", "table": "ast", "label": "Ayurveda Standard Terminology", "code_column": "code"},
]


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _corpus_and_coverage() -> List[Dict[str, Any]]:
    """
    Per-tradition corpus size (raw table rows) and mapping coverage (from the
    AI engine's indexed pool, which is the same pool /api/ai/unmapped uses —
    so this dashboard's numbers and that page's numbers can never disagree).
    """
    conn = _conn()
    cur = conn.cursor()
    out = []
    ai_available = ai_mapping.is_ready()
    for t in TRADITIONS:
        cur.execute(f"SELECT COUNT(*) AS n FROM {t['table']}")
        raw_total = cur.fetchone()["n"]

        indexed_total = unmapped = None
        if ai_available:
            try:
                unmapped = ai_mapping.list_unmapped(page=1, page_size=1, source_system=t["system"])["total_unmapped"]
            except ai_mapping.EngineNotReadyError:
                ai_available = False

        out.append({
            "system": t["system"],
            "label": t["label"],
            "corpus_size": raw_total,
            "unmapped": unmapped,
            "mapped": (raw_total - unmapped) if unmapped is not None else None,
            "coverage_pct": round(100.0 * (raw_total - unmapped) / raw_total, 1) if unmapped is not None and raw_total else None,
        })
    conn.close()
    return out


def _mapping_registry() -> Dict[str, Any]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM concept_map")
    total = cur.fetchone()["n"]
    cur.execute("SELECT equivalence, COUNT(*) AS n FROM concept_map GROUP BY equivalence")
    by_equivalence = {r["equivalence"]: r["n"] for r in cur.fetchall()}
    cur.execute("SELECT COALESCE(source, 'rule_v1') AS source, COUNT(*) AS n FROM concept_map GROUP BY 1")
    by_source = {r["source"]: r["n"] for r in cur.fetchall()}
    cur.execute("""
        SELECT
          CASE WHEN i.chapterno = '26' THEN 'ICD-11 TM2' ELSE 'ICD-11 Biomedicine' END AS target_kind,
          COUNT(*) AS n
        FROM concept_map cm LEFT JOIN icd11 i ON i.code = cm.target_code
        GROUP BY 1
    """)
    by_target_kind = {r["target_kind"]: r["n"] for r in cur.fetchall()}
    conn.close()
    return {
        "total_mappings": total,
        "equivalent": by_equivalence.get("equivalent", 0),
        "related": by_equivalence.get("relatedto", 0),
        "curated_rule_based": by_source.get("rule_v1", 0),
        "ai_reviewed": by_source.get("ai_reviewed_v1", 0),
        "target_tm2": by_target_kind.get("ICD-11 TM2", 0),
        "target_biomedicine": by_target_kind.get("ICD-11 Biomedicine", 0),
    }


def _review_queue_throughput() -> Dict[str, Any]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) AS n FROM review_queue GROUP BY status")
    by_status = {r["status"]: r["n"] for r in cur.fetchall()}
    cur.execute("SELECT decision, COUNT(*) AS n FROM review_queue GROUP BY decision")
    by_decision = {r["decision"]: r["n"] for r in cur.fetchall()}
    cur.execute("SELECT flag_type, COUNT(*) AS n FROM review_queue GROUP BY COALESCE(flag_type, 'ai_suggestion')")
    by_flag = {r["flag_type"] or "ai_suggestion": r["n"] for r in cur.fetchall()}
    cur.execute("""
        SELECT ROUND(AVG(
          (JULIANDAY(reviewed_at) - JULIANDAY(created_at)) * 24
        ), 2) AS avg_hours
        FROM review_queue WHERE reviewed_at IS NOT NULL
    """)
    avg_hours = cur.fetchone()["avg_hours"]
    conn.close()
    return {
        "pending": by_status.get("pending", 0),
        "approved": by_status.get("approved", 0),
        "rejected": by_status.get("rejected", 0),
        "needs_info": by_status.get("needs_info", 0),
        "by_decision_tier": by_decision,
        "ai_suggestions": by_flag.get("ai_suggestion", 0),
        "legacy_reclassifications": by_flag.get("legacy_reclassification", 0),
        "avg_review_turnaround_hours": avg_hours,
    }


def _audit_activity(days: int = 30) -> List[Dict[str, Any]]:
    """Real audit-log volume per day, for a governance activity chart."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DATE(created_at) AS day, COUNT(*) AS n
        FROM audit_log
        WHERE created_at >= DATETIME('now', ?)
        GROUP BY DATE(created_at)
        ORDER BY day ASC
    """, (f"-{int(days)} days",))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _audit_action_breakdown(limit: int = 12) -> List[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT action, COUNT(*) AS n FROM audit_log GROUP BY action ORDER BY n DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def overview() -> Dict[str, Any]:
    who_status = who_sync.status()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "traditions": _corpus_and_coverage(),
        "mapping_registry": _mapping_registry(),
        "review_queue": _review_queue_throughput(),
        "who_sync": {
            "mode": who_status["mode"],
            "snapshot_release": who_status["snapshot_release"],
            "open_drift_items": who_status["open_drift_items"],
            "release_sync_coverage_pct": who_status["release_sync_coverage_pct"],
            "last_release_sync": who_status["last_release_sync"],
        },
        "audit_activity": _audit_activity(30),
        "audit_action_breakdown": _audit_action_breakdown(12),
        "data_honesty_note": (
            "Every figure on this page is computed live from this service's own tables "
            "(nam/nsm/num/ast, concept_map, review_queue, audit_log, who_sync_log). There is "
            "no patient or encounter volume shown anywhere on this page — none is persisted "
            "by this service, and a plausible-looking number here would not be real data."
        ),
    }
