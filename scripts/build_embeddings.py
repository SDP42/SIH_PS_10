"""
Build sentence embeddings for every NAMASTE-family source concept (nam, nsm,
num, ast) and every ICD-11 TM2 target concept (icd11), for the ambiguity-aware
AI mapping engine in app/ai_mapping.py.

Model choice: all-MiniLM-L6-v2 (general-purpose, 384-dim, ~80MB), NOT
cambridgeltl/SapBERT-from-PubMedBERT-fulltext. SapBERT is a much larger
biomedical-specific model (~400MB+ download, slower CPU inference) — for a
same-night offline build this is a real cost with no guaranteed win, since
NAMASTE/ICD-11 text here is short clinical phrases (often single words or
Sanskrit/Devanagari transliterations) rather than the PubMed sentence-length
text SapBERT was tuned on. all-MiniLM-L6-v2 is fast enough to embed ~55k
concepts in well under a minute on CPU and is a well-established general
baseline. This is an engineering choice, not a claim of medical accuracy —
see the disclaimer surfaced by every AI mapping API response.

No vector DB / FAISS is used: at this scale (a few thousand source vectors,
~37k target vectors, 384 dims) a plain in-memory numpy matrix and a single
matmul for cosine similarity is exact, fast, and avoids an entire class of
native-library bugs.

Usage:
    python scripts/build_embeddings.py            # build if not already built
    python scripts/build_embeddings.py --rebuild   # force rebuild
"""
import os
import sys
import json
import time
import sqlite3
import argparse

DB_PATH = "db/ayush_icd11_combined.db"
EMBED_DIR = "db/embeddings"
MODEL_NAME = "all-MiniLM-L6-v2"

# (table, code_column, text_columns_in_priority_order)
SOURCE_TABLES = [
    ("nam", "namc_code", ["name_english", "namc_term", "short_definition"]),
    ("nsm", "namc_code", ["namc_term", "short_definition"]),
    ("num", "numc_code", ["numc_term", "short_definition"]),
    ("ast", "code", ["word", "short_defination"]),
]
TARGET_TABLE = ("icd11", "code", ["title"])


def _build_text(row: dict, columns: list[str]) -> str:
    parts = [str(row[c]).strip() for c in columns if row.get(c) and str(row[c]).strip().lower() != "none"]
    return " — ".join(dict.fromkeys(parts))  # de-dup while preserving order


def _is_built() -> bool:
    return (
        os.path.exists(os.path.join(EMBED_DIR, "source_vectors.npy"))
        and os.path.exists(os.path.join(EMBED_DIR, "target_vectors.npy"))
        and os.path.exists(os.path.join(EMBED_DIR, "meta.json"))
    )


def build(force: bool = False):
    if _is_built() and not force:
        print(f"Embeddings already built at {EMBED_DIR}/ — pass --rebuild to force. Skipping.")
        return

    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"WARNING: embeddings dependencies not installed ({e}). "
              f"Run: pip install sentence-transformers numpy scikit-learn. Skipping embeddings build.")
        return

    os.makedirs(EMBED_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print(f"Loading model: {MODEL_NAME} (CPU) ...")
    t0 = time.time()
    model = SentenceTransformer(MODEL_NAME, device="cpu")
    print(f"Model loaded in {time.time() - t0:.1f}s")

    # ---- Source concepts (NAMASTE-family) ----
    source_records = []  # (system, code, display_text, embed_text)
    for table, code_col, text_cols in SOURCE_TABLES:
        cur.execute(f"SELECT * FROM {table}")
        for row in cur.fetchall():
            row = dict(row)
            code = row.get(code_col)
            if not code or not str(code).strip():
                continue
            text = _build_text(row, text_cols)
            if not text:
                continue
            source_records.append((table.upper(), str(code).strip(), text, f"{code} {text}"))

    # ---- Target concepts (ICD-11 TM2) ----
    target_records = []  # (system, code, display_text, embed_text)
    t_table, t_code_col, t_text_cols = TARGET_TABLE
    cur.execute(f"SELECT * FROM {t_table}")
    for row in cur.fetchall():
        row = dict(row)
        code = row.get(t_code_col)
        if not code or not str(code).strip():
            continue
        text = _build_text(row, t_text_cols)
        if not text:
            continue
        target_records.append(("ICD11", str(code).strip(), text, f"{code} {text}"))

    conn.close()

    print(f"Encoding {len(source_records)} source concepts and {len(target_records)} target concepts ...")
    t0 = time.time()
    source_vecs = model.encode(
        [r[3] for r in source_records], batch_size=64, show_progress_bar=False,
        convert_to_numpy=True, normalize_embeddings=True,
    ).astype("float32")
    target_vecs = model.encode(
        [r[3] for r in target_records], batch_size=64, show_progress_bar=False,
        convert_to_numpy=True, normalize_embeddings=True,
    ).astype("float32")
    build_seconds = round(time.time() - t0, 2)
    print(f"Encoded in {build_seconds}s")

    np.save(os.path.join(EMBED_DIR, "source_vectors.npy"), source_vecs)
    np.save(os.path.join(EMBED_DIR, "target_vectors.npy"), target_vecs)

    # embedding_index table: row position in the .npy array <-> system/code/display_text
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS embedding_index")
    cur.execute("""
        CREATE TABLE embedding_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matrix TEXT NOT NULL,      -- 'source' or 'target'
            vector_index INTEGER NOT NULL,
            system TEXT NOT NULL,
            code TEXT NOT NULL,
            display_text TEXT
        )
    """)
    cur.execute("CREATE INDEX idx_embedding_index_lookup ON embedding_index(matrix, system, code)")

    for i, (system, code, display_text, _) in enumerate(source_records):
        cur.execute(
            "INSERT INTO embedding_index (matrix, vector_index, system, code, display_text) VALUES (?, ?, ?, ?, ?)",
            ("source", i, system, code, display_text),
        )
    for i, (system, code, display_text, _) in enumerate(target_records):
        cur.execute(
            "INSERT INTO embedding_index (matrix, vector_index, system, code, display_text) VALUES (?, ?, ?, ?, ?)",
            ("target", i, system, code, display_text),
        )
    conn.commit()
    conn.close()

    meta = {
        "model_name": MODEL_NAME,
        "embedding_dimension": int(source_vecs.shape[1]),
        "n_source_vectors": len(source_records),
        "n_target_vectors": len(target_records),
        "build_seconds": build_seconds,
        "is_medically_validated": False,
        "disclaimer": (
            "Engineering baseline for semantic retrieval/ranking only. "
            "Not medically validated. Similarity scores are ranking signals, not clinical confidence."
        ),
    }
    with open(os.path.join(EMBED_DIR, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Saved {len(source_records)} source + {len(target_records)} target vectors to {EMBED_DIR}/")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild even if embeddings already exist")
    args = parser.parse_args()
    build(force=args.rebuild)
