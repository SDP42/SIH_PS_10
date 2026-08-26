"""
Tests for WHO ICD-11 API synchronisation (app/who_sync.py, app/who_router.py).

Two halves:
  * The **degraded** paths, which must hold up with no credentials and no
    network — this is what protects the live demo.
  * The **live** path, exercised against a stubbed WHO ICD-API so token
    handling, two-step codeinfo→entity resolution and drift detection are
    genuinely covered without depending on WHO being reachable from CI.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pytest
from fastapi.testclient import TestClient

from app import who_sync
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_who_state():
    """Each test starts from an empty WHO cache/drift/log and no token."""
    who_sync._token_cache.update({"access_token": None, "expires_at": 0.0})
    conn = sqlite3.connect(who_sync.DB_PATH)
    for table in ("who_entity_cache", "who_drift", "who_sync_log"):
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


# ── Title normalisation ──────────────────────────────────────────────────
def test_normalize_strips_csv_depth_prefix():
    """
    ICD-11.csv encodes tree depth as a literal '- - - ' title prefix. Without
    stripping it, every code would be reported as drifted.
    """
    assert who_sync.normalize_title("- - - Cholera") == who_sync.normalize_title("Cholera")
    assert who_sync.normalize_title("  Cholera.  ") == "cholera"
    assert who_sync.normalize_title(None) == ""


# ── Degraded (no credentials) behaviour ──────────────────────────────────
def test_status_reports_snapshot_only_without_credentials(no_credentials):
    body = client.get("/api/who/status").json()
    assert body["credentials_configured"] is False
    assert body["mode"] == "SNAPSHOT_ONLY"
    assert body["snapshot_release"] == who_sync.SNAPSHOT_RELEASE
    assert body["mapping_target_codes"] > 0


def test_code_lookup_falls_back_to_snapshot_without_credentials(no_credentials):
    code, _ = _local_target_code()
    body = client.get(f"/api/who/code/{code}").json()
    assert body["provenance"] == who_sync.PROV_LOCAL_SNAPSHOT
    assert body["local"]["code"] == code
    assert body["who"] is None
    assert "credentials not configured" in body["degraded_reason"]


def test_code_lookup_never_500s_when_who_is_unreachable(with_credentials, monkeypatch):
    """A dead network must degrade to the snapshot, not fail the request."""
    def _boom(*args, **kwargs):
        raise who_sync.requests.RequestException("network down")
    monkeypatch.setattr(who_sync.requests, "post", _boom)
    monkeypatch.setattr(who_sync.requests, "get", _boom)

    code, _ = _local_target_code()
    resp = client.get(f"/api/who/code/{code}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provenance"] == who_sync.PROV_LOCAL_SNAPSHOT
    assert "unreachable" in body["degraded_reason"] or "token endpoint" in body["degraded_reason"]


def test_sync_requires_auth(no_credentials):
    assert client.post("/api/who/sync", json={"limit": 2}).status_code == 401


def test_sync_without_credentials_is_skipped_not_an_error(no_credentials, demo_auth_headers):
    resp = client.post("/api/who/sync", json={"limit": 2}, headers=demo_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "SKIPPED_NO_CREDENTIALS"
    assert body["codes_checked"] == 0
    # The skipped run is still logged — "we tried and WHO was unavailable" is
    # itself an auditable fact.
    assert client.get("/api/who/history").json()["runs"][0]["mode"] == "SKIPPED_NO_CREDENTIALS"


# ── Live path against a stubbed WHO ICD-API ──────────────────────────────
class _FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


def _install_fake_who(monkeypatch, entity_title_for):
    """
    Stub WHO: token endpoint + the two-step codeinfo → stem-entity resolution.
    `entity_title_for(code)` returns the WHO title, or None for a 404.
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

        # Stem-entity fetch — recover the code from the pending codeinfo call.
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


def test_live_lookup_confirms_matching_title(with_credentials, monkeypatch):
    code, local_title = _local_target_code()
    _install_fake_who(monkeypatch, lambda c: who_sync._display_title(local_title))

    body = client.get(f"/api/who/code/{code}").json()
    assert body["provenance"] == who_sync.PROV_WHO_LIVE
    assert body["comparison"]["status"] == who_sync.CMP_CONFIRMED
    assert body["who"]["browser_url"].startswith("https://icd.who.int/")


def test_live_lookup_detects_title_drift(with_credentials, monkeypatch):
    code, _ = _local_target_code()
    _install_fake_who(monkeypatch, lambda c: "Completely Different WHO Title")

    body = client.get(f"/api/who/code/{code}").json()
    assert body["comparison"]["status"] == who_sync.CMP_TITLE_DRIFT
    assert body["comparison"]["who_title"] == "Completely Different WHO Title"


def test_second_lookup_is_served_from_cache(with_credentials, monkeypatch):
    code, local_title = _local_target_code()
    calls = _install_fake_who(monkeypatch, lambda c: who_sync._display_title(local_title))

    assert client.get(f"/api/who/code/{code}").json()["provenance"] == who_sync.PROV_WHO_LIVE
    gets_after_first = len(calls["get"])

    second = client.get(f"/api/who/code/{code}").json()
    assert second["provenance"] == who_sync.PROV_WHO_CACHE
    assert len(calls["get"]) == gets_after_first, "cache hit must not call WHO again"
    assert second["comparison"]["status"] == who_sync.CMP_CONFIRMED


def test_force_bypasses_cache(with_credentials, monkeypatch):
    code, local_title = _local_target_code()
    calls = _install_fake_who(monkeypatch, lambda c: who_sync._display_title(local_title))

    client.get(f"/api/who/code/{code}")
    gets_after_first = len(calls["get"])
    body = client.get(f"/api/who/code/{code}", params={"force": True}).json()
    assert body["provenance"] == who_sync.PROV_WHO_LIVE
    assert len(calls["get"]) > gets_after_first


def test_missing_code_is_reported_not_invented(with_credentials, monkeypatch):
    code, _ = _local_target_code()
    _install_fake_who(monkeypatch, lambda c: None)  # WHO 404s everything

    body = client.get(f"/api/who/code/{code}").json()
    assert body["who"] is None
    assert body["comparison"]["status"] == who_sync.CMP_NOT_IN_RELEASE
    assert body["local"] is not None, "snapshot data is still returned alongside the WHO verdict"


def test_sync_run_records_drift_and_audit(with_credentials, demo_auth_headers, monkeypatch):
    _install_fake_who(monkeypatch, lambda c: f"WHO Retitled {c}")

    body = client.post("/api/who/sync", json={"limit": 3}, headers=demo_auth_headers).json()
    assert body["mode"] == "COMPLETED"
    assert body["codes_checked"] == 3
    assert body["drifted"] + body["missing"] == 3

    drift = client.get("/api/who/drift").json()["items"]
    assert len(drift) == 3
    assert all(d["drift_type"] == who_sync.CMP_TITLE_DRIFT for d in drift)

    events = client.get("/api/audit/recent").json()["events"]
    assert any(e["action"].startswith("WHO_SYNC_") for e in events)

    status = client.get("/api/who/status").json()
    assert status["open_drift_items"] == 3
    assert status["codes_cached_from_who"] == 3


def test_sync_clears_drift_once_titles_agree(with_credentials, demo_auth_headers, monkeypatch):
    """A code that drifted and then matches again must leave the drift registry."""
    _install_fake_who(monkeypatch, lambda c: "Stale WHO Title")
    client.post("/api/who/sync", json={"limit": 2}, headers=demo_auth_headers)
    assert len(client.get("/api/who/drift").json()["items"]) == 2

    conn = sqlite3.connect(who_sync.DB_PATH)
    conn.row_factory = sqlite3.Row
    titles = {
        r["code"]: who_sync._display_title(r["title"])
        for r in conn.execute(
            "SELECT i.code, i.title FROM icd11 i JOIN who_drift d ON d.code = i.code"
        ).fetchall()
    }
    # run_sync sweeps least-recently-checked codes first, so a plain re-run
    # would move on to the *next* two codes. Drop these two from the cache to
    # put them back at the head of the queue, i.e. simulate the sweep coming
    # back around to them on a later pass.
    conn.execute("DELETE FROM who_entity_cache")
    conn.commit()
    conn.close()

    _install_fake_who(monkeypatch, lambda c: titles.get(c, "Stale WHO Title"))
    body = client.post("/api/who/sync", json={"limit": 2}, headers=demo_auth_headers).json()
    assert body["confirmed"] == 2
    assert client.get("/api/who/drift").json()["items"] == []


def test_repeated_syncs_sweep_new_codes(with_credentials, demo_auth_headers, monkeypatch):
    """
    Consecutive runs must advance through the corpus (least-recently-checked
    first) rather than re-checking the same head batch forever.
    """
    _install_fake_who(monkeypatch, lambda c: f"WHO Title {c}")

    first = client.post("/api/who/sync", json={"limit": 3}, headers=demo_auth_headers).json()
    second = client.post("/api/who/sync", json={"limit": 3}, headers=demo_auth_headers).json()

    first_codes = {r["code"] for r in first["results"]}
    second_codes = {r["code"] for r in second["results"]}
    assert first_codes and second_codes
    assert first_codes.isdisjoint(second_codes)


def test_sync_stops_on_transport_failure_instead_of_hammering_who(with_credentials, demo_auth_headers, monkeypatch):
    def fake_post(url, **kwargs):
        return _FakeResponse(200, {"access_token": "fake-token", "expires_in": 3600})

    gets = {"n": 0}

    def fake_get(url, **kwargs):
        gets["n"] += 1
        raise who_sync.requests.RequestException("connection reset")

    monkeypatch.setattr(who_sync.requests, "post", fake_post)
    monkeypatch.setattr(who_sync.requests, "get", fake_get)

    body = client.post("/api/who/sync", json={"limit": 20}, headers=demo_auth_headers).json()
    assert body["mode"] == "PARTIAL"
    assert body["errored"] == 1
    assert gets["n"] == 1, "batch must abort after the first transport failure"


def test_sync_batch_size_is_capped(demo_auth_headers):
    resp = client.post(
        "/api/who/sync",
        json={"limit": who_sync.MAX_SYNC_BATCH + 1},
        headers=demo_auth_headers,
    )
    assert resp.status_code == 422


def test_releases_degrades_without_credentials(no_credentials):
    body = client.get("/api/who/releases").json()
    assert body["provenance"] == who_sync.PROV_LOCAL_SNAPSHOT
    assert body["latest"] is None


def test_releases_lists_who_releases(with_credentials, monkeypatch):
    def fake_post(url, **kwargs):
        return _FakeResponse(200, {"access_token": "fake-token", "expires_in": 3600})

    def fake_get(url, **kwargs):
        return _FakeResponse(200, {
            "releaseId": "2025-01",
            "release": [
                "http://id.who.int/icd/release/11/2025-01/mms",
                "http://id.who.int/icd/release/11/2024-01/mms",
                "http://id.who.int/icd/release/11/2023-01/mms",
            ],
        })

    monkeypatch.setattr(who_sync.requests, "post", fake_post)
    monkeypatch.setattr(who_sync.requests, "get", fake_get)

    body = client.get("/api/who/releases").json()
    assert body["provenance"] == who_sync.PROV_WHO_LIVE
    assert body["releases"] == ["2025-01", "2024-01", "2023-01"]
    assert body["snapshot_is_latest"] is True
