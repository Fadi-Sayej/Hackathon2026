---
ID: PLAN-PHASE-5
Title: Phase 5 — V2, F8 Order Quantity (F8-S1)
Status: Ready for review
Owner: smartshelf-architect
Parent: [Implementation plan](plan.md)
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md (Approved 2026-09-25), ADR-030, ADR-031, ADR-032, ADR-033, ADR-034, ADR-035 (Accepted 2026-09-26), docs/architecture/system-design.md §10.1 §19 §21, CLAUDE.md, .claude/SKILLS/HANDOVER.md]
Updated: 2026-09-26
---

# Phase 5 — V2, F8 Order Quantity

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans, task by task. Each task's `Files:` block is
> the engineer's scope boundary. A file not listed there is not the task's to change.

**Goal.** Build F8-S1: per-product order suggestions on the existing Reorder entry, from his
own per-day sales, with these rules:
- a model-picked boost when the nearby market runs out;
- a shelf-life cap from his stated shelf lives;
- stock subtracted only when the count is recent and checks out;
- approvals listed on Approved orders;
- one-time disagreement questions.

**It publishes nothing until the store owner supplies the inputs** (F8-S1 OQ-903, OQ-904,
OQ-908). Every task must therefore be proven on fixtures, and the capability must say
precisely what it waits for on real data.

**Architecture.** There are three new engine capabilities, each separately unavailable
(ADR-014):

| Capability | Needs | ADR |
|---|---|---|
| `market_running_out` | the delivery-catalogue presence series | ADR-031 |
| `market_boost` | running out and the model | ADR-032, ADR-035 |
| `order_quantity` | per-day sales and the store facts | ADR-030, ADR-033, ADR-034 |

- **Inputs:** per-day reports (ADR-030) and `configs/store_facts.yaml` (ADR-033).
- **The boost** is a model's pick, sealed as a daily snapshot and replayed in print mode
  (ADR-032, ADR-035).
- **The disagreement** is a second fact kind in the existing owner-question population
  (ADR-034).
- **The browser** renders the Reorder and Approved orders entries, and computes nothing
  (ADR-001).

## Phase constraints

These apply on top of the index's Global Constraints.

- **No figure is ever guessed.**
  - Order days, shelf lives, deliveries and missing days are either stated or recorded as
    unknown, never defaulted.
  - `None` is never `0` (F8-S1 INV-071, INV-072).
  - `configs/shelf_life.yaml` is not an input (FR-152).
- **No quantity from a report longer than a day** (INV-070). The monthly tables are never
  read by F8.
- **`order_quantity` carries no value.** Its `value_policy` is `none`: no ₪ on any entry,
  export or total (INV-069).
- **The model moves one number** (INV-079). A pick outside 0–25% gives no boost, never a
  clipped one. Print mode never calls the model (ADR-035).
- **One new permanent family, `order.suggestion`, and one new question fact,
  `market_disagreement`.** Neither is ever renamed or reused (ADR-034). The index's "eleven
  families" becomes twelve for V2.
- **Screens first.** Nothing the owner sees is built before the repository owner has approved
  its mockups (Task 5.13).

## Tasks, in dependency order

| Task | Depends on | Delivers |
|---|---|---|
| 5.0 | — | Policy values, three registry entries, the new family and fact |
| 5.1 | 5.0 | The per-day importer, and the `.gitignore` path for daily files |
| 5.2 | 5.1 | Per-day evidence in `load_inputs`, `vintages.sales_daily`, the degraded rule |
| 5.3 | 5.0 | The store facts file and its loader |
| 5.4 | 5.0 | `market_running_out` |
| 5.5 | 5.2 | The evidence math: window, moving, daily mean |
| 5.6 | 5.4, 5.5 | `market_boost`: the model call, the checks, the sealed snapshot |
| 5.7 | 5.5 | The quantity arithmetic: stock now, net and gross, the cap, rounding |
| 5.8 | 5.3, 5.6, 5.7 | `order_quantity`: population, reasons, entries, identity, facts |
| 5.9 | 5.4, 5.5 | The disagreement question |
| 5.10 | 5.8, 5.9 | Schema and publisher |
| 5.11 | 5.6, 5.10 | The nightly workflow |
| 5.12 | 5.10 | Boundary probes (rule 12) |
| 5.13 | 5.10 | Mockups for the repository owner's approval |
| 5.14 | 5.13 approved | The Reorder and Approved orders pages |
| 5.15 | 5.13 approved | The disagreement question in the panel |

5.3 and 5.4 are independent of 5.1 and 5.2 and of each other.

---

### Task 5.0: Policy, registry, family and fact

**Files:**
- Modify: `configs/policy.yaml`, `src/engine/policy.py`, `src/engine/registry.py`,
  `src/engine/model.py`
- Test: `tests/engine/test_policy.py`, `tests/engine/test_registry.py`,
  `tests/engine/test_model.py`, `tests/engine/test_unavailable_reasons.py`

**Interfaces:**
- `policy.order`:
  - `window_days: 28`, `min_report_days: 21`, `freshness_days: 7`;
  - `max_count_age_days: 7`.

  All are provisional, citing F8-S1 OQ-906.
- `policy.running_out`:
  - `prior_days: 14`, `min_listed: 10`;
  - `min_absent: 2`, `max_absent: 7`;
  - `catalogue_change_pct: 10`, `thin_collection_ratio: 0.5`;
  - `signal_min_usable: 10`, `signal_max_age_days: 2`.

  All come from ADR-031.
- `policy.boost`:
  - `model: claude-sonnet-5`, `max_pct: 25`, `request_ceiling: 200`;
  - `prompt: configs/prompts/market_boost.v1.md`.

  These come from ADR-032 and D-21.
- The registry gains `market_running_out`, `market_boost` and `order_quantity`.
  - Each has `value_policy: none` and `admitted: False`: none is a daily-surface entry.
  - Each declares its `requires`, as the Architecture table sets out.
- New unavailable reasons: `no_daily_sales`, `stale_daily_sales`, `no_store_facts`,
  `market_signal_thin`, `market_signal_stale`, `no_boost_model`, `no_boost_key`.
- `SIGNAL_FAMILIES` gains `order.suggestion`, and `QUESTION_FACTS` gains
  `market_disagreement`.

- [ ] **Step 1:** Write failing tests. Policy loads every new key, and refuses a missing or
  out-of-range one: `max_pct` must lie in [0, 100], `min_listed` ≤ `prior_days`, and so on.
  The registry holds the three ids with the stated `requires` and `value_policy`. The family
  and fact are present and frozen. Every new reason is reachable (the existing guard in
  `test_unavailable_reasons.py`).
- [ ] **Step 2:** Add the policy keys and their loader validation, then the registry
  entries, the family and the fact.
- [ ] **Step 3:** Run `npm run test:py`: green. Commit.

---

### Task 5.1: The per-day importer, and the daily files' path (ADR-030)

**Files:**
- Create: `src/internal_pos/sales_daily_importer.py`
- Modify: `.gitignore`, and CLAUDE.md rule 6 (its second exception)
- Test: `tests/internal_pos/test_sales_daily_importer.py`, `tests/test_gitignore_daily_sales.py`

**Interfaces:**
- `import_sales_daily(directory, *, silver_dir) -> dict` writes
  `silver_pos/sales_daily.parquet`: `barcode, day, units, receipts`.
  - `receipts` is **null when the file has no `כניסות מלאי` column**.
  - It returns `{report_days, failed_files, deliveries_reported: {day: bool}}`.
- The day comes from the file name: `דוח מכירות יום YYYY-MM-DD.csv`. The importer reuses the
  monthly importer's column map, and its duplicate rule (ADR-019).
- In `.gitignore`, `data/internal/raw_pos/` becomes:
  - `data/internal/raw_pos/*`
  - `!data/internal/raw_pos/yomyom/`
  - `data/internal/raw_pos/yomyom/*`
  - `!data/internal/raw_pos/yomyom/sales_daily/`

  Every other path stays ignored.

- [ ] **Step 1:** Write failing tests with fixture CSVs:
  - the day is read from the name, and a bad name is a failed file;
  - a product absent from a file gets no row;
  - receipts are null when the column is missing, never 0;
  - a duplicate conflicting line is excluded, as in ADR-019;
  - an unparseable file is listed and never read as a zero day.
- [ ] **Step 2:** Write the `.gitignore` test. `git check-ignore` must **not** match
  `data/internal/raw_pos/yomyom/sales_daily/x.csv`, and **must** still match
  `data/internal/raw_pos/yomyom/inventory.csv` and `data/internal/raw_pos/other/x.csv`.
  Check against a scratch copy, as in ADR-030.
- [ ] **Step 3:** Implement the importer and the `.gitignore` change. Add rule 6's exception
  in CLAUDE.md, beside `data/internal/snapshots/`, in one sentence.
- [ ] **Step 4:** Tests green. Commit.

---

### Task 5.2: Per-day evidence in the run, and its vintage (ADR-030 Decisions 3–4, ADR-017)

**Files:**
- Modify: `src/engine/inputs.py`, `src/engine/run.py`
- Test: `tests/engine/test_inputs.py`, `tests/engine/test_run.py`

**Interfaces:**
- A run step `sales_daily_import`, after `sales_import`.
- `inputs.sales_daily`: per-product per-day rows, `None` when no daily file exists.
- `vintages.sales_daily`:
  - `{first_day, last_day, report_days, missing_days, deliveries_missing_days}`;
  - `missing_days` covers the window plus the freshness limit;
  - all of it is derived from the files present, with no memory of earlier runs (ADR-004).
- **The run verdict** is `degraded` only when daily files exist and `last_day` is more than
  `order.freshness_days` before the run. Before the first file there is no degradation.

- [ ] **Step 1:** Write failing tests for the verdict:
  - no daily files: the run is `ok`, and `order_quantity` is unavailable with
    `no_daily_sales`;
  - files up to five days ago: `ok`;
  - files ending nine days ago: `degraded`, and `order_quantity` is unavailable with
    `stale_daily_sales`;
  - a weekly batch leaves the six nights between batches `ok`.
- [ ] **Step 2:** Implement, wiring the importer from Task 5.1.
- [ ] **Step 3:** Run `npm run test:py`, then `npm run check:signals`, which must still pass:
  V1 is untouched. Commit.

---

### Task 5.3: The store facts (ADR-033)

**Files:**
- Create: `configs/store_facts.yaml`, `src/engine/store_facts.py`
- Modify: `src/engine/inputs.py`
- Test: `tests/engine/test_store_facts.py`

**Interfaces:**
- `configs/store_facts.yaml` holds **no departments**, only its header. The header documents
  each entry's form:
  - `order_schedule`: `weekdays` | `every_days` + `from` | `no_fixed_days`;
  - `shelf_life_days`: an integer ≥ 0 (`0` meaning less than a day) | `does_not_spoil`;
  - `stated_by: owner`, `stated_on`, `recorded_by: team`.

  **No value is filled in.** The team adds entries as the store owner states them (F8-S1
  OQ-903, OQ-908).
- `load_store_facts(path, catalogue_departments) -> StoreFacts` returns
  `{facts: {department: …}, rejected: [{department, reason}]}`.
  - A department with no entry is absent: never a default.
- `inputs.store_facts`.

- [ ] **Step 1:** Write failing tests:
  - each schedule form parses;
  - a malformed schedule is rejected, and so is an unknown department or a negative shelf
    life. A rejected entry is reported and never repaired;
  - `0` and `does_not_spoil` are distinct;
  - an empty file gives no facts, and no error.
- [ ] **Step 2:** Implement the loader, and wire it into `load_inputs`.
- [ ] **Step 3:** Tests green. Commit.

---

### Task 5.4: `market_running_out` (ADR-031)

**Files:**
- Create: `src/market/running_out.py`, `src/engine/market_running_out.py`
- Modify: `src/engine/inputs.py`, `src/engine/run.py` (the runner map)
- Test: `tests/test_running_out.py`, `tests/engine/test_market_running_out.py`

**Interfaces:**
- `running_out(series, market_store_ids, policy, on_day) -> {barcode: {stores_out,
  days_absent}}` is pure over `load_presence(source_id="delivery_catalog")`. It applies
  ADR-031's Decisions 1 to 3:
  - listed on 10 of the prior 14 usable days;
  - absent for 2 to 7 days;
  - listed-but-not-orderable counted as absent;
  - a catalogue-change day or thin-collection day at a store excludes absences that begin on
    it.
- `market_running_out` capability:
  - available per ADR-031 Decision 5, otherwise unavailable with `market_signal_thin` or
    `market_signal_stale`;
  - publishes `on_day`, the excluded store-days, and each product's facts;
  - covers only the D-18 market (the stores at or above the floor, the client excluded).

- [ ] **Step 1:** Write failing tests on synthetic series:
  - one-day and eight-day absences never count; two and seven do;
  - a store dropping more than 10% of its steady listings in a day excludes those
    absences;
  - a thin day is excluded;
  - a store below the floor never contributes.
- [ ] **Step 2:** Write a replay test on the committed snapshots. It skips when `data/` is
  absent, as `test_figures_cli` does. Wolt Market's 2026-08-31, 09-01 and 09-15 must be the
  only excluded store-days, and no night may exceed ADR-031's replayed range.
- [ ] **Step 3:** Implement. Tests green. Commit.

---

### Task 5.5: The evidence math (F8-S1 FR-143 … FR-146)

**Files:**
- Create: `src/engine/order_evidence.py`
- Test: `tests/engine/test_order_evidence.py`

**Interfaces:**
- `evidence_window(report_days, policy, run_at) -> Window | None` implements FR-144:
  - the 28 days ending on the latest report day;
  - at least 21 report days, and at least one in each 7-day block;
  - within 7 days of the run.
- `product_evidence(rows, window) -> {moving: bool, weekly_units: [4], daily_mean: float |
  None}`. The daily mean is units over report days. Missing days are left out, never zero.

- [ ] **Step 1:** Write failing tests:
  - a missing day is excluded from the mean;
  - 20 report days means no window, and so does a week with none;
  - a window ending eight days ago means no window;
  - "moving" requires a sale in each week;
  - a monthly row can never enter (INV-070).
- [ ] **Step 2:** Implement, as pure functions with no I/O.
- [ ] **Step 3:** Tests green. Commit.

---

### Task 5.6: `market_boost`: the model call, the checks, the sealed snapshot (ADR-032, ADR-035)

**Files:**
- Create: `src/engine/market_boost.py`, `configs/prompts/market_boost.v1.md`
- Modify: `src/engine/run.py` (the live step; print mode reads only)
- Test: `tests/engine/test_market_boost.py`

**Interfaces:**
- `build_request(product_facts) -> {payload, inputs_digest}`.
  - It uses only the published facts FR-164 names.
  - `inputs_digest` is the sha256 of the canonical JSON of those facts.
- `ask(payload, *, model, key) -> raw` is one HTTPS call to Anthropic's Messages API.
  - It uses the standard library's `urllib`, with no SDK and no new dependency, one retry
    and a timeout.
  - It sets no sampling parameter.
- `check(raw, max_pct) -> {accepted, boost_pct, reason, rejected_because}` checks in this
  order:
  - parse, then the range 0 to `max_pct`, with no clipping;
  - a reason containing any of the digits 0–9, ٠–٩ or ۰–۹ is withheld.
- The snapshot is `data/external/snapshots/<on_day>/boost_picks/picks.json` plus
  `_manifest.json`.
  - It follows `scripts/write_snapshot_manifest.py`'s conventions.
  - It is merge-never-replace: a same-day re-run asks only for products with no pick.
  - `<on_day>` is `market_running_out.on_day`.
- Requests go in a fixed order: units in the window, descending, then barcode. Products past
  `request_ceiling` get `ceiling_reached`.
- **In print mode the model is never called.** The snapshot is read, and a pick whose
  `inputs_digest` differs is not applied (ADR-035 Decision 4).

- [ ] **Step 1:** Write failing tests with a **fake transport**. No test may reach the
  network.
  - Accepted at 10; rejected at 40, −1, "abc" and on malformed JSON; never clipped.
  - A reason "sold 12 more" is withheld, and so is one written with Arabic-Indic digits.
  - The ceiling ordering is fixed.
  - A re-run adds without replacing.
  - Print mode makes zero transport calls, applies a matching digest and skips a mismatched
    one.
  - No key gives `no_boost_key`. A transport error makes the capability unavailable, and the
    run stays `ok`.
- [ ] **Step 2:** Write the prompt file. It says what the model is given, that it must return
  JSON with `boost_pct` from 0 to 25 and a reason of at most 160 characters with no numbers,
  and that it must not claim competitor sales volumes (F8-S1 §21).
- [ ] **Step 3:** Implement. Tests green. Commit.

---

### Task 5.7: The quantity arithmetic (F8-S1 FR-146 … FR-153)

**Files:**
- Create: `src/engine/order_arithmetic.py`
- Test: `tests/engine/test_order_arithmetic.py`

**Interfaces:**
- `next_order_day(schedule, run_date)` and `cycle_days(schedule, order_day)` cover weekdays,
  an interval from a date, and "no fixed days", which gives `None`.
- `stock_now(count, count_date, rows_since, run_date) -> float | None`.
  - It is `None` unless the count is at most 7 days old, and neither reconciliation nor
    hygiene flags it.
  - It also needs the product to have a row on every report day since the count, with
    deliveries reported that day (ADR-030 Decision 2).
  - The value is the count plus receipts less units, and a value below zero gives `None`.
- `stock_at_order_day(stock_now, adjusted_daily_mean, days_to_order_day)` is floored at 0.
- `quantity(adjusted_daily_mean, cycle_days, stock_at_order_day, shelf_life) -> {quantity |
  None, kind: net | gross, capped, reason}`.
  - An expectation below one unit gives no quantity.
  - The need rounds to the nearest unit, halves up; a quantity the cap sets rounds down.
  - A shelf life of 0 gives no quantity; `does_not_spoil` gives no cap.
  - A net zero is flagged as covered.

- [ ] **Step 1:** Write failing tests, one per spec scenario of arithmetic:
  - SCN-133 and SCN-134 on a Thursday for Sunday, net and gross;
  - SCN-138: a two-day shelf life caps the quantity, less stock;
  - SCN-139: a shelf life of 0;
  - SCN-147: a negative stock now;
  - SCN-149: less than one unit per cycle;
  - 1.14 a day stays 1, not 2;
  - an irregular Sunday/Wednesday schedule.
- [ ] **Step 2:** Implement, as pure functions.
- [ ] **Step 3:** Tests green. Commit.

---

### Task 5.8: `order_quantity`: population, reasons, entries, identity (FR-145 … FR-163, ADR-034)

**Files:**
- Create: `src/engine/order_quantity.py`
- Modify: `src/engine/run.py` (the runner map)
- Test: `tests/engine/test_order_quantity.py`

**Interfaces:**
- One entry per moving product with a quantity:
  - `signal_family: order.suggestion`, variant = the order day;
  - `entry_id = sha256("order.suggestion" | barcode | order_day)[:16]`;
  - no `value`.
- **Evidence (FR-154):**
  - the order schedule and the cycle's dates;
  - the window's dates and weekly units;
  - the daily mean, and the adjusted mean with its pick, reason and model, or why there is
    none;
  - the count, its date, whether it was used and why;
  - the deliveries and sales since the count, the stock now and the stock at the order day;
  - the shelf life, its source and whether it capped;
  - `kind: net | gross`;
  - `schedule_changed` when an owner outcome exists for a pending order day the schedule no
    longer has.
- **Per-department reasons for no quantity (FR-155, FR-156)**, one of:
  - `not_moving`;
  - `no_order_schedule` or `no_fixed_days`;
  - `no_shelf_life`;
  - `no_window`;
  - `below_one_per_cycle`;
  - `shelf_life_under_a_day`;
  - `cap_rounds_to_zero`;
  - `not_itemised`.
- `covered_by_stock`: a count of products. It is not money (INV-069).

- [ ] **Step 1:** Write failing tests:
  - SCN-132: only monthly reports gives the capability unavailable, `no_daily_sales`;
  - SCN-140 and SCN-146: missing store facts;
  - SCN-142: a department that is not itemised;
  - SCN-145: the id is stable on Friday and Saturday for a Sunday order, and new after it;
  - FR-162: no `value` and no ₪ field on any entry.
- [ ] **Step 2:** Implement over Tasks 5.3, 5.5, 5.6 and 5.7.
- [ ] **Step 3:** Tests green. Commit.

---

### Task 5.9: The disagreement question (FR-158, FR-159, ADR-034)

**Files:**
- Modify: `src/engine/owner_questions.py`
- Test: `tests/engine/test_owner_questions.py`

**Interfaces:**
- A second fact kind, `market_disagreement`.
  - `question_id = sha256("market_disagreement|" + barcode)[:16]`.
  - It is raised for a product he stocks (F8-S1 §5, "He stocks": a sale or delivery in the
    window, or, where not itemised, a latest count above 0) that is running out and not
    moving.
  - It is raised only when a window exists, except FR-156's case (SCN-148).
- **Its `why` carries only observed facts:** `stores_out`, `days_absent`, and `units_in_window`
  or `no_sales_row`.
- **The answer options are** shelf place, price, weak market here, and sells elsewhere (not
  through these reports).
- **Never re-raised once answered** (D-20, over FR-089). Revisable (FR-090).
- **Ordered after every question with money** (ADR-027), then by units in the window and by
  barcode. The global limit of three still holds (D-8).

- [ ] **Step 1:** Write failing tests:
  - SCN-141: raised once; answered, it stays retired even when the facts change;
  - SCN-148: no window gives none, except in a department that is not itemised;
  - the ordering follows the 11 money questions;
  - no `why` says "sells a lot" or "zero sales";
  - a withdrawn product is never asked about (FR-082 holds).
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** Tests green. Commit.

---

### Task 5.10: Schema and publisher

**Files:**
- Modify: `schemas/dashboard.schema.json`, `src/engine/publish.py`
- Test: `tests/engine/test_publish.py`

**Interfaces:**
- The schema admits:
  - the three capabilities;
  - `vintages.sales_daily`;
  - the `order.suggestion` evidence shape;
  - the `market_disagreement` question shape.
- The publisher refuses an `order_quantity` entry with a `value` or any ₪-named field, and a
  boost outside 0–25 (INV-069, INV-074).

- [ ] **Step 1:** Write failing tests. Each forbidden shape is refused at publish, and a
  valid artefact with all three capabilities passes.
- [ ] **Step 2:** Implement. Tests green. Commit.

---

### Task 5.11: The nightly workflow (ADR-032, ADR-035)

**Files:**
- Modify: `.github/workflows/collect-daily.yml`
- Test: `tests/test_nightly_boost_step.py`

**Interfaces:**
- The engine step gets `ANTHROPIC_API_KEY` from secrets. When it is missing, the step
  warns: no boost tonight, with the reason. It does not fail.
- A new step, **"Commit tonight's boost picks"**, runs right after the engine and before the
  blocking probes.
  - It adds only `data/external/snapshots/*/boost_picks/`.
  - It commits only when that snapshot changed.
  - Paid picks survive a failed probe.

- [ ] **Step 1:** Write a failing test that parses the workflow. The picks step exists; it
  comes after the engine and before the probes; it adds only `boost_picks`; and the key comes
  from secrets.
- [ ] **Step 2:** Implement. Tests green. Commit.

---

### Task 5.12: Boundary probes (CLAUDE.md rule 12, F8-S1 §20)

**Files:**
- Create: `scripts/check_order_signals.py`
- Modify: `package.json` (`check:order-signals`), `.github/workflows/collect-daily.yml` (run
  the probe; blocking once F8 is live)
- Test: `tests/test_check_order_signals.py`

**Interfaces:**
- The probe drives `run_engine(mode="print")` **with the market inputs**, over copied data
  and fixture daily files. It reads the published artefact and exits 1, naming the failure,
  unless every one of these holds:
  - withholding the report days gives `order_quantity` unavailable, and no monthly
    substitute;
  - withholding deliveries gives no net suggestion;
  - withholding the store facts gives no quantity in those departments;
  - withholding the market snapshots means suggestions still publish, unadjusted;
  - withholding `boost_picks` gives no boost and zero model calls;
  - withholding owner state means an answered disagreement is not raised again.

- [ ] **Step 1:** Write the probe's own test, as `check_independence`'s test does.
- [ ] **Step 2:** Implement, and wire it into the nightly after the picks commit.
- [ ] **Step 3:** Commit.

---

### Task 5.13: Screens first: mockups for the repository owner's approval

**Files:**
- Create: `docs/reviews/F8-screens-mockups.md` (the mockups as images or an artefact link,
  and the questions for him)

**What is shown.** Four screens:
- **Reorder, filled.** Suggestions by department, each showing:
  - its net or gross wording, including "you'll sell about X before your next order";
  - its reasons and boost, marked as the model's estimate;
  - approve, change and dismiss.
- **Reorder, waiting.** Each missing input or fact is named, per department.
- **Approved orders.** Quantity and order day for each line, a CSV export, and no ₪.
- **The disagreement question.** Its wording and its four answers.

- [ ] **Step 1:** Produce the mockups (Hebrew and Arabic) from fixture artefacts.
- [ ] **Step 2:** Present them. **Stop until the repository owner approves.** Record his
  answer in the file, with the date.

---

### Task 5.14: The Reorder and Approved orders pages (FR-160 … FR-163)

**Files:**
- Create: `src/pages/ReorderPage.jsx`, `src/pages/ApprovedOrdersPage.jsx`
- Modify: `src/App.jsx` (the `recommendations` and `orders` entries leave `AWAITING` once
  `order_quantity` is available), `src/owner/ownerState.js` (the outcome snapshot fields of
  ADR-034), `src/lib/i18n/dictionaries/{he,ar,en}.js`
- Test: `src/pages/__tests__/ReorderPage.test.jsx`,
  `src/pages/__tests__/ApprovedOrdersPage.test.jsx`

**Interfaces:**
- The page renders only what the artefact carries (ADR-001), as approved in Task 5.13.
- **Approve** records `acted` with `approved_quantity`. **Dismiss** records `declined`.
- The CSV export is a projection of `acted` outcomes: product, barcode, quantity, order day.
- The i18n dictionaries keep key parity across the three languages (C-53).

- [ ] **Step 1:** Write failing tests:
  - SCN-143: his quantity is recorded beside the suggested one;
  - SCN-145: an approval is still shown the next night;
  - the awaiting notice names the missing input;
  - no ₪ appears anywhere;
  - the CSV columns are exact.
- [ ] **Step 2:** Implement against the approved mockups. Tests green. Commit.

---

### Task 5.15: The disagreement question in the panel (FR-158, FR-159)

**Files:**
- Modify: `src/questions/QuestionPanel.jsx`, `src/lib/i18n/dictionaries/{he,ar,en}.js`
- Test: `src/questions/__tests__/QuestionPanel.test.jsx`

**Interfaces:**
- The panel renders the `market_disagreement` question from its `why`, as approved in Task
  5.13, with the four answers.
- An answer is recorded at `answers[barcode]["market_disagreement"]`, and is revisable.

- [ ] **Step 1:** Write failing tests:
  - the wording states only the observed facts;
  - the four answers are recorded;
  - the panel still shows at most three questions in total.
- [ ] **Step 2:** Implement. Tests green. Commit.

---

## Checkpoint 5

1. **Every test passes on fixtures:** `npm run test:py` and `npm test`.
2. **`npm run check:order-signals` passes**, and `check:signals` and `check:independence`
   still pass, since V1 is untouched.
3. **On real data today,** `order_quantity` is unavailable with `no_daily_sales`. Reorder
   shows the waiting notice naming it, and nothing is guessed.
4. **The mockups are approved,** with the date recorded (Task 5.13).

## Release conditions (outside implementation)

- **The store owner's inputs:**
  - per-day sales and deliveries, sent at least weekly (OQ-904, owner conversation #7);
  - each department's order schedule and shelf life, recorded in `configs/store_facts.yaml`
    (OQ-903, OQ-908, #8).
- **`ANTHROPIC_API_KEY`** set as a GitHub secret by the repository owner, and a monthly spend
  limit on its workspace (ADR-032).
- **ASM-065 confirmed with the owner for the daily reports:** a product absent from a day's
  report sold nothing that day.
