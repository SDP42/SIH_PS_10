"""
Tests for the new FHIR $translate / CodeSystem / ValueSet/$expand endpoints
(app/fhir_extra.py) — additive alongside the original app/conceptmap.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from fastapi.testclient import TestClient

from app import governance
from app.main import app

client = TestClient(app)


def _find_curated_pair():
    conn = sqlite3.connect(governance.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT source_code FROM concept_map LIMIT 1")
    row = cur.fetchone()
    conn.close()
    assert row is not None, "expected at least one curated concept_map row"
    return row[0]


def test_translate_matched_curated():
    code = _find_curated_pair()
    resp = client.get("/ConceptMap/$translate", params={"system": "NAM", "code": code})
    assert resp.status_code == 200
    body = resp.json()
    assert body["resourceType"] == "Parameters"
    result_param = next(p for p in body["parameter"] if p["name"] == "result")
    assert result_param["valueBoolean"] is True
    assert any(p["name"] == "match" for p in body["parameter"])


def test_translate_defaults_to_dual_coding():
    """Default target_system=BOTH must return one match group per system
    (TM2 and Biomedicine), each independently curated-first/AI-fallback."""
    code = _find_curated_pair()
    resp = client.get("/ConceptMap/$translate", params={"system": "NAM", "code": code})
    assert resp.status_code == 200
    matches = [p for p in resp.json()["parameter"] if p["name"] == "match"]
    groups = {
        next(x["valueString"] for x in m["part"] if x["name"] == "targetSystemGroup")
        for m in matches
    }
    assert groups == {"ICD-11 TM2", "ICD-11 Biomedicine"}


def test_translate_target_system_filter():
    code = _find_curated_pair()
    resp = client.get(
        "/ConceptMap/$translate", params={"system": "NAM", "code": code, "target_system": "ICD11-TM2"}
    )
    assert resp.status_code == 200
    matches = [p for p in resp.json()["parameter"] if p["name"] == "match"]
    for m in matches:
        group = next(x["valueString"] for x in m["part"] if x["name"] == "targetSystemGroup")
        assert group == "ICD-11 TM2"


def test_translate_unmatched_unknown_code():
    resp = client.get("/ConceptMap/$translate", params={"system": "NAM", "code": "NOT_A_REAL_CODE_XYZ"})
    assert resp.status_code == 200
    body = resp.json()
    result_param = next(p for p in body["parameter"] if p["name"] == "result")
    assert result_param["valueBoolean"] is False
    match_param = next(p for p in body["parameter"] if p["name"] == "match")
    equivalence = next(p for p in match_param["part"] if p["name"] == "equivalence")
    assert equivalence["valueCode"] == "unmatched"


def test_conceptmap_by_code_route_still_works():
    """Regression guard: mounting fhir_extra before conceptmap.router must not
    break GET /ConceptMap/{source_code}."""
    code = _find_curated_pair()
    resp = client.get(f"/ConceptMap/{code}")
    assert resp.status_code == 200
    assert resp.json()["resourceType"] == "ConceptMap"


def test_code_system_namaste():
    resp = client.get("/CodeSystem/NAM")
    assert resp.status_code == 200
    body = resp.json()
    assert body["resourceType"] == "CodeSystem"
    assert body["content"] == "not-present"
    assert body["count"] > 0


def test_code_system_unknown():
    resp = client.get("/CodeSystem/NOT_A_SYSTEM")
    assert resp.status_code == 404


def test_code_system_icd11_split_tm2_biomedicine():
    tm2 = client.get("/CodeSystem/ICD11-TM2").json()
    biomedicine = client.get("/CodeSystem/ICD11-BIOMEDICINE").json()
    assert tm2["count"] > 0
    assert biomedicine["count"] > 0
    # Biomedicine (25 chapters) must be far larger than TM2 (1 chapter)
    assert biomedicine["count"] > tm2["count"]


def test_bundle_upload_requires_auth():
    resp = client.post("/Bundle", json={"resourceType": "Bundle", "type": "transaction", "entry": []})
    assert resp.status_code == 401


def test_bundle_upload_enriches_condition_with_dual_coding(demo_auth_headers):
    code = _find_curated_pair()
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {"resource": {
                "resourceType": "Condition",
                "id": "cond-1",
                "code": {"coding": [{"system": "http://namaste.terminology/CodeSystem/ayurveda-morbidity", "code": code}]},
            }}
        ],
    }
    resp = client.post("/Bundle", json=bundle, headers=demo_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    codings = body["entry"][0]["resource"]["code"]["coding"]
    # original NAMASTE coding plus at least one ICD-11 coding appended
    assert len(codings) >= 2
    assert codings[0]["code"] == code


def test_bundle_upload_rejects_non_bundle(demo_auth_headers):
    resp = client.post("/Bundle", json={"resourceType": "Condition"}, headers=demo_auth_headers)
    assert resp.status_code == 400


def test_bundle_upload_rejects_no_condition(demo_auth_headers):
    resp = client.post("/Bundle", json={"resourceType": "Bundle", "type": "transaction", "entry": []}, headers=demo_auth_headers)
    assert resp.status_code == 400


def test_valueset_expand():
    resp = client.get("/ValueSet/$expand", params={"filter": "fever", "system": "icd11", "count": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["resourceType"] == "ValueSet"
    assert isinstance(body["expansion"]["contains"], list)
