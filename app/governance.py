"""
Human-in-the-loop governance review queue.

NEEDS_CONTEXT / EXPERT_REVIEW AI suggestions (see app/ai_mapping.py) get
auto-enqueued here for a human reviewer. Approving an item writes a **new**
row into the existing concept_map table (never mutates an existing row) so
an approved AI suggestion becomes a first-class curated mapping — the same
table the original 468 rule-based mappings live in, distinguished by a
`source` column stamped "ai_reviewed_v1" vs "rule_v1" for the originals.
"""
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

DB_PATH = "db/ayush_icd11_combined.db"

VALID_STATUSES = {"pending", "approved", "rejected", "needs_info"}


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema():
    """
    Idempotent, safe-to-rerun migration: creates review_queue if missing, and
    adds version/source columns to concept_map if they don't already exist.
    Never drops or alters existing data.
    """
    conn = _conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS review_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_system TEXT NOT NULL,
            source_code TEXT NOT NULL,
            ai_suggested_code TEXT,
            ai_suggested_title TEXT,
            confidence REAL,
            decision TEXT NOT NULL,
            rationale TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            reviewer_note TEXT,
            reviewed_at TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(source_code, status)")

    cur.execute("PRAGMA table_info(concept_map)")
    existing_cols = {row[1] for row in cur.fetchall()}
    if "version" not in existing_cols:
        cur.execute("ALTER TABLE concept_map ADD COLUMN version TEXT DEFAULT 'v1'")
    if "source" not in existing_cols:
        cur.execute("ALTER TABLE concept_map ADD COLUMN source TEXT DEFAULT 'rule_v1'")

    conn.commit()
    conn.close()


def enqueue_from_suggestion(suggestion: Dict[str, Any]) -> Optional[int]:
    """Insert a review-queue row for a NEEDS_CONTEXT/EXPERT_REVIEW AI suggestion, deduped on pending source_code."""
    if suggestion["decision"] not in ("NEEDS_CONTEXT", "EXPERT_REVIEW"):
        return None

    conn = _conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM review_queue WHERE source_code = ? AND status = 'pending'",
        (suggestion["namaste_code"],),
    )
    existing = cur.fetchone()
    if existing:
        conn.close()
        return existing["id"]

    top = suggestion["candidates"][0] if suggestion["candidates"] else None
    cur.execute(
        """
        INSERT INTO review_queue
            (source_system, source_code, ai_suggested_code, ai_suggested_title, confidence, decision, rationale, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """,
        (
            suggestion["source_system"],
            suggestion["namaste_code"],
            top["icd11_code"] if top else None,
            top["icd11_title"] if top else None,
            top["similarity"] if top else None,
            suggestion["decision"],
            suggestion.get("rationale"),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_queue(status: Optional[str] = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    conn = _conn()
    cur = conn.cursor()

    where = "WHERE status = ?" if status else ""
    params = [status] if status else []

    cur.execute(f"SELECT COUNT(*) FROM review_queue {where}", params)
    total = cur.fetchone()[0]

    cur.execute(
        f"SELECT * FROM review_queue {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [page_size, (page - 1) * page_size],
    )
    items = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {"total": total, "page": page, "page_size": page_size, "items": items}


def decide(item_id: int, status: str, note: Optional[str] = None) -> Dict[str, Any]:
    if status not in VALID_STATUSES or status == "pending":
        raise ValueError(f"Invalid decision status: {status}")

    conn = _conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM review_queue WHERE id = ?", (item_id,))
    item = cur.fetchone()
    if not item:
        conn.close()
        raise LookupError(f"Review queue item {item_id} not found")

    reviewed_at = datetime.now(timezone.utc).isoformat()
    cur.execute(
        "UPDATE review_queue SET status = ?, reviewer_note = ?, reviewed_at = ? WHERE id = ?",
        (status, note, reviewed_at, item_id),
    )

    new_mapping_id = None
    if status == "approved" and item["ai_suggested_code"]:
        equivalence = "equivalent" if item["decision"] == "AUTO_SUGGEST" else "relatedto"
        normalized_source = re.sub(r"\s+", " ", item["source_code"]).strip()

        cur.execute(
            "SELECT id FROM concept_map WHERE source_code = ? AND target_code = ? AND equivalence = ?",
            (normalized_source, item["ai_suggested_code"], equivalence),
        )
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO concept_map (source_system, source_code, target_system, target_code, equivalence, version, source)
                VALUES (?, ?, 'ICD-11 TM2', ?, ?, 'v1', 'ai_reviewed_v1')
                """,
                (item["source_system"], normalized_source, item["ai_suggested_code"], equivalence),
            )
            new_mapping_id = cur.lastrowid

    conn.commit()

    cur.execute("SELECT * FROM review_queue WHERE id = ?", (item_id,))
    result = dict(cur.fetchone())
    conn.close()

    result["new_concept_mapping_id"] = new_mapping_id
    return result
