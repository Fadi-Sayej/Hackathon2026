---
ID: PLAN-PHASE-7
Title: Phase 7 — A new store without code changes (ADR-036)
Status: Approved — by the repository owner, 2026-09-30 ("approved"), with ADR-036
Owner: smartshelf-architect
Parent: [Implementation plan](plan.md)
Inputs: [D-28, ADR-036 (Accepted 2026-09-30), docs/pilot/next-store.md, src/engine/inputs.py, src/engine/run.py, src/common/paths.py, src/context/weather.py, src/internal_pos/, scripts/import_yomyom_pos.py, scripts/import_yomyom_sales.py, src/matching/product_matching.py, configs/delivery_targets.yaml, configs/store_types.yaml, firestore.rules, scripts/check_firebase_config.mjs, .github/workflows/collect-daily.yml, index.html]
Updated: 2026-10-08 (Tasks 7.7–7.10 for D-39 and ADR-043, ready for review); 2026-10-08 (Checkpoint 7 checked on a clean copy: met after #296, #299 and #302; one question open); 2026-10-01 (Tasks 7.1–7.6 built; one pull request)
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


### Result, 2026-10-08: met, after three fixes the run found

Checked on a clean copy made from main for a test store, "Store B". It has another format
(`urban_minimarket`), its own settings and none of YomYom's venues. The copy stayed in a
scratch directory and was never pushed. The run found three defects, each fixed and merged
before this result was taken:
- **#296:** the copy told a new store to fill `store_policy.yaml` with a script that could not
  run for any store.
- **#299:** the probes' test world read the store's format and venue list from the copy's
  settings. In a copy its market was empty, and `check_order_signals` would have blocked
  every nightly once the store's own data went live.
- **#302:** the boost prompt told the model the shop was in Kafr Qasim, with three nearby
  stores.

| Item | Result |
|---|---|
| YomYom's artefact unchanged | **Met.** Print-mode runs at 2026-10-08T08:00Z on main and with #299 are identical, except the `run_id`, which is random on every run. #302 changes only `thresholds.market_boost.prompt` (v1 to v2) and the `inputs_digest` that covers it; no capability figure moves. |
| A clean copy is made and builds | **Met.** 1,411 code files and 8 empty settings, with no `store_policy.yaml`. `npm run build` passes, with Store B's title and site address. |
| It passes the suites | **Met as ADR-036's 2026-10-01 note defines it, not literally.** Code is tested here, where CI runs; a copy carries no `ci.yml`. In the copy, Python: 1,228 pass and 44 fail. JS: 640 pass, 2 fail and 2 suites do not load. Every one reads something a new copy does not have yet: YomYom's committed venues, snapshots, monthly reports or artefact; YomYom's venue ids in its `store_types.yaml` (nine engine unit tests); the artefact the first nightly writes; or the Firebase set-up (step 3), which `check:firebase` correctly reports as not done. None tests code the copy runs. The order probe the copy's nightly runs passes there, 17 checks. |
| `check:store` lists what `next-store.md` asks for | **Met for every file `next-store.md` names:** the store's own entries, the nearby venues and their formats, the POS export, the monthly and daily reports, the department facts and the shelf layout. It also lists the two Actions secrets. The rest of the list is not files, so it cannot be checked: the owner's sign-in (an account), GAP-009, and time for three questions a day. GAP-011 is a file value (`owner_declared_ceiling_pct`). A copy starts with it empty, which means the derived ceiling, published as derived. |
| No hard-coded store value in the code a copy runs | **Met after #302.** The sweep covered the 312 files a copy carries from `src/`, `scripts/`, `configs/`, the nightly and the build. It looked for YomYom's name, its town, coordinates and format, its Firebase project, its site addresses and its venue id. It found docstrings and history comments, which this checkpoint allows, and one example in a hint: `check:firebase` shows "e.g. hackathon26-a6ebd" for a missing project id. |

**Open, for the repository owner:** `price_policy_pct` in `configs/policy.yaml` is the pilot
owner's +60%. F3-S1 FR-045 calls it "a declared maximum premium … settable as a product
decision". A copy carries it as code, and the loader falls back to 60 when the key is absent.
So a second store's F3 findings would use +60% until someone changes it. The setup guide
(step 7) says to ask the new owner; nothing checks that anyone did.


## Added 2026-10-08: D-39, the price rule is the owner's (ADR-043)

**Status:** Approved, with ADR-043 and its wording, by the repository owner on 2026-10-08
("approve"). Tasks 7.7 to 7.9 merge in one pull request,
because the engine's split and the screens that read it must arrive together.

### Task 7.7: The rule as a store fact (ADR-043 §1)

- `configs/store_facts.yaml` gains `price_rule`, YomYom's entry as ADR-043 gives it, and
  `src/engine/store_facts.py` validates it.
- `configs/policy.yaml` loses `price_policy_pct`. `src/engine/policy.py` no longer defaults it.
- The engine gains the input `price_rule`, and `check:store` gains its row.

**Done when:** YomYom's artefact is unchanged (the print-mode proof); a fixture without the
entry, and one with a malformed entry, both leave the input absent and say why; and
`check:store` on a clean copy lists the rule as missing.

### Task 7.8: `policy_breach`, the breaches' own capability (ADR-043 §2, §3, §5)

- **The capability.** It is registered with `requires` that include `price_rule`, its
  `published_from` set to its first nightly, and its place after `competitor_position` in
  both order lists.
- **One pass.** It is computed in the same pass as `competitor_position`, which keeps the
  comparison and the purchase-cost findings.
- **The probe** withholds the rule.

**Done when:** the print-mode proof shows YomYom's 10 breaches under `policy_breach` with the
same ids, evidence and order, and `competitor_position` otherwise unchanged. The probe passes,
and catches each case when its guard is removed.

### Task 7.9: The findings page and Today read both (ADR-043 §3, §4)

- **The screens.** The F3 findings page and the composer read `policy_breach` beside
  `competitor_position`.
- **The words.** `unavailable.no_price_rule` is added in three languages, as approved.

**Done when:** the screenshot comparison shows every YomYom screen byte-identical before and
after (126 screens), and a fixture without the rule shows the approved sentence where the
breaches were, with the purchase-cost findings still listed.

### Task 7.10: Checkpoint 7, again, for D-39

On a clean copy for a test store:
- `check:store` lists the rule;
- the artefact publishes `policy_breach` unavailable (`no_price_rule`) and
  `competitor_position` available.
