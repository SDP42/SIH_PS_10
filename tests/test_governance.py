"""
Tests for the governance review-queue workflow (app/governance.py).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pytest
from fastapi.testclient import TestClient

from app import governance, ai_mapping
from app.main import app

client = TestClient(app)

pytestmark = pytest.mark.skipif(
    not ai_mapping.is_ready(),
    reason="AI mapping embeddings not built — run: python scripts/build_embeddings.py",
)


def _find_review_suggestion():
    source_rows, _ = ai_mapping._load_index()
    for row in source_rows[:100]:
        suggestion = ai_mapping.get_candidates(row["code"])
        if suggestion["decision"] in ("NEEDS_CONTEXT", "EXPERT_REVIEW"):
            return suggestion
    return None


def test_enqueue_and_approve_writes_curated_mapping():
    suggestion = _find_review_suggestion()
    assert suggestion is not None, "expected at least one NEEDS_CONTEXT/EXPERT_REVIEW suggestion among sampled concepts"

    item_id = governance.enqueue_from_suggestion(suggestion)
    assert item_id is not None

    conn = sqlite3.connect(governance.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM concept_map")
    before = cur.fetchone()[0]
    conn.close()

    result = governance.decide(item_id=item_id, status="approved", note="test approval")
    assert result["status"] == "approved"
    assert result["new_concept_mapping_id"] is not None

    conn = sqlite3.connect(governance.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM concept_map")
    after = cur.fetchone()[0]
    cur.execute("SELECT source, version FROM concept_map WHERE id = ?", (result["new_concept_mapping_id"],))
    row = cur.fetchone()
    conn.close()

    assert after == before + 1
    assert row[0] == "ai_reviewed_v1"


def test_dedupe_on_repeated_enqueue():
    suggestion = _find_review_suggestion()
    assert suggestion is not None
    first_id = governance.enqueue_from_suggestion(suggestion)
    second_id = governance.enqueue_from_suggestion(suggestion)
    assert first_id == second_id


def test_reject_does_not_write_mapping():
    suggestion = _find_review_suggestion()
    assert suggestion is not None
    item_id = governance.enqueue_from_suggestion(suggestion)

    conn = sqlite3.connect(governance.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM concept_map")
    before = cur.fetchone()[0]
    conn.close()

    result = governance.decide(item_id=item_id, status="rejected", note="not a match")
    assert result["status"] == "rejected"
    assert result["new_concept_mapping_id"] is None

    conn = sqlite3.connect(governance.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM concept_map")
    after = cur.fetchone()[0]
    conn.close()
    assert after == before


def test_queue_endpoint():
    resp = client.get("/api/governance/queue", params={"page": 1, "page_size": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body and "total" in body


def test_decide_endpoint_invalid_status():
    resp = client.post("/api/governance/999999/decide", json={"status": "bogus"})
    assert resp.status_code == 400


def test_decide_endpoint_not_found():
    resp = client.post("/api/governance/999999/decide", json={"status": "approved"})
    assert resp.status_code == 404
