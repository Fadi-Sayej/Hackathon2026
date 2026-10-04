---
ID: PLAN-PHASE-8
Title: Phase 8 — V4, F12 Planogram (F12-S1)
Status: Ready for review
Owner: smartshelf-architect
Parent: [Implementation plan](plan.md)
Inputs: [docs/features/F12-planogram/specs/F12-S1-planogram.md (Approved 2026-10-04), ADR-037 and ADR-038 (Accepted 2026-10-04), ADR-009, ADR-014, ADR-016, ADR-029, ADR-030, ADR-036, D-29, D-30, D-31, src/engine/order_evidence.py, src/engine/store_facts.py, src/engine/registry.py, src/engine/model.py, src/engine/publish.py, src/common/store.py, src/owner/ownerState.js, src/App.jsx, scripts/check_order_signals.py, scripts/build_order_example.py]
Updated: 2026-10-04
---

# Phase 8 — V4, F12 Planogram

**Goal.** Build F12-S1:
- a committed layout file (ADR-037);
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
  days. Task 8.5 moves those checks out of `evidence_window` into one function that both call,
  never a second copy.
- **One "he stocks" and one demand.** `shelf_plan` calls `order_evidence.stocks` and
  `order_evidence.product_evidence`. It never re-derives them (INV-085).
- **No ₪ anywhere.** The publisher refuses a value, or any money-named field other than a placed
  product's `margin_per_sale`, in all three capabilities (INV-087).
- **No invented store data.** The fixture worlds are test shops under `tests/fixtures/`. The
  example is built from one of them, under D-31's banner. No task writes a layout file, a sales
  report or an arrangement for a real store (D-23, CLAUDE.md rule 7).
- **Nothing the owner sees changes before Task 8.8's mockups are approved** (F12-S1 C-75). Until
  then the two pages stay awaiting shells.
- **No new dependency.** The regression is a logistic fit in numpy (Task 8.5). `statsmodels` and
  `scipy` are not installed, and the nightly does not need them.
- **Determinism.** The bootstrap's draws use a seed fixed in policy, so print mode and
  `npm run figures` reproduce the artefact (NFR-073).
- **Actions minutes.** Three pull requests, each tested locally first (the suites, lint, build
  and bundle, e2e, `check:signals`) and pushed once.

## Provisional values, proposed for the owner's approval

F12-S1 leaves these to the plan (OQ-1204, OQ-1207). They go into `configs/policy.yaml` under
`shelf:`, and the artefact publishes every one.

| Value | Proposed | Why |
|---|---|---|
| Space elasticity, until his own is measured | 0.17 | Eisend's mean over 1,268 estimates (F12-S1 §23) |
| Facings cap per product | 4 | A judgement, not research. At 0.17 the 2nd facing adds 12.5% to a product's sales, the 3rd 7.1%, the 4th 5.0%, and a 5th would add 3.9%. Past 4, the length does more for another product. His "at least N" rule overrides it |
| Window length and minimum report days | 28 and 21, every week holding one | F8's own values (`order.window_days`, `order.min_report_days`), so the measurement uses the windows the plan does |
| Interval level | 95% | The level the repository's other intervals use (`wilson_interval`, `sales_movement`) |
| Minimum arrangements for a store elasticity | 8 | A bootstrap over fewer whole fixtures is too rough to trust. Eight is a floor, not a guarantee |
| Minimum arranged products | 40 | About five per arrangement |
| Bootstrap draws | 1,000 | Enough for a stable 95% interval; seconds of compute |

## Proposed for the owner, from earlier answers

- **The example's source (D-31).** It is built like Reorder's: by `scripts/build_shelf_example.py`,
  in print mode, from Task 8.6's fixture world, into `public/examples/shelf-plan-example.json`.
- **The photo-reading test (OQ-1202, "yes why not").** It runs after this phase, on the next
  store's first shelf photographs. A model's reading of each facing width is compared with the
  team's own reading of the same photographs. Nothing in this phase waits on it, because there
  is no store to photograph now (D-23).

## Tasks, in dependency order

| Task | Depends on | Delivers |
|---|---|---|
| 8.1 | — | The layout file and its loader |
| 8.2 | 8.1 | `layout_facts` |
| 8.3 | 8.2 | `shelf_plan` and its `shelf.plan` entries |
| 8.4 | — | The arrangement record in the browser |
| 8.5 | 8.3, 8.4 | `shelf_measurement`, and the plan reading its elasticity |
| 8.6 | 8.5 | The fixture worlds and the probe |
| 8.7 | 8.6 | The marked example |
| 8.8 | 8.7 | Mockups for the owner's approval |
| 8.9 | 8.8 approved | The two pages |

### Task 8.1: The layout file and its loader (ADR-037; FR-178 … FR-180, FR-199)

**Files:** `src/engine/store_layout.py`, `configs/store_layout.yaml` (empty), `src/engine/inputs.py`,
`src/engine/registry.py`, `src/common/store.py`, `scripts/check_store.py`,
`tests/engine/test_store_layout.py`

- The loader follows `store_facts.load_store_facts`. It validates the input, never repairs it,
  rejects entries by name with a reason, and checks provenance by kind (`measured_by` /
  `measured_on`, or `stated_by` / `stated_on` / `recorded_by`). It returns the facts and the
  rejections.
- It rejects:
  - two eye-level shelves on one fixture;
  - a rule naming a product outside the catalogue;
  - a department on two fixtures with no "keep on" rule;
  - a product of a split department that no rule names;
  - a width, length or facing count that is not a positive whole number;
  - a rule outside FR-188's five.
- Current facings and their shelf are dated measurements (ADR-037).
- `EngineInputs.store_layout` is None when the file is absent. An empty file is a file.
  `INPUT_REASONS["store_layout"] = "no_store_layout"`.
- `configs/store_layout.yaml` joins `STARTS_EMPTY`, and `check:store` names it when it is
  missing.

**Done when:** AC-184 and AC-188 pass, and YomYom's print-mode artefact is unchanged apart from the
three new capabilities, each `no_store_layout`.

### Task 8.2: `layout_facts` (FR-190, FR-191, FR-196 … FR-199)

**Files:** `src/engine/layout_facts.py`, `src/engine/registry.py`, `src/engine/run.py`,
`tests/engine/test_layout_facts.py`

- `layout_facts` requires `products` and `store_layout`, with the rule-level reason
  `layout_all_rejected`.
- It publishes:
  - each fixture with its dates;
  - departments on no fixture;
  - products without a width (FR-190's two counts, with and without F8's window);
  - the rejected entries;
  - the unplanned lists: "no sale or delivery in the window", "count zero or below" and
    "stock unknown".
- It is `value_policy: none` and not admitted.

**Done when:** AC-172 and AC-173 (their layout halves), AC-176 (its lists) and AC-186 (its
"stock unknown") pass.

### Task 8.3: `shelf_plan` (FR-181 … FR-189, FR-192, FR-193)

**Files:** `src/engine/shelf_plan.py`, `src/engine/model.py`, `src/engine/registry.py`,
`src/engine/publish.py`, `schemas/dashboard.schema.json`, `configs/policy.yaml`,
`src/engine/policy.py`, `tests/engine/test_shelf_plan.py`

- It requires `products`, `store_layout` and `sales_daily`. Its rule-level reasons are
  `layout_all_rejected`, `no_evidence_window` and `stale_daily_sales`, by F8's
  `order_freshness_days`.
- Planned products come from `order_evidence.stocks` over F8's window. Demand comes from
  `product_evidence` (INV-085).
- The packing:
  - first facings shelf by shelf, known earnings first, from eye level down (FR-183);
  - an over-full fixture gets no plan (FR-184);
  - extra facings only where every size is known, greedy by the next facing's earnings per
    centimetre at the policy elasticity, up to the cap (FR-185, FR-186);
  - rules obeyed, or the fixture stopped with the rule named (FR-188).
- Each fixture's plan is one `shelf.plan` entry (ADR-038 Decisions 1–3). `SIGNAL_FAMILIES` gains
  `shelf.plan`. `entry_id` takes the variant `fixture|plan date` with no barcode. The schema
  admits `arrange_shelf`, and nulls for barcode, name and department, for that family only.
- The plan publishes the elasticity it used and why (FR-189, FR-206). Until Task 8.5 it is the
  policy value, "his own is not yet measured".
- The publisher's money guard covers all three capabilities (INV-087).

**Done when:** AC-174 … AC-181, AC-185 and AC-187 pass on a fixture shop, and SCN-161's two
shelves of 100 cm and 90 cm pack as stated.

### Task 8.4: The arrangement record (FR-201; ADR-038 Decisions 4–6, 9)

**Files:** `src/owner/ownerState.js`, `src/owner/__tests__/ownerState.test.js`,
`src/owner/__tests__/ownerStateContract.test.js`, `tests/fixtures/owner_state_firestore_contract.json`
(regenerated), `src/owner_state/model.py`, `tests/owner_state/test_firestore_contract.py`

- `recordOutcome` gains a `shelf.plan` branch. The snapshot carries `barcode: null`, `fixture`,
  `plan_date`, `plan_window`, `arranged_on` (the device's calendar day) and `placements`.
- On an entry already acted it changes nothing, and keeps the first `at` and `arranged_on`.
  `clearOutcome` is the undo.
- The contract test records one `shelf.plan` outcome through the real `recordOutcome`, and the
  fixture is regenerated by its own command. The Python side reads it back.

**Done when:** a second press leaves the record byte-identical, undo removes it, a team account's
press writes nothing, and both sides of the contract pass.

### Task 8.5: `shelf_measurement`, and the plan using it (FR-202 … FR-209)

**Files:** `src/engine/order_evidence.py` (the shared window check), `src/engine/shelf_measurement.py`,
`src/engine/registry.py`, `src/engine/run.py`, `src/engine/shelf_plan.py`, `configs/policy.yaml`,
`tests/engine/test_shelf_measurement.py`

- **The window check is moved, not copied.** `window_between(first, last, report_days, policy)`
  holds FR-144's checks, and `evidence_window` calls it. All of F8's tests pass unchanged.
- **The capability.** It requires `products`, `store_layout` and `sales_daily`. Its rule-level
  reasons are `layout_all_rejected`, `owner_state_unavailable` and `no_arrangement_recorded`.
  It runs before `shelf_plan`.
- **Arrangements.** It reads the `acted` outcomes of `shelf.plan` from the pulled owner state.
  An arrangement is not measurable when:
  - its history is too short;
  - its fixture was rearranged again inside its windows.
- **Windows and eligibility.** The before window is the span ending the day before the plan's
  window begins. The after window is the span starting the day after `arranged_on`. A product
  is measured only if it sold in the plan's window (FR-204).
- **The fit.** FR-205's Poisson regression, with a term per product and arrangement, is fitted
  in its conditional form. Given a product's units over both windows, its after units are
  binomial, with a log-odds of:
  - the arrangement's window term;
  - plus the arranged, facing and eye-level terms.

  The product terms cancel, so the fit is a logistic regression with one intercept per
  arrangement. For Poisson this gives the same estimates as the full fit (Hausman, Hall and
  Griliches, 1984). A product that sold nothing in both windows carries no information and
  drops out, as in the full fit. The fit is iteratively reweighted least squares in numpy.
- **Per-product change (FR-203).** after ÷ before, per report day, divided by the exponent of
  the arrangement's window term.
- **Bootstrap.** Whole fixtures are resampled with the policy seed. A draw that leaves an
  arrangement without comparison drops that arrangement, and a draw with no arrangement, or no
  variation in facings, is drawn again. The interval is the policy level's percentile interval.
  The eye-level term is kept or dropped once, on the full sample.
- **Placebo (FR-209).** Two earlier windows, the same distance apart, with both terms tested and
  the same minimums. Too few arrangements means "not run".
- **The plan.** `shelf_plan` reads the store elasticity. It uses it only when its verdict is
  measured, it lies between 0 and 1, and the placebo passed. Otherwise it uses the policy value,
  and says which and why (FR-206).

**Done when:** AC-191 … AC-198 pass on Task 8.6's worlds; F8's suites pass unchanged; print mode
reproduces the measurement.

### Task 8.6: The fixture worlds and the probe (§20)

**Files:** `tests/fixtures/shelf_signals/build.py`, `scripts/check_order_signals.py`,
`scripts/check_v1_signals.py`, `tests/test_check_v1_signals.py`

- **A planogram world.** It has about 150 report days, eight to ten fixtures, a layout file and
  arrangements. Their records come from the contract fixture's shape (Task 8.4), so they are the
  browser's. It has three variants:
  - **known:** sales built with a known elasticity, so AC-192 can check the interval holds it;
  - **drifting:** later-arranged products already moving apart, so the placebo's arranged term
    fails (AC-197);
  - **rising:** products given more space were already rising, so the placebo's facing term
    fails (AC-197).
- **The probe.** `check:order-signals` gains the cases in the spec's §20:
  - it withholds the daily reports, the layout file, one width, the arrangement records and the
    owner-state pull;
  - separately, it arranges every fixture.

  It reads the published artefact only.
- **`PROBED_ELSEWHERE`** lists `store_layout`, with the probe's word for it.

**Done when:** `npm run check:signals` passes and catches each case when its guard is removed by
hand.

### Task 8.7: The marked example (FR-200, D-31)

**Files:** `scripts/build_shelf_example.py`, `public/examples/shelf-plan-example.json`

The example is built as `build_order_example.py` builds Reorder's: from the planogram world in
print mode, into `public/examples/`, which no engine step, loader, probe or measurement reads.

**Done when:** the file is built by its command, and a test asserts that nothing under `src/engine`,
`scripts/check_*` or `src/lib/dataAdapters` reads it.

### Task 8.8: Mockups for the owner's approval (C-75)

**Files:** `docs/reviews/F12-screens-mockups.md` (the mockups, and his answer with its date)

What is shown, in Hebrew and Arabic, from Task 8.7's example:
- **Store layout.** Fixtures and shelves, with their dates; what is missing; rejected entries.
- **Shelf plan, filled.** For each fixture:
  - its shelves, with products and facings;
  - the unplaced lists, with their reasons;
  - the conditions, including the elasticity used and why;
  - "I've arranged this shelf", its warning while a measurement runs, and undo.
- **The measurement.** Its windows; per-product changes with no verdict; the store elasticity
  with its interval and verdict; the placebo; "N report days to go".
- **Waiting.** Each reason in his words, and the example under its banner.
- **The team account's read-only view** (ADR-029).

Present them, and **stop until he approves.** Record his answer and its date.

### Task 8.9: The two pages (FR-191, FR-194, FR-195, FR-200, FR-201)

**Files:** `src/pages/StoreLayoutPage.jsx`, `src/pages/ShelfPlanPage.jsx`, `src/App.jsx` (out of
`AWAITING`), `src/lib/i18n/*` (he, ar, en), `src/pages/__tests__/`, `e2e/`

Built against the approved mockups. Each page reads `loadDashboard.js` only. The arrangement
shown is the published one (ADR-038 Decision 6). There is no arithmetic in the browser
(ADR-001).

**Done when:** AC-172, AC-173, AC-182, AC-189 and AC-190 pass in the browser; the e2e invariants
pass in three languages on a phone; and every other page is byte-identical by the
126-screenshot harness.

## Pull requests

1. **Engine and record:** Tasks 8.1 … 8.5. The proof is YomYom's print-mode artefact, unchanged
   apart from three new capabilities, each `no_store_layout`.
2. **Probe and example:** Tasks 8.6 and 8.7.
3. **Pages:** Task 8.9, after Task 8.8's approval.

## Checkpoint 8

- Tasks 8.1 … 8.7 are merged, and `check:signals` covers all three capabilities.
- On real data, all three are published `unavailable` with `no_store_layout`. Every other
  capability's output is unchanged.
- The mockups are approved, with the date recorded (Task 8.8). The pages are built and pass
  (Task 8.9).
- The provisional values above are in `configs/policy.yaml` and published, as approved.
