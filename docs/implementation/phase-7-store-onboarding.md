---
ID: PLAN-PHASE-7
Title: Phase 7 — A new store without code changes (ADR-036)
Status: Approved — by the repository owner, 2026-09-30 ("approved"), with ADR-036
Owner: smartshelf-architect
Parent: [Implementation plan](plan.md)
Inputs: [D-28, ADR-036 (Accepted 2026-09-30), docs/pilot/next-store.md, src/engine/inputs.py, src/engine/run.py, src/common/paths.py, src/context/weather.py, src/internal_pos/, scripts/import_yomyom_pos.py, scripts/import_yomyom_sales.py, src/matching/product_matching.py, configs/delivery_targets.yaml, configs/store_types.yaml, firestore.rules, scripts/check_firebase_config.mjs, .github/workflows/collect-daily.yml, index.html]
Updated: 2026-10-01 (Tasks 7.1–7.6 built; one pull request)
---

# Phase 7 — A new store without code changes

**Goal.** Build ADR-036. After this phase, a store is set up by:
1. making a clean copy;
2. filling `configs/store.yaml`;
3. finding and confirming its nearby venues;
4. committing its exports;
5. setting its accounts.

`npm run check:store` says what is still missing and what it blocks. Code never changes.

**Nothing YomYom's copy shows or publishes changes.** Every task that touches the engine,
the build or the nightly proves it with the same data before and after.

## Phase constraints

- **No defaults to YomYom.** A missing settings key stops the run and names the key
  (ADR-036 §2).
- **No invented data.** The venue finder's tests use a response captured from the live
  listing, never an invented one. No task generates a POS file, a sales report or a store
  fact (D-23, CLAUDE.md rule 7).
- **The identical-artefact proof** runs `run_engine(mode="print")` over the same data before
  and after. It compares every capability's status, counts, thresholds, entry ids and
  evidence, `assortment_gap`'s market prices, and every figure. Only the run's time, id and
  step timings may differ.
- **Actions minutes.** Three PRs, each tested locally first (the suites, lint, build and
  bundle, e2e, and `check:signals`) and pushed once.

## Tasks, in dependency order

### Task 7.1: The settings file and its loader (ADR-036 §2)

**Files:** `configs/store.yaml` (new), `src/common/store.py` (new), `tests/test_store_settings.py` (new),
`src/engine/inputs.py`, `src/engine/run.py`, `src/context/weather.py`, `src/internal_pos/`
(the importers' default paths and the silver names), `src/matching/product_matching.py`,
and every other reader of `yomyom_products.parquet` or `yomyom_inventory.parquet`, which
`git grep` lists at the start of the task.

- The loader validates every key. A missing or invalid one raises with the key's name.
- `OUR_FORMAT`, `SALES_DIR`, the client store ids, the weather coordinates and the store id
  come from the settings.
- The silver tables become `products.parquet` and `inventory.parquet`.

**Done when:** the identical-artefact proof passes, and so do the suites and `check:signals`.
A test removes each key in turn and sees the run stop, naming it.

### Task 7.2: The nightly, the build and Firebase read the settings

**Files:** `.github/workflows/collect-daily.yml`, `scripts/import_yomyom_pos.py` →
`scripts/import_pos.py`, `scripts/import_yomyom_sales.py` → `scripts/import_sales.py`
(the export path from the settings, with no `--input` needed), `vite.config.js` (the tab
title from `site_title`), `index.html`, `scripts/check_firebase_config.mjs`, `package.json`,
CLAUDE.md rule 6, `docs/operations/deployment.md`.

- The nightly sets `VITE_STORE_ID` from the settings and runs the renamed importers.
- `check_firebase_config` fails when `firestore.rules`' pinned root or `VITE_STORE_ID`
  differs from the settings' `id`.

**Done when:**
- the built `index.html` title is byte-identical to today's;
- the nightly's import and engine commands, run locally, give the identical artefact;
- `check:firebase` passes;
- e2e is green.

### Task 7.3: The nearby-venue finder (ADR-036 §4)

**Files:** `scripts/find_nearby_venues.py`, `src/external/venue_discovery.py`,
`tests/test_find_nearby_venues.py`, `tests/fixtures/venue_discovery/` (a captured response).

**Done when:** over YomYom's location and 5 km, it lists the venues of
`configs/delivery_targets.yaml` that the listing still carries, each with its distance. It
writes only its review file. Its tests run offline on the captured response.

### Task 7.4: `npm run check:store` (ADR-036 §5)

**Files:** `scripts/check_store.py`, `tests/test_check_store.py`, `package.json`.

**Done when:**
- On this copy it reports:
  - the POS export present, dated 2026-06-06;
  - the monthly reports present;
  - the daily reports missing, naming `order_quantity`;
  - the department facts missing;
  - every nearby venue classified.
- On an empty copy (Task 7.5) it reports every input missing.
- An invalid settings file exits 1. It never prints a secret's value.

### Task 7.5: The manifest, the copy script and the setup guide (ADR-036 §3)

**Files:** `src/common/store.py` (the manifest), `scripts/new_store_copy.py`,
`tests/test_new_store_copy.py`, `docs/operations/new-store.md`, `docs/pilot/next-store.md`
(a link to the guide).

**Done when:**
- A copy made into a temporary directory holds no manifest data, and no manifest path holds
  YomYom's id or name.
- On that copy, with its settings filled, `npm run build` passes and `check:store` lists what a
  store must supply.
- `--update` carries a code change across and leaves every manifest path untouched.

> **Refined 2026-10-01, while building.** "The suites pass on the copy" is dropped. Many tests
> read the committed store data (the artefact, the snapshots, the export), which a clean copy
> does not have. A copy does not change code: code is tested here, and `--update` carries it
> across. So a copy leaves out `ci.yml`, and its nightly, with the probes in it, runs as it
> does here. The ignore rules move from YomYom's folder to any store's
> (`raw_pos/*/sales_daily/`, and `/*.csv` for Vercel), or a new store's daily reports would
> never be committed.

### Task 7.6: The fake data goes (ADR-036 §6)

**Files:** `scripts/generate_fake_yomyom_pos.py` (deleted), `README.md`,
`src/matching/product_matching.py` (the sample-CSV fallback), and `samples/sample_expiry_scans.csv`
(deleted 2026-10-01: invented expiry scans that nothing read).

**Done when:** `git grep` finds no reference to either, and the suites pass.

## Pull requests

One pull request for the phase, instead of three, to spend Actions minutes once: its commits
are the six tasks, each tested locally first.

## Checkpoint 7

- YomYom's artefact is unchanged by the phase (the proof in PR 1 and PR 2).
- A clean copy is made, builds, passes the suites, and `check:store` on it lists exactly what
  `docs/pilot/next-store.md` says a store must send.
- No hard-coded store id, name, path, format or coordinate remains in the code a copy runs:
  the engine, the importers, the nightly, the build, the Firebase checks and the setup tools.
  Research scripts written against the pilot's data (the Alonit discovery, velocity,
  baselines) say so in their docstrings, and comments that record the pilot's history keep
  its name.
