"""Tests for app/problem_list.py and app/consent.py."""
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
    return row[0]


def test_build_problem_list_entry():
    code = _find_curated_pair()
    resp = client.post("/api/problem-list/build", json={"namaste_code": code})
    assert resp.status_code == 200
    body = resp.json()
    assert body["resourceType"] == "Condition"
    assert body["category"][0]["coding"][0]["code"] == "problem-list-item"
    codings = body["code"]["coding"]
    assert codings[0]["code"] == code
    assert len(codings) >= 1  # at least the NAMASTE coding, plus any resolved ICD-11 codes


def test_build_problem_list_entry_unknown_code():
    resp = client.post("/api/problem-list/build", json={"namaste_code": "NOT_A_REAL_CODE_XYZ"})
    assert resp.status_code == 404


def test_consent_stub():
    resp = client.get("/Consent/demo-consent-001")
    assert resp.status_code == 200
    assert resp.json()["resourceType"] == "Consent"


def test_consent_stub_unknown_id():
    resp = client.get("/Consent/not-a-real-id")
    assert resp.status_code == 404
