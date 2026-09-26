---
ID: PLAN-PHASE-5
Title: Phase 5 — V2, F8 Order Quantity (F8-S1)
Status: Approved — by the repository owner, 2026-09-26
Owner: smartshelf-architect
Parent: [Implementation plan](plan.md)
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md (Approved 2026-09-25), ADR-030, ADR-031, ADR-032, ADR-033, ADR-034, ADR-035 (Accepted 2026-09-26), docs/architecture/system-design.md §10.1 §19 §21, CLAUDE.md, .claude/SKILLS/HANDOVER.md, the code as of main 0c41353]
Updated: 2026-09-26 (rewritten after an independent review against the code; approved by the repository owner the same day)
---

# Phase 5 — V2, F8 Order Quantity

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans, task by task. Each task's `Files:` block is
> the engineer's scope boundary. A file not listed there is not the task's to change. If a
> step needs one, stop and report it.

**Goal.** Build F8-S1: per-product order suggestions on the existing Reorder entry, from his
own per-day sales. The quantity has:
- a model-picked boost when the nearby market runs out;
- a shelf-life cap from his stated shelf lives;
- stock subtracted only when the count is recent and checks out.

Approvals are listed on Approved orders, and each disagreement is asked once.

**It publishes nothing until the store owner supplies the inputs** (F8-S1 OQ-903, OQ-904,
OQ-908). Every task is proven on fixtures.

## How the pieces connect

This is the part the first draft got wrong, so it is stated before any task.

1. **Runners receive only `inputs`** (`run.py`), and a capability's `requires` are
   **`EngineInputs` field names**, mapped to reasons in `registry.INPUT_REASONS`.
   Cross-capability data therefore flows **through `inputs`**, never through another
   capability's output. `load_inputs` computes the following:

   | Input | What it is | Task |
   |---|---|---|
   | `sales_daily` | Per-day rows | 5.2 |
   | `store_facts` | The owner's stated facts | 5.3 |
   | `running_out` | ADR-031's signal | 5.4 |
   | `boost_picks` | Read from the day's sealed snapshot | 5.6 |

   The three capabilities then publish what those inputs say.
2. **The live boost step runs between inputs and capabilities.** In publish mode only,
   after `load_inputs` has `running_out`, `store_facts` and the evidence, the step asks the
   model and writes the snapshot. `inputs.boost_picks` is then read from that snapshot. Print
   mode skips the step and reads whatever snapshot exists (ADR-035).
3. **The reconciliation and hygiene flags.** `order_quantity` needs the flags that decide
   whether a stock count is usable. It gets them from one pure function in
   `src/engine/reconciliation.py`, `flagged_barcodes(inputs)`, which the reconciliation and
   hygiene capabilities also use. The flags are one derivation, at one moment.
4. **A capability is registered in the same task as its runner.** The publisher refuses a
   real run whose artefact lacks a registered id (`publish.py`, `require_complete_registry`).
   A registry entry without a runner stops the nightly publishing. Each such task also
   updates `tests/engine/test_run_capabilities.py`, the exact id set.
5. **Nothing new reaches the owner's screens before Task 5.12's mockups are approved.**
   - Today and Data list every capability by id (`DailyPage.jsx`, `DataPage.jsx`).
   - `compose.js` admits every capability not in its `NOT_ADMITTED` set.
   - `QuestionPanel.jsx` renders every question as a cost question.

   So Task 5.0 adds a no-visible-change guard in the browser, and Task 5.9's questions are
   published behind a policy flag that stays `false` until Task 5.14.
6. **Tests and probes never reach the network, and never rewrite a committed file.**
   - `run_engine` gains explicit paths: `daily_sales_dir`, `store_facts_path` and
     `snapshots_root`.
   - It also gains an injectable `boost_transport`. The default makes a real call only in
     publish mode with the key present.
   - Probes pass fixture roots, and never set `skip_market=False`, which would call
     Open-Meteo and rewrite `market-context.json`.

## Phase constraints

These apply on top of the index's Global Constraints.

- **No figure is ever guessed.**
  - Order days, shelf lives, deliveries and missing days are stated, or recorded as unknown.
  - `None` is never `0`: a blank cell is null (INV-071, INV-072).
  - `configs/shelf_life.yaml` is not an input (FR-152).
- **No quantity from a report longer than a day** (INV-070). The monthly reports are read by
  F8 only to know which departments the evidence itemises at all (FR-156, SCN-148).
- **The new capabilities carry no value.** `order_quantity`, `market_running_out` and
  `market_boost` have `value_policy: none`, and all three are `admitted: False`. No ₪ appears
  on any entry, export or total (INV-069).
- **The model moves one number** (INV-079). A pick outside 0–25% gives no boost, never a
  clipped one. Print mode never calls the model (ADR-035).
- **Permanent names.** `SIGNAL_FAMILIES` already holds **12** families, and `order.suggestion`
  makes **13**. The question fact `market_disagreement` joins `cost_price`. Neither is ever
  renamed or reused (ADR-034).
- **A disagreement is asked once, ever, so its population must be right the first time.**
  - "He does not stock it" is read from the window: no sale and no delivery. It is never read
    from F4's withdrawn class (F8-S1 §5, C-67, D-14).
  - `owner_questions`' idle suppression does not apply to it (FR-082a gives way, C-67).

## Tasks, in dependency order

| Task | Depends on | Delivers |
|---|---|---|
| 5.0 | — | Policy values, and the browser guard (no visible change) |
| 5.1 | — | The per-day importer, and the `.gitignore` path for daily files |
| 5.2 | 5.0, 5.1 | `inputs.sales_daily`, `vintages.sales_daily`, the degraded rule |
| 5.3 | 5.0 | `inputs.store_facts` and its loader |
| 5.4 | 5.0 | Availability in the presence series; `inputs.running_out`; the `market_running_out` capability |
| 5.5 | 5.2 | The evidence math: window, moving, daily mean |
| 5.6 | 5.3, 5.4, 5.5 | The live boost step, `inputs.boost_picks`, and the `market_boost` capability |
| 5.7 | 5.5 | The quantity arithmetic: stock now, net and gross, the cap, rounding |
| 5.8 | 5.6, 5.7 | The `order_quantity` capability, its family and action, schema and publisher |
| 5.9 | 5.4, 5.5 | The disagreement question kind, published behind a flag |
| 5.10 | 5.6 | The nightly workflow |
| 5.11 | 5.8, 5.9, 5.10 | Boundary probes (rule 12) |
| 5.12 | 5.8, 5.9 | Mockups for the repository owner's approval |
| 5.13 | 5.12 approved | The Reorder and Approved orders pages |
| 5.14 | 5.12 approved | Answers stored per fact, and the disagreement in the panel |

---

### Task 5.0: Policy values, and the browser guard

**Files:**
- Modify: `configs/policy.yaml`, `src/engine/policy.py`, `src/surface/compose.js`,
  `src/surface/DailyPage.jsx`, `src/pages/DataPage.jsx`
- Test: `tests/engine/test_policy.py`, `src/surface/__tests__/compose.test.js`,
  `src/surface/__tests__/DailyPage.test.jsx`, `src/__tests__/everyCapabilityReachable.test.jsx`
  (it must exempt `NOT_YET_SHOWN`, or it fails the moment Task 5.4 registers an id)

**Interfaces:**
- **`policy.order`:**
  - `window_days: 28`, `min_report_days: 21`, `freshness_days: 7`;
  - `max_count_age_days: 7`;
  - `publish_disagreement_questions: false`, which Task 5.14 turns on.

  All are provisional, citing F8-S1 OQ-906.
- **`policy.running_out`:** `prior_days: 14`, `min_listed: 10`, `min_absent: 2`,
  `max_absent: 7`, `catalogue_change_pct: 10`, `thin_collection_ratio: 0.5`,
  `signal_min_usable: 10`, `signal_max_age_days: 2`. These come from ADR-031.
- **`policy.boost`:** `model: claude-sonnet-5`, `max_pct: 25`, `request_ceiling: 200`,
  `prompt: configs/prompts/market_boost.v1.md`.
  - **The loader refuses `max_pct` above 25**, D-21's limit, the way it already refuses D-8
    and D-9 breaches.
- **The browser guard.** A single list in `compose.js`, `NOT_YET_SHOWN`, holds
  `order_quantity`, `market_running_out` and `market_boost`.
  - `compose` never admits them.
  - Today's and Data's capability lists skip them.
  - Tasks 5.13 and 5.14 remove them from the list, once the owner has approved their screens.

- [ ] **Step 1:** Write failing tests.
  - Policy loads every key, and refuses a missing key, `max_pct: 26` and `min_listed` above
    `prior_days`.
  - An artefact carrying the three ids renders **exactly** as one without them: same DOM on
    Today and Data, and nothing composed.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** Prove the screens are unchanged. Take before and after screenshots of the
  daily and data pages on the committed artefact; they must be byte-identical (the
  visual-no-change method). Then `npm test` and `npm run test:py`, green. Commit.

---

### Task 5.1: The per-day importer, and the daily files' path (ADR-030)

**Files:**
- Create: `src/internal_pos/sales_daily_importer.py`
- Modify: `.gitignore`, `CLAUDE.md` (rule 6, one sentence)
- Test: `tests/internal_pos/test_sales_daily_importer.py`,
  `tests/test_gitignore_daily_sales.py`

**Interfaces:**
- **`import_sales_daily(directory, *, silver_dir) -> dict`** writes
  `silver_pos/sales_daily.parquet`: `barcode, day, units, receipts`.
  - **A blank or unparseable cell is null, never 0.** This is unlike the monthly importer's
    `_num`.
  - `receipts` is null throughout a file that has no `כניסות מלאי` column.
  - It returns `{report_days, failed_files, deliveries_reported: {day: bool}, reprinted}`.
- **The day** comes from the file name, `דוח מכירות יום YYYY-MM-DD.csv`.
- **Reprinted lines.** It reuses the monthly importer's reprint handling (#156): identical
  lines collapse, and conflicting lines stay as printed and are counted.
- **`.gitignore`.** `data/internal/raw_pos/` becomes:
  - `data/internal/raw_pos/*`
  - `!data/internal/raw_pos/yomyom/`
  - `data/internal/raw_pos/yomyom/*`
  - `!data/internal/raw_pos/yomyom/sales_daily/`
- **CLAUDE.md rule 6** gains one sentence naming what is committed under `data/internal/`:
  the POS snapshots, and now `sales_daily/`.

- [ ] **Step 1:** Write failing tests with fixture CSVs:
  - the day is read from the name, and a bad name is a failed file;
  - an absent product gets no row;
  - blank cells are null, and a missing deliveries column gives null throughout;
  - reprints collapse or are counted;
  - a failed file is never a zero day.
- [ ] **Step 2:** Write the `.gitignore` test against a scratch copy. The daily path is **not**
  ignored; `raw_pos/yomyom/inventory.csv` and `raw_pos/other/x.csv` still are.
- [ ] **Step 3:** Implement. Tests green. Commit.

---

### Task 5.2: Per-day evidence in the run, and its vintage (ADR-030, ADR-017)

**Files:**
- Modify: `src/engine/inputs.py` (`EngineInputs.sales_daily`, and `_digest` covers it),
  `src/engine/run.py` (the step, the verdict, the `daily_sales_dir` parameter),
  `tests/engine/helpers.py` (`make_inputs` gets the new field)
- Test: `tests/engine/test_inputs.py`, `tests/engine/test_run.py`

**Interfaces:**
- **A run step `sales_daily_import`,** after `sales_import`.
- **`inputs.sales_daily`** is `None` when no daily file exists.
- **`vintages.sales_daily`** is `{first_day, last_day, report_days, missing_days,
  deliveries_missing_days}`, derived from the files present (ADR-004).
- **The run is `degraded` only when** daily files exist and `last_day` is more than
  `order.freshness_days` before the run.

- [ ] **Step 1:** Write failing tests. The inputs digest changes when a daily file changes.
  The verdict works as follows:

  | Daily files | Verdict |
  |---|---|
  | None | `ok` |
  | Latest five days old | `ok` |
  | Latest nine days old | `degraded` |
  | Weekly batches, on the nights between | `ok` |

  These tests do **not** assert `order_quantity`: it does not exist until Task 5.8.
- [ ] **Step 2:** Implement. Run `npm run test:py`, then `npm run check:signals`: V1 is
  unchanged. Commit.

---

### Task 5.3: The store facts (ADR-033)

**Files:**
- Create: `configs/store_facts.yaml`, `src/engine/store_facts.py`
- Modify: `src/engine/inputs.py` (`EngineInputs.store_facts`, `_digest`), `src/engine/run.py`
  (the `store_facts_path` parameter), `tests/engine/helpers.py`
- Test: `tests/engine/test_store_facts.py`

**Interfaces:**
- **`configs/store_facts.yaml`** is a header documenting the forms, and **no departments**.
  **No value is filled in** (OQ-903, OQ-908).
- **`load_store_facts(path, catalogue_departments)`** returns `{facts, rejected}`.
  - A missing department is absent, never defaulted.
  - A malformed entry is rejected and reported, never repaired.
  - `0` means "keeps less than a day", and `does_not_spoil` is distinct from it.
- **Every fact keeps its `stated_on`,** for publishing (ADR-033 Decision 3).

- [ ] **Step 1:** Write failing tests:
  - every schedule form parses;
  - rejections: an unknown department, a negative shelf life, a malformed schedule;
  - an empty file gives no facts and no error;
  - the digest changes when a fact changes.
- [ ] **Step 2:** Implement. Tests green. Commit.

---

### Task 5.4: Running out (ADR-031)

**Files:**
- Create: `src/market/running_out.py`, `src/engine/market_running_out.py`
- Modify:
  - `src/market/presence.py`: carry `is_online_available`, so a listed but not-orderable item
    counts as absent. Existing readers stay unchanged.
  - `src/engine/inputs.py`: `EngineInputs.running_out`, computed from `snapshots_root`; and
    `_digest`.
  - `src/engine/run.py`: the runner map, and the `snapshots_root` parameter.
  - `src/engine/registry.py`: the `market_running_out` entry, and `INPUT_REASONS
    running_out → market_signal_thin`.
  - `src/lib/i18n/dictionaries/{he,ar,en}.js`: copy for `market_signal_thin` and
    `market_signal_stale`.
  - `tests/engine/helpers.py`, `tests/engine/test_run_capabilities.py` (eight ids).
- Test: `tests/test_presence.py`, `tests/test_running_out.py`,
  `tests/engine/test_market_running_out.py`, `tests/engine/test_unavailable_reasons.py`,
  `src/lib/i18n/__tests__/unavailableReason.test.js`

**Interfaces:**
- **`running_out(series, market_store_ids, policy, on_day)`** returns `{barcode: {stores_out,
  days_absent}}`. It applies ADR-031 Decisions 1 to 3.
- **The capability `market_running_out`:**
  - requires `running_out`;
  - `market_signal_stale` is a rule-level reason its runner sets;
  - publishes `on_day`, the excluded store-days, and each product's facts.
- **Only the D-18 market counts:** the stores at or above the floor, excluding the client.

- [ ] **Step 1:** Write failing tests on synthetic series:
  - absences of 1 and 8 days never count; 2 and 7 do;
  - a store dropping more than 10% of its steady listings in a day excludes those absences;
  - a thin day is excluded;
  - not-orderable counts as absent;
  - a store below the floor never contributes.
- [ ] **Step 2:** Write a replay test **pinned to 2026-08-29 … 2026-09-24.** It skips when
  `data/` is absent. Only Wolt Market's 08-31, 09-01 and 09-15 are excluded, and every night
  flags 10 to 40 products. Pinning the dates keeps the test valid as snapshots accumulate.
- [ ] **Step 3:** Implement. Tests green, and `npm run check:signals` passes. Commit.

---

### Task 5.5: The evidence math (FR-143 … FR-146)

**Files:**
- Create: `src/engine/order_evidence.py`
- Test: `tests/engine/test_order_evidence.py`

**Interfaces:**
- **`evidence_window(report_days, policy, run_at)`** returns a `Window`, or `None` when there
  is no window. The window is the 28 days ending on the latest report day, and it needs:
  - at least 21 report days;
  - at least one report day in each 7-day block;
  - a latest report day within 7 days of the run.
- **`product_evidence(rows, window)`** returns `{moving, weekly_units[4], units_in_window,
  daily_mean}`. The daily mean is units over report days, and missing days are left out.
- **`stocks(rows, window, latest_count)`** implements "he stocks" (F8-S1 §5): a sale or a
  delivery in the window. In a department that is not itemised, it is a latest count above 0.

- [ ] **Step 1:** Write failing tests:
  - a missing day is excluded from the mean;
  - 20 report days, a week with none, or an eight-day-old window each mean no window;
  - moving needs a sale in every week;
  - no monthly row can enter (INV-070);
  - "he stocks" behaves as defined.
- [ ] **Step 2:** Implement, as pure functions. Tests green. Commit.

---

### Task 5.6: The boost (ADR-032, ADR-035)

**Files:**
- Create: `src/engine/market_boost.py`, `configs/prompts/market_boost.v1.md`
- Modify:
  - `src/engine/run.py`: the live step between `load_inputs` and the capabilities, the
    `boost_transport` parameter, and print mode skipping the step.
  - `src/engine/inputs.py`: `EngineInputs.boost_picks`, read from the snapshot; and
    `_digest`.
  - `src/engine/registry.py`: the `market_boost` entry, `INPUT_REASONS`, and the reasons
    `no_boost_key` and `boost_unavailable`.
  - `src/lib/i18n/dictionaries/{he,ar,en}.js`, `tests/engine/helpers.py`,
    `tests/engine/test_run_capabilities.py` (nine ids).
- Test: `tests/engine/test_market_boost.py`, `tests/engine/test_unavailable_reasons.py`,
  `src/lib/i18n/__tests__/unavailableReason.test.js`

**Interfaces:**
- **Who is asked.** Only products that are **moving and running out** (FR-147).
- **What they are asked with.** Only published facts (FR-164): weekly units, daily mean,
  `stores_out`, `days_absent`, department, name and shelf life (Task 5.3).
  `inputs_digest` is the sha256 of those facts.
- **The call.** `ask(payload, *, model, key, transport)` makes one HTTPS call to the Messages
  API through `urllib`: no SDK, no new dependency, one retry, a timeout, and no sampling
  parameter.
- **The check.** `check(raw, max_pct)` parses, then checks the range 0 to 25, with no
  clipping. A reason containing a digit (0–9, ٠–٩ or ۰–۹) is withheld.
- **The snapshot** is `data/external/snapshots/<on_day>/boost_picks/picks.json`, and its **own**
  `boost_picks/_manifest.json`.
  - It never touches the day-level manifest, which `presence.py` reads to decide whether a day
    is usable.
  - It is merge-never-replace.
  - `<on_day>` is `running_out`'s day.
- **Order and ceiling.** Requests go in a fixed order: units in the window, descending, then
  barcode. Products beyond the ceiling get `ceiling_reached`.
- **Replay.** A pick whose `inputs_digest` differs from today's facts is not applied
  (ADR-035 Decision 4).

- [ ] **Step 1:** Write failing tests with a fake transport. The default transport is never
  constructed in tests.
  - Accepted at 10; rejected at 40, −1, "abc" and malformed JSON; never clipped.
  - Reasons with Western or Arabic-Indic digits are withheld.
  - Only moving, running-out products are asked, in a fixed order, with the ceiling applied.
  - Merge-never-replace holds.
  - The day manifest is untouched.
  - Print mode makes zero calls, and applies a pick only when the digest matches.
  - With no key, the capability is unavailable with `no_boost_key` and the run is `ok`.
  - The request holds exactly FR-164's facts.
- [ ] **Step 2:** Write the prompt. It asks for JSON with `boost_pct` from 0 to 25 and a
  reason of at most 160 characters containing no numbers, and forbids claims about
  competitor volumes (F8-S1 §21).
- [ ] **Step 3:** Implement. Tests green, and `npm run check:signals` passes. Commit.

---

### Task 5.7: The quantity arithmetic (FR-146 … FR-153)

**Files:**
- Create: `src/engine/order_arithmetic.py`
- Test: `tests/engine/test_order_arithmetic.py`

**Interfaces:**
- **`next_order_day(schedule, run_date)` and `cycle_days(schedule, order_day)`** cover
  weekdays, an interval from a date, and "no fixed days", which gives `None`.
- **`stock_now(count, count_date, flagged, rows_since, deliveries_reported, run_date)`**
  returns `None` unless all of these hold:
  - the count is at most 7 days old;
  - the product is not in `flagged`;
  - it has a row on **every** report day since the count;
  - deliveries were reported on each of those days.

  The value is the count plus receipts less units. A value below 0 gives `None`.
- **`stock_at_order_day(...)`** is floored at 0.
- **`quantity(...)`** returns `{quantity | None, kind, capped, reason}`:
  - expected sales below one unit give none;
  - the need rounds to the nearest unit, halves up, while a quantity the cap sets rounds
    down;
  - a shelf life of 0 gives none, and `does_not_spoil` gives no cap;
  - a net zero is flagged `covered`.

- [ ] **Step 1:** Write failing tests:
  - SCN-133 and SCN-134: a Thursday run for Sunday, gross and net;
  - **SCN-135:** a flagged count, so gross;
  - SCN-138: capped, less stock;
  - SCN-139: a shelf life of 0;
  - SCN-147: a negative stock now;
  - SCN-149: below one unit per cycle;
  - 1.14 a day stays 1;
  - a Sunday/Wednesday schedule;
  - a day with deliveries unreported, so gross.
- [ ] **Step 2:** Implement, as pure functions. Tests green. Commit.

---

### Task 5.8: `order_quantity` (FR-143 … FR-163, ADR-034)

**Files:**
- Create: `src/engine/order_quantity.py`
- Modify:
  - `src/engine/reconciliation.py`: extract `flagged_barcodes(inputs)`, which reconciliation
    and hygiene then use, with no behaviour change.
  - `src/engine/model.py`: `SIGNAL_FAMILIES` gains `order.suggestion`, making 13, and
    `ACTIONS` gains `place_order`.
  - `schemas/dashboard.schema.json`: the family and action enums, the `order_quantity`
    evidence shape, and `vintages.sales_daily`.
  - `src/engine/publish.py`: refuse a value or any ₪-named field on an `order_quantity`
    entry, and refuse an **applied** boost outside 0–25. A recorded, rejected pick is facts,
    and is never checked as an applied boost.
  - `src/engine/registry.py`, `src/engine/run.py`, `src/lib/i18n/dictionaries/{he,ar,en}.js`
    (the reasons `no_daily_sales`, `stale_daily_sales`, `no_store_facts`),
    `tests/engine/helpers.py`, `tests/engine/test_run_capabilities.py` (ten ids).
- Test: `tests/engine/test_order_quantity.py`, `tests/engine/test_publish.py`,
  `tests/engine/test_reconciliation.py`, `tests/engine/test_unavailable_reasons.py`,
  `src/lib/i18n/__tests__/unavailableReason.test.js`

**Interfaces:**
- **The capability.** `order_quantity` requires `sales_daily` and `store_facts`.
- **An entry.** One per moving product with a quantity:
  - family `order.suggestion`, action `place_order`;
  - `entry_id = sha256("order.suggestion|" + barcode + "|" + order_day)[:16]`;
  - no `value`.
- **Its evidence (FR-154):**
  - the schedule and the cycle's dates;
  - the window and its weekly units;
  - the daily mean and the **expected sales**;
  - the boost applied, with its pick, reason and model, or why there is none;
  - the count, its date, whether it was used and why;
  - the deliveries and sales since the count, the stock now and the stock at the order day;
  - the shelf life with its `stated_on`, and whether it capped;
  - `kind`;
  - `schedule_changed`.
- **Per-department reasons (FR-155, FR-156):** `not_moving`, `no_order_schedule`,
  `no_fixed_days`, `no_shelf_life`, `no_window`, `below_one_per_cycle`,
  `shelf_life_under_a_day`, `cap_rounds_to_zero`, `not_itemised`. `not_itemised` is read
  over **any** evidence, monthly reports included, as FR-156 defines it.
- **`covered_by_stock`** is a count of products, not money.

- [ ] **Step 1:** Write failing tests:
  - SCN-132: monthly reports only, so unavailable with `no_daily_sales`;
  - SCN-140 and SCN-146: missing store facts;
  - SCN-142: a department that is not itemised;
  - SCN-145: the id is stable on Friday and Saturday for Sunday, and new after it;
  - **SCN-136 and INV-074:** the boost is applied once, from `boost_picks`;
  - no value and no ₪ field on any entry;
  - **AC-140, AC-149 and NFR-067:** a print-mode re-run over the same committed inputs
    reproduces every published quantity and fact;
  - the publisher refusals;
  - reconciliation and hygiene are unchanged after the `flagged_barcodes` extraction.
- [ ] **Step 2:** Implement. Tests green, and `npm run check:signals` and
  `check:independence` pass. Commit.

---

### Task 5.9: The disagreement question (FR-158, FR-159, ADR-034)

**Files:**
- Modify: `src/engine/owner_questions.py` (a second fact kind), `schemas/dashboard.schema.json`
  (the question shape)
- Test: `tests/engine/test_owner_questions.py`

**Interfaces:**
- **Identity.** `FACTS` holds `cost_price` and `market_disagreement`, and
  `question_id = sha256(fact + "|" + barcode)[:16]`, following the existing format.
- **Who is asked.** A product he **stocks** (Task 5.5), that is running out and not moving.
  - It needs a window, except where the department is not itemised in any evidence
    (SCN-148, FR-156).
  - **It is not suppressed as idle or by F4's withdrawn class** (C-67). A product he does not
    stock is never asked about (FR-082 holds).
- **Its `why`:** `stores_out`, `days_absent`, and `units_in_window` or `no_sales_row`.
- **The answers:** shelf place, price, weak market, and sells elsewhere.
- **Answered means retired for good** (D-20, over FR-089).
- **Order.** It follows every question with money (ADR-027), then by units and barcode.
- **Publication.** Emitted into `owner_questions.items` **only when
  `order.publish_disagreement_questions` is true**. That is false until Task 5.14, so today's
  panel never shows one as a cost question.

- [ ] **Step 1:** Write failing tests:
  - SCN-141: raised once; answered, it stays retired as facts change;
  - SCN-148: no window gives none, except where not itemised;
  - **AC-142:** the market withheld gives none;
  - idle and withdrawn-class products he stocks **are** asked, and one he does not stock is
    not;
  - it is ordered after the money questions;
  - no `why` says "sells a lot" or "zero sales";
  - with the flag false, `items` is unchanged byte for byte.
- [ ] **Step 2:** Implement. Tests green. Commit.

---

### Task 5.10: The nightly workflow (ADR-032, ADR-035)

**Files:**
- Modify: `.github/workflows/collect-daily.yml`
- Test: `tests/test_nightly_boost_step.py`

**Interfaces:**
- **The engine step** gets `ANTHROPIC_API_KEY` from secrets. When it is missing, the step
  warns and there is no boost; it does not fail.
- **"Commit tonight's boost picks"** runs right after the engine and before the blocking
  probes.
  - It force-adds a guarded pathspec, as the snapshot step does, since `data/external/` is
    ignored: `git add -f data/external/snapshots/*/boost_picks/`.
  - It commits only when that changed, so paid picks survive a failed probe.

- [ ] **Step 1:** Write a failing test that parses the workflow:
  - the step exists, after the engine and before the probes;
  - it adds only `boost_picks`, with `-f`;
  - the key comes from secrets.
- [ ] **Step 2:** Implement. Tests green. Commit.

---

### Task 5.11: Boundary probes (CLAUDE.md rule 12, F8-S1 §20)

**Files:**
- Create: `scripts/check_order_signals.py`, and fixture roots for it under
  `tests/fixtures/order_signals/` (daily files, `store_facts.yaml`, a `boost_picks` snapshot,
  and a presence snapshot slice)
- Modify: `scripts/check_independence.py` (F8's independence), `package.json`
  (`check:order-signals`), `.github/workflows/collect-daily.yml` (run it after Task 5.10's
  step), `CLAUDE.md` (rule 12's list of probes)
- Test: `tests/test_check_order_signals.py`

**Interfaces:**
- **How it runs.** `run_engine(mode="print")` over copies of the fixture roots, passed as
  `daily_sales_dir`, `store_facts_path` and `snapshots_root`. It reads the published
  artefact, and never uses `skip_market=False`.
- **The baseline must first show** suggestions, a boost and a disagreement, so that each
  withholding really removes something.
- **It exits 1 unless each of these holds:**

  | Withheld | Must happen |
  |---|---|
  | Report days | `order_quantity` unavailable, and no monthly substitute |
  | Deliveries | No net suggestion |
  | Store facts | No quantities |
  | Market snapshots | Suggestions still publish, unadjusted, and no disagreement |
  | `boost_picks` | No boost, and zero model calls |
  | Owner state with an answered disagreement | It is not raised again |

- **`check:independence` adds one check:** `order_quantity` and `market_boost` fail
  independently.
- **Blocking starts from the first nightly on which `order_quantity` is `available` on real
  data.** Before that the probe runs and warns.

- [ ] **Step 1:** Write the probe's test, asserting each case fails when its expectation is
  broken.
- [ ] **Step 2:** Implement and wire it in. Update rule 12's sentence listing the probes.
  Commit.

---

### Task 5.12: Mockups for the repository owner's approval

**Files:**
- Create: `docs/reviews/F8-screens-mockups.md` (the mockups, and his answer with its date)

**What is shown**, in Hebrew and Arabic, from the fixture artefact of Task 5.11:
- **Reorder, filled.** Suggestions by department:
  - net or gross wording, including "you'll sell about X before your next order";
  - the reasons, and the boost marked as the model's estimate;
  - approve, change and dismiss;
  - the **team account's read-only view** (D-22, ADR-029).
- **Reorder, waiting.** Each missing input or fact is named, per department, using Tasks 5.4,
  5.6 and 5.8's reason copy, which he approves here.
- **Approved orders.** Product name, department, quantity and order day; a CSV export; no ₪.
- **The disagreement question.** Its wording and its four answers.

- [ ] **Step 1:** Produce the mockups.
- [ ] **Step 2:** Present them. **Stop until the repository owner approves.** Record his
  answer with the date.

---

### Task 5.13: The Reorder and Approved orders pages (FR-160 … FR-163)

**Files:**
- Create: `src/pages/ReorderPage.jsx`, `src/pages/ApprovedOrdersPage.jsx`
- Modify:
  - `src/App.jsx`: the `recommendations` and `orders` entries leave the `AWAITING` map, and
    route to the new pages, which render their own waiting state from the capability's reason
    instead of the static `demand` notice.
  - `src/surface/compose.js`: `order_quantity` and `market_running_out` leave
    `NOT_YET_SHOWN`, for the Data page only. They stay out of Today.
  - `src/pages/DataPage.jsx`, `src/owner/ownerState.js` (ADR-034's outcome snapshot fields),
    `src/lib/i18n/dictionaries/{he,ar,en}.js`.
- Test: `src/pages/__tests__/ReorderPage.test.jsx`,
  `src/pages/__tests__/ApprovedOrdersPage.test.jsx`, `src/__tests__/appSpine.test.jsx`,
  `src/__tests__/everyCapabilityReachable.test.jsx`, `src/__tests__/teamReadOnly.test.jsx`

**Interfaces:**
- **Rendering.** The pages render only artefact fields (ADR-001), as approved in Task 5.12.
- **Outcomes.** Approve records `acted` with `approved_quantity`, and dismiss records
  `declined`. A team account is `readOnly`.
- **The CSV** joins `acted` outcomes to `catalogue.json` (ADR-024) for the name and the
  department. It is a projection with no arithmetic.
- **Copy.** The three languages keep key parity (C-53).

- [ ] **Step 1:** Write failing tests:
  - the waiting page names `no_daily_sales`, as Checkpoint 5 item 3 requires;
  - SCN-143: his quantity is recorded beside the suggested one;
  - SCN-145: an approval is shown the next night;
  - a team account cannot approve;
  - no ₪ anywhere;
  - the CSV columns are exact.
- [ ] **Step 2:** Implement against the approved mockups. Tests green. Commit.

---

### Task 5.14: Answers stored per fact, and the disagreement in the panel (FR-158, FR-159)

**Files:**
- Modify:
  - `src/owner/ownerState.js`: `recordAnswer(barcode, fact, …)` merges into
    `answers[barcode][fact]`, never replacing the barcode's record.
  - `src/owner/remoteOwnerState.js`: `mergeFields` on the `barcode.fact` field path.
  - `src/questions/QuestionPanel.jsx`: renders by `fact`.
  - `configs/policy.yaml`: `order.publish_disagreement_questions: true`.
  - `src/lib/i18n/dictionaries/{he,ar,en}.js`.
- Test: `src/owner/__tests__/ownerState.test.js`, `src/owner/__tests__/remoteOwnerState.test.js`,
  `src/owner/__tests__/ownerStateContract.test.js`, `src/questions/__tests__/QuestionPanel.test.jsx`,
  `src/__tests__/teamReadOnly.test.jsx`

**Interfaces:**
- **Storage.** A cost answer and a disagreement answer for the same barcode coexist, locally
  and in Firestore. An existing `{cost_price}` record keeps working unchanged. The engine
  already reads per fact (`answered_cost`).
- **The panel** renders `market_disagreement` from its `why`, with the four answers. It still
  shows at most three questions in total (D-8).

- [ ] **Step 1:** Write failing tests:
  - recording a disagreement never erases a cost answer, and the reverse, locally and in the
    remote write's field path;
  - the wording shows only observed facts;
  - the three-question limit holds;
  - a team account cannot answer.
- [ ] **Step 2:** Implement, and turn the flag on. Tests green. Commit.

---

## Checkpoint 5

1. **Everything passes on fixtures:** `npm test`, `npm run test:py`, `check:order-signals`,
   `check:signals` and `check:independence`.
2. **Task 5.0's screenshots** are byte-identical before and after.
3. **On real data today,** `order_quantity` is unavailable with `no_daily_sales`, and the
   Reorder page names it. Nothing is guessed.
4. **The mockups are approved,** with the date recorded (Task 5.12).

## Release conditions (outside implementation)

- **The store owner's inputs:**
  - per-day sales and deliveries, at least weekly (OQ-904, owner conversation #7);
  - each department's schedule and shelf life, in `configs/store_facts.yaml` (OQ-903,
    OQ-908, #8).
- **`ANTHROPIC_API_KEY`** as a GitHub secret, with a monthly spend limit on its workspace
  (ADR-032).
- **ASM-065 confirmed for the daily reports:** a product absent from a day's report sold
  nothing that day.
