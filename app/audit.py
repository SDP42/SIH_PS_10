"""
Real audit trail — replaces the frontend's hardcoded AUDIT_EVENTS array.

Rows are written for every governance decision, every AI-approved mapping,
every Bundle upload, every WHO sync, every API key action, and every
terminology simulation. This is what Overview.tsx's "Gateway Audit &
Activity Timeline" shows instead of four fake, hardcoded log lines.

Tamper-evident hash chain (Phase 3B): each row's `row_hash` is
SHA-256(prev_hash + this row's own content), so a chain of N rows commits
to the entire history — changing any field in any past row, deleting a
row, or reordering rows all break the chain at a specific, identifiable
point. This is a hash chain (the same core idea as a git commit history or
a blockchain's block-linking, applied to one local table), not a
distributed ledger or a cryptographic signature scheme — verify() can
prove "this history has not been altered since it was written," not "this
history was written by an authorized party" (that's what require_demo_auth
on every write path already covers) and not "no two parties disagree about
this history" (there is only one party: this database).

log() keeps its exact original signature and behavior for every existing
caller (governance_router, who_router, apikey_router,
terminology_simulator_router, fhir_extra's Bundle upload) — none of them
need to change for the chain to apply to their writes.
"""
import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

DB_PATH = "db/ayush_icd11_combined.db"

GENESIS_HASH = "0" * 64  # the fixed "previous hash" for the very first row in the chain

router = APIRouter(prefix="/api/audit", tags=["Audit"])


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema():
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            target TEXT,
            details TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC)")

    cur.execute("PRAGMA table_info(audit_log)")
    existing_cols = {row[1] for row in cur.fetchall()}
    if "row_hash" not in existing_cols:
        cur.execute("ALTER TABLE audit_log ADD COLUMN row_hash TEXT")
    if "prev_hash" not in existing_cols:
        cur.execute("ALTER TABLE audit_log ADD COLUMN prev_hash TEXT")
    conn.commit()

    # Backfill any rows written before the chain existed (or before this
    # process's first ensure_schema() call), in id order, exactly once.
    cur.execute("SELECT id, action, actor, target, details, created_at, row_hash FROM audit_log ORDER BY id ASC")
    rows = cur.fetchall()
    prev_hash = GENESIS_HASH
    needs_backfill = any(r["row_hash"] is None for r in rows)
    if needs_backfill:
        for row in rows:
            row_hash = row["row_hash"] or _compute_hash(prev_hash, row["action"], row["actor"], row["target"], row["details"], row["created_at"])
            if row["row_hash"] is None:
                cur.execute("UPDATE audit_log SET row_hash = ?, prev_hash = ? WHERE id = ?", (row_hash, prev_hash, row["id"]))
            prev_hash = row_hash
        conn.commit()

    conn.close()


def _compute_hash(prev_hash: str, action: str, actor: str, target: Optional[str], details: Optional[str], created_at: str) -> str:
    payload = "|".join([prev_hash, action, actor, target or "", details or "", created_at])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _last_hash(cur) -> str:
    cur.execute("SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    return row["row_hash"] if row and row["row_hash"] else GENESIS_HASH


def log(action: str, actor: str, target: Optional[str] = None, details: Optional[str] = None) -> None:
    conn = _conn()
    cur = conn.cursor()
    created_at = datetime.now(timezone.utc).isoformat()
    prev_hash = _last_hash(cur)
    row_hash = _compute_hash(prev_hash, action, actor, target, details, created_at)
    cur.execute(
        "INSERT INTO audit_log (action, actor, target, details, created_at, row_hash, prev_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (action, actor, target, details, created_at, row_hash, prev_hash),
    )
    conn.commit()
    conn.close()


def recent(limit: int = 20) -> List[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def verify_chain() -> Dict[str, Any]:
    """
    Walks the entire chain in insertion order and recomputes every row's
    hash from its stored content. Returns the first point of disagreement,
    if any — which is exactly the row that was altered, deleted (a gap in
    the id sequence with a broken prev_hash link), or inserted out of order.
    """
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_log ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    prev_hash = GENESIS_HASH
    checked = 0
    for row in rows:
        checked += 1
        if row["prev_hash"] != prev_hash:
            return {
                "valid": False,
                "broken_at_id": row["id"],
                "reason": "prev_hash does not match the previous row's stored hash — a row was deleted, reordered, or inserted outside the chain",
                "rows_checked": checked,
                "total_rows": len(rows),
            }
        expected = _compute_hash(prev_hash, row["action"], row["actor"], row["target"], row["details"], row["created_at"])
        if row["row_hash"] != expected:
            return {
                "valid": False,
                "broken_at_id": row["id"],
                "reason": "stored row_hash does not match a hash recomputed from this row's own content — this row's action/actor/target/details/created_at was modified after it was written",
                "rows_checked": checked,
                "total_rows": len(rows),
            }
        prev_hash = row["row_hash"]

    return {"valid": True, "broken_at_id": None, "reason": None, "rows_checked": checked, "total_rows": len(rows)}


@router.get("/recent")
def get_recent(limit: int = Query(20, ge=1, le=100)):
    return {"events": recent(limit)}


@router.get("/verify")
def get_verify():
    """
    Walks the tamper-evident hash chain and reports whether it's intact. A
    real, useful negative result: if any audit_log row is ever edited
    directly in the database (bypassing log()), this endpoint names the
    exact row where the chain breaks.
    """
    return verify_chain()
