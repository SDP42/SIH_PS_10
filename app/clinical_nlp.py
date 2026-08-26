"""
Human clinical-text -> terminology candidate assistant (Phase 1).

Answers "what did the clinician write?" without ever answering "what disease
does the patient have?" — that second question stays a human decision. See
the module-level SAFETY_NOTE below; every public function in this file is
built around it.

Pipeline (see docs/strategy for the full architecture):
  1. extract()     free text -> ExtractedSymptom list (symptom, negation,
                    duration, laterality, body site) — pattern/lexicon based,
                    not a model, so every extraction is auditable by reading
                    the rule that fired.
  2. normalize()    raw symptom span -> a canonical symptom label via a
                    small hand-maintained synonym table.
  3. candidates()   canonical label -> real terminology search hits across
                    NAMASTE (all three living traditions) and ICD-11, reusing
                    app.api's existing FTS5 search rather than a parallel
                    index.

Deliberately NOT built in this pass (see the roadmap): automatic FHIR
Condition/Observation generation, and a curated per-code symptom/sign/
diagnosis role table. Both are real features; shipping them without the
underlying data (a verified clinical role for each of ~19k codes doesn't
exist yet) would mean guessing structure onto codes we haven't reviewed.
Until that table exists, this module deliberately never asserts a role for
a *candidate* — only for the *text the clinician typed*, which is always
treated as reported symptoms, never a diagnosis.

SAFETY_NOTE — read before changing this file:
  This module must never produce a field that reads as a diagnosis. Its
  output vocabulary is intentionally limited to "detected symptom" and
  "possible related terminology concept, needs clinician confirmation."
  If you're tempted to add a "likely_diagnosis" field: don't — that is
  exactly the automatic symptom-to-diagnosis inference this system is
  built to refuse, per the SIH platform-strategy safety gate.
"""
import re
import sqlite3
from typing import Any, Dict, List, Optional

DB_PATH = "db/ayush_icd11_combined.db"

SAFETY_NOTE = (
    "These are patient-reported symptoms and possible related terminology matches, "
    "not a diagnosis. No disease or condition is inferred automatically from symptoms "
    "alone — a clinician must review and explicitly confirm before any of this becomes "
    "part of a clinical record."
)

# ── Negation cues ─────────────────────────────────────────────────────────
# Checked against the words immediately preceding a matched symptom span.
# Deliberately a fixed list, not a model — a negation miss here is the
# highest-cost failure mode in this whole module (recording a denied
# symptom as present), so it needs to be a rule a reviewer can read in full.
_NEGATION_CUES = [
    "no", "not", "denies", "denied", "without", "absent", "negative for",
    "no history of", "no evidence of", "ruled out", "free of",
]
_NEGATION_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in sorted(_NEGATION_CUES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# ── Duration ──────────────────────────────────────────────────────────────
_DURATION_PATTERN = re.compile(
    r"\b(?:for|since|over the (?:last|past))\s+(\d+)\s*(day|days|week|weeks|month|months|hour|hours|year|years)\b",
    re.IGNORECASE,
)

# ── Laterality ────────────────────────────────────────────────────────────
_LATERALITY_TERMS = {"left", "right", "bilateral", "both sides"}

# ── Body sites (small, common, general-medical gazetteer) ─────────────────
_BODY_SITES = [
    "lower back", "back", "chest", "abdomen", "stomach", "throat", "joint",
    "knee", "leg", "head", "eye", "ear", "skin", "shoulder", "ankle",
    "wrist", "hip", "neck", "urinary tract",
]

# ── Symptom lexicon: surface form -> canonical label ───────────────────────
# General, uncontroversial common-medical vocabulary — not a clinical claim,
# just a normalization table so "coughing"/"persistent cough"/"cough" search
# as one concept. Extend this list; do not extend the negation or safety
# logic without re-reading SAFETY_NOTE above.
_SYMPTOM_SYNONYMS: Dict[str, str] = {
    "cough": "cough", "coughing": "cough", "persistent cough": "cough",
    "productive cough": "cough", "dry cough": "cough",
    "fever": "fever", "febrile": "fever", "high temperature": "fever",
    "pain": "pain", "ache": "pain", "aching": "pain", "soreness": "pain",
    "stiffness": "stiffness", "stiff": "stiffness",
    "headache": "headache", "head pain": "headache",
    "nausea": "nausea", "nauseous": "nausea",
    "vomiting": "vomiting", "vomit": "vomiting", "throwing up": "vomiting",
    "diarrhea": "diarrhea", "diarrhoea": "diarrhea", "loose motion": "diarrhea", "loose motions": "diarrhea",
    "constipation": "constipation",
    "fatigue": "fatigue", "tiredness": "fatigue", "weakness": "fatigue", "lethargy": "fatigue",
    "dizziness": "dizziness", "giddiness": "dizziness", "vertigo": "dizziness",
    "itching": "itching", "itchiness": "itching", "pruritus": "itching",
    "rash": "rash", "skin rash": "rash",
    "swelling": "swelling", "swollen": "swelling", "edema": "swelling", "oedema": "swelling",
    "breathlessness": "breathlessness", "shortness of breath": "breathlessness", "dyspnea": "breathlessness",
    "burning sensation": "burning sensation", "burning": "burning sensation",
    "irritation": "irritation",
    "radiating pain": "radiating pain", "radiation": "radiating pain",
    "numbness": "numbness", "tingling": "numbness",
    "chills": "chills",
    "sore throat": "sore throat", "throat irritation": "sore throat",
}
# Sort surface forms longest-first so "productive cough" matches before "cough".
_SYMPTOM_TERMS_BY_LENGTH = sorted(_SYMPTOM_SYNONYMS.keys(), key=len, reverse=True)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _find_body_site(window: str) -> Optional[Dict[str, Any]]:
    lower = window.lower()
    for site in _BODY_SITES:
        if site in lower:
            laterality = next((l for l in _LATERALITY_TERMS if l in lower), None)
            return {"site": site, "laterality": laterality}
    return None


def extract(text: str) -> List[Dict[str, Any]]:
    """
    Rule-based extraction: for each recognised symptom surface form, record
    whether it's negated, its duration if stated nearby, and any body
    site/laterality found in the same sentence. Every field here is
    traceable to a specific pattern match — nothing is inferred by a model.
    """
    if not text or not text.strip():
        return []

    # Sentence/clause-level splitting keeps negation/duration/site windows
    # from leaking across unrelated clauses. "but"/"however"/etc matter here
    # specifically: "no fever but has cough" must not let "no" reach "cough".
    sentences = re.split(
        r"(?<=[.!?;])\s+|\b(?:and|but|however|although|though|yet)\b",
        text,
    )
    results: List[Dict[str, Any]] = []
    seen = set()

    for sentence in sentences:
        lower = sentence.lower()
        matched_spans: List[str] = []
        for term in _SYMPTOM_TERMS_BY_LENGTH:
            if re.search(r"\b" + re.escape(term) + r"\b", lower):
                # Skip a shorter term already covered by a longer match in this sentence
                # (e.g. don't also emit "cough" once "productive cough" matched).
                if any(term in longer and term != longer for longer in matched_spans):
                    continue
                matched_spans.append(term)

        for term in matched_spans:
            canonical = _SYMPTOM_SYNONYMS[term]
            match = re.search(r"\b" + re.escape(term) + r"\b", lower)
            start = match.start() if match else 0

            # Negation: only a cue in the immediately preceding few words counts.
            # A full-clause lookback (rather than a tight word window) is exactly
            # what let "no fever but has cough" wrongly negate "cough" too, once
            # clause-splitting on "but" wasn't yet in place — kept tight here as
            # a second, independent safeguard against that failure mode.
            preceding = lower[:start]
            preceding_words = preceding.split()[-4:]
            negated = bool(_NEGATION_PATTERN.search(" ".join(preceding_words))) if preceding_words else False

            duration_match = _DURATION_PATTERN.search(sentence)
            duration = f"{duration_match.group(1)} {duration_match.group(2)}" if duration_match else None

            site_info = _find_body_site(sentence)

            dedupe_key = (canonical, negated, duration, site_info["site"] if site_info else None)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            results.append({
                "surface_form": term,
                "symptom": canonical,
                "negated": negated,
                "duration": duration,
                "body_site": site_info["site"] if site_info else None,
                "laterality": site_info["laterality"] if site_info else None,
            })

    return results


def _search_terminology(cur, term: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Reuses the same FTS5 machinery app/api.py's /api/search already exercises."""
    from app.api import _search_namaste_traditions  # local import avoids a circular import at module load

    safe_q = term.replace('"', "").strip()
    if not safe_q:
        return []
    fts_query = f'"{safe_q}"' if " " in safe_q else f"{safe_q}*"

    namaste_hits = _search_namaste_traditions(cur, fts_query, limit, 0)

    icd11_hits = []
    try:
        cur.execute(
            """
            SELECT i.code, i.title FROM icd11_fts f
            JOIN icd11 i ON f.rowid = i.rowid
            WHERE icd11_fts MATCH ? LIMIT ?
            """,
            (fts_query, limit),
        )
        icd11_hits = [
            {"code": r["code"], "display": r["title"], "system": "ICD-11", "system_id": "icd11"}
            for r in cur.fetchall()
        ]
    except sqlite3.OperationalError:
        pass

    return (namaste_hits[:limit] + icd11_hits[:limit])


def build_candidates(text: str, limit_per_symptom: int = 5) -> Dict[str, Any]:
    """
    The end-to-end Phase 1 pipeline: extract -> normalize (folded into the
    lexicon lookup) -> search -> package for clinician review. Never returns
    a diagnosis field — see SAFETY_NOTE.
    """
    extracted = extract(text)
    conn = _conn()
    cur = conn.cursor()
    try:
        symptom_results = []
        seen_symptoms = set()
        for item in extracted:
            if item["negated"]:
                # A denied symptom is recorded (so the clinician can see it was
                # considered) but never searched — searching it would put
                # "candidate concepts" next to a symptom the patient doesn't have.
                symptom_results.append({**item, "candidates": [], "searched": False})
                continue
            if item["symptom"] in seen_symptoms:
                continue
            seen_symptoms.add(item["symptom"])
            hits = _search_terminology(cur, item["symptom"], limit_per_symptom)
            symptom_results.append({
                **item,
                "candidates": hits,
                "searched": True,
                "no_candidates_found": len(hits) == 0,
            })
    finally:
        conn.close()

    detected = [s for s in symptom_results if not s["negated"]]
    negated = [s for s in symptom_results if s["negated"]]

    return {
        "input_text": text,
        "detected_symptoms": detected,
        "negated_symptoms": negated,
        "diagnosis_inferred": False,
        "requires_clinician_confirmation": True,
        "safety_note": SAFETY_NOTE,
    }
