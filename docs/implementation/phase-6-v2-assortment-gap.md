---
ID: PLAN-PHASE-6
Title: Phase 6 — V2, F9 Assortment Gap (F9-S1)
Status: Ready for review — built on the repository owner's approval of F9-S1 (2026-09-28), which he gave as the go-ahead to build
Owner: smartshelf-architect
Parent: [Implementation plan](plan.md)
Inputs: [docs/features/F9-assortment-gap/specs/F9-S1-assortment-gap.md (Approved 2026-09-28), D-25, ADR-009, ADR-014, ADR-031, docs/architecture/system-design.md §21, src/market/running_out.py, src/engine/registry.py, src/surface/compose.js]
Updated: 2026-09-28 (Tasks 6.1–6.4 built; 6.4's probe coverage landed inside 6.2, because the registry refuses an input no probe withholds; Task 6.5 waits for the card's approval)
---

# Phase 6 — V2, F9 Assortment Gap

**Goal.** Build F9-S1. The new capability `assortment_gap` publishes the products he does not
stock that the nearby market ran out of recently and still sells, in FR-172's order, and the
surface gives it at most one unvalued place, the first. It runs on data already held (D-23),
so unlike Phase 5 it publishes on real data from its first night.

**It stays off every screen until the repository owner approves the card** (FR-175, Task 6.5).
Tasks 6.1 … 6.4 therefore change nothing anyone sees.

## Phase constraints

- **One rule for "ran out".** Task 6.1 calls `running_out` from `src/market/running_out.py`
  for each night. It never re-implements it (FR-167).
- **No value, anywhere.** Entries carry `value: None`, and no evidence field holds an amount
  or a price (FR-169, INV-081).
- **Policy, not code,** for the window, the cap and the order the surface keeps (FR-171).
- **Nothing visible changes before Task 6.5.** The surface's within-capability order stays as
  it is for every other capability. FR-106a asks for it to follow each capability's key, and
  today it follows the entry id. That is reported to the repository owner as its own change,
  because it moves what Today shows.

## Tasks, in dependency order

### Task 6.1: The recent replay (FR-167, §5)

**Files:** `src/market/recent.py`, `tests/test_market_recent.py` *(named for what they hold, the market's recent running-out, beside `running_out.py` and `test_running_out.py`)*

A pure function over a presence series, the market's store ids, the policy and the night.
It runs `running_out` for each usable night of the last `window_days` calendar days, and
returns plain data:
- the window, with its first and last day and its usable nights;
- per flagged barcode, its nights and stores;
- per barcode, the stores listing it on the last `max_absent` usable days, and tonight;
- the market's product names.

**Done when:** tests on a fixture series pin each §5 term, including SCN-153 (dropped) and the
`max_absent` edge of "still sold". The function's flags for the last night equal
`running_out`'s for that night.

### Task 6.2: The capability (FR-165 … FR-170, FR-172, FR-174, FR-176)

**Files:** `src/engine/inputs.py`, `src/engine/registry.py`, `src/engine/assortment_gap.py`,
`src/engine/run.py`, `src/engine/surface_candidates.py`, `configs/policy.yaml`,
`src/engine/policy.py`, `tests/engine/test_assortment_gap.py`

- `EngineInputs.market_recent` comes from Task 6.1. It is None whenever `running_out` is None,
  and is fed to the digest.
- The registry entry is admitted, with value policy `none`. It requires `products`,
  `running_out` and `market_recent`, and is `published_from` its first nightly.
- The capability is unavailable on the input reasons, or on `market_signal_stale` through
  `market_running_out.is_stale`. Its entries are published in FR-172's order.
- `REQUIRED_EVIDENCE` gets FR-168's four fields.
- Policy: `assortment_gap.window_days: 14`, and the surface lines of Task 6.3.

**Done when:** AC-164 (fixture form), AC-166 and AC-169 pass, and a run over the committed
data for 2026-09-28 publishes 138 entries.

### Task 6.3: The surface (FR-171, FR-172, FR-175)

**Files:** `src/surface/compose.js`, `src/surface/__tests__/compose*.test.js`, `configs/policy.yaml`

- `surface.unvalued_caps: {assortment_gap: 1}`, with `assortment_gap` first in
  `unvalued_order`.
- `surface.engine_ordered: [assortment_gap]`: the capabilities whose published order the
  surface keeps.
- `assortment_gap` joins `NOT_YET_SHOWN`.

**Done when:** AC-167, AC-170 and AC-171 pass. Today and every page render byte-identically
before and after, by the 126-screenshot harness, because nothing is shown yet.

### Task 6.4: The probes (AC-165, NFR-071)

**Files:** `scripts/check_v1_signals.py` and its tests, `scripts/check_deploy_data.py` only if
`published_from` needs it.

**Done when:** withholding the delivery catalogues makes `assortment_gap` and
`market_running_out` unavailable. Withholding the catalogue makes `assortment_gap`
unavailable while `market_running_out` stays available. `npm run figures` still completes
within 2 minutes on a fresh clone.

### Task 6.5: The card (FR-173, FR-175, FR-177) — waits for the card's approval

**Files:** `src/surface/EntryCard.jsx` (or its action map), the three dictionaries,
`src/surface/compose.js` (`NOT_YET_SHOWN`), and a mockup review under `docs/reviews/`.

Mockups in the three languages go to the repository owner first. On his approval, the labels
and the `action.*` string land, and `assortment_gap` leaves `NOT_YET_SHOWN`.

**Done when:** AC-168 passes and the card is live.

## Progress

- **6.1 … 6.3 built on 2026-09-28**, in one PR:
  - on the committed data a print run for 2026-09-28 publishes 138 findings, none catalogued;
  - nothing visible changes, shown by the 126-screenshot harness.
- **6.4 is done inside 6.2.** `check_v1_signals` refuses a required input that no probe
  withholds, so the probe coverage had to land with the registration:
  - `check_order_signals` now requires F9 to go unavailable without the market snapshots;
  - its fixture world has a finding in the baseline;
  - the catalogue case shows `market_running_out` untouched;
  - the whole engine run takes 4.4 s locally, so the 2-minute budget holds.
- **6.5 built on 2026-09-29**, after the repository owner approved the mockups
  (`docs/reviews/f9-card-2026-09-29.md`). F9 is on Today and on the Assortment page.

## Checkpoint 6

- Tasks 6.1 … 6.4 are merged.
- The nightly publishes `assortment_gap` available on real data.
- `check:signals` covers it, and nothing visible has changed.
- Task 6.5 follows the card's approval.
