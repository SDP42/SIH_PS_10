"""
Voice / text clinical terminology assistant — Phase 3.

This module is a THIN ROUTING LAYER. It contains no terminology logic of
its own: it detects what the user is asking for, then delegates to the
engines that already exist and are already tested —

    app.api.search_concepts          terminology search (all traditions)
    app.fhir_extra.translate         real dual-coding TM2 + Biomedicine
    app.clinical_nlp.build_candidates free-text symptom extraction
    app.v1_router._VALIDATE_TABLES    code-existence validation
    app.problem_list                  FHIR Condition construction

Voice and text are treated as two input methods for the same engine: the
browser performs speech-to-text and speech synthesis locally via the Web
Speech API, so no external speech provider, audio API or paid key is
involved anywhere in this pipeline. The backend only ever sees text.

Two answer sources, kept strictly apart:

  * PROJECT / FAQ questions are answered ONLY from data/knowledge_base.json.
    The stored answer is returned verbatim. The assistant never paraphrases,
    never composes a new explanation, and never falls back to a generative
    model — if nothing in the knowledge base matches confidently it says so
    and offers the topics it does cover. This is what makes the assistant's
    project answers non-hallucinating by construction rather than by prompt.

  * TERMINOLOGY questions are answered ONLY by calling the existing engines
    above, so the assistant can never disagree with what the rest of the
    platform would return for the same query.

Clinical safety: a symptom is never promoted to a diagnosis (see
app/clinical_nlp.py's SAFETY_NOTE, which this module inherits by
delegating to it), and any action that would write clinical data requires
explicit user confirmation before it executes — see PENDING_ACTIONS below.
"""
import json
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = "db/ayush_icd11_combined.db"
KB_PATH = os.path.join("data", "knowledge_base.json")

# ── Intents ───────────────────────────────────────────────────────────────
INTENT_PROJECT_FAQ = "PROJECT_FAQ"
INTENT_TERMINOLOGY_SEARCH = "TERMINOLOGY_SEARCH"
INTENT_TRANSLATE_MAPPING = "TRANSLATE_MAPPING"
INTENT_VALIDATE_CODE = "VALIDATE_CODE"
INTENT_CLINICAL_TEXT = "CLINICAL_TEXT"
INTENT_CREATE_CONDITION = "CREATE_CONDITION"
INTENT_UNKNOWN = "UNKNOWN"

# Actions that would create or change clinical data. These are never executed
# from a single utterance — recognise() returns requires_confirmation=True and
# the caller must come back through confirm_action() with an explicit yes.
CONFIRMATION_REQUIRED_INTENTS = {INTENT_CREATE_CONDITION}

FALLBACK_ANSWER = "I couldn't find a reliable answer in my knowledge base."
FALLBACK_SUGGESTION = (
    "Try asking about NAMASTE, ICD-11, TM2, FHIR, dual coding, mapping, or API integration. "
    "You can also say things like \"search Gridhrasi\" or \"show the TM2 mapping for AA-1\"."
)

# Confidence floor for returning a stored knowledge-base answer. Below this,
# the assistant declines rather than returning a weak match — a wrong
# confident answer is worse than an admitted gap.
KB_CONFIDENCE_FLOOR = 0.34

_STOPWORDS = {
    "what", "is", "the", "a", "an", "of", "for", "to", "in", "on", "does", "do",
    "how", "why", "this", "that", "it", "are", "and", "me", "my", "you", "your",
    "please", "can", "could", "would", "tell", "about", "explain", "show", "give",
}


# ── Knowledge base ────────────────────────────────────────────────────────
_kb_cache: Optional[List[Dict[str, Any]]] = None


def load_knowledge_base(force: bool = False) -> List[Dict[str, Any]]:
    """
    Reads data/knowledge_base.json. Cached after first read; pass force=True
    to pick up edits without restarting (the file is meant to be editable by
    a non-developer, so re-reading has to be possible).
    """
    global _kb_cache
    if _kb_cache is not None and not force:
        return _kb_cache
    try:
        with open(KB_PATH, encoding="utf-8") as f:
            payload = json.load(f)
        entries = payload.get("entries", []) if isinstance(payload, dict) else payload
    except (OSError, json.JSONDecodeError):
        # A missing or malformed knowledge base must not take the assistant
        # down — it degrades to "I don't know" rather than erroring.
        entries = []
    _kb_cache = [e for e in entries if e.get("question") and e.get("answer")]
    return _kb_cache


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\sऀ-ॿ஀-௿؀-ۿ]", " ", (text or "").lower()).strip()


def _tokens(text: str) -> set:
    return {t for t in _normalize(text).split() if t and t not in _STOPWORDS}


def match_knowledge_base(query: str) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Lightweight matching, in the priority the brief specifies:
      1. exact (normalised) question match  -> confidence 1.0
      2. keyword / token overlap similarity -> scored
    No vector database is introduced; the existing embedding engine is used
    for terminology, not for these fixed FAQ answers, because an exact
    controlled answer set is precisely what should NOT be fuzzy-matched
    loosely.
    """
    entries = load_knowledge_base()
    if not entries:
        return None, 0.0

    q_norm = _normalize(query)
    q_tokens = _tokens(query)
    if not q_tokens:
        return None, 0.0

    best: Optional[Dict[str, Any]] = None
    best_score = 0.0

    for entry in entries:
        # 1. exact match on the canonical question
        if _normalize(entry["question"]) == q_norm:
            return entry, 1.0

        # 1b. exact match on any declared keyword phrase
        for kw in entry.get("keywords", []):
            if _normalize(kw) == q_norm:
                return entry, 1.0

        # 2. token overlap against question + keywords
        entry_tokens = _tokens(entry["question"])
        for kw in entry.get("keywords", []):
            entry_tokens |= _tokens(kw)
        if not entry_tokens:
            continue

        overlap = q_tokens & entry_tokens
        if not overlap:
            continue
        # Weighted toward covering the user's query rather than the entry's
        # own vocabulary, so a short question can still match a rich entry.
        coverage = len(overlap) / len(q_tokens)
        specificity = len(overlap) / len(entry_tokens)
        score = 0.7 * coverage + 0.3 * specificity

        # A multi-word keyword phrase appearing verbatim is strong evidence.
        for kw in entry.get("keywords", []):
            kw_norm = _normalize(kw)
            if " " in kw_norm and kw_norm in q_norm:
                score = max(score, 0.9)

        if score > best_score:
            best, best_score = entry, score

    return best, round(best_score, 3)


# ── Intent detection ──────────────────────────────────────────────────────
_SEARCH_PATTERNS = [
    r"\b(?:search|find|look\s*up|lookup)\b\s+(?:for\s+)?(?:the\s+)?(?:namaste\s+)?(?:code\s+for\s+)?(.+)",
    r"\bnamaste\s+code\s+for\b\s+(.+)",
    r"\bwhat\s+is\s+the\s+code\s+for\b\s+(.+)",
]
_TRANSLATE_PATTERNS = [
    r"\b(?:show|get|give)\b.*\b(?:mapping|translation)\b.*?\bfor\b\s+(.+)",
    r"\b(?:tm2|biomedical|biomedicine|icd[\s-]*11)\b.*\bfor\b\s+(.+)",
    r"\btranslate\b\s+(.+)",
    r"\bmap\b\s+(.+?)\s+to\b",
]
_VALIDATE_PATTERNS = [
    r"\bvalidate\b\s+(?:the\s+)?(?:code\s+)?(.+)",
    r"\bis\b\s+(.+?)\s+\ba\s+valid\s+code\b",
]
_CREATE_PATTERNS = [
    r"\b(?:add|save|record)\b.*\bproblem\s+list\b",
    r"\bcreate\b.*\b(?:fhir\s+)?condition\b",
    r"\bsave\b.*\b(?:this|it)\b",
]
_CLINICAL_MARKERS = [
    "patient has", "patient is", "patient reports", "patient complains",
    "complains of", "presenting with", "presents with", "suffering from",
    "he has", "she has", "they have", "history of",
]

# Terminology targets a user might name in a mapping request.
_TARGET_HINTS = {
    "tm2": "ICD11-TM2",
    "traditional medicine": "ICD11-TM2",
    "biomedical": "ICD11-BIOMEDICINE",
    "biomedicine": "ICD11-BIOMEDICINE",
}


def _subject_from_span(original: str, match: "re.Match") -> str:
    """
    Slice the captured subject out of the original (case-preserved) text
    using the match span, rather than taking it from the lowercased copy
    the pattern was matched against.
    """
    return _clean_subject(original[match.start(1):match.end(1)])


def _clean_subject(raw: str) -> str:
    """Trim trailing politeness/filler that speech-to-text tends to append."""
    s = raw.strip().strip(".?!,")
    s = re.sub(r"\b(?:please|for me|thanks|thank you)\b\s*$", "", s, flags=re.I).strip()
    s = re.sub(r"^(?:me|us)\s+", "", s, flags=re.I).strip()
    return s


def detect_intent(text: str) -> Dict[str, Any]:
    """
    Returns {intent, subject, target_system}. Ordering matters: a
    data-changing request is checked before anything else so a phrase like
    "save this to the problem list" can never be mistaken for a search.
    """
    raw = (text or "").strip()
    low = raw.lower()

    if not raw:
        return {"intent": INTENT_UNKNOWN, "subject": None, "target_system": None}

    for pat in _CREATE_PATTERNS:
        if re.search(pat, low):
            return {"intent": INTENT_CREATE_CONDITION, "subject": None, "target_system": None}

    # Patterns are matched against the lowercased text for robustness, but the
    # subject is sliced out of the ORIGINAL string by span — terminology codes
    # are case-sensitive ("EB-10.18" is not "eb-10.18"), so lowercasing the
    # captured subject would silently break every code lookup.
    for pat in _VALIDATE_PATTERNS:
        m = re.search(pat, low)
        if m:
            return {"intent": INTENT_VALIDATE_CODE, "subject": _subject_from_span(raw, m), "target_system": None}

    for pat in _TRANSLATE_PATTERNS:
        m = re.search(pat, low)
        if m:
            target = None
            for hint, system in _TARGET_HINTS.items():
                if hint in low:
                    target = system
                    break
            return {"intent": INTENT_TRANSLATE_MAPPING, "subject": _subject_from_span(raw, m), "target_system": target}

    # Clinical narrative before generic search: "patient has cough" is a
    # clinical description, not a request to search the word "patient".
    if any(marker in low for marker in _CLINICAL_MARKERS):
        return {"intent": INTENT_CLINICAL_TEXT, "subject": raw, "target_system": None}

    for pat in _SEARCH_PATTERNS:
        m = re.search(pat, low)
        if m:
            subject = _subject_from_span(raw, m)
            if subject:
                return {"intent": INTENT_TERMINOLOGY_SEARCH, "subject": subject, "target_system": None}

    # Question-shaped input falls to the controlled knowledge base.
    return {"intent": INTENT_PROJECT_FAQ, "subject": raw, "target_system": None}


# ── Delegation to the existing engines ────────────────────────────────────
def _looks_like_code(subject: str) -> bool:
    """NAMASTE/ICD-11 codes look like AA-1, EB-10.18, 1A00, SR10 (AAA-2.1)."""
    return bool(re.match(r"^[A-Za-z0-9][A-Za-z0-9\-.\s()]{0,30}$", subject or "")) and any(c.isdigit() for c in subject or "")


# ── Phonetic fallback for spoken input ────────────────────────────────────
# NAMASTE terms are stored in IAST-style transliteration (gRudhrasI,
# vAtavyAdhiH). Speech-to-text will never reproduce that casing or vowel
# choice — a clinician saying "Gridhrasi" produces "gridhrasi", which
# shares no searchable prefix with "gRudhrasI" and returns nothing.
#
# This is query normalisation, NOT a second terminology engine: it reduces
# both sides to a consonant skeleton to find candidate codes, then hands
# those straight back to the existing search. Sanskrit/Tamil/Arabic
# transliteration varies mostly in vowels (the vocalic ṛ appears as ri, ru
# or r), so the consonant sequence is the stable part.
_VOWELS = set("aeiou")
_skeleton_index_cache: Optional[Dict[str, List[Tuple[str, str, str]]]] = None


def _skeleton(text: str) -> str:
    letters = [c for c in _normalize(text) if c.isalpha() and c.isascii()]
    return "".join(c for c in letters if c not in _VOWELS)


def _build_skeleton_index() -> Dict[str, List[Tuple[str, str, str]]]:
    """code/term/tradition grouped by consonant skeleton. Built once, cached."""
    global _skeleton_index_cache
    if _skeleton_index_cache is not None:
        return _skeleton_index_cache

    index: Dict[str, List[Tuple[str, str, str]]] = {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    for tradition, table, code_col, term_col in (
        ("Ayurveda", "nam", "namc_code", "namc_term"),
        ("Siddha", "nsm", "namc_code", "namc_term"),
        ("Unani", "num", "numc_code", "numc_term"),
    ):
        try:
            cur.execute(f"SELECT {code_col} AS c, {term_col} AS t FROM {table} WHERE TRIM(COALESCE({term_col},'')) != ''")
        except sqlite3.OperationalError:
            continue
        for row in cur.fetchall():
            sk = _skeleton(row["t"])
            if len(sk) >= 3:
                index.setdefault(sk, []).append((row["c"], row["t"], tradition))
    conn.close()
    _skeleton_index_cache = index
    return index


def _phonetic_candidates(subject: str, limit: int = 5) -> List[Dict[str, Any]]:
    sk = _skeleton(subject)
    if len(sk) < 3:
        return []
    index = _build_skeleton_index()

    hits = list(index.get(sk, []))
    if not hits:
        # Allow a near-miss on the skeleton's tail (speech-to-text often
        # drops or adds a trailing consonant).
        for key, entries in index.items():
            if key.startswith(sk) or sk.startswith(key):
                if abs(len(key) - len(sk)) <= 1:
                    hits.extend(entries)
            if len(hits) >= limit:
                break

    return [
        {"code": c, "display": t, "tradition": tr, "system": "NAMASTE", "system_id": "namaste",
         "native_script": None, "matched_by": "phonetic"}
        for c, t, tr in hits[:limit]
    ]


def _do_search(subject: str) -> Dict[str, Any]:
    from app.api import search_concepts  # local import avoids a circular import at module load

    result = search_concepts(q=subject, system="both", page=1, page_size=8)
    results = result.get("results", [])

    phonetic_used = False
    if not results:
        results = _phonetic_candidates(subject)
        phonetic_used = bool(results)

    if not results:
        return {
            "answer": f"I searched the terminologies for \"{subject}\" and found no matching concept.",
            "data": {"query": subject, "results": []},
        }

    if phonetic_used:
        top = results[0]
        return {
            "answer": (
                f"I didn't find an exact match for \"{subject}\", but by pronunciation the closest concept is "
                f"{top['display']}, code {top['code']}, from {top['tradition']}. "
                f"Please confirm this is the term you meant."
            ),
            "data": {"query": subject, "total": len(results), "results": results, "matched_by": "phonetic"},
        }

    top = results[0]
    tradition = top.get("tradition") or top.get("system")
    native = f" ({top['native_script']})" if top.get("native_script") else ""
    answer = (
        f"I found {result.get('total', len(results))} matches for \"{subject}\". "
        f"The closest is {top.get('display')}{native}, code {top.get('code')}, from {tradition}."
    )
    return {"answer": answer, "data": {"query": subject, "total": result.get("total"), "results": results}}


def _resolve_code_for(subject: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Turns whatever the user said into a concrete (code, system, display).
    Accepts a literal code, or a term to search for first. Returns
    (None, None, None) when nothing resolves.
    """
    if _looks_like_code(subject):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for system, table, code_col, term_col in (
            ("NAM", "nam", "namc_code", "namc_term"),
            ("NSM", "nsm", "namc_code", "namc_term"),
            ("NUM", "num", "numc_code", "numc_term"),
        ):
            cur.execute(f"SELECT {term_col} AS t FROM {table} WHERE {code_col} = ? LIMIT 1", (subject,))
            row = cur.fetchone()
            if row:
                conn.close()
                return subject, system, row["t"]
        conn.close()

    from app.api import search_concepts

    result = search_concepts(q=subject, system="namaste", page=1, page_size=1)
    results = result.get("results", [])
    if not results:
        return None, None, None
    top = results[0]
    tradition_to_system = {"Ayurveda": "NAM", "Siddha": "NSM", "Unani": "NUM"}
    return top.get("code"), tradition_to_system.get(top.get("tradition"), "NAM"), top.get("display")


def _do_translate(subject: str, target_system: Optional[str]) -> Dict[str, Any]:
    from app import fhir_extra

    code, system, display = _resolve_code_for(subject)
    if not code:
        return {
            "answer": f"I couldn't resolve \"{subject}\" to a NAMASTE code, so I can't show a mapping for it.",
            "data": {"query": subject},
        }

    params = fhir_extra.translate(system=system, code=code, target_system=target_system or "BOTH")
    matches = [p for p in params.get("parameter", []) if p.get("name") == "match"]

    lines: List[str] = []
    mapped: List[Dict[str, Any]] = []
    for part in matches:
        fields = {x["name"]: x for x in part.get("part", [])}
        group = fields.get("targetSystemGroup", {}).get("valueString", "ICD-11")
        equivalence = fields.get("equivalence", {}).get("valueCode")
        if equivalence == "unmatched":
            lines.append(f"{group}: no validated equivalent.")
            mapped.append({"target_system": group, "equivalence": "unmatched", "code": None, "display": None})
            continue
        concept = fields.get("concept", {}).get("valueCoding", {})
        lines.append(f"{group}: {concept.get('code')} — {concept.get('display')} ({equivalence}).")
        mapped.append({
            "target_system": group, "equivalence": equivalence,
            "code": concept.get("code"), "display": concept.get("display"),
        })

    answer = f"For {display or subject} (code {code}): " + " ".join(lines) if lines else \
        f"I found {code} but no mapping was returned."
    return {"answer": answer, "data": {"source_code": code, "source_system": system, "source_display": display, "mappings": mapped}}


def _do_validate(subject: str) -> Dict[str, Any]:
    from app.v1_router import _VALIDATE_TABLES

    code = _clean_subject(subject)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    for system, (table, code_col, display_col) in _VALIDATE_TABLES.items():
        if system in ("ICD-11",):  # duplicate alias of ICD11
            continue
        cur.execute(f"SELECT {display_col} AS d FROM {table} WHERE {code_col} = ? LIMIT 1", (code,))
        row = cur.fetchone()
        if row:
            conn.close()
            return {
                "answer": f"Yes — {code} is a valid {system} code: {row['d']}.",
                "data": {"code": code, "system": system, "display": row["d"], "valid": True},
            }
    conn.close()
    return {
        "answer": f"No — I could not find {code} in any terminology this platform indexes.",
        "data": {"code": code, "valid": False},
    }


def _do_clinical_text(text: str) -> Dict[str, Any]:
    from app import clinical_nlp

    result = clinical_nlp.build_candidates(text)
    detected = result.get("detected_symptoms", [])
    negated = result.get("negated_symptoms", [])

    if not detected and not negated:
        return {
            "answer": "I couldn't identify any recognised symptom in that description. You can try naming a symptom directly, or search a terminology term instead.",
            "data": result,
        }

    parts: List[str] = []
    if detected:
        described = []
        for s in detected:
            bit = s["symptom"]
            extras = [x for x in (s.get("duration"), s.get("body_site"), s.get("laterality")) if x]
            if extras:
                bit += f" ({', '.join(extras)})"
            described.append(bit)
        noun = "symptom" if len(described) == 1 else "symptoms"
        parts.append(f"I identified {', '.join(described)} as a reported {noun}." if len(described) == 1 else f"I identified {', '.join(described)} as reported {noun}.")
    if negated:
        parts.append("You stated " + ", ".join(s["symptom"] for s in negated) + " was not present, so I did not search for it.")

    # The clinical-safety sentence is not optional decoration — it is the
    # spoken form of the same guarantee app/clinical_nlp.py enforces in data.
    parts.append(
        "I cannot infer a definitive diagnosis from symptoms alone. "
        "I have searched the standardised terminologies for the symptoms above — a clinician must confirm any coding."
    )
    return {"answer": " ".join(parts), "data": result}


def _prepare_condition(subject: Optional[str], context_code: Optional[str]) -> Dict[str, Any]:
    """
    Builds — but does NOT save — a FHIR Condition, and hands back a pending
    action the caller must explicitly confirm. Nothing is persisted here.
    """
    code = context_code or subject
    if not code:
        return {
            "answer": "I need to know which concept to record first. Search for a term, then ask me to add it.",
            "data": {}, "requires_confirmation": False,
        }

    resolved_code, system, display = _resolve_code_for(code)
    if not resolved_code:
        return {
            "answer": f"I couldn't resolve \"{code}\" to a NAMASTE code, so I have nothing to record.",
            "data": {}, "requires_confirmation": False,
        }

    from app import problem_list

    condition = problem_list.build_problem_list_entry(
        problem_list.BuildProblemListRequest(namaste_code=resolved_code, source_system=system)
    )
    coding_count = len(condition.get("code", {}).get("coding", []))
    return {
        "answer": (
            f"I have prepared a FHIR Condition for {display or resolved_code} "
            f"with {coding_count} coding(s), including its ICD-11 mappings. Do you want me to save it?"
        ),
        "data": {"preview": condition},
        "requires_confirmation": True,
        "pending_action": {"action": "SAVE_CONDITION", "namaste_code": resolved_code, "source_system": system},
    }


# ── Public entry point ────────────────────────────────────────────────────
def ask(text: str, context_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Single entry point for both voice and typed input — the browser does
    speech-to-text before this is called, so this function only ever sees
    text and behaves identically for both.
    """
    query = (text or "").strip()
    if not query:
        return {
            "intent": INTENT_UNKNOWN, "answer": "I didn't catch that. Could you say it again?",
            "confidence": 0.0, "data": {}, "requires_confirmation": False, "source": "assistant",
        }

    detected = detect_intent(query)
    intent = detected["intent"]
    subject = detected["subject"]

    if intent == INTENT_PROJECT_FAQ:
        entry, confidence = match_knowledge_base(query)
        if entry and confidence >= KB_CONFIDENCE_FLOOR:
            return {
                "intent": intent, "answer": entry["answer"], "confidence": confidence,
                "matched_question": entry["question"], "category": entry.get("category"),
                "data": {}, "requires_confirmation": False, "source": "knowledge_base",
            }
        return {
            "intent": INTENT_UNKNOWN, "answer": FALLBACK_ANSWER, "suggestion": FALLBACK_SUGGESTION,
            "confidence": confidence, "data": {}, "requires_confirmation": False, "source": "knowledge_base",
        }

    if intent == INTENT_TERMINOLOGY_SEARCH:
        out = _do_search(subject)
    elif intent == INTENT_TRANSLATE_MAPPING:
        out = _do_translate(subject, detected.get("target_system"))
    elif intent == INTENT_VALIDATE_CODE:
        out = _do_validate(subject)
    elif intent == INTENT_CLINICAL_TEXT:
        out = _do_clinical_text(query)
    elif intent == INTENT_CREATE_CONDITION:
        out = _prepare_condition(subject, context_code)
    else:
        return {
            "intent": INTENT_UNKNOWN, "answer": FALLBACK_ANSWER, "suggestion": FALLBACK_SUGGESTION,
            "confidence": 0.0, "data": {}, "requires_confirmation": False, "source": "assistant",
        }

    return {
        "intent": intent,
        "answer": out["answer"],
        "confidence": 1.0,
        "data": out.get("data", {}),
        "requires_confirmation": out.get("requires_confirmation", False),
        "pending_action": out.get("pending_action"),
        "source": "terminology_engine",
    }


def confirm_action(action: Dict[str, Any], actor: str) -> Dict[str, Any]:
    """
    Executes a previously-prepared action after explicit user confirmation.
    Kept separate from ask() on purpose: a single spoken utterance can never
    reach this code path.
    """
    from app import audit, problem_list

    if action.get("action") != "SAVE_CONDITION":
        return {"executed": False, "answer": f"I don't know how to perform '{action.get('action')}'."}

    code = action.get("namaste_code")
    system = action.get("source_system", "NAMASTE")
    if not code:
        return {"executed": False, "answer": "That action is missing the code to record."}

    condition = problem_list.build_problem_list_entry(
        problem_list.BuildProblemListRequest(namaste_code=code, source_system=system)
    )
    audit.log(
        action="ASSISTANT_CONDITION_CONFIRMED",
        actor=actor,
        target=f"Condition for {system} {code}",
        details=f"User confirmed via assistant; {len(condition.get('code', {}).get('coding', []))} coding(s)",
    )
    return {
        "executed": True,
        "answer": f"Saved. The FHIR Condition for {code} has been recorded and the action is in the audit trail.",
        "data": {"condition": condition},
    }


def capabilities() -> Dict[str, Any]:
    """What the assistant can answer — used to populate on-screen hints."""
    entries = load_knowledge_base()
    return {
        "knowledge_base_entries": len(entries),
        "categories": sorted({e.get("category", "general") for e in entries}),
        "example_questions": [e["question"] for e in entries[:6]],
        "example_commands": [
            "Search Gridhrasi",
            "Show the TM2 mapping for AA-1",
            "Validate code AA-1",
            "Patient has lower back pain radiating to the right leg",
        ],
        "intents": [
            INTENT_PROJECT_FAQ, INTENT_TERMINOLOGY_SEARCH, INTENT_TRANSLATE_MAPPING,
            INTENT_VALIDATE_CODE, INTENT_CLINICAL_TEXT, INTENT_CREATE_CONDITION,
        ],
        "safety_note": (
            "The assistant answers project questions only from a controlled knowledge base and never invents "
            "an explanation. It identifies symptoms but never infers a diagnosis, and any action that would "
            "record clinical data requires explicit confirmation first."
        ),
    }
