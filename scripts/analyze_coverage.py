import sqlite3

DB = "db/ayush_icd11_combined.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

SEP = "-" * 52

# ── 1. NAMASTE (nam) coverage ─────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM nam")
total_nam = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT source_code) FROM concept_map")
mapped_nam = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM nam
    WHERE namc_code NOT IN (SELECT DISTINCT source_code FROM concept_map)
""")
unmapped_nam = cur.fetchone()[0]

print("NAMASTE (nam) Coverage")
print(SEP)
print(f"  Total concepts   : {total_nam:,}")
print(f"  Mapped           : {mapped_nam:,}  ({mapped_nam/total_nam*100:.1f}%)")
print(f"  UNMAPPED         : {unmapped_nam:,}  ({unmapped_nam/total_nam*100:.1f}%)")

# ── 2. Siddha (nsm) coverage ─────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM nsm")
total_nsm = cur.fetchone()[0]
# nsm codes use namc_code column too
cur.execute("""
    SELECT COUNT(*) FROM nsm
    WHERE namc_code NOT IN (SELECT DISTINCT source_code FROM concept_map)
""")
unmapped_nsm = cur.fetchone()[0]
mapped_nsm = total_nsm - unmapped_nsm

print(f"\nSIDDHA (nsm) Coverage")
print(SEP)
print(f"  Total concepts   : {total_nsm:,}")
print(f"  Mapped           : {mapped_nsm:,}  ({mapped_nsm/total_nsm*100:.1f}%)")
print(f"  UNMAPPED         : {unmapped_nsm:,}  ({unmapped_nsm/total_nsm*100:.1f}%)")

# ── 3. Unani (num) coverage ───────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM num")
total_num = cur.fetchone()[0]
cur.execute("PRAGMA table_info(num)")
num_cols = [r["name"] for r in cur.fetchall()]
# find the code column
code_col_num = "numc_code" if "numc_code" in num_cols else num_cols[2]
cur.execute(f"""
    SELECT COUNT(*) FROM num
    WHERE {code_col_num} NOT IN (SELECT DISTINCT source_code FROM concept_map)
""")
unmapped_num = cur.fetchone()[0]
mapped_num = total_num - unmapped_num

print(f"\nUNANI (num) Coverage  [code col: {code_col_num}]")
print(SEP)
print(f"  Total concepts   : {total_num:,}")
print(f"  Mapped           : {mapped_num:,}  ({mapped_num/total_num*100:.1f}%)")
print(f"  UNMAPPED         : {unmapped_num:,}  ({unmapped_num/total_num*100:.1f}%)")

# ── 4. AST dataset ────────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM ast")
total_ast = cur.fetchone()[0]
cur.execute("""
    SELECT COUNT(*) FROM ast
    WHERE code NOT IN (SELECT DISTINCT source_code FROM concept_map)
      AND code NOT IN (SELECT DISTINCT target_code FROM concept_map)
""")
unmapped_ast = cur.fetchone()[0]

print(f"\nAYURVEDA STD TERMS (ast) Coverage")
print(SEP)
print(f"  Total concepts   : {total_ast:,}")
print(f"  UNMAPPED         : {unmapped_ast:,}  ({unmapped_ast/total_ast*100:.1f}%)")

# ── 5. ICD-11 coverage ────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM icd11")
total_icd = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT target_code) FROM concept_map")
mapped_icd = cur.fetchone()[0]
unmapped_icd = total_icd - mapped_icd

print(f"\nICD-11 TM2 Coverage (as target)")
print(SEP)
print(f"  Total concepts   : {total_icd:,}")
print(f"  Targeted (mapped): {mapped_icd:,}  ({mapped_icd/total_icd*100:.1f}%)")
print(f"  UNMAPPED         : {unmapped_icd:,}  ({unmapped_icd/total_icd*100:.1f}%)")

# ── 6. Grand summary ──────────────────────────────────────────────────────
total_all_source = total_nam + total_nsm + total_num
unmapped_all_source = unmapped_nam + unmapped_nsm + unmapped_num
mapped_all_source = total_all_source - unmapped_all_source

print(f"\nGRAND SUMMARY (NAMASTE source datasets)")
print(SEP)
print(f"  Total source concepts (nam+nsm+num) : {total_all_source:,}")
print(f"  Currently mapped                    : {mapped_all_source:,}  ({mapped_all_source/total_all_source*100:.1f}%)")
print(f"  UNMAPPED TOTAL                      : {unmapped_all_source:,}  ({unmapped_all_source/total_all_source*100:.1f}%)")
print(f"  Total mappings in concept_map       : 468  (218 equivalent + 250 related)")

# ── 7. Unmapped NAMASTE by prefix ────────────────────────────────────────
cur.execute("""
    SELECT
        SUBSTR(namc_code, 1, 2) AS prefix,
        COUNT(*) AS total,
        SUM(CASE WHEN namc_code IN (SELECT DISTINCT source_code FROM concept_map) THEN 1 ELSE 0 END) AS mapped,
        SUM(CASE WHEN namc_code NOT IN (SELECT DISTINCT source_code FROM concept_map) THEN 1 ELSE 0 END) AS unmapped
    FROM nam
    GROUP BY prefix
    ORDER BY total DESC
""")
rows = cur.fetchall()
print(f"\nNAMASTE Unmapped by Prefix (nam table)")
print(f"  {'Prefix':<8} {'Total':>7} {'Mapped':>8} {'Unmapped':>10} {'Coverage':>10}")
print("  " + "-" * 48)
for r in rows:
    pct = (r["mapped"] / r["total"] * 100) if r["total"] else 0
    bar = "#" * int(pct / 10) + "." * (10 - int(pct / 10))
    print(f"  {r['prefix']:<8} {r['total']:>7,} {r['mapped']:>8,} {r['unmapped']:>10,} {pct:>8.1f}%  [{bar}]")

# ── 8. Sample unmapped NAMASTE codes ─────────────────────────────────────
cur.execute("""
    SELECT namc_code, namc_term, name_english
    FROM nam
    WHERE namc_code NOT IN (SELECT DISTINCT source_code FROM concept_map)
    ORDER BY namc_code
    LIMIT 15
""")
samples = cur.fetchall()
print(f"\nSample Unmapped NAMASTE Concepts (15 of {unmapped_nam:,})")
print("  " + "-" * 70)
for r in samples:
    eng = (r["name_english"] or "")[:30]
    print(f"  {r['namc_code']:<22} | {(r['namc_term'] or '')[:35]:<35} | {eng}")

conn.close()
