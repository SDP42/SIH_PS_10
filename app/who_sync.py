"""
WHO ICD-11 API synchronisation.

The problem statement asks for ICD-11 TM2 integration "via the WHO ICD-API",
not against a frozen spreadsheet. Everything else in this service reads the
`icd11` table, which is a **static snapshot** of WHO's MMS linearization
(data/ICD-11.csv, version column `version_2025_jan_24_-_22_30_utc`). This
module is the live half: it authenticates against WHO's OAuth 2.0 token
service, resolves codes through the real ICD-API, caches what it learns, and
reports **drift** — codes whose WHO title no longer matches our snapshot, or
that have disappeared from the requested release entirely.

Design constraints this module is built around:

1. **It must never take the demo down.** WHO credentials may be absent, the
   venue Wi-Fi may be gone, WHO may rate-limit. Every public function
   degrades to the local snapshot and reports *why* in a `provenance` field
   instead of raising. There is no code path here that can 500 the app
   because the network is unavailable.

2. **Provenance is always explicit.** A caller can always tell whether an
   answer came from WHO right now (`WHO_LIVE`), from our cache of a previous
   WHO call (`WHO_CACHE`), or from the offline snapshot (`LOCAL_SNAPSHOT`).
   We never present snapshot data as if it were live.

3. **No new runtime dependencies.** `requests` is already required. Nothing
   here loads a model or allocates a large array — the service's memory
   profile is unchanged.

Credentials: register a free client at https://icd.who.int/icdapi and set
ICD_API_CLIENT_ID / ICD_API_CLIENT_SECRET. Without them this module still
runs, in snapshot-only mode.
"""
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

DB_PATH = "db/ayush_icd11_combined.db"

# ── WHO ICD-API endpoints (API version 2) ────────────────────────────────
TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
TOKEN_SCOPE = "icdapi_access"
API_ROOT = "https://id.who.int/icd/release/11"

# The release our static CSV snapshot was taken from. Used as the default
# comparison target so drift is measured against a known baseline rather
# than a moving one.
SNAPSHOT_RELEASE = "2025-01"
SNAPSHOT_LABEL = "2025-01-24 22:30 UTC (data/ICD-11.csv)"

REQUEST_TIMEOUT = 8       # seconds — a hung WHO call must not hang a page load
CACHE_TTL_SECONDS = 7 * 24 * 3600
MAX_SYNC_BATCH = 100      # hard ceiling; WHO is a shared public service

# ── Provenance markers (returned to the client, rendered in the UI) ──────
PROV_WHO_LIVE = "WHO_LIVE"
PROV_WHO_CACHE = "WHO_CACHE"
PROV_LOCAL_SNAPSHOT = "LOCAL_SNAPSHOT"

# ── Comparison verdicts ──────────────────────────────────────────────────
CMP_CONFIRMED = "CONFIRMED"                  # WHO title matches our snapshot
CMP_TITLE_DRIFT = "TITLE_DRIFT"              # WHO has retitled this code
CMP_NOT_IN_RELEASE = "NOT_IN_WHO_RELEASE"    # code absent from that release
CMP_LOCAL_ONLY = "LOCAL_ONLY"                # we hold it, WHO not consulted
CMP_FETCH_ERROR = "FETCH_ERROR"              # transport/auth failure

DISCLAIMER = (
    "Drift is a string comparison between WHO's live title for a code and the "
    "title in our static ICD-11 snapshot. It flags terminology changes for a "
    "human to review; it never rewrites a mapping automatically."
)


class WhoApiError(RuntimeError):
    """Any failure reaching or authenticating against the WHO ICD-API."""


# ── Schema ───────────────────────────────────────────────────────────────
def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema() -> None:
    """Idempotent, additive migration — mirrors app/governance.py's approach."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS who_entity_cache (
            code TEXT NOT NULL,
            release_id TEXT NOT NULL,
            entity_id TEXT,
            title TEXT,
            definition TEXT,
            class_kind TEXT,
            browser_url TEXT,
            found INTEGER NOT NULL DEFAULT 1,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (code, release_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS who_sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT NOT NULL,
            release_id TEXT NOT NULL,
            actor TEXT,
            mode TEXT NOT NULL,
            codes_checked INTEGER NOT NULL DEFAULT 0,
            confirmed INTEGER NOT NULL DEFAULT 0,
            drifted INTEGER NOT NULL DEFAULT 0,
            missing INTEGER NOT NULL DEFAULT 0,
            errored INTEGER NOT NULL DEFAULT 0,
            duration_seconds REAL,
            detail TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS who_drift (
            code TEXT NOT NULL,
            release_id TEXT NOT NULL,
            drift_type TEXT NOT NULL,
            local_title TEXT,
            who_title TEXT,
            detected_at TEXT NOT NULL,
            PRIMARY KEY (code, release_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_who_sync_log_run ON who_sync_log(run_at DESC)")
    conn.commit()
    conn.close()


# ── Credentials & token handling ─────────────────────────────────────────
_token_cache: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def _credentials() -> Tuple[Optional[str], Optional[str]]:
    client_id = os.environ.get("ICD_API_CLIENT_ID") or os.environ.get("WHO_ICD_CLIENT_ID")
    client_secret = os.environ.get("ICD_API_CLIENT_SECRET") or os.environ.get("WHO_ICD_CLIENT_SECRET")
    return client_id, client_secret


def credentials_configured() -> bool:
    client_id, client_secret = _credentials()
    return bool(client_id and client_secret)


def _get_token(force: bool = False) -> str:
    """
    OAuth 2.0 client-credentials grant against WHO's token service. Tokens are
    cached in-process until 60s before expiry — WHO issues hour-long tokens and
    re-minting one per request would be abusive.
    """
    now = time.time()
    if not force and _token_cache["access_token"] and _token_cache["expires_at"] > now:
        return _token_cache["access_token"]

    client_id, client_secret = _credentials()
    if not (client_id and client_secret):
        raise WhoApiError(
            "WHO ICD-API credentials not configured. Register free at "
            "https://icd.who.int/icdapi and set ICD_API_CLIENT_ID / ICD_API_CLIENT_SECRET."
        )

    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": TOKEN_SCOPE,
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        raise WhoApiError(f"Could not reach WHO token endpoint: {e}")

    if resp.status_code != 200:
        raise WhoApiError(f"WHO token request rejected (HTTP {resp.status_code}) — check client id/secret.")

    payload = resp.json()
    token = payload.get("access_token")
    if not token:
        raise WhoApiError("WHO token response contained no access_token.")

    _token_cache["access_token"] = token
    _token_cache["expires_at"] = now + max(int(payload.get("expires_in", 3600)) - 60, 60)
    return token


def _who_get(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    GET an ICD-API resource. Returns None for a clean 404 (code genuinely not
    in that release) and raises WhoApiError for anything else, so callers can
    distinguish "WHO says no" from "we couldn't ask".
    """
    # WHO's own URIs are minted as http://id.who.int/... — always call https.
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]

    headers = {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/json",
        "Accept-Language": "en",
        "API-Version": "v2",
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        raise WhoApiError(f"WHO ICD-API unreachable: {e}")

    if resp.status_code == 404:
        return None
    if resp.status_code == 401:
        # Token may have been revoked mid-session; retry once with a fresh one.
        headers["Authorization"] = f"Bearer {_get_token(force=True)}"
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            raise WhoApiError(f"WHO ICD-API unreachable after token refresh: {e}")
        if resp.status_code == 404:
            return None
    if resp.status_code != 200:
        raise WhoApiError(f"WHO ICD-API returned HTTP {resp.status_code} for {url}")

    try:
        return resp.json()
    except ValueError as e:
        raise WhoApiError(f"WHO ICD-API returned non-JSON payload: {e}")


# ── Title normalisation ──────────────────────────────────────────────────
# ICD-11 CSV rows carry their tree depth as a literal "- - - " prefix on the
# title (see data/ICD-11.csv). WHO's API returns the bare title, so drift
# comparison has to strip that presentation artifact or every single code
# would look like it drifted.
_DEPTH_PREFIX = re.compile(r"^(?:\s*-\s*)+")


def normalize_title(title: Optional[str]) -> str:
    if not title:
        return ""
    text = _DEPTH_PREFIX.sub("", title)
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    return text.casefold()


def _display_title(title: Optional[str]) -> str:
    """Snapshot title with the depth prefix stripped, but original casing kept."""
    if not title:
        return ""
    return re.sub(r"\s+", " ", _DEPTH_PREFIX.sub("", title)).strip()


def _extract_label(node: Any) -> Optional[str]:
    """ICD-API returns labels as {'@language': 'en', '@value': '...'}."""
    if isinstance(node, dict):
        return node.get("@value")
    if isinstance(node, str):
        return node
    return None


# ── Local snapshot access ────────────────────────────────────────────────
def _local_concept(cur, code: str) -> Optional[Dict[str, Any]]:
    cur.execute(
        "SELECT code, title, classkind, chapterno, browserlink FROM icd11 WHERE code = ? LIMIT 1",
        (code,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "code": row["code"],
        "title": _display_title(row["title"]),
        "raw_title": row["title"],
        "class_kind": row["classkind"],
        "chapter": row["chapterno"],
        "snapshot_release": SNAPSHOT_RELEASE,
    }


# ── Cache access ─────────────────────────────────────────────────────────
def _cache_get(cur, code: str, release_id: str, max_age_seconds: int = CACHE_TTL_SECONDS) -> Optional[Dict[str, Any]]:
    cur.execute(
        "SELECT * FROM who_entity_cache WHERE code = ? AND release_id = ?",
        (code, release_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(row["fetched_at"])).total_seconds()
    except (TypeError, ValueError):
        return None
    if age > max_age_seconds:
        return None
    return dict(row)


def _cache_put(cur, code: str, release_id: str, entity: Optional[Dict[str, Any]]) -> None:
    cur.execute(
        """
        INSERT INTO who_entity_cache
            (code, release_id, entity_id, title, definition, class_kind, browser_url, found, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code, release_id) DO UPDATE SET
            entity_id=excluded.entity_id, title=excluded.title, definition=excluded.definition,
            class_kind=excluded.class_kind, browser_url=excluded.browser_url,
            found=excluded.found, fetched_at=excluded.fetched_at
        """,
        (
            code,
            release_id,
            (entity or {}).get("entity_id"),
            (entity or {}).get("title"),
            (entity or {}).get("definition"),
            (entity or {}).get("class_kind"),
            (entity or {}).get("browser_url"),
            1 if entity else 0,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


# ── WHO lookups ──────────────────────────────────────────────────────────
def list_releases() -> Dict[str, Any]:
    """Available ICD-11 MMS releases straight from WHO, or a degraded report."""
    if not credentials_configured():
        return {
            "provenance": PROV_LOCAL_SNAPSHOT,
            "degraded_reason": "WHO ICD-API credentials not configured.",
            "snapshot_release": SNAPSHOT_RELEASE,
            "releases": [SNAPSHOT_RELEASE],
            "latest": None,
        }
    try:
        payload = _who_get(f"{API_ROOT}/mms") or {}
    except WhoApiError as e:
        return {
            "provenance": PROV_LOCAL_SNAPSHOT,
            "degraded_reason": str(e),
            "snapshot_release": SNAPSHOT_RELEASE,
            "releases": [SNAPSHOT_RELEASE],
            "latest": None,
        }

    releases = [uri.rstrip("/").rsplit("/", 2)[-2] if uri.rstrip("/").endswith("/mms") else uri.rstrip("/").rsplit("/", 1)[-1]
                for uri in payload.get("release", [])]
    releases = [r for r in releases if re.fullmatch(r"\d{4}-\d{2}", r)]
    latest = payload.get("releaseId") or (releases[0] if releases else None)
    return {
        "provenance": PROV_WHO_LIVE,
        "snapshot_release": SNAPSHOT_RELEASE,
        "releases": releases,
        "latest": latest,
        "snapshot_is_latest": latest == SNAPSHOT_RELEASE if latest else None,
    }


def _fetch_from_who(code: str, release_id: str) -> Optional[Dict[str, Any]]:
    """
    Two-step ICD-API resolution: `codeinfo/{code}` gives the stem entity URI
    for a linearization code, then that URI carries the actual title and
    definition. Returns None when WHO does not have the code in that release.
    """
    info = _who_get(f"{API_ROOT}/{release_id}/mms/codeinfo/{code}")
    if not info:
        return None
    stem_id = info.get("stemId")
    if not stem_id:
        return None

    entity = _who_get(stem_id)
    if not entity:
        return None

    return {
        "entity_id": stem_id.rstrip("/").rsplit("/", 1)[-1],
        "entity_uri": stem_id,
        "title": _extract_label(entity.get("title")),
        "definition": _extract_label(entity.get("definition")),
        "class_kind": entity.get("classKind"),
        "browser_url": entity.get("browserUrl"),
        "code": entity.get("code") or code,
    }


def _compare(local: Optional[Dict[str, Any]], who: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if who is None:
        return {
            "status": CMP_NOT_IN_RELEASE,
            "message": "WHO does not list this code in the requested release.",
        }
    if local is None:
        return {
            "status": CMP_LOCAL_ONLY,
            "message": "Code exists at WHO but is absent from our local snapshot.",
        }
    if normalize_title(local["raw_title"]) == normalize_title(who.get("title")):
        return {"status": CMP_CONFIRMED, "message": "WHO title matches the local snapshot."}
    return {
        "status": CMP_TITLE_DRIFT,
        "message": "WHO has a different title for this code than our snapshot.",
        "local_title": local["title"],
        "who_title": who.get("title"),
    }


def fetch_code(code: str, release_id: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
    """
    Resolve one ICD-11 code with explicit provenance. Never raises for network
    or credential problems — it downgrades to cache, then to snapshot, and
    says so in `provenance` / `degraded_reason`.
    """
    release_id = release_id or SNAPSHOT_RELEASE
    code = code.strip()
    conn = _conn()
    cur = conn.cursor()
    try:
        local = _local_concept(cur, code)
        who: Optional[Dict[str, Any]] = None
        provenance = PROV_LOCAL_SNAPSHOT
        degraded_reason: Optional[str] = None

        if not force:
            cached = _cache_get(cur, code, release_id)
            if cached:
                provenance = PROV_WHO_CACHE
                who = {
                    "entity_id": cached["entity_id"],
                    "title": cached["title"],
                    "definition": cached["definition"],
                    "class_kind": cached["class_kind"],
                    "browser_url": cached["browser_url"],
                    "code": code,
                } if cached["found"] else None

        if provenance == PROV_LOCAL_SNAPSHOT:
            if not credentials_configured():
                degraded_reason = (
                    "WHO ICD-API credentials not configured — serving the offline snapshot. "
                    "Register at https://icd.who.int/icdapi and set ICD_API_CLIENT_ID / ICD_API_CLIENT_SECRET."
                )
            else:
                try:
                    who = _fetch_from_who(code, release_id)
                    provenance = PROV_WHO_LIVE
                    _cache_put(cur, code, release_id, who)
                    conn.commit()
                except WhoApiError as e:
                    degraded_reason = f"{e} — serving the offline snapshot instead."

        comparison = (
            _compare(local, who)
            if provenance in (PROV_WHO_LIVE, PROV_WHO_CACHE)
            else {"status": CMP_LOCAL_ONLY, "message": "WHO was not consulted for this lookup."}
        )

        return {
            "code": code,
            "release_id": release_id,
            "provenance": provenance,
            "degraded_reason": degraded_reason,
            "who": who,
            "local": local,
            "comparison": comparison,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": DISCLAIMER,
        }
    finally:
        conn.close()


# ── Sync run ─────────────────────────────────────────────────────────────
def _codes_to_sync(cur, limit: int) -> List[str]:
    """
    Sync the ICD-11 codes we actually depend on — the mapping targets — oldest
    cache entries first, so repeated runs sweep the whole set rather than
    re-checking the same head every time.
    """
    cur.execute(
        """
        SELECT DISTINCT cm.target_code AS code
        FROM concept_map cm
        LEFT JOIN who_entity_cache c ON c.code = cm.target_code
        WHERE cm.target_code IS NOT NULL AND TRIM(cm.target_code) != ''
        ORDER BY COALESCE(c.fetched_at, '0000') ASC, cm.target_code ASC
        LIMIT ?
        """,
        (limit,),
    )
    return [r["code"] for r in cur.fetchall()]


def run_sync(limit: int = 25, release_id: Optional[str] = None, actor: str = "system") -> Dict[str, Any]:
    """
    Check a batch of our mapping-target ICD-11 codes against the live WHO
    release, record drift, and write a sync-log row. Returns a summary; a
    missing-credentials or unreachable-WHO run is reported as mode SKIPPED,
    not as an error, so the caller can render it calmly.
    """
    release_id = release_id or SNAPSHOT_RELEASE
    limit = max(1, min(int(limit), MAX_SYNC_BATCH))
    started = time.time()
    run_at = datetime.now(timezone.utc).isoformat()

    conn = _conn()
    cur = conn.cursor()
    try:
        if not credentials_configured():
            detail = (
                "WHO ICD-API credentials not configured — no live call attempted. "
                "The service continues to serve the offline ICD-11 snapshot."
            )
            cur.execute(
                """INSERT INTO who_sync_log (run_at, release_id, actor, mode, codes_checked, duration_seconds, detail)
                   VALUES (?, ?, ?, 'SKIPPED_NO_CREDENTIALS', 0, ?, ?)""",
                (run_at, release_id, actor, round(time.time() - started, 3), detail),
            )
            conn.commit()
            return {
                "mode": "SKIPPED_NO_CREDENTIALS",
                "run_at": run_at,
                "release_id": release_id,
                "codes_checked": 0,
                "confirmed": 0, "drifted": 0, "missing": 0, "errored": 0,
                "results": [],
                "detail": detail,
                "disclaimer": DISCLAIMER,
            }

        codes = _codes_to_sync(cur, limit)
        results: List[Dict[str, Any]] = []
        counts = {"confirmed": 0, "drifted": 0, "missing": 0, "errored": 0}
        fatal: Optional[str] = None

        for code in codes:
            local = _local_concept(cur, code)
            try:
                who = _fetch_from_who(code, release_id)
                _cache_put(cur, code, release_id, who)
            except WhoApiError as e:
                # One transport failure means the rest of the batch will fail
                # the same way — stop rather than hammering WHO 24 more times.
                fatal = str(e)
                counts["errored"] += 1
                results.append({"code": code, "status": CMP_FETCH_ERROR, "message": str(e)})
                break

            verdict = _compare(local, who)
            status = verdict["status"]
            if status == CMP_CONFIRMED:
                counts["confirmed"] += 1
                cur.execute("DELETE FROM who_drift WHERE code = ? AND release_id = ?", (code, release_id))
            elif status == CMP_TITLE_DRIFT:
                counts["drifted"] += 1
                cur.execute(
                    """INSERT INTO who_drift (code, release_id, drift_type, local_title, who_title, detected_at)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(code, release_id) DO UPDATE SET
                         drift_type=excluded.drift_type, local_title=excluded.local_title,
                         who_title=excluded.who_title, detected_at=excluded.detected_at""",
                    (code, release_id, status, (local or {}).get("title"), who.get("title"),
                     datetime.now(timezone.utc).isoformat()),
                )
            elif status == CMP_NOT_IN_RELEASE:
                counts["missing"] += 1
                cur.execute(
                    """INSERT INTO who_drift (code, release_id, drift_type, local_title, who_title, detected_at)
                       VALUES (?, ?, ?, ?, NULL, ?)
                       ON CONFLICT(code, release_id) DO UPDATE SET
                         drift_type=excluded.drift_type, local_title=excluded.local_title,
                         who_title=NULL, detected_at=excluded.detected_at""",
                    (code, release_id, status, (local or {}).get("title"),
                     datetime.now(timezone.utc).isoformat()),
                )

            results.append({
                "code": code,
                "status": status,
                "local_title": (local or {}).get("title"),
                "who_title": (who or {}).get("title"),
                "browser_url": (who or {}).get("browser_url"),
            })

        duration = round(time.time() - started, 3)
        mode = "PARTIAL" if fatal else "COMPLETED"
        detail = fatal or f"Checked {len(results)} mapping-target codes against WHO release {release_id}."

        cur.execute(
            """INSERT INTO who_sync_log
                 (run_at, release_id, actor, mode, codes_checked, confirmed, drifted, missing, errored, duration_seconds, detail)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_at, release_id, actor, mode, len(results), counts["confirmed"], counts["drifted"],
             counts["missing"], counts["errored"], duration, detail),
        )
        conn.commit()

        return {
            "mode": mode,
            "run_at": run_at,
            "release_id": release_id,
            "codes_checked": len(results),
            **counts,
            "duration_seconds": duration,
            "results": results,
            "detail": detail,
            "disclaimer": DISCLAIMER,
        }
    finally:
        conn.close()


# ── Read models for the dashboard ────────────────────────────────────────
def status() -> Dict[str, Any]:
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM who_sync_log ORDER BY id DESC LIMIT 1")
        last = cur.fetchone()
        cur.execute("SELECT COUNT(*) AS n FROM who_entity_cache WHERE found = 1")
        cached = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM who_drift")
        drift_count = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(DISTINCT target_code) AS n FROM concept_map WHERE TRIM(COALESCE(target_code,'')) != ''")
        total_targets = cur.fetchone()["n"]

        return {
            "credentials_configured": credentials_configured(),
            "snapshot_release": SNAPSHOT_RELEASE,
            "snapshot_label": SNAPSHOT_LABEL,
            "token_endpoint": TOKEN_URL,
            "api_root": API_ROOT,
            "registration_url": "https://icd.who.int/icdapi",
            "last_sync": dict(last) if last else None,
            "codes_cached_from_who": cached,
            "mapping_target_codes": total_targets,
            "coverage_pct": round(100.0 * cached / total_targets, 1) if total_targets else 0.0,
            "open_drift_items": drift_count,
            "mode": "LIVE_CAPABLE" if credentials_configured() else "SNAPSHOT_ONLY",
            "disclaimer": DISCLAIMER,
        }
    finally:
        conn.close()


def drift_items(limit: int = 100) -> List[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM who_drift ORDER BY detected_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def history(limit: int = 20) -> List[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM who_sync_log ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
