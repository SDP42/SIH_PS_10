"""
Ambiguity-aware AI mapping engine.

For any indexed NAMASTE-family source concept (nam/nsm/num/ast — built by
scripts/build_embeddings.py), ranks ICD-11 TM2 candidates by cosine
similarity of precomputed sentence embeddings, combined with a lexical
word-overlap signal, then classifies the result into one of four transparent
decisions so the engine never silently guesses:

  AUTO_SUGGEST            top candidate is strong AND clearly separated from
                           the runner-up.
  NEEDS_CONTEXT           moderate top score, or several candidates are close
                           together (genuine ambiguity) — return the close set.
  EXPERT_REVIEW           weak but non-trivial signal — too low to suggest.
  NO_VALIDATED_EQUIVALENT every candidate is below the floor — refuses to guess.

All thresholds are named engineering constants, not medical judgments — see
DISCLAIMER, echoed in every response.
"""
import os
import json
import re
import sqlite3
from functools import lru_cache
from typing import Any, Dict, List, Optional

DB_PATH = "db/ayush_icd11_combined.db"
EMBED_DIR = "db/embeddings"

# ── Decision thresholds (tunable) ────────────────────────────────────────
AUTO_THRESHOLD = 0.72
EXPERT_REVIEW_THRESHOLD = 0.45
FLOOR_THRESHOLD = 0.30
MARGIN_CLEAR_THRESHOLD = 0.05

SEMANTIC_WEIGHT = 0.75
LEXICAL_WEIGHT = 0.25

DECISION_AUTO_SUGGEST = "AUTO_SUGGEST"
DECISION_NEEDS_CONTEXT = "NEEDS_CONTEXT"
DECISION_EXPERT_REVIEW = "EXPERT_REVIEW"
DECISION_NO_VALIDATED_EQUIVALENT = "NO_VALIDATED_EQUIVALENT"

VALID_DECISIONS = {
    DECISION_AUTO_SUGGEST, DECISION_NEEDS_CONTEXT,
    DECISION_EXPERT_REVIEW, DECISION_NO_VALIDATED_EQUIVALENT,
}

DISCLAIMER = (
    "Similarity scores and decision tiers are engineering ranking heuristics "
    "from a general-purpose sentence embedding model (all-MiniLM-L6-v2), not "
    "medical judgments. No candidate is ever automatically approved as a "
    "mapping — every tier still requires human review."
)

_STOPWORDS = {"of", "the", "and", "a", "in", "with", "due", "to", "or", "not", "unspecified"}


class EngineNotReadyError(RuntimeError):
    pass


class SourceConceptNotFoundError(LookupError):
    pass


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@lru_cache(maxsize=1)
def _load_matrices():
    try:
        import numpy as np
    except ImportError as e:
        raise EngineNotReadyError(f"numpy not installed: {e}")

    source_path = os.path.join(EMBED_DIR, "source_vectors.npy")
    target_path = os.path.join(EMBED_DIR, "target_vectors.npy")
    meta_path = os.path.join(EMBED_DIR, "meta.json")

    if not (os.path.exists(source_path) and os.path.exists(target_path) and os.path.exists(meta_path)):
        raise EngineNotReadyError(
            "AI mapping embeddings have not been built. Run: python scripts/build_embeddings.py"
        )

    source_vectors = np.load(source_path)
    target_vectors = np.load(target_path)
    with open(meta_path) as f:
        meta = json.load(f)
    return source_vectors, target_vectors, meta


@lru_cache(maxsize=1)
def _load_index():
    """Returns (source_rows, target_rows): each a list of sqlite3.Row-like dicts ordered by vector_index."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM embedding_index WHERE matrix = 'source' ORDER BY vector_index")
    source_rows = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT * FROM embedding_index WHERE matrix = 'target' ORDER BY vector_index")
    target_rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return source_rows, target_rows


def is_ready() -> bool:
    try:
        _load_matrices()
        return True
    except EngineNotReadyError:
        return False


def get_model_info() -> Dict[str, Any]:
    _, _, meta = _load_matrices()
    return meta


def _find_source_row(namaste_code: str, source_system: Optional[str] = None) -> Optional[Dict[str, Any]]:
    source_rows, _ = _load_index()
    code = namaste_code.strip()
    matches = [r for r in source_rows if r["code"] == code]
    if source_system:
        system_matches = [r for r in matches if r["system"].upper() == source_system.upper()]
        if system_matches:
            matches = system_matches
    return matches[0] if matches else None


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def _lexical_overlap(source_text: str, target_text: str) -> float:
    a, b = _tokenize(source_text), _tokenize(target_text)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _curated_mappings(namaste_code: str) -> List[Dict[str, Any]]:
    conn = _get_conn()
    cur = conn.cursor()
    normalized = re.sub(r"\s+", " ", namaste_code).strip()
    cur.execute(
        """
        SELECT cm.target_code, cm.equivalence, i.title AS target_title
        FROM concept_map cm
        LEFT JOIN icd11 i ON cm.target_code = i.code
        WHERE cm.source_code = ? OR cm.source_code LIKE ? OR cm.source_code LIKE ?
        """,
        (normalized, f"{normalized}(%", f"{normalized} %"),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _classify(top1: float, top2: Optional[float]) -> str:
    if top1 < FLOOR_THRESHOLD:
        return DECISION_NO_VALIDATED_EQUIVALENT
    margin = top1 - (top2 if top2 is not None else 0.0)
    if top1 >= AUTO_THRESHOLD:
        return DECISION_AUTO_SUGGEST if margin >= MARGIN_CLEAR_THRESHOLD else DECISION_NEEDS_CONTEXT
    if top1 >= EXPERT_REVIEW_THRESHOLD:
        return DECISION_NEEDS_CONTEXT
    return DECISION_EXPERT_REVIEW


def _rationale(decision: str, candidates: List[Dict[str, Any]], margin: Optional[float]) -> str:
    if not candidates:
        return (
            f"No ICD-11 TM2 candidate scored above the minimum floor ({FLOOR_THRESHOLD}) — "
            "the engine found nothing worth suggesting rather than forcing a low-quality guess."
        )
    top = candidates[0]
    if decision == DECISION_AUTO_SUGGEST:
        second = candidates[1]["icd11_title"] if len(candidates) > 1 else None
        margin_txt = f"a clear {margin:.2f} margin over '{second}'" if second else "no close competitor"
        return (
            f"Top candidate '{top['icd11_title']}' scores {top['similarity']:.2f} with {margin_txt} "
            f"(shared terms: {', '.join(top.get('shared_terms', [])) or 'none'}) — confident enough to "
            "suggest directly, though it still requires human sign-off."
        )
    if decision == DECISION_NEEDS_CONTEXT:
        close = [c["icd11_title"] for c in candidates[:3]]
        reason = "the runner-up is close behind" if margin is not None and margin < MARGIN_CLEAR_THRESHOLD else "the score is only moderate"
        return f"Top candidate '{top['icd11_title']}' scores {top['similarity']:.2f}, but {reason} — {len(close)} close candidates ({', '.join(close)}) need a clinician to pick between them."
    if decision == DECISION_EXPERT_REVIEW:
        return f"Top candidate '{top['icd11_title']}' scores only {top['similarity']:.2f} — a weak but non-trivial signal, routed to expert review rather than surfaced as a hint."
    return f"Best candidate '{top['icd11_title']}' scores {top['similarity']:.2f}, below the {FLOOR_THRESHOLD} floor — treated as no validated equivalent."


def get_candidates(namaste_code: str, source_system: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
    import numpy as np

    source_vectors, target_vectors, meta = _load_matrices()
    source_rows, target_rows = _load_index()

    source_row = _find_source_row(namaste_code, source_system)
    if source_row is None:
        raise SourceConceptNotFoundError(
            f"'{namaste_code}' is not an indexed NAMASTE-family concept (checked nam/nsm/num/ast)."
        )

    source_vec = source_vectors[source_row["vector_index"]]
    semantic_scores = target_vectors @ source_vec  # cosine similarity, vectors are L2-normalized

    top_pool = min(top_k * 4, len(target_rows))
    pool_idx = np.argpartition(-semantic_scores, top_pool - 1)[:top_pool] if top_pool > 0 else np.array([], dtype=int)

    scored = []
    for idx in pool_idx:
        idx = int(idx)
        target = target_rows[idx]
        sem = float(semantic_scores[idx])
        lex = _lexical_overlap(source_row["display_text"] or "", target["display_text"] or "")
        combined = SEMANTIC_WEIGHT * sem + LEXICAL_WEIGHT * lex
        shared = sorted(_tokenize(source_row["display_text"] or "") & _tokenize(target["display_text"] or ""))
        scored.append({
            "icd11_code": target["code"],
            "icd11_title": target["display_text"],
            "similarity": round(combined, 4),
            "semantic_score": round(sem, 4),
            "lexical_score": round(lex, 4),
            "shared_terms": shared,
        })

    scored.sort(key=lambda c: c["similarity"], reverse=True)
    candidates = scored[:top_k]
    for i, c in enumerate(candidates):
        c["rank"] = i + 1

    top1 = candidates[0]["similarity"] if candidates else 0.0
    top2 = candidates[1]["similarity"] if len(candidates) > 1 else None
    margin = round(top1 - (top2 if top2 is not None else 0.0), 4) if candidates else None

    decision = _classify(top1, top2)
    rationale = _rationale(decision, candidates, margin)

    curated = _curated_mappings(source_row["code"])

    return {
        "namaste_code": source_row["code"],
        "source_system": source_row["system"],
        "decision": decision,
        "margin": margin,
        "candidates": candidates,
        "rationale": rationale,
        "has_curated_mapping": len(curated) > 0,
        "curated_mappings": curated,
        "disclaimer": DISCLAIMER,
    }


def list_unmapped(page: int = 1, page_size: int = 20, source_system: Optional[str] = None) -> Dict[str, Any]:
    """
    Paginated list of indexed NAMASTE-family concepts with NO row in
    concept_map — the real "mapping gap" the AI engine targets.
    """
    source_rows, _ = _load_index()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT source_code FROM concept_map")
    mapped_codes = set()
    for (code,) in cur.fetchall():
        normalized = re.sub(r"\s+", " ", code).strip()
        mapped_codes.add(normalized)
        # Also strip a trailing "(...)" qualifier, matching fetch_concept_map's LIKE patterns
        mapped_codes.add(re.sub(r"\s*\(.*\)\s*$", "", normalized).strip())
    conn.close()

    pool = [r for r in source_rows if r["code"] not in mapped_codes]
    if source_system:
        pool = [r for r in pool if r["system"].upper() == source_system.upper()]

    total = len(pool)
    start = (page - 1) * page_size
    page_rows = pool[start:start + page_size]

    return {
        "total_unmapped": total,
        "page": page,
        "page_size": page_size,
        "concepts": [
            {"system": r["system"], "code": r["code"], "display_text": r["display_text"]}
            for r in page_rows
        ],
    }
