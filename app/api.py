"""
Extended API endpoints for the AYUSH Nexus frontend.
Provides statistics, search, concept browsing, and mapping operations.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sqlite3
import re

from app import ai_mapping

DB_PATH = "db/ayush_icd11_combined.db"


def _real_confidence(source_code: str, target_code: str) -> Optional[float]:
    """
    Backend-computed confidence for a curated mapping: real embedding cosine
    similarity + lexical overlap between the actual source and target concept
    text (same model/formula as the AI suggestion engine — see
    app/ai_mapping.py:score_pair), not a hardcoded per-equivalence constant.
    Returns None (never a fake number) if the AI embeddings haven't been
    built or either code isn't in the precomputed index.
    """
    result = ai_mapping.score_pair(source_code, target_code)
    return result["combined_score"] if result else None

router = APIRouter()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_code(code: str) -> str:
    return re.sub(r"\s+", " ", code).strip()


# ---------------------------------------------------------------------------
# /api/stats
# ---------------------------------------------------------------------------

@router.get("/stats")
def get_stats():
    """Return summary statistics for the Overview dashboard."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM nam")
    namaste_concepts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM icd11")
    icd11_concepts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM concept_map")
    total_mappings = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM concept_map WHERE equivalence = 'equivalent'")
    validated_mappings = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM concept_map WHERE equivalence = 'relatedto'")
    related_mappings = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT source_code) FROM concept_map")
    mapped_namaste_codes = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT target_code) FROM concept_map")
    mapped_icd11_codes = cur.fetchone()[0]

    conn.close()

    return {
        "namaste_concepts": namaste_concepts,
        "icd11_concepts": icd11_concepts,
        "total_mappings": total_mappings,
        "validated_mappings": validated_mappings,
        "related_mappings": related_mappings,
        "mapped_namaste_codes": mapped_namaste_codes,
        "mapped_icd11_codes": mapped_icd11_codes,
        "terminologies": [
            {
                "id": "namaste",
                "name": "NAMASTE",
                "full_name": "National AYUSH Morbidity and Standardized Terminologies Electronic",
                "version": "v1.2",
                "status": "active",
                "concept_count": namaste_concepts,
                "source": "Ministry of Ayush",
            },
            {
                "id": "icd11",
                "name": "ICD-11 TM2",
                "full_name": "ICD-11 Traditional Medicine Module 2",
                "version": "v2022.1",
                "status": "active",
                "concept_count": icd11_concepts,
                "source": "WHO",
            },
        ],
    }


# ---------------------------------------------------------------------------
# /api/concepts   (browse NAMASTE + ICD-11 concepts)
# ---------------------------------------------------------------------------

@router.get("/concepts")
def get_concepts(
    system: Optional[str] = Query(None, description="namaste | icd11"),
    q: Optional[str] = Query(None, description="Free-text search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Browse concepts from NAMASTE or ICD-11.
    Returns paginated results with optional full-text search.
    """
    conn = get_db()
    cur = conn.cursor()
    offset = (page - 1) * page_size
    results = []
    total = 0

    system = (system or "").lower()

    if system == "icd11":
        if q:
            safe_q = q.replace('"', '').strip()
            fts_query = f'"{safe_q}"' if ' ' in safe_q else f'{safe_q}*'
            try:
                cur.execute(
                    """
                    SELECT i.code, i.title FROM icd11_fts f
                    JOIN icd11 i ON f.rowid = i.rowid
                    WHERE f MATCH ?
                    LIMIT ? OFFSET ?
                    """,
                    (fts_query, page_size, offset),
                )
                rows = cur.fetchall()
                cur.execute(
                    "SELECT COUNT(*) FROM icd11_fts WHERE icd11_fts MATCH ?", (fts_query,)
                )
                total = cur.fetchone()[0]
            except Exception:
                rows = []
                total = 0
        else:
            cur.execute(
                "SELECT code, title FROM icd11 ORDER BY code LIMIT ? OFFSET ?",
                (page_size, offset),
            )
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) FROM icd11")
            total = cur.fetchone()[0]

        results = [
            {
                "code": r["code"],
                "display": r["title"],
                "system": "ICD-11 TM2",
                "system_id": "icd11",
            }
            for r in rows
        ]

    else:
        # Default: NAMASTE (also handles system == "namaste")
        if q:
            safe_q = q.replace('"', '').strip()
            fts_query = f'"{safe_q}"' if ' ' in safe_q else f'{safe_q}*'
            try:
                cur.execute(
                    """
                    SELECT namc_code, namc_term, name_english, short_definition
                    FROM nam_fts
                    WHERE nam_fts MATCH ?
                    LIMIT ? OFFSET ?
                    """,
                    (fts_query, page_size, offset),
                )
                rows = cur.fetchall()
                cur.execute(
                    "SELECT COUNT(*) FROM nam_fts WHERE nam_fts MATCH ?", (fts_query,)
                )
                total = cur.fetchone()[0]
            except Exception:
                rows = []
                total = 0
        else:
            cur.execute(
                "SELECT namc_code, namc_term, name_english, short_definition FROM nam ORDER BY namc_code LIMIT ? OFFSET ?",
                (page_size, offset),
            )
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) FROM nam")
            total = cur.fetchone()[0]

        results = [
            {
                "code": r["namc_code"],
                "display": r["namc_term"],
                "name_english": r["name_english"],
                "definition": r["short_definition"],
                "system": "NAMASTE",
                "system_id": "namaste",
            }
            for r in rows
        ]

    conn.close()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "system": system or "namaste",
        "results": results,
    }


# ---------------------------------------------------------------------------
# /api/search   (unified cross-system concept search)
# ---------------------------------------------------------------------------

@router.get("/search")
def search_concepts(
    q: str = Query(..., min_length=1, description="Search term"),
    system: Optional[str] = Query(None, description="namaste | icd11 | both"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Unified full-text search across NAMASTE and/or ICD-11 terminologies.
    """
    conn = get_db()
    cur = conn.cursor()
    offset = (page - 1) * page_size

    safe_q = q.replace('"', '').strip()
    fts_query = f'"{safe_q}"' if ' ' in safe_q else f'{safe_q}*'

    namaste_results = []
    icd11_results = []
    system = (system or "both").lower()

    if system in ("namaste", "both"):
        try:
            cur.execute(
                """
                SELECT namc_code, namc_term, name_english, short_definition
                FROM nam_fts
                WHERE nam_fts MATCH ?
                LIMIT ? OFFSET ?
                """,
                (fts_query, page_size, offset),
            )
            namaste_results = [
                {
                    "code": r["namc_code"],
                    "display": r["namc_term"],
                    "name_english": r["name_english"],
                    "definition": r["short_definition"],
                    "system": "NAMASTE",
                    "system_id": "namaste",
                }
                for r in cur.fetchall()
            ]
        except Exception:
            namaste_results = []

    if system in ("icd11", "both"):
        try:
            cur.execute(
                """
                SELECT i.code, i.title FROM icd11_fts f
                JOIN icd11 i ON f.rowid = i.rowid
                WHERE f MATCH ?
                LIMIT ? OFFSET ?
                """,
                (fts_query, page_size, offset),
            )
            icd11_results = [
                {
                    "code": r["code"],
                    "display": r["title"],
                    "system": "ICD-11 TM2",
                    "system_id": "icd11",
                }
                for r in cur.fetchall()
            ]
        except Exception:
            icd11_results = []

    conn.close()

    combined = namaste_results + icd11_results
    return {
        "query": q,
        "total": len(combined),
        "namaste_count": len(namaste_results),
        "icd11_count": len(icd11_results),
        "results": combined,
    }


# ---------------------------------------------------------------------------
# /api/mappings   (browse / filter mappings)
# ---------------------------------------------------------------------------

@router.get("/mappings")
def get_mappings(
    source_code: Optional[str] = Query(None),
    target_code: Optional[str] = Query(None),
    equivalence: Optional[str] = Query(None, description="equivalent | relatedto"),
    q: Optional[str] = Query(None, description="Search source/target term"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Browse all concept mappings with optional filtering.
    Joins with nam and icd11 tables to return display names.
    """
    conn = get_db()
    cur = conn.cursor()
    offset = (page - 1) * page_size

    where_clauses = []
    params = []

    if source_code:
        where_clauses.append("cm.source_code = ?")
        params.append(normalize_code(source_code))

    if target_code:
        where_clauses.append("cm.target_code = ?")
        params.append(target_code)

    if equivalence:
        where_clauses.append("cm.equivalence = ?")
        params.append(equivalence)

    if q:
        where_clauses.append(
            "(LOWER(n.namc_term) LIKE ? OR LOWER(i.title) LIKE ? OR cm.source_code LIKE ? OR cm.target_code LIKE ?)"
        )
        like_q = f"%{q.lower()}%"
        params.extend([like_q, like_q, like_q, like_q])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_query = f"""
        SELECT COUNT(*) FROM concept_map cm
        LEFT JOIN nam n ON cm.source_code = n.namc_code
        LEFT JOIN icd11 i ON cm.target_code = i.code
        {where_sql}
    """
    cur.execute(count_query, params)
    total = cur.fetchone()[0]

    data_query = f"""
        SELECT
            cm.id,
            cm.source_system,
            cm.source_code,
            n.namc_term AS source_display,
            n.name_english AS source_english,
            n.short_definition AS source_definition,
            cm.target_system,
            cm.target_code,
            i.title AS target_display,
            cm.equivalence
        FROM concept_map cm
        LEFT JOIN nam n ON cm.source_code = n.namc_code
        LEFT JOIN icd11 i ON cm.target_code = i.code
        {where_sql}
        ORDER BY cm.source_code, cm.target_code
        LIMIT ? OFFSET ?
    """
    cur.execute(data_query, params + [page_size, offset])
    rows = cur.fetchall()

    conn.close()

    results = [
        {
            "id": r["id"],
            "source_system": r["source_system"] or "NAMASTE",
            "source_code": r["source_code"],
            "source_display": r["source_display"] or r["source_code"],
            "source_english": r["source_english"],
            "source_definition": r["source_definition"],
            "target_system": r["target_system"] or "ICD-11 TM2",
            "target_code": r["target_code"],
            "target_display": r["target_display"] or r["target_code"],
            "equivalence": r["equivalence"],
            # Real backend-computed confidence (embedding similarity + lexical
            # overlap), not a hardcoded per-equivalence constant. None means
            # the AI embeddings haven't been built — never faked.
            "confidence": _real_confidence(r["source_code"], r["target_code"]),
        }
        for r in rows
    ]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "results": results,
    }


# ---------------------------------------------------------------------------
# /api/mappings/{id}   (single mapping detail)
# ---------------------------------------------------------------------------

@router.get("/mappings/{mapping_id}")
def get_mapping_by_id(mapping_id: int):
    """Return full detail for a single mapping record."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            cm.id,
            cm.source_system,
            cm.source_code,
            n.namc_term AS source_display,
            n.name_english AS source_english,
            n.namc_term_devanagari AS source_devanagari,
            n.short_definition AS source_definition,
            cm.target_system,
            cm.target_code,
            i.title AS target_display,
            cm.equivalence
        FROM concept_map cm
        LEFT JOIN nam n ON cm.source_code = n.namc_code
        LEFT JOIN icd11 i ON cm.target_code = i.code
        WHERE cm.id = ?
        """,
        (mapping_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Mapping {mapping_id} not found")

    return {
        "id": row["id"],
        "source_system": row["source_system"] or "NAMASTE",
        "source_code": row["source_code"],
        "source_display": row["source_display"] or row["source_code"],
        "source_english": row["source_english"],
        "source_devanagari": row["source_devanagari"],
        "source_definition": row["source_definition"],
        "target_system": row["target_system"] or "ICD-11 TM2",
        "target_code": row["target_code"],
        "target_display": row["target_display"] or row["target_code"],
        "equivalence": row["equivalence"],
        "confidence": _real_confidence(row["source_code"], row["target_code"]),
        "status": "validated" if row["equivalence"] == "equivalent" else "review",
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# /api/terminologies   (system metadata)
# ---------------------------------------------------------------------------

@router.get("/terminologies")
def get_terminologies():
    """Return metadata about available terminology systems."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM nam")
    namaste_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM icd11")
    icd11_count = cur.fetchone()[0]

    conn.close()

    return [
        {
            "id": "namaste",
            "name": "NAMASTE",
            "full_name": "National AYUSH Morbidity and Standardized Terminologies Electronic",
            "description": "Traditional medicine terminology covering Ayurveda, Siddha, and Unani systems",
            "version": "v1.2 (Active)",
            "status": "active",
            "concept_count": namaste_count,
            "source": "Ministry of Ayush, Government of India",
            "url": "http://namaste.terminology/CodeSystem",
        },
        {
            "id": "icd11",
            "name": "ICD-11 TM2",
            "full_name": "International Classification of Diseases - Traditional Medicine Module 2",
            "description": "WHO standard classification for traditional medicine conditions",
            "version": "v2022.1 (Active)",
            "status": "active",
            "concept_count": icd11_count,
            "source": "World Health Organization",
            "url": "http://id.who.int/icd/release/11/mms",
        },
    ]


# ---------------------------------------------------------------------------
# /api/concept/{system}/{code}   (single concept lookup)
# ---------------------------------------------------------------------------

@router.get("/concept/{system}/{code:path}")
def get_concept(system: str, code: str):
    """Fetch a single concept by system and code, including its mappings."""
    conn = get_db()
    cur = conn.cursor()
    system = system.lower()
    code = normalize_code(code)

    if system == "namaste":
        cur.execute(
            "SELECT namc_code, namc_term, name_english, namc_term_devanagari, short_definition FROM nam WHERE namc_code = ? LIMIT 1",
            (code,),
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"NAMASTE concept {code} not found")
        concept = {
            "code": row["namc_code"],
            "display": row["namc_term"],
            "name_english": row["name_english"],
            "devanagari": row["namc_term_devanagari"],
            "definition": row["short_definition"],
            "system": "NAMASTE",
            "system_id": "namaste",
        }
        # Fetch mappings for this concept
        cur.execute(
            """
            SELECT cm.id, cm.target_code, cm.equivalence, i.title AS target_display
            FROM concept_map cm
            LEFT JOIN icd11 i ON cm.target_code = i.code
            WHERE cm.source_code = ?
            """,
            (code,),
        )

    elif system == "icd11":
        cur.execute("SELECT code, title FROM icd11 WHERE code = ? LIMIT 1", (code,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"ICD-11 concept {code} not found")
        concept = {
            "code": row["code"],
            "display": row["title"],
            "system": "ICD-11 TM2",
            "system_id": "icd11",
        }
        cur.execute(
            """
            SELECT cm.id, cm.source_code, cm.equivalence, n.namc_term AS source_display
            FROM concept_map cm
            LEFT JOIN nam n ON cm.source_code = n.namc_code
            WHERE cm.target_code = ?
            """,
            (code,),
        )
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="system must be 'namaste' or 'icd11'")

    mappings = [dict(r) for r in cur.fetchall()]
    conn.close()

    concept["mappings"] = mappings
    return concept
