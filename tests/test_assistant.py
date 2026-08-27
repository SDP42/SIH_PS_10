"""
Tests for the voice/text clinical terminology assistant (app/assistant.py,
app/assistant_router.py).

Three properties matter more than the rest and each has dedicated coverage:

  1. It never invents an answer. Project questions come only from the
     controlled knowledge base; an unmatched question must decline.
  2. It never infers a diagnosis from symptoms.
  3. It never writes clinical data from a single utterance — a data-changing
     request must return a confirmation prompt, and executing it requires
     authentication.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app import assistant
from app.main import app

client = TestClient(app)


# ── Knowledge base ────────────────────────────────────────────────────────
def test_knowledge_base_loads_and_has_entries():
    entries = assistant.load_knowledge_base(force=True)
    assert len(entries) > 0
    for e in entries:
        assert e["question"] and e["answer"]


def test_exact_question_match_returns_full_confidence():
    entry, conf = assistant.match_knowledge_base("What is NAMASTE?")
    assert entry is not None
    assert conf == 1.0
    assert "NAMASTE" in entry["answer"]


def test_keyword_match_works_for_paraphrased_question():
    entry, conf = assistant.match_knowledge_base("tell me about dual coding")
    assert entry is not None
    assert conf >= assistant.KB_CONFIDENCE_FLOOR
    assert "dual coding" in entry["answer"].lower()


def test_answer_is_returned_verbatim_from_the_knowledge_base():
    """The assistant must not paraphrase — the stored answer is the answer."""
    entries = assistant.load_knowledge_base()
    target = next(e for e in entries if e["question"] == "What is TM2?")
    result = assistant.ask("What is TM2?")
    assert result["answer"] == target["answer"]
    assert result["source"] == "knowledge_base"


# ── The non-hallucination guarantee ───────────────────────────────────────
def test_out_of_scope_question_declines_rather_than_inventing():
    result = assistant.ask("What is the capital of France?")
    assert result["intent"] == assistant.INTENT_UNKNOWN
    assert result["answer"] == assistant.FALLBACK_ANSWER
    assert "suggestion" in result


def test_declined_answer_offers_topics_it_does_cover():
    result = assistant.ask("explain quantum entanglement to me")
    assert result["intent"] == assistant.INTENT_UNKNOWN
    assert "NAMASTE" in result["suggestion"]


def test_empty_input_is_handled_gracefully():
    result = assistant.ask("")
    assert result["intent"] == assistant.INTENT_UNKNOWN
    assert result["requires_confirmation"] is False


# ── Intent detection ──────────────────────────────────────────────────────
@pytest.mark.parametrize("text,expected", [
    ("What is NAMASTE?", assistant.INTENT_PROJECT_FAQ),
    ("Search Gridhrasi", assistant.INTENT_TERMINOLOGY_SEARCH),
    ("find the namaste code for fever", assistant.INTENT_TERMINOLOGY_SEARCH),
    ("show the mapping for AA-1", assistant.INTENT_TRANSLATE_MAPPING),
    ("show the TM2 mapping for EC-7", assistant.INTENT_TRANSLATE_MAPPING),
    ("validate code AA-1", assistant.INTENT_VALIDATE_CODE),
    ("Patient has cough", assistant.INTENT_CLINICAL_TEXT),
    ("add this to the problem list", assistant.INTENT_CREATE_CONDITION),
])
def test_intent_detection(text, expected):
    assert assistant.detect_intent(text)["intent"] == expected


def test_clinical_narrative_is_not_mistaken_for_a_search():
    """"Patient has cough" must not be read as a request to search "patient"."""
    detected = assistant.detect_intent("Patient has lower back pain radiating to the right leg")
    assert detected["intent"] == assistant.INTENT_CLINICAL_TEXT


def test_code_casing_is_preserved_through_intent_detection():
    """
    Terminology codes are case-sensitive. Patterns match against a lowercased
    copy, so the subject must be sliced from the original string — otherwise
    "EB-10.18" becomes "eb-10.18" and never resolves.
    """
    assert assistant.detect_intent("show the mapping for EB-10.18")["subject"] == "EB-10.18"
    assert assistant.detect_intent("validate code AA-1")["subject"] == "AA-1"


# ── Terminology delegation ────────────────────────────────────────────────
def test_search_delegates_and_returns_real_results():
    result = assistant.ask("search fever")
    assert result["intent"] == assistant.INTENT_TERMINOLOGY_SEARCH
    assert result["source"] == "terminology_engine"
    assert "results" in result["data"]


def test_translate_returns_real_dual_coding():
    result = assistant.ask("show the mapping for EC-7")
    assert result["intent"] == assistant.INTENT_TRANSLATE_MAPPING
    mappings = result["data"].get("mappings", [])
    assert mappings, "expected at least one mapping group"
    assert {m["target_system"] for m in mappings} & {"ICD-11 TM2", "ICD-11 Biomedicine"}


def test_translate_surfaces_no_validated_equivalent_honestly():
    """A refusal from the mapping engine must reach the user, not be hidden."""
    result = assistant.ask("show the mapping for EB-10.18")
    mappings = result["data"].get("mappings", [])
    unmatched = [m for m in mappings if m["equivalence"] == "unmatched"]
    if unmatched:
        assert "no validated equivalent" in result["answer"].lower()


def test_validate_confirms_a_real_code():
    result = assistant.ask("validate code AA-1")
    assert result["data"]["valid"] is True
    assert result["data"]["system"] == "NAM"


def test_validate_rejects_a_fake_code():
    result = assistant.ask("validate code TOTALLY-FAKE-9999")
    assert result["data"]["valid"] is False


def test_phonetic_fallback_resolves_spoken_transliteration():
    """
    Speech-to-text produces "Gridhrasi"; the corpus stores "gRudhrasI".
    The fallback should find it and explicitly ask the user to confirm
    rather than silently assuming the match is correct.
    """
    result = assistant.ask("Search Gridhrasi")
    assert result["data"].get("matched_by") == "phonetic"
    assert "confirm" in result["answer"].lower()


# ── Clinical safety ───────────────────────────────────────────────────────
def test_symptom_is_never_promoted_to_a_diagnosis():
    result = assistant.ask("Patient has cough")
    answer = result["answer"].lower()
    assert "cannot infer a definitive diagnosis" in answer
    for disease in ("pneumonia", "bronchitis", "tuberculosis", "asthma"):
        assert disease not in answer


def test_negated_symptom_is_reported_as_absent():
    result = assistant.ask("Patient has no fever but has cough for 5 days")
    assert "not present" in result["answer"].lower()
    negated = {s["symptom"] for s in result["data"]["negated_symptoms"]}
    assert "fever" in negated


def test_clinical_response_never_contains_a_diagnosis_field():
    result = assistant.ask("Patient has fever and productive cough")
    assert result["data"]["diagnosis_inferred"] is False
    assert result["data"]["requires_clinician_confirmation"] is True


# ── Confirmation flow for data-changing actions ───────────────────────────
def test_create_condition_requires_confirmation_and_does_not_execute():
    result = assistant.ask("add this to the problem list", context_code="EC-7")
    assert result["intent"] == assistant.INTENT_CREATE_CONDITION
    assert result["requires_confirmation"] is True
    assert result["pending_action"]["action"] == "SAVE_CONDITION"
    # The preview exists, but nothing has been saved yet.
    assert "preview" in result["data"]


def test_confirm_endpoint_requires_authentication():
    prepared = assistant.ask("add this to the problem list", context_code="EC-7")
    resp = client.post("/api/v1/assistant/confirm", json={"action": prepared["pending_action"]})
    assert resp.status_code == 401


def test_confirm_executes_only_after_explicit_confirmation(demo_auth_headers):
    prepared = assistant.ask("add this to the problem list", context_code="EC-7")
    resp = client.post(
        "/api/v1/assistant/confirm",
        json={"action": prepared["pending_action"]},
        headers=demo_auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["executed"] is True
    assert body["data"]["condition"]["resourceType"] == "Condition"


def test_confirm_rejects_an_unknown_action(demo_auth_headers):
    resp = client.post(
        "/api/v1/assistant/confirm",
        json={"action": {"action": "DELETE_EVERYTHING"}},
        headers=demo_auth_headers,
    )
    assert resp.status_code == 400


def test_confirmed_action_is_written_to_the_audit_trail(demo_auth_headers):
    prepared = assistant.ask("add this to the problem list", context_code="EC-7")
    client.post("/api/v1/assistant/confirm", json={"action": prepared["pending_action"]}, headers=demo_auth_headers)
    events = client.get("/api/audit/recent", params={"limit": 20}).json()["events"]
    assert any(e["action"] == "ASSISTANT_CONDITION_CONFIRMED" for e in events)


# ── HTTP surface ──────────────────────────────────────────────────────────
def test_ask_endpoint_works_for_typed_input():
    resp = client.post("/api/v1/assistant/ask", json={"text": "What is FHIR?"})
    assert resp.status_code == 200
    assert resp.json()["source"] == "knowledge_base"


def test_ask_endpoint_rejects_empty_text():
    assert client.post("/api/v1/assistant/ask", json={"text": ""}).status_code == 422


def test_ask_endpoint_rejects_oversized_text():
    assert client.post("/api/v1/assistant/ask", json={"text": "a" * 2000}).status_code == 422


def test_capabilities_endpoint_lists_what_it_can_answer():
    body = client.get("/api/v1/assistant/capabilities").json()
    assert body["knowledge_base_entries"] > 0
    assert body["example_commands"]
    assert "never infers a diagnosis" in body["safety_note"]


def test_knowledge_base_reload_requires_auth():
    assert client.post("/api/v1/assistant/reload-knowledge-base").status_code == 401


def test_knowledge_base_reload_works_with_auth(demo_auth_headers):
    resp = client.post("/api/v1/assistant/reload-knowledge-base", headers=demo_auth_headers)
    assert resp.status_code == 200
    assert resp.json()["reloaded"] is True
