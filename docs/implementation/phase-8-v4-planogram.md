---
ID: PLAN-PHASE-8
Title: Phase 8 — V4, F12 Planogram (F12-S1)
Status: Approved — by the repository owner, 2026-10-04 ("yes"), with the values it proposes. The same answer added D-32, an AI explanation of each shelf (Task 8.10)
Owner: smartshelf-architect
Parent: [Implementation plan](plan.md)
Inputs: [docs/features/F12-planogram/specs/F12-S1-planogram.md (Approved 2026-10-04), ADR-037 and ADR-038 (Accepted 2026-10-04), ADR-009, ADR-014, ADR-016, ADR-029, ADR-030, ADR-036, D-29, D-30, D-31, src/engine/order_evidence.py, src/engine/store_facts.py, src/engine/registry.py, src/engine/model.py, src/engine/publish.py, src/common/store.py, src/common/store_readiness.py, src/surface/compose.js, src/owner/ownerState.js, src/App.jsx, scripts/check_order_signals.py, scripts/build_order_example.py, src/lib/dataAdapters/loadOrderExample.js]
Updated: 2026-10-04 (approved; D-32 adds Task 8.10)
---

# Phase 8 — V4, F12 Planogram

**Goal.** Build F12-S1:
- a layout file the team records (ADR-037);
- three capabilities: `layout_facts`, `shelf_plan` and `shelf_measurement`;
- his "I've arranged this shelf" record (ADR-038);
- the probe;
- the marked example (D-31);
- after he approves their mockups, the Store layout and Shelf plan pages.

**On real data, all three capabilities are unavailable when it ends.** There is no store
(D-23), so there is no layout file and no daily reports. Each says why: `no_store_layout`,
like F8's `no_daily_sales`. Everything is proven on fixture worlds, as Phase 5 was.

## Phase constraints

- **One window rule.** The before and after windows apply F8-S1 FR-144's rules to a span of
  days. Task 8.5 moves those checks out of `evidence_window` into one function that both call.
  It is never a second copy.
- **One "he stocks", and one demand.** `shelf_plan` calls `order_evidence.stocks` and
  `order_evidence.product_evidence`. It never re-derives them (INV-085). The window's values are
  read from `order.*` in policy, never copied (one fact, decided once).
- **No ₪ anywhere.** The publisher refuses a value, or any money-named field other than a placed
  product's `margin_per_sale`, in all three capabilities (INV-087).
- **No invented store data.** The fixture worlds are test shops under `tests/fixtures/`. The
  example is built from one of them, under D-31's banner. No task writes a layout file, a sales
  report or an arrangement for a real store (D-23, CLAUDE.md rule 7).
- **Nothing the owner sees changes before Task 8.8's mockups are approved** (F12-S1 C-75). Task
  8.0 keeps the new capabilities off every screen, and the two pages stay awaiting shells until
  Task 8.9.
- **No new dependency.** The regression is a logistic fit in numpy (Task 8.5). `requirements.txt`
  lists neither `statsmodels` nor `scipy`, and numpy comes with pandas.
- **Determinism.** The bootstrap's draws use a seed set in policy, so print mode and
  `npm run figures` reproduce the artefact (NFR-073).
- **Actions minutes.** Three pull requests. Each is tested locally first (the suites, lint,
  build and bundle, e2e, `check:signals`) and pushed once.

## Provisional values, proposed for the owner's approval

F12-S1 leaves these to the plan (OQ-1204, OQ-1207). The new values go into `configs/policy.yaml`
under `shelf:`, and the artefact publishes every one.

| Value | Proposed | Basis |
|---|---|---|
| Space elasticity, until his own is measured | 0.17 | Research: Eisend's mean over 1,268 estimates (F12-S1 §23) |
| Facings cap per product | 4 | A judgement. At 0.17, a product's 2nd facing adds 12.5% to its sales, the 3rd 7.1%, the 4th 5.0%, and a 5th would add 3.9%. The cap stops one product taking a shelf for a few percent per facing. His "at least N" rule overrides it |
| Window length and minimum report days | F8's: 28 and 21, a report in every week | Read from `order.window_days` and `order.min_report_days`, not copied, so the measurement's windows are the plan's |
| Interval level | 95% | The level the repository's other intervals use (`wilson_interval`, `sales_movement`, z = 1.96) |
| Minimum arrangements for a store elasticity | 8, each on a different fixture | A judgement. The bootstrap resamples fixtures, so the minimum counts fixtures. A small store has ten to twenty fixtures, and intervals from so few clusters run too narrow (Cameron, Gelbach and Miller, 2008). That makes a false "measured" more likely, not less. The guards against one replacing 0.17 are the placebo and the 0-to-1 range (FR-206, FR-209). The estimate publishes how many fixtures it rests on |
| Minimum arranged products | 40 | A judgement: about five per arrangement |
| Bootstrap draws, and the seed | 1,000; a fixed seed | 1,000 is common for a 95% percentile interval. Its time is measured in Task 8.5 (NFR-072, NFR-076) |

## Proposed for the owner, from earlier answers

- **The example's source (D-31).** It is built like Reorder's: by `scripts/build_shelf_example.py`,
  in print mode, from Task 8.5's planogram world, into `public/examples/shelf-plan-example.json`.
- **The photo-reading test (OQ-1202, "yes why not").** It runs after this phase, on the next
  store's first shelf photographs. A model's reading of each facing width is compared with the
  team's own reading of the same photographs. Nothing in this phase waits on it, because there
  is no store to photograph now (D-23).

## Tasks, in dependency order

| Task | Depends on | Delivers |
|---|---|---|
| 8.0 | — | The browser guard, the reason words and the publication dates |
| 8.1 | 8.0 | The layout file's loader |
| 8.2 | 8.1 | `layout_facts` |
| 8.3 | 8.2 | `shelf_plan` and its `shelf.plan` entries |
| 8.4 | — | The arrangement record in the browser |
| 8.5 | 8.3, 8.4 | The planogram world, `shelf_measurement`, and the plan reading its elasticity |
| 8.6 | 8.5 | The probe |
| 8.7 | 8.5 | The marked example |
| 8.8 | 8.7 | Mockups for the owner's approval |
| 8.9 | 8.8 approved | The two pages |

### Task 8.0: The browser guard, the reason words and the publication dates (AC-187)

**Files:**
- `src/surface/compose.js`, `src/surface/__tests__/compose.test.js`
- `src/__tests__/everyCapabilityReachable.test.jsx`, `src/surface/__tests__/checkpoint2.test.jsx`
- `src/lib/i18n/dictionaries/{he,ar,en}.js`, `src/lib/i18n/__tests__/unavailableReason.test.js`
- `tests/engine/test_unavailable_reasons.py`, `src/engine/registry.py`, `scripts/check_deploy_data.py`

Today and Data list every capability an artefact publishes, unless `compose.js` keeps it off. The
registry's `admitted: false` is not enough on its own. So, as Phase 5's Task 5.0 did:
- `layout_facts`, `shelf_plan` and `shelf_measurement` join `NOT_ON_TODAY` for good (FR-192).
  They also join `NOT_YET_SHOWN` until Task 8.9.
- The registry entries come later, each with its runner: Tasks 8.2, 8.3 and 8.5. An entry with
  no runner would stop the nightly from publishing. Each of those tasks sets its entry's
  `published_from`, so `check_deploy_data` accepts an earlier artefact without it. That script
  needs no change.
- Every new reason gets its words in all three dictionaries, as his words (FR-194). The new
  reasons are `no_store_layout`, `layout_all_rejected`, `no_evidence_window`,
  `owner_state_unavailable` and `no_arrangement_recorded`. Of FR-193's reasons, only
  `stale_daily_sales` and `no_daily_sales` have words already. F8 says "no window" per
  department, not for the capability.

**Done when:** a test artefact carrying the three ids renders exactly as one without them: the same
DOM on Today and Data, and nothing composed. The suites pass, and Today and every page are
byte-identical before and after. The proof is the before-and-after screenshot method of Phase 5
and #185: every page, in three languages and two widths, each side served on its own port.

### Task 8.1: The layout file's loader (ADR-037; FR-178 … FR-180, FR-199; AC-183)

**Files:** `src/engine/store_layout.py`, `src/engine/inputs.py`, `src/engine/registry.py`,
`src/common/store.py`, `src/common/store_readiness.py` (its inventory and a `FEEDS` entry),
`docs/pilot/next-store.md` (the list `check:store` mirrors), `docs/operations/new-store.md`,
`tests/engine/test_store_layout.py`, `tests/test_new_store_copy.py`, `tests/test_check_store.py`

- The loader follows `store_facts.load_store_facts`: it validates, never repairs, rejects entries
  by name with a reason, and checks provenance by kind. A measurement carries `measured_by` and
  `measured_on`. A statement carries `stated_by`, `stated_on` and `recorded_by`.
- It rejects:
  - two eye-level shelves on one fixture;
  - a rule naming a product outside the catalogue;
  - a department on two fixtures with no "keep on" rule;
  - a product of a split department that no rule names;
  - a width, length or facing count that is not a positive whole number;
  - a rule outside FR-188's five.

  Current facings and their shelf are dated measurements (ADR-037).
- `EngineInputs.store_layout` is None when `configs/store_layout.yaml` is absent, and
  `INPUT_REASONS["store_layout"]` is `"no_store_layout"`.
- **No empty file is committed, and a new copy starts without one.** The file goes in
  `STARTS_WITHOUT`, not `STARTS_EMPTY`. An empty file is a present file (FR-193), so a copy that
  started with one would never say `no_store_layout`; it would show a layout with no fixtures.
  Starting without it keeps "the measurements have not been recorded" true until the team
  records a store's first fixture and commits the file. Either way the file is store data that
  a copy never inherits or overwrites, as ADR-037 §5 says. That section's words "files that
  start empty" were corrected with this plan.
- `check:store`'s inventory (`store_readiness.py`) names the file when it is missing (AC-188).
- A test asserts the capabilities' inputs are the layout file and the existing artefact inputs:
  no image, camera or sensor path (INV-084, AC-183).

**Done when:**
- AC-183, AC-184 and AC-188 pass.
- YomYom's print-mode artefact is unchanged in every capability. Its thresholds, `run.steps` and
  inputs digest may change.

### Task 8.2: `layout_facts` (FR-190, FR-191, FR-196 … FR-199)

**Files:** `src/engine/layout_facts.py`, `src/engine/registry.py`, `src/engine/run.py`,
`tests/engine/test_layout_facts.py`

- `layout_facts` requires `products` and `store_layout`, with the rule-level reason
  `layout_all_rejected`.
- It publishes:
  - each fixture with its dates;
  - departments on no fixture;
  - products without a width, counted both ways FR-190 describes;
  - rejected entries;
  - the unplanned lists: "no sale or delivery in the window", "count zero or below", "stock
    unknown".
- It is `value_policy: none`, and not admitted.

**Done when:** AC-172 and AC-173 (the layout halves), AC-176 (the lists) and AC-186 (its "stock
unknown") pass.

### Task 8.3: `shelf_plan` (FR-181 … FR-189, FR-192, FR-193)

**Files:** `src/engine/shelf_plan.py`, `src/engine/model.py`, `src/engine/registry.py`,
`src/engine/publish.py`, `schemas/dashboard.schema.json`, `configs/policy.yaml`,
`src/engine/policy.py`, `tests/engine/test_shelf_plan.py`

- It requires `products`, `store_layout` and `sales_daily`. Its rule-level reasons are
  `layout_all_rejected`, `no_evidence_window` and `stale_daily_sales` (by F8's
  `order.freshness_days`).
- Planned products come from `order_evidence.stocks` over F8's window, and demand from
  `product_evidence` (INV-085).
- Packing:
  - first facings shelf by shelf, known earnings first, from eye level down (FR-183);
  - an over-full fixture gets no plan (FR-184);
  - extra facings only where every size is known, greedy by the next facing's earnings per
    centimetre at the policy elasticity, up to the cap (FR-185, FR-186);
  - every rule obeyed, or the fixture stopped with the rule named (FR-188).
- Each fixture's plan is one `shelf.plan` entry (ADR-038 Decisions 1–3):
  - `SIGNAL_FAMILIES` gains `shelf.plan`;
  - `entry_id` takes the variant `fixture|plan date`, with no barcode;
  - the schema admits `arrange_shelf` and null barcode, name and department, for that family
    only.
- The plan publishes the elasticity it used and why (FR-189, FR-206). Until Task 8.5 that is
  the policy value, "his own is not yet measured".
- The publisher's money guard covers all three capabilities (INV-087).

**Done when:**
- AC-174 … AC-181, AC-185 and AC-187 pass on a fixture shop, and so does AC-186's half on
  facings: one each in a department the evidence does not itemise, with demand unknown.
- SCN-161's two shelves, of 100 cm and 90 cm, pack as stated.

### Task 8.4: The arrangement record (FR-201; ADR-038 Decisions 4, 5, 9)

**Files:** `src/owner/ownerState.js`, `src/owner/__tests__/ownerState.test.js`,
`src/owner/__tests__/ownerStateContract.test.js`, `tests/fixtures/owner_state_firestore_contract.json`
(regenerated by `UPDATE_CONTRACT_FIXTURE=1`), `src/owner_state/model.py`,
`tests/owner_state/test_firestore_contract.py`

- `recordOutcome` gains a `shelf.plan` branch. Its snapshot carries:
  - `barcode: null` and `fixture`;
  - `plan_date` and `plan_window`;
  - `arranged_on`, the device's calendar day;
  - `placements`.
- On an entry already acted, it changes nothing: the first `at` and `arranged_on` stay.
  `clearOutcome` is the undo.
- The contract test records one `shelf.plan` outcome through the real `recordOutcome`, and
  the Python side reads it back.

**Done when:** a second press leaves the record byte-identical, undo removes it, and both sides of
the contract pass. The team account's guard is App.jsx's `readOnly` and `canWriteOwnerState`, and
Task 8.9 tests it on the page.

### Task 8.5: The planogram world, `shelf_measurement`, and the plan using it (FR-202 … FR-209)

**Files:** `src/engine/order_evidence.py` (the shared window check), `src/engine/shelf_measurement.py`,
`src/engine/registry.py`, `src/engine/run.py`, `src/engine/shelf_plan.py`, `src/engine/policy.py`,
`configs/policy.yaml`, `schemas/dashboard.schema.json`, `tests/fixtures/shelf_signals/build.py`,
`tests/engine/test_shelf_measurement.py`

- **The window check is moved, not copied.** `window_between(first, last, report_days, policy)`
  holds FR-144's checks, and `evidence_window` calls it. F8's suites pass unchanged.
- **The capability.** It requires `products`, `store_layout` and `sales_daily`. Its rule-level
  reasons are `layout_all_rejected`, `owner_state_unavailable` and `no_arrangement_recorded`. It
  runs before `shelf_plan`.
- **Arrangements.** It reads the `acted` outcomes of `shelf.plan` from the pulled owner state.
  An arrangement is not measurable when its history is too short, or when its fixture was
  rearranged again inside its windows.
- **Windows and eligibility.**
  - The before window is the span that ends the day before the plan's window begins.
  - The after window is the span that starts the day after `arranged_on`.
  - A product is measured only if it sold in the plan's window (FR-204).
  - A comparison product enters each arrangement it serves as a separate unit, so its units may
    count in several arrangements.
- **The fit.** FR-205's Poisson regression, with a term per product and arrangement, is fitted
  in its conditional form:
  - Given a product's units over both windows, its after units are binomial.
  - Their log-odds are: the offset log(after report days ÷ before report days), counted for that
    product as `product_evidence` counts them; plus the arrangement's window term; plus the
    arranged, facing and eye-level terms.
  - The product terms cancel, so the fit is a logistic regression with one intercept per
    arrangement. For Poisson this gives the same estimates as the full fit (Hausman, Hall and
    Griliches, 1984).
  - A product that sold nothing in both windows carries no information and drops out, as it
    would in the full fit.
  - The fit is iteratively reweighted least squares, in numpy.
- **Per-product change (FR-203).** A product's after ÷ before, each per report day, divided by
  the exponent of its arrangement's window term.
- **Bootstrap.**
  - Whole fixtures are resampled with the policy seed. A fixture drawn twice enters as two
    clusters, with fresh unit ids.
  - A draw that leaves an arrangement without comparison products drops that arrangement. A
    draw with no arrangement left, or with no variation in facings, is drawn again.
  - The eye-level term is kept or dropped once, on the full sample.
  - The interval is the policy level's percentile interval.
- **Placebo (FR-209).** It uses two earlier windows the same distance apart, tests both terms, and
  is held to the same minimums. With too few arrangements, it is "not run".
- **The plan.** `shelf_plan` reads the store elasticity, and uses it only when it is "measured",
  between 0 and 1, and its placebo passed. Otherwise it uses the policy value and says which
  and why (FR-206).
- **The planogram world.** `tests/fixtures/shelf_signals/build.py` builds a test shop:
  - at least 220 report days;
  - at least 14 fixtures;
  - arrangements staggered so that each keeps comparison fixtures throughout its span.

  Its records take the contract fixture's shape (Task 8.4), so they are the browser's. It has
  four variants:
  - **known:** sales built with a known elasticity, so AC-192 can check the interval holds it;
  - **drifting:** the later-arranged products are already moving apart, so the placebo's
    arranged term fails (AC-197);
  - **rising:** the products given more space were already rising, so the placebo's facing
    term fails (AC-197);
  - **short:** too few arrangements have the history for a placebo, so it is "not run"
    (AC-197).

**Done when:**
- AC-191 … AC-198 pass on the world.
- F8's suites pass unchanged.
- `npm run figures` reproduces the measurement and the plan from the same inputs (NFR-073).
- The new steps' times are measured, on the world and on YomYom's data, and recorded in the pull
  request. Neither grows with the market history (NFR-072, NFR-076).

### Task 8.6: The probe (§20)

**Files:** `scripts/check_order_signals.py`, `scripts/check_v1_signals.py`, `tests/test_check_v1_signals.py`

- `check:order-signals` gains F12-S1 §20's cases over the planogram world:
  - it withholds the daily reports, the layout file, one width, the arrangement records and the
    owner-state pull;
  - separately, it arranges every fixture.

  It reads the published artefact only.
- `PROBED_ELSEWHERE` lists `store_layout`, with the probe's word for it.
- The probe's added time is measured. Each engine run fits up to 2,000 times (the bootstrap and
  its placebo). If the probe adds more than two minutes to the nightly, it runs with fewer draws.
  That changes the probe's world, never the store's policy.

**Done when:** `npm run check:signals` passes, and catches each case when its guard is removed by
hand.

### Task 8.7: The marked example (FR-200, D-31)

**Files:** `scripts/build_shelf_example.py`, `public/examples/shelf-plan-example.json`,
`src/lib/dataAdapters/loadShelfExample.js`, `tests/test_shelf_example.py`

The example is built as Reorder's is:
- from the planogram world, in print mode;
- into `public/examples/`, which no engine step, loader other than its own, probe or
  measurement reads;
- read only through `loadShelfExample.js`.

**Done when:** the file is what the engine builds today. `tests/test_shelf_example.py` asserts it,
and asserts that only its loader, its builder, its page and their tests name it, as
`test_order_example.py` does for Reorder's. A store copy keeps it.

### Task 8.8: Mockups for the owner's approval (C-75)

**Files:** `docs/reviews/F12-screens-mockups.md` (the mockups, and his answer with its date)

What is shown, in Hebrew and Arabic, from Task 8.7's example:
- **Store layout.** Fixtures and shelves with their dates; what is missing; the rejected entries.
- **Shelf plan, filled.** Per fixture:
  - its shelves, with products and facings;
  - the unplaced lists, with their reasons;
  - the conditions, including the elasticity used and why;
  - "I've arranged this shelf", its warning while a measurement runs, and undo.
- **The measurement:**
  - its windows;
  - per-product changes, with no verdict;
  - the store elasticity, with its interval and verdict;
  - the placebo;
  - "N report days to go".
- **Waiting.** Each reason in his words; the example under its banner.
- **The team account's read-only view** (ADR-029).

Present them, and **stop until he approves.** Record his answer with its date.

### Task 8.9: The two pages (FR-191, FR-194, FR-195, FR-200, FR-201; NFR-074)

**Files:** `src/pages/StoreLayoutPage.jsx`, `src/pages/ShelfPlanPage.jsx`, `src/App.jsx` (out of
`AWAITING`), `src/surface/compose.js` (out of `NOT_YET_SHOWN`), `src/lib/i18n/dictionaries/*`,
`src/pages/__tests__/`, `e2e/`

Built against the approved mockups. Each page reads:
- the artefact, through `loadDashboard.js`;
- the example, through `loadShelfExample.js`, only while `shelf_plan` is unavailable;
- this device's own arrangement record, until the nightly has published it (ADR-038
  Decision 6).

There is no arithmetic in the browser (ADR-001).

**Done when:**
- AC-172, AC-173, AC-182, AC-189 and AC-190 pass in the browser, including the team account's
  press writing nothing.
- The e2e invariants pass in three languages on a phone (NFR-074).
- Every other page is byte-identical by Task 8.0's screenshot method.

## Pull requests

1. **Engine and record:** Tasks 8.0 … 8.5. The proof is YomYom's print-mode artefact, unchanged
   in every existing capability, with three new ones, each `no_store_layout`.
2. **Probe and example:** Tasks 8.6 and 8.7.
3. **Pages:** Task 8.9, after Task 8.8's approval.

## Checkpoint 8

- Tasks 8.0 … 8.7 are merged, and `check:signals` covers all three capabilities.
- On real data, all three are published `unavailable` with `no_store_layout`, and every other
  capability's output is unchanged.
- The mockups are approved with the date recorded (Task 8.8), and the pages are built and pass
  (Task 8.9).
- The provisional values above are in `configs/policy.yaml` as approved, and published.
