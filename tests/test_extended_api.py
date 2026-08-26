#!/usr/bin/env python3
"""
Extended API test suite for the AYUSH Nexus backend.
Covers every /api/* route added in app/api.py that the frontend consumes.

Run with:
    pytest tests/test_extended_api.py -v
    pytest tests/ -v          # run all test files together
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def get_first_mapping_id() -> int:
    """Return the id of the first mapping in the database."""
    r = client.get("/api/mappings", params={"page_size": 1})
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) > 0, "Database has no mappings – cannot run detail tests"
    return results[0]["id"]


def get_first_namaste_code() -> str:
    """Return the first NAMASTE source code found in mappings."""
    r = client.get("/api/mappings", params={"page_size": 1})
    return r.json()["results"][0]["source_code"]


def get_first_icd11_code() -> str:
    """Return the first ICD-11 target code found in mappings."""
    r = client.get("/api/mappings", params={"page_size": 1})
    return r.json()["results"][0]["target_code"]


# ─────────────────────────────────────────────
#  /api/stats
# ─────────────────────────────────────────────

class TestStats:
    """Tests for GET /api/stats — the Overview dashboard datasource."""

    def test_stats_returns_200(self):
        r = client.get("/api/stats")
        assert r.status_code == 200

    def test_stats_has_required_keys(self):
        data = client.get("/api/stats").json()
        required = [
            "namaste_concepts", "icd11_concepts",
            "total_mappings", "validated_mappings",
            "related_mappings", "mapped_namaste_codes",
            "mapped_icd11_codes", "terminologies",
        ]
        for key in required:
            assert key in data, f"Missing key: {key}"

    def test_stats_counts_are_positive_integers(self):
        data = client.get("/api/stats").json()
        int_fields = [
            "namaste_concepts", "icd11_concepts", "total_mappings",
            "validated_mappings", "related_mappings",
            "mapped_namaste_codes", "mapped_icd11_codes",
        ]
        for field in int_fields:
            assert isinstance(data[field], int) and data[field] >= 0, \
                f"{field} should be a non-negative integer"

    def test_stats_mapping_counts_add_up(self):
        """validated + related must equal total_mappings."""
        d = client.get("/api/stats").json()
        assert d["validated_mappings"] + d["related_mappings"] == d["total_mappings"], \
            "validated + related should equal total_mappings"

    def test_stats_terminologies_structure(self):
        terms = client.get("/api/stats").json()["terminologies"]
        assert isinstance(terms, list) and len(terms) == 2, \
            "Should return exactly 2 terminology entries"
        for t in terms:
            for key in ("id", "name", "full_name", "version", "status", "concept_count", "source"):
                assert key in t, f"Terminology entry missing key: {key}"
            assert t["status"] == "active"

    def test_stats_known_data_volume(self):
        """Verify real-world data counts match the known dataset size."""
        d = client.get("/api/stats").json()
        assert d["namaste_concepts"] == 2910, "Expected 2910 NAMASTE concepts"
        assert d["icd11_concepts"] == 36782, "Expected 36782 ICD-11 concepts"
        assert d["total_mappings"] == 468, "Expected 468 total mappings"


# ─────────────────────────────────────────────
#  /api/terminologies
# ─────────────────────────────────────────────

class TestTerminologies:
    """Tests for GET /api/terminologies."""

    def test_terminologies_returns_200(self):
        assert client.get("/api/terminologies").status_code == 200

    def test_terminologies_returns_list(self):
        data = client.get("/api/terminologies").json()
        assert isinstance(data, list)

    def test_terminologies_has_namaste_and_icd11(self):
        data = client.get("/api/terminologies").json()
        ids = {t["id"] for t in data}
        assert "namaste" in ids
        assert "icd11" in ids

    def test_terminologies_full_name_present(self):
        data = client.get("/api/terminologies").json()
        for t in data:
            assert "full_name" in t and len(t["full_name"]) > 5, \
                f"full_name missing or too short for {t['id']}"

    def test_terminologies_have_source_url(self):
        data = client.get("/api/terminologies").json()
        for t in data:
            assert "url" in t and t["url"].startswith("http"), \
                f"Expected an http URL for {t['id']}"

    def test_terminologies_concept_counts_positive(self):
        data = client.get("/api/terminologies").json()
        for t in data:
            assert t["concept_count"] > 0, \
                f"concept_count for {t['id']} must be > 0"


# ─────────────────────────────────────────────
#  /api/concepts
# ─────────────────────────────────────────────

class TestConcepts:
    """Tests for GET /api/concepts — Terminology Explorer datasource."""

    def test_concepts_default_returns_200(self):
        assert client.get("/api/concepts").status_code == 200

    def test_concepts_pagination_shape(self):
        data = client.get("/api/concepts", params={"page": 1, "page_size": 10}).json()
        for key in ("total", "page", "page_size", "total_pages", "results"):
            assert key in data

    def test_concepts_respects_page_size(self):
        data = client.get("/api/concepts", params={"page_size": 5}).json()
        assert len(data["results"]) <= 5

    def test_concepts_namaste_system(self):
        data = client.get("/api/concepts", params={"system": "namaste", "page_size": 5}).json()
        for r in data["results"]:
            assert r["system_id"] == "namaste"
            assert "code" in r and "display" in r

    def test_concepts_icd11_system(self):
        data = client.get("/api/concepts", params={"system": "icd11", "page_size": 5}).json()
        for r in data["results"]:
            assert r["system_id"] == "icd11"

    def test_concepts_total_pages_calculated_correctly(self):
        data = client.get("/api/concepts", params={"page_size": 10}).json()
        import math
        expected = math.ceil(data["total"] / 10)
        assert data["total_pages"] == expected

    def test_concepts_search_namaste(self):
        """Searching for 'Vata' should return NAMASTE results."""
        data = client.get("/api/concepts", params={"system": "namaste", "q": "Vata"}).json()
        # May be 0 if FTS table not populated, but should not error
        assert isinstance(data["results"], list)

    def test_concepts_search_icd11(self):
        """Searching for 'fever' should return ICD-11 results."""
        data = client.get("/api/concepts", params={"system": "icd11", "q": "fever"}).json()
        assert isinstance(data["results"], list)

    def test_concepts_page_out_of_bounds_returns_empty(self):
        """A very large page number should return an empty result set gracefully."""
        data = client.get("/api/concepts", params={"page": 99999, "page_size": 20}).json()
        assert data["results"] == []

    def test_concepts_results_have_code_and_display(self):
        data = client.get("/api/concepts", params={"page_size": 20}).json()
        valid_rows = [r for r in data["results"] if r.get("code") is not None]
        # At least some rows should have codes
        assert len(valid_rows) > 0, "All concept rows have null codes — DB issue"
        for r in valid_rows:
            assert r["code"], "code must be non-empty string"
            assert r.get("display"), "display must be non-empty"



# ─────────────────────────────────────────────
#  /api/search
# ─────────────────────────────────────────────

class TestSearch:
    """Tests for GET /api/search — unified cross-system search."""

    def test_search_requires_query(self):
        """Missing q param should return 422 Unprocessable Entity."""
        r = client.get("/api/search")
        assert r.status_code == 422

    def test_search_empty_query_rejected(self):
        """q='' is shorter than min_length=1, expect 422."""
        r = client.get("/api/search", params={"q": ""})
        assert r.status_code == 422

    def test_search_valid_query_returns_200(self):
        r = client.get("/api/search", params={"q": "fever"})
        assert r.status_code == 200

    def test_search_response_shape(self):
        data = client.get("/api/search", params={"q": "pain"}).json()
        for key in ("query", "total", "namaste_count", "icd11_count", "results"):
            assert key in data

    def test_search_query_echoed_back(self):
        data = client.get("/api/search", params={"q": "diabetes"}).json()
        assert data["query"] == "diabetes"

    def test_search_count_consistency(self):
        """namaste_count + icd11_count == len(results)."""
        data = client.get("/api/search", params={"q": "pain"}).json()
        assert data["namaste_count"] + data["icd11_count"] == len(data["results"])

    def test_search_system_filter_namaste(self):
        data = client.get("/api/search", params={"q": "Vata", "system": "namaste"}).json()
        for r in data["results"]:
            assert r["system_id"] == "namaste"

    def test_search_system_filter_icd11(self):
        data = client.get("/api/search", params={"q": "fever", "system": "icd11"}).json()
        for r in data["results"]:
            assert r["system_id"] == "icd11"

    def test_search_icd11_returns_real_matches_not_silently_empty(self):
        """
        Regression guard: SQLite 3.35+ rejects `MATCH` against an FTS5
        table's alias ("WHERE f MATCH ?" where `f` aliases icd11_fts),
        raising OperationalError — which the endpoint's bare except then
        silently swallowed into an empty result list. Every ICD-11 search
        was returning zero hits without ever surfacing an error. A plain
        200-with-possibly-empty-list assertion can't catch that; this
        asserts a well-known ICD-11 term actually resolves to real codes.
        """
        data = client.get("/api/search", params={"q": "cough", "system": "icd11"}).json()
        assert data["icd11_count"] > 0
        assert any("cough" in r["display"].lower() for r in data["results"])

    def test_search_no_results_for_gibberish(self):
        data = client.get("/api/search", params={"q": "xyzxyzxyznonexistent123"}).json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_search_results_have_required_fields(self):
        data = client.get("/api/search", params={"q": "pain"}).json()
        for r in data["results"]:
            assert "code" in r
            assert "display" in r
            assert "system_id" in r


# ─────────────────────────────────────────────
#  /api/mappings
# ─────────────────────────────────────────────

class TestMappings:
    """Tests for GET /api/mappings — Mapping Intelligence table."""

    def test_mappings_returns_200(self):
        assert client.get("/api/mappings").status_code == 200

    def test_mappings_pagination_shape(self):
        data = client.get("/api/mappings").json()
        for key in ("total", "page", "page_size", "total_pages", "results"):
            assert key in data

    def test_mappings_default_page_size(self):
        data = client.get("/api/mappings").json()
        assert len(data["results"]) <= 20

    def test_mappings_custom_page_size(self):
        data = client.get("/api/mappings", params={"page_size": 5}).json()
        assert len(data["results"]) == 5

    def test_mappings_result_fields(self):
        data = client.get("/api/mappings", params={"page_size": 3}).json()
        required = [
            "id", "source_system", "source_code", "source_display",
            "target_system", "target_code", "target_display",
            "equivalence", "confidence",
        ]
        for m in data["results"]:
            for field in required:
                assert field in m, f"Mapping missing field: {field}"

    def test_mappings_confidence_range(self):
        """Confidence must be None (embeddings unavailable) or between 0 and 1 — never out of range."""
        data = client.get("/api/mappings", params={"page_size": 20}).json()
        for m in data["results"]:
            if m["confidence"] is not None:
                assert 0.0 <= m["confidence"] <= 1.0, \
                    f"Confidence out of range: {m['confidence']}"

    def test_mappings_equivalence_values(self):
        """Only 'equivalent' and 'relatedto' should appear."""
        data = client.get("/api/mappings", params={"page_size": 50}).json()
        valid = {"equivalent", "relatedto"}
        for m in data["results"]:
            assert m["equivalence"] in valid, \
                f"Unexpected equivalence: {m['equivalence']}"

    def test_mappings_filter_by_equivalence_equivalent(self):
        data = client.get("/api/mappings", params={"equivalence": "equivalent", "page_size": 10}).json()
        for m in data["results"]:
            assert m["equivalence"] == "equivalent"

    def test_mappings_filter_by_equivalence_relatedto(self):
        data = client.get("/api/mappings", params={"equivalence": "relatedto", "page_size": 10}).json()
        for m in data["results"]:
            assert m["equivalence"] == "relatedto"

    def test_mappings_filter_by_source_code(self):
        code = get_first_namaste_code()
        data = client.get("/api/mappings", params={"source_code": code}).json()
        assert data["total"] > 0, f"No mappings found for source_code={code}"
        for m in data["results"]:
            assert m["source_code"] == code

    def test_mappings_filter_by_target_code(self):
        code = get_first_icd11_code()
        data = client.get("/api/mappings", params={"target_code": code}).json()
        assert data["total"] >= 0  # some codes may have only one mapping

    def test_mappings_search_query(self):
        data = client.get("/api/mappings", params={"q": "vata"}).json()
        assert isinstance(data["results"], list)

    def test_mappings_invalid_equivalence_returns_no_results(self):
        data = client.get("/api/mappings", params={"equivalence": "nonexistent"}).json()
        assert data["total"] == 0

    def test_mappings_total_matches_known_count(self):
        """Unfiltered total should equal 468 (our dataset)."""
        data = client.get("/api/mappings", params={"page_size": 1}).json()
        assert data["total"] == 468, f"Expected 468, got {data['total']}"

    def test_mappings_pagination_second_page(self):
        p1 = client.get("/api/mappings", params={"page": 1, "page_size": 5}).json()
        p2 = client.get("/api/mappings", params={"page": 2, "page_size": 5}).json()
        ids_p1 = {m["id"] for m in p1["results"]}
        ids_p2 = {m["id"] for m in p2["results"]}
        assert ids_p1.isdisjoint(ids_p2), "Pages must not share records"


# ─────────────────────────────────────────────
#  /api/mappings/{id}
# ─────────────────────────────────────────────

class TestMappingDetail:
    """Tests for GET /api/mappings/{id}."""

    def test_mapping_detail_valid_id_returns_200(self):
        mid = get_first_mapping_id()
        assert client.get(f"/api/mappings/{mid}").status_code == 200

    def test_mapping_detail_fields(self):
        mid = get_first_mapping_id()
        data = client.get(f"/api/mappings/{mid}").json()
        required = [
            "id", "source_system", "source_code", "source_display",
            "target_system", "target_code", "target_display",
            "equivalence", "confidence", "status", "version",
        ]
        for field in required:
            assert field in data, f"Detail missing field: {field}"

    def test_mapping_detail_id_matches(self):
        mid = get_first_mapping_id()
        data = client.get(f"/api/mappings/{mid}").json()
        assert data["id"] == mid

    def test_mapping_detail_status_values(self):
        mid = get_first_mapping_id()
        data = client.get(f"/api/mappings/{mid}").json()
        assert data["status"] in ("validated", "review"), \
            f"Unexpected status: {data['status']}"

    def test_mapping_detail_version_format(self):
        mid = get_first_mapping_id()
        data = client.get(f"/api/mappings/{mid}").json()
        # Should look like "1.0.0"
        parts = data["version"].split(".")
        assert len(parts) == 3 and all(p.isdigit() for p in parts), \
            f"Unexpected version format: {data['version']}"

    def test_mapping_detail_not_found_returns_404(self):
        r = client.get("/api/mappings/99999999")
        assert r.status_code == 404

    def test_mapping_detail_404_has_detail_message(self):
        r = client.get("/api/mappings/99999999")
        assert "detail" in r.json()

    def test_mapping_detail_confidence_in_range(self):
        mid = get_first_mapping_id()
        data = client.get(f"/api/mappings/{mid}").json()
        # None is a valid, honest answer when the AI embeddings aren't built —
        # never a fake fallback number — but this environment has them built.
        assert data["confidence"] is not None, "AI embeddings not built — run scripts/build_embeddings.py"
        assert 0.0 <= data["confidence"] <= 1.0

    def test_mapping_detail_confidence_is_backend_computed_not_a_constant(self):
        """
        Confidence must be real, per-pair embedding similarity, not the old
        hardcoded 0.98-for-equivalent / 0.72-for-relatedto constants — assert
        real variance across distinct equivalent mappings.
        """
        data = client.get("/api/mappings", params={"equivalence": "equivalent", "page_size": 15}).json()
        confidences = {m["confidence"] for m in data["results"] if m["confidence"] is not None}
        assert len(confidences) > 1, "All confidences identical — looks like a hardcoded constant, not a real score"
        assert confidences != {0.98}, "Confidence is still the old hardcoded constant"

    def test_mapping_detail_confidence_matches_ai_engine_score_pair(self):
        """The API's confidence must equal app.ai_mapping.score_pair's combined_score for the same pair."""
        from app import ai_mapping
        mid = get_first_mapping_id()
        detail = client.get(f"/api/mappings/{mid}").json()
        expected = ai_mapping.score_pair(detail["source_code"], detail["target_code"])
        assert expected is not None
        assert detail["confidence"] == expected["combined_score"]


# ─────────────────────────────────────────────
#  /api/concept/{system}/{code}
# ─────────────────────────────────────────────

class TestConceptLookup:
    """Tests for GET /api/concept/{system}/{code}."""

    def test_namaste_concept_lookup_valid(self):
        code = get_first_namaste_code()
        r = client.get(f"/api/concept/namaste/{code}")
        assert r.status_code == 200

    def test_namaste_concept_fields(self):
        code = get_first_namaste_code()
        data = client.get(f"/api/concept/namaste/{code}").json()
        for field in ("code", "display", "system", "system_id", "mappings"):
            assert field in data, f"NAMASTE concept missing: {field}"
        assert data["system_id"] == "namaste"

    def test_namaste_concept_has_mappings_list(self):
        code = get_first_namaste_code()
        data = client.get(f"/api/concept/namaste/{code}").json()
        assert isinstance(data["mappings"], list)
        # This specific code has at least one mapping (we got it from the mappings table)
        assert len(data["mappings"]) > 0

    def test_icd11_concept_lookup_valid(self):
        code = get_first_icd11_code()
        import urllib.parse
        encoded = urllib.parse.quote(code, safe="")
        r = client.get(f"/api/concept/icd11/{encoded}")
        assert r.status_code == 200

    def test_icd11_concept_fields(self):
        code = get_first_icd11_code()
        import urllib.parse
        encoded = urllib.parse.quote(code, safe="")
        data = client.get(f"/api/concept/icd11/{encoded}").json()
        for field in ("code", "display", "system", "system_id", "mappings"):
            assert field in data
        assert data["system_id"] == "icd11"

    def test_concept_lookup_invalid_code_returns_404(self):
        r = client.get("/api/concept/namaste/INVALID_CODE_XYZ123")
        assert r.status_code == 404

    def test_concept_lookup_invalid_system_returns_400(self):
        r = client.get("/api/concept/ayush/SOMEVALUE")
        assert r.status_code == 400

    def test_concept_lookup_404_has_detail(self):
        r = client.get("/api/concept/namaste/DOESNOTEXIST")
        assert "detail" in r.json()


# ─────────────────────────────────────────────
#  Performance / non-functional tests
# ─────────────────────────────────────────────

class TestPerformance:
    """Non-functional tests: response time, payload size, idempotency."""

    def test_stats_responds_fast(self):
        import time
        start = time.time()
        r = client.get("/api/stats")
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 3.0, f"Stats too slow: {elapsed:.2f}s"

    def test_mappings_responds_fast(self):
        import time
        start = time.time()
        r = client.get("/api/mappings", params={"page_size": 20})
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 3.0, f"Mappings too slow: {elapsed:.2f}s"

    def test_search_responds_fast(self):
        import time
        start = time.time()
        r = client.get("/api/search", params={"q": "pain"})
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 3.0, f"Search too slow: {elapsed:.2f}s"

    def test_stats_idempotent(self):
        """Same stats should be returned on two consecutive calls."""
        r1 = client.get("/api/stats").json()
        r2 = client.get("/api/stats").json()
        assert r1["total_mappings"] == r2["total_mappings"]
        assert r1["namaste_concepts"] == r2["namaste_concepts"]

    def test_mappings_page1_idempotent(self):
        """Calling page 1 twice should give the same IDs."""
        d1 = client.get("/api/mappings", params={"page": 1, "page_size": 10}).json()
        d2 = client.get("/api/mappings", params={"page": 1, "page_size": 10}).json()
        ids1 = [m["id"] for m in d1["results"]]
        ids2 = [m["id"] for m in d2["results"]]
        assert ids1 == ids2


# ─────────────────────────────────────────────
#  Edge / boundary cases
# ─────────────────────────────────────────────

class TestEdgeCases:
    """Boundary, injection, and encoding edge cases."""

    def test_page_size_max_enforced(self):
        """page_size > 100 should be rejected (422) per API validation."""
        r = client.get("/api/concepts", params={"page_size": 999})
        assert r.status_code == 422

    def test_page_size_zero_rejected(self):
        r = client.get("/api/concepts", params={"page_size": 0})
        assert r.status_code == 422

    def test_page_zero_rejected(self):
        r = client.get("/api/concepts", params={"page": 0})
        assert r.status_code == 422

    def test_search_with_sql_injection_attempt(self):
        """SQL injection strings must not crash the server."""
        r = client.get("/api/search", params={"q": "' OR '1'='1"})
        assert r.status_code == 200  # handled gracefully

    def test_search_with_special_chars(self):
        """Unicode and special chars in query must not crash the server."""
        r = client.get("/api/search", params={"q": "āyurveda"})
        assert r.status_code == 200

    def test_mappings_q_with_special_chars(self):
        r = client.get("/api/mappings", params={"q": "vāta"})
        assert r.status_code == 200

    def test_concept_lookup_url_encoded_code(self):
        """Codes with spaces (URL-encoded as %20) should be handled correctly."""
        code = get_first_namaste_code()
        import urllib.parse
        encoded = urllib.parse.quote(code)
        r = client.get(f"/api/concept/namaste/{encoded}")
        # Either 200 (found) or 404 (not found) — must not be 500
        assert r.status_code in (200, 404)

    def test_concepts_page_size_100_allowed(self):
        """Max allowed page_size is 100."""
        r = client.get("/api/concepts", params={"page_size": 100})
        assert r.status_code == 200

    def test_mappings_page_size_100_allowed(self):
        r = client.get("/api/mappings", params={"page_size": 100})
        assert r.status_code == 200


# ─────────────────────────────────────────────
#  CORS headers (for frontend integration)
# ─────────────────────────────────────────────

class TestCORS:
    """Verify CORS headers allow the Vite dev server at localhost:5173."""

    def test_cors_header_on_stats(self):
        r = client.get(
            "/api/stats",
            headers={"Origin": "http://localhost:5173"},
        )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") in (
            "http://localhost:5173", "*"
        ), "CORS header missing or wrong for frontend origin"

    def test_cors_preflight_options(self):
        r = client.options(
            "/api/stats",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Must not return 4xx/5xx
        assert r.status_code in (200, 204)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
