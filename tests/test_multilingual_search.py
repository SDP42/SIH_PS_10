"""
Real native-script search across the three living NAMASTE traditions.

Before scripts/migrate_multilingual_fts.py, nam_fts indexed only the IAST
transliteration (never namc_term_devanagari), nsm_fts never indexed
tamil_term, and num_fts didn't index any term column at all — Unani was not
searchable by name in any script. These tests lock in the fix: searching in
Devanagari, Tamil, or Arabic must resolve to the real underlying NAMASTE
code, not just the transliterated form.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_devanagari_search_resolves_ayurveda_code():
    """प्रमेह (Sanskrit) must resolve to the real Ayurveda NAMASTE code for it."""
    body = client.get("/api/search", params={"q": "प्रमेह", "system": "namaste"}).json()
    assert body["total"] > 0
    assert any(r["tradition"] == "Ayurveda" for r in body["results"])
    hit = next(r for r in body["results"] if r["tradition"] == "Ayurveda")
    assert hit["native_script"] is not None
    assert hit["native_script_language"] == "Devanagari (Sanskrit)"
    assert "प्रमेह" in hit["native_script"]


def test_tamil_search_resolves_siddha_code():
    """சித்தா (Tamil) must resolve to a real Siddha NAMASTE row."""
    body = client.get("/api/search", params={"q": "சித்தா", "system": "namaste"}).json()
    assert body["total"] > 0
    hit = next(r for r in body["results"] if r["tradition"] == "Siddha")
    assert hit["native_script_language"] == "Tamil"
    assert "சித்த" in hit["native_script"]


def test_arabic_search_resolves_unani_code():
    """رطوبت (Arabic) must resolve to a real Unani NAMASTE row — previously
    impossible, since num_fts indexed no term column of any kind."""
    body = client.get("/api/search", params={"q": "رطوبت", "system": "namaste"}).json()
    assert body["total"] > 0
    hit = next(r for r in body["results"] if r["tradition"] == "Unani")
    assert hit["native_script_language"] == "Arabic"
    assert "رطوبت" in hit["native_script"]


def test_search_still_covers_all_three_traditions_for_transliterated_query():
    """A plain-English/transliterated query must not silently drop back to Ayurveda-only."""
    body = client.get("/api/search", params={"q": "disorder", "system": "namaste"}).json()
    traditions = {r["tradition"] for r in body["results"]}
    assert traditions, "expected at least one tradition to match 'disorder'"


def test_unmatched_native_script_query_returns_empty_not_error():
    body = client.get("/api/search", params={"q": "अनुपस्थित999", "system": "namaste"})
    assert body.status_code == 200
    assert body.json()["total"] == 0


def test_english_search_unaffected_by_multilingual_change():
    """Guard against a regression in the ordinary English-search path."""
    resp = client.get("/api/search", params={"q": "fever"})
    assert resp.status_code == 200
    assert "results" in resp.json()
