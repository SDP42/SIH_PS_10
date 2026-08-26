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


def test_valueset_expand():
    resp = client.get("/ValueSet/$expand", params={"filter": "fever", "system": "icd11", "count": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["resourceType"] == "ValueSet"
    assert isinstance(body["expansion"]["contains"], list)
