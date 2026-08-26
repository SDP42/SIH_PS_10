"""
Tests for the Population Health Demo (app/population_analytics.py,
app/population_analytics_router.py) — a SYNTHETIC dataset, structurally
separate from the real governance analytics dashboard.

The single most important property under test: this synthetic data must
never leak into or be confused with app/analytics.py's real, live-computed
metrics. Two separate guard tests exist for that — one in each module's
test file — so a regression in either direction gets caught.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app import population_analytics as pop
from app.main import app

client = TestClient(app)


def test_dataset_is_available_after_generation():
    """The generator has already been run against this test DB copy (it was
    run against the real DB before pytest's conftest copied it)."""
    assert pop.is_available() is True


def test_overview_shape_and_disclaimer():
    body = pop.overview()
    assert body["is_synthetic"] is True
    assert "SYNTHETIC" in body["disclaimer"]
    assert 2000 <= body["total_patients"] <= 2500
    assert body["total_encounters"] > 0


def test_endpoint_returns_synthetic_flag_and_disclaimer():
    resp = client.get("/api/analytics/population-demo")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_synthetic"] is True
    assert body["available"] is True
    assert "SYNTHETIC" in body["disclaimer"]
    assert "SYNTHETIC" in body["overview"]["disclaimer"]


def test_by_gender_covers_real_categories_and_sums_to_total():
    rows = pop.by_gender()
    genders = {r["gender"] for r in rows}
    assert genders <= {"Male", "Female", "Other"}
    total = sum(r["n"] for r in rows)
    assert total == pop.overview()["total_patients"]


def test_by_age_band_covers_all_bands_in_order():
    rows = pop.by_age_band()
    assert [r["age_band"] for r in rows] == ["0-17", "18-29", "30-44", "45-59", "60-74", "75+"]
    assert sum(r["n"] for r in rows) == pop.overview()["total_patients"]


def test_by_region_uses_real_indian_state_names():
    rows = pop.by_region()
    regions = {r["region"] for r in rows}
    # Spot-check a few real states are present — these are real place names,
    # only the patient counts attached to them are synthetic.
    assert "Maharashtra" in regions or "Uttar Pradesh" in regions
    assert sum(r["patients"] for r in rows) == pop.overview()["total_patients"]


def test_by_month_is_chronologically_ordered():
    rows = pop.by_month()
    months = [r["month"] for r in rows]
    assert months == sorted(months)
    assert sum(r["n"] for r in rows) == pop.overview()["total_encounters"]


def test_by_tradition_only_covers_the_three_living_traditions():
    rows = pop.by_tradition()
    traditions = {r["tradition"] for r in rows}
    assert traditions <= {"Ayurveda", "Siddha", "Unani"}
    assert sum(r["n"] for r in rows) == pop.overview()["total_encounters"]


def test_gender_by_region_pivots_correctly():
    rows = pop.gender_by_region()
    total = sum(sum(v for k, v in r.items() if k != "region") for r in rows)
    assert total == pop.overview()["total_patients"]


def test_encounters_reference_real_namaste_codes():
    """The patient is fabricated; the terminology code it's attached to must be real."""
    import sqlite3
    conn = sqlite3.connect(pop.DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT namaste_code, tradition FROM synthetic_encounters LIMIT 20")
    sample = cur.fetchall()
    assert sample

    table_by_tradition = {"Ayurveda": ("nam", "namc_code"), "Siddha": ("nsm", "namc_code"), "Unani": ("num", "numc_code")}
    for row in sample:
        table, code_col = table_by_tradition[row["tradition"]]
        cur.execute(f"SELECT 1 FROM {table} WHERE {code_col} = ? LIMIT 1", (row["namaste_code"],))
        assert cur.fetchone() is not None, f"{row['namaste_code']} should be a real code in {table}"
    conn.close()


def test_every_synthetic_row_is_flagged_in_the_database_itself():
    """Not just the API — the raw table schema also makes fabrication status obvious."""
    import sqlite3
    conn = sqlite3.connect(pop.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM synthetic_patients WHERE is_synthetic != 1")
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT COUNT(*) FROM synthetic_encounters WHERE is_synthetic != 1")
    assert cur.fetchone()[0] == 0
    conn.close()


def test_real_governance_dashboard_is_not_contaminated_by_synthetic_data():
    """
    The critical cross-module guarantee: app/analytics.py's real overview
    must never reference the synthetic tables, and must not change shape
    because they now exist in the same database.
    """
    resp = client.get("/api/analytics/overview")
    assert resp.status_code == 200
    body = resp.json()
    dumped = str(body).lower()
    for banned in ("synthetic", "synthetic_patient", "synthetic_encounter"):
        assert banned not in dumped
    # The real dashboard's own honesty note must still be exactly as strict.
    assert "no patient or encounter volume shown anywhere on this page" in body["data_honesty_note"]


def test_top_conditions_national_returns_real_terms_ranked_by_encounters():
    rows = pop.top_conditions_national(5)
    assert len(rows) <= 5
    assert all(rows[i]["encounters"] >= rows[i + 1]["encounters"] for i in range(len(rows) - 1))
    for r in rows:
        assert r["display"] != r["namaste_code"], "expected a real term, not a bare code fallback"


def test_top_conditions_by_region_respects_limit_per_region():
    rows = pop.top_conditions_by_region(limit_per_region=3)
    assert rows
    for r in rows:
        assert len(r["top_conditions"]) <= 3
        encounters = [c["encounters"] for c in r["top_conditions"]]
        assert encounters == sorted(encounters, reverse=True)


def test_full_payload_includes_condition_breakdowns():
    resp = client.get("/api/analytics/population-demo")
    body = resp.json()
    assert "top_conditions_national" in body
    assert "top_conditions_by_region" in body
    assert len(body["top_conditions_national"]) > 0


def test_condition_codes_are_real_namaste_codes_not_fabricated():
    """The disease/code identity itself must be real data, only the encounter count is synthetic."""
    import sqlite3
    rows = pop.top_conditions_national(10)
    conn = sqlite3.connect(pop.DB_PATH)
    cur = conn.cursor()
    table_by_tradition = {"Ayurveda": ("nam", "namc_code"), "Siddha": ("nsm", "namc_code"), "Unani": ("num", "numc_code")}
    for r in rows:
        table, code_col = table_by_tradition[r["tradition"]]
        cur.execute(f"SELECT 1 FROM {table} WHERE {code_col} = ? LIMIT 1", (r["namaste_code"],))
        assert cur.fetchone() is not None
    conn.close()
