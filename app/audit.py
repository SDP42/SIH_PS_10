"""
Real audit trail — replaces the frontend's hardcoded AUDIT_EVENTS array.

Rows are written for every governance decision, every AI-approved mapping,
and every Bundle upload. This is what Overview.tsx's "Gateway Audit &
Activity Timeline" should show instead of four fake, hardcoded log lines.
"""
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

DB_PATH = "db/ayush_icd11_combined.db"

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
    conn.commit()
    conn.close()


def log(action: str, actor: str, target: Optional[str] = None, details: Optional[str] = None) -> None:
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audit_log (action, actor, target, details, created_at) VALUES (?, ?, ?, ?, ?)",
        (action, actor, target, details, datetime.now(timezone.utc).isoformat()),
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


@router.get("/recent")
def get_recent(limit: int = Query(20, ge=1, le=100)):
    return {"events": recent(limit)}
