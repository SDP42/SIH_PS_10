"""
Tests for the Terminology Firewall (app/terminology_firewall.py, mounted at
POST /api/v1/firewall/check in app/v1_router.py).

The firewall is a composition of already-tested logic (code existence,
who_drift, dual-coding translate) — these tests focus on the composition
itself: does the right verdict come out for each real scenario, and does
checking a Bundle ever mutate concept_map/review_queue (it must not).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pytest
from fastapi.testclient import TestClient

from app import terminology_firewall as firewall
from app import apikeys
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_state():
    conn = sqlite3.connect(firewall.DB_PATH)
    # who_drift is cleared too: other test files (test_who_sync.py,
    # test_terminology_simulator.py) insert fake drift rows against real
    # local target codes as part of their own scenarios, and — being
    # autouse only within their own file — don't clean up after the last
    # test in that file runs. Since the firewall's REVIEW_REQUIRED verdict
    # legitimately depends on who_drift, a stray fake row left behind by
    # an unrelated test file would otherwise flip an ACCEPTED case here.
    for table in ("firewall_decisions", "api_usage", "api_keys", "api_clients", "who_drift"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
    yield


def _fhir_integration_key():
    client_row = apikeys.create_client("Test EMR", None, created_by="pytest")
    key = apikeys.create_key(client_id=client_row["id"], key_type="fhir_integration", created_by="pytest")
    return key["secret"]


def _sandbox_key():
    client_row = apikeys.create_client("Test EMR Sandbox", None, created_by="pytest")
    key = apikeys.create_key(client_id=client_row["id"], key_type="sandbox", created_by="pytest")
    return key["secret"]


def _real_curated_code():
    """
    A code whose mapping is curated (not AI-fallback) on BOTH the TM2 and
    Biomedicine legs — deterministically ACCEPTED regardless of what the AI
    engine's confidence happens to be for less-fully-curated codes. Picking
    an arbitrary `LIMIT 1` row here previously made this test's outcome
    depend on which row that happened to be — most curated codes still fall
    back to the (variable-confidence) AI engine on one leg or the other.
    """
    conn = sqlite3.connect(firewall.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT cm.source_code, cm.source_system, i.chapterno
           FROM concept_map cm JOIN icd11 i ON i.code = cm.target_code"""
    ).fetchall()
    conn.close()

    chapters_by_code = {}
    for r in rows:
        key = (r["source_code"], r["source_system"])
        chapters_by_code.setdefault(key, set()).add("TM2" if r["chapterno"] == "26" else "BIOMED")

    for (source_code, _source_system), chapters in chapters_by_code.items():
        if chapters == {"TM2", "BIOMED"}:
            return source_code
    raise AssertionError("expected at least one NAMASTE code curated on both TM2 and Biomedicine")


def _bundle_with_condition(resource: dict) -> dict:
    return {"resourceType": "Bundle", "type": "collection", "entry": [{"resource": resource}]}


def _valid_condition(code: str, resource_id: str = "c1") -> dict:
    return {
        "resourceType": "Condition", "id": resource_id,
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "subject": {"reference": "Patient/demo"},
        "code": {"coding": [{"system": "http://namaste.terminology/CodeSystem/ayurveda-morbidity", "code": code}]},
    }


def test_requires_api_key():
    resp = client.post("/api/v1/firewall/check", json=_bundle_with_condition(_valid_condition("AA-1")))
    assert resp.status_code == 401


def test_requires_bundle_write_scope():
    key = _sandbox_key()  # sandbox has no bundle:write
    resp = client.post(
        "/api/v1/firewall/check", json=_bundle_with_condition(_valid_condition("AA-1")),
        headers={"X-API-Key": key},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["issue"][0]["code"] == "forbidden"


def test_accepts_a_real_curated_mapping():
    key = _fhir_integration_key()
    code = _real_curated_code()
    resp = client.post(
        "/api/v1/firewall/check", json=_bundle_with_condition(_valid_condition(code)),
        headers={"X-API-Key": key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "ACCEPTED"
    assert body["operationOutcome"]["resourceType"] == "OperationOutcome"


def test_rejects_a_code_that_does_not_exist():
    key = _fhir_integration_key()
    resp = client.post(
        "/api/v1/firewall/check", json=_bundle_with_condition(_valid_condition("TOTALLY-FAKE-CODE-9999")),
        headers={"X-API-Key": key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "REJECTED"
    assert "does not exist" in body["reasons"][0]


def test_rejects_structurally_incomplete_condition():
    key = _fhir_integration_key()
    incomplete = {"resourceType": "Condition", "id": "c1",
                  "code": {"coding": [{"system": "http://namaste.terminology/CodeSystem/ayurveda-morbidity", "code": "AA-1"}]}}
    resp = client.post("/api/v1/firewall/check", json=_bundle_with_condition(incomplete), headers={"X-API-Key": key})
    body = resp.json()
    assert body["verdict"] == "REJECTED"
    assert "missing required field" in body["reasons"][0]


def test_rejects_condition_with_no_namaste_coding():
    key = _fhir_integration_key()
    no_coding = _valid_condition("AA-1")
    no_coding["code"] = {"coding": [{"system": "http://example.org/other", "code": "X"}]}
    resp = client.post("/api/v1/firewall/check", json=_bundle_with_condition(no_coding), headers={"X-API-Key": key})
    assert resp.json()["verdict"] == "REJECTED"


def test_rejects_non_bundle_input():
    key = _fhir_integration_key()
    resp = client.post("/api/v1/firewall/check", json={"resourceType": "NotABundle"}, headers={"X-API-Key": key})
    assert resp.json()["verdict"] == "REJECTED"


def test_rejects_bundle_with_no_conditions():
    key = _fhir_integration_key()
    resp = client.post(
        "/api/v1/firewall/check", json={"resourceType": "Bundle", "type": "collection", "entry": []},
        headers={"X-API-Key": key},
    )
    assert resp.json()["verdict"] == "REJECTED"


def test_never_mutates_concept_map_or_review_queue():
    key = _fhir_integration_key()
    code = _real_curated_code()

    conn = sqlite3.connect(firewall.DB_PATH)
    before_cm = conn.execute("SELECT COUNT(*) FROM concept_map").fetchone()[0]
    before_rq = conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0]
    conn.close()

    client.post("/api/v1/firewall/check", json=_bundle_with_condition(_valid_condition(code)), headers={"X-API-Key": key})
    client.post("/api/v1/firewall/check", json=_bundle_with_condition(_valid_condition("FAKE-999")), headers={"X-API-Key": key})

    conn = sqlite3.connect(firewall.DB_PATH)
    after_cm = conn.execute("SELECT COUNT(*) FROM concept_map").fetchone()[0]
    after_rq = conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0]
    conn.close()

    assert before_cm == after_cm
    assert before_rq == after_rq


def test_decision_is_recorded_and_listed_in_history():
    key = _fhir_integration_key()
    code = _real_curated_code()
    client.post("/api/v1/firewall/check", json=_bundle_with_condition(_valid_condition(code)), headers={"X-API-Key": key})

    history = client.get("/api/v1/firewall/history").json()["decisions"]
    assert len(history) == 1
    assert history[0]["verdict"] == "ACCEPTED"
    assert history[0]["decided_by"].startswith("api_key:")


def test_worst_verdict_wins_across_multiple_conditions():
    key = _fhir_integration_key()
    code = _real_curated_code()
    bundle = {
        "resourceType": "Bundle", "type": "collection",
        "entry": [
            {"resource": _valid_condition(code, "good")},
            {"resource": _valid_condition("TOTALLY-FAKE-9999", "bad")},
        ],
    }
    resp = client.post("/api/v1/firewall/check", json=bundle, headers={"X-API-Key": key})
    body = resp.json()
    assert body["checked_conditions"] == 2
    assert body["verdict"] == "REJECTED"  # the worst of ACCEPTED + REJECTED
