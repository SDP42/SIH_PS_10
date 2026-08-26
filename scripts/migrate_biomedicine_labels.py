"""
Data-correction migration: concept_map.target_system was hardcoded to
'ICD-11 TM2' for every one of the 468 curated rows by the original 5-pass
mapping script, regardless of which ICD-11 chapter the target_code actually
falls in. Chapter 26 is real TM2 (and TM1); chapters 01-25 are Biomedicine.

Cross-checking target_code against icd11.chapterno found ~247 of the 468
rows actually target Biomedicine-chapter codes, mislabeled as TM2. Those
came from the 5-pass algorithm's fuzzier stages (single-token FTS / partial
English matching), which were never precision-validated the way the exact
and bracket-trim passes were.

This script:
  1. Relabels every concept_map.target_system correctly from the objective
     fact of which chapter its target_code belongs to (chapter membership
     isn't a judgment call, so this part needs no human review).
  2. For every row newly relabeled to 'ICD-11 Biomedicine', enqueues it into
     the existing governance review_queue (flag_type='legacy_reclassification')
     so a human confirms match *quality* before it's trusted as curated,
     rather than silently presenting an unvalidated fuzzy match as ground
     truth.

Idempotent and safe to rerun: relabeling is deterministic, and
enqueue_legacy_reclassification dedupes on (concept_map_id, pending).
"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import governance  # noqa: E402

DB_PATH = "db/ayush_icd11_combined.db"


def _target_kind(chapterno: str, title: str) -> str:
    if chapterno == "26":
        return "ICD-11 TM2" if "(TM2)" in (title or "") else "ICD-11 TM1 (unsupported)"
    return "ICD-11 Biomedicine"


def migrate():
    governance.ensure_schema()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT cm.id, cm.source_system, cm.source_code, cm.target_system AS old_target_system,
               cm.target_code, i.chapterno, i.title
        FROM concept_map cm
        LEFT JOIN icd11 i ON cm.target_code = i.code
        """
    )
    rows = [dict(r) for r in cur.fetchall()]

    relabeled_to_biomedicine = 0
    relabeled_to_tm2 = 0
    unchanged = 0
    unknown_target = 0
    to_enqueue = []

    # Pass 1: apply and commit all relabeling first, then close this
    # connection — enqueue_legacy_reclassification opens its own connection
    # per call, and SQLite will lock if we try that while still holding an
    # uncommitted write transaction open here.
    for row in rows:
        if row["chapterno"] is None:
            unknown_target += 1
            continue

        correct_system = _target_kind(row["chapterno"], row["title"])

        if correct_system != row["old_target_system"]:
            cur.execute(
                "UPDATE concept_map SET target_system = ? WHERE id = ?",
                (correct_system, row["id"]),
            )
            if correct_system == "ICD-11 Biomedicine":
                relabeled_to_biomedicine += 1
            elif correct_system == "ICD-11 TM2":
                relabeled_to_tm2 += 1
        else:
            unchanged += 1

        if correct_system == "ICD-11 Biomedicine":
            to_enqueue.append((row, correct_system))

    conn.commit()
    conn.close()

    # Pass 2: enqueue review-queue rows for every Biomedicine-relabeled row.
    enqueued = 0
    for row, correct_system in to_enqueue:
        queue_id = governance.enqueue_legacy_reclassification(
            source_system=row["source_system"],
            source_code=row["source_code"],
            concept_map_id=row["id"],
            target_code=row["target_code"],
            target_title=row["title"],
            target_system=correct_system,
            rationale=(
                f"Legacy mapping originally labeled '{row['old_target_system']}' — "
                f"target_code '{row['target_code']}' is actually in ICD-11 chapter "
                f"{row['chapterno']} ('{row['title']}'), i.e. Biomedicine, not TM2. "
                "Relabeled automatically (chapter membership is a fact); match "
                "quality itself was produced by a fuzzy-matching pass and has not "
                "been human-validated — please confirm or reject."
            ),
        )
        if queue_id:
            enqueued += 1

    print(f"Scanned {len(rows)} concept_map rows.")
    print(f"  Relabeled to ICD-11 TM2:         {relabeled_to_tm2}")
    print(f"  Relabeled to ICD-11 Biomedicine: {relabeled_to_biomedicine}")
    print(f"  Already correctly labeled:       {unchanged}")
    print(f"  Target code not found in icd11:  {unknown_target}")
    print(f"Enqueued {enqueued} legacy Biomedicine rows for human review confirmation.")


if __name__ == "__main__":
    migrate()
