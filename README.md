<div align="center">

# 🌿 NAMASTE × ICD-11 Integration

### *Bridging Traditional Wisdom with Modern Medical Standards*

**A FHIR R4-Compliant Terminology Microservice** — Seamlessly integrating India's **NAMASTE** codes with **WHO's ICD-11 Traditional Medicine Module 2 (TM2)** for next-generation EMR interoperability.

[![Ministry of AYUSH](https://img.shields.io/badge/Organization-Ministry_of_AYUSH-FF6600?style=flat-square)](https://ayush.gov.in)
[![FHIR R4](https://img.shields.io/badge/Standard-FHIR_R4-E53935?style=flat-square)](https://hl7.org/fhir/R4/)
[![ICD-11 TM2](https://img.shields.io/badge/WHO-ICD--11_TM2-1B5E20?style=flat-square)](https://icd.who.int/)
[![Python](https://img.shields.io/badge/Python-3.10+-F9A825?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.117-00897B?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![SQLite](https://img.shields.io/badge/SQLite-FTS5-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)

</div>

---

## 📖 Table of Contents

- [Problem Statement](#-problem-statement)
- [What We Built](#-what-we-built)
- [Mapping Coverage](#-mapping-coverage)
- [Architecture](#️-architecture)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Frontend Dashboard](#️-frontend-dashboard)
- [Testing](#-testing)
- [Database Schema](#️-database-schema)
- [Mapping Strategy](#-mapping-strategy)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🎯 Problem Statement

> **Develop API code to integrate NAMASTE (National AYUSH Morbidity & Standardized Terminologies Electronic) and the International Classification of Diseases (ICD-11) via the Traditional Medicine Module 2 (TM2) into existing EMR systems that comply with Electronic Health Record (EHR) Standards for India.**
>
> — *Ministry of Ayush | All India Institute of Ayurveda (AIIA) | Smart India Hackathon 2026*

### The Core Challenge

Traditional medicine practitioners in Ayurveda, Siddha, and Unani use **NAMASTE** — India's national standard for traditional medicine coding. Modern hospitals use **ICD-11** — the WHO's global disease classification. These two systems have **no standard bridge**, which means:

- Patient records are fragmented across traditional and modern facilities
- Dual coding (NAMASTE + ICD-11) is done manually, leading to errors
- No machine-readable interoperability exists between AYUSH and allopathic EMRs
- Clinical research comparing traditional and modern outcomes is impossible

**Our solution:** A FHIR R4-compliant API microservice that creates the authoritative, machine-readable bridge between NAMASTE and ICD-11 TM2, enabling seamless EMR interoperability.

---

## ✨ What We Built

A **full-stack FHIR R4-compliant terminology microservice**:

```
┌───────────────────────────────────────────────────────────────────────┐
│                       NAMASTE × ICD-11 Platform                        │
│                                                                         │
│  ┌──────────────────┐    ┌────────────────────┐    ┌───────────────┐  │
│  │   React SPA      │───▶│  FastAPI Backend    │───▶│ SQLite + FTS5 │  │
│  │   Dashboard      │    │  (FHIR R4 REST API) │    │  468 mappings │  │
│  │  (5 pages)       │    │  9 endpoints        │    │  +FTS indexes │  │
│  └──────────────────┘    └────────────────────┘    └───────────────┘  │
│                                                                         │
│  ● 468 curated concept mappings (218 equivalent + 250 relatedto)       │
│  ● 296 unique NAMASTE codes bidirectionally mapped                      │
│  ● 437 unique ICD-11 TM2 codes linked                                   │
│  ● FTS5-powered sub-100ms full-text search across both terminologies   │
│  ● FHIR R4 ConceptMap resource serialization with equivalence flags     │
│  ● One-command setup — everything auto-downloaded and configured        │
└───────────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| 🔄 **Bidirectional Lookup** | NAMASTE → ICD-11 **and** ICD-11 → NAMASTE |
| 🔍 **Full-Text Search** | FTS5-indexed search across 700+ concepts in milliseconds |
| 📋 **FHIR R4 Compliant** | ConceptMap resources with proper `equivalent` / `relatedto` flags |
| 🖥️ **Web Dashboard** | React + TypeScript SPA with 5 dedicated views |
| 🧪 **Full Test Coverage** | API, FHIR compliance, mapping logic, and extended endpoint tests |
| ⚙️ **One-Command Setup** | `python scripts/init.py` — downloads data, builds DB, generates mappings |
| 📊 **Audit Exports** | CSV + summary exports for governance and clinical review |
| 🏥 **EMR-Ready** | Drop-in REST API for AYUSH and allopathic EMR integration |
| 🌐 **WHO ICD-API Sync** | Live OAuth2 sync against WHO's ICD-API with drift detection — degrades to the offline snapshot when WHO is unreachable |
| 🗣️ **Multilingual** | Real Devanagari/Tamil/Arabic terminology search (not translated — sourced from the NAMASTE CSVs) + English/Hindi/Marathi/Gujarati UI |
| 💬 **Clinical Text Assistant** | Free-text symptom extraction (negation/duration/site-aware) with real terminology candidates — never infers a diagnosis |
| 🔑 **API Key Developer Platform** | Real key issuance, scopes, rate limiting, rotation/revocation, and a versioned `/api/v1` surface an EMR could actually integrate against |
| 🧪 **Population Health Demo** | 2,200 synthetic patients across gender/region/time, structurally isolated from — and never mixed into — the real governance analytics |
| 🔀 **Terminology What-If Simulator** | Diffs any two real WHO ICD-11 releases and reports exactly which curated mappings would break or go ambiguous — before the release ships |
| ⛓️ **Tamper-Evident Audit Ledger** | Hash-chains the real audit trail — editing any row directly in the database is caught, and the exact row is named |
| 🛡️ **Terminology Firewall** | Composes existing validation logic into one accept/reject/review gateway verdict for incoming FHIR Bundles |
| 🎙️ **Voice Terminology Assistant** | Browser-native speech in/out (no external voice API) routed to the existing engines — answers project questions only from a controlled knowledge base, never invents an answer |
| 📍 **Regional Disease Intelligence** | Population Health Demo now ranks real NAMASTE conditions nationally and per-region — the exact drill-down a government analyst needs |

---

## 📊 Mapping Coverage

### Overall Statistics

<div align="center">

| Metric | Count | Notes |
|--------|:-----:|-------|
| **Total Concept Mappings** | **468** | Across all NAMASTE prefixes |
| **High-Confidence Equivalent** | **218** | Direct code or title agreement |
| **Clinical Context Related** | **250** | Useful anchors for dual coding |
| **Unique NAMASTE Codes Mapped** | **296** | Out of full NAMASTE corpus |
| **Unique ICD-11 TM2 Codes Linked** | **437** | Across all TM2 chapters |
| **Terminologies Supported** | **2** | NAMASTE v1.2 + ICD-11 v2022.1 |

</div>

### Coverage by NAMASTE Prefix (Detailed)

| Prefix | Clinical Domain | Total Mappings | Equivalent | Related | Unique NAMASTE | Unique ICD-11 |
|--------|----------------|:--------------:|:----------:|:-------:|:--------------:|:-------------:|
| `ED` | Examination Diagnostics | **151** | 42 | 109 | 6 | 141 |
| `SM` | Srotas / Manifestation Disorders | **82** | 76 | 6 | 80 | 80 |
| `SK` | Skin & Dermatological (Tvacha) | **62** | 62 | 0 | 62 | 62 |
| `SN` | Snayu — Ligaments & Tendons | **40** | 40 | 0 | 40 | 40 |
| `SP` | Specific Pathologies | **33** | 12 | 21 | 28 | 31 |
| `SR` | Srotovaha Roga (Channel Disorders) | **24** | 24 | 0 | 24 | 24 |
| `SS` | Sandhi Shotha (Joint Inflammation) | **19** | 19 | 0 | 19 | 19 |
| `SL` | Shalya (Surgical Conditions) | **19** | 17 | 2 | 17 | 18 |
| `EC` | External / Environmental Conditions | **19** | 0 | 19 | 2 | 19 |
| `SQ` | Sequential / Progressive Patterns | **13** | 13 | 0 | 13 | 13 |
| *Others* | Additional NAMASTE prefixes | **6** | 3 | 3 | 5 | 5 |
| **Total** | | **468** | **218** | **250** | **296** | **437** |

### Relationship Mix

```
Equivalent Links (218) ████████████████████████░░░░░░  46.6%
  → Strong lexical/code agreement → ideal for automated dual coding
  → Confidence score: 0.98

Related Links (250)    ███████████████████████████░░░  53.4%
  → Useful clinical anchors for context-based ICD-11 assignment
  → Confidence score: 0.72
  → Recommended for human review before strict clinical adoption
```

### Sample Mappings

| NAMASTE Code | NAMASTE Term | ICD-11 TM2 Code | Relationship |
|-------------|--------------|:---------------:|:------------:|
| `SR11 (AAA-1)` | Vatavyadhi — Vata disorder | `SR11` | `equivalent` |
| `SK84 (AAB-15)` | Kushtha — Skin disorder | `SK84` | `equivalent` |
| `SM33 (EB-10)` | Grahani — Digestive disorder | `SM33` | `relatedto` |
| `ED-14` | Nadi pariksha finding | `EB01.1` | `relatedto` |
| `EC-7` | Ahara vihara factor | `6B80.0` | `relatedto` |
| `SN22` | Gridhrasi — Sciatica | `SN22` | `equivalent` |
| `SP41` | Amavata — Rheumatoid pattern | `SP41` | `equivalent` |

---

## 🏗️ Architecture

```
NAMASTE-ICD-11-Integration/
│
├── 🐍 Backend (Python / FastAPI)
│   ├── app/
│   │   ├── main.py           — FastAPI app + serves React SPA
│   │   ├── api.py            — Extended REST API (9 endpoints)
│   │   └── conceptmap.py     — FHIR R4 ConceptMap router
│   └── requirements.txt
│
├── ⚛️  Frontend (React 18 + TypeScript 5.5 + Vite)
│   └── frontend/src/
│       ├── pages/
│       │   ├── Overview.tsx            — Live dashboard stats
│       │   ├── TerminologyExplorer.tsx — Side-by-side concept browser
│       │   ├── MappingIntelligence.tsx — Mapping filter & explorer
│       │   ├── FhirWorkspace.tsx       — FHIR resource playground
│       │   └── Settings.tsx            — API config & preferences
│       ├── components/
│       │   └── AppShell.tsx            — Navigation shell
│       └── api/
│           ├── client.ts               — Axios client
│           └── index.ts                — API query hooks
│
├── 🗄️  Database (SQLite 3 + FTS5)
│   └── db/ayush_icd11_combined.db    — Auto-created by scripts/init.py
│       ├── nam                        — NAMASTE codes & terms
│       ├── icd11                      — ICD-11 TM2 codes & titles
│       ├── nsm / num / ast            — Additional NAMASTE tables
│       ├── concept_map                — 468 curated mappings
│       └── *_fts                      — FTS5 virtual tables
│
├── 📜 Scripts (Automation Pipeline)
│   ├── init.py               — Master orchestrator (run this first)
│   ├── create_database.py    — Schema + FTS5 index creation
│   ├── download_namaste.py   — Fetch NAMASTE CSV dataset
│   ├── download_icd11.py     — Fetch ICD-11 TM2 CSV dataset
│   ├── normalize_database.py — Code whitespace normalization
│   ├── create_concept_map.py — 5-pass mapping generation
│   ├── export_mappings.py    — CSV + summary export
│   └── analyze_coverage.py   — Coverage analysis report
│
└── 🧪 Tests
    ├── run_tests.py           — Test runner
    ├── test_api.py            — REST API behaviour tests
    ├── test_fhir.py           — FHIR R4 compliance tests
    ├── test_logic.py          — Mapping logic correctness
    └── test_extended_api.py   — Extended endpoint coverage
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** *(frontend only)*
- **Git**

### Backend Setup

**1. Clone the repository**
```bash
git clone https://github.com/SDP42/SIH_PS_10.git
cd SIH_PS_10/NAMASTE-ICD-11-Integration
```

**2. Create & activate virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate       # Windows
```

**3. Install Python dependencies**
```bash
pip install -r requirements.txt
```

**4. One-command setup — downloads data, builds DB, generates mappings**
```bash
python scripts/init.py
```

This orchestrator will:
- ✅ Download NAMASTE and ICD-11 TM2 datasets automatically
- ✅ Create the optimized SQLite database with FTS5 full-text indexes
- ✅ Normalize code formatting (whitespace, casing) across both datasets
- ✅ Generate all 468 curated concept mappings via 5-pass algorithm
- ✅ Validate schema integrity and print a detailed setup summary

**5. Start the API server**
```bash
uvicorn app.main:app --reload
```

> 📖 **Swagger docs:** http://localhost:8000/docs  
> 📋 **ReDoc:** http://localhost:8000/redoc

---

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

> 🖥️ **Dashboard:** http://localhost:5173 — you'll land on an **ABHA Demo Mode** login screen first;
> enter any name/role to continue (no password, no real ABHA — see "AI / Governance Layer" below).

### Production (Unified Serving)

```bash
# Build the React app
cd frontend && npm run build

# FastAPI auto-serves the React SPA from /frontend/dist
cd ..
uvicorn app.main:app
```

> Everything runs on a single port — **http://localhost:8000**

---

## 🔗 API Reference

### FHIR ConceptMap Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/ConceptMap` | List all FHIR R4 ConceptMap resources |
| `GET` | `/ConceptMap/{code}` | Get FHIR mappings for a specific NAMASTE code |

### Extended REST API (`/api/`)

| Method | Endpoint | Query Params | Description |
|--------|----------|-------------|-------------|
| `GET` | `/api/stats` | — | Dashboard statistics: counts, system health |
| `GET` | `/api/concepts` | `system`, `q`, `page`, `page_size` | Paginated concept browser |
| `GET` | `/api/search` | `q`, `system`, `page`, `page_size` | Unified FTS search |
| `GET` | `/api/mappings` | `source_code`, `target_code`, `equivalence`, `q`, `page` | Browse & filter mappings |
| `GET` | `/api/mappings/{id}` | — | Full detail for a single mapping |
| `GET` | `/api/terminologies` | — | Terminology system metadata |
| `GET` | `/api/concept/{system}/{code}` | — | Single concept with its mappings |

### WHO ICD-11 Synchronisation (`/api/who/`)

| Method | Endpoint | Query Params | Description |
|--------|----------|-------------|-------------|
| `GET` | `/api/who/status` | — | Live-vs-snapshot posture: credentials, last sync, cache coverage, open drift |
| `GET` | `/api/who/releases` | — | ICD-11 MMS releases WHO publishes, and whether our snapshot is the latest |
| `GET` | `/api/who/code/{code}` | `release`, `force` | Resolve one code against WHO, with explicit provenance |
| `GET` | `/api/who/drift` | `limit` | Codes whose WHO title no longer matches the snapshot |
| `GET` | `/api/who/history` | `limit` | Past sync runs, including ones that could not reach WHO |
| `POST` | `/api/who/sync` | body: `limit`, `release` | Run a sync pass — **requires ABHA Demo Mode auth** |

### Example Calls

```bash
# FHIR ConceptMap for a vata pattern code
curl "http://localhost:8000/ConceptMap/SR10%20(AAA-2.1)"

# FHIR ConceptMap for an examination finding
curl "http://localhost:8000/ConceptMap/ED-6.10"

# Search across both terminologies
curl "http://localhost:8000/api/search?q=vata&system=both"

# All high-confidence equivalent mappings (page 1)
curl "http://localhost:8000/api/mappings?equivalence=equivalent&page=1&page_size=20"

# System statistics
curl "http://localhost:8000/api/stats"

# Single NAMASTE concept with its ICD-11 mappings
curl "http://localhost:8000/api/concept/namaste/SR11%20(AAA-1)"

# Browse ICD-11 concepts with search
curl "http://localhost:8000/api/concepts?system=icd11&q=skin&page=1"
```

### FHIR ConceptMap Response

```json
{
  "resourceType": "ConceptMap",
  "id": "namaste-icd11-conceptmap",
  "url": "http://terminology.ayush.gov.in/ConceptMap/namaste-icd11",
  "version": "1.0.0",
  "name": "NAMASTE_ICD11_ConceptMap",
  "title": "NAMASTE to ICD-11 TM2 Concept Map",
  "status": "active",
  "group": [
    {
      "source": "http://terminology.ayush.gov.in/CodeSystem/namaste",
      "target": "http://id.who.int/icd/entity",
      "element": [
        {
          "code": "ED-6.10",
          "target": [
            { "code": "ED00", "equivalence": "equivalent" }
          ]
        }
      ]
    }
  ]
}
```

---

## 🖥️ Frontend Dashboard

Five dedicated views in the React + TypeScript SPA:

| Page | Description |
|------|-------------|
| 📊 **Overview** | Live stats — total mappings, concept counts, terminology system health |
| 🔍 **Terminology Explorer** | Paginated browser for NAMASTE & ICD-11 concepts with full-text search |
| 🗺️ **Mapping Intelligence** | Filter by code, equivalence, or term; inspect mapping details |
| 🏥 **FHIR Workspace** | Interactive ConceptMap resource builder and query playground |
| ⚙️ **Settings** | API endpoint configuration and display preferences |

**Frontend tech stack:**
- React 18 + TypeScript 5.5
- Vite (build tooling)
- TanStack Query v5 (async state)
- Axios (HTTP client)
- React Router v6 (SPA routing)
- Lucide React (icons)

---

## 🧪 Testing

### Run the full test suite

```bash
python tests/run_tests.py
```

Validates:
- ✅ Database connectivity, schema integrity, and FTS index availability
- ✅ Concept mapping precision and equivalence tagging
- ✅ FHIR R4 ConceptMap compliance and JSON serialization
- ✅ REST API behaviour, URL encoding, and error handling
- ✅ Extended endpoints: stats, search, mappings, concept lookups

### Export mappings for audit

```bash
python scripts/export_mappings.py
```

Generates in `output/`:

| File | Contents |
|------|----------|
| `namaste_icd11_mappings_[timestamp].csv` | Full 468-row export |
| `namaste_icd11_mappings_[timestamp]_summary.txt` | Prefix breakdown statistics |
| `namaste_icd11_sample_[timestamp].csv` | Sample set (up to 10 per prefix) |

---

## 🗄️ Database Schema

**Database:** `db/ayush_icd11_combined.db` (SQLite 3, auto-created)

| Table | Columns | Description |
|-------|---------|-------------|
| `nam` | `namc_code`, `namc_term`, `name_english`, `namc_term_devanagari`, `short_definition` | NAMASTE Ayurveda morbidity codes |
| `icd11` | `code`, `title` | ICD-11 TM2 codes and English titles |
| `nsm` | NAMASTE Siddha medicine codes | Additional NAMASTE modules |
| `num` | NAMASTE Unani medicine codes | Additional NAMASTE modules |
| `ast` | NAMASTE AST codes | Additional NAMASTE modules |
| `concept_map` | `id`, `source_system`, `source_code`, `target_system`, `target_code`, `equivalence` | 468 curated NAMASTE ↔ ICD-11 mappings |
| `nam_fts` | FTS5 virtual | Full-text index over NAMASTE terms |
| `icd11_fts` | FTS5 virtual | Full-text index over ICD-11 titles |

### Sample SQL Queries

```sql
-- Mapping counts by NAMASTE prefix
SELECT SUBSTR(source_code, 1, 2) AS prefix, COUNT(*) AS count,
       SUM(equivalence = 'equivalent') AS equiv,
       SUM(equivalence = 'relatedto') AS related
FROM concept_map
GROUP BY prefix
ORDER BY count DESC;

-- All equivalent SR-family mappings
SELECT source_code, target_code FROM concept_map
WHERE source_code LIKE 'SR%' AND equivalence = 'equivalent';

-- Full concept join with display names
SELECT cm.source_code, n.namc_term, n.name_english,
       cm.target_code, i.title, cm.equivalence
FROM concept_map cm
JOIN nam n ON cm.source_code = n.namc_code
JOIN icd11 i ON cm.target_code = i.code
WHERE cm.source_code LIKE 'SM%';
```

---

## 🔬 Mapping Strategy

The pipeline uses a **5-pass precision-first algorithm** that prioritises correctness over volume:

### Pass 1 — Exact Code Alignment
```sql
INSERT INTO concept_map (...)
SELECT 'NAMASTE', n.namc_code, 'ICD-11 TM2', i.code, 'equivalent'
FROM nam_fts n JOIN icd11_fts i ON n.namc_code = i.code;
```
**Result:** Captures codes that are identical in both systems.

### Pass 2 — Bracket Trimming
```sql
-- "SR11 (AAA-1)" → extract "SR11" → match icd11.code = "SR11"
JOIN icd11_fts i ON TRIM(SUBSTR(n.namc_code, 1,
    CASE WHEN INSTR(n.namc_code, ' (') > 0
         THEN INSTR(n.namc_code, ' (') - 1
         ELSE LENGTH(n.namc_code) END)) = TRIM(i.code);
```
**Result:** Matches canonical fragments inside NAMASTE bracket notation.

### Pass 3 — Single-Token FTS Lookup
Performs English keyword search on `icd11_fts.title` for short, unambiguous nouns.
**Result:** Widens equivalent coverage for clear concept matches.

### Pass 4 — Exact English Title Parity
```sql
WHERE LOWER(TRIM(n.name_english)) = LOWER(TRIM(i.title))
```
**Result:** Links entries with identical English labels across both systems.

### Pass 5 — Bounded Partial Matching (cap: 150)
```sql
WHERE LOWER(i.title) LIKE '%' || token || '%'
  AND NOT EXISTS (SELECT 1 FROM concept_map WHERE ...)
LIMIT 150;
```
**Result:** Bounded `relatedto` associations for clinical context without diluting precision.

> 💡 Every pass has a `NOT EXISTS` deduplication guard — no source/target pair is ever inserted more than once.

---

## 🤖 AI / Governance Layer (New)

The 5-pass algorithm above is precision-first and deliberately conservative — it only produces
468 mappings, leaving thousands of NAMASTE-family codes (`nam`/`nsm`/`num`/`ast`) with **no**
curated ICD-11 equivalent. The AI layer targets exactly that gap, without ever silently guessing.

### Ambiguity-aware AI mapping engine

`scripts/build_embeddings.py` encodes every NAMASTE-family concept and every ICD-11 TM2 concept
with `sentence-transformers` (**all-MiniLM-L6-v2** — general-purpose, 384-dim, fast on CPU;
`cambridgeltl/SapBERT-from-PubMedBERT-fulltext` was evaluated but skipped as too large/slow for a
same-night offline build — see the script's docstring for the full rationale). Vectors are stored
as `.npy` files under `db/embeddings/` (not blobbed into SQLite), with an `embedding_index` table
mapping vector position → system/code/display text.

`app/ai_mapping.py` scores every ICD-11 candidate against a source concept's vector with plain
`numpy` cosine similarity (no FAISS/vector DB — unnecessary at this scale, ~40k vectors fit
comfortably in memory), blended with a lexical word-overlap signal, and classifies the result into
one of four **transparent decisions** — named threshold constants, never a silent guess:

| Decision | Meaning |
|---|---|
| `AUTO_SUGGEST` | Strong top score, clearly separated from the runner-up |
| `NEEDS_CONTEXT` | Moderate score, or several close candidates — genuinely ambiguous |
| `EXPERT_REVIEW` | Weak but non-trivial signal |
| `NO_VALIDATED_EQUIVALENT` | Every candidate below the floor — the engine refuses to guess |

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/ai/suggest/{code}` | Ranked TM2+Biomedicine-mixed candidates + decision + rationale |
| `GET` | `/api/ai/suggest/{code}/dual` | **Real double-coding**: independent TM2 and Biomedicine decisions for the same code |
| `GET` | `/api/ai/unmapped` | Paginated NAMASTE-family codes with no curated mapping |
| `POST` | `/api/ai/batch_suggest` | Suggestions for a code list, or `{"all_unmapped": true, "limit": 50}` |
| `GET` | `/api/ai/model-info` | Embedding model + build metadata |

### ICD-11 Biomedicine dual-coding — a real bug found and fixed

A direct DB audit found the `icd11` table already contains the full WHO ICD-11 Biomedicine
linearization (36,782 rows: chapters 01–25 are Biomedicine, ~35,536 concepts; chapter 26 is
Traditional Medicine, ~1,246 concepts) — it was simply never distinguished from TM2. Worse,
`concept_map.target_system` was hardcoded `'ICD-11 TM2'` for **all** 468 curated rows regardless
of which chapter the target actually fell in; **248 of them actually targeted Biomedicine
codes**, mislabeled.

`scripts/migrate_biomedicine_labels.py` (idempotent, run automatically by `scripts/init.py` step
4a) corrects every row's label from the objective fact of chapter membership, then routes every
row newly relabeled to Biomedicine into the governance `review_queue`
(`flag_type="legacy_reclassification"`) so a human confirms the underlying fuzzy-matched pairing
is actually correct before it's trusted — the mislabeling became a governance demo, not a silent
fix. `app/ai_mapping.py`'s `get_dual_candidates()` runs the AI engine against the TM2 and
Biomedicine chapter pools independently, each with its own decision tier.

### FHIR completeness — real double-coding

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/ConceptMap/$translate?system=&code=&target_system=BOTH\|ICD11-TM2\|ICD11-BIOMEDICINE` | Default `BOTH` returns one match group per system, each curated-first/AI-fallback; `unmatched` per-system when nothing validates, never silently dropped |
| `POST` | `/Bundle` | **Auth-gated.** Accepts a Bundle with a NAMASTE-coded Condition, returns it enriched with real dual TM2+Biomedicine codes + inline `Provenance` |
| `POST` | `/api/problem-list/build` | Builds a FHIR `Condition` (`category=problem-list-item`) with dual coding from one NAMASTE code |
| `GET` | `/CodeSystem/{NAM\|NSM\|NUM\|AST\|ICD11-TM2\|ICD11-BIOMEDICINE}` | `content:"not-present"` + a real, chapter-filtered live count |
| `GET` | `/ValueSet/$expand?filter=&system=` | Real FTS5 search wrapped in FHIR `expansion.contains` |
| `GET` | `/Consent/{id}` | **Stub only** — one static, correctly-shaped Consent resource; no real consent is collected |

AI-sourced `$translate`/Bundle results carry an inline FHIR `Provenance` resource (agent, decision,
confidence).

### Human-in-the-loop governance

`NEEDS_CONTEXT`/`EXPERT_REVIEW` suggestions (and the 248 legacy Biomedicine reclassifications
above) auto-enqueue into `review_queue`. A reviewer decision of `approved` on an AI suggestion
writes a **new** row into `concept_map` (`source="ai_reviewed_v1"`, vs `"rule_v1"` for the
original 468); on a legacy item, approve keeps the (already-relabeled) row, **reject deletes it**
— a reviewer can actually remove a bad legacy mapping from the registry.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/governance/queue?status=` | Paginated, filterable review queue (filterable client-side by `flag_type` too) |
| `POST` | `/api/governance/{id}/decide` | **Auth-gated.** `{status, note}` — `approved` writes/keeps a `concept_map` row, `rejected` on a legacy item deletes it |

### ABHA Demo Mode auth + real audit trail

`app/auth.py` issues a signed (HMAC-SHA256), short-lived bearer token via `POST
/api/auth/demo-login` (name + role, no password) — **not real ABHA OAuth2**, but a real FastAPI
dependency (`require_demo_auth`) that 401s without a valid token, gating `POST /Bundle` and
`POST /api/governance/{id}/decide`. Every response is labeled `"mode": "ABHA_DEMO"`.

`app/audit.py`'s `audit_log` table records every governance decision and Bundle upload with the
real actor identity from the token; `GET /api/audit/recent` backs Overview's activity timeline.

### Frontend

The app now sits behind a login screen (`/login`, ABHA Demo Mode) before any page is reachable.
**AI Mapping Lab** (`/ai-lab`) shows independent TM2/Biomedicine suggestion cards side by side, plus
the batch-run tool. **Expert Review** (`/review-queue`) tags rows AI Suggestion vs Legacy
Reclassification with a filter, and approve/reject really writes/deletes registry rows. **FHIR
Workspace** gained `$translate` (now dual-coded by default), **Bundle Upload (Double-Coding)**, and
**Problem List Builder** tabs, all hitting live endpoints. **Overview**'s activity timeline is the
real audit trail, not a hardcoded array; **AppShell** shows the real logged-in identity and a real
backend-liveness ping instead of a static "Operational" dot.

### WHO ICD-11 API synchronisation

Everything else in this service reads `db/ayush_icd11_combined.db`, whose `icd11` table is a **static
snapshot** of WHO's MMS linearization (`data/ICD-11.csv`, version column
`version_2025_jan_24_-_22_30_utc`). That is fine for a demo and wrong for a production terminology
service: WHO revises ICD-11 on a release cadence, and a bridge built on a frozen copy silently rots.

`app/who_sync.py` is the live half.

**Two independent WHO sources**, because ICD-API registration is a real barrier and shouldn't be
the only path to a live answer:

1. **Release files (default, no credentials).** WHO publishes every ICD-11 MMS release as a Simple
   Tabulation file on its own CDN (`icdcdn.who.int/static/releasefiles/...`) — no login, no OAuth,
   nothing. It's the same file format our own snapshot was built from. `POST /api/who/sync` downloads
   the current release and diffs **every** mapping-target code against it in one pass.
2. **The ICD-API (optional, needs credentials).** Register free at icd.who.int/icdapi, set
   `ICD_API_CLIENT_ID` / `ICD_API_CLIENT_SECRET`, and `POST /api/who/sync/api` adds per-code
   definitions and browser links via the real OAuth2 `client_credentials` flow
   (`icdaccessmanagement.who.int/connect/token`, scope `icdapi_access`) and the two-step
   `codeinfo/{code}` → stem-entity resolution the API actually requires.

Both write to the same drift registry, so the governance story doesn't change with the source —
only the provenance label does (`WHO_RELEASE_FILE` vs `WHO_LIVE`/`WHO_CACHE`).

**What it does**

1. **Resolves codes for real** — a single-code lookup automatically prefers a cached ICD-API answer,
   then the live API, then the release file, then the offline snapshot, in that order, never failing.
2. **Detects drift.** For each ICD-11 code we actually depend on (the `concept_map` targets), it
   compares WHO's current title to our snapshot and classifies the result:

   | Verdict | Meaning |
   |---------|---------|
   | `CONFIRMED` | WHO agrees with our snapshot |
   | `TITLE_DRIFT` | WHO has retitled the code since our snapshot |
   | `NOT_IN_WHO_RELEASE` | the code is gone from the requested release |
   | `LOCAL_ONLY` | WHO was not consulted (degraded mode) |

   Drift is **raised for a human**, never auto-applied — the same discipline the AI mapping engine
   follows. A mapping is not silently rewritten because a string changed upstream.
3. **Sweeps forward on the API path.** Each ICD-API sync takes the least-recently-verified batch, so
   repeated runs walk the whole corpus instead of re-checking the same head. The release-file path
   needs no batching — one download covers all 456 mapping targets.

**Three things this deliberately gets right**

- **It cannot take the demo down.** No public function in `who_sync.py` raises on a network or
  credential failure. Missing credentials, dead Wi-Fi, a WHO rate-limit — each degrades to the local
  snapshot and reports *why*. A sync with no credentials is logged as `SKIPPED_NO_CREDENTIALS`, not
  as an error.
- **Provenance is never implied.** Every answer is stamped `WHO_LIVE`, `WHO_CACHE`, or
  `LOCAL_SNAPSHOT`, and the UI renders that as a badge. Snapshot data is never presented as live.
- **No new runtime weight.** It uses `requests`, already a dependency. Nothing here loads a model or
  allocates a large array, so the service's memory profile on a small instance is unchanged.

**Title normalisation gotcha.** `data/ICD-11.csv` encodes tree depth as a literal `- - - ` prefix on
each title (`- - - Cholera`). WHO's API returns the bare title. Without stripping that presentation
artifact, *every single code* would be reported as drifted — `who_sync.normalize_title()` handles it,
and `tests/test_who_sync.py` locks the behaviour down.

**Verified live, both sources — actual numbers from a real run:**

```
Sync with WHO (release file, no credentials): release 2026-01 vs our 2025-01 snapshot
  456 mapping-target codes checked → 454 confirmed, 0 drifted, 2 retired by WHO
  (9C6Y, 9C6Z — two glaucoma codes no longer in WHO's current release)
  100% coverage, one HTTPS download, zero WHO credentials used

Refresh via ICD-API (needs credentials): GET 1A00 → "Cholera" resolved live,
  full WHO definition returned, CONFIRMED against our snapshot
```

WHO's *current* published release (2026-01) is a full release ahead of the CSV snapshot this service
ships with (2025-01) — exactly the gap this feature exists to catch, found on the first real sync.

**Enabling live mode.** The release-file source needs nothing. For the ICD-API source, register free
at [icd.who.int/icdapi](https://icd.who.int/icdapi) and put the two keys in `.env` (see
`.env.example`) or export them:

```bash
export ICD_API_CLIENT_ID="your-client-id"
export ICD_API_CLIENT_SECRET="your-client-secret"
```

On Render, set the same two keys as environment variables in the service dashboard. Without them
the ICD-API source reports `SKIPPED_NO_CREDENTIALS` (not an error) and the release-file source keeps
working exactly as above.

**Tests.** `tests/test_who_sync.py` (23 tests) covers both sources with every WHO network call
stubbed: release-file download/parse/cache (including a real bug the test suite caught — WHO's zip
also ships a `readme.txt` that a naive "first `.txt` file" match would silently parse as the data
file), drift raised and cleared, sync-triggered force-refresh, the ICD-API token flow and
`codeinfo`→entity resolution, cache hit/bypass, batch abort on transport failure, and auth
enforcement on both `POST` endpoints.

---

### What's real vs. demo-mode

**Real** (live computation, covered by `pytest`, no mocked data):
- Embeddings, hybrid scoring, decision tiering (single-pool and dual TM2+Biomedicine).
- The governance approve→registry write path, including deleting a rejected legacy mapping.
- `$translate`, `CodeSystem` (split TM2/Biomedicine), `ValueSet/$expand`, `POST /Bundle`,
  `POST /api/problem-list/build` — real double-coding throughout.
- ABHA Demo Mode auth enforcement (real 401s, real token verification) and the audit trail.
- The original 468 curated mappings and 5-pass algorithm, now correctly TM2/Biomedicine-labeled.
- WHO ICD-API synchronisation: OAuth 2.0 client-credentials flow, two-step `codeinfo` → stem-entity
  resolution, drift detection, caching, and graceful snapshot fallback (see below for the one
  caveat — it has not yet been exercised against WHO's real servers).

**Not built / explicitly out of scope** — do not claim these to judges:
- Nothing — the WHO sync integration has been verified against WHO's real, live servers on both
  sources (see the "Verified live, both sources" numbers above). Say exactly what happened: on the
  first real sync, WHO's current release turned out to be one release ahead of our snapshot, and two
  glaucoma codes we still carry have since been retired from WHO's classification.
- **Real ABHA OAuth2** — the auth flow above is a clearly-labeled demo stub, not a connection to
  India's actual ABHA gateway.
- **`Consent`** — a single static stub resource; no consent is ever actually collected or verified.
- **ISO 22600 access control** — not implemented; the demo-auth gate is a partial answer at best.
- **SNOMED CT / LOINC semantics** — no licensed data source available; not attempted.
- **"WHO International Terminologies of Ayurveda"** — the `ast` table (labeled "Ayurveda Standard
  Terminology") has not been verified as that exact WHO-published vocabulary; treat it as
  best-available data, flagged as such in its `CodeSystem` response.
- A 2D embedding/ambiguity-map visualization — not built.
- The "run batch" demo button is a single synchronous call + final table, not a live-streaming
  progress UI.

---

## 🗣️ Multilingual

Two genuinely different things live under "multilingual," and this project deliberately keeps them
separate so neither one overclaims:

**1. Real native-script terminology search.** Every NAMASTE tradition's source CSV already carries a
native-script term column — `namc_term_devanagari` (Ayurveda/Sanskrit), `tamil_term` (Siddha),
`arabic_term` (Unani) — but before this pass, none of it was searchable. `nam_fts` indexed only the
IAST transliteration (`vyAdhi-viniScayaH`, never `व्याधि-विनिश्चयः`); `nsm_fts` never indexed
`tamil_term`; `num_fts` didn't index a term column of any kind, so **Unani was not searchable by name
in any script**. `scripts/migrate_multilingual_fts.py` rebuilds all three FTS indexes to include the
real native-script column, and `GET /api/search` now queries all three living traditions together
(previously it silently covered Ayurveda only). This is not translation — it's exposing data that was
already there. Try it:

```bash
curl -s "http://localhost:8000/api/search?q=%E0%A4%AA%E0%A5%8D%E0%A4%B0%E0%A4%AE%E0%A5%87%E0%A4%B9&system=namaste" | python3 -m json.tool   # प्रमेह — Ayurveda
curl -s "http://localhost:8000/api/search?q=%E0%AE%9A%E0%AE%BF%E0%AE%A4%E0%AF%8D%E0%AE%A4%E0%AE%BE&system=namaste" | python3 -m json.tool   # சித்தா — Siddha
curl -s "http://localhost:8000/api/search?q=%D8%B1%D8%B7%D9%88%D8%A8%D8%AA&system=namaste"   | python3 -m json.tool   # رطوبت — Unani
```

Each result carries `native_script`, `native_script_language`, and `tradition` fields; the
Terminology Explorer renders the native-script term inline with a language badge.

**2. UI localization (English / Hindi / Marathi / Gujarati).** `frontend/src/i18n/` holds a small,
hand-written dictionary for interface chrome — navigation, page headers, common action labels — with
a `LanguageProvider` context and a switcher in the top header (persisted to `localStorage`). This is
scoped deliberately: it covers the sidebar nav (always visible) and the headers of the newest pages
(Terminology Explorer, Analytics, WHO Sync, Overview), not every microcopy string across all nine
pages, and it never touches clinical terminology — that's real data (above), not translated copy.
Marathi and Gujarati have no columns anywhere in the NAMASTE source data, so no clinical term is ever
translated into them; only ordinary interface vocabulary is.

## 💬 Human Clinical Text &rarr; Terminology Assistant

`POST /api/v1/clinical-text/candidates` takes free text ("Patient has fever and productive cough for
5 days") and returns real terminology candidates for each detected symptom &mdash; without ever
inferring a diagnosis. First use of an `/api/v1` prefix in this codebase, deliberately: API versioning
is independent of terminology-release versioning (`2025-01` vs `2026-01`).

**Pipeline:** rule/lexicon extraction (symptom, negation, duration, body site, laterality) &rarr;
canonicalization &rarr; real FTS5 search across NAMASTE (all three traditions) and ICD-11, reusing the
exact same search machinery `/api/search` uses &mdash; no parallel index. A negated symptom
("no fever") is shown but never searched, so it can never produce a candidate.

```bash
curl -s -X POST http://localhost:8000/api/v1/clinical-text/candidates \
  -H "Content-Type: application/json" \
  -d '{"text": "Patient has no fever but has cough for 5 days."}' | python3 -m json.tool
```

Verified against every worked example in the feature's own design spec, including the hardest one:
"no fever but has cough" correctly negates only fever &mdash; catching a real bug along the way (see
below). The response never contains a field that could read as a diagnosis; that's enforced by a test
that greps the response for banned field names, the same pattern used for the analytics dashboard's
no-fabricated-encounter-data guarantee.

**A real bug this feature caught, twice:**
1. **Negation scope.** The first implementation let a negation cue ("no") reach across a clause
   boundary ("no fever <em>but</em> has cough"), incorrectly negating both symptoms. Fixed by splitting
   on contrastive conjunctions and tightening the negation lookback to a 4-word window &mdash; both
   independently, so one regressing doesn't silently reopen the bug.
2. **ICD-11 search was silently returning zero results, everywhere, on this SQLite version.**
   `WHERE f MATCH ?` (`f` aliasing an FTS5 virtual table) raises `OperationalError` on SQLite 3.35+;
   every call site wrapped it in a bare `except Exception: results = []`, so `/api/search`,
   `/api/concepts`, and `ValueSet/$expand`'s ICD-11 branches had been quietly returning empty results
   with no error surfaced. Fixed by matching against the real table name instead of the alias in all
   four call sites (`app/api.py` &times;2, `app/fhir_extra.py`, `app/clinical_nlp.py`). A regression
   test now asserts a real match count, not just a 200 status &mdash; the old tests only checked shape,
   which an empty list satisfies vacuously.

## 🔑 API Key / Developer Platform

The credential system an external EMR vendor actually integrates against &mdash; separate from the
clinician-facing ABHA Demo Mode login. Two identity systems now exist on purpose: one answers "which
clinician is acting" for the web UI, the other answers "which external client is calling the API."

**Five key types**, each with a default scope grant and a tiered rate limit (sandbox tightest, admin
loosest): `sandbox`, `readonly`, `translation`, `fhir_integration`, `admin`. The plaintext secret is
shown exactly once, at creation or rotation &mdash; only its SHA-256 hash is ever stored, and a
non-secret prefix (`nsk_sandbox_AbC123...`) is kept so a key can be recognised in a list without the
full secret ever being retrievable again.

```bash
# 1. Create a client + sandbox key (requires ABHA Demo Mode auth, like governance decisions)
curl -s -X POST http://localhost:8000/api/v1/api-keys/clients \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Apollo Hospitals EMR"}'
curl -s -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"client_id": 1, "key_type": "sandbox"}'

# 2. Call the versioned public API with the key (no clinician login needed)
curl -s "http://localhost:8000/api/v1/terminology/search?q=fever" -H "X-API-Key: $SECRET"
curl -s "http://localhost:8000/api/v1/translate?system=NAM&code=AA-1" -H "X-API-Key: $SECRET"
curl -s -X POST http://localhost:8000/api/v1/validate-code -H "X-API-Key: $SECRET" \
  -H "Content-Type: application/json" -d '{"system": "NAM", "code": "AA-1"}'
```

Every failure mode returns a real FHIR R4 `OperationOutcome`, not a generic error object: missing key
(401), wrong scope (403), rate limit exceeded (429, tiered per key type and enforced by counting the
key's own recent requests &mdash; no new infrastructure). `GET /api/v1/CapabilityStatement` is the one
open, unauthenticated endpoint, since a client needs to discover what this server supports before it
has a key at all &mdash; it lists only resources/operations with a real handler behind them.

The **Developer Portal** page (`/developer-portal`) does this end-to-end in the browser: generate a
key, see the secret exactly once, then call the live `/api/v1` API with it and watch the real response
(including the real 403 if you pick an endpoint outside the key's scopes).

**A real, previously-invisible bug this surface exposed:** calling the new `/api/v1/terminology/search`
against ICD-11 is what led to re-testing `/api/search`'s ICD-11 branch directly, which is how the
FTS5-alias bug (see the Clinical Text Assistant section above) was actually found and fixed. ICD-11
search had been silently returning zero results everywhere in this codebase before that fix.

## 🧪 Population Health Demo (Synthetic Data)

A separate page (`/population-demo`, `GET /api/analytics/population-demo`) illustrating what a
national AYUSH population-health view could look like at realistic volume &mdash; gender, region, and
time breakdowns a government stakeholder would want to see. **Every patient and encounter here is
fabricated.** `scripts/generate_synthetic_population.py` generates 2,000&ndash;2,500 synthetic patients
(gender, age band, one of 16 real Indian states/UTs) and 1&ndash;3 encounters each, spread over a
trailing 12 months, each attached to a **real** NAMASTE code drawn from the actual `nam`/`nsm`/`num`
tables &mdash; the terminology is genuine, the patient behind it is not.

```bash
python scripts/generate_synthetic_population.py --count 2200 --seed 42
```

This is kept structurally separate from `app/analytics.py` (the real governance dashboard) on every
level, on purpose:

- **Separate tables** (`synthetic_patients`, `synthetic_encounters`), each with an `is_synthetic`
  column baked into the schema itself &mdash; a raw SQL query against the database makes the
  fabrication status obvious, not just the API.
- **Separate module, separate router, separate page.** `app/population_analytics.py` never touches
  `app/analytics.py`, and vice versa.
- **A test that enforces the boundary in both directions**: `tests/test_population_analytics.py`
  asserts the real dashboard's response never mentions "synthetic" in any form, and
  `tests/test_analytics.py` already asserted the real dashboard carries no fabricated encounter/patient
  figure at all. If either module starts leaking into the other, a test fails.
- **An unmissable UI treatment** &mdash; a striped amber banner reading "100% SYNTHETIC DEMONSTRATION
  DATA &mdash; NO REAL PATIENTS" that cannot be mistaken for the real Analytics page's dark, sober
  honesty banner.

Say out loud, every time this page comes up in a demo: *"this is illustrative, not real usage — the
Analytics page next to it is the real one."*

## 🔀 Terminology What-If Simulator (Phase 3)

Answers a question the live WHO sync feature can only answer for one fixed pair of releases (our
shipped snapshot vs. whatever WHO currently publishes), generalised to **any** two releases:
*"if the terminology moved from release X to release Y, what in our own mapping registry breaks?"*

Built as a thin layer over `app/who_sync.py` &mdash; `fetch_release_table()` already does the real work
(download, cache, parse WHO's release format); this module only adds diffing two arbitrary releases
against each other, then joining that diff against `concept_map` to find real impact.

```bash
curl -s -X POST http://localhost:8000/api/v1/terminology/simulate \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"from_release": "2025-01", "to_release": "2026-01"}' | python3 -m json.tool
```

Verified against real WHO releases, matching this project's own known ground truth exactly: comparing
`2025-01` (the shipped snapshot) against WHO's actual current `2026-01` release reports **2 broken
mappings** &mdash; the same two glaucoma codes (`9C6Y`, `9C6Z`) the WHO Sync feature already found
independently. A same-release sanity check (`2025-01` vs `2025-01`) correctly reports zero of
everything.

**Safety discipline, same as everywhere else in this project:** running a simulation is 100% read-only
against `concept_map` and `review_queue` &mdash; it only writes to its own `terminology_simulations`
tables. Nothing is modified until an operator explicitly calls
`POST /api/v1/terminology/simulate/{id}/escalate`, which inserts new `review_queue` rows (flagged
`terminology_drift`, distinct from AI suggestions) for a human to look at. It never rewrites or deletes
an existing curated mapping, and escalating the same simulation twice is idempotent &mdash; it does not
duplicate review-queue rows.

The **What-If Simulator** page (`/what-if-simulator`) does this end-to-end: pick two real WHO releases
from a live dropdown, run the diff, see the risk score and affected-mappings table, escalate to the
real expert review queue with one click.

## ⛓️ Tamper-Evident Audit Ledger (Phase 3B)

The real audit trail (`app/audit.py` — already written to by every governance decision, WHO sync, API
key action, Bundle upload, and terminology simulation) now hash-chains its own rows: each row's
`row_hash` is `SHA-256(prev_hash + this row's own content)`. This is a hash chain &mdash; the same core
idea behind a git commit history or a blockchain's block-linking, applied to one local table &mdash; not
a distributed ledger, not a cryptographic signature scheme, and not a claim of any kind of
certification. It proves *"this history has not been altered since it was written,"* nothing more.

```bash
curl -s http://localhost:8000/api/audit/verify | python3 -m json.tool
```

**Live-verified this session, by actually attacking it:** wrote a real governance event, then edited
that row's `details` field directly in the SQLite database &mdash; bypassing the API entirely, exactly
the way an attacker with raw DB access would. `GET /api/audit/verify` immediately reported
`"valid": false"` and named the exact tampered row id. A second test confirmed the same for a tampered
`actor` field, and a third confirmed that deleting a row breaks the chain at the very next row.

`log()` keeps its exact original function signature &mdash; every existing call site across
`governance_router.py`, `who_router.py`, `apikey_router.py`, `terminology_simulator_router.py`, and
`fhir_extra.py`'s Bundle upload needed zero changes for the chain to apply to their writes.
`ensure_schema()` automatically backfills any pre-existing rows into the chain the first time it runs.

The Analytics page carries a **"Verify audit integrity"** chip (Governance Activity card) that calls
this endpoint live and shows either a green "Audit chain verified (N rows)" badge or a red
"TAMPERED — broken at row #N" badge &mdash; the single most effective thing to do live in front of
judges: hand-edit one row in a DB browser, then click the chip and watch it get caught.

## 🛡️ Terminology Firewall (Phase 3C)

"A clinical terminology quality gateway for existing EMRs" &mdash; positioned exactly as the platform
strategy doc's Phase 3C. Deliberately not a new validation engine: every check is a call into logic
that already exists and is already tested (code-existence, the WHO drift registry, dual-coding
translate). The firewall's only contribution is composing those into one verdict an EMR integration
can act on.

```bash
curl -s -X POST http://localhost:8000/api/v1/firewall/check \
  -H "X-API-Key: $SECRET" -H "Content-Type: application/json" \
  -d '{"resourceType":"Bundle","type":"collection","entry":[{"resource":{
        "resourceType":"Condition","id":"c1",
        "clinicalStatus":{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/condition-clinical","code":"active"}]},
        "subject":{"reference":"Patient/demo"},
        "code":{"coding":[{"system":"http://namaste.terminology/CodeSystem/ayurveda-morbidity","code":"AA-1"}]}}}]}' \
  | python3 -m json.tool
```

Three verdicts, never a fourth invented one: **ACCEPTED** (code exists, current, resolves to a
validated mapping), **REVIEW_REQUIRED** (code exists but the mapping is AI-uncertain or the target has
drifted per WHO Sync), **REJECTED** (structurally invalid input, or the code doesn't exist at all).
Requires an API key with `bundle:write` scope (`fhir_integration` or `admin`); never modifies the
Bundle, `concept_map`, or `review_queue` &mdash; a check is advisory, not a mutation. The
**Terminology Firewall** page (`/terminology-firewall`) runs this live in the browser.

## 📍 Regional Disease Intelligence (Population Health Demo extension)

Extends the synthetic Population Health Demo with the drill-down a government analyst actually asked
for: which condition is most common, nationally and region-by-region. The **codes and their real
NAMASTE terms are genuine terminology data** &mdash; only the encounter volume behind them is
synthetic, same discipline as the rest of that page. `GET /api/analytics/population-demo` now includes
`top_conditions_national` and `top_conditions_by_region`, both rendered as new tables on the page.

## 🎙️ Voice / Text Clinical Terminology Assistant (Phase 3)

A floating assistant available on every page. **Voice and typing are two input methods for one
engine** &mdash; speech-to-text and text-to-speech both run in the browser via the Web Speech API, so
there is no external speech provider, no audio upload, and no paid API key anywhere in this pipeline.
Where the browser has no speech support the panel says so plainly and typing continues to work.

```bash
curl -s -X POST http://localhost:8000/api/v1/assistant/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "What is dual coding?"}' | python3 -m json.tool
```

**It is a routing layer, not a new engine.** `app/assistant.py` contains no terminology logic of its
own &mdash; it detects intent and delegates to the components that already exist and are already
tested (`app.api.search_concepts`, `app.fhir_extra.translate`, `app.clinical_nlp.build_candidates`,
the `$validate-code` tables, and `app.problem_list`). The assistant therefore cannot disagree with
what the rest of the platform would return for the same query.

**Two answer sources, kept strictly apart:**

- **Project / FAQ questions** are answered *only* from `data/knowledge_base.json`, returned verbatim.
  The assistant never paraphrases, never composes a new explanation, and has no generative fallback.
  Below a confidence floor it declines &mdash; *"I couldn't find a reliable answer in my knowledge
  base"* &mdash; and lists the topics it does cover. Non-hallucination here is structural, not a prompt
  instruction. Edit the JSON file (question / answer / category / keywords) to extend it; no code
  changes, and `POST /api/v1/assistant/reload-knowledge-base` picks up edits without a restart.
- **Terminology questions** are answered *only* by calling the existing engines above.

**Clinical safety.** A symptom is never promoted to a diagnosis &mdash; the assistant inherits
`app/clinical_nlp.py`'s guarantee by delegating to it. Asked about a patient with a cough it reports
the symptom, states plainly that it cannot infer a diagnosis, and searches the terminologies for the
symptom only. Negated symptoms ("no fever") are reported as absent and never searched.

**Confirmation gate.** Any request that would write clinical data (*"add this to the problem list"*)
returns a prepared FHIR Condition preview plus `requires_confirmation: true` &mdash; nothing is saved.
Execution goes through a separate authenticated `POST /api/v1/assistant/confirm`, so a single spoken
utterance can never cause a write, and the confirmed action is stamped into the audit trail.

**Phonetic fallback for spoken terms.** NAMASTE terms are stored in IAST transliteration
(`gRudhrasI`); speech-to-text produces `"Gridhrasi"`, which shares no searchable prefix. When the
primary search returns nothing, the assistant reduces both sides to a consonant skeleton to find
candidates, then *asks the user to confirm* rather than silently assuming the match. This is query
normalisation feeding the existing search &mdash; not a second search engine.

## 🔧 Advanced Usage

```bash
# Regenerate concept mappings independently
python scripts/create_concept_map.py

# Analyze coverage statistics and prefix breakdown
python scripts/analyze_coverage.py

# Export all mappings to CSV
python scripts/export_mappings.py
```

### EMR Integration Example

```python
import requests

BASE = "http://localhost:8000"

# Translate a NAMASTE code to ICD-11
concept_map = requests.get(f"{BASE}/ConceptMap/SR10%20(AAA-2.1)").json()
icd11_codes = [
    t["code"]
    for g in concept_map["group"]
    for e in g["element"]
    for t in e["target"]
]
print("ICD-11 codes:", icd11_codes)

# Search across terminologies
results = requests.get(f"{BASE}/api/search", params={"q": "vata", "system": "both"}).json()
print(f"Found {results['total']} results: "
      f"{results['namaste_count']} NAMASTE, {results['icd11_count']} ICD-11")

# Get high-confidence mappings for a code family
mappings = requests.get(f"{BASE}/api/mappings",
                        params={"equivalence": "equivalent", "page": 1}).json()
print(f"Total equivalent mappings: {mappings['total']}")
```

---

## 🔧 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `Database not found` | Init not run | `python scripts/init.py` |
| `ModuleNotFoundError` | Wrong environment | `source .venv/bin/activate` |
| `Test failures` | Stale DB | Re-run `python scripts/init.py` |
| `uvicorn: command not found` | Missing install | `pip install fastapi uvicorn` |
| `npm: ERR_MODULE_NOT_FOUND` | Missing npm deps | `cd frontend && npm install` |
| `CORS error` in browser | Backend not running | Start backend on port 8000 |
| `FTS match error` | Special chars in query | URL-encode the query string |

---

## 🤝 Contributing

1. **Fork** the repository
2. **Branch**: `git checkout -b feature/your-feature-name`
3. **Develop** with tests
4. **Validate**: `python tests/run_tests.py`
5. **PR**: Open a pull request with a clear description of changes

---

## 📄 License

Developed for the **Ministry of Ayush, All India Institute of Ayurveda (AIIA)** as part of India's national digital health transformation initiative under Smart India Hackathon 2026.

---

<div align="center">

**Built with ❤️ for India's Digital Health Mission**

*Connecting 5000 years of Ayurvedic wisdom with modern healthcare standards*

[![AYUSH](https://img.shields.io/badge/AYUSH-Powered-FF6600?style=for-the-badge)](https://ayush.gov.in)
[![WHO ICD-11](https://img.shields.io/badge/WHO-ICD--11_Compliant-1565C0?style=for-the-badge)](https://icd.who.int)
[![FHIR R4](https://img.shields.io/badge/FHIR_R4-Compliant-E53935?style=for-the-badge)](https://hl7.org/fhir/R4/)

</div>
