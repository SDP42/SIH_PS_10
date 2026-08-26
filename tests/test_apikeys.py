"""
Tests for the API key / developer platform (app/apikeys.py,
app/apikey_router.py, app/apikey_auth.py) and the versioned public surface
it gates (app/v1_router.py).

Core properties under test: the plaintext secret is shown exactly once and
never recoverable afterward, scopes are actually enforced per-endpoint,
rate limits are actually enforced, and revoke/rotate behave correctly.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pytest
from fastapi.testclient import TestClient

from app import apikeys
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_apikey_state():
    conn = sqlite3.connect(apikeys.DB_PATH)
    for table in ("api_usage", "api_keys", "api_clients"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
    yield


def _make_client_and_key(key_type="sandbox", **kwargs):
    c = apikeys.create_client("Test EMR", "Test Org", created_by="pytest")
    key = apikeys.create_key(client_id=c["id"], key_type=key_type, created_by="pytest", **kwargs)
    return c, key


# ── Core module behaviour ─────────────────────────────────────────────────
def test_secret_is_never_recoverable_after_creation():
    _, key = _make_client_and_key()
    listed = apikeys.list_keys()
    assert "secret" not in listed[0]
    assert "key_hash" not in listed[0]
    assert listed[0]["key_prefix"] in key["secret"]


def test_verify_key_resolves_a_valid_secret():
    _, key = _make_client_and_key()
    resolved = apikeys.verify_key(key["secret"])
    assert resolved["id"] == key["id"]


def test_verify_key_rejects_garbage():
    with pytest.raises(apikeys.InvalidKeyError):
        apikeys.verify_key("nsk_sandbox_not_a_real_secret")


def test_verify_key_enforces_scope():
    _, key = _make_client_and_key(key_type="sandbox")  # no validate:read by default
    with pytest.raises(apikeys.InsufficientScopeError):
        apikeys.verify_key(key["secret"], required_scope="validate:read")
    # but its own granted scope passes
    apikeys.verify_key(key["secret"], required_scope="search:read")


def test_revoke_is_idempotent_and_blocks_future_use():
    _, key = _make_client_and_key()
    apikeys.revoke_key(key["id"])
    apikeys.revoke_key(key["id"])  # second call must not raise
    with pytest.raises(apikeys.InvalidKeyError):
        apikeys.verify_key(key["secret"])


def test_rotate_invalidates_old_secret_and_issues_a_new_one():
    _, key = _make_client_and_key()
    new_key = apikeys.rotate_key(key["id"], created_by="pytest")
    assert new_key["secret"] != key["secret"]
    assert new_key["rotated_from_id"] == key["id"]
    with pytest.raises(apikeys.InvalidKeyError):
        apikeys.verify_key(key["secret"])
    apikeys.verify_key(new_key["secret"])  # new one works


def test_rate_limit_enforced_per_key():
    _, key = _make_client_and_key(key_type="sandbox")  # 30/min
    for _ in range(30):
        apikeys.check_rate_limit(key["id"], 30)
        apikeys.record_usage(key["id"], "GET", "/api/v1/terminology/search")
    with pytest.raises(apikeys.RateLimitedError):
        apikeys.check_rate_limit(key["id"], 30)


def test_expired_key_is_rejected():
    _, key = _make_client_and_key(expires_in_days=1)
    conn = sqlite3.connect(apikeys.DB_PATH)
    conn.execute("UPDATE api_keys SET expires_at = '2000-01-01T00:00:00+00:00' WHERE id = ?", (key["id"],))
    conn.commit()
    conn.close()
    with pytest.raises(apikeys.InvalidKeyError):
        apikeys.verify_key(key["secret"])


def test_revoking_client_blocks_all_its_keys():
    c, key = _make_client_and_key()
    conn = sqlite3.connect(apikeys.DB_PATH)
    conn.execute("UPDATE api_clients SET status = 'suspended' WHERE id = ?", (c["id"],))
    conn.commit()
    conn.close()
    with pytest.raises(apikeys.InvalidKeyError):
        apikeys.verify_key(key["secret"])


# ── HTTP surface ───────────────────────────────────────────────────────────
def test_management_endpoints_require_demo_auth():
    assert client.post("/api/v1/api-keys/clients", json={"name": "x"}).status_code == 401
    assert client.post("/api/v1/api-keys", json={"client_id": 1, "key_type": "sandbox"}).status_code == 401
    assert client.get("/api/v1/api-keys").status_code == 401


def test_full_create_list_rotate_revoke_flow(demo_auth_headers):
    c = client.post("/api/v1/api-keys/clients", json={"name": "Apollo EMR"}, headers=demo_auth_headers).json()
    key = client.post(
        "/api/v1/api-keys", json={"client_id": c["id"], "key_type": "fhir_integration"}, headers=demo_auth_headers
    ).json()
    assert key["secret"].startswith("nsk_fhir_")
    assert "bundle:write" in key["scopes"]

    listed = client.get("/api/v1/api-keys", headers=demo_auth_headers).json()["keys"]
    assert any(k["id"] == key["id"] for k in listed)

    rotated = client.post(f"/api/v1/api-keys/{key['id']}/rotate", headers=demo_auth_headers).json()
    assert rotated["id"] != key["id"]

    revoked = client.post(f"/api/v1/api-keys/{rotated['id']}/revoke", headers=demo_auth_headers).json()
    assert revoked["revoked_at"] is not None


def test_invalid_key_type_rejected(demo_auth_headers):
    c = client.post("/api/v1/api-keys/clients", json={"name": "x"}, headers=demo_auth_headers).json()
    resp = client.post("/api/v1/api-keys", json={"client_id": c["id"], "key_type": "not_a_real_type"}, headers=demo_auth_headers)
    assert resp.status_code == 400


# ── v1 public surface gating ────────────────────────────────────────────────
def test_v1_search_requires_a_key():
    resp = client.get("/api/v1/terminology/search", params={"q": "fever"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["resourceType"] == "OperationOutcome"


def test_v1_search_works_with_a_valid_sandbox_key():
    _, key = _make_client_and_key(key_type="sandbox")
    resp = client.get("/api/v1/terminology/search", params={"q": "fever"}, headers={"X-API-Key": key["secret"]})
    assert resp.status_code == 200
    assert "results" in resp.json()


def test_v1_translate_works_with_scope():
    _, key = _make_client_and_key(key_type="sandbox")  # sandbox has translate:read
    resp = client.get(
        "/api/v1/translate", params={"system": "NAM", "code": "AA-1"}, headers={"X-API-Key": key["secret"]}
    )
    assert resp.status_code == 200
    assert resp.json()["resourceType"] == "Parameters"


def test_v1_validate_code_blocked_without_scope():
    _, key = _make_client_and_key(key_type="sandbox")  # no validate:read
    resp = client.post(
        "/api/v1/validate-code", json={"system": "NAM", "code": "AA-1"}, headers={"X-API-Key": key["secret"]}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["issue"][0]["code"] == "forbidden"


def test_v1_validate_code_confirms_a_real_code():
    _, key = _make_client_and_key(key_type="readonly")  # has validate:read
    resp = client.post(
        "/api/v1/validate-code", json={"system": "NAM", "code": "AA-1"}, headers={"X-API-Key": key["secret"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {"name": "result", "valueBoolean": True} in body["parameter"]


def test_v1_validate_code_rejects_a_fake_code():
    _, key = _make_client_and_key(key_type="readonly")
    resp = client.post(
        "/api/v1/validate-code", json={"system": "NAM", "code": "TOTALLY-FAKE-999"}, headers={"X-API-Key": key["secret"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {"name": "result", "valueBoolean": False} in body["parameter"]


def test_v1_rate_limit_returns_429():
    _, key = _make_client_and_key(key_type="sandbox")  # 30/min
    headers = {"X-API-Key": key["secret"]}
    for _ in range(30):
        r = client.get("/api/v1/terminology/search", params={"q": "fever"}, headers=headers)
        assert r.status_code == 200
    r = client.get("/api/v1/terminology/search", params={"q": "fever"}, headers=headers)
    assert r.status_code == 429
    assert r.json()["detail"]["issue"][0]["code"] == "throttled"


def test_capability_statement_needs_no_key():
    resp = client.get("/api/v1/CapabilityStatement")
    assert resp.status_code == 200
    body = resp.json()
    assert body["resourceType"] == "CapabilityStatement"
    resource_types = {r["type"] for r in body["rest"][0]["resource"]}
    assert "ConceptMap" in resource_types
    assert "Consent" in resource_types


def test_usage_is_tracked_per_key(demo_auth_headers):
    c = client.post("/api/v1/api-keys/clients", json={"name": "x"}, headers=demo_auth_headers).json()
    key = client.post("/api/v1/api-keys", json={"client_id": c["id"], "key_type": "sandbox"}, headers=demo_auth_headers).json()
    client.get("/api/v1/terminology/search", params={"q": "fever"}, headers={"X-API-Key": key["secret"]})
    client.get("/api/v1/terminology/search", params={"q": "cough"}, headers={"X-API-Key": key["secret"]})

    usage = client.get(f"/api/v1/api-keys/{key['id']}/usage", headers=demo_auth_headers).json()
    assert usage["total_requests"] == 2
