# SmartShelf — System Design

**Status:** Authoritative · **Version:** 1.1 · **Date:** 2026-09-08 · **Branch:** `system-design`
**Inputs:** [PRD](../product/PRD.md) + the seven [feature intents](../features/) (approved; formerly the monolithic `intent.md`) · the seven [feature specs](../features/) `F1-S1 … F7-S1` v1.1, the [intent register](../product/intent-register.md) and [gaps register](../features/gaps-and-open-questions.md) (formerly the monolithic `specs.md`; passed the intent → spec gate, [`intent-spec-conformance.md`](../reviews/intent-spec-conformance.md))
**Supersedes:** every earlier design statement in this repository — `ARCHITECTURE.md` (retained only as the pre-design current-state trace, now at [`docs/archive/ARCHITECTURE.md`](../archive/ARCHITECTURE.md)), `docs/TECH_*.md`, `docs/UI_DATA_CONTRACT.md`, `docs/RECOMMENDATION_FAMILIES.md`, `docs/PRODUCT_REQUIREMENTS.md`, `docs/SAAS_*.md`, `docs/SPRINT*.md`, `docs/PLANOGRAM_ROADMAP.md`. Those files were moved to `docs/archive/` by this change and carry no authority.

```
INTENTS  ->  SPECS  ->  SYSTEM DESIGN  ->  IMPLEMENTATION
                        ^ this document
```

This document answers one question: *given the approved specifications and the assets that
verifiably exist in the repository, what architecture should SmartShelf V1 have?* It was
derived from the specifications and from the code, tests, configs, workflows and data
artefacts as they are on 2026-09-08 — never from the legacy design prose. Where the code
and a specification disagree, the specification wins. Where a legacy document and the
code disagree, the code was believed and the document was not.

Two sentences summarise the design:

> **One deterministic rule engine, in Python, owns every figure the owner sees. The
> browser presents a bounded surface over that engine's published artefact and records
> what the owner did; the owner's answers, outcomes and revivals are the only mutable
> state in the system, and they flow back into the next engine run.**

Everything else — the typed capability contract, the availability semantics, the money
typing, the single reproduction path, the owner-state store, the removal of the parallel
browser-side engines — follows from those two sentences and from the specifications that
force them.

> **Version 1.1 (2026-09-08)** closed the one blocker raised by the implementation-readiness
> gate ([`system-design-readiness.md`](../reviews/system-design-readiness.md),
> ARCH-GATE-001). Version 1.0 used *capability* extensionally and answered a membership
> question two different ways: the contract sections put data hygiene inside
> `reconciliation`, the behaviour sections gave it its own badge, value policy, precedence
> slot and page. The term is now defined — **a capability is the smallest unit that can
> independently become unavailable** (ADR-014) — `hygiene` is registered as one,
> `catalogue_lifecycle` and `owner_questions` move inside `capabilities{}` and gain the
> `status` they lacked, `status` is computed from a declared `requires` list rather than
> hand-declared, and `entry_id` now hashes a permanent `signal_family` instead of the
> mutable capability id, so a future re-carving can no longer orphan the owner's recorded
> decisions (ADR-009).

---

## Contents

1. [Authority and Inputs](#1-authority-and-inputs)
2. [Architectural Drivers](#2-architectural-drivers)
3. [Current-State Reality](#3-current-state-reality)
4. [Current Subsystem Assessment](#4-current-subsystem-assessment)
5. [Reuse / Refactor / Replace / Remove Decisions](#5-reuse--refactor--replace--remove-decisions)
6. [Target Architecture](#6-target-architecture)
7. [Components and Responsibilities](#7-components-and-responsibilities)
8. [Boundaries](#8-boundaries)
9. [Data and Control Flows](#9-data-and-control-flows)
10. [Domain and Data Model](#10-domain-and-data-model)
11. [Interfaces and Contracts](#11-interfaces-and-contracts)
12. [State Ownership](#12-state-ownership)
13. [Failure and Recovery](#13-failure-and-recovery)
14. [Reliability and Invariant Enforcement](#14-reliability-and-invariant-enforcement)
15. [Security and Privacy](#15-security-and-privacy)
16. [Performance and Resource Model](#16-performance-and-resource-model)
17. [Observability](#17-observability)
18. [Testability](#18-testability)
19. [Architecture Decisions](#19-architecture-decisions)
20. [Current → Target Migration Strategy](#20-current--target-migration-strategy)
21. [Spec → Design Traceability Matrix](#21-spec--design-traceability-matrix)
22. [Risks and Remaining Unknowns](#22-risks-and-remaining-unknowns)
23. [Implementation Handoff](#23-implementation-handoff)
24. [Design Readiness Verdict](#24-design-readiness-verdict)

---

## 1. Authority and Inputs

### 1.1 Source-of-truth hierarchy used throughout

| Rank | Source | How it was used |
|---|---|---|
| 1 | `intent.md` — 13 intents, 13 settled decisions D-1 … D-13 | Product meaning; nothing here reopens a D-decision |
| 2 | `specs.md` v1.1 — SPEC-000 … SPEC-007, SPEC-GAPS | The contract. Every FR/INV/NFR/AC with architectural weight is answered in §21 |
| 3 | Immutable external constraints | The POS export shape (no sales dates, monthly reports), the price-transparency server keeping one day only, Wolt catalogue shape, a two-person team, single store |
| 4 | Verified current behaviour the specs protect | Store-format source discipline (C-20/C-21), three-language rendering (C-53), negative-stock clamp at the data boundary (C-32), persisted decisions (C-50/C-52), the ≤3 question bound (C-40), the ranking rule (C-41), no velocity claims without evidence (INV-005/INV-055) |
| 5 | The existing implementation | Evidence of what works, measured by running it (§3, §4) |
| 6 | Legacy design documentation | Not used as authority. Read only to know what to supersede |

### 1.2 What was verified, and how (2026-09-08)

| Check | Result |
|---|---|
| `npx vitest run` | **498 passed** (35 files) |
| `.venv/bin/python -m pytest tests -q` | **324 passed** |
| `npm run lint` · `npm run build` | clean · builds (main chunk **4.36 MB**, of which `src/data/demoProducts.js` is 193,729 lines) |
| `node scripts/check_signals_live.mjs` | passes — every probed signal reaches an output (all probes are V2 reorder signals) |
| `npx playwright test` | **29 passed** (real Chrome, real dev server) |
| `npm run figures` | runs in **0.87 s**, writes nothing, and still prints two figures the intent layer has since withdrawn (₪103,829 stock-discrepancy money, ₪919,170 idle-stock money) |
| Data artefacts | read with pyarrow — counts in §3.5 |
| Repository topology | 5 parallel read-only audits (internal POS pipeline, market pipeline, frontend, data artefacts, tooling/deployment) |

No workflow in `.github/workflows/` runs any test suite. The only automated quality gate is
`check_signals_live.mjs` inside the nightly collector.

### 1.3 Scope of this design

V1 only — SPEC-001 … SPEC-007. INT-004/005/007/008 (V2, V3) and INT-006 (V4) are not
designed here; SPEC-000 §4 explains why they cannot be. The design does, however, leave
the two things the intent schedules to *start* on 12/9 in place: receipt/expiry capture
by staff (INT-007's data, `intent.md` §7) and the request for two-year sales reports
(SPEC-004 FR-063c's input). It also keeps V2/V4 code out of the V1 build rather than out
of git (§5, ADR-010).

---

## 2. Architectural Drivers

An architectural driver is a requirement that changes the shape of the system. Nine were
found. Everything in §6 onward is traceable to at least one of them.

### ARCH-DRIVER-001 — One rule, one implementation, one reproduction path
**Driven by:** SPEC-007 FR-121, FR-124, FR-125, INV-062, INV-065, NFR-061, NFR-062; SPEC-001 NFR-002; SPEC-002 NFR-011; SPEC-003 NFR-021; SPEC-004 NFR-032; SPEC-005 NFR-041; SPEC-006 NFR-053.
**Implication:** every figure the owner sees must be computable by exactly one rule that
the reproduction path runs unchanged. Today three implementations disagree (§3.4): the
Python engine flags Wolt gaps at a flat 5 %, the JS ranks them and attaches money, and
`print_figures.py` re-reads the raw CSV with an 18 % constant. The target has a single
engine, in Python, and `npm run figures` *is* that engine in print mode (ADR-001, ADR-002).
The browser computes no business rule.

### ARCH-DRIVER-002 — Honest absence is a first-class state
**Driven by:** D-3; SPEC-001 FR-006, FR-011; SPEC-002 §11; SPEC-003 FR-044c, FR-051, §11; SPEC-004 INV-036; SPEC-006 FR-117, FR-118, INV-057; SPEC-007 FR-126, FR-128, FR-129, INV-061.
**Implication:** "unavailable", "no comparison", "no figure" and "zero" are four different
values and must be distinguishable in every artefact and on every surface. The current
artefact cannot express unavailability — a missing directory yields an empty list
(`ARCHITECTURE.md` seam 1; the 2026-09-05 empty-export incident). The target capability
contract carries an explicit `status`, and the publisher refuses to write when any
capability has none (ADR-005).

### ARCH-DRIVER-003 — Money discipline is structural, not editorial
**Driven by:** D-1, D-2, D-11; SPEC-001 FR-012, FR-013; SPEC-002 FR-023, FR-025, FR-029, INV-010 … INV-014; SPEC-004 FR-069a, FR-069b; SPEC-006 FR-104 … FR-106a, FR-116, INV-051, INV-054; SPEC-007 FR-134, INV-064.
**Implication:** a value is a typed object `{amount, kind, certainty}`, not a number; a
capability declares at registration whether it may carry one; the publisher asserts the
declaration; the browser never derives money. FR-105's single-kind premise is *published
as a derived fact* (`value_kinds_present`) and asserted, not assumed (ADR-012). Today the
browser multiplies unaccounted units by cost (`actionPriority.js:85-92`) and the shipped
surface's entire top-20 is that forbidden figure (§3.4).

### ARCH-DRIVER-004 — The owner's knowledge must persist and flow back into the rules
**Driven by:** SPEC-005 FR-087, FR-088, FR-089, FR-090, FR-093, NFR-042, INV-042; SPEC-006 FR-103(3), FR-112 … FR-115, INV-053, NFR-052, C-50, C-52; SPEC-001 C-4; SPEC-002 C-13; SPEC-004 FR-067, C-33; INT-MEAS.
**Implication:** answers, outcomes and manual revivals are the only mutable state in the
product. They must survive reload and device loss, must reach the engine without the owner
doing anything further, and must be readable by reproduction. Today answers are a
browser-local dead end (the YAML export has no button and the named importer never
existed) and completion actions are never mirrored anywhere. The target has one owner-state
store, written only by the browser, pulled by the engine at the start of every run (ADR-003).

### ARCH-DRIVER-005 — Withdrawal is a re-evaluated rule, not an event
**Driven by:** SPEC-004 FR-060a, FR-060b, FR-063a-c, FR-065, FR-066, FR-067, INV-030 … INV-032, INV-034, §10; SPEC-005 FR-082, FR-082a; SPEC-006 FR-102.
**Implication:** the withdrawn set is a pure function of (sales evidence, recorded stock,
owner revivals). No engine-owned lifecycle store is needed; interrupted ingestion leaves
the previous artefact authoritative by construction (ADR-004). Nothing of this capability
exists today.

### ARCH-DRIVER-006 — Single store, single user, single POS import, static delivery
**Driven by:** D-12, D-13, D-7; `intent.md` §8 (a two-person team, ~15 h/week each); SPEC-004 FR-068, INV-033.
**Implication:** no accounts, no tenancy, no runtime server, no second import path. A
static site behind one shared credential, a nightly CI run, and a hosted document store
for owner state are the whole runtime (ADR-007). The browser CSV connector, the Comax stub,
the LLM proxy, the MCP server and the telemetry entry point are outside this ceiling.

### ARCH-DRIVER-007 — Every figure carries its vintage and its thresholds
**Driven by:** SPEC-007 FR-120, FR-123, FR-127, FR-131, FR-132, INV-060, NFR-063, C-60, C-61; SPEC-001 FR-005; SPEC-003 FR-046; SPEC-004 FR-061.
**Implication:** the artefact has a `vintages` block (POS export date, months of sales
evidence, competitor snapshot date, owner-state pull time) and a `thresholds` block, and
every count on every page is rendered with them. Reproduction on a fresh clone must work:
the inventory CSV and the seven sales reports are committed; competitor observations are
rehydrated from committed snapshots; matches are recomputed content-addressed by their
inputs (ADR-002, §16). GAP-005 closes.

### ARCH-DRIVER-008 — Protected existing behaviour
**Driven by:** SPEC-003 C-20, C-21, C-22, INV-020; SPEC-006 C-53, INV-055, C-54; SPEC-004 C-32; SPEC-005 C-40, C-41.
**Implication:** store-format affinity stays the source-discipline layer — but it moves
into the engine, because today it is enforced only in JavaScript over a stale generated
file and never in the Python path that produces the competitor family (§3.3). Three
languages, no split numbers, no horizontal overflow, no untranslated key: the existing
i18n module and its four guard layers are reused unchanged. Negative stock is read raw by
the lifecycle rule.

### ARCH-DRIVER-009 — Bounded attention with stated allocation
**Driven by:** D-8, D-9; SPEC-006 FR-100, FR-101, FR-103, FR-106, FR-106a, FR-108, NFR-050; SPEC-005 FR-084, FR-086.
**Implication:** the surface is a pure composition (admission → outcome filter →
allocation across value kinds → one place per product → bound of ten) over engine
candidates. Composition depends on outcomes the browser owns, so it runs in the browser;
but it produces no figure, so ARCH-DRIVER-001 is not breached (ADR-006). Today there is
no ten-cap anywhere, the money list caps at 20 with a "show all N" toggle, and the data
list prints "Showing 20 of N" — both forbidden by FR-101.

---
## 3. Current-State Reality

Reconstructed from code, configs, workflows and on-disk artefacts. `ARCHITECTURE.md`
(2026-09-05) was checked against this and found accurate on the file-level data flow; it
is silent on the three findings that matter most for design (§3.4).

> **A trace of the tree on 2026-09-08, kept as it was.** §5's REUSE / REFACTOR / REMOVE
> decisions rest on it, so it is not rewritten as the tree changes. Phase 4 has since
> removed most of what §5.4 and §20.1 mark REMOVE (2026-09-15 … 09-24, ADR-028), and §20.1
> records each row's state. Read the paths in §3 and §4 as they stood on that date.

### 3.1 Executables and runtime topology

| Runtime | What it is | Evidence |
|---|---|---|
| **Static SPA** on Vercel | React 19 + Vite 8, two build entries (`index.html`, `telemetry.html`), navigation is `useState` (no URL routing), Arabic default, `<html dir>` switching | `vite.config.js`, `vercel.json`, `src/App.jsx:89,632-656` |
| **Edge middleware** | HTTP Basic Auth on every path; fails closed (503) when the two env vars are unset — and they are unset in `.env` | `middleware.ts` |
| **Nightly GitHub Actions job** | 00:00 UTC: collect Alonit price file (FTPS) + 9 Wolt venues → seal + commit snapshot → import POS CSV + 7 sales CSVs → `refresh_pipeline.py` → `check_signals_live.mjs` → commit `public/data/*.json` | `.github/workflows/collect-daily.yml` |
| **Watchdog job** | 12:00 UTC health check only | `collection-health.yml` |
| **Firestore** (project `hackathon26-a6ebd`) | Rules pinned to `/stores/yomyom-kafr-qasim/**`, anonymous auth. **Inert at runtime**: `VITE_FIREBASE_API_KEY` and `APP_ID` are empty, so `isFirebaseConfigured()` is false and persistence is localStorage only — the state `check_firebase_config.mjs` itself calls "the worst state" | `src/firebase.js:57-65`, `src/lib/persistence/persistence.js:9`, `firestore.rules` |
| **No server process** | `src/api/llm_proxy.py` (FastAPI/Gemini) and `src/mcp_server/price_server.py` (MCP) exist; nothing launches either; `VITE_LLM_PROXY_URL` is empty | audit §1 |

### 3.2 Data stores and their vintages (2026-09-08)

| Store | Content | Vintage | Committed? |
|---|---|---|---|
| `yomyom-inventory.csv` (= `data/internal/raw_pos/yomyom/all4shop_Mlai.csv`, byte-identical) | 7,674 catalogue rows: barcode, name, type, stock, cost, shelf price, WOLT price, department | file dated 2026-08-02 | yes |
| `data/internal/raw_pos/yomyom/sales/*.csv` | 7 monthly reports Jan–Jul 2026, 3,942 rows, 1,778 barcodes, 410,724 units, **no date column** | Jan–Jul 2026 | yes |
| `data/internal/silver_pos/*.parquet` | 4 tables × 7,674 rows (products, inventory, margins, sales-per-product) | `_imported_at` 2026-08-11 — **28 days older than the artefact stamped over it** | no (rebuilt in CI) |
| `data/external/snapshots/<date>/` | 29 sealed days 2026-08-11 … 2026-09-08; ~518k Alonit price rows/day over 154 branches, ~5.1k Wolt rows/day over 9 venues | daily | yes (force-added by CI) |
| `data/external/silver/` | locally a May-25 fossil (1,374 rows); rebuilt from snapshots by `rehydrate_silver.py` inside `data:refresh` | — | no |
| `data/signals/`, `data/recommendations/`, `data/matching/product_matches.parquet` | **absent locally**; exist only inside a CI run | — | no |
| `public/data/operational.json` | 4,496 recommendations of 6 types; `meta.competitorSignals: 515516` | 2026-09-08 | yes |
| `public/data/market-context.json` | weather + calendars; `demandSignals: {}`, `ownerAnswers` all empty | 2026-09-08 | yes |
| `public/data/assortment_gap.json` | 300 rows | **2026-08-11**, nothing regenerates it | yes |
| `configs/owner_answers.yaml` | `carried: {}`, `shelf_life_days: {}`, `shelf_life_categories: {}` | empty | yes |
| Browser localStorage | 7 keys; only `smartshelf.demoState.v1` has a (dormant) Firestore mirror; `smartshelf.operationalActions.v1` (outcomes) and `smartshelf.ownerAnswers.v1` (answers) never leave the device | per device | — |
| `data/internal/expiry/`, `data/internal/receiving/` | **do not exist** | — | — |

### 3.3 Modules, by pipeline

**Internal (POS) half — Python**

```
yomyom-inventory.csv ──► src/internal_pos/pos_importer.py ──► silver_pos/{products,inventory,margins,sales}.parquet
sales/*.csv ──► scripts/import_yomyom_sales.py ──► REWRITES silver_pos/yomyom_sales.parquet (one row per product;
                                                     month from FILENAME; reconcile_* columns)
silver_pos ──► src/recommendations/operational_recommendations.py ──► 6 types (see §3.4)
            ──► scripts/export_dashboard_data.py ──► public/data/operational.json  (+ sources.json)
```

**Market half — Python**

```
CI: alonit_connector (FTPS) + delivery_venue_connector (Wolt) ──► snapshots/<date>/ ──► rehydrate_silver ──► silver/
silver/ ──► src/signals/competitor_product_signals.py ──► signals/competitor_product_signals_<ts>.parquet
signals + silver_pos/products ──► src/matching/product_matching.py ──► matching/product_matches.parquet
matches ──► src/recommendations/product_recommendations.py ──► WATCH_PRODUCT only (PRICE_CHECK: 0 of 1,855)
```

**Browser — JavaScript (two unrelated spines)**

```
Pipeline spine:  fetch operational.json ──► rankActions (actionPriority.js) ──► OperationalPage (money/data split, TOP_N=20)
Demo spine:      src/data/demoProducts.js (193k lines, generated) ──► inventoryEngine ──► reorderEngine ──► 10 other pages,
                 openQuestions (430 questions on real data), planogram, report, dashboard
```

The two spines share nothing but the barcode. Only `OperationalPage` and `ExpiryPage`
read the pipeline artefact; every other page is fed from the generated demo module.

### 3.4 The findings that decide the design

1. **Three implementations of the price rule, all different.**
   `operational_recommendations.py:288` flags |gap| ≥ 5 % in either direction (1,147 rows);
   `actionPriority.js` re-ranks them with `credibility.js` guards and attaches ₪;
   `print_figures.py:83` reads the *raw CSV* with a hard-coded 18 % ceiling (68 inverted +
   136 above). None derives the ceiling from data (SPEC-001 FR-004), none distinguishes
   inverted from above-ceiling as the spec requires, and the reproduction path
   (`npm run figures`) does not run the rule the surface runs — a standing INV-065 breach.

2. **The surface's top-20 is money on a stock quantity.** `actionPriority.js:85-92` values
   `CHECK_STOCK_DISCREPANCY` as `unaccounted units × cost`; run over the committed artefact
   the whole visible top-20 is that figure (top row ₪8,718.96; one-off total ₪103,828.75).
   `print_figures.py` still prints the confirmed/estimated split (₪76,500 / ₪27,328) and
   the ₪919,170 idle valuation — both withdrawn by `intent.md` §2ب and §4ب and forbidden by
   SPEC-002 FR-023 and SPEC-004 FR-069a.

3. **Owner state has no return leg.** `answerStore.toYaml()` is called by nothing but a
   test; `scripts/import_owner_answers.py` (named in the YAML header) never existed on any
   branch; Firestore is off; completion actions (`smartshelf.operationalActions.v1`) are
   written to localStorage only and are never mirrored even when Firestore is on. Every
   `ownerAnswers` map in the pipeline is empty. SPEC-005 FR-088/NFR-042 and SPEC-006
   FR-113/NFR-052 are unmet today.

4. **Three V1 capabilities do not exist.** Catalogue lifecycle (SPEC-004) has no code
   anywhere (`grep IDLE|WITHDRAW|DEAD_STOCK` → nothing; only `print_figures.py` counts the
   classes). Competitor price position as specified (balanced reference, cost floor,
   declared policy, attention threshold, format allowance — SPEC-003) does not exist;
   `PRICE_CHECK` is a different rule and produced 0 rows. Owner cost questions (SPEC-005's
   12) do not exist; `openQuestions.js` asks V2 questions (carried / shelf life).

5. **Store-format discipline is enforced only in JavaScript, and not on the path that
   matters.** `product_recommendations.py` applies no affinity at all; `storeFormat.js`
   gates a browser-side competitor engine fed by `src/data/marketData.js`, generated
   2026-08-09 and lacking the `storeType` key. The protected behaviour C-20/C-21 protects a
   demo path, not the product path.

6. **A destructive ordering bug in the one command the rules say to run.**
   `refresh_pipeline.py` never runs `import_yomyom_sales.py`; with `--input` it re-runs the
   POS importer, which rewrites `yomyom_sales.parquet` with the 7-column schema and wipes
   `reconcile_*`, silently zeroing `CHECK_STOCK_DISCREPANCY`. Only the CI workflow runs the
   two importers in the right order.

7. **Barcode normalisation disagrees across modules.** `presence.py`, `labelled_store.py`,
   `join_yomyom_kaggle.py`, `build_assortment_gap.py` strip leading zeros;
   `competitor_product_signals.py` and `product_matching.py` do not — barcode-exact
   matching misses zero-padded pairs. `operational_recommendations.py` strips only inside
   the reconciliation rule.

8. **Evidence semantics are wrong for the catalogue rule.** Exactly one product in the
   catalogue appears in a sales report with zero units; 5,848 of 7,463 classifications
   rest on *no row at all* (GAP-009). `import_yomyom_sales.py` collapses the seven reports
   to one row per product and derives `units_sold_7d` from a monthly average — a
   per-product-per-month table, the shape SPEC-004 FR-060b needs, is never written.

9. **No PR/push CI.** All three workflows are cron or manual. 498 + 324 + 29 tests exist and
   nothing runs them before a merge.

10. **Repository weight that serves nothing.** `code/` (176 tracked files, a stale full copy
    of an older generation with a Windows path in its README) and `SmartShelf AI/` (22
    files, 7 MB) are tracked, un-ignored by `.vercelignore` and ESLint, and referenced by
    nothing. ~29 of 66 scripts have no execution path. Two explanation generators, two
    planogram engines and two Firestore schemas coexist.

### 3.5 Data facts that bound the design (measured)

| Fact | Value | Consequence |
|---|---|---|
| Catalogue rows / distinct barcodes / without barcode | 7,674 / 7,319 / 307 | 307 are hygiene records (SPEC-002 FR-028), outside every other population |
| Shelf + Wolt price both > 0 · identical · inverted · above | 6,260 · 4,932 · 68 · 1,260 | SPEC-001 population; 151 zero-valued Wolt prices are *absent*, not zero |
| Negative stock · zero stock · zero/absent cost · zero price | 625 · 4,251 · 1,270 · 223 | Hygiene and question populations |
| Products with any sales row (7 reports) | 1,565 (20.4 %) | 79.6 % have `none`, never zero |
| Products in reports with observed zero units | 1 | ASM-030 carries 5,848 classifications (GAP-009) |
| Reconciliation flags (implied opening < 0, receipts > 0) | 458 (artefact) / 459 (`stock_reconciles == False`) | Intent says 371 — the count is window-dependent and must be reproduced, not quoted |
| Products with ≥ 1 competitor price (all snapshots) | 2,650 — Alonit 2,548 · King Store 388 · Shufersal 322 · Victory 325 · Rami Levy 277 | Intent's 1,970 / 755 / 1,314 / 663 came from Kaggle-era files that never ran in CI — SPEC-003 counts must be recomputed by the new capability, not carried |
| Competitor snapshot size | 518k rows/day, 154 branches; 5.1k Wolt rows/day, 9 venues | Signal build must stay incremental (it was SIGTERM'd once on a runner) |
| Sales evidence window | 7 months, < a full annual cycle | Every withdrawal is provisional (FR-063a) until the two-year reports arrive |

---

## 4. Current Subsystem Assessment

Status vocabulary: **VERIFIED_WORKING** (executed and observed correct against its own
contract) · **LIKELY_WORKING** (tests pass, not executed end-to-end here) · **UNVERIFIED**
(no test, not executed) · **BROKEN** (executed or read and found wrong) ·
**DEAD_OR_OBSOLETE** (no execution path, or serves a removed requirement). "Correct" here
means correct against its *own* contract; fit with the specifications is judged in §5.

| # | Subsystem | Status | Evidence |
|---|---|---|---|
| S1 | `src/internal_pos/pos_importer.py` + `pos_normalizer.py` (POS CSV → 4 silver tables) | LIKELY_WORKING | Produces 7,674 rows in all four tables; encoding/delimiter sniffing; **no tests**; YAML claims a negative-stock clamp that does not exist (rows pass through raw — which is what SPEC-004 C-32 needs) |
| S2 | `scripts/import_yomyom_sales.py` (7 reports → per-product velocity) | BROKEN for V1 | Month from filename; collapses to one row per product; `units_sold_7d` synthesised from a monthly mean; never called by `refresh_pipeline`; overwritten by S1 when `--input` is passed |
| S3 | `src/recommendations/operational_recommendations.py` | LIKELY_WORKING / spec-divergent | Runs, deterministic, no tests; flat 5 % Wolt rule; emits `cost_price` on reconciliation rows so the browser can price them; margin rule unspecified by any V1 spec |
| S4 | `scripts/export_dashboard_data.py` | VERIFIED_WORKING | `EmptyExportError` guard tested; but cannot express "unavailable" and re-types thresholds inline |
| S5 | `scripts/refresh_pipeline.py` | BROKEN (ordering) | See §3.4-6; step isolation and `partial/degraded` reporting are sound |
| S6 | `scripts/print_figures.py` | BROKEN vs specs | Parallel rule implementation over raw CSV; prints withdrawn money figures; 18 % constant |
| S7 | Collectors + snapshots (`alonit_connector`, `delivery_venue_connector`, `seal_snapshot`, `write_snapshot_manifest`, `check_collection_health`, `rehydrate_silver`) | VERIFIED_WORKING | 29 consecutive sealed days; manifests; tests for seal/manifest/health; the portal fallback path in `alonit_connector.py:753` has a `NameError` (dead branch) |
| S8 | `src/signals/competitor_product_signals.py` | LIKELY_WORKING | 515,516 signals in the last CI run; incremental load; no tests; no zero-stripping of barcodes |
| S9 | `src/matching/product_matching.py` | LIKELY_WORKING | Three passes with stated thresholds; global dedupe to one row per barcode discards branch prices; no tests |
| S10 | `src/recommendations/product_recommendations.py` | UNVERIFIED / spec-divergent | WATCH_PRODUCT (V2/INT-005) is its only live output; no format gating; two dead evidence branches |
| S11 | `src/common/store_types.py` + `configs/store_types.yaml` | VERIFIED_WORKING | 18 tests; affinity matrix, floor 0.3, exclusion at 0.0; one collected venue (Super Alonit Einat) unclassified |
| S12 | `src/context/*` (weather, calendars, demand signals, owner answers loader) | LIKELY_WORKING, inert | Tests pass; `demandSignals` is `{}` in the artefact; consumes only V2 inputs |
| S13 | `src/expiry/`, `src/internal/receiving.py`, `restock_reconcile.py` | LIKELY_WORKING, no data | Tested; `data/internal/{expiry,receiving}` do not exist; V2 (INT-007) |
| S14 | `src/snapshots/velocity.py`, `censored_demand.py`, `pos_snapshots.py` | LIKELY_WORKING, off-path | Tested; velocity from snapshot deltas is documented as inert (identical re-imports); V2 |
| S15 | `src/lib/analytics/actionPriority.js` + `credibility.js` | VERIFIED_WORKING vs its own contract; BROKEN vs D-1 | 18 tests; attaches money to a stock quantity |
| S16 | `src/pages/OperationalPage.jsx` + `ActionCard.jsx` | VERIFIED_WORKING vs its own contract; spec-divergent | e2e passes; TOP_N 20, "show all N", "Showing 20 of N", summed per-sale total |
| S17 | `src/lib/operational/completionActions.js` | VERIFIED_WORKING | 22 tests; closed enums; optimistic write with rollback; localStorage only |
| S18 | `src/lib/persistence/{localStorageAdapter,firestoreAdapter,persistence}.js` | LIKELY_WORKING | 9 reconcile tests (LWW by `updatedAt`); Firestore path never exercised in this environment |
| S19 | `src/lib/questions/{openQuestions,answerStore}.js` + `QuestionPanel` | VERIFIED_WORKING vs its own contract; wrong questions for V1 | 17 tests; asks V2 questions; YAML export unreachable |
| S20 | `src/lib/i18n/*` + guards | VERIFIED_WORKING | 673 keys × 3 languages, parity tests, e2e untranslated-control and split-number guards |
| S21 | `src/lib/analytics/reorderEngine.js`, `inventoryEngine.js`, `demandEngine.js`, `competitorEngine.js`, `storeFormat.js` (browser engines) | LIKELY_WORKING, V2 scope | 100+ tests; decide orders from stock quantities the owner distrusts; fed by the generated demo module |
| S22 | `src/lib/planogram/*`, `StoreLayoutPage`, `ShelfPlanPage` | LIKELY_WORKING, V4 scope | e2e passes; the older `PlanogramPage` + `complianceEngine` + `planogramEngine` are unreachable duplicates |
| S23 | `src/lib/ai/*`, `src/api/llm_proxy.py` | BROKEN / off | Proxy never launched; `buildLLMExplanationPayload` never called, so `factsGuard` would reject any numeric reply; unspecified by any spec |
| S24 | `src/telemetry/*` | DEAD_OR_OBSOLETE | Second build entry, unlinked, one commit, sees one browser's localStorage |
| S25 | `src/lib/posConnectors/*` (browser CSV upload, Comax stub) | DEAD_OR_OBSOLETE under D-12 | Second import path; Comax stub always fails |
| S26 | `src/data/{demoProducts,marketData,marketParams,storeTypes,marketContext}.js` + `normalize-datasets.mjs` | LIVE but OBSOLETE under the target | Generated snapshots of pipeline data compiled into the bundle (4.36 MB); `marketData.js` dated 2026-08-09 |
| S27 | `src/data/{mockMarketData,datasetCatalog}.js`, `mockAI.js`, `firestore_writer.py`, `kaggle_supermarket_importer.py`, `mcp_server/`, `mcp_price_adapter.py`, `tenbis_connector.py` (unreachable branch), `join_yomyom_kaggle.py`, `export_competitor_market_data.py`, `build_assortment_gap.py`, `export_assortment_gap.py`, `alonit_signal_pipeline.py`, 17 unreferenced scripts | DEAD_OR_OBSOLETE | Grep-verified: no execution path from `package.json`, `.github/`, `refresh_pipeline.py`, `collect_daily.sh`, or any live module |
| S28 | `code/`, `SmartShelf AI/` | DEAD_OR_OBSOLETE | Tracked copies; referenced by nothing; uploaded to Vercel and linted on every run |
| S29 | `scripts/check_signals_live.mjs` | VERIFIED_WORKING (mechanism) | Proves wiring with synthetic probes; all its probes target V2 reorder signals |
| S30 | `e2e/*` (Playwright) | VERIFIED_WORKING | 29 tests; the UI-invariant suite is the executable form of C-53 |

---
## 5. Reuse / Refactor / Replace / Remove Decisions

Each decision was made on correctness against the specifications, coupling, testability
and migration risk — not on how much code it saves or how the code looks. Component
numbers refer to §4.

### 5.1 REUSE — kept as-is or with local fixes

| Component | Current responsibility | Status | Specs served | Why | Risks |
|---|---|---|---|---|---|
| S7 Collectors, snapshots, manifests, health checks, `rehydrate_silver.py` | Daily competitor observation capture and durable history | VERIFIED_WORKING | SPEC-003 inputs; SPEC-007 C-60, C-61 | Irreplaceable history, tested, 29 clean days. The only local fix: delete the dead portal branch with the `NameError` | FTPS credentials and Wolt markup drift are external; the watchdog covers silent stops |
| S8 `competitor_product_signals.py` | Unified competitor observation table | LIKELY_WORKING | SPEC-003 inputs | Sound schema, incremental load. Fix: strip leading zeros from barcodes (§3.4-7); add tests | No tests today |
| S9 `product_matching.py` | Our barcodes ↔ competitor products | LIKELY_WORKING | SPEC-003 precondition (shared identifier) | Three-pass matching with stated thresholds is exactly what FR-043 needs recorded per item. Fix: barcode zero-stripping; stop the global one-row-per-barcode dedupe so *every* store's price survives to the reference step (FR-044 needs cheapest per format) | Fuzzy matches are the OQ-303 risk; kept in the review band, never auto-approved above 0.85 |
| S11 `store_types.py` + `configs/store_types.yaml` | Store formats and affinity | VERIFIED_WORKING | SPEC-003 FR-040 … FR-042, C-20 … C-22, INV-020 … INV-022 | Tested and already the protected behaviour. Fix: classify the Super Alonit Einat venue; mark the client store's own venue `role: client` so D-5 is enforceable | — |
| S1 POS importer | POS CSV → silver | LIKELY_WORKING | All V1 inputs | Works on the real export; fix the YAML lie about clamping (document that stock is preserved raw, C-32) and add the `--as-of` vintage; add tests | Header drift in a future export — the mapping YAML is the seam |
| S17 `completionActions.js` (enums, entry validation, optimistic write) | Owner outcomes per entry | VERIFIED_WORKING | SPEC-006 FR-112 … FR-115 | Closed enums map cleanly: DONE→acted, DISMISSED→declined, SNOOZED→deferred; dismissal reasons are the pilot's most valuable output. Moves under the owner-state module; persistence target changes | Legacy ids need the one-time translation (ADR-009) |
| S18 Persistence adapters (localStorage, Firestore, LWW reconcile) | Durable owner state | LIKELY_WORKING | SPEC-005 NFR-042; SPEC-006 NFR-052, C-52 | The reconcile logic is tested; it becomes the single owner-state channel | Firestore never exercised here — first-run risk (§22) |
| S20 i18n + guards | Three languages, RTL, digit forms | VERIFIED_WORKING | SPEC-006 C-53, AC-112 | Reused unchanged; new keys added | Key parity test enforces completeness |
| S30 e2e suite | UI invariants | VERIFIED_WORKING | AC-112 | Reused; surface specs replaced | — |
| S13 receiving/expiry capture (`ReceivingCaptureForm`, `receivingQueue.js`, `src/internal/receiving.py`) | Staff capture of deliveries and expiry dates | LIKELY_WORKING | none in V1; `intent.md` §7/§8 schedule the *capture* from 12/9 | Kept as a route so the 30-day counter can start; produces V2 data, consumes nothing from V1 | Its CSV hand-off is manual; acceptable for capture, revisited in V2 design |
| S29 `check_signals_live.mjs` (mechanism) | Prove a signal moves an output | VERIFIED_WORKING | CLAUDE.md rule 12 | The INACTIVE/INERT distinction is right; probes are retargeted to V1 capabilities (§18) | — |

### 5.2 REFACTOR — logic kept, shape changed

| Component | Decision | Why | Specs served | Risks |
|---|---|---|---|---|
| S2 `import_yomyom_sales.py` | Split into (a) a **per-product-per-month** silver table `sales_monthly.parquet` (barcode, month, units, receipts, revenue) and (b) the derived per-product summary; called by the engine run, never by a POS-only import; `import_pos_file` no longer touches the sales table | FR-060b (annual-cycle test), FR-061 (window stated), rule 13 (`none` vs zero) need month granularity; fixes §3.4-6 | SPEC-002 FR-020/021; SPEC-004 FR-060 … FR-063c | Month-from-filename stays the only date source — recorded as a vintage assumption |
| S3 `operational_recommendations.py` | Split into capability modules under `src/engine/`: the reconciliation arithmetic and hygiene rules are kept verbatim; the Wolt rule is replaced (§5.3); money-bearing fields leave the reconciliation row; `gap_ratio` becomes the ordering key | The arithmetic is exactly SPEC-002 FR-020; only its packaging is wrong | SPEC-002 FR-020 … FR-033 | None material |
| S4 `export_dashboard_data.py` | Becomes `src/engine/publish.py`: typed capability contract, availability status, vintages, thresholds, atomic write; the `EmptyExportError` idea generalises to "refuse on any capability without a status" | ARCH-DRIVER-002, -003, -007 | SPEC-006 FR-117, INV-057; SPEC-007 FR-120, FR-123 | Schema change — the browser migrates with it (§20) |
| S5 `refresh_pipeline.py` | Becomes `scripts/run_engine.py`: fixed step order (owner-state pull → POS import → sales import → rehydrate → signals → matching → capabilities → publish), same step isolation and `partial/degraded` reporting | Fixes ordering; one entry point for CI, local and reproduction | SPEC-007 FR-124, NFR-062 | — |
| S16 `OperationalPage` | Replaced by `DailyPage` over a pure `compose()`; the search box, print button, handled list with undo, and source strip are kept as presentation | SPEC-006 in full | SPEC-006 | — |
| S15 `actionPriority.js` | Ordering moves to the engine (per capability, published `ordering_key`); the JS keeps only `compose()` (admission ∧ outcome ∧ allocation ∧ dedupe ∧ bound). `credibility.js` thresholds (₪0.50, 2×, 300 %) move into the engine's D-4 artefact rule | ARCH-DRIVER-001, -003 | SPEC-001 FR-010; SPEC-006 FR-104 … FR-108 | The 300 % gap guard has no spec; it is kept as an *exclusion counted and reported* under FR-010's "artefact" definition — flagged in §22 |
| S19 questions | The question *engine* moves to Python (`owner_questions.py`, cost questions only in V1); the `QuestionPanel` and `answerStore` shape (barcode-keyed) are kept; answers persist through the owner-state store | SPEC-005 FR-080 … FR-093 | SPEC-005 | The V2 questions (carried, shelf life) return with V2 |
| S12 `src/context/owner_answers.py` | Generalised into `src/owner_state/` (pull, validate, expose answers/outcomes/revivals to capabilities) | ARCH-DRIVER-004 | SPEC-005 FR-093 | — |

### 5.3 REPLACE — same responsibility, new implementation

| Component | Replaced by | Why | Specs served |
|---|---|---|---|
| Wolt gap rule (in S3) | `src/engine/price_consistency.py`: four states, derived ceiling with an explicit derivation record, inverted = confirmed loss, above-ceiling = question, D-4 exclusions counted | The current rule is a different product (flat 5 %, both directions, no characterisation) | SPEC-001 FR-001 … FR-013 |
| S10 `product_recommendations.py` (competitor family) | `src/engine/competitor_position.py`: format-gated sources, balanced reference, measured format allowance, cost floor before comparison, declared policy 60 %, attention 100 %, coverage against the full catalogue, position per source | SPEC-003 is a new capability; `WATCH_PRODUCT` is INT-005 (V2) and leaves V1 | SPEC-003 FR-040 … FR-053 |
| S6 `print_figures.py` | `scripts/figures.py` = the engine in print mode (no publish), printing every registered figure with vintage and reproduction time | INV-065: reproduction must run the surface's rule | SPEC-007 FR-124 … FR-127, NFR-060 … NFR-063 |
| `configs/owner_answers.yaml` round trip | Owner-state store (Firestore, browser-written) pulled by the engine and mirrored to `data/owner/owner_state.json` | The YAML leg never existed | SPEC-005 FR-088, NFR-042 |
| Legacy design docs | This document | — | — |

### 5.4 REMOVE — from the V1 product, build and routes

| Component | Why it goes | Reversibility |
|---|---|---|
| S26 generated demo spine (`src/data/demoProducts.js`, `marketData.js`, `marketParams.js`, `storeTypes.js`, `marketContext.js`, `normalize-datasets.mjs`, `loadDemoStoreData`, `demoDataConnector`) | Compiles pipeline data into the bundle (4.36 MB), a second copy of the truth that rule 7 warns can overwrite committed files; every V1 figure comes from the artefact | git; `normalize:data` is gone for good — the artefact is the only bridge |
| S21 browser engines (`reorderEngine`, `inventoryEngine`, `demandEngine`, `competitorEngine`, `storeFormat.js`, `reorderFacts`, `explainReorder`) and their pages (`RecommendationsPage`, `ApprovedOrdersPage`, `DashboardPage`, `ReportPage`, `PriceGapPage`, `ProductsPage`, `AssortmentGapPage`) | V2 scope (INT-004/005), decide from stock quantities the intent distrusts, fed only by the demo spine. `storeFormat.js`'s rule is re-implemented in the engine (S11 already holds the data) | Out of the build now; deleted from the tree at the end of Phase 4 under a git tag `v1-attic`; V2 design decides what returns and in which language |
| S22 planogram (`src/lib/planogram/*`, `StoreLayoutPage`, `ShelfPlanPage`, `PlanogramPage`, `complianceEngine`, `planogramEngine`, `affinityEngine`) | V4 scope (INT-006); `intent.md` §9.7 says the planogram is *presented as a dated plan, not a shipped feature* | Same tag; the e2e `shelf-planning.spec.js` goes with it |
| S23 LLM layer (`src/lib/ai/*`, `src/api/llm_proxy.py`, Gemini env, `compare_explanations.mjs`, `report_reorder_explanations.mjs`) | No specification mentions a model; the guard is wired shut; D-12 forbids a runtime server for one store | git |
| S24 telemetry entry (`telemetry.html`, `src/telemetry/*`) | Unlinked, single-device; INT-MEAS is *registered, unspecified*; the design captures what it will need (outcome snapshots, §10) and builds no surface | git |
| S25 browser POS connectors (`csvConnector`, `comaxConnectorStub`, `DataSourcePage`) | D-12: one POS import path, the pipeline | git |
| S27 dead modules and 17 unreferenced scripts; the second Firestore schema (`firestore_writer.py`); `mcp_server/`; `.mcp.json` entry | No execution path; the MCP entry fails to start (`python` not on PATH) | git |
| S28 `code/`, `SmartShelf AI/` | Tracked copies of an older generation, deployed and linted for nothing | git |
| `public/data/assortment_gap.json`, `market-context.json` as V1 inputs | Stale (Aug 11) and V2-only respectively; `market-context.json` continues to be produced by the nightly run for V2 but nothing in V1 reads it | — |

**What this leaves in the V1 product:** the collectors and snapshot history, the POS and
sales importers, the signal and matching layers, the store-type registry, one engine with
five capabilities plus a surface producer and a provenance module, one publisher, one
artefact, one owner-state store, one browser app with a daily page, five capability pages,
a question panel, a receiving-capture page and a data page, the i18n module, and the test
and CI infrastructure. Roughly 40 % of the current source tree.

---

## 6. Target Architecture

### 6.1 Overview

```
                         SOURCES (immutable inputs)
  ┌──────────────────────┐  ┌────────────────────────┐  ┌──────────────────────────┐
  │ POS inventory CSV    │  │ 7+ monthly sales CSVs  │  │ competitor snapshots     │
  │ (committed, dated)   │  │ (committed, dated)     │  │ data/external/snapshots/ │
  └──────────┬───────────┘  └───────────┬────────────┘  │ (CI writes daily)        │
             │                          │               └────────────┬─────────────┘
             ▼                          ▼                            ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │  INGEST (Python, existing modules)                                              │
  │  pos_importer → silver_pos/{products,inventory,margins}                         │
  │  sales_importer → silver_pos/sales_monthly (+ per-product summary)              │
  │  rehydrate_silver → competitor_product_signals → product_matching               │
  └─────────────────────────────────────┬───────────────────────────────────────────┘
                                        │ EngineInputs (frames + vintages)
  ┌───────────────────┐                 ▼
  │ OWNER-STATE STORE │ pull   ┌────────────────────────────────────────────────────┐
  │ (Firestore, one   │──────► │  ENGINE  src/engine/   (pure, deterministic)       │
  │  store document   │        │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
  │  tree; browser is │        │  │ price_       │ │ reconcilia-  │ │ competitor_│ │
  │  the only writer) │        │  │ consistency  │ │ tion+hygiene │ │ position   │ │
  └────────▲──────────┘        │  │ SPEC-001     │ │ SPEC-002     │ │ SPEC-003   │ │
           │                   │  └──────────────┘ └──────────────┘ └────────────┘ │
           │ answers,          │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
           │ outcomes,         │  │ catalogue_   │ │ owner_       │ │ margin     │ │
           │ revivals          │  │ lifecycle    │ │ questions    │ │ (unspec'd, │ │
           │                   │  │ SPEC-004     │ │ SPEC-005     │ │ browse only│ │
           │                   │  └──────────────┘ └──────────────┘ └────────────┘ │
           │                   │  surface_candidates (SPEC-006 producer side)       │
           │                   │  provenance + figure registry (SPEC-007)           │
           │                   └────────────────────┬───────────────────────────────┘
           │                                        │ CapabilityOutput × n
           │                                        ▼
           │                   ┌────────────────────────────────────────────────────┐
           │                   │  PUBLISH  src/engine/publish.py                    │
           │                   │  schema check · money assertion · availability     │
           │                   │  assertion · atomic write                          │
           │                   └────────────────────┬───────────────────────────────┘
           │                                        │
           │                     public/data/dashboard.json  (committed by CI)
           │                                        │ fetch (no-store)
  ┌────────┴───────────────────────────────────────▼───────────────────────────────┐
  │  BROWSER  (static SPA, Vercel, Basic Auth)                                      │
  │  loadDashboard (schema-validated) → compose() → DailyPage (≤10)                 │
  │  capability pages (full sets, counts, thresholds, window) · QuestionPanel (≤3)  │
  │  ownerState (answers · outcomes · revivals) → localStorage cache → Firestore    │
  │  receiving capture (V2 data, starts 12/9) · data page (vintages, status)        │
  └─────────────────────────────────────────────────────────────────────────────────┘

  REPRODUCTION:  npm run figures  ==  scripts/figures.py  ==  ENGINE in print mode
                 (same modules, same rules, current silver + owner state, no publish)
```

### 6.2 The five properties the shape guarantees

1. **Single rule path.** The engine is the only place a business rule exists. The browser
   holds one pure function (`compose`) whose output is a selection, never a figure.
2. **Single artefact.** One versioned JSON with explicit per-capability status, vintages
   and thresholds. The browser reads nothing else.
3. **Single mutable state.** Owner state — nothing else in the system is written by a
   human. Everything else is derived and can be regenerated from committed inputs.
4. **Single reproduction path.** `figures` runs the engine. It cannot disagree with the
   surface except by reading newer data, which it reports (FR-127).
5. **Single scale ceiling.** One store, one owner, one CSV path, one nightly job. Nothing
   in the shape assumes more, and nothing prevents a later V2 from adding capabilities as
   further engine modules with the same contract.

### 6.3 What runs where, and when

| When | Where | What |
|---|---|---|
| Nightly (00:00 UTC) | GitHub Actions | collect → seal → pull owner state → import POS + sales → rehydrate → signals → matching → engine → publish → `check:signals` → commit `dashboard.json` + `data/owner/owner_state.json` |
| On a new POS export | Team laptop or manual dispatch | commit the CSV → same run (`npm run data:refresh`) |
| Each morning | Owner's phone | fetch artefact → compose → act → outcomes written to owner state |
| On challenge | Team laptop | `npm run figures` → engine print mode over current data |
| On push / PR | GitHub Actions (new `ci.yml`) | lint · vitest · pytest · artefact contract test |

---
## 7. Components and Responsibilities

Every behaviour below has exactly one owner. "Forbidden" lists what a component must
never do, because in the current code it does.

### 7.1 Ingestion (Python, `src/internal_pos/`, `scripts/`, `src/signals/`, `src/matching/`)

| Component | Responsibility | Owns | Inputs → Outputs | Depends on | Forbidden |
|---|---|---|---|---|---|
| **POS importer** (`pos_importer.py`) | Turn the POS inventory CSV into typed silver tables, preserving values raw | `silver_pos/{products,inventory,margins}.parquet`, POS vintage (`--as-of`, default: file mtime) | CSV → 3 parquet tables + quality report | `configs/pos_schema_mapping.yaml` | Writing the sales table; clamping, rounding or dropping negative stock; inferring anything |
| **Sales importer** (`import_yomyom_sales.py`, refactored) | Turn the monthly reports into month-grained evidence | `silver_pos/sales_monthly.parquet` (barcode, month, units, receipts, revenue, cost) and the derived `silver_pos/sales_summary.parquet` (per product: months present, total units, last month with units) | CSVs → 2 parquet tables + the **evidence window** record `{months:[…], first, last, count, full_annual_cycle}` | — (needs no stock date: the reconcile window is cut in the engine, once per run — ADR-026) | Synthesising `units_sold_7d`; writing any row for a product absent from every report (absence stays absence) |
| **Competitor observation builder** (`competitor_product_signals.py`) | One row per (barcode, store) with the freshest price and observation time | `data/signals/competitor_product_signals_<ts>.parquet` | rehydrated silver → signals | `rehydrate_silver.py` | Dropping stores; interpreting formats |
| **Matcher** (`product_matching.py`) | Our barcode ↔ competitor products with method and confidence | `data/matching/product_matches.parquet`, review queue | products + signals → matches | rapidfuzz | Collapsing to one store per product; auto-approving fuzzy matches above the stated band |
| **Store registry** (`store_types.py`) | Format and affinity per store; client-store flag | `configs/store_types.yaml` (hand-maintained, C-22) | — | — | Inferring over a manual classification |

### 7.2 Owner state (Python `src/owner_state/`, JS `src/owner/`)

| Component | Responsibility | Owns | Inputs → Outputs | Forbidden |
|---|---|---|---|---|
| **Owner-state store** (Firestore `stores/{store}/ownerState/*`, localStorage cache) | Durable record of what the owner told the system and did | answers, outcomes, revivals (§10.3) | browser writes; engine reads | Engine writes; inference writes (INV-042) |
| **JS `ownerState.js`** | The only browser module that reads/writes owner state; validates entries; translates legacy ids once | localStorage keys; sync via the existing adapters | UI events → records | Deriving money; guessing a missing reason |
| **Python `owner_state/pull.py`** | Pull the store at run start; validate; mirror to `data/owner/owner_state.json`; expose `OwnerState` to capabilities | the mirror file and its `pulled_at` vintage | Firestore → JSON → `OwnerState` | Writing back; silently substituting an empty state when the pull fails (status must say `unavailable`) |

### 7.3 Engine (Python `src/engine/`)

**What a capability is (ADR-014).** *A capability is the smallest unit that can
independently become unavailable.* Availability is the only one of the roles the word
carries — spec, module, status, registry entry, badge, page, precedence slot — that is
forced by the world rather than chosen: the inventory CSV arrives, the seven monthly sales
reports may not. Every other role follows the availability unit; none of them defines it.
Two consequences: a capability is **not** a Python module (`reconciliation.py` returns two
`CapabilityOutput`s), and a specification may produce **more than one** capability
(SPEC-002 produces two, which is why `CapabilityOutput.spec` is many-to-one).

All capability modules are pure: `run(inputs: EngineInputs, owner: OwnerState, policy: Policy) -> list[CapabilityOutput]`.
They read frames, never files; they never write. `EngineInputs` is built once per run by
`inputs.py` and carries every vintage.

| Capability | Spec | Responsibility | Owns (published) | Value policy | Ordering key |
|---|---|---|---|---|---|
| **price_consistency** | SPEC-001 | Classify every price-paired product into identical / within ceiling / above ceiling / inverted; derive and report the ceiling; exclude D-4 artefacts; characterise | `entries` (inverted, above), `counts` per state + excluded, `ceiling {pct | null, method, bands}` | **per_sale**, confirmed — inverted entries only (`shelf − delivery`, labelled recurring, FR-012). Above-ceiling entries are questions (FR-008): the difference travels as evidence (FR-009), never as a value | inverted: value desc; above: markup desc |
| **reconciliation** | SPEC-002 (detection half) | Flag negative implied opening balance (receipts > 0) | `entries` (flagged), `counts`, `window` | **none** (INV-010) | `gap_ratio` desc |
| **hygiene** | SPEC-002 (hygiene half) | Structurally invalid records: negative stock, no usable barcode, absent price | `entries` (one `variant` per reason), `counts` per reason | **none** (INV-013, INV-054) | reason group, then name |
| **competitor_position** | SPEC-003 | Format-gate sources; balanced reference; measured format allowance; cost floor first; policy breach at +60 %; attention split at +100 %; purchase-cost findings; coverage vs full catalogue; position per source | `entries` (attention, review, purchase_cost), `counts`, `thresholds {policy 60, attention 100, cost_floor 10, format_allowance | null, freshness_days}`, `coverage`, `position[]` | **none** in V1 (a breach is a question, FR-047/048; no amount is claimed) | premium over reference desc |
| **catalogue_lifecycle** | SPEC-004 | Classify living / withdrawable / idle; withdraw; revive; provisional statement; implausible-quantity questions; handover list; withdrawn-set exclusion for every other capability | `classification` per entry, `withdrawn[]` with evidence, `idle[]` ranked, `counts`, `window`, `provisional: bool` | **none** (D-11); `unit_cost` shown per idle entry, labelled per-unit | idle: `unit_cost` desc, missing cost last |
| **owner_questions** | SPEC-005 | Select the ≤3 cost questions; suppress withdrawn and idle; order by money × yield; report suppressed counts | `questions[]` (full ordered list, presentation limit stated), `suppressed_counts` | n/a | expected value desc |
| **margin_below_cost** *(unspecified)* | — | The existing `CHECK_MARGIN` rule, retained for its browse page only | `entries`, `counts` | per_sale (confirmed) — **but not admitted** to the surface (§22 SPEC-GAP-A) | loss desc |
| **surface_candidates** | SPEC-006 (producer side) | Stamp `actionable` conditions 1, 2 and 4 on every entry; assign `attention`; compute `value_kinds_present`; enforce one-entry-per-product precedence *within* the engine's own knowledge (the browser re-applies with live outcomes) | `meta.value_kinds_present`, per-entry `actionable`, `not_actionable_reason` | — | — |
| **provenance** | SPEC-007 | Figure registry: every published number registers `{name, value | null, unit, inputs, thresholds}`; vintages block; reproduction timestamp | `meta.vintages`, `meta.thresholds`, `figures{}` | — | — |
| **publish** | — | Validate against `schemas/dashboard.schema.json`; assert money policy; assert every capability has a status; write atomically (`.tmp` + rename); refuse otherwise | `public/data/dashboard.json` | — | Writing a partial artefact; defaulting a missing status to `available` |

The `run_engine.py` orchestrator owns step order, step isolation, the run manifest and
the `ok / partial / degraded` verdict (kept from `refresh_pipeline.py`).

### 7.4 Browser (JS `src/`)

| Component | Responsibility | Owns | Forbidden |
|---|---|---|---|
| **`loadDashboard.js`** | Fetch, validate against the same JSON schema, expose `status: loaded | unavailable | stale` with the artefact's vintages | in-memory artefact | Reporting a fetch failure as `ready`; defaulting missing capabilities to empty |
| **`compose.js`** (pure) | `compose(artefact, ownerState, config) → Surface`: admission (`actionable` ∧ no standing outcome) → allocation (`unvalued_places` of `bound`) → one place per product → bound; also `emptyState` vs `unavailable` | nothing persistent | Computing any figure; summing values; showing a remainder |
| **`DailyPage`** | Render the surface: ≤10 entries, capability badge, physical action, evidence, value with kind, estimate label, outcome controls, per-capability availability, empty state, data age | UI state only | Counts of unshown; totals |
| **Capability pages** (one per registry id: price_consistency, reconciliation, hygiene, competitor_position, catalogue_lifecycle, + margin browse) | Full sets (FR-102), per-capability `status` badge (FR-117), counts with window/thresholds/coverage, handover list download (FR-075), manual revival (FR-067), idle outcomes (FR-070) | UI state only | Re-ranking; re-deriving; rendering an unavailable capability as zero findings |
| **`QuestionPanel`** | ≤3 questions, answer / defer / revise; shows product, fact sought, why it matters | UI state only | Queue, total, progress (FR-086) |
| **`ownerState.js`** | See 7.2 | — | — |
| **Receiving capture** | Existing delivery/expiry capture (V2 data) | its own queue keys | Reading V1 artefact semantics |
| **Data page** | Vintages, source statuses, run status, last successful run | — | — |
| **i18n** | Unchanged | — | — |

### 7.5 Reproduction (`scripts/figures.py`)

Runs `run_engine.py` in `--print` mode: same ingestion (skipping steps whose
content-addressed outputs are current, §16), same capabilities, no publish; prints every
registered figure with `input_vintage` and `printed_at`, in Arabic as today. Exit code 1
and a named missing input when a figure is unavailable — never a remembered value.

---

## 8. Boundaries

| Boundary | Where | Crossing contract | Why it exists |
|---|---|---|---|
| **Source boundary** | committed CSVs and snapshots → ingestion | Files with a vintage. Nothing upstream is writable by the system (D-7) | The POS is external; the price server keeps one day; history exists only because it is committed |
| **Ingestion → Engine** | `EngineInputs` | Typed frames + vintages; a missing table is `None`, never an empty frame | Lets a capability say *unavailable* rather than compute over nothing (ARCH-DRIVER-002) |
| **Owner state → Engine** | `OwnerState` (read-only in Python) | Pulled once per run; `status: available | unavailable`, `pulled_at` | The engine must use answers (FR-093) but must never write them (INV-042) |
| **Engine → Publisher** | `CapabilityOutput` ×n | Schema-validated dataclasses; money policy declared per capability | Assertions happen here, before anything reaches disk |
| **Publisher → Browser** | `public/data/dashboard.json` (schema v2, `schemas/dashboard.schema.json`) | Immutable per run; validated on both sides against the same schema file | The only coupling between Python and JS; a contract test guards it (§18) |
| **Browser → Owner state** | `ownerState.js` → adapters → Firestore | LWW by `updatedAt`; browser is the sole writer | Durability (NFR-042/052) without a server |
| **Engine ↔ Reproduction** | none — the same code | `--print` vs `--publish` flag | INV-065 by construction |
| **Trust boundary** | Vercel Basic Auth (site) · Firestore rules pinned to one store path (owner state) · GitHub secrets (service account, FTPS) | see §15 | Single-user pilot |
| **Model/AI boundary** | none in V1 | — | No specification asks for a model; the legacy layer is removed (§5.4) |
| **V2/V4 boundary** | receiving capture writes its own queue; nothing in V1 reads it; the nightly run still produces `market-context.json` for V2 but no V1 component reads it | — | Keeps the data capture running from 12/9 without coupling V1 to unspecified capabilities |

---
## 9. Data and Control Flows

Sequence diagrams use the component names of §7. Each flow states the normal path, the
alternate path that matters, and the failure path.

### 9.1 Nightly ingestion and publish (every V1 scenario's precondition)

```
CI            Collectors     OwnerState.pull   Ingest        Engine         Publish        Git
 │  collect ─────►│                                                                          │
 │◄─ snapshot/<d> │                                                                          │
 │  commit snapshot ────────────────────────────────────────────────────────────────────────►│
 │  pull ────────────────►│  Firestore read                                                  │
 │◄── OwnerState{status, pulled_at} + data/owner/owner_state.json                            │
 │  import POS (--as-of) ───────────────►│                                                   │
 │  import sales (monthly + summary) ───►│                                                   │
 │  rehydrate → signals → matches ──────►│                                                   │
 │  run capabilities ──────────────────────────────►│ CapabilityOutput ×6 + figures         │
 │  publish ────────────────────────────────────────────────────►│ schema · money · status  │
 │                                                              │ atomic write dashboard.json
 │  check:signals (V1 probes) ───────────────────────────────────────────────────────────►  │
 │  commit dashboard.json + owner_state.json ──────────────────────────────────────────────►│
```

**Alternate — owner state unreachable.** `pull` returns `status: unavailable`. The run
continues: answers are treated as absent (FR-092 → D-3 behaviour), `owner_questions`
publishes `status: unavailable, reason: answer_storage_unavailable` (SPEC-005 §11:
"do not present questions that cannot be recorded"), outcomes are not applied in the
engine (the browser still applies its local copy), and `meta.vintages.owner_state`
records the failure. The run verdict is `degraded`; CI **does** publish (the artefact is
better than yesterday's) but goes red so someone looks.

**Alternate — no competitor snapshot today** (2026-09-02 happened). Rehydrate uses the
newest sealed day; `competitor_position` computes freshness per observation and marks
stale ones; if *no* observation is within the freshness bound the capability publishes
`unavailable: observations_stale`. Never zero findings.

**Failure — a step raises.** Step isolation records the error; downstream steps that
depend on it see `None` inputs and publish `unavailable`; the publisher still validates
the whole artefact. If the POS tables are missing entirely, *every* capability is
unavailable and the publisher refuses (extends `EmptyExportError`): yesterday's artefact
stays on disk and in git. CI fails.

**Failure — interrupted mid-publish.** The write is `dashboard.json.tmp` then `rename`;
readers never see a torn file. Withdrawal state is not stored anywhere else, so an
interrupted run cannot leave a half-applied withdrawal set (SPEC-004 §10).

### 9.2 The owner opens the surface (SPEC-006 SCN-100 … SCN-109)

```
Browser        loadDashboard    ownerState (cache→Firestore)    compose        DailyPage
 │ open ────────►│                                                                   │
 │◄── artefact (validated) or {status: unavailable}                                  │
 │ load ───────────────────────────►│ local cache, then reconcile                    │
 │◄── answers, outcomes, revivals                                                    │
 │ compose(artefact, owner, {bound:10, unvalued_places:3}) ────────►│               │
 │◄── Surface{entries ≤10, perCapability{status}, emptyState | unavailable}          │
 │ render ──────────────────────────────────────────────────────────────────────────►│
```

`compose` in order: (1) drop entries with `actionable: false`; (2) drop entries with a
standing outcome (acted, declined, deferred-until > now); (3) split by value kind —
valued entries ordered by `value.amount` desc; unvalued entries interleaved across the
unvalued capabilities in the stated order **reconciliation → competitor_position →
catalogue_lifecycle (idle) → hygiene**, each by its own `ordering_key`; (4) one place per
product — a valued entry wins; among unvalued, the capability order above (provisional,
OQ-601); (5) fill `unvalued_places` from the unvalued list and the remaining places from
the valued list; if either side is short, the other fills (the allocation is a
*reservation*, not a quota); (6) truncate to the bound. No count of the remainder is
produced (FR-101). `owner_questions` takes no place in this order: questions occupy their
own panel (OQ-503, §22.2).

**Why hygiene ranks last among the unvalued.** It is the largest set (1,155 records) and
the only one that is finite one-time cleanup rather than a recurring daily judgement;
ranked higher it would hold the reserved places for weeks and turn the morning screen
into the system's own housekeeping list. It stays admissible — FR-106 requires unvalued
work to have a route to the surface, and GAP-006 exists because hygiene had none — but it
fills a reserved place only when the capabilities above it have nothing to offer. The
order is provisional under OQ-601/OQ-602 and lives in `configs/policy.yaml`
(`surface.unvalued_order`), so it moves without a code change.

**Duplication across capabilities is real and step (4) is what handles it.** A product
with negative recorded stock can be both a `hygiene` entry and — once receipts exist — a
`reconciliation` entry; INV-056 forbids it occupying two places, and the order above
decides which one the owner sees. Both entry ids persist, so an outcome recorded on one
does not silently satisfy the other.

**Alternate — a capability is unavailable.** Its badge shows *unavailable* with the
reason; its entries are absent; the empty state is *not* shown if any capability is
unavailable (FR-118 distinguishes them).

**Failure — artefact fetch fails or fails validation.** The page shows *the data could
not be loaded*, with the last known vintage if a cached copy exists, and no entries. It
never shows "nothing to act on".

### 9.3 The owner records an outcome (SCN-104, SCN-105)

```
DailyPage    ownerState.js           localStorage      Firestore
 │ acted/declined/deferred ─►│ validate entry (closed enums)
 │                           │ write cache ────────►│
 │                           │ write-through ─────────────────────►│ LWW by updatedAt
 │◄── committed (only after the cache write succeeds)               │
 │ re-compose → entry gone                                          │
```

Entry recorded: `{entry_id, status, reason?, deferred_until?, at,
snapshot:{signal_family, capability, barcode, value?, kind?, characterisation}}`. The
snapshot is what INT-MEAS will need later (§10.3); it is captured now because it cannot be
reconstructed after thresholds move (FR-115). `signal_family` is mandatory and is the
durable grouping key — `entry_id` is a hash and cannot be read backwards into a family,
and `capability` is the routing label ADR-009 kept out of the id precisely because it
moves ([ADR-016](decisions/ADR-016-outcome-snapshot-carries-the-signal-family.md)).

**Failure — cache write fails.** The UI rolls back and shows the error; the outcome is
not presented as recorded (SPEC-006 §11). **Failure — Firestore write fails.** The cache
holds it; the existing reconcile pushes it on `online`; the engine sees it on the next
successful pull. Until then the browser's own filter keeps the entry off the surface.

### 9.4 The owner answers a cost question (SPEC-005 SCN-083 … SCN-086)

```
QuestionPanel   ownerState.js   Firestore    (nightly) pull → engine → publish    Browser next morning
 │ answer cost ──►│ write answer {barcode, fact: cost_price, value, at}
 │                │───────────────►│
 │◄── "recorded; takes effect at the next run"                         
                                          │ OwnerState.answers.cost_price[barcode]
                                          │ price_consistency: D-4 artefact test now has a cost
                                          │ competitor_position: product enters the policy comparison
                                          │ owner_questions: question no longer open
                                          │ reconciliation: unchanged (uses no cost, ASM-012)
                                                                                      │ outputs reflect it
```

The answer is authoritative: a later import carrying a different cost for that barcode
does **not** overwrite it (FR-087, INV-042); the engine records `cost_source: owner`.
Deferral writes `{status: deferred, at}` and no value (FR-091). Revision overwrites the
answer with a new `at` (FR-090). "I don't know" (OQ-501) is stored as a deferral with
`reason: unknown` — distinct in data, treated as deferral in V1 behaviour (provisional).

**Failure — Firestore unavailable when the panel opens.** `owner_questions` published
`unavailable` on the last run *only if the pull failed then*; the browser additionally
checks its own write path: if the cache is unavailable (private mode, quota), the panel
is not shown (SPEC-005 §11).

### 9.5 The owner challenges a figure (SPEC-007 SCN-120 … SCN-127)

```
Team laptop:  npm run figures
  scripts/figures.py → run_engine.py --print
    ingestion steps: reuse when content-address(inputs) == recorded, else recompute
    OwnerState.pull (or the committed mirror, flagged as such)
    capabilities → figure registry
    print: figure · unit · input vintage · thresholds in force · printed_at
```

Every figure on the surface is in the registry, so the printed value is the surface's
value on the same data (INV-065). If data has refreshed since the surface was built,
both vintages are printed and the difference is visible (FR-127). If an input is
missing, the figure prints as *unavailable — missing: <input>* and the process exits 1
(FR-126, AC-122).

### 9.6 Withdrawal, revival and the handover list (SPEC-004 SCN-061 … SCN-070)

Normal: every run recomputes classification over the evidence window; withdrawable
entries are published under `catalogue.withdrawn[]` each with `{barcode, window,
evidence: no_row_in_reports | observed_zero, recorded_stock: 0, provisional: true,
statement}`; other capabilities receive the withdrawn set through `EngineInputs` and
exclude it before counting (FR-074).

Revival by sale: the next run finds a row with units > 0 → the entry is living; it
simply is not in `withdrawn[]` (INV-032). Revival by owner: the browser writes
`revivals[barcode] = {at, window_id}`; the engine keeps the entry living while
`window_id` equals the current window's id (FR-067); when the window changes
(a new report arrives), the revival lapses and the rule re-evaluates.

Longer evidence: when `full_annual_cycle` becomes true, `provisional` flips to false
and withdrawals are re-evaluated against the whole window; entries with any sale in any
month return (FR-063c). Whether stock-carrying entries then become withdrawable is
OQ-409 and is **not** implemented: `Policy.withdraw_with_stock = false` is asserted.

Handover: the catalogue page renders `withdrawn[]` as a CSV download (barcode, name,
evidence, window) — a file the owner gives his POS operator (D-7, FR-075).

**Failure — sales evidence absent.** `catalogue_lifecycle` publishes `unavailable:
no_sales_evidence`; `withdrawn[]` is absent (not empty); other capabilities receive
`withdrawn = None` and do not exclude (INV-036). **Failure — a report for a month is
malformed.** The importer rejects the file, the window shrinks, and the window statement
says so.

### 9.7 A new POS export with a moved ceiling (SPEC-001 SCN-009, SPEC-007 SCN-127)

The ceiling is derived per run and published with its derivation. Products whose
classification changed because the ceiling moved are not marked "new": the surface
carries no new/carried-over distinction in V1 (OQ-607), and outcomes are keyed to the
entry id, which does not include the ceiling (C-4, AC-009).

---

## 10. Domain and Data Model

### 10.1 Domain entities (engine vocabulary)

| Entity | Identity | Attributes | Lifecycle |
|---|---|---|---|
| **Product** | `barcode` (leading zeros stripped; absent → not a Product but a *hygiene record*) | name, department, shelf_price, delivery_price (absent when ≤ 0), cost_price (absent when ≤ 0; source: pos | owner), recorded_stock (raw, may be negative or absent) | Rebuilt per run |
| **SalesEvidence** | (barcode, month) | units, receipts, revenue | Append-only as reports arrive |
| **EvidenceWindow** | run | months, first, last, count, `full_annual_cycle` (OQ-408: provisional definition = 12 consecutive months present) | Per run |
| **EvidenceState** (per product) | barcode | `observed_units` (units > 0) · `observed_zero` (a row with 0) · `no_row` (absent from every report in the window) | Per run — the rule-13 distinction |
| **CompetitorObservation** | (barcode, store_id, observed_at) | price, source_type (price_file | delivery), store → **Store** | Per snapshot |
| **Store** | store_id | name, chain, format, affinity to the client format, `role: client | competitor`, provenance (branch_known | chain_format) | Hand-maintained |
| **Match** | (barcode, external_key) | method (barcode_exact | name_normalized | fuzzy_name), confidence, approved | Per run, content-addressed |
| **Classification** | barcode | living | withdrawable | idle; plus excluded reasons (negative_stock, no_identifier); `provisional` | Per run |
| **Entry** | `entry_id = sha256(signal_family ‖ barcode ‖ variant)[:16]`. `signal_family` is a permanent identity string (`recon.impossible_opening`, `hygiene.negative_stock`, `hygiene.no_identifier`, `hygiene.absent_price`, `price.inverted`, `price.above_ceiling`, `competitor.policy_breach`, `competitor.purchase_cost`, `catalogue.idle`, `catalogue.implausible_quantity`, `margin.below_cost`) fixed once and **never** reused or renamed. It is *not* the routing `capability` id — see ADR-009 | capability, signal_family, action, characterisation, evidence{}, value?, ordering_key, actionable, attention | Per run; outcomes reference it across runs |
| **Value** | — | `{amount: number, kind: 'per_sale', certainty: 'confirmed' | 'estimated'}` — the only kind in V1 | — |
| **Question** | `question_id = sha256('cost_price' ‖ barcode)` | product, fact, why (products affected, money at stake), expected value | open → answered | deferred |
| **Figure** | name | value | null, unit, inputs (vintage keys), thresholds | Per run |

### 10.2 Value semantics (the D-1/D-2 model)

```
value_policy per capability (declared in src/engine/registry.py — the registry is the
complete list of capability ids; the artefact's capabilities{} keys are exactly these):
  price_consistency    : per_sale allowed (inverted only)
  reconciliation       : none
  hygiene              : none            (INV-013, INV-054)
  competitor_position  : none            (V1: questions, not amounts)
  catalogue_lifecycle  : none            (unit_cost is evidence, labelled per-unit, never a value)
  owner_questions      : none            (a question carries no value)
  margin_below_cost    : per_sale allowed (not admitted)
publish asserts: no entry of a `none` capability has `value`; every value.kind ∈ declared kinds;
                 meta.value_kinds_present == set of kinds actually present  (FR-105, derived);
                 every registry id appears in capabilities{} with a status  (ARCH-DRIVER-002)
```

`estimated` is reserved for a value resting on an input marked unreliable (FR-130);
no V1 capability produces one, and the label machinery exists so a future one cannot
ship unlabelled (INV-052/INV-063).

### 10.3 Owner state (the only mutable model)

```
OwnerState (Firestore: stores/{storeId}/ownerState/{doc}; mirror: data/owner/owner_state.json)
  answers:   { [barcode]: { cost_price: { value, at, status: answered | deferred, reason?: unknown } } }
  outcomes:  { [entry_id]: { status: acted | declined | deferred, reason?: wrong_data | not_worth_it | already_handled,
                             deferred_until?, at, snapshot: { signal_family, capability, barcode,
                                                              value?, kind?, certainty?, characterisation } } }
  revivals:  { [barcode]: { at, window_id } }
  meta:      { schema: 1, updated_at }
```

Persistence representation: Firestore documents per top-level map (three documents
plus meta) so a single answer does not rewrite outcomes; localStorage holds the same
JSON under `smartshelf.ownerState.v2` (one key; the seven legacy keys are read once and
migrated, §20). Every record carries `at`; reconciliation is last-write-wins per record
(existing adapter semantics). The mirror file is written by the engine only and is
never read by the browser.

### 10.4 Persistence representation vs domain

| Domain | Storage | Notes |
|---|---|---|
| Product, Evidence, Observations, Matches | parquet under `data/` (gitignored, regenerated) | Silver is derived; only sources are committed |
| Sources | CSVs + snapshots, committed | Vintage = file date / snapshot day |
| Artefact | `public/data/dashboard.json`, committed by CI | Schema v2, `schemas/dashboard.schema.json` |
| Owner state | Firestore + localStorage cache + committed mirror | §10.3 |
| Policy constants | `configs/policy.yaml` (`price_policy_pct: 60`, `attention_pct: 100`, `cost_floor_pct: 10`, `freshness_days: 14`, `artefact_min_price: 0.5`, `artefact_cost_ratio: 2`, `surface: {bound: 10, unvalued_places: 3}`, `question_limit: 3`, `ceiling_derivation: {band_pct: 2, drop_ratio: 0.75, min_band_count: 20}`) | Declared, versioned, published in `meta.thresholds` |

### 10.5 Important constraints and state transitions

- Classification partitions the classified population exactly (INV-034): a product
  without a usable identifier or with negative stock is *excluded before* classification
  and counted separately (FR-062, AC-070).
- Withdrawal transitions are exactly those of SPEC-004 §10; the engine has no code path
  for `in catalogue → withdrawn` by owner action (OQ-403) or for stock-carrying
  withdrawal (OQ-409); both are asserted absent by tests.
- Question transitions are those of SPEC-005 §10; `answered → open` happens only through
  revision (owner) — the engine cannot reopen an answered question.
- Outcome transitions are those of SPEC-006 §10; a deferral lapses at `deferred_until`
  (OQ-604 — provisional: the three existing durations); a decline stands for the entry id
  (OQ-605 — provisional: a changed value does not reopen).

---
## 11. Interfaces and Contracts

### 11.1 `EngineInputs` (ingestion → engine, Python dataclass)

| Field | Type | Absent means |
|---|---|---|
| `products`, `inventory`, `margins` | frames or `None` | POS import missing → every capability unavailable |
| `sales_monthly`, `sales_summary`, `window: EvidenceWindow` | frames or `None`; `sales_summary` rows carry `reconcile_units`, `reconcile_receipts` and `reconcile_months` (distinct months), cut here from `sales_monthly` at the month of the run's usable stock date, and null when there is none (ADR-026) | reconciliation, lifecycle, questions unavailable |
| `observations`, `matches`, `stores` | frames or `None` | competitor_position unavailable |
| `withdrawn: set[barcode] | None` | from lifecycle, fed to the others in the same run | `None` → no exclusion (INV-036) |
| `vintages` | `{pos: {file, as_of}, sales: {months, first, last, full_annual_cycle, imported_this_run (ADR-017), reconcile_before (the month this run's reconcile figures were cut at — ADR-026)}, competitor: {snapshot_date, sources: [...]}, owner_state: {pulled_at | null, status}}` | required |
| `owner: OwnerState` | §10.3 | `status: unavailable` |
| `policy: Policy` | `configs/policy.yaml` | required |

Ownership: `src/engine/inputs.py`. Compatibility: additive fields only; a capability
must not read a field it did not declare in the registry.

### 11.2 `CapabilityOutput` (engine → publisher)

```
CapabilityOutput
  id: str                          # 'price_consistency' | 'reconciliation' | 'hygiene' | … — a registry id
  spec: str                        # 'SPEC-001' — many-to-one: SPEC-002 yields 'reconciliation' and 'hygiene'
  requires: list[str]              # EngineInputs keys this capability cannot compute without,
                                   #   e.g. reconciliation: ['products','inventory','sales_summary']
                                   #        hygiene:        ['products','inventory']
  status: 'available' | 'unavailable'   # DERIVED, never hand-declared: unavailable iff any `requires` key is None
  unavailable_reason?: str         # names the missing input(s) or the rule-level reason
                                   #   'no_delivery_prices' | 'no_sales_evidence' | 'no_comparable_source'
                                   #   | 'observations_stale' | 'answer_storage_unavailable' | 'ceiling_degenerate' | …
  window?: EvidenceWindow          # lifecycle: the sales span · reconciliation: the span it reconciled (ADR-026)
  thresholds: dict                 # every value a count depends on (FR-005, FR-046, FR-061)
  counts: dict[str, int | None]    # None = unstatable, never 0-for-missing
  entries: list[Entry]             # full set (FR-102); ordered by ordering_key
  figures: list[Figure]            # registered for reproduction
  notes: list[str]                 # statements that must accompany the output (FR-063a, FR-076 …)
```

Failure semantics: a capability that cannot compute returns `status: unavailable` with
a reason; it never raises for a missing input (raising is reserved for bugs, which the
orchestrator records as `error`). Because `status` is computed from `requires` against
the inputs that actually landed, a capability cannot be *declared* available over a
missing input, and the SPEC-002 §11 case — receipts absent, so `reconciliation` is
unavailable while `hygiene` continues — falls out of the two `requires` lists rather than
being written by hand. Ownership: each capability module.

### 11.3 `Entry` (the unit the surface and the outcome store agree on)

```
Entry
  id: str                          # sha256(signal_family ‖ barcode ‖ variant)[:16] — stable across runs,
                                   #   thresholds AND any future re-carving of capabilities (ADR-009)
  signal_family: str               # permanent identity, never renamed or reused (§10.1)
  capability: str                  # routing/presentation id; may change without touching `id`
  barcode: str | null              # null only for hygiene 'no_identifier'
  product_name, department
  action: 'verify_price' | 'count_product' | 'fix_record' | 'decide_idle' | 'review_policy' | 'check_purchase_cost'
  characterisation: str            # spec-defined: 'confirmed_loss' | 'question' | 'inconsistent' | 'hygiene' | 'policy_breach_attention' | 'policy_breach_review' | 'purchase_cost' | 'idle'
  evidence: dict                   # capability-specific, every number labelled; sufficient for FR-009/FR-027/NFR-020/NFR-033
  value: Value | null
  ordering_key: {name: str, value: number | null}
  actionable: bool                 # FR-103 (1),(2),(4) — the browser applies (3)
  not_actionable_reason?: str
  attention: 'today' | 'review'    # competitor_position only; others 'today'
```

### 11.4 Artefact: `public/data/dashboard.json` (schema v2)

```
{ schema_version: 2, generated_at, run_id,
  run: { status: ok|partial|degraded, steps: [{step, status, ms, error?}] },
  vintages: {…as 11.1…},
  thresholds: { price_consistency: {ceiling_pct|null, method, bands}, competitor_position: {policy_pct, attention_pct, cost_floor_pct, format_allowance_pct|null, format_allowance_basis_count, freshness_days}, surface: {bound, unvalued_places}, artefact: {min_price, cost_ratio}, question_limit },
  value_kinds_present: ['per_sale'],
  capabilities: {                     // exactly the registry ids; every one carries a status
    price_consistency:   CapabilityOutput minus figures,
    reconciliation:      CapabilityOutput minus figures,
    hygiene:             CapabilityOutput minus figures,
    competitor_position: CapabilityOutput minus figures,
    margin_below_cost:   CapabilityOutput minus figures,
    catalogue_lifecycle: CapabilityOutput minus figures
                         + { provisional, withdrawn: [...], statement },   // capability-specific extras
    owner_questions:     CapabilityOutput minus figures
                         + { limit, items: [...], suppressed: {withdrawn, idle, no_effect} }
  },
  figures: { [name]: {value, unit, inputs, thresholds} } }
```

Validated by `schemas/dashboard.schema.json` on write (Python `jsonschema`) and on read
(a small JS validator generated from the same file at build time). Compatibility: the
browser refuses an artefact whose `schema_version` it does not know and shows
*unavailable*. Ownership: publisher writes, `loadDashboard.js` reads; the schema file is
owned jointly and changed only with both sides in the same commit.

### 11.5 Owner-state contract (browser ↔ Firestore ↔ engine)

Documents under `stores/{VITE_STORE_ID}/ownerState/{answers|outcomes|revivals|meta}`;
each map keyed as in §10.3; every record has `at` (ms epoch) and the document has
`updated_at`. Writer: browser only. Reader: browser (reconcile), engine (pull, service
account). Failure: unreachable → cache-first browser; engine `status: unavailable`.
Compatibility: `meta.schema` bumps require a browser migration; the engine rejects an
unknown schema with `unavailable: owner_state_schema`.

### 11.6 Reproduction CLI

`python3 scripts/figures.py [--json]` — no arguments required (NFR-062). Exit 0 with all
figures; exit 1 naming the missing input when any registered figure is unavailable. Time
budget: two minutes on the pilot data (NFR-060), measured at the Phase 3 checkpoint.

### 11.7 External integration contracts (unchanged, reused)

| Integration | Contract | Failure |
|---|---|---|
| Dor Alon price transparency (FTPS) | daily `*pricef*`/`*promof*`/`*store*` files; one day kept server-side | day lost → manifest `partial`; watchdog |
| Wolt venue pages | `query-state` JSON; prices in minor units | venue 503 → other venues continue; 0 products = error |
| Firestore | rules pinned to one store path; anonymous auth for the browser; service account for CI | see 9.1 / 9.3 |
| Vercel | static build; Basic Auth middleware; `/data/*` `no-store` | 503 if credentials unset (fail closed) |

---

## 12. State Ownership

| State | Owner | Mutated by | Read by | Authoritative copy | Consistency | After interruption |
|---|---|---|---|---|---|---|
| POS inventory source | The owner's POS (external) | new CSV committed by the team | ingestion | the committed CSV | vintage recorded | last committed file stands |
| Sales reports | External | new CSV committed | ingestion | committed CSVs | window derived from filenames | — |
| Competitor snapshots | CI collector | append-only, sealed per day | rehydrate | git | manifest per day; merge-never-replace | a partial day is sealed as `partial` |
| Silver tables, signals, matches | Ingestion | regenerated per run | engine | none (derived) | content-addressed by input vintages | regenerated |
| **Owner state** | **Owner (via browser)** | browser only | browser, engine | Firestore; localStorage is a cache; the committed mirror is a *read replica* for reproduction | LWW per record by `at`/`updatedAt` | cache replays on `online`; engine uses last successful pull and says so |
| Artefact | Publisher | one atomic write per run | browser, figures (cross-check only) | git | immutable per run | previous artefact stays |
| Policy constants | Team | commits to `configs/policy.yaml` | engine | git | published in `meta.thresholds` | — |
| Surface composition | Browser (ephemeral) | recomputed on every render | — | none | pure function | — |
| UI language | Browser | owner | i18n | localStorage | — | default `ar` |
| Receiving/expiry queue (V2 data) | Browser | staff | manual CSV export | localStorage | — | out of V1 scope |

Nothing else is mutable. In particular the engine owns **no** persistent state of its
own: withdrawal (SPEC-004 §10's one lifecycle state) is recomputed from evidence plus
owner revivals every run (ADR-004).

---

## 13. Failure and Recovery

| Condition | Where detected | Behaviour | Owner of recovery | User-visible |
|---|---|---|---|---|
| POS CSV header drift | POS importer (mapping YAML) | Import fails; run `partial`; capabilities depending on POS `unavailable`; publisher refuses if every capability is unavailable | Team edits the mapping | Data page: last good vintage; surface: unavailable capabilities |
| Sales report malformed / missing month | Sales importer | File rejected; window shrinks; statements updated | Team | Window statement on every count |
| Delivery prices absent for the whole catalogue | price_consistency | `unavailable: no_delivery_prices` | — | Capability badge |
| Ceiling underivable | price_consistency | `ceiling: null`; above-ceiling entries suppressed and count `None`; inverted entries continue (FR-006) | — | "ceiling undetermined" stated with the count |
| Receipts or sales absent | `requires` check in `inputs.py` | `reconciliation` computes `unavailable: no_sales_evidence` (its `requires` names `sales_summary`); `hygiene` stays `available` and publishes its full set (its `requires` names only `products`, `inventory`) — SPEC-002 §11 | — | Two badges, two independent states |
| No comparable-format source; all observations stale; format allowance unmeasurable | competitor_position | `unavailable` with reason; or per-product "no comparison" (FR-044c) | Collector watchdog | Badge / "no comparison" |
| Collector failed for a day | CI manifest + watchdog | snapshot `partial`; next day recovers; freshness bound protects the capability | Team reruns | Data page shows snapshot age |
| Sales evidence absent | catalogue_lifecycle | `unavailable`; nothing withdrawn; no exclusion applied (INV-036) | — | Badge |
| Owner state unreachable at run | pull | `owner_state: unavailable`; answers absent (D-3); questions `unavailable`; run `degraded`, published | Team checks the secret / Firebase | Question panel absent; data page states it |
| Firestore unreachable in the browser | adapter | cache-first; write-through retried on `online` | — | Outcome recorded (cache); a subtle "will sync" note |
| localStorage unavailable (private mode, quota) | ownerState | Outcomes cannot be recorded → controls disabled with explanation; questions not shown | — | Explicit |
| Artefact fetch fails / schema mismatch | loadDashboard | `unavailable`; never "nothing to do" | Team | Explicit |
| Every capability unavailable | publisher | Refuse to write; CI red; previous artefact stands | Team | Yesterday's surface with its vintage. SPEC-006 §11 has two rows for this; the *stale input* row governs, because the browser never receives an all-unavailable artefact — the age of the data is shown and the entries remain valid as of it |
| Engine step raises | orchestrator | Recorded; dependents `unavailable`; run `partial` | Team | Data page run status |
| Interrupted publish | filesystem rename | Torn file impossible | — | — |
| Reproduction input missing | figures | Exit 1 naming the input; no remembered value | Team | — |

Retries: only the Firestore write-through (existing adapter, on `online`) and the CI
`git pull --rebase` before push. No other retries — every other failure is either
permanent for the day or a bug, and both must be visible rather than smoothed over.

---

## 14. Reliability and Invariant Enforcement

Each MUST NEVER has a mechanism that makes the violation structurally impossible or a
test that fails the build. "Type" = enforced by data shape; "Assert" = publisher or
engine assertion; "Test" = AC-named test; "UI" = the browser has no code path.

| Invariant | Mechanism |
|---|---|
| D-1 / INV-010, INV-011, INV-013, INV-054, FR-069a — no money on stock-derived signals | Type + Assert: `value_policy: none` in the registry; publisher rejects any `value` on those capabilities; the browser has no money arithmetic (Test AC-021, AC-025, AC-071a) |
| D-2 / INV-014, INV-051, FR-105, FR-116 — never sum recurring with standing | Type: `Value.kind`; `compose` orders within kind and never adds; no total is rendered; Assert: `value_kinds_present` derived and, in V1, asserted to be `{'per_sale'}` or empty (Test AC-103) |
| D-3 / INV-057, INV-061, FR-128, FR-129 — absence ≠ zero | Type: `status`, `counts: int | None`, `ceiling: null`; UI renders `None` as "no figure"; publisher refuses missing status (Test AC-005, AC-107, AC-123) |
| SPEC-002 §11, INV-057 — a signal family with its own inputs fails on its own | Type: availability is per capability, and a capability is *defined* as the smallest independently-unavailable unit (ADR-014); `status` is computed from `requires`, so it cannot be declared over a missing input. Boundary test: a run with the sales reports removed must publish `reconciliation: unavailable` **and** `hygiene: available` with a non-zero count (Test AC-107 + the rule-12 probe below) |
| D-5 / INV-024 — own price never a benchmark | Type: `Store.role = client` excluded from reference candidates before any computation (Test AC-047b) |
| D-7 / INV-033, FR-068 — never write to the POS | No code path exists; the only outputs are files under this repo and Firestore (Test AC-064 asserts no network write in the engine) |
| D-8 / INV-040 — ≤3 questions | `questions.limit` published; `QuestionPanel` slices; Test AC-080 |
| D-9 / INV-050 — ≤10 entries | `compose` truncates; Test AC-100 (property test over random candidate sets) |
| INV-001 — loss only when inverted | `characterisation: confirmed_loss` assigned only in the inverted branch; Test AC-003 |
| INV-003 / NFR-003 — surfaced < price-paired; ≤10 % | Assert at publish: if surfaced ≥ paired or > 10 %, the capability publishes `unavailable: ceiling_degenerate` (Test AC-008) |
| INV-005 / INV-055 — no velocity claim | Type: no entry field for units/day exists; `evidence` keys are enumerated per capability in the schema (Test AC-007, AC-111) |
| INV-015 — no cause asserted | Characterisation and i18n strings only; Test AC-027 greps the dictionaries for cause words on reconciliation keys |
| INV-020 — no excluded source | Type: affinity-0 stores dropped in `inputs.py` before the capability sees observations; Test AC-040 (the existing acceptance check, retargeted to the engine) |
| INV-025 / C-24 — never recommend below cost + floor | Cost floor evaluated first in `competitor_position`; the module has no branch that emits a price recommendation at all in V1 (it emits questions); Test AC-049 |
| INV-026 — reference never a single competitor price when balanced is obtainable | Reference builder returns `{kind: midpoint | supermarket_plus_allowance | none}`; Test AC-052/053 |
| INV-030, INV-031, INV-031a, INV-032, INV-034, INV-036 | Withdrawal is a pure function with `withdraw_with_stock = false` asserted; `provisional` derived from the window; revival by any sale is the absence of a withdrawal; partition asserted per run (Tests AC-060 … AC-066, AC-070) |
| INV-041, INV-044 — no question about withdrawn products / with no effect | Suppression runs over `withdrawn` and `idle` before ranking; yield 0 → suppressed (Test AC-081, AC-088) |
| INV-042 — answers never overwritten | Engine never writes owner state (no write client in `src/engine/`); `cost_source: owner` precedence (Test AC-085) |
| INV-053 — outcomes never lost | Write-through with rollback; Firestore mirror; Test AC-105 |
| INV-056 — one product one place | `compose` dedupe; Test AC-109 |
| INV-060, INV-062, INV-065 — vintage always; reproduction = surface | `figures{}` is the same registry the artefact publishes; `figures.py` runs the same modules (Test AC-127: artefact figures == print-mode figures on the same inputs) |
| INV-063 / INV-052 — estimates labelled | `Value.certainty` is required; UI renders the label from it (Test AC-104, AC-124) |
| C-32 — withdrawal reads raw stock | `inventory.current_stock` is never clamped anywhere in the engine (Test AC-070) |
| C-53 — three languages, no split numbers, no overflow | Existing key-parity test + e2e invariants, extended to the new pages (Test AC-112) |
| Rule 12 — a signal must move something | `check:signals` retargeted: owner cost answer moves questions/competitor entries; a withdrawal moves other capabilities' counts; the cost floor removes ≥1 breach on pilot data; a ceiling change moves the above-ceiling count; **and the independence probe — run with `sales_monthly` withheld and assert `reconciliation.status == 'unavailable'` while `hygiene.status == 'available'` and `hygiene.counts` total > 0.** A unit test cannot catch this: it supplies each capability's inputs directly and never crosses the boundary where the coupling lives |

---
## 15. Security and Privacy

Derived from D-12 (single store, single user) and from what the data actually is: one
business's cost prices, margins, stock and the owner's decisions.

| Concern | Design |
|---|---|
| **Trust boundary 1 — the site** | Vercel Edge Basic Auth on every path (existing `middleware.ts`, fail-closed). One shared credential for the pilot. `X-Robots-Tag: noindex`. Unchanged |
| **Trust boundary 2 — owner state** | Firestore rules pinned to `/stores/yomyom-kafr-qasim/**`, anonymous sign-in. **Accepted pilot posture**, recorded in `firestore.rules` itself: anyone who loads the app can mint a token and read/write that subtree. Mitigation before wider exposure (not V1): App Check. The design adds nothing here because D-12 forbids accounts |
| **Trust boundary 3 — CI** | FTPS credentials (public read-only account), Firebase service account JSON (`FIREBASE_SERVICE_ACCOUNT_JSON`) as GitHub secrets; the engine's pull is read-only and the service account should be granted read-only on Firestore |
| **Sensitive data paths** | `dashboard.json` carries cost prices and margins (as `operational.json` does today) — behind Basic Auth, `no-store`. The inventory CSV and sales reports are committed to a private repository. No new exposure class is introduced; the mirror `data/owner/owner_state.json` adds the owner's outcomes and answers to the repo, which already holds his cost column |
| **Secrets in the bundle** | The Gemini key path is removed with the LLM layer. `VITE_*` remains the only browser-visible namespace; `check_firebase_config.mjs` is kept as a pre-deploy guard |
| **Validation boundaries** | Owner-state records are validated on write (closed enums, numeric cost > 0) and on pull (schema); the artefact is validated on both sides; CSV imports are validated by the mapping YAML. Comment/answer text is never rendered as HTML |
| **Removed attack surface** | No runtime server (LLM proxy, MCP server gone); no browser file upload; no second Firestore schema |

---

## 16. Performance and Resource Model

| Path | Budget | Expected | Mechanism |
|---|---|---|---|
| Nightly run (CI) | ≤ 30 min job timeout (existing) | collection dominates; engine seconds | Incremental signal loading kept; matching bounded by rapidfuzz blocking; owner-state pull is one document tree |
| **Reproduction** (`figures`) | **≤ 2 min** (NFR-060) on the pilot data | engine < 10 s once silver is current; first run on a fresh clone pays rehydrate + signals + matching once | Intermediate outputs are **content-addressed**: `signals`, `matches` and the silver tables record `sha256(input vintages ‖ policy version)`; a step is skipped only when the address matches, so reuse is provably identical to recomputation (FR-125 is honoured because nothing *remembered* is ever substituted for a computation — only a computation over the same inputs) |
| Artefact size | ≤ 3 MB (today 2.88 MB) | ~1.5–2.5 MB: ~7k entries with compact evidence; withdrawn list ~4k small records | Gzip on Vercel; no product names duplicated across entries beyond one field |
| Browser | first paint < 1 s on a phone after fetch; compose O(n log n) over ≤ 10k entries | trivial | The 4.36 MB demo bundle disappears with the demo spine; expected main chunk < 400 KB |
| Firestore | a few dozen writes per day; one read-tree per run | negligible cost | — |
| Memory (CI runner) | the signal build was SIGTERM'd once at 31 days of concatenation | bounded | Keep the fold-and-dedupe loop; do not load all snapshots at once |

No caching layer beyond content addressing; no concurrency beyond the existing
per-venue collector isolation.

---

## 17. Observability

Enough to answer *what ran, on what data, what each capability decided, and why the
owner saw what he saw* — without a metrics stack.

| Signal | Where | Content |
|---|---|---|
| **Run manifest** | `run` block inside `dashboard.json` + `data/runs/<run_id>.json` (gitignored) | step list with status, duration, error text; input vintages; per-capability status and counts; `check:signals` result |
| **Figure registry** | `figures{}` in the artefact | every stated number with inputs and thresholds — the reproduction and the surface read the same block |
| **Snapshot manifests** | existing `_manifest.json` per day | unchanged |
| **CI** | job red on `partial`/`degraded`/refused publish/inert signal/unhealthy collection | existing pattern, extended to the engine |
| **Browser** | Data page: artefact vintage, run status, capability statuses, owner-state sync state; console must stay error-free (e2e asserts it) | — |
| **Owner outcomes** | owner state (dismissal reasons `wrong_data` etc.) — the pilot's own diagnostic | read by the team via the committed mirror |

No tracing, no external metrics: a two-person team reads a JSON block and a red job.

---

## 18. Testability

| Level | What | How the architecture enables it |
|---|---|---|
| **Unit (Python)** | Every capability rule against small frames; ceiling derivation reproduces 18 % on the pilot distribution; cost floor removes the three intent examples; classification partition; question suppression arithmetic (1,270 → 12) | Capabilities are pure functions of `EngineInputs` — no files, no clock (run time is an input) |
| **Acceptance tests as tests** | One test per AC-xxx in `tests/acceptance/test_spec_00N.py` and `src/**/__tests__/ac-*.test.js`, named by the criterion | The traceability matrix (§21) doubles as the test index; a missing AC test is a review finding |
| **Contract** | `schemas/dashboard.schema.json`: Python publishes a fixture artefact from a fixture silver set; JS loads it; both validate; `compose` snapshot over the fixture | One schema file, two validators, one fixture in `fixtures/pilot-mini/` (200 products, 3 months, 2 stores) |
| **Boundary-crossing (rule 12)** | `check:signals` V1 probes: owner cost answer → competitor/question outputs move; withdrawn set → other counts move; cost floor on → breach count drops; ceiling moved → above-ceiling count moves; **sales evidence withheld → `reconciliation` unavailable while `hygiene` still emits** (the ADR-014 independence probe); each with a synthetic probe when the real input is absent | Runs against the real artefact in CI before commit |
| **Integration** | `scripts/run_engine.py --print` over the committed pilot data on a fresh clone: exits 0, ≤ 2 min, figures equal the artefact's `figures{}` (INV-065) | Reproduction is the integration test |
| **End-to-end** | Existing Playwright invariants (three languages, no split numbers, no overflow, no raw keys) over the new pages; new journeys: surface ≤ 10 and no remainder text; outcome survives reload; unavailable capability rendered as such; question limit | Real browser, real dev server, fixture artefact served from `public/data/` |
| **Determinism** | Same inputs + policy → byte-identical artefact except `generated_at`/`run_id` (NFR-002/011/021/032/041/053/061) | No randomness; sorted iteration; content addresses |
| **CI** | New `ci.yml` on push/PR: lint · vitest · pytest · contract · build. Nightly keeps `check:signals` | Today nothing runs before a merge |

---
## 19. Architecture Decisions

The architecture decision records live one per file under [`decisions/`](decisions/).
The first fourteen were extracted from this section by the 2026-09-08 documentation
migration; their content is unchanged, and every `ADR-0NN` reference elsewhere in this
document resolves to the file below. ADR-021 … ADR-025 state no reversibility of their
own, so their rows say so rather than grade it after the fact.

| ADR | Decision | Reversibility |
|---|---|---|
| [ADR-001](decisions/ADR-001-one-rule-engine-in-python.md) | One rule engine, in Python; the browser computes no business rule | Difficult |
| [ADR-002](decisions/ADR-002-reproduction-is-the-engine-in-print-mode.md) | Reproduction is the engine in print mode | Easy |
| [ADR-003](decisions/ADR-003-owner-state-in-firestore-browser-written.md) | Owner state lives in Firestore, written only by the browser, pulled by the engine | Moderate |
| [ADR-004](decisions/ADR-004-catalogue-lifecycle-recomputed-every-run.md) | Catalogue lifecycle is recomputed every run; the engine owns no persistent state | Easy |
| [ADR-005](decisions/ADR-005-typed-capability-contract-and-one-artefact.md) | A typed capability contract and one schema-validated artefact | Moderate |
| [ADR-006](decisions/ADR-006-surface-composition-is-a-pure-browser-function.md) | Surface composition is a pure browser function over engine candidates | Easy |
| [ADR-007](decisions/ADR-007-static-site-nightly-ci-no-runtime-server.md) | Static site, nightly CI, no runtime server; V2/V4 and AI code leave the V1 build | Easy |
| [ADR-008](decisions/ADR-008-store-format-affinity-enforced-in-the-engine.md) | Store-format affinity is enforced in the engine, under the balanced reference | Easy |
| [ADR-009](decisions/ADR-009-stable-entry-identity-via-signal-family.md) | Entry identity is stable and legacy outcome ids are translated once | Easy |
| [ADR-010](decisions/ADR-010-demo-catalogue-and-normalize-data-leave-the-product.md) | The generated demo catalogue and `normalize:data` leave the product | Easy |
| [ADR-011](decisions/ADR-011-evidence-semantics-no-row-is-recorded.md) | Evidence semantics: `no_row` is recorded, and classification states it | Easy |
| [ADR-012](decisions/ADR-012-money-is-a-typed-value-with-a-declared-policy.md) | Money is a typed value with a declared per-capability policy | Easy |
| [ADR-014](decisions/ADR-014-a-capability-is-the-smallest-independently-unavailable-unit.md) | A capability is the smallest independently-unavailable unit; data hygiene is one | Easy |
| [ADR-015](decisions/ADR-015-ceiling-is-the-densest-qualifying-collapse.md) | The markup ceiling is the densest qualifying collapse, not the last; ties take the higher edge | Easy |
| [ADR-016](decisions/ADR-016-outcome-snapshot-carries-the-signal-family.md) | The owner-outcome snapshot carries signal_family, the only durable grouping key for INT-MEAS | Easy |
| [ADR-017](decisions/ADR-017-a-run-states-whether-its-sales-evidence-arrived.md) | A run that continued on older sales evidence is never ok; vintages.sales states whether the reports arrived | Easy |
| [ADR-018](decisions/ADR-018-the-browser-does-not-ship-a-schema-validator.md) | The browser checks four preconditions it cannot render without; the schema is enforced at publish and in CI | Easy |
| [ADR-019](decisions/ADR-019-a-conflicting-duplicate-barcode-is-a-hygiene-record.md) | A duplicate barcode whose rows disagree is excluded and reported as hygiene; no field is picked | Easy |
| [ADR-020](decisions/ADR-020-the-published-population-is-a-policy-not-a-constant.md) | The published population is a policy setting; the artefact states it, so D-14 no longer blocks the cut-over | Easy |
| [ADR-013](decisions/ADR-013-tests-run-before-merge.md) | Tests run before merge | Easy |
| [ADR-021](decisions/ADR-021-the-artefact-states-how-many-devices-wrote-owner-state.md) | The artefact states how many devices have written owner state, and when | Not stated |
| [ADR-022](decisions/ADR-022-a-barcode-less-row-is-identified-by-its-name.md) | A barcode-less row is identified by its name, under ADR-019's rule | Not stated |
| [ADR-023](decisions/ADR-023-the-engine-publishes-the-pilot-measurement.md) | The engine publishes the pilot measurement; the browser renders it — **`Ready for review`** | Not stated |
| [ADR-024](decisions/ADR-024-the-catalogue-is-published-beside-the-artefact.md) | The product catalogue is published beside the artefact, not inside it | Not stated |
| [ADR-025](decisions/ADR-025-the-comparison-behind-the-finding-is-published.md) | The comparison behind a competitor finding is published, not only the finding | Not stated |
| [ADR-026](decisions/ADR-026-reconciliation-publishes-the-span-it-reconciled.md) | The reconcile window is cut once per run, at the run's own stock date, and reconciliation publishes that cut | Easy |
| [ADR-027](decisions/ADR-027-a-question-whose-money-is-unknown-carries-no-figure.md) | A question whose money is unknown carries no figure, and ranks after every question that has one | Easy |
| [ADR-028](decisions/ADR-028-the-nav-is-the-owners-and-only-unshipped-code-leaves.md) | The nav is the owner's, and §20.1 removes only the code no screen runs | Easy |

---

## 20. Current → Target Migration Strategy

### 20.1 Current → target mapping

| Current component | Status (§4) | Target component | Action |
|---|---|---|---|
| `src/external/*` collectors, `scripts/collect_daily.sh`, `seal_snapshot.py`, `write_snapshot_manifest.py`, `check_collection_health.py`, `rehydrate_silver.py` | VERIFIED_WORKING | same | **REUSE** (delete the dead portal branch in `alonit_connector.py`) |
| `src/internal_pos/pos_importer.py`, `pos_normalizer.py`, `configs/pos_schema_mapping.yaml` | LIKELY_WORKING | same + `--as-of`; sales table removed from its outputs | **REUSE** (fix YAML comment on clamping; add tests) |
| `scripts/import_yomyom_sales.py` | BROKEN for V1 | `src/internal_pos/sales_importer.py` → `sales_monthly` + `sales_summary` + `EvidenceWindow` | **REFACTOR** |
| `src/signals/competitor_product_signals.py` | LIKELY_WORKING | same | **REUSE** (barcode zero-strip; tests) |
| `src/matching/product_matching.py` | LIKELY_WORKING | same, per-store rows preserved | **REUSE** (zero-strip; drop global dedupe; tests) |
| `src/common/store_types.py`, `configs/store_types.yaml` | VERIFIED_WORKING | same + `role: client`, Einat venue classified | **REUSE** |
| `src/common/paths.py`, `source_status.py`, `parquet_writer.py`, `raw_storage.py`, `quality.py` | LIKELY_WORKING | `paths.py` reused; `source_status.py` replaced by `vintages` | **REUSE / REMOVE** |
| `src/recommendations/operational_recommendations.py` | LIKELY_WORKING, spec-divergent | `src/engine/reconciliation.py` (arithmetic + hygiene, verbatim logic), `src/engine/margin_below_cost.py` (browse-only) | **REFACTOR** |
| — Wolt gap rule inside it | spec-divergent | `src/engine/price_consistency.py` | **REPLACE** |
| `src/recommendations/product_recommendations.py` | UNVERIFIED, V2 output | `src/engine/competitor_position.py` (new); `WATCH_PRODUCT` leaves V1 | **REPLACE** |
| — (none) | — | `src/engine/catalogue_lifecycle.py`, `src/engine/owner_questions.py`, `src/engine/surface_candidates.py`, `src/engine/provenance.py`, `src/engine/registry.py`, `src/engine/inputs.py` | **NEW** |
| `scripts/export_dashboard_data.py` | VERIFIED_WORKING | `src/engine/publish.py` + `schemas/dashboard.schema.json` | **REFACTOR** |
| `scripts/refresh_pipeline.py` | BROKEN (ordering) | `scripts/run_engine.py` (`npm run data:refresh`) | **REFACTOR** |
| `scripts/print_figures.py` | BROKEN vs specs | `scripts/figures.py` (`npm run figures`) = engine `--print` | **REPLACE** |
| `src/context/owner_answers.py`, `configs/owner_answers.yaml` | live but empty | `src/owner_state/{pull,model}.py`, `data/owner/owner_state.json` (CI-committed) | **REPLACE** |
| `src/context/{build,weather,hebrew,islamic,demand_signals,competitor_stockouts,shelf_life}.py`, `public/data/market-context.json` | LIKELY_WORKING, inert | unchanged, produced nightly for V2; not read by V1 | **REUSE (off V1 path)** |
| `src/expiry/`, `src/internal/receiving.py`, `restock_reconcile.py`, `src/snapshots/*`, `src/market/*` | LIKELY_WORKING, no data / off-path | unchanged; V2 inputs | **REUSE (off V1 path)** |
| `scripts/check_signals_live.mjs` | VERIFIED_WORKING | retired 2026-09-24 (#77): the V1 probes are `check_v1_signals.py` and `check_independence.py`, blocking in the nightly | **REMOVE**, done (ADR-028) |
| `src/lib/persistence/*` (adapters, reconcile) | LIKELY_WORKING | `src/owner/persistence/*` | **REUSE** |
| `src/lib/operational/completionActions.js` | VERIFIED_WORKING | `src/owner/outcomes.js` (enums mapped: DONE→acted, DISMISSED→declined, SNOOZED→deferred) | **REUSE** (rename, id migration) |
| `src/lib/questions/answerStore.js` (shape), `QuestionPanel.jsx` | VERIFIED_WORKING | `src/owner/answers.js`, `src/questions/QuestionPanel.jsx` over artefact questions, at the top of Today (the owner, 2026-09-23, #158) | **REFACTOR**, done. The pre-V1 `components/questions/QuestionPanel.jsx` and `answerStore.js` were removed on 2026-09-24 (#176, [ADR-028](decisions/ADR-028-the-nav-is-the-owners-and-only-unshipped-code-leaves.md)) |
| `src/lib/questions/openQuestions.js`, `proposeGroup.js` | wrong questions for V1 | engine `owner_questions.py` | **REPLACE**, done; the files were removed on 2026-09-24 (#176, ADR-028) |
| `src/lib/analytics/actionPriority.js`, `credibility.js` | BROKEN vs D-1 | `src/surface/compose.js` (selection only); D-4 constants → `configs/policy.yaml` | **REPLACE** |
| `src/pages/OperationalPage.jsx`, `components/operational/ActionCard.jsx` | spec-divergent | `src/surface/DailyPage.jsx`, `EntryCard.jsx` | **REPLACE**, done 2026-09-23 (#152); the two files were removed on 2026-09-24 (#174, #176, ADR-028) |
| `src/lib/dataAdapters/loadOperationalData.js` | LIKELY_WORKING | `src/lib/dataAdapters/loadDashboard.js` (schema-validated, honest status) | **REPLACE** |
| `src/pages/ExpiryPage.jsx` (+ receiving capture) | LIKELY_WORKING | `src/pages/ReceivingPage.jsx` — capture only, on the Expiry entry below its waiting note (the owner, 2026-09-24, #170); expiry summary removed until V2 | **REFACTOR**, done; `ExpiryPage.jsx` was removed on 2026-09-24 (#174, ADR-028) |
| `src/pages/DataSourcePage.jsx` | demo/upload | `src/pages/DataPage.jsx` — vintages, statuses, run | **REPLACE**, done (the Data entry renders `DataPage`); `DataSourcePage.jsx` was removed on 2026-09-24 (#174, ADR-028) |
| `src/lib/i18n/*`, `I18nProvider`, `rtl.js`, `format.js` | VERIFIED_WORKING | same | **REUSE** |
| `src/components/layout/AppShell.jsx`, shared components | VERIFIED_WORKING | same. **The nav is the owner's** ([ADR-028](decisions/ADR-028-the-nav-is-the-owners-and-only-unshipped-code-leaves.md)): Today (cost questions above the actions) · Reorder · Approved orders · Prices · Assortment gaps · Store layout · Shelf plan · Products · Expiry (receiving capture) · Overview · Report · the six findings pages behind one heading · Data. An entry with nothing honest to show renders `PageAwaitingData` | **REUSE** |
| `src/App.jsx` | two spines | one spine: artefact + owner state | **REPLACE** |
| `src/data/*.js`, `scripts/normalize-datasets.mjs`, `loadDemoStoreData`, `posConnectors/*`, `scripts/build-rag-corpus.mjs`, `scripts/audit-store-format.mjs` | obsolete under target | — | **REMOVE**, done: `audit-store-format.mjs` on 2026-09-15 (`6567976`), the rest on 2026-09-24 (#180) |
| `src/lib/analytics/{reorderEngine,demandEngine,competitorEngine,storeFormat,reorderFacts,affinityEngine,affinityRules,planogramEngine,complianceEngine,mockAI,recommendationTypes}.js`, `src/lib/i18n/explainReorder.js`, pages `Recommendations/ApprovedOrders/Dashboard/Report/AssortmentGap` | V2/V4/demo; no screen ships them (ADR-028) | — (tag `v1-attic`). **The nav entries stay**, as `PageAwaitingData` shells | **REMOVE**: the code, not the entries. Done 2026-09-24: the pages in #174, the engines and `explainReorder.js` in #178 |
| `src/pages/PriceGapPage.jsx`, `src/pages/ProductsPage.jsx`, `src/lib/analytics/{inventoryEngine,velocityConfidence}.js` | rebuilt on the engine: Prices on the comparison (ADR-025), Products on the catalogue (ADR-024) | same | **KEEP** (ADR-028). Listed REMOVE above until 2026-09-24 |
| `src/lib/planogram/*`, `StoreLayoutPage`, `ShelfPlanPage`, `PlanogramPage`, `components/planogram/*`, `e2e/shelf-planning.spec.js` | V4; no screen ships them (ADR-028) | — (tag `v1-attic`). **The Store layout and Shelf plan entries stay**, as `PageAwaitingData` shells | **REMOVE**: the code, not the entries. Done 2026-09-24: the three pages in #174, the libraries, components and e2e spec in #175 |
| `src/surface/V1Spine.jsx`, `src/surface/pages.js` | mounted only by tests; `check:surface` rendered through it | `check:surface` renders `App` | **REMOVE**, done 2026-09-24 (#173), once the gate was re-pointed (ADR-028) |
| Other modules no screen ships: `src/lib/context/*` (the browser's market context), `src/lib/dataAdapters/{artefactToOperational,inventoryAdapter,issueText,loadMarketContext,multiCompetitorAdapter,productAdapter,salesAdapter,validation}.js`, `src/components/{MarketIntelligencePanel,dashboard/*,reports/*,shared/MetricCard,shared/DataProvenanceBanner}`, `src/lib/receiving/leadTimeResolver.js`, `src/lib/types.js`, `src/lib/utils/geoUtils.js` | not shipped (production build, 2026-09-24) | — (tag `v1-attic`) | **REMOVE** (ADR-028), done 2026-09-24 (#176, #178, #180) |
| `src/lib/ai/*`, `src/api/llm_proxy.py`, `tests/test_llm_*.py`, `compare_explanations.mjs`, `report_reorder_explanations.mjs`, Gemini env keys | unspecified, wired shut | — | **REMOVE**, done 2026-09-24 (#178), except `GEMINI_API_KEY` / `GEMINI_MODEL`, which `scripts/enrich_product_profiles.py` still reads |
| `src/telemetry/*`, `telemetry.html`, second Vite entry | **not dead — blind.** Reads the frozen `operational.json`, joins on the pre-ADR-009 id namespace, and reads the pre-V1 decision store, so it has measured nothing since the cut-over (verified 2026-09-13) | rebuilt against `dashboard.json` entries + `ownerState.v2` + `signal_family` labels — F13, spec owed | **REPLACE** |
| `src/mcp_server/`, `mcp_price_adapter.py`, `.mcp.json` entry, `scripts/run_mcp_price_lookup.py`, `firestore_writer.py`, `run_delivery_to_firestore.py`, `export_market_params.py`, `export_store_types.py` | dead | — | **REMOVE**, done: the MCP group (#115), the Firestore writer and the market-params generator (#117), `export_store_types.py` (#180) |
| `kaggle_supermarket_importer.py`, `import_kaggle_supermarkets.py`, `join_yomyom_kaggle.py`, `export_competitor_market_data.py` | run only by `scripts/pilot_daily.sh` (`npm run pilot:daily`), the legacy chain | — | **REMOVE** with Phase 4 Task 4.2, which retires that chain. `export_competitor_market_data.py` fails at its write since `src/data/` went (#180) |
| `build_assortment_gap.py`, `export_assortment_gap.py`, `measure_gap_ranking.py`, `public/data/assortment_gap.json` | their one reader, `AssortmentGapPage`, was removed in #174; only the `gap.emptyDetail` string still names them | — | **REMOVE**, unblocked |
| `tenbis_connector.py`, `alonit_signal_pipeline.py`, `run_alonit_signal_pipeline.py` | **live**, not dead: `delivery_venue_connector.py` imports the first at module top level and the nightly runs it; the alonit pair is the `collect:alonit-signals` npm script | — | **KEEP** until those callers change (Phase 4 Task 4.1 audit, 2026-09-16) |
| "17 unreferenced scripts" | named by count, never by path | — | not executable as written: there is nothing to verify or delete by path (Phase 4 Task 4.1 audit) |
| `code/`, `SmartShelf AI/` | dead copies | — | **REMOVE**, done 2026-09-08 (`2a37c09`) |
| `ARCHITECTURE.md` | accurate trace | banner: superseded by `design.md`, retained as the pre-design trace | **SUPERSEDE** |
| `docs/TECH_*.md`, `UI_DATA_CONTRACT.md`, `RECOMMENDATION_FAMILIES.md`, `PRODUCT_REQUIREMENTS.md`, `SAAS_*.md`, `SPRINT*.md`, `PLANOGRAM_ROADMAP.md` | legacy design prose | `docs/archive/` | **ARCHIVE** (done with this change) |

### 20.2 Transitional states and adapters

| Transition | Temporary mechanism | Removed when |
|---|---|---|
| Artefact cut-over | The engine publishes `dashboard.json`; the browser reads only `dashboard.json` from its first cut-over build. `operational.json` keeps being written for **one** release so a rolled-back browser still works; `sources.json` stops immediately | End of Phase 2 |
| Outcome ids | One-shot legacy id translation in `ownerState.js` (ADR-009), needs the last `operational.json` to be fetchable | Never built: `migrate()` copied legacy ids verbatim (verified 2026-09-16, Phase 4 Task 4.2 note). Moot since 2026-09-24, when the migration it would have extended was removed (#78) |
| Owner-state keys | One-shot migration of `smartshelf.operationalActions.v1`, `smartshelf.ownerAnswers.v1`, `smartshelf.demoState.v1.recommendationDecisions` into `smartshelf.ownerState.v2`; old keys left in place but unread | Phase 4 — **done 2026-09-24** (#78), once the owner confirmed every device had opened the app since the cut-over. The old keys stay, unread |
| `check:signals` | Runs old (reorder) probes until the reorder engine leaves the build, then only V1 probes | Phase 4 — **done 2026-09-24** (#77): only the V1 probes remain |
| Firestore off → on | Until the six `VITE_FIREBASE_*` values and the CI secret exist, the system behaves as "owner state unavailable" honestly (§13); it is *not* silently local | Phase 0 prerequisite |

No permanent compatibility layer survives Phase 4.

### 20.3 Data migration

- **Silver**: regenerated; no migration.
- **Owner state**: localStorage migration above; nothing exists in Firestore today.
- **Committed artefacts**: `operational.json` replaced by `dashboard.json`; `market-context.json` continues (V2).
- **Configs**: `owner_answers.yaml` deleted; `policy.yaml` created; `store_types.yaml` edited.

---

## 21. Spec → Design Traceability Matrix

Design elements: **E** engine module · **P** publisher/artefact · **C** `compose.js` · **U** UI component · **O** owner-state store · **R** reproduction · **I** ingestion. Verification names the AC test (§18) or the mechanism (§14).

### SPEC-001 — Delivery-platform price consistency

| Requirement | Design element | Flow / contract | Verification |
|---|---|---|---|
| FR-001, FR-002, FR-003 | E `price_consistency`: four-state classification; only inverted + above published as entries | 11.2 counts per state | AC-001, AC-002 |
| FR-004, FR-005, FR-006 | E ceiling derivation with published `{pct, method, bands}`; `null` → above suppressed, inverted kept | 11.4 `thresholds.price_consistency` | AC-004, AC-005 (pilot reproduces 18 %) |
| FR-007, FR-008, INV-001 | `characterisation: confirmed_loss` (inverted; commission statement in i18n) / `question` (above) | 11.3 | AC-002, AC-003 |
| FR-009, NFR-001 | `evidence: {shelf, delivery, difference, markup_pct}` | 11.3 | AC-110c |
| FR-010, D-4 | artefact exclusion in E; `counts.excluded_artefact` | 10.4 policy | AC-006 |
| FR-011 | absent price → not in the population; never a zero difference | 11.1 absence semantics | AC-005/SCN-006 |
| FR-012, FR-013, D-2 | `Value{kind: per_sale}`; no totals | ADR-012 | AC-103 |
| INV-002 | ceiling inputs = this run's POS vintage; recorded in `figures` | 11.4 | AC-004 |
| INV-003, NFR-003 | publish-time guard → `unavailable: ceiling_degenerate` | §14 | AC-008 |
| INV-004 | identical never an entry | E | AC-001 |
| INV-005, C-3 | no velocity field exists in `Entry` | 11.3 | AC-007 |
| NFR-002 | pure function, sorted iteration | §18 determinism | AC-004 |
| C-1 | delivery price read only from POS `wolt_price`; competitor observations never enter E | 11.1 | code review + AC-047b |
| C-4, AC-009 | `entry_id` excludes thresholds; outcomes keyed by id | ADR-009 | AC-009 |
| SCN-009 | no "new" marker; ceiling published with change | 9.7 | AC-129 |

### SPEC-002 — Stock reconciliation and data hygiene

| Requirement | Design element | Flow / contract | Verification |
|---|---|---|---|
| FR-020, FR-021, FR-022 | E `reconciliation`: implied opening < 0 with receipts > 0 in the reconcile window, cut once per run at load (ADR-026) | 11.1 `sales_summary` | AC-020 |
| FR-023, FR-025, FR-026, INV-010, INV-011 | `value_policy: none`; publisher assertion; no cost on the row; i18n copy for "not determinable before a count" | ADR-012 | AC-021, AC-022, AC-023 |
| FR-024 | `ordering_key: gap_ratio` | 11.3 | AC-020 |
| FR-027, NFR-010 | `evidence: {recorded_stock, receipts, units_sold, unaccounted, window}`, where `window` is the span reconciled (ADR-026) | 11.3 | AC-024 |
| FR-028, FR-029, FR-030, INV-013, C-12 | E `hygiene` — a capability of its own (ADR-014), `value_policy: none`, one `variant` per reason (negative_stock, no_identifier, absent_price), own badge and own page | 11.2, 11.4 | AC-025 |
| FR-031, FR-032, INV-014 | no standing kind exists in V1; `value_kinds_present` | ADR-012 | AC-026 |
| FR-033, INV-015 | `action: count_product`; no cause strings | §14 | AC-027 |
| INV-012 | detection independent of sign; the rule reads raw stock | I no clamp | AC-020 |
| NFR-011, AC-028 | determinism; `figures` | R | AC-028 |
| C-13, SCN-028 | outcomes persist independent of flag | O | AC-029 |
| §11 unavailable rows | `reconciliation.requires` names `sales_summary`, `hygiene.requires` does not; `status` is computed from `requires`, so receipts absent → `reconciliation: unavailable` while `hygiene` stays available | 11.2, ADR-014 | AC-107 + the rule-12 independence probe (§14) |
| OQ-201/202 | no floor applied (FR-103(4)); window vintages published so misalignment is visible; the capability's own window is the span it reconciled, and `vintages.sales.reconcile_before` the boundary it was cut at (ADR-026) | 11.4 | — |

### SPEC-003 — Competitor price position

| Requirement | Design element | Flow / contract | Verification |
|---|---|---|---|
| FR-040, FR-041, INV-020, C-20, C-21 | I drops affinity-0 stores; context-only sources can only be half a reference | ADR-008 | AC-040, AC-041 |
| FR-042, INV-021, NFR-020 | every displayed observation carries `store {name, format}` + format statement | 11.3 evidence | AC-042 |
| FR-043 | `evidence.reference {kind, same_format_source, supermarket_source}` | 11.3 | AC-040 |
| FR-043a … FR-043d, INV-025, C-24 | cost floor evaluated before the policy; `characterisation: purchase_cost`; missing cost → not evaluated | E | AC-049, AC-050, AC-051 |
| FR-044, FR-044a, FR-044b, FR-044c, INV-026 | reference builder; allowance measured (median over products holding both); substitution flagged; neither → no comparison | 11.4 thresholds | AC-052, AC-053, AC-045 |
| FR-045, FR-045a, FR-045b | `policy_pct 60`, `attention_pct 100` from `policy.yaml`; every breach recorded; `attention: today|review` | 10.4 | AC-054 |
| FR-046, AC-043 | four values in `thresholds.competitor_position` | 11.4 | AC-043 |
| FR-047, FR-048, FR-049 | characterisations `policy_breach_attention` / `policy_breach_review` with the policy stated; no "error" copy | i18n | AC-047 |
| FR-050, FR-051, FR-052, INV-023 | `coverage {catalogue, comparable_population, matched, structurally_uncomparable}`; per-product "no comparison" | 11.2 counts | AC-044, AC-045 |
| FR-053 | `position[]` per comparable source incl. cheaper | 11.2 | AC-046 |
| INV-022 | format-explained differences (within allowance) are not breaches | E | AC-047a |
| INV-024, C-23, D-5 | `role: client` exclusion | ADR-008 | AC-047b |
| NFR-021, NFR-022 | determinism; `freshness_days` (provisional 14) | 10.4 | AC-048 |
| C-22 | manual classification never overwritten (existing) | S11 | existing tests |
| §11 unavailable | no comparable source / stale / no data → `unavailable` | 13 | AC-107 |

### SPEC-004 — Catalogue lifecycle

| Requirement | Design element | Flow / contract | Verification |
|---|---|---|---|
| FR-060, FR-060a, FR-060b, INV-034 | E `catalogue_lifecycle` per run; `EvidenceWindow.full_annual_cycle`; partition assert | 9.6 | AC-065 |
| FR-061, FR-076 | window and seasonal statement in `catalogue.statement` and every count | 11.4 | AC-067 |
| FR-062, C-32, INV-030 (negative) | excluded before classification; raw stock | 10.5 | AC-070 |
| FR-063, FR-063a, FR-063b, FR-063c, INV-031a | automatic withdrawal; `provisional` per entry; re-evaluation is the rule itself | ADR-004, 9.6 | AC-060, AC-063a, AC-063b, AC-063c |
| FR-064, INV-030, D-6, OQ-409 | `withdraw_with_stock = false` asserted | 10.5 | AC-060 |
| FR-065, NFR-031, NFR-033, INV-031 | `withdrawn[]` with evidence; catalogue page lists and revives | U | AC-061 |
| FR-066, INV-032 | any sale → not withdrawn | 9.6 | AC-062 |
| FR-067 | `revivals[barcode].window_id` | O | AC-063 |
| FR-068, INV-033, C-30 | no external write path | §14 | AC-064 |
| FR-069, FR-069a, FR-069b, D-11 | idle ranked by `unit_cost`; no value; stock quantity not shown as justification | 11.3 | AC-071, AC-071a |
| FR-070, FR-071 | outcomes on the idle entry: `present_unsold | quantity_wrong | not_carried` — recorded as an outcome `reason`, no "correct" answer | O | AC-071b |
| FR-072, FR-073, INV-035 | implausible quantity as a question entry (`characterisation: question`); OQ-405 margin provisional (`implausible_ratio` in policy, default: value > 10 % of 7-month revenue) | 10.4 | AC-069 |
| FR-074, C-31 | `withdrawn` in `EngineInputs` for every capability; counts exclude | 11.1 | AC-068 |
| FR-075 | handover CSV from the catalogue page | U | SCN-070 |
| INV-036, SCN-067 | `unavailable: no_sales_evidence`; `withdrawn = None` | 13 | AC-066 |
| NFR-030 | automatic; idle page paginates by rank | U | — |
| NFR-032 | determinism | R | AC-065 |
| C-33 | answers/outcomes keyed by barcode/entry id survive | O | AC-090 |
| ASM-030 / GAP-009 | `EvidenceState.no_row` published on every withdrawn entry | ADR-011 | release condition |

### SPEC-005 — Owner knowledge capture

| Requirement | Design element | Flow / contract | Verification |
|---|---|---|---|
| FR-080, FR-081, INV-044 | E `owner_questions`: only `cost_price` missing on products where an output changes (living products; yield computed) | 11.4 questions | AC-088 |
| FR-082, FR-082a, INV-041 | suppression over `withdrawn` and `idle` | 9.4 | AC-081 |
| FR-083 | `questions.suppressed {withdrawn, idle, no_effect}` | 11.4 | AC-082 |
| FR-084, INV-040, D-8, C-40 | `questions.limit = 3`; panel slices | U | AC-080 |
| FR-085, C-41, NFR-041 | expected value = money at stake × yield (deterministic); where the money cannot be computed none is published, and the question ranks after every question that has one (ADR-027) | E | AC-083 |
| FR-086 | panel renders no queue/total/progress | U | AC-089 |
| FR-087, INV-042 | owner cost precedence; engine read-only | ADR-003 | AC-085 |
| FR-088, FR-093 | pulled at next run; every capability reads `OwnerState` | 9.4 | AC-084 |
| FR-089, FR-090, OQ-502 | answered questions not re-selected; revision by owner only | 10.5 | AC-087 |
| FR-091, INV-043, FR-092 | deferral without value; dependents follow D-3 | 9.4 | AC-086 |
| NFR-040 | suppression bounds the set (1,270 → 12 on pilot) | E | AC-082 |
| NFR-042, C-43 | Firestore + cache | ADR-003 | AC-090 |
| INV-045 | questions ask only for facts from his own records (cost) | — | — |
| §11 storage unavailable | panel not shown | 9.4 | — |
| OQ-503 | questions occupy their own panel at the top of the daily page, above the action list, and take none of its places (resolved 2026-09-23 by the repository owner) | ADR-006 | — |

### SPEC-006 — Daily action surface

| Requirement | Design element | Flow / contract | Verification |
|---|---|---|---|
| FR-100, INV-050, D-9 | `compose` bound | C | AC-100 |
| FR-101 | no remainder anywhere; the old "show all N"/"Showing 20 of N" removed | U | AC-101 |
| FR-102, C-51 | capability pages hold full sets | U | AC-110 |
| FR-103 | `actionable` (1,2,4) in E; (3) in C | ADR-006 | AC-110a |
| FR-104 | valued entries by `value.amount` desc | C | AC-102 |
| FR-105, INV-051, FR-116 | `value_kinds_present` derived; no totals | ADR-012 | AC-103 |
| FR-106, FR-106a | `unvalued_places` (provisional 3) with per-capability keys | C | AC-100 + unit test |
| FR-107 | capability badge on every entry | U | AC-110b |
| FR-108, INV-056 | dedupe with precedence | C | AC-109 |
| FR-109, FR-110, NFR-051 | `action` enum + evidence on the card | U | AC-110c |
| FR-111, INV-052 | `Value.certainty` label | U | AC-104 |
| FR-112 … FR-115, INV-053, NFR-052, C-50, C-52 | outcomes in O; id stability; snapshot on outcome | ADR-003, ADR-009 | AC-105, AC-106 |
| FR-117, INV-057 | per-capability `status` rendered | U | AC-107 |
| FR-118 | empty state only when all available and nothing admitted | C | AC-108 |
| INV-054 | hygiene `value_policy: none` | ADR-012 | AC-103 |
| INV-055, C-54 | no velocity field | 11.3 | AC-111 |
| NFR-050 | bound + ten-minute measurement (GAP-007) | — | pilot measurement |
| NFR-053 | `compose` pure | C | property test |
| C-53 | i18n + e2e invariants | U | AC-112 |
| OQ-601/602/604/605/606/607 | provisional constants in `policy.yaml` / existing behaviour (§22) | — | — |

### SPEC-007 — Figure provenance and reproducibility

| Requirement | Design element | Flow / contract | Verification |
|---|---|---|---|
| FR-120, INV-060, FR-132, C-60 | `vintages` block; every page renders it; refresh cadence stated on the data page | 11.4 | AC-120 |
| FR-121, FR-124, FR-125, NFR-062 | `figures.py` = engine print mode; no args; current data | ADR-002 | AC-121 |
| FR-122 | a figure without a registry entry cannot be published (schema requires `inputs`) | P | schema |
| FR-123, AC-129 | thresholds in every figure record | 11.4 | AC-129 |
| FR-126, INV-062 | missing input → unavailable, exit 1 | 11.6 | AC-122 |
| FR-127 | `printed_at` + input vintages | 9.5 | AC-125 |
| FR-128, FR-129, INV-061 | `None` ≠ 0 throughout; UI "no figure" | §14 | AC-123 |
| FR-130, INV-063 | `certainty` required | ADR-012 | AC-124 |
| FR-131 | `intent.md`'s boxed warning stays; the data page links to reproduction | — | AC-128 |
| FR-133, FR-134, INV-064 | no composites in V1; the schema forbids a value without kind | P | AC-126 |
| INV-065, AC-127 | one code path | ADR-001 | AC-127 |
| NFR-060 | ≤ 2 min; content addressing | §16 | Phase 3 checkpoint |
| NFR-061 | determinism | §18 | AC-127 |
| NFR-063, C-61, GAP-005 | committed inputs + rehydrate + recompute → fresh clone reproduces; coverage figures now come from E | ADR-002 | AC-128 |
| C-62 | D-1/D-4/D-3 mechanisms above | §14 | AC-123/124 |

### Cross-cutting decisions

| Decision | Design element |
|---|---|
| D-12 single store/user/POS | ADR-007; no tenancy, no accounts, one importer, `VITE_STORE_ID` pinned |
| D-13 no sensors/cameras | Nothing in the design; the shelf-photo module leaves with the planogram (§5.4) |
| D-10 uncertainty labelled before challenge | `certainty`, `provisional`, `EvidenceState` are all in the artefact, not added on challenge |
| INT-MEAS | outcome snapshots captured (§10.3); no surface built; OQ-801 open |

### Reverse check — every component has a reason

| Component | Justified by |
|---|---|
| Collectors/snapshots | SPEC-003 inputs; C-60 (one day kept server-side) |
| POS + sales importers | every V1 input |
| Signals + matching | SPEC-003 precondition |
| Store registry | C-20 … C-22 |
| Owner-state store + pull | ARCH-DRIVER-004 |
| Engine (7 capabilities + surface + provenance) | SPEC-001 … SPEC-007; SPEC-002 yields two capabilities under ADR-014; margin: browse-only pending SPEC-008 (§22) |
| Publisher + schema | ARCH-DRIVER-002, -003, -007 |
| `compose` + DailyPage | SPEC-006 |
| Capability pages | FR-102, FR-065, FR-067, FR-070, FR-075 |
| QuestionPanel | SPEC-005 |
| Receiving capture | `intent.md` §7/§8 (starts 12/9) — the one component justified by the intent rather than a spec; explicitly V2 data capture |
| Data page | FR-120, FR-132, FR-117 |
| i18n | C-53 |
| figures CLI | SPEC-007 |
| CI (`ci.yml`, nightly) | ADR-013; C-60 |

Everything not in this table is removed (§5.4).

---
## 22. Risks and Remaining Unknowns

### 22.1 Specification-layer items the design surfaces (not architectural blockers)

| ID | Item | Design stance |
|---|---|---|
| **SPEC-GAP-A** | **Margin below cost has no specification.** `intent.md` §2ب names "prices *and margins*" as V1's money-bearing kind and D-4 exists for it, but SPEC-001 §3 scopes it out as "a different signal with a different threshold" and no SPEC covers it. Today it is the surface's highest-weighted type | Retained as a capability with a browse page; **not admitted** to the daily surface (FR-103 requires a producing specification to define actionability). The owner will therefore *not* see below-cost items on the morning screen until a SPEC-008 exists. This is a visible product consequence and should be decided at the spec layer before V1 release — the architecture is unaffected either way |
| GAP-009 | "Sold nothing" = "no sales row" for 5,848 classifications | `EvidenceState.no_row` published; owner check is a release condition |
| GAP-007 | Ten minutes unverified | `bound` is a constant; measure in pilot |
| OQ-801 | INT-MEAS money component | outcome snapshots captured; no surface |

### 22.2 Provisional parameters (configurable; product decisions pending, none blocks implementation)

| Parameter | Provisional value | Open question |
|---|---|---|
| `surface.unvalued_places` | 3 of 10 | OQ-602 |
| Unvalued precedence for one-product-one-place and interleaving (`surface.unvalued_order`) | reconciliation → competitor_position → idle → hygiene (hygiene last: 1,155 finite cleanup records, §9.2) | OQ-601 |
| Questions placement | own panel above the action list, not surface places — **resolved 2026-09-23** | OQ-503 |
| Deferral lapse | 4 h / tomorrow / next week (existing) | OQ-604 |
| Decline permanence | stands for the entry id; changed value does not reopen | OQ-605 |
| `freshness_days` | 14 | OQ-306 |
| Ceiling derivation parameters | 2-point bands, ≥ 75 % density drop, ≥ 20 items in the preceding band (reproduces 18 % on pilot) | — (FR-004 requires derivation; the method is a design choice and is published) |
| `implausible_ratio` | value > 10 % of seven-month revenue | OQ-405 |
| `full_annual_cycle` | 12 consecutive months present | OQ-408 |
| Materiality floors | none (per FR-103(4)) | OQ-101, OQ-202 |
| `MAX_CREDIBLE_GAP_PCT 300` from `credibility.js` | kept as a counted exclusion in price_consistency, reported like D-4 | no spec names it — decide keep/drop at the spec layer |
| "I don't know" | stored as deferral with `reason: unknown` | OQ-501 |

### 22.3 Technical risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Firestore first-run: rules, anonymous auth, service-account read from CI have never been exercised here | High | Owner state unavailable → questions absent, outcomes device-local | Phase 0 checkpoint: `check:firebase-live` + a CI dry-run pull before any capability work; the system degrades honestly (§13) |
| Ceiling derivation degenerate on a future export | Medium | above-ceiling suppressed | FR-006 behaviour is designed; inverted continues |
| Competitor coverage counts will differ from the intent's (1,970 vs 2,650 measured) | Certain | numbers in the 12/9 deck | `figures` is the source; `intent.md` §12 already says so |
| rapidfuzz false matches with a shared identifier across pack sizes (OQ-303) | Medium | spurious extreme premiums | review band retained; fuzzy matches never auto-approved ≥ 0.85; matched-by-fuzzy shown in evidence |
| Reproduction > 2 min on a fresh clone | Medium | NFR-060 | content addressing; measure at Phase 3 |
| Removing 60 % of the tree breaks a hidden dependency | Low | build | removal is the last phase, behind green CI |
| Two-year reports change the window mid-pilot | Expected | withdrawals re-evaluated | FR-063c designed; OQ-409 asserted absent |

---

## 23. Implementation Handoff

Not a task list — the dependency structure implementation must respect.

### Phase 0 — Foundations (blocking everything else)

1. **Contract**: `schemas/dashboard.schema.json` v2; `CapabilityOutput` (with `requires`
   and computed `status`), `Entry` (with `signal_family`), `Value` dataclasses;
   `configs/policy.yaml` (incl. `surface.unvalued_order`); `src/engine/registry.py` — the
   complete capability list **including `hygiene`** with its `requires` and value policy,
   and the frozen `signal_family` enumeration (ADR-009, ADR-014). Nothing downstream may
   start before the id set and the `signal_family` strings are fixed: they are the keys of
   every owner decision the pilot will record.
2. **Owner-state model** (§10.3): JS `ownerState.js` (+ key migration), Python `pull.py`
   + mirror; Firebase configured end to end (six `VITE_FIREBASE_*`, service-account secret,
   rules deployed). **Checkpoint 0-A:** `check:firebase-live` passes; a CI dry run pulls
   and mirrors an empty state.
3. **Ingestion fixes**: `--as-of` on the POS importer; `sales_importer` (monthly +
   summary + window); barcode zero-strip in signals and matching; per-store matches;
   `store_types.yaml` client role + Einat.
4. **Orchestrator + publisher** (`run_engine.py`, `publish.py`) with no capabilities yet;
   `ci.yml`. **Checkpoint 0-B:** a run publishes a valid, empty-of-capabilities artefact
   and CI is green.

### Phase 1 — Capabilities (independent of each other once Phase 0 lands)

Implementable in parallel by two people:

- **1a** `reconciliation` + `hygiene` (refactor; one module, two `CapabilityOutput`s with
  different `requires`) and `price_consistency` (replace).
- **1b** `catalogue_lifecycle` then `owner_questions` (depends on lifecycle's withdrawn/idle sets).
- **1c** `competitor_position` — depends on ingestion fixes (0.3) and the store registry.
- **1d** `surface_candidates`, `provenance`, `margin_below_cost` (browse-only).

**Checkpoint 1:** every AC test for SPEC-001 … SPEC-005 passes on the pilot fixture; the
publisher's money and status assertions hold on the real data; `figures` prints the
registry (temporary text output).

### Phase 2 — Browser cut-over (depends on Phase 1's artefact)

- `loadDashboard`, `compose` (with property tests), `DailyPage`, `EntryCard`, six
  capability pages (incl. `hygiene` and the margin browse), `QuestionPanel` over
  `capabilities.owner_questions`, `DataPage`, `ReceivingPage`, reduced `AppShell` nav,
  i18n keys in all three languages.
- One-shot outcome-id and localStorage migrations.
- `operational.json` still published alongside for one release.

**Checkpoint 2:** e2e invariants pass on the new pages; AC-100 … AC-112 pass; a recorded
outcome survives reload and appears in Firestore; the surface never shows a remainder.

### Phase 3 — Reproduction and gates (depends on Phases 1–2)

- `scripts/figures.py` as engine print mode; content addressing; `check:signals` V1
  probes; nightly workflow updated (pull → import → engine → publish → probes → commit
  `dashboard.json` + `owner_state.json`).

**Checkpoint 3:** fresh clone → `npm run figures` exits 0 in ≤ 2 min and its figures equal
the committed artefact's `figures{}` (AC-127); nightly run green two nights in a row.

### Phase 4 — Removal (depends on Checkpoint 3)

- Tag `v1-attic`; delete §5.4's list; stop publishing `operational.json`; remove the
  migrations; archive-doc banners already in place.

**Checkpoint 4:** bundle < 500 KB; CI green; `git grep` finds no reference to removed
modules; the three workflows plus `ci.yml` are the only automation.

### Release conditions (outside implementation)

- SPEC-GAP-A decided (margin below cost specified or explicitly left off the surface).
- GAP-009 owner check performed (name twenty absent products).
- GAP-005: `figures` on a fresh clone verified before any coverage figure is stated.

---

## 24. Design Readiness Verdict

| Gate condition | Status |
|---|---|
| Every material spec requirement has a design answer | Yes — §21 |
| Every invariant has a technical enforcement strategy | Yes — §14 |
| Major state ownership explicit | Yes — §12; one mutable store |
| Component responsibilities explicit | Yes — §7 |
| Important contracts explicit | Yes — §11, schema v2 |
| Important flows explicit | Yes — §9 |
| Important failure paths designed | Yes — §13 |
| Target architecture coherent | Yes — §6 |
| Current → target migration understood | Yes — §20 |
| Major decisions have rationale | Yes — §19, 13 ADRs |
| Important unknowns resolved | Architectural unknowns resolved; product unknowns are parameterised with stated provisional values (§22.2) — none forces implementation to invent architecture |
| No architecture exists only because legacy code contained it | Yes — every surviving component is justified in §21's reverse check; legacy engines, demo spine, AI layer and copies are removed |
| Implementation can proceed without inventing architectural decisions | Yes |

## READY FOR IMPLEMENTATION

With two conditions carried forward as **release** (not implementation) conditions:
SPEC-GAP-A — margin-below-cost has no producing specification and is therefore designed
*off* the daily surface until one exists; and GAP-009 — the owner confirms that absence
from a monthly report means no sale, before 3,900 products are withdrawn in front of him.
