# NAMASTE × ICD-11 Integration — Presentation & Demo Guide

**Problem statement:** `DJS_26_SW_10` — *"Develop API code to integrate NAMASTE and/or ICD-11 via TM2 into
existing EMR systems that comply with Electronic Health Record (EHR) Standards for India."*

This document is written for the team preparing the pitch — it explains **what every screen is for,
why it was built that way, and exactly how to click through it live**, so a presentation deck and demo
script can be built directly from it without re-deriving anything.

---

## 1. The 60-second pitch

India's Ayush sector records diagnoses in **NAMASTE** (Ayurveda/Siddha/Unani terminology). Modern
hospitals, insurers, and WHO reporting all speak **ICD-11**. Nobody has built a working bridge between
them — until now. This project is a FHIR R4 terminology micro-service that:

1. Maps NAMASTE codes to **both** ICD-11 Traditional Medicine (TM2) **and** ICD-11 Biomedicine —
   real double-coding, not a single lossy translation.
2. Fills the ~19,000-code gap the original rule-based mapper leaves unmapped, using an **ambiguity-aware
   AI engine** that explicitly refuses to guess when it isn't confident.
3. Never lets an AI suggestion become official without a **human reviewer** approving it.
4. Speaks real FHIR: `$translate`, `CodeSystem`, `ValueSet/$expand`, `Bundle` upload, `ProblemList`
   construction — the actual operations an EMR vendor would call.
5. Is honest about what's demo-scaffolding (auth) versus what's real (everything else).

---

## 2. Architecture in one picture

```
NAMASTE CSVs + WHO ICD-11 CSV  →  SQLite (FTS5) db/ayush_icd11_combined.db
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
         5-pass rule-based        sentence-transformer   FastAPI backend
         matcher (468 curated     embeddings for every    (app/*.py)
         mappings, now TM2/       NAMASTE + ICD-11               │
         Biomedicine-labeled)     concept                        │
                    │                   │                        │
                    └─────────┬─────────┘                        │
                               ▼                                 ▼
                    Ambiguity-aware AI decision engine   React + Vite frontend
                    (AUTO_SUGGEST / NEEDS_CONTEXT /       (src/pages/*.tsx)
                     EXPERT_REVIEW / NO_VALIDATED_
                     EQUIVALENT — dual TM2 + Biomedicine)
                               │
                               ▼
                    Governance review queue → approve
                    writes a new curated mapping row
```

Backend: Python/FastAPI + SQLite+FTS5, no external services required. Frontend: React 18 + TypeScript +
Vite. Everything runs fully offline once the database and embeddings are built.

---

## 3. Page-by-page: purpose, why, and how to demo

### 3.1 Landing Page (`/`)

**Purpose:** First impression — the page a judge sees before signing in. Establishes the pitch in one
screen: what this is, what's real, and the numbers to back it up.

**Why built this way:** Judges skim. The hero line states the differentiator (double-coding + AI +
governance) in one sentence, the live stat strip proves the numbers are real (pulled from
`GET /api/stats`, not typed in), and the 6-card feature grid gives a reviewer reading the spec closely
something to check off against each requirement.

**How to demo:** Just load it. Point out the stat strip updates from the live database — refresh the
page and the same real numbers reappear (proves it isn't a static screenshot). Scroll to the feature
grid and read out 2–3 cards that map directly to spec line items (double-coding, FHIR R4, governance).

### 3.2 Sign In (`/login`) — ABHA Demo Mode

**Purpose:** Gate to the actual application; demonstrates a real authentication code path.

**Why built this way:** The spec asks for "ABHA-linked OAuth 2.0 authentication." Real ABHA requires
registering with India's Ayushman Bharat Digital Mission gateway — out of reach for an offline build.
Instead of skipping auth entirely (which would be a bigger credibility gap), this issues a real
HMAC-signed bearer token with a real expiry, and a real FastAPI dependency (`require_demo_auth`) that
returns actual `401`s without one. It's the same *shape* as production auth; only the identity
provider is a stub — and every screen says so.

**How to demo:** Enter any name + pick a role, click **Continue**. Mention explicitly: "no password
checked, this is labeled ABHA Demo Mode — but the token it issues really gates write actions later in
the demo, which I'll show you." This pre-empts the "is this just for show?" question before a judge
asks it.

### 3.3 Overview (`/overview`)

**Purpose:** Live dashboard — the "state of the system" screen.

**Why built this way:** Every number here is computed from the database at request time — nothing is
hardcoded. The four AI/governance stat cards (unmapped codes, pending reviews, AI-reviewed mappings
added, AI engine status) exist specifically so the "close the loop" demo moment (see §4) has a visible
before/after. The activity timeline reads from a real `audit_log` table populated by actual governance
decisions and Bundle uploads — not a scripted fake feed.

**How to demo:** Note the **Total Mappings: 468** and **Unmapped: 19,181** cards now — you'll return
here after the AI Lab / Review Queue demo to show these numbers actually changed.

### 3.4 Terminology Explorer (`/terminology`)

**Purpose:** Browse and search the raw NAMASTE and ICD-11 registries directly.

**Why built this way:** Proves the underlying data is real and searchable (SQLite FTS5 full-text
search, sub-15ms), not a toy dataset. This is the "show me the terminology data itself" screen.

**How to demo:** Search a common term (e.g. "fever" or "vata") and show results ranked by relevance
across both systems.

### 3.5 Mapping Intelligence (`/mapping`)

**Purpose:** Browse the 468 **curated, rule-based** mappings — the "ground truth" registry.

**Why built this way:** This is the original deterministic 5-pass mapper's output, kept completely
separate from anything AI-generated. Filtering by Equivalent/Related and clicking into detail shows
confidence, version, and provenance per mapping.

**How to demo:** Filter to "Equivalent," click one row, point out the source/target side-by-side panel
and the confidence bar — then pivot: "this is the 468 we started with; here's how we cover the other
19,000+."

### 3.6 AI Mapping Lab (`/ai-lab`) — ★ the centerpiece

**Purpose:** The core differentiator. Search any NAMASTE code with no curated mapping and watch the AI
engine produce a transparent, dual (TM2 + Biomedicine) suggestion.

**Why built this way:** Two independent `SuggestionCard`s render side by side because a code can be a
confident TM2 match while its Biomedicine match is completely different — combining them into one score
would hide that. Each card shows: a color-coded decision badge, the top1/top2 margin (why it is or
isn't confident), a plain-English rationale citing the actual similarity numbers, and — when one
exists — the curated "ground truth" mapping right above the AI result for direct comparison.

**How to demo (this is the moment to slow down):**
1. Click one of the "Try:" suggestion chips, or type a code like `SR10 (AAA-2.1)`.
2. Point at the **TM2** card: `AUTO_SUGGEST`, green badge, curated mapping shown above matching the AI
   top candidate — "the AI agrees with our rule-based ground truth."
3. Point at the **Biomedicine** card next to it: no curated mapping exists, so the AI gives an honest
   `EXPERT_REVIEW` at ~35% confidence — "and when it's not sure, it says so instead of guessing."
4. Scroll down, click **Run Batch** — 50 real unmapped codes get AI suggestions in front of the judges
   in a few seconds. This is the single best "wow" moment: real computation, not a loading spinner
   faking it.

### 3.7 Expert Review (`/review-queue`) — closes the governance loop

**Purpose:** Human-in-the-loop safety valve. Every ambiguous AI suggestion lands here; nothing becomes
an official mapping without a person clicking Approve.

**Why built this way:** While building this, a real data-quality bug was found — 248 of the original
468 "curated" mappings were mislabeled TM2 when they actually pointed at Biomedicine codes (the 5-pass
algorithm never checked which ICD-11 chapter it matched into). Rather than silently fixing the label
and moving on, every one of those 248 rows was routed into this same review queue
(`flag_type=legacy_reclassification`) so a human confirms the underlying match is still correct — the
bug became a governance demo instead of a footnote.

**How to demo:**
1. Show the **Legacy Reclassifications (248)** filter and the banner explaining why they're there —
   "we found this ourselves, and we didn't just trust it."
2. Switch to **AI Suggestions** filter (populated from the AI Lab batch run in §3.6).
3. Click **Reject** on one row. State plainly: "this deletes it from the registry" — then switch to the
   Overview tab in another moment to prove it.
4. Click **Approve** on another row. State: "this writes a brand-new row into the same table the
   original 468 live in."
5. **Immediately navigate to Overview** — the **Total Mappings** and **AI-Reviewed Mappings Added**
   cards will have visibly changed. This is the loop-closing moment: AI suggests → human decides →
   registry updates, live, in front of the judges.

### 3.8 FHIR Workspace (`/fhir`) — for judges who know the standard

**Purpose:** Prove the FHIR operations are real, spec-shaped resources, not decorative JSON.

**Four tabs, each a different proof point:**
- **Browse ConceptMaps** — the original static `GET /ConceptMap/{code}` resource generator.
- **`$translate` (Live)** — hits the real operation; defaults to `target_system=BOTH`, so one call
  returns independent TM2 and Biomedicine match groups, each tagged so you can tell which is which.
  Try an unmapped code to show a spec-correct `result:false / equivalence:"unmatched"` response — never
  silently omitted.
- **Bundle Upload (Double-Coding)** — paste/edit a sample `Condition` Bundle, POST it (gated by your
  ABHA Demo Mode token from sign-in), and get back the same Bundle with both ICD-11 codes appended plus
  an inline `Provenance` resource for any AI-sourced addition.
- **Problem List Builder** — the literal "construct a FHIR ProblemList entry" deliverable named in the
  spec's demonstration checklist: enter a code, get a `Condition` resource with
  `category=problem-list-item` carrying the dual coding.

**How to demo:** Run `$translate` on a code with no curated mapping first (shows the honest
`unmatched`/AI-fallback path), then on a curated one (shows curated-first). Then go straight to Bundle
Upload and point out the `Authorization: Bearer …` header is being attached automatically from the
login token — "this isn't decorative auth, it's actually enforced."

### 3.9 Settings (`/settings`)

**Purpose:** Session/config transparency screen — who you're logged in as, when the token expires, what
backend URL the frontend is pointed at, and a live snapshot of connected terminology systems.

**Why built this way:** Every field here is real (the session identity from your actual login, the
actual configured API base URL) — there is no hardcoded fake user profile.

---

## 4. Recommended live demo script (≈6 minutes)

1. **Landing → Sign In** (30s) — state the pitch, sign in, call out ABHA Demo Mode honestly.
2. **Overview** (30s) — note current numbers: 468 mappings, ~19,181 unmapped, 0 AI-reviewed added.
3. **AI Mapping Lab** (2 min) — search `SR10 (AAA-2.1)` for the dual TM2/Biomedicine contrast, then run
   the 50-code batch live.
4. **Expert Review** (1.5 min) — show the legacy-reclassification honesty story, approve one AI
   suggestion.
5. **Back to Overview** (20s) — point at the changed numbers. *This is the payoff moment — don't skip
   it.*
6. **FHIR Workspace** (1.5 min) — `$translate` on a matched and an unmatched code, then Bundle Upload to
   show the auth token actually gating a write.

## 5. What's real vs. demo-mode (say this out loud, don't wait to be asked)

**Real:** terminology data (56k+ concepts), the AI embedding engine and dual TM2/Biomedicine decision
tiers, the governance approve/reject → registry write/delete path, `$translate`/`CodeSystem`/
`ValueSet/$expand`/`Bundle`/`ProblemList`, the audit trail, and the ABHA Demo Mode token enforcement
(real 401s).

**Demo-mode / not built** — say this before a judge finds it: real ABHA OAuth2 (this is a labeled
stand-in), the `Consent` resource (one static stub, no consent is actually collected), ISO 22600 access
control, SNOMED CT/LOINC semantics, and a live sync job against the WHO ICD-API (the Biomedicine/TM2
data already present locally was sufficient for tonight's build). Full detail in `README.md`'s "What's
real vs. demo-mode" section.

## 6. Running it for the presentation

```bash
cd "SIH_PS_10" && source venv/bin/activate && uvicorn app.main:app --reload
```
```bash
cd "SIH_PS_10/frontend" && npm run dev
```
Open `http://localhost:5173` — you'll land on the Landing page, then Sign In.

If the database or embeddings need rebuilding from scratch:
```bash
python scripts/init.py          # rebuilds DB, 5-pass mappings, TM2/Biomedicine labels, embeddings
```
