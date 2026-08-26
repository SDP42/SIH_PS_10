"""
Test isolation: point every module at a throwaway copy of the demo database
before any app module is imported, so pytest runs (governance approve/reject,
review-queue inserts) never write into db/ayush_icd11_combined.db — the file
used for the live demo.

Runs at collection time, before any tests/test_*.py or app.* module import,
by monkeypatching the DB_PATH module attributes each module reads from.
"""
import os
import shutil
import sqlite3
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCE_DB = os.path.join(_HERE, "..", "db", "ayush_icd11_combined.db")

_test_db_dir = tempfile.mkdtemp(prefix="namaste_icd11_test_db_")
TEST_DB_PATH = os.path.join(_test_db_dir, "ayush_icd11_combined_test.db")
shutil.copyfile(_SOURCE_DB, TEST_DB_PATH)

# app/api.py, app/conceptmap.py, app/ai_mapping.py, app/governance.py,
# app/fhir_extra.py, app/audit.py each hardcode
# DB_PATH = "db/ayush_icd11_combined.db" as a module-level constant (no
# settings object to override via env var), so the only reliable
# interception point is patching that attribute directly on each
# already-imported module before any test runs.
import app.api as _api
import app.conceptmap as _conceptmap
import app.ai_mapping as _ai_mapping
import app.governance as _governance
import app.fhir_extra as _fhir_extra
import app.audit as _audit
import app.who_sync as _who_sync

for _mod in (_api, _conceptmap, _ai_mapping, _governance, _fhir_extra, _audit, _who_sync):
    _mod.DB_PATH = TEST_DB_PATH

_governance.ensure_schema()
_audit.ensure_schema()
_who_sync.ensure_schema()


@pytest.fixture
def demo_auth_headers():
    """Authorization header for a demo-mode ABHA token, for tests hitting
    write endpoints gated by app.auth.require_demo_auth."""
    from app.auth import _sign
    import time

    now = int(time.time())
    token = _sign({"name": "Test Reviewer", "role": "AYUSH Clinician", "iat": now, "exp": now + 3600, "mode": "ABHA_DEMO"})
    return {"Authorization": f"Bearer {token}"}
