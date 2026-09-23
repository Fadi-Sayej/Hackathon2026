---
ID: ADR-026
Title: The reconcile window is cut once per run, at the run's own stock date, and reconciliation publishes that cut
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-23
Parent: [System Design](../system-design.md) §19
Related Specs: F2-S1, F6-S1, F7-S1
Inputs: [F2-S1 §5, §11, FR-027, NFR-010, ASM-011, OQ-201; ADR-005, ADR-009, ADR-011, ADR-016, ADR-017, ADR-021; docs/architecture/system-design.md §7.1, §11.1, §11.2, §21; public/data/dashboard.json (2026-09-23); src/engine/inputs.py; src/engine/reconciliation.py; src/engine/run.py; src/internal_pos/sales_importer.py; scripts/import_yomyom_sales.py; src/surface/compose.js; tests/engine/test_unavailable_reasons.py; issue #150; issue #105; PR #144]
Updated: 2026-09-23
---

# ADR-026 — The reconcile window is cut once per run, at the run's own stock date, and reconciliation publishes that cut

**Status:** Accepted (2026-09-23, by the repository owner) · **Recorded in:**
[System Design](../system-design.md) §19 · proposed by `smartshelf-architect` for #150 and held
at `Ready for review` until he decided it, because a role may not approve its own output
(HANDOVER rule 2). Asked directly and answered directly, on PR #157.

## Context

The committed artefact of 2026-09-23 (run `ok`):

```
vintages.pos.as_of                   2026-06-06   (declared_sidecar)
vintages.sales.months                2026-01 … 2026-07   (7)
vintages.sales.reconcile_before      2026-06      ← published by #144
capabilities.reconciliation.window   2026-01..2026-07, count 7
entries                              355, every one with evidence.window_id 2026-01..2026-07
evidence.reconcile_months            {1: 181, 2: 84, 3: 48, 4: 32, 5: 10}
figures.reconciliation.flagged       355, thresholds.window 2026-01..2026-07
```

The capability says seven months. Its arithmetic summed five.

**Where the owner reads it.** On the daily surface `EntryCard` renders every evidence key
(`EntryCard.jsx:39`), and `evidence.window_id` is labelled **התקופה**, *the period*.
`compose` reserves the unvalued places for reconciliation first
(`thresholds.surface.unvalued_places: 3`, `unvalued_order` led by `reconciliation`), so the
owner sees at most three reconciliation cards at a time. The reconciliation page lists all 355
by name and characterisation only, without a period (`CapabilityPage.jsx`).

F2-S1 defines receipts and units sold as quantities recorded "over the observed period" (§5).
NFR-010 requires every flagged product to show its arithmetic "in a form the owner can check
against his own records". An owner who totals his own January–July receipts for a card's
product gets a different number from the card, because the card's receipts stop at May. The
finding is right, but the label beside it makes it uncheckable.

**Why the code says seven.** The design has two windows and never says which one reconciliation
carries. §7.1 has the importer produce the *evidence window* record
`{months, first, last, count, full_annual_cycle}` and, separately, sums "in the reconcile
window", which "ends before the POS month". §21 routes FR-020 through "the reconcile window".
§11.2 says only `window?: EvidenceWindow  # lifecycle, reconciliation`. The code took the
evidence window (`reconciliation.py:160`). That is right for `catalogue_lifecycle`, whose
statement covers every month (ADR-011: *"no sales row in 7 monthly reports (Jan–Jul 2026)"*),
and wrong for reconciliation.

#150 gives two readings and asks for a decision rather than a tidy-up. *Read 1:* the capability
overstates its own evidence base. *Read 2:* the value is already on the owner's screen, so
changing it rewrites a published field, which is the architect's and the owner's call. Both
hold.

## Measured before deciding

**The boundary is decided twice today, at two different moments:**

- `import_sales` cuts the summary at the stock date's month **when it writes the summary**
  (`sales_importer.py:111`). It stores the sums, not the boundary.
- `load_inputs` derives `reconcile_before` again from the POS vintage **when it loads**
  (`inputs.py:266-268`).

When no monthly report parses, `import_sales` returns before writing
(`sales_importer.py:108`). The older summary survives, and ADR-017 lets the run continue on it.
Both derivations also exist twice over: `run.py`'s `_sales_import` asks `usable_stock_date`,
while `scripts/import_yomyom_sales.py:34` cuts with a bare `date.fromisoformat`.

**Reproduced over a copy of the real silver tables.** The boundary the arithmetic used was
*recovered from the tables*: it is the month *B* for which the rows before *B* reproduce every
summary row's three reconcile figures. When every month precedes the count, any *B* after the
last month reproduces them.

| day | published `reconcile_before` | boundary reproducing the summary | #150's narrow window | months summed | flagged |
|---|---|---|---|---|---|
| normal night, count 2026-06-06 | 2026-06 | 2026-06 | 2026-01..2026-05 | 2026-01..2026-05 ✓ | 355 |
| summary cut at a 2026-02-15 count, then a 2026-08-12 export lands and no report parses | **2026-08** | **2026-02** | **2026-01..2026-07** | **2026-01** ✗ | **139** |
| control: a clean import on 2026-08-12 | 2026-08 | any month after 2026-07 | 2026-01..2026-07 | 2026-01..2026-07 ✓ | 439 |

On the second day, #144's field contradicts its own schema description (*"the month boundary
reconciliation actually used"*). The window #150 proposes would claim seven months over
arithmetic that summed one. And 139 findings are published over a February cut beside an
August count. That is the misalignment ASM-011 says makes the arithmetic unsound, and it is
#105's finding 2.

**The same reproduction with the cut made once, in `load_inputs`, at the run's own date.**
This was a throwaway simulation: the real engine, with only the three reconcile figures
recomputed from `sales_monthly`.

| day | flagged | entries compared with today's engine |
|---|---|---|
| normal night | 355 | **identical**: ids, order and every evidence value; only `window_id` differs (`2026-01..2026-05`) |
| #105 day | **439** | the same 439 as the clean-import control |

## Decision

**The reconcile window is cut once per run, in `load_inputs`, at the month of the run's own
usable stock date. The reconcile figures, the published boundary and
`capabilities.reconciliation.window` all come from that one cut. The importer no longer
cuts.**

1. **`load_inputs` makes the cut.** It already derives the boundary for #144, and it takes the
   three figures from `sales_monthly` with the same strict `<` the importer applies today. The
   figures are `reconcile_units`, `reconcile_receipts`, and `reconcile_months`, which counts
   **distinct months**, as its name says. They go on the same `sales_summary` rows the
   capability already reads. With no usable stock date the three are null, never the full
   history. That behaviour is #102's, and it is protected here.
2. **The importer stops cutting.** `import_sales` loses its `inventory_as_of` parameter and the
   three columns. It parses reports and summarises them, and needs no date. Neither
   `_sales_import` nor `scripts/import_yomyom_sales.py` reads the POS vintage any more, so the
   two date rules that disagree today become none.
3. **`vintages.sales.reconcile_before` is unchanged in meaning,** and now true on every day: it
   *is* the boundary that run's figures were cut at. The schema is unchanged, including its
   description.
4. **Reconciliation publishes the cut.** It carves its window from `inputs.window`, which it
   already declares, keeping the months strictly before `vintages.sales.reconcile_before`, and
   builds them with the existing `evidence_window`. The shape stays the same `EvidenceWindow`,
   so no consumer changes shape. Every entry's `evidence.window_id` and the `flagged` figure's
   `thresholds.window` carry it. On today's data that is **`2026-01..2026-05`, count 5**.
5. **The boundary enters `inputs_digest`.** Today it reaches the digest only through sums baked
   into the summary rows. Once those are cut at load, two runs over identical files with count
   dates in different months would otherwise share a digest while publishing different
   findings.

**What does not move:**
- The registry's `requires` and the rule-12 withholding map (`check_v1_signals.py`).
- Both existing refusals: `unknown_stock_date` and `no_sales_evidence`.
- `vintages.sales.months`, `first`, `last` and `full_annual_cycle`, which describe the sales
  data.
- `catalogue_lifecycle` and `owner_questions`, which keep `inputs.window` because they reason
  over every month.
- There is **no new `unavailable_reason`, no new owner-facing wording and no schema change.**

**The invariant, which the implementation tests.** Whenever reconciliation is `available`, its
window holds at least one month, and its last month precedes `vintages.sales.reconcile_before`.
The figures and the window are cut from the same `sales_monthly` rows at the same boundary in
the same run, and `no_sales_evidence` already refuses when no row precedes the boundary. So a
carve can be empty only when the capability has refused.

## What changes for the owner

- **The period on a reconciliation card changes from `2026-01..2026-07` to
  `2026-01..2026-05`.** The value changes in all 355 entries' evidence. The owner sees it on
  the reconciliation cards the daily surface shows, at most three at a time. The label stays.
- **On a day like #105's,** the flagged list is computed against the stock count actually in
  hand: 439 in the reproduction, the same as a clean import, instead of 139 cut at February.
  Such a day has not happened yet. When it does, the run still says `degraded` and
  `imported_this_run: false`, because the reports did not arrive (ADR-017), and its arithmetic
  is aligned.
- **Nothing else changes, and on a normal night that is measured, not inferred:**
  - **The entries.** Ids, order and every evidence value except `window_id` are identical
    (above).
  - **Recorded outcomes and "Later" deferrals.** Both are keyed on `entry.id`. The ADR-016
    snapshot holds `signal_family`, `capability`, `barcode` and `characterisation`, and no
    evidence (`ownerState.js:161`).
  - **Revivals.** They key on `inputs.window.window_id` (`catalogue_lifecycle.py:54`).
  - **The surface.** `compose.js` reads no evidence and no window.

## What this settles beyond #150

**#105 finding 2 stops being possible, rather than becoming a refusal.** A new stock date can no
longer sit beside a summary cut for an older one, because the summary no longer carries a cut.
This is consistent with ADR-017, which rejected refusing stale evidence because stale findings
are *"older than today, not wrong"*. That remains true: the #105 day still publishes, on older
reports, now cut at the count actually in hand. #105 can close when this is implemented.

## What this does not decide

- **OQ-201 itself.** Month granularity still drops the flows between the first of the count's
  month and the count. This makes the window honest about the months it used. It does not make
  monthly reports daily.
- **The duplicate report lines** in "Found while measuring" below: whether they are one sale
  reported twice is a fact about the POS export.

## Rejected options

### Keep the full span, and write down that `reconcile_before` is the answer
This is #150's "if no". The window is published beside the numbers it qualifies, on the cards,
and NFR-010 makes those numbers something the owner checks against his records. A sentence in
F2-S1 does not reach the card, and the field it would point to is itself wrong on the #105 day.

### Narrow the window from `reconcile_before` while the importer keeps cutting
This is #150's "if yes", as written. It is correct every normal night and wrong on the #105 day,
as measured above: seven months claimed over one summed. It trades a window that is always
slightly wrong for one that is usually right and badly wrong on a degraded day, which is the
worse failure, because nobody is looking when it happens.

### Stamp the boundary on the summary, and read the window from the stamp
This was this ADR's first draft. It **records** the first derivation instead of **removing** the
second:
- The #105 day stays at 139 findings over misaligned periods, merely made visible.
- A summary with no stamp needs a new `unavailable_reason`.
  `tests/engine/test_unavailable_reasons.py` correctly refuses to let the engine emit that
  without the owner's words for it in three languages.
- The refusal would need a new probe, because CI always re-imports, so it would never fire
  there.
- It changes #144's field on days reconciliation refuses: a stamped boundary would sit beside
  `unknown_stock_date`.

It is more machinery that ends in a worse answer.

### Re-cut the summary inside `import_sales` from the surviving `sales_monthly` on a no-report day
This option keeps a rule that needs the stock date inside ingestion, which is why two writers
of it disagree today. It would also make `import_sales` rewrite silver from silver on exactly
the day ADR-017 describes it as one that *"writes nothing"*.

### Compute the figures inside `reconciliation.run` instead of `load_inputs`
The capability would read `sales_monthly`, which it does not declare. Declaring it moves the
registry and the rule-12 withholding map: deleting `sales_monthly.parquet` also removes
`window`, which `catalogue_lifecycle` declares. And the published boundary would still be
derived in `load_inputs`, so one cut would be computed in one function and stated from another.
That is the shape this ADR removes.

### Add a second window to the capability, and keep `window` as the sales span
The card renders `evidence.window_id`, so the second window would also have to go into every
entry's evidence. The owner would then see two periods on one card, one of which the arithmetic
never used. Two fields describing one subject is the drift ADR-021's review removed from its own
draft.

### Give each entry its own window: the months that product had rows
A product with rows only in March and May would read `2026-03..2026-05`, which hides that
January and February were considered and held no row. That is the distinction ADR-011 exists to
keep, and the boundary is a property of the run, not of the product.

## Consequences

**We accept:**
- §7.1's split moves: the importer stops cutting, and the summary loses three columns.
- A degraded #105-type day publishes a different, aligned flagged set.
- The boundary must be added to `inputs_digest` explicitly.
- The importer's window tests move to `load_inputs`, where the cut now lives.
- The committed browser fixture needs no change: its stock date is 2026-08-02, so the cut
  keeps every month before 2026-08, which is the `2026-01..2026-07` it already carries.

**We gain:**
- One cut per run. #144's field, #150's window and the figures agree by construction, every
  day.
- #105 finding 2 disappears instead of being refused.
- No new reason, wording, column or probe.
- The importer no longer needs the stock date, so its two date rules become none.
- `reconcile_months` counts months.

**We will know it was wrong if:** the owner checks a card against his own January–May records
and still cannot reproduce its receipts. That would mean the months are right and the summing is
not; see the next section for one way that happens.

## Found while measuring, and not decided here

Filed as #156. Read from the local silver tables:

- **`reconcile_months` and `months_present` count rows, not months.** 28 barcode-month pairs carry
  two rows, across 13 barcodes, and 12 summary rows carry a `reconcile_months` larger than the
  months they span. This ADR's cut counts distinct months (Decision, part 1).
- **The sums add both rows.** In all 28 pairs the units and receipts are identical: 5 pairs are
  identical in every field and 23 differ only in `cost_price`. Nine of the 13 barcodes are
  ADR-019 conflicting duplicates and never reach detection. **Four do reach it.** None of the
  four is flagged today. On an August count, though, `7622300489427` would be flagged with
  receipts 20 and units 8 over two months, which are doubled if its lines are one sale reported
  twice. Deciding that needs someone to read the raw reports, not the engine to guess.

## Reversibility

Easy. The importer's cut can be restored and the figures read from the summary again. Nothing
keys on the window's value, so nothing needs migrating in either direction, and the digest
change reverts with the code.

## Implementation — for `smartshelf-engineer`, once accepted

**Files:**
- Modify:
  - `src/engine/inputs.py`: the cut, the figures and the digest.
  - `src/internal_pos/sales_importer.py`: drop `inventory_as_of` and the three columns.
  - `src/engine/run.py`: `_sales_import` stops reading the POS vintage.
  - `src/engine/reconciliation.py`: the carved window.
  - `scripts/import_yomyom_sales.py`: drop its date.
  - `src/engine/stock_date.py`: its docstring only. It names `_sales_import` as one of the two
    places that ask for the stock date; after the change they are `load_inputs` and
    `reconciliation.run`.
- Test:
  - `tests/engine/test_unknown_reconcile_window.py`: re-point the importer tests at
    `load_inputs`; `:401` and `:420` keep their meaning.
  - `tests/engine/test_reconciliation.py` and `tests/engine/helpers.py`: `make_inputs` gains a
    sales vintage whose `reconcile_before` follows its POS `as_of` of 2026-08-02, so every
    existing window, including `:51`, holds.
  - `tests/engine/test_inputs.py`
  - `tests/engine/test_run.py`
  - `tests/internal_pos/test_sales_importer.py`: its three `import_sales` calls pass
    `inventory_as_of`, and one asserts reconcile figures the importer no longer writes.

**Interfaces:**
- Summary parquet rows lose the three `reconcile_*` columns.
- `inputs.sales_summary` rows carry them, cut at load.
- `vintages.sales.reconcile_before` has the same meaning and is now true every day.
- `capabilities.reconciliation.window` is the carved `EvidenceWindow`.
- `inputs_digest` covers the boundary.

**Steps:**
1. **Boundary test first (rule 12).** Drive `run_engine` in print mode over copied real-shaped
   silver through the #105 sequence, and read the artefact it returns. The flagged set must
   equal the clean-import control's, with window `2026-01..2026-07` and `reconcile_before`
   `2026-08`. Today it fails with 139.
2. **Normal night.** Entries must be identical to today's in ids, order and every evidence value
   but `window_id`, which is `2026-01..2026-05`, and the figure's `thresholds.window` must match.
3. **Protected (#102).** An unusable stock date must leave the three figures null and
   reconciliation `unknown_stock_date` with no findings. The existing probe pins that reason.
4. **The digest.** Identical files with count dates in two different months must give two
   digests; count dates within the same month must give one.
5. Run `npm run test:py`, vitest, `npm run check:signals` and `npm run check:independence`,
   then read the published artefact rather than a return value.

**On acceptance,** in the commit that flips the status, update:
- System Design §7.1 (the importer no longer cuts, and `load_inputs` does).
- §11.1 (`sales_summary`'s reconcile figures are cut at load).
- §11.2 (the `window` comment names both windows).
- §21 SPEC-002 (replace the pointers added with this ADR).
- The §19 row.
- `docs/README.md`.
- The accepted-ADR lists in `CLAUDE.md` and `.claude/SKILLS/HANDOVER.md`, checked
  byte-identical.

## Review, 2026-09-23

This ADR was reviewed adversarially against the code and the artefact before handover, the same
way ADR-021 was, and **the review changed the decision.** The first draft stamped the boundary
on the summary.

| # | Finding | Outcome |
|---|---|---|
| C1 | The draft's new `unavailable_reason` fails `test_unavailable_reasons.py`, which requires owner-approved copy in three languages | Verified. The new decision needs no new reason |
| I1 | The draft said the owner sees the period on "each of the 355 cards". `EntryCard` renders only on the daily surface, at most three reconciliation cards at a time | Verified and corrected above |
| I2 | The draft missed cutting once where the stock date meets the reports | Verified by simulation (above) and adopted |
| I3 | The stamp would change #144's field on refusing days, and a second writer cuts with `date.fromisoformat` | Verified. Both are moot now that the importer takes no date |
| I4 | The draft's new refusal had no boundary probe | Moot: there is no new refusal. Step 1 is the boundary test for this decision |
| I5 | The duplicate lines double the sums, not only the month count, and the issue was not yet filed | Verified, described above, filed |
| I6 | §21 did not name ADR-026 | Pointers added to the SPEC-002 rows, marked as not yet accepted |

The review reran the first reproduction and matched its normal-night and #105-day rows. The
control row and the cut-once simulation were run after the review, in response to I2; both scripts
are attached to the pull request. Every file:line citation and every artefact figure was
confirmed. Of the minor findings, the template fields, the digest, reversibility and the stale
fixture are folded in above, and the scripts are attached to the pull request.

## Binds

| F# | How this constrains it |
|---|---|
| F2 | The reconcile window is cut once per run at the run's own stock date; reconciliation publishes that cut |
| F6 | The period on a reconciliation card changes value, not shape; no surface code changes |
| F7 | `vintages.sales.reconcile_before` and the capability's window state one cut; `inputs_digest` covers it |
