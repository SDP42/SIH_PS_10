"""
API key platform — the credential system an external EMR vendor actually
integrates against, independent of the clinician-facing ABHA Demo Mode
login in app/auth.py.

Two separate identity systems now exist in this service, on purpose:
  - app/auth.py's demo bearer token answers "which clinician/reviewer is
    acting" for the web UI.
  - This module answers "which external client is calling the API" for
    programmatic integration — an EMR's coding-assist widget, a hospital's
    batch upload job, etc. Neither replaces the other.

Design constraints (see the platform strategy doc, §19):
  1. The plaintext secret is shown exactly once, at creation or rotation.
     Only its SHA-256 hash is ever stored. A short, non-secret prefix is
     stored separately purely so an admin can recognise a key in a list
     without the full secret ever being retrievable again.
  2. Every key carries an explicit scope list; a caller must hold the
     scope an endpoint requires, not just "any valid key."
  3. Rate limiting is per-key, tiered by key type, enforced by counting
     this key's own recent usage rows — no new infrastructure (no Redis),
     consistent with the rest of this service's SQLite-only footprint.
  4. Revocation and rotation are different operations: revocation ends a
     key immediately and permanently; rotation issues a new secret under
     the same client record without a gap, and immediately revokes the
     old one.
  5. The plaintext secret must never reach a log line or an audit_log
     `details` string — every audit call in this module logs the key's
     id/prefix, never the secret.
"""
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

DB_PATH = "db/ayush_icd11_combined.db"

KEY_PREFIX_BY_TYPE = {
    "sandbox": "nsk_sandbox_",
    "readonly": "nsk_readonly_",
    "translation": "nsk_translate_",
    "fhir_integration": "nsk_fhir_",
    "admin": "nsk_admin_",
}

# Each key type's default scope grant. A caller can request a narrower
# custom scope list at creation; these are what a plain "give me a
# <type> key" request receives.
DEFAULT_SCOPES_BY_TYPE: Dict[str, List[str]] = {
    "sandbox": ["search:read", "translate:read"],
    "readonly": ["search:read", "codesystem:read", "validate:read"],
    "translation": ["search:read", "translate:read", "expand:read", "validate:read"],
    "fhir_integration": ["search:read", "translate:read", "expand:read", "validate:read", "bundle:write", "condition:write"],
    "admin": ["search:read", "translate:read", "expand:read", "validate:read", "bundle:write", "condition:write",
              "governance:write", "mapping:write", "sync:write"],
}

# Requests per minute, tiered by type — sandbox tightest, admin loosest.
DEFAULT_RATE_LIMIT_BY_TYPE = {
    "sandbox": 30,
    "readonly": 120,
    "translation": 120,
    "fhir_integration": 240,
    "admin": 600,
}

VALID_KEY_TYPES = set(KEY_PREFIX_BY_TYPE)
ALL_SCOPES = sorted({s for scopes in DEFAULT_SCOPES_BY_TYPE.values() for s in scopes})


class ApiKeyError(RuntimeError):
    """Base for all client-facing API-key failures — callers map these to HTTP codes."""


class InvalidKeyError(ApiKeyError):
    pass


class InsufficientScopeError(ApiKeyError):
    def __init__(self, required: str):
        super().__init__(f"This key does not have the '{required}' scope.")
        self.required = required


class RateLimitedError(ApiKeyError):
    def __init__(self, limit: int):
        super().__init__(f"Rate limit exceeded ({limit} requests/minute for this key).")
        self.limit = limit


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema() -> None:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            organization TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL REFERENCES api_clients(id),
            key_type TEXT NOT NULL,
            key_hash TEXT NOT NULL UNIQUE,
            key_prefix TEXT NOT NULL,
            scopes TEXT NOT NULL,
            rate_limit_per_minute INTEGER NOT NULL,
            label TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            revoked_at TEXT,
            rotated_from_id INTEGER,
            last_used_at TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key_id INTEGER NOT NULL REFERENCES api_keys(id),
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            status_code INTEGER,
            occurred_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_key_time ON api_usage(api_key_id, occurred_at DESC)")
    conn.commit()
    conn.close()


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _generate_secret(key_type: str) -> str:
    prefix = KEY_PREFIX_BY_TYPE[key_type]
    return f"{prefix}{secrets.token_urlsafe(32)}"


def create_client(name: str, organization: Optional[str], created_by: str) -> Dict[str, Any]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO api_clients (name, organization, created_by, created_at, status) VALUES (?, ?, ?, ?, 'active')",
        (name, organization, created_by, datetime.now(timezone.utc).isoformat()),
    )
    client_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"id": client_id, "name": name, "organization": organization, "status": "active"}


def create_key(
    client_id: int,
    key_type: str,
    created_by: str,
    label: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    expires_in_days: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Returns the plaintext secret alongside metadata — the ONE time it will
    ever be available. Callers (the router) must return it to the requester
    and never log it or write it anywhere else.
    """
    if key_type not in VALID_KEY_TYPES:
        raise ValueError(f"Unknown key_type '{key_type}'. Valid: {sorted(VALID_KEY_TYPES)}")

    granted_scopes = scopes if scopes is not None else DEFAULT_SCOPES_BY_TYPE[key_type]
    unknown = set(granted_scopes) - set(ALL_SCOPES)
    if unknown:
        raise ValueError(f"Unknown scope(s): {sorted(unknown)}")

    secret = _generate_secret(key_type)
    key_hash = _hash(secret)
    prefix_shown = secret[: len(KEY_PREFIX_BY_TYPE[key_type]) + 6]  # e.g. "nsk_sandbox_AbC123"
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=expires_in_days)).isoformat() if expires_in_days else None

    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO api_keys
             (client_id, key_type, key_hash, key_prefix, scopes, rate_limit_per_minute,
              label, created_by, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (client_id, key_type, key_hash, prefix_shown, ",".join(granted_scopes),
         DEFAULT_RATE_LIMIT_BY_TYPE[key_type], label, created_by, now.isoformat(), expires_at),
    )
    key_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": key_id,
        "client_id": client_id,
        "key_type": key_type,
        "secret": secret,  # shown once
        "key_prefix": prefix_shown,
        "scopes": granted_scopes,
        "rate_limit_per_minute": DEFAULT_RATE_LIMIT_BY_TYPE[key_type],
        "label": label,
        "expires_at": expires_at,
        "warning": "This is the only time the full secret is shown. Store it now — it cannot be retrieved again.",
    }


def _row_to_key_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    d["scopes"] = d["scopes"].split(",") if d["scopes"] else []
    d.pop("key_hash", None)
    return d


def list_keys(client_id: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    if client_id:
        cur.execute("SELECT * FROM api_keys WHERE client_id = ? ORDER BY id DESC", (client_id,))
    else:
        cur.execute("SELECT * FROM api_keys ORDER BY id DESC")
    rows = [_row_to_key_dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_key(key_id: int) -> Optional[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_key_dict(row) if row else None


def revoke_key(key_id: int) -> Dict[str, Any]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise LookupError(f"No API key with id {key_id}")
    if row["revoked_at"]:
        conn.close()
        return _row_to_key_dict(row)  # already revoked — idempotent

    now = datetime.now(timezone.utc).isoformat()
    cur.execute("UPDATE api_keys SET revoked_at = ? WHERE id = ?", (now, key_id))
    conn.commit()
    cur.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,))
    updated = cur.fetchone()
    conn.close()
    return _row_to_key_dict(updated)


def rotate_key(key_id: int, created_by: str) -> Dict[str, Any]:
    """Revokes the old key and issues a brand new secret + row under the same client, same type/scopes."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,))
    old = cur.fetchone()
    conn.close()
    if not old:
        raise LookupError(f"No API key with id {key_id}")

    revoke_key(key_id)
    new_key = create_key(
        client_id=old["client_id"],
        key_type=old["key_type"],
        created_by=created_by,
        label=old["label"],
        scopes=old["scopes"].split(",") if old["scopes"] else None,
    )
    conn = _conn()
    cur = conn.cursor()
    cur.execute("UPDATE api_keys SET rotated_from_id = ? WHERE id = ?", (key_id, new_key["id"]))
    conn.commit()
    conn.close()
    new_key["rotated_from_id"] = key_id
    return new_key


# ── Runtime verification (called by the FastAPI dependency) ───────────────
def verify_key(secret: str, required_scope: Optional[str] = None) -> Dict[str, Any]:
    """
    Resolves a presented secret to its key record, checking revocation,
    expiry, and (if given) a required scope. Raises InvalidKeyError /
    InsufficientScopeError — never returns a partial/ambiguous result.
    Rate limiting is checked separately by check_rate_limit(), since that
    needs to happen after we know which key this is but the caller may want
    to log the attempt regardless of outcome.
    """
    key_hash = _hash(secret)
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT k.*, c.status AS client_status FROM api_keys k
           JOIN api_clients c ON c.id = k.client_id
           WHERE k.key_hash = ?""",
        (key_hash,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        raise InvalidKeyError("API key not recognised.")
    if row["revoked_at"]:
        raise InvalidKeyError("This API key has been revoked.")
    if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc).isoformat():
        raise InvalidKeyError("This API key has expired.")
    if row["client_status"] != "active":
        raise InvalidKeyError("The client this key belongs to is not active.")

    scopes = row["scopes"].split(",") if row["scopes"] else []
    if required_scope and required_scope not in scopes:
        raise InsufficientScopeError(required_scope)

    return _row_to_key_dict(row)


def check_rate_limit(key_id: int, limit_per_minute: int) -> None:
    conn = _conn()
    cur = conn.cursor()
    one_minute_ago = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    cur.execute(
        "SELECT COUNT(*) AS n FROM api_usage WHERE api_key_id = ? AND occurred_at >= ?",
        (key_id, one_minute_ago),
    )
    count = cur.fetchone()["n"]
    conn.close()
    if count >= limit_per_minute:
        raise RateLimitedError(limit_per_minute)


def record_usage(key_id: int, method: str, path: str, status_code: Optional[int] = None) -> None:
    conn = _conn()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cur.execute(
        "INSERT INTO api_usage (api_key_id, method, path, status_code, occurred_at) VALUES (?, ?, ?, ?, ?)",
        (key_id, method, path, status_code, now),
    )
    cur.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, key_id))
    conn.commit()
    conn.close()


def usage_summary(key_id: int, hours: int = 24) -> Dict[str, Any]:
    conn = _conn()
    cur = conn.cursor()
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    cur.execute(
        "SELECT COUNT(*) AS n FROM api_usage WHERE api_key_id = ? AND occurred_at >= ?",
        (key_id, since),
    )
    total = cur.fetchone()["n"]
    cur.execute(
        """SELECT path, COUNT(*) AS n FROM api_usage
           WHERE api_key_id = ? AND occurred_at >= ?
           GROUP BY path ORDER BY n DESC LIMIT 10""",
        (key_id, since),
    )
    by_path = [dict(r) for r in cur.fetchall()]
    cur.execute(
        "SELECT * FROM api_usage WHERE api_key_id = ? ORDER BY occurred_at DESC LIMIT 20",
        (key_id,),
    )
    recent = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"key_id": key_id, "window_hours": hours, "total_requests": total, "by_path": by_path, "recent": recent}
