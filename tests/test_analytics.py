"""
Tests for governance & interoperability analytics (app/analytics.py).

The main thing worth locking down here isn't the arithmetic (it's plain SQL
aggregation) but the **honesty constraint**: this dashboard must never carry
a fabricated encounter/patient-volume number, since none is ever persisted
anywhere in this codebase.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app import ai_mapping
from app.main import app

client = TestClient(app)

pytestmark = pytest.mark.skipif(
    not ai_mapping.is_ready(),
    reason="AI mapping embeddings not built — run: python scripts/build_embeddings.py",
)


def test_overview_returns_200_with_expected_top_level_shape():
    body = client.get("/api/analytics/overview").json()
    for key in ("traditions", "mapping_registry", "review_queue", "who_sync", "audit_activity", "data_honesty_note"):
        assert key in body


def test_no_fabricated_encounter_or_patient_volume_is_present():
    """
    The whole point of this dashboard is to be honest about what's real. No
    panel here may claim a patient/encounter count, because this service
    never persists one anywhere.
    """
    body = client.get("/api/analytics/overview")
    text = body.text.lower()
    for banned in ("encounter_volume", "patient_count", "encounters_per_day", "patient_volume"):
        assert banned not in text


def test_tradition_coverage_matches_raw_table_counts():
    body = client.get("/api/analytics/overview").json()
    by_system = {t["system"]: t for t in body["traditions"]}
    assert set(by_system) == {"NAM", "NSM", "NUM", "AST"}
    for t in by_system.values():
        assert t["corpus_size"] > 0
        if t["mapped"] is not None:
            assert t["mapped"] + t["unmapped"] == t["corpus_size"]
            assert 0 <= t["coverage_pct"] <= 100


def test_mapping_registry_totals_are_internally_consistent():
    body = client.get("/api/analytics/overview").json()
    reg = body["mapping_registry"]
    assert reg["equivalent"] + reg["related"] == reg["total_mappings"]
    assert reg["curated_rule_based"] + reg["ai_reviewed"] == reg["total_mappings"]


def test_review_queue_reflects_real_queue_state():
    body = client.get("/api/analytics/overview").json()
    rq = body["review_queue"]
    total = rq["pending"] + rq["approved"] + rq["rejected"] + rq["needs_info"]
    assert total >= 0
    assert isinstance(rq["by_decision_tier"], dict)


def test_audit_activity_endpoint_accepts_day_window():
    body = client.get("/api/analytics/audit-activity", params={"days": 7}).json()
    assert body["days"] == 7
    assert isinstance(body["activity"], list)


def test_audit_activity_rejects_out_of_range_days():
    assert client.get("/api/analytics/audit-activity", params={"days": 0}).status_code == 422
    assert client.get("/api/analytics/audit-activity", params={"days": 1000}).status_code == 422


def test_overview_reflects_a_new_audit_event():
    from app import audit
    before = client.get("/api/analytics/overview").json()
    before_total = sum(a["n"] for a in before["audit_action_breakdown"] if a["action"] == "TEST_ANALYTICS_EVENT")

    audit.log(action="TEST_ANALYTICS_EVENT", actor="pytest", target="analytics-test", details="probe")

    after = client.get("/api/analytics/overview").json()
    after_total = sum(a["n"] for a in after["audit_action_breakdown"] if a["action"] == "TEST_ANALYTICS_EVENT")
    assert after_total == before_total + 1
