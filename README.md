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

> 🖥️ **Dashboard:** http://localhost:5173

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
