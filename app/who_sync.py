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

There are **two** WHO sources here, because the obvious one has a barrier:

  * **Release files (default, no credentials).** WHO publishes each ICD-11
    MMS release as a Simple Tabulation file on its own CDN
    (icdcdn.who.int/static/releasefiles/...), with no login, no OAuth and no
    registration. That file is the authoritative published release — in fact
    it is byte-for-byte the format of our own local snapshot. Diffing a
    freshly downloaded release against our snapshot is real synchronisation
    against real WHO data, and it needs nothing but an outbound HTTPS call.
    It also checks *every* mapping target in one pass instead of trickling
    through a rate-limited API.

  * **The ICD-API (optional, needs credentials).** Register a free client at
    https://icd.who.int/icdapi and set ICD_API_CLIENT_ID /
    ICD_API_CLIENT_SECRET to enable per-code live resolution with
    definitions and browser links. Without them this half simply stays off.

Both write the same drift verdicts into the same registry, so the governance
story does not change with the source — only the provenance label does.
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

# WHO's public release-file CDN — no authentication of any kind. This is the
# same file our local snapshot was built from (identical column layout, right
# down to the trailing "Version:..." column).
RELEASE_FILE_BASE = "https://icdcdn.who.int/static/releasefiles"
RELEASE_FILE_NAME = "SimpleTabulation-ICD-11-MMS-en"
RELEASES_INDEX_URL = "https://icd.who.int/browse/releases/mms/en"

REQUEST_TIMEOUT = 8       # seconds — a hung WHO call must not hang a page load
DOWNLOAD_TIMEOUT = 120    # a release file is a few MB; give it room
CACHE_TTL_SECONDS = 7 * 24 * 3600
MAX_SYNC_BATCH = 100      # hard ceiling; WHO is a shared public service

# ── Provenance markers (returned to the client, rendered in the UI) ──────
PROV_WHO_LIVE = "WHO_LIVE"
PROV_WHO_CACHE = "WHO_CACHE"
PROV_LOCAL_SNAPSHOT = "LOCAL_SNAPSHOT"
PROV_WHO_RELEASE_FILE = "WHO_RELEASE_FILE"

# Sync sources
SOURCE_RELEASE_FILE = "release_file"   # default — needs no credentials
SOURCE_API = "api"                     # needs ICD_API_CLIENT_ID/SECRET
VALID_SOURCES = {SOURCE_RELEASE_FILE, SOURCE_API}

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
    cur.execute("PRAGMA table_info(who_sync_log)")
    if "source" not in {r[1] for r in cur.fetchall()}:
        cur.execute(f"ALTER TABLE who_sync_log ADD COLUMN source TEXT DEFAULT '{SOURCE_API}'")

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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS who_release_cache (
            release_id TEXT NOT NULL,
            code TEXT NOT NULL,
            title TEXT,
            class_kind TEXT,
            chapter_no TEXT,
            PRIMARY KEY (release_id, code)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS who_release_meta (
            release_id TEXT PRIMARY KEY,
            version_label TEXT,
            code_count INTEGER,
            source_url TEXT,
            downloaded_at TEXT NOT NULL
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
    """
    Available ICD-11 MMS releases. Prefers WHO's public release index (no
    credentials needed) since that is the source `run_release_sync` actually
    uses; falls back to the authenticated API's release list, then to the
    local snapshot, if that is somehow unreachable too.
    """
    via_files = discover_releases()
    if via_files["provenance"] == PROV_WHO_RELEASE_FILE:
        return via_files

    if not credentials_configured():
        return via_files  # already LOCAL_SNAPSHOT with a degraded_reason set

    try:
        payload = _who_get(f"{API_ROOT}/mms") or {}
    except WhoApiError as e:
        via_files["degraded_reason"] = f"{via_files.get('degraded_reason')}; ICD-API also failed: {e}"
        return via_files

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

        if provenance == PROV_LOCAL_SNAPSHOT and credentials_configured():
            try:
                who = _fetch_from_who(code, release_id)
                provenance = PROV_WHO_LIVE
                _cache_put(cur, code, release_id, who)
                conn.commit()
            except WhoApiError as e:
                degraded_reason = f"{e} — falling back to WHO's public release file."

        if provenance == PROV_LOCAL_SNAPSHOT:
            # No usable ICD-API answer (no credentials, or the API call above
            # failed) — fall back to WHO's credential-free release file. This
            # is still a real WHO source, just without per-code definitions
            # or a browser link.
            try:
                release = fetch_release_table(release_id)
                who_title = release["table"].get(code)
                provenance = PROV_WHO_RELEASE_FILE
                if who_title is not None:
                    who = {"entity_id": None, "title": who_title, "definition": None,
                           "class_kind": None, "browser_url": None, "code": code}
                if not credentials_configured():
                    degraded_reason = (
                        (degraded_reason + " " if degraded_reason else "")
                        + "WHO ICD-API credentials not configured — resolved against WHO's public "
                          "release file instead (no definitions/browser link available via this route). "
                          "Register at https://icd.who.int/icdapi for per-code API detail."
                    )
            except WhoApiError as e:
                degraded_reason = (
                    (degraded_reason + " " if degraded_reason else "")
                    + f"WHO release file also unavailable: {e} — serving the offline snapshot."
                )

        comparison = (
            _compare(local, who)
            if provenance in (PROV_WHO_LIVE, PROV_WHO_CACHE, PROV_WHO_RELEASE_FILE)
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


# ── WHO release files (credential-free source) ───────────────────────────
def release_file_url(release_id: str) -> str:
    return f"{RELEASE_FILE_BASE}/{release_id}/{RELEASE_FILE_NAME}.zip"


def discover_releases() -> Dict[str, Any]:
    """
    Release ids straight off WHO's public release index — no credentials.
    Returns the ids newest-first plus whichever one our snapshot is.
    """
    try:
        resp = requests.get(RELEASES_INDEX_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {
            "provenance": PROV_LOCAL_SNAPSHOT,
            "degraded_reason": f"Could not reach WHO's release index: {e}",
            "releases": [SNAPSHOT_RELEASE],
            "latest": None,
            "snapshot_release": SNAPSHOT_RELEASE,
        }

    ids = sorted({m for m in re.findall(r"20\d{2}-\d{2}", resp.text)}, reverse=True)
    latest = ids[0] if ids else None
    return {
        "provenance": PROV_WHO_RELEASE_FILE,
        "releases": ids,
        "latest": latest,
        "snapshot_release": SNAPSHOT_RELEASE,
        "snapshot_is_latest": (latest == SNAPSHOT_RELEASE) if latest else None,
        "releases_behind": (ids.index(SNAPSHOT_RELEASE) if SNAPSHOT_RELEASE in ids else None),
    }


def _parse_release_tsv(text: str) -> Tuple[List[Tuple[str, str, str, str]], Optional[str]]:
    """
    Parse a Simple Tabulation file into (code, title, class_kind, chapter) rows.

    The layout is identical to our own snapshot's — the final header cell is a
    'Version:...' stamp which we keep as the release's human-readable label.
    Rows without a Code are groupings/blocks, which carry no code to map to.
    """
    import csv as _csv
    import io as _io

    reader = _csv.DictReader(_io.StringIO(text), delimiter="\t")
    version_label = None
    for field in (reader.fieldnames or []):
        if field and field.strip().lower().startswith("version"):
            version_label = field.split(":", 1)[-1].strip()

    rows = []
    for row in reader:
        code = (row.get("Code") or "").strip()
        if not code:
            continue
        rows.append((
            code,
            (row.get("Title") or "").strip(),
            (row.get("ClassKind") or "").strip(),
            (row.get("ChapterNo") or "").strip(),
        ))
    return rows, version_label


def fetch_release_table(release_id: str, force: bool = False) -> Dict[str, Any]:
    """
    Return {code: title} for a WHO release, downloading and caching the
    official release file on first use. Raises WhoApiError on failure so the
    caller can decide how to degrade.
    """
    import io as _io
    import zipfile as _zipfile

    conn = _conn()
    cur = conn.cursor()
    try:
        if not force:
            cur.execute("SELECT * FROM who_release_meta WHERE release_id = ?", (release_id,))
            meta = cur.fetchone()
            if meta:
                cur.execute("SELECT code, title FROM who_release_cache WHERE release_id = ?", (release_id,))
                table = {r["code"]: r["title"] for r in cur.fetchall()}
                if table:
                    return {"table": table, "meta": dict(meta), "downloaded": False}

        url = release_file_url(release_id)
        try:
            resp = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
        except requests.RequestException as e:
            raise WhoApiError(f"Could not download WHO release file {release_id}: {e}")
        if resp.status_code == 404:
            raise WhoApiError(f"WHO publishes no Simple Tabulation file for release {release_id}.")
        if resp.status_code != 200:
            raise WhoApiError(f"WHO release file {release_id} returned HTTP {resp.status_code}.")

        try:
            archive = _zipfile.ZipFile(_io.BytesIO(resp.content))
            # The zip also carries a readme.txt and an .xlsx copy — match
            # the data file by its known stem, not just any ".txt" (readme.txt
            # sorts first in some zips and was silently "parsed" as 0 rows).
            name = next(n for n in archive.namelist() if RELEASE_FILE_NAME in n and n.endswith(".txt"))
            text = archive.read(name).decode("utf-8-sig")
        except (_zipfile.BadZipFile, StopIteration, UnicodeDecodeError) as e:
            raise WhoApiError(f"WHO release file {release_id} could not be read: {e}")

        rows, version_label = _parse_release_tsv(text)
        if not rows:
            raise WhoApiError(f"WHO release file {release_id} contained no coded entities.")

        cur.execute("DELETE FROM who_release_cache WHERE release_id = ?", (release_id,))
        cur.executemany(
            "INSERT OR REPLACE INTO who_release_cache (release_id, code, title, class_kind, chapter_no) VALUES (?, ?, ?, ?, ?)",
            [(release_id, c, t, k, ch) for c, t, k, ch in rows],
        )
        cur.execute(
            """INSERT INTO who_release_meta (release_id, version_label, code_count, source_url, downloaded_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(release_id) DO UPDATE SET
                 version_label=excluded.version_label, code_count=excluded.code_count,
                 source_url=excluded.source_url, downloaded_at=excluded.downloaded_at""",
            (release_id, version_label, len(rows), url, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

        cur.execute("SELECT * FROM who_release_meta WHERE release_id = ?", (release_id,))
        return {"table": {c: t for c, t, _, _ in rows}, "meta": dict(cur.fetchone()), "downloaded": True}
    finally:
        conn.close()


def run_release_sync(release_id: Optional[str] = None, actor: str = "system") -> Dict[str, Any]:
    """
    Diff **every** mapping-target code against a real WHO release file.

    Unlike the API sweep this is a single download plus a local comparison, so
    there is no batching and no rate limit to respect — one run covers the
    whole corpus. Never raises: a failed download is reported as a FAILED run.
    """
    started = time.time()
    run_at = datetime.now(timezone.utc).isoformat()

    if release_id is None:
        discovered = discover_releases()
        release_id = discovered.get("latest") or SNAPSHOT_RELEASE

    conn = _conn()
    cur = conn.cursor()
    try:
        try:
            # A sync run is a deliberate, explicit operator action (not a
            # background poll) — always re-download rather than serving a
            # cached copy of this release, otherwise pressing "Sync with
            # WHO" twice in a row would silently do nothing the second time.
            release = fetch_release_table(release_id, force=True)
        except WhoApiError as e:
            cur.execute(
                """INSERT INTO who_sync_log (run_at, release_id, actor, mode, source, duration_seconds, detail)
                   VALUES (?, ?, ?, 'FAILED', ?, ?, ?)""",
                (run_at, release_id, actor, SOURCE_RELEASE_FILE, round(time.time() - started, 3), str(e)),
            )
            conn.commit()
            return {
                "mode": "FAILED", "source": SOURCE_RELEASE_FILE, "run_at": run_at,
                "release_id": release_id, "codes_checked": 0,
                "confirmed": 0, "drifted": 0, "missing": 0, "errored": 1,
                "results": [], "detail": str(e), "disclaimer": DISCLAIMER,
            }

        who_table = release["table"]

        cur.execute(
            """SELECT DISTINCT cm.target_code AS code, i.title AS local_title
               FROM concept_map cm LEFT JOIN icd11 i ON i.code = cm.target_code
               WHERE TRIM(COALESCE(cm.target_code, '')) != ''
               ORDER BY cm.target_code"""
        )
        targets = cur.fetchall()

        counts = {"confirmed": 0, "drifted": 0, "missing": 0, "errored": 0}
        results: List[Dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for row in targets:
            code, local_title = row["code"], row["local_title"]
            who_title = who_table.get(code)

            if who_title is None:
                status = CMP_NOT_IN_RELEASE
                counts["missing"] += 1
            elif normalize_title(local_title) == normalize_title(who_title):
                status = CMP_CONFIRMED
                counts["confirmed"] += 1
            else:
                status = CMP_TITLE_DRIFT
                counts["drifted"] += 1

            if status == CMP_CONFIRMED:
                cur.execute("DELETE FROM who_drift WHERE code = ? AND release_id = ?", (code, release_id))
            else:
                cur.execute(
                    """INSERT INTO who_drift (code, release_id, drift_type, local_title, who_title, detected_at)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(code, release_id) DO UPDATE SET
                         drift_type=excluded.drift_type, local_title=excluded.local_title,
                         who_title=excluded.who_title, detected_at=excluded.detected_at""",
                    (code, release_id, status, _display_title(local_title),
                     _display_title(who_title) if who_title else None, now_iso),
                )
                results.append({
                    "code": code,
                    "status": status,
                    "local_title": _display_title(local_title),
                    "who_title": _display_title(who_title) if who_title else None,
                })

        duration = round(time.time() - started, 3)
        meta = release["meta"]
        detail = (
            f"Compared all {len(targets)} mapping-target codes against WHO's official "
            f"{release_id} release file ({meta.get('code_count')} coded entities, "
            f"version {meta.get('version_label')}). Snapshot release is {SNAPSHOT_RELEASE}."
        )

        cur.execute(
            """INSERT INTO who_sync_log
                 (run_at, release_id, actor, mode, source, codes_checked, confirmed, drifted, missing, errored, duration_seconds, detail)
               VALUES (?, ?, ?, 'COMPLETED', ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_at, release_id, actor, SOURCE_RELEASE_FILE, len(targets), counts["confirmed"],
             counts["drifted"], counts["missing"], counts["errored"], duration, detail),
        )
        conn.commit()

        return {
            "mode": "COMPLETED",
            "source": SOURCE_RELEASE_FILE,
            "run_at": run_at,
            "release_id": release_id,
            "release_version_label": meta.get("version_label"),
            "release_code_count": meta.get("code_count"),
            "release_source_url": meta.get("source_url"),
            "snapshot_release": SNAPSHOT_RELEASE,
            "codes_checked": len(targets),
            **counts,
            "duration_seconds": duration,
            "results": results,
            "detail": detail,
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


def run_api_sync(limit: int = 25, release_id: Optional[str] = None, actor: str = "system") -> Dict[str, Any]:
    """
    Check a batch of our mapping-target ICD-11 codes against the live WHO
    ICD-API (needs ICD_API_CLIENT_ID/SECRET), record drift, and write a
    sync-log row. Returns a summary; a missing-credentials or unreachable-WHO
    run is reported as mode SKIPPED, not as an error, so the caller can
    render it calmly. See run_release_sync() for the credential-free source.
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
                """INSERT INTO who_sync_log (run_at, release_id, actor, mode, source, codes_checked, duration_seconds, detail)
                   VALUES (?, ?, ?, 'SKIPPED_NO_CREDENTIALS', ?, 0, ?, ?)""",
                (run_at, release_id, actor, SOURCE_API, round(time.time() - started, 3), detail),
            )
            conn.commit()
            return {
                "mode": "SKIPPED_NO_CREDENTIALS",
                "source": SOURCE_API,
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
                 (run_at, release_id, actor, mode, source, codes_checked, confirmed, drifted, missing, errored, duration_seconds, detail)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_at, release_id, actor, mode, SOURCE_API, len(results), counts["confirmed"], counts["drifted"],
             counts["missing"], counts["errored"], duration, detail),
        )
        conn.commit()

        return {
            "mode": mode,
            "source": SOURCE_API,
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
    """
    Live-vs-snapshot posture. Two independent WHO sources are tracked
    separately because they have different reach: the release-file sync
    needs no credentials and checks every mapping target in one pass; the
    ICD-API sync needs registration and checks codes one at a time.
    """
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM who_sync_log ORDER BY id DESC LIMIT 1")
        last = cur.fetchone()
        cur.execute(
            "SELECT * FROM who_sync_log WHERE source = ? AND mode = 'COMPLETED' ORDER BY id DESC LIMIT 1",
            (SOURCE_RELEASE_FILE,),
        )
        last_release_sync = cur.fetchone()
        cur.execute(
            "SELECT * FROM who_sync_log WHERE source = ? ORDER BY id DESC LIMIT 1",
            (SOURCE_API,),
        )
        last_api_sync = cur.fetchone()

        cur.execute("SELECT COUNT(*) AS n FROM who_entity_cache WHERE found = 1")
        api_cached = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM who_drift")
        drift_count = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(DISTINCT target_code) AS n FROM concept_map WHERE TRIM(COALESCE(target_code,'')) != ''")
        total_targets = cur.fetchone()["n"]

        release_checked = last_release_sync["codes_checked"] if last_release_sync else 0
        release_coverage = round(100.0 * release_checked / total_targets, 1) if total_targets else 0.0

        if last_release_sync:
            mode = "LIVE_VERIFIED"       # a real release-file diff has completed at least once
        elif credentials_configured():
            mode = "LIVE_CAPABLE"        # API credentials present, nothing synced yet
        else:
            mode = "SNAPSHOT_ONLY"       # nothing has ever been verified against WHO

        return {
            "credentials_configured": credentials_configured(),
            "snapshot_release": SNAPSHOT_RELEASE,
            "snapshot_label": SNAPSHOT_LABEL,
            "token_endpoint": TOKEN_URL,
            "api_root": API_ROOT,
            "release_file_base": RELEASE_FILE_BASE,
            "registration_url": "https://icd.who.int/icdapi",
            "last_sync": dict(last) if last else None,
            "last_release_sync": dict(last_release_sync) if last_release_sync else None,
            "last_api_sync": dict(last_api_sync) if last_api_sync else None,
            "release_sync_coverage_pct": release_coverage,
            "codes_cached_from_who": api_cached,
            "mapping_target_codes": total_targets,
            "coverage_pct": release_coverage or (round(100.0 * api_cached / total_targets, 1) if total_targets else 0.0),
            "open_drift_items": drift_count,
            "mode": mode,
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
