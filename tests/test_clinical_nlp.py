"""
Tests for the human clinical-text -> terminology candidate assistant
(app/clinical_nlp.py, app/clinical_text_router.py).

The load-bearing constraint this whole module exists to enforce: a symptom
must never be silently promoted to a diagnosis, and a negated symptom must
never be searched or presented as a candidate. Every test here traces back
to one of the worked examples in the platform strategy document.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app import clinical_nlp
from app.main import app

client = TestClient(app)


# ── Extraction correctness ────────────────────────────────────────────────
def test_simple_symptom_detected():
    result = clinical_nlp.extract("Patient has cough.")
    assert len(result) == 1
    assert result[0]["symptom"] == "cough"
    assert result[0]["negated"] is False


def test_duration_extracted():
    result = clinical_nlp.extract("Patient has fever and productive cough for 5 days.")
    by_symptom = {r["symptom"]: r for r in result}
    assert by_symptom["cough"]["duration"] == "5 days"
    assert by_symptom["fever"]["negated"] is False


def test_negation_scoped_to_its_own_clause_not_the_whole_sentence():
    """
    The exact case from the platform strategy doc: "no fever but has cough"
    must negate ONLY fever. Before the clause-splitting/word-window fix,
    the negation cue "no" incorrectly reached across "but" and negated
    both symptoms.
    """
    result = clinical_nlp.extract("Patient has no fever but has cough for 5 days.")
    by_symptom = {r["symptom"]: r for r in result}
    assert by_symptom["fever"]["negated"] is True
    assert by_symptom["cough"]["negated"] is False
    assert by_symptom["cough"]["duration"] == "5 days"


def test_denies_cue_negates_correctly():
    result = clinical_nlp.extract("Patient denies chest pain.")
    assert result[0]["negated"] is True
    assert result[0]["body_site"] == "chest"


def test_body_site_and_laterality_extracted():
    result = clinical_nlp.extract("Patient complains of lower back pain radiating to right leg.")
    pain = next(r for r in result if r["symptom"] == "pain")
    assert pain["body_site"] == "lower back"
    assert pain["laterality"] == "right"
    assert pain["negated"] is False


def test_no_symptom_recognised_returns_empty_not_error():
    assert clinical_nlp.extract("Patient reports feeling generally okay today.") == []


def test_empty_text_returns_empty():
    assert clinical_nlp.extract("") == []
    assert clinical_nlp.extract("   ") == []


# ── The safety contract ───────────────────────────────────────────────────
def test_response_never_contains_a_diagnosis_field():
    body = clinical_nlp.build_candidates("Patient has fever and productive cough for 5 days.")
    assert body["diagnosis_inferred"] is False
    assert body["requires_clinician_confirmation"] is True
    dumped = str(body).lower()
    for banned in ("likely_diagnosis", "\"diagnosis\":", "'diagnosis':"):
        assert banned not in dumped


def test_negated_symptom_is_never_searched():
    body = clinical_nlp.build_candidates("Patient has no fever but has cough for 5 days.")
    negated = {s["symptom"]: s for s in body["negated_symptoms"]}
    assert "fever" in negated
    assert negated["fever"]["searched"] is False
    assert negated["fever"]["candidates"] == []

    detected = {s["symptom"]: s for s in body["detected_symptoms"]}
    assert "cough" in detected
    assert detected["cough"]["searched"] is True


def test_detected_symptom_gets_real_terminology_candidates():
    body = clinical_nlp.build_candidates("Patient has cough.")
    cough = body["detected_symptoms"][0]
    assert cough["candidates"], "expected real search hits for a common symptom term"
    for c in cough["candidates"]:
        assert "code" in c and "display" in c and "system" in c


def test_burning_urination_example_from_master_prompt():
    body = clinical_nlp.build_candidates("Patient reports burning sensation during urination.")
    assert any(s["symptom"] == "burning sensation" for s in body["detected_symptoms"])
    assert body["diagnosis_inferred"] is False


# ── API surface ────────────────────────────────────────────────────────────
def test_extract_endpoint():
    resp = client.post("/api/v1/clinical-text/extract", json={"text": "Patient has cough."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["diagnosis_inferred"] is False
    assert body["extracted"][0]["symptom"] == "cough"


def test_candidates_endpoint_full_pipeline():
    resp = client.post(
        "/api/v1/clinical-text/candidates",
        json={"text": "Patient has fever and productive cough for 5 days."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["diagnosis_inferred"] is False
    assert len(body["detected_symptoms"]) == 2


def test_candidates_endpoint_rejects_empty_text():
    resp = client.post("/api/v1/clinical-text/candidates", json={"text": ""})
    assert resp.status_code == 422


def test_candidates_endpoint_rejects_oversized_text():
    resp = client.post("/api/v1/clinical-text/candidates", json={"text": "a" * 3000})
    assert resp.status_code == 422
