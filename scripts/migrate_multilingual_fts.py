#!/usr/bin/env python3
"""
One-time, idempotent migration: rebuild nam_fts/nsm_fts/num_fts to index each
tradition's native-script term column, so full-text search actually works in
the language practitioners use — Devanagari for Ayurveda, Tamil for Siddha,
Arabic for Unani — not just their IAST/English transliteration.

Before this migration, nam_fts indexed namc_term (an IAST transliteration,
e.g. "vyAdhi-viniScayaH") and never touched namc_term_devanagari at all;
nsm_fts never indexed tamil_term; num_fts didn't even index a term column
(only numc_code + short_definition — Unani terms weren't searchable by name
in any script). Searching प्रमेह, சித்தா, or رطوبت غریزیہ returned nothing.

Mirrors app/governance.py's ensure_schema() pattern: safe to run repeatedly,
drops and rebuilds only the derived FTS indexes (never the source nam/nsm/num
tables), and does nothing if the columns already match.

Run: python scripts/migrate_multilingual_fts.py
"""
import os
import sqlite3
import sys

DB_PATH = "db/ayush_icd11_combined.db"

# (table, fts_table, columns) — columns order matters only for readability;
# FTS5 doesn't care, callers reference by name.
MIGRATIONS = [
    ("nam", "nam_fts", ["namc_code", "namc_term", "namc_term_devanagari", "name_english", "long_definition"]),
    ("nsm", "nsm_fts", ["namc_code", "namc_term", "tamil_term", "short_definition"]),
    ("num", "num_fts", ["numc_code", "arabic_term", "numc_term", "short_definition"]),
]


def _current_fts_columns(cur, fts_table: str):
    cur.execute(f"PRAGMA table_info({fts_table})")
    return [r[1] for r in cur.fetchall()]


def migrate(db_path: str = DB_PATH) -> None:
    if not os.path.exists(db_path):
        print(f"No database at {db_path} — nothing to migrate (a fresh scripts/init.py build already includes this).")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for table, fts_table, columns in MIGRATIONS:
        cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name=?", (fts_table,))
        exists = cur.fetchone() is not None

        if exists and set(_current_fts_columns(cur, fts_table)) == set(columns):
            print(f"{fts_table}: already indexes {columns} — skipping.")
            continue

        print(f"{fts_table}: rebuilding to index {columns} (native-script term included)...")
        cur.execute(f"DROP TABLE IF EXISTS {fts_table}")
        columns_sql = ", ".join(columns)
        cur.execute(f"""
            CREATE VIRTUAL TABLE {fts_table} USING fts5(
                {columns_sql},
                content='{table}',
                content_rowid='rowid'
            )
        """)
        cur.execute(f"INSERT INTO {fts_table}({columns_sql}) SELECT {columns_sql} FROM {table}")
        conn.commit()
        print(f"{fts_table}: rebuilt.")

    conn.close()
    print("Multilingual FTS migration complete.")


if __name__ == "__main__":
    migrate(sys.argv[1] if len(sys.argv) > 1 else DB_PATH)
