"""
Tests for the tamper-evident audit hash chain (app/audit.py, Phase 3B).

The property that matters: any direct modification to an audit_log row —
made by editing the database directly, not through log() — must be caught
by verify_chain(), which must name the exact row where the chain breaks.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pytest
from fastapi.testclient import TestClient

from app import audit
from app.main import app

client = TestClient(app)


def _heal_chain():
    conn = sqlite3.connect(audit.DB_PATH)
    conn.execute("UPDATE audit_log SET row_hash = NULL, prev_hash = NULL")
    conn.commit()
    conn.close()
    audit.ensure_schema()


@pytest.fixture(autouse=True)
def _heal_chain_around_each_test():
    """
    Several tests here deliberately tamper with / delete audit_log rows to
    prove verify_chain() catches it. The test database is shared across this
    whole file *and every other test file in the same pytest run* — healing
    only after each test left the very first test in this file exposed to
    whatever raw-write state other files' fixtures left behind before this
    file even started. Healing both before and after closes that gap.
    """
    _heal_chain()
    yield
    _heal_chain()


def _row_count():
    conn = sqlite3.connect(audit.DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    conn.close()
    return n


def test_fresh_chain_is_valid():
    audit.log(action="TEST_EVENT", actor="pytest", target="x", details="y")
    result = audit.verify_chain()
    assert result["valid"] is True
    assert result["broken_at_id"] is None
    assert result["rows_checked"] == result["total_rows"]


def test_every_row_gets_a_hash_and_links_to_the_previous_one():
    audit.log(action="TEST_EVENT_A", actor="pytest")
    audit.log(action="TEST_EVENT_B", actor="pytest")

    conn = sqlite3.connect(audit.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 2").fetchall()
    conn.close()
    newer, older = rows[0], rows[1]

    assert newer["row_hash"] is not None
    assert older["row_hash"] is not None
    assert newer["prev_hash"] == older["row_hash"], "each row's prev_hash must equal the prior row's row_hash"


def test_genesis_row_chains_from_the_fixed_genesis_hash():
    conn = sqlite3.connect(audit.DB_PATH)
    conn.row_factory = sqlite3.Row
    first = conn.execute("SELECT * FROM audit_log ORDER BY id ASC LIMIT 1").fetchone()
    conn.close()
    assert first["prev_hash"] == audit.GENESIS_HASH


def test_tampering_with_row_content_is_detected():
    audit.log(action="TEST_TAMPER_TARGET", actor="pytest", details="original")
    conn = sqlite3.connect(audit.DB_PATH)
    row = conn.execute("SELECT id FROM audit_log WHERE action = 'TEST_TAMPER_TARGET' ORDER BY id DESC LIMIT 1").fetchone()
    tampered_id = row[0]

    conn.execute("UPDATE audit_log SET details = 'TAMPERED' WHERE id = ?", (tampered_id,))
    conn.commit()
    conn.close()

    result = audit.verify_chain()
    assert result["valid"] is False
    assert result["broken_at_id"] == tampered_id
    assert "modified" in result["reason"]


def test_tampering_with_actor_field_is_also_detected():
    """Every field is covered by the hash, not just `details`."""
    audit.log(action="TEST_TAMPER_ACTOR", actor="honest actor")
    conn = sqlite3.connect(audit.DB_PATH)
    row = conn.execute("SELECT id FROM audit_log WHERE action = 'TEST_TAMPER_ACTOR' ORDER BY id DESC LIMIT 1").fetchone()
    tampered_id = row[0]
    conn.execute("UPDATE audit_log SET actor = 'attacker' WHERE id = ?", (tampered_id,))
    conn.commit()
    conn.close()

    result = audit.verify_chain()
    assert result["valid"] is False
    assert result["broken_at_id"] == tampered_id


def test_deleting_a_row_breaks_the_chain_at_the_next_row():
    audit.log(action="TEST_DELETE_A", actor="pytest")
    audit.log(action="TEST_DELETE_B", actor="pytest")
    conn = sqlite3.connect(audit.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id FROM audit_log WHERE action IN ('TEST_DELETE_A','TEST_DELETE_B') ORDER BY id ASC").fetchall()
    first_id, second_id = rows[0]["id"], rows[1]["id"]

    conn.execute("DELETE FROM audit_log WHERE id = ?", (first_id,))
    conn.commit()
    conn.close()

    result = audit.verify_chain()
    assert result["valid"] is False
    assert result["broken_at_id"] == second_id
    assert "deleted" in result["reason"] or "reordered" in result["reason"]


def test_verify_endpoint_reflects_module_function():
    audit.log(action="TEST_ENDPOINT_CHECK", actor="pytest")
    resp = client.get("/api/audit/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body == audit.verify_chain()


def test_ensure_schema_backfills_legacy_rows_without_a_hash():
    """
    Simulates a row written before the chain existed (row_hash/prev_hash
    NULL) and confirms ensure_schema() backfills it into the chain rather
    than leaving a hole verify_chain() can't reason about.
    """
    conn = sqlite3.connect(audit.DB_PATH)
    conn.execute(
        "INSERT INTO audit_log (action, actor, target, details, created_at) VALUES (?, ?, ?, ?, ?)",
        ("TEST_LEGACY_ROW", "pytest", None, None, "2020-01-01T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    audit.ensure_schema()  # should backfill the row above
    result = audit.verify_chain()
    assert result["valid"] is True


def test_log_function_signature_unchanged_for_existing_callers():
    """All existing call sites (governance_router, who_router, apikey_router,
    terminology_simulator_router, fhir_extra) call log() positionally/by
    keyword exactly as before — this must keep working with no changes there."""
    audit.log("ACTION", "actor", "target", "details")
    audit.log(action="ACTION2", actor="actor2")
    assert audit.verify_chain()["valid"] is True
