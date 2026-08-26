#!/usr/bin/env python3
"""
Generates a SYNTHETIC population-health demo dataset — 2,000-2,500 fabricated
patient records and encounters, for a "what would this look like with real
usage volume" demo view.

THIS IS NOT REAL DATA. No patient, encounter, or usage record exists
anywhere else in this codebase (see app/analytics.py's own docstring, which
explicitly refuses to show a fabricated encounter count on the real
governance dashboard). This script exists specifically to produce a
separate, unmistakably-labeled dataset for a *different* page
(Population Health Demo) that a government/Ministry stakeholder might want
to see illustrated with realistic volume — every table, API response, and
UI surface for this data says "SYNTHETIC" because none of it should ever be
read as real by a judge, a stakeholder, or a future maintainer skimming the
database.

Every row is tied to a REAL NAMASTE code drawn from the actual nam/nsm/num
tables (so terminology distribution is genuine), with a FABRICATED patient
attached to it (gender, age band, region, encounter date) — the code is
real, the patient is not.

Run: python scripts/generate_synthetic_population.py [--count 2200] [--seed 42]
"""
import argparse
import random
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = "db/ayush_icd11_combined.db"

# Real Indian states/UTs, roughly population-weighted (not precise census
# figures — a reasonable spread for a demo, not a claimed accurate model).
REGIONS = [
    ("Uttar Pradesh", 14), ("Maharashtra", 11), ("Bihar", 9), ("West Bengal", 8),
    ("Madhya Pradesh", 7), ("Tamil Nadu", 7), ("Rajasthan", 6), ("Karnataka", 6),
    ("Gujarat", 6), ("Andhra Pradesh", 5), ("Odisha", 4), ("Telangana", 4),
    ("Kerala", 4), ("Punjab", 3), ("Assam", 3), ("Delhi", 3),
]

GENDERS = [("Female", 51), ("Male", 48), ("Other", 1)]

AGE_BANDS = [
    ("0-17", 15), ("18-29", 22), ("30-44", 25), ("45-59", 20), ("60-74", 13), ("75+", 5),
]

TRADITION_TABLES = [
    ("Ayurveda", "nam", "namc_code"),
    ("Siddha", "nsm", "namc_code"),
    ("Unani", "num", "numc_code"),
]
TRADITION_WEIGHTS = [70, 15, 15]  # Ayurveda dominant in the real curated corpus too


def _weighted_choice(pairs):
    values, weights = zip(*pairs)
    return random.choices(values, weights=weights, k=1)[0]


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS synthetic_patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_ref TEXT NOT NULL UNIQUE,
            gender TEXT NOT NULL,
            age_band TEXT NOT NULL,
            region TEXT NOT NULL,
            is_synthetic INTEGER NOT NULL DEFAULT 1,
            generated_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS synthetic_encounters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL REFERENCES synthetic_patients(id),
            encounter_date TEXT NOT NULL,
            tradition TEXT NOT NULL,
            namaste_code TEXT NOT NULL,
            is_synthetic INTEGER NOT NULL DEFAULT 1,
            generated_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_synth_enc_date ON synthetic_encounters(encounter_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_synth_enc_patient ON synthetic_encounters(patient_id)")
    conn.commit()


def _real_codes_by_tradition(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    codes = {}
    for tradition, table, code_col in TRADITION_TABLES:
        cur.execute(f"SELECT DISTINCT {code_col} FROM {table} WHERE {code_col} IS NOT NULL AND TRIM({code_col}) != ''")
        codes[tradition] = [r[0] for r in cur.fetchall()]
    return codes


def generate(count: int, seed: int, months_back: int = 12) -> None:
    random.seed(seed)
    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM synthetic_patients")
    if cur.fetchone()[0] > 0:
        print("synthetic_patients already populated — clearing before regenerating (idempotent).")
        cur.execute("DELETE FROM synthetic_encounters")
        cur.execute("DELETE FROM synthetic_patients")
        conn.commit()

    codes_by_tradition = _real_codes_by_tradition(conn)
    now = datetime.now(timezone.utc)
    generated_at = now.isoformat()

    patient_ids = []
    for i in range(count):
        ref = f"SYN-P-{i+1:05d}"
        gender = _weighted_choice(GENDERS)
        age_band = _weighted_choice(AGE_BANDS)
        region = _weighted_choice(REGIONS)
        cur.execute(
            "INSERT INTO synthetic_patients (patient_ref, gender, age_band, region, is_synthetic, generated_at) VALUES (?, ?, ?, ?, 1, ?)",
            (ref, gender, age_band, region, generated_at),
        )
        patient_ids.append(cur.lastrowid)

    # 1-3 encounters per patient, spread over the trailing `months_back` months.
    encounter_rows = []
    for patient_id in patient_ids:
        n_encounters = random.choices([1, 2, 3], weights=[60, 30, 10], k=1)[0]
        for _ in range(n_encounters):
            tradition = _weighted_choice(list(zip([t[0] for t in TRADITION_TABLES], TRADITION_WEIGHTS)))
            code_pool = codes_by_tradition.get(tradition) or []
            if not code_pool:
                continue
            code = random.choice(code_pool)
            days_back = random.randint(0, months_back * 30)
            enc_date = (now - timedelta(days=days_back)).date().isoformat()
            encounter_rows.append((patient_id, enc_date, tradition, code, generated_at))

    cur.executemany(
        "INSERT INTO synthetic_encounters (patient_id, encounter_date, tradition, namaste_code, is_synthetic, generated_at) VALUES (?, ?, ?, ?, 1, ?)",
        encounter_rows,
    )
    conn.commit()

    print(f"Generated {len(patient_ids)} synthetic patients and {len(encounter_rows)} synthetic encounters.")
    print("Every row is flagged is_synthetic=1 — see app/population_analytics.py for how it's surfaced.")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=2200, help="Number of synthetic patients (2000-2500 range)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    args = parser.parse_args()
    if not (2000 <= args.count <= 2500):
        raise SystemExit("--count must be between 2000 and 2500 to match the requested demo scale")
    generate(args.count, args.seed)
