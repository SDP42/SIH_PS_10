"""
Tests for the Terminology What-If Simulator (app/terminology_simulator.py,
app/terminology_simulator_router.py).

Every WHO network call is stubbed (same pattern as tests/test_who_sync.py)
so these tests never depend on reaching WHO's real servers. The one thing
this module must get right above all else: it must NEVER modify
concept_map, and must never touch review_queue until an explicit,
separately-authenticated escalate() call.
"""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pytest
from fastapi.testclient import TestClient

from app import terminology_simulator as sim
from app import who_sync
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_state():
    conn = sqlite3.connect(sim.DB_PATH)
    for table in ("simulation_affected_mappings", "terminology_simulations",
                  "who_release_cache", "who_release_meta"):
        conn.execute(f"DELETE FROM {table}")
    conn.execute("DELETE FROM review_queue WHERE flag_type = 'terminology_drift'")
    conn.commit()
    conn.close()
    yield


def _local_target_code():
    conn = sqlite3.connect(sim.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """SELECT cm.id, cm.target_code AS code, i.title AS title
           FROM concept_map cm JOIN icd11 i ON i.code = cm.target_code LIMIT 1"""
    ).fetchone()
    conn.close()
    return row["id"], row["code"], row["title"]


class _FakeResponse:
    def __init__(self, status_code, content=b""):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise who_sync.requests.HTTPError(f"HTTP {self.status_code}")


def _fake_zip(rows, version="stub"):
    header = f"Code\tTitle\tClassKind\tChapterNo\tVersion:{version}\n"
    lines = [header] + [f"{c}\t{t}\tcategory\t01\t\n" for c, t in rows]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "columns\n")
        zf.writestr(f"{who_sync.RELEASE_FILE_NAME}.txt", "".join(lines).encode("utf-8-sig"))
    return buf.getvalue()


def _install_releases(monkeypatch, tables_by_release):
    def fake_get(url, **kwargs):
        for release_id, rows in tables_by_release.items():
            if f"/{release_id}/" in url:
                return _FakeResponse(200, content=_fake_zip(rows))
        return _FakeResponse(404)
    monkeypatch.setattr(who_sync.requests, "get", fake_get)


def test_simulate_detects_broken_and_ambiguous_mappings(monkeypatch, demo_auth_headers):
    cm_id, code, title = _local_target_code()
    display = who_sync._display_title(title)

    _install_releases(monkeypatch, {
        "2099-01": [(code, display)],
        "2099-02": [("ZZZZ-DECOY", "Some other unrelated code")],  # the target code vanished -> broken
    })
    body = client.post(
        "/api/v1/terminology/simulate", json={"from_release": "2099-01", "to_release": "2099-02"},
        headers=demo_auth_headers,
    ).json()
    assert body["broken_mappings"] == 1
    assert body["ambiguous_mappings"] == 0
    assert body["risk_score"] in ("MEDIUM", "HIGH")


def test_simulate_detects_retitled_as_ambiguous(monkeypatch, demo_auth_headers):
    cm_id, code, title = _local_target_code()
    display = who_sync._display_title(title)

    _install_releases(monkeypatch, {
        "2099-03": [(code, display)],
        "2099-04": [(code, "A Totally Different Title")],  # still exists, retitled
    })
    body = client.post(
        "/api/v1/terminology/simulate", json={"from_release": "2099-03", "to_release": "2099-04"},
        headers=demo_auth_headers,
    ).json()
    assert body["broken_mappings"] == 0
    assert body["ambiguous_mappings"] == 1


def test_simulate_against_itself_reports_zero_changes(monkeypatch, demo_auth_headers):
    cm_id, code, title = _local_target_code()
    display = who_sync._display_title(title)
    _install_releases(monkeypatch, {"2099-05": [(code, display)]})

    body = client.post(
        "/api/v1/terminology/simulate", json={"from_release": "2099-05", "to_release": "2099-05"},
        headers=demo_auth_headers,
    ).json()
    assert body["new_concepts"] == 0
    assert body["deprecated_concepts"] == 0
    assert body["retitled_concepts"] == 0
    assert body["broken_mappings"] == 0
    assert body["ambiguous_mappings"] == 0
    assert body["risk_score"] == "LOW"


def test_simulate_requires_auth():
    resp = client.post("/api/v1/terminology/simulate", json={"from_release": "2025-01", "to_release": "2026-01"})
    assert resp.status_code == 401


def test_simulate_never_touches_concept_map_or_review_queue(monkeypatch, demo_auth_headers):
    """The core safety property: a simulation is read-only against both tables until escalate()."""
    cm_id, code, title = _local_target_code()
    display = who_sync._display_title(title)
    _install_releases(monkeypatch, {"2099-06": [(code, display)], "2099-07": [("ZZZZ-DECOY", "Some other unrelated code")]})

    conn = sqlite3.connect(sim.DB_PATH)
    before_cm = conn.execute("SELECT COUNT(*) FROM concept_map").fetchone()[0]
    before_rq = conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0]
    conn.close()

    client.post("/api/v1/terminology/simulate", json={"from_release": "2099-06", "to_release": "2099-07"}, headers=demo_auth_headers)

    conn = sqlite3.connect(sim.DB_PATH)
    after_cm = conn.execute("SELECT COUNT(*) FROM concept_map").fetchone()[0]
    after_rq = conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0]
    conn.close()
    assert before_cm == after_cm
    assert before_rq == after_rq


def test_escalate_creates_review_queue_items_without_touching_concept_map(monkeypatch, demo_auth_headers):
    cm_id, code, title = _local_target_code()
    display = who_sync._display_title(title)
    _install_releases(monkeypatch, {"2099-08": [(code, display)], "2099-09": [("ZZZZ-DECOY", "Some other unrelated code")]})

    sim_id = client.post(
        "/api/v1/terminology/simulate", json={"from_release": "2099-08", "to_release": "2099-09"},
        headers=demo_auth_headers,
    ).json()["id"]

    conn = sqlite3.connect(sim.DB_PATH)
    before_cm = conn.execute("SELECT COUNT(*) FROM concept_map").fetchone()[0]
    conn.close()

    resp = client.post(f"/api/v1/terminology/simulate/{sim_id}/escalate", headers=demo_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1

    conn = sqlite3.connect(sim.DB_PATH)
    conn.row_factory = sqlite3.Row
    after_cm = conn.execute("SELECT COUNT(*) FROM concept_map").fetchone()[0]
    rq_row = conn.execute("SELECT * FROM review_queue WHERE id = ?", (body["review_queue_ids"][0],)).fetchone()
    conn.close()

    assert after_cm == before_cm, "escalation must never touch concept_map"
    assert rq_row["flag_type"] == "terminology_drift"
    assert rq_row["decision"] == "EXPERT_REVIEW"
    assert rq_row["status"] == "pending"


def test_escalate_requires_auth(monkeypatch, demo_auth_headers):
    cm_id, code, title = _local_target_code()
    display = who_sync._display_title(title)
    _install_releases(monkeypatch, {"2099-10": [(code, display)], "2099-11": [("ZZZZ-DECOY", "Some other unrelated code")]})
    sim_id = client.post(
        "/api/v1/terminology/simulate", json={"from_release": "2099-10", "to_release": "2099-11"},
        headers=demo_auth_headers,
    ).json()["id"]
    assert client.post(f"/api/v1/terminology/simulate/{sim_id}/escalate").status_code == 401


def test_escalate_is_idempotent(monkeypatch, demo_auth_headers):
    cm_id, code, title = _local_target_code()
    display = who_sync._display_title(title)
    _install_releases(monkeypatch, {"2099-12": [(code, display)], "2099-13": [("ZZZZ-DECOY", "Some other unrelated code")]})
    sim_id = client.post(
        "/api/v1/terminology/simulate", json={"from_release": "2099-12", "to_release": "2099-13"},
        headers=demo_auth_headers,
    ).json()["id"]

    first = client.post(f"/api/v1/terminology/simulate/{sim_id}/escalate", headers=demo_auth_headers).json()
    second = client.post(f"/api/v1/terminology/simulate/{sim_id}/escalate", headers=demo_auth_headers).json()
    assert first["review_queue_ids"] == second["review_queue_ids"]

    conn = sqlite3.connect(sim.DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM review_queue WHERE flag_type='terminology_drift'").fetchone()[0]
    conn.close()
    assert n == 1, "re-escalating must not duplicate review_queue rows"


def test_affected_mappings_endpoint_filters_by_impact_type(monkeypatch, demo_auth_headers):
    cm_id, code, title = _local_target_code()
    display = who_sync._display_title(title)
    _install_releases(monkeypatch, {"2099-14": [(code, display)], "2099-15": [("ZZZZ-DECOY", "Some other unrelated code")]})
    sim_id = client.post(
        "/api/v1/terminology/simulate", json={"from_release": "2099-14", "to_release": "2099-15"},
        headers=demo_auth_headers,
    ).json()["id"]

    broken = client.get(f"/api/v1/terminology/simulate/{sim_id}/affected-mappings", params={"impact_type": "BROKEN_MAPPING"}).json()
    ambiguous = client.get(f"/api/v1/terminology/simulate/{sim_id}/affected-mappings", params={"impact_type": "AMBIGUOUS_MAPPING"}).json()
    assert len(broken["items"]) == 1
    assert len(ambiguous["items"]) == 0


def test_unknown_simulation_id_404s():
    assert client.get("/api/v1/terminology/simulate/999999").status_code == 404
    assert client.get("/api/v1/terminology/simulate/999999/affected-mappings").status_code == 404


def test_who_fetch_failure_returns_502_not_500(monkeypatch, demo_auth_headers):
    def fake_get(url, **kwargs):
        return _FakeResponse(404)
    monkeypatch.setattr(who_sync.requests, "get", fake_get)
    resp = client.post(
        "/api/v1/terminology/simulate", json={"from_release": "nonexistent-1", "to_release": "nonexistent-2"},
        headers=demo_auth_headers,
    )
    assert resp.status_code == 502


def test_releases_endpoint_needs_no_auth():
    resp = client.get("/api/v1/terminology/releases")
    assert resp.status_code == 200
