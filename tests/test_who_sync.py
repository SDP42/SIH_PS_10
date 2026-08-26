"""
Tests for WHO ICD-11 synchronisation (app/who_sync.py, app/who_router.py).

Two independent WHO sources are covered:

  * The **release-file** path (app/who_sync.run_release_sync /
    discover_releases / fetch_release_table) — no credentials needed, checks
    every mapping target in one pass against a downloaded WHO release file.
    This is the default sync endpoint (POST /api/who/sync).
  * The **ICD-API** path (app/who_sync.run_api_sync / fetch_code's live
    branch) — needs ICD_API_CLIENT_ID/SECRET, resolves codes one at a time
    with definitions and browser links (POST /api/who/sync/api).

Every WHO network call is stubbed here — no test depends on reaching the
real icd.who.int / icdcdn.who.int over the network.
"""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pytest
from fastapi.testclient import TestClient

from app import who_sync
from app.main import app

client = TestClient(app)

_WHO_TABLES = (
    "who_entity_cache", "who_drift", "who_sync_log",
    "who_release_cache", "who_release_meta",
)


@pytest.fixture(autouse=True)
def _clean_who_state():
    """Each test starts from an empty WHO cache/drift/log and no token."""
    who_sync._token_cache.update({"access_token": None, "expires_at": 0.0})
    conn = sqlite3.connect(who_sync.DB_PATH)
    for table in _WHO_TABLES:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
    yield


@pytest.fixture
def no_credentials(monkeypatch):
    for var in ("ICD_API_CLIENT_ID", "ICD_API_CLIENT_SECRET", "WHO_ICD_CLIENT_ID", "WHO_ICD_CLIENT_SECRET"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def with_credentials(monkeypatch):
    monkeypatch.setenv("ICD_API_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("ICD_API_CLIENT_SECRET", "test-client-secret")


@pytest.fixture
def network_down(monkeypatch):
    """Simulate total network unreachability — the deepest degradation."""
    def _boom(*args, **kwargs):
        raise who_sync.requests.RequestException("network down")
    monkeypatch.setattr(who_sync.requests, "get", _boom)
    monkeypatch.setattr(who_sync.requests, "post", _boom)


def _local_target_code():
    """A real mapping-target ICD-11 code that also exists in the snapshot."""
    conn = sqlite3.connect(who_sync.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """SELECT cm.target_code AS code, i.title AS title
           FROM concept_map cm JOIN icd11 i ON i.code = cm.target_code
           LIMIT 1"""
    ).fetchone()
    conn.close()
    return row["code"], row["title"]


def _all_target_codes(n=None):
    conn = sqlite3.connect(who_sync.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT DISTINCT cm.target_code AS code, i.title AS title
           FROM concept_map cm JOIN icd11 i ON i.code = cm.target_code
           ORDER BY cm.target_code"""
    ).fetchall()
    conn.close()
    out = [(r["code"], r["title"]) for r in rows]
    return out[:n] if n else out


# ── Fake WHO transport ────────────────────────────────────────────────────
class _FakeResponse:
    def __init__(self, status_code, payload=None, content=b"", text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.content = content
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise who_sync.requests.HTTPError(f"HTTP {self.status_code}")


def _fake_release_zip(rows, version_label="2099 Jan 01 - 00:00 UTC"):
    """Build a WHO-shaped Simple Tabulation zip: tab-delimited, version stamped
    onto the trailing header cell exactly as WHO's real files do it."""
    header = f"Code\tTitle\tClassKind\tChapterNo\tVersion:{version_label}\n"
    lines = [header] + [f"{code}\t{title}\tcategory\t01\t\n" for code, title in rows]
    text = "".join(lines)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # WHO's real release zip also carries a readme.txt (and an .xlsx copy)
        # alongside the data file — readme.txt sorts first, which is exactly
        # what caught a real bug (naive ".txt" matching grabbed the readme).
        zf.writestr("readme.txt", "This file describes the columns below.\n")
        zf.writestr(f"{who_sync.RELEASE_FILE_NAME}.txt", text.encode("utf-8-sig"))
        zf.writestr(f"{who_sync.RELEASE_FILE_NAME}.xlsx", b"not a real xlsx, just a placeholder")
    return buf.getvalue()


def _install_fake_release_file(monkeypatch, rows, version_label="2099 Jan 01 - 00:00 UTC", status_code=200):
    """Stub requests.get for a release-file download, for any release id."""
    zip_bytes = _fake_release_zip(rows, version_label) if status_code == 200 else b""

    def fake_get(url, **kwargs):
        assert url.startswith(who_sync.RELEASE_FILE_BASE)
        return _FakeResponse(status_code, content=zip_bytes)

    monkeypatch.setattr(who_sync.requests, "get", fake_get)


def _install_fake_release_index(monkeypatch, release_ids):
    text = " ".join(release_ids) + " some other text 1999-99 not-a-release"

    def fake_get(url, **kwargs):
        assert url == who_sync.RELEASES_INDEX_URL
        return _FakeResponse(200, text=text)

    monkeypatch.setattr(who_sync.requests, "get", fake_get)


def _install_fake_who_api(monkeypatch, entity_title_for):
    """
    Stub the ICD-API path: token endpoint + two-step codeinfo -> stem-entity
    resolution. `entity_title_for(code)` returns the WHO title, or None for 404.
    """
    calls = {"token": 0, "get": []}

    def fake_post(url, **kwargs):
        calls["token"] += 1
        assert url == who_sync.TOKEN_URL
        assert kwargs["data"]["grant_type"] == "client_credentials"
        assert kwargs["data"]["scope"] == who_sync.TOKEN_SCOPE
        return _FakeResponse(200, {"access_token": "fake-token", "expires_in": 3600})

    def fake_get(url, **kwargs):
        calls["get"].append(url)
        assert kwargs["headers"]["API-Version"] == "v2"
        assert kwargs["headers"]["Authorization"] == "Bearer fake-token"
        assert url.startswith("https://"), "WHO's http:// URIs must be upgraded to https"

        if "/codeinfo/" in url:
            code = url.rsplit("/codeinfo/", 1)[1]
            if entity_title_for(code) is None:
                return _FakeResponse(404)
            return _FakeResponse(200, {
                "stemId": f"http://id.who.int/icd/release/11/{who_sync.SNAPSHOT_RELEASE}/mms/{abs(hash(code)) % 10**9}",
                "code": code,
            })

        prior = [u for u in calls["get"] if "/codeinfo/" in u]
        code = prior[-1].rsplit("/codeinfo/", 1)[1]
        return _FakeResponse(200, {
            "title": {"@language": "en", "@value": entity_title_for(code)},
            "definition": {"@language": "en", "@value": "Stub definition."},
            "classKind": "category",
            "browserUrl": f"https://icd.who.int/browse/2025-01/mms/{code}",
            "code": code,
        })

    monkeypatch.setattr(who_sync.requests, "post", fake_post)
    monkeypatch.setattr(who_sync.requests, "get", fake_get)
    return calls


# ── Title normalisation ──────────────────────────────────────────────────
def test_normalize_strips_csv_depth_prefix():
    """
    ICD-11.csv encodes tree depth as a literal '- - - ' title prefix. Without
    stripping it, every code would be reported as drifted.
    """
    assert who_sync.normalize_title("- - - Cholera") == who_sync.normalize_title("Cholera")
    assert who_sync.normalize_title("  Cholera.  ") == "cholera"
    assert who_sync.normalize_title(None) == ""


# ── Release-file source (default, credential-free) ───────────────────────
def test_release_sync_requires_auth():
    assert client.post("/api/who/sync", json={}).status_code == 401


def test_release_sync_works_without_any_who_credentials(no_credentials, demo_auth_headers, monkeypatch):
    """The whole point of this source: zero credentials, real WHO data."""
    targets = _all_target_codes(3)
    _install_fake_release_file(monkeypatch, [(c, t) for c, t in targets])

    resp = client.post("/api/who/sync", json={"release": "2026-01"}, headers=demo_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "COMPLETED"
    assert body["source"] == who_sync.SOURCE_RELEASE_FILE
    assert body["codes_checked"] == len(_all_target_codes())
    assert body["confirmed"] == len(targets)


def test_release_sync_detects_drift_and_missing_codes(no_credentials, demo_auth_headers, monkeypatch):
    code_a, title_a = _local_target_code()
    all_targets = _all_target_codes()
    # WHO retitles code_a and drops the rest entirely from this release.
    rows = [(code_a, "A Completely Different WHO Title")]
    _install_fake_release_file(monkeypatch, rows)

    body = client.post("/api/who/sync", json={"release": "2026-01"}, headers=demo_auth_headers).json()
    assert body["confirmed"] == 0
    assert body["drifted"] == 1
    assert body["missing"] == len(all_targets) - 1

    drift = {d["code"]: d for d in client.get("/api/who/drift").json()["items"]}
    assert drift[code_a]["drift_type"] == who_sync.CMP_TITLE_DRIFT
    assert drift[code_a]["who_title"] == "A Completely Different WHO Title"

    events = client.get("/api/audit/recent").json()["events"]
    assert any(e["action"] == "WHO_SYNC_COMPLETED" for e in events)


def test_release_sync_clears_drift_once_titles_agree_again(no_credentials, demo_auth_headers, monkeypatch):
    code_a, title_a = _local_target_code()
    _install_fake_release_file(monkeypatch, [(code_a, "Stale Title")])
    client.post("/api/who/sync", json={"release": "2026-01"}, headers=demo_auth_headers)
    assert len(client.get("/api/who/drift").json()["items"]) >= 1

    _install_fake_release_file(monkeypatch, [(code_a, who_sync._display_title(title_a))])
    body = client.post("/api/who/sync", json={"release": "2026-01"}, headers=demo_auth_headers).json()
    assert body["confirmed"] >= 1
    assert code_a not in {d["code"] for d in client.get("/api/who/drift").json()["items"]}


def test_release_sync_reports_failure_without_crashing(no_credentials, demo_auth_headers, monkeypatch):
    _install_fake_release_file(monkeypatch, [], status_code=404)
    resp = client.post("/api/who/sync", json={"release": "1999-01"}, headers=demo_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "FAILED"
    assert body["errored"] == 1

    runs = client.get("/api/who/history").json()["runs"]
    assert runs[0]["mode"] == "FAILED"
    assert runs[0]["source"] == who_sync.SOURCE_RELEASE_FILE


def test_release_file_is_cached_across_calls(no_credentials, monkeypatch):
    """A second sync against the same release must not re-download the file."""
    targets = _all_target_codes(2)
    calls = {"n": 0}

    def fake_get(url, **kwargs):
        calls["n"] += 1
        return _FakeResponse(200, content=_fake_release_zip(targets))

    monkeypatch.setattr(who_sync.requests, "get", fake_get)

    who_sync.fetch_release_table("2026-01")
    who_sync.fetch_release_table("2026-01")
    assert calls["n"] == 1, "second call must be served from who_release_cache"

    who_sync.fetch_release_table("2026-01", force=True)
    assert calls["n"] == 2, "force=True must bypass the cache"


def test_discover_releases_lists_ids_newest_first(no_credentials):
    def fake_get(url, **kwargs):
        assert url == who_sync.RELEASES_INDEX_URL
        return _FakeResponse(200, text="2018-06 2019-04 2025-01 2026-01")
    import unittest.mock as mock
    with mock.patch.object(who_sync.requests, "get", fake_get):
        body = who_sync.discover_releases()
    assert body["provenance"] == who_sync.PROV_WHO_RELEASE_FILE
    assert body["releases"] == ["2026-01", "2025-01", "2019-04", "2018-06"]
    assert body["snapshot_is_latest"] is False


def test_releases_endpoint_degrades_when_index_unreachable(network_down):
    body = client.get("/api/who/releases").json()
    assert body["provenance"] == who_sync.PROV_LOCAL_SNAPSHOT
    assert body["latest"] is None
    assert "degraded_reason" in body


# ── Single-code lookup fallback order ─────────────────────────────────────
def test_code_lookup_uses_release_file_without_credentials(no_credentials, monkeypatch):
    """
    No ICD-API credentials at all — GET /api/who/code must still resolve
    against WHO's public release file rather than dropping straight to the
    offline snapshot.
    """
    code, title = _local_target_code()
    _install_fake_release_file(monkeypatch, [(code, who_sync._display_title(title))])

    body = client.get(f"/api/who/code/{code}").json()
    assert body["provenance"] == who_sync.PROV_WHO_RELEASE_FILE
    assert body["comparison"]["status"] == who_sync.CMP_CONFIRMED
    assert body["who"]["browser_url"] is None  # release file carries no browser link


def test_code_lookup_falls_back_to_snapshot_when_network_is_down(no_credentials, network_down):
    code, _ = _local_target_code()
    body = client.get(f"/api/who/code/{code}").json()
    assert body["provenance"] == who_sync.PROV_LOCAL_SNAPSHOT
    assert body["local"]["code"] == code
    assert body["who"] is None
    assert body["degraded_reason"]


def test_code_lookup_never_500s_when_who_is_unreachable(with_credentials, network_down):
    """A dead network must degrade all the way to the snapshot, never 500."""
    code, _ = _local_target_code()
    resp = client.get(f"/api/who/code/{code}")
    assert resp.status_code == 200
    assert resp.json()["provenance"] == who_sync.PROV_LOCAL_SNAPSHOT


def test_code_lookup_prefers_api_over_release_file_when_credentials_present(with_credentials, monkeypatch):
    code, title = _local_target_code()
    calls = _install_fake_who_api(monkeypatch, lambda c: who_sync._display_title(title))

    body = client.get(f"/api/who/code/{code}").json()
    assert body["provenance"] == who_sync.PROV_WHO_LIVE
    assert body["who"]["browser_url"] is not None
    assert not any(who_sync.RELEASE_FILE_BASE in u for u in calls["get"])


def test_missing_code_via_release_file_is_reported_not_invented(no_credentials, monkeypatch):
    code, _ = _local_target_code()
    _install_fake_release_file(monkeypatch, [("ZZZZ", "A decoy code, not ours")])  # release has ours missing

    body = client.get(f"/api/who/code/{code}").json()
    assert body["who"] is None
    assert body["comparison"]["status"] == who_sync.CMP_NOT_IN_RELEASE
    assert body["local"] is not None, "snapshot data is still returned alongside the WHO verdict"


# ── ICD-API source (needs credentials) ────────────────────────────────────
def test_api_sync_requires_auth():
    assert client.post("/api/who/sync/api", json={"limit": 2}).status_code == 401


def test_api_sync_without_credentials_is_skipped_not_an_error(no_credentials, demo_auth_headers):
    resp = client.post("/api/who/sync/api", json={"limit": 2}, headers=demo_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "SKIPPED_NO_CREDENTIALS"
    assert body["codes_checked"] == 0
    assert client.get("/api/who/history").json()["runs"][0]["mode"] == "SKIPPED_NO_CREDENTIALS"


def test_api_sync_batch_size_is_capped(demo_auth_headers):
    resp = client.post(
        "/api/who/sync/api",
        json={"limit": who_sync.MAX_SYNC_BATCH + 1},
        headers=demo_auth_headers,
    )
    assert resp.status_code == 422


def test_api_sync_run_records_drift_and_audit(with_credentials, demo_auth_headers, monkeypatch):
    _install_fake_who_api(monkeypatch, lambda c: f"WHO Retitled {c}")

    body = client.post("/api/who/sync/api", json={"limit": 3}, headers=demo_auth_headers).json()
    assert body["mode"] == "COMPLETED"
    assert body["source"] == who_sync.SOURCE_API
    assert body["codes_checked"] == 3
    assert body["drifted"] + body["missing"] == 3

    events = client.get("/api/audit/recent").json()["events"]
    assert any(e["action"].startswith("WHO_SYNC_") for e in events)


def test_api_sync_stops_on_transport_failure_instead_of_hammering_who(with_credentials, demo_auth_headers, monkeypatch):
    def fake_post(url, **kwargs):
        return _FakeResponse(200, {"access_token": "fake-token", "expires_in": 3600})

    gets = {"n": 0}

    def fake_get(url, **kwargs):
        gets["n"] += 1
        raise who_sync.requests.RequestException("connection reset")

    monkeypatch.setattr(who_sync.requests, "post", fake_post)
    monkeypatch.setattr(who_sync.requests, "get", fake_get)

    body = client.post("/api/who/sync/api", json={"limit": 20}, headers=demo_auth_headers).json()
    assert body["mode"] == "PARTIAL"
    assert body["errored"] == 1
    assert gets["n"] == 1, "batch must abort after the first transport failure"


def test_api_sync_repeated_runs_sweep_new_codes(with_credentials, demo_auth_headers, monkeypatch):
    """Consecutive runs advance least-recently-checked-first, not the same head batch."""
    _install_fake_who_api(monkeypatch, lambda c: f"WHO Title {c}")

    first = client.post("/api/who/sync/api", json={"limit": 3}, headers=demo_auth_headers).json()
    second = client.post("/api/who/sync/api", json={"limit": 3}, headers=demo_auth_headers).json()

    first_codes = {r["code"] for r in first["results"]}
    second_codes = {r["code"] for r in second["results"]}
    assert first_codes and second_codes
    assert first_codes.isdisjoint(second_codes)


# ── Overall status ─────────────────────────────────────────────────────
def test_status_is_snapshot_only_before_any_sync(no_credentials):
    body = client.get("/api/who/status").json()
    assert body["mode"] == "SNAPSHOT_ONLY"
    assert body["credentials_configured"] is False
    assert body["mapping_target_codes"] > 0


def test_status_is_live_verified_after_a_completed_release_sync(no_credentials, demo_auth_headers, monkeypatch):
    targets = _all_target_codes(2)
    _install_fake_release_file(monkeypatch, targets)
    client.post("/api/who/sync", json={"release": "2026-01"}, headers=demo_auth_headers)

    body = client.get("/api/who/status").json()
    assert body["mode"] == "LIVE_VERIFIED"
    assert body["last_release_sync"]["mode"] == "COMPLETED"
    assert body["release_sync_coverage_pct"] > 0


def test_status_is_live_capable_with_credentials_but_no_sync_yet(with_credentials):
    body = client.get("/api/who/status").json()
    assert body["mode"] == "LIVE_CAPABLE"
    assert body["credentials_configured"] is True
