---
ID: ADR-030
Title: F8's own sales arrive as daily reports, one file per day, and a missing day stays missing
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-25
Parent: [System Design](../system-design.md) §19
Related Specs: F8-S1 (FR-143, FR-144, FR-149, INV-070, INV-072, ASM-064, ASM-065, OQ-904)
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, CLAUDE.md rules 5, 6 and 13, .gitignore, commit a3aca1e, ADR-011, ADR-017, ADR-019, ADR-028 §4, D-12, D-22, src/internal_pos/sales_importer.py, .github/workflows/collect-daily.yml, data/internal/raw_pos/yomyom/sales/]
Updated: 2026-09-26
---

# ADR-030 — F8's own sales arrive as daily reports, one file per day, and a missing day stays missing

**Status:** Accepted (2026-09-26, by the repository owner, on PR #200) · **Recorded in:** [System Design](../system-design.md) §19

## Context

F8-S1 computes quantities only from **report days**, meaning sales and deliveries per
product per day (FR-143). The only sales evidence today is seven **monthly** reports.
Dividing them into days is what Task 0.6 deleted `units_sold_30d` for (CLAUDE.md rules 5 and
13), and ADR-028 §4 says V2 builds on real per-day demand.

The monthly reports are the POS's own sales report, «דוח מכירות». They carry units (`מכר`)
and deliveries (`כניסות מלאי`), and have no date column. The importer reads the month from the
file name (`month_from_filename`). The files are committed under
`data/internal/raw_pos/yomyom/sales/`, which is how the nightly run can read them. That
directory is gitignored (`.gitignore`, `data/internal/raw_pos/`): the seven files are tracked
only because commit a3aca1e force-added them. The column map also reads a missing
`כניסות מלאי` column as 0.0, which would turn "not reported" into "zero deliveries".

Whether the POS can run that report for a single day, and who sends it how often, is still
open (F8-S1 OQ-904, owner conversation #7).

## Decision

1. **The input is the same report, run for one day.**
   - One file per day, named with the ISO date: `דוח מכירות יום YYYY-MM-DD.csv`.
   - The files are committed under `data/internal/raw_pos/yomyom/sales_daily/`.
   - Git cannot re-include a path under an ignored directory, so a plain negation would not
     work. The ignore rules are restructured instead:
     - `data/internal/raw_pos/*`
     - `!data/internal/raw_pos/yomyom/`
     - `data/internal/raw_pos/yomyom/*`
     - `!data/internal/raw_pos/yomyom/sales_daily/`

     Tested on a scratch repository: the daily files are tracked, and every sibling stays
     ignored. The implementation task makes the change, and adds it to CLAUDE.md rule 6 as the
     second exception, beside `data/internal/snapshots/`.
   - The day comes from the file name, exactly as the month does today, because the report
     carries no date.
   - Seven daily files sent together once a week are equally valid.
2. **A daily importer sits beside the monthly one.**
   - It reuses the monthly importer's column map and its duplicate-line rule (ADR-019).
   - It writes `silver_pos/sales_daily.parquet`: `barcode, day, units, receipts`.
   - `receipts` is **null, never 0**, when a file has no `כניסות מלאי` column. Each report day
     records `deliveries_reported: true | false`. A day without it cannot carry a stock count
     forward (F8-S1 FR-149).
   - A product absent from a day's file gets **no row** (ADR-011). Inside a department the
     evidence itemises, F8-S1 reads that as no sale that day (ASM-065).
   - **It says nothing about deliveries.** The report lists only products that sold: none of
     the 3,942 monthly rows has zero units (`sales_monthly.parquet`). So a delivery of a
     product that did not sell that day is invisible. For a product-day with no row,
     deliveries are **unknown, never zero**. A stock count can therefore be carried forward
     only across days on which the product has a row (F8-S1 FR-149). Otherwise the
     suggestion is gross.
3. **Report days are the files that parsed; everything else is missing.**
   - A calendar day with no file, or with a file that failed to parse, is a **missing day**.
     It is recorded as such and never read as zero sales (INV-072).
   - A file that fails is named in the run's steps.
4. **The vintage says what arrived**, read from the files present with no memory of
   earlier runs (ADR-004). `vintages.sales_daily` carries:
   - `first_day` and `last_day`;
   - `report_days`, a count;
   - `missing_days`, the list within the window plus the freshness limit (F8-S1 FR-144's
     policy);
   - `deliveries_missing_days`.

   ADR-017's rule extends to it in one case only. **Once daily files have started to arrive**,
   a run whose latest report day is older than the freshness limit is `degraded`. Before the
   first file, F8 is unavailable and says it waits for daily sales, and the run is not
   degraded by it. A weekly batch therefore leaves the run `ok` on the six nights between
   batches.
5. **The monthly reports stay as they are.** They keep feeding F2 and F4, and never F8
   (INV-070).
6. **The window and freshness values are policy, not import logic.** The 28 days, 21
   report days and 7-day freshness are F8-S1's policy values (FR-144). They live in
   `configs/policy.yaml`, and the importer knows nothing of them.

## Rejected options

### Derive daily sales from consecutive stock snapshots
`src/snapshots/velocity.py` already exists and would need no new export. But a stock
decrease is sales only if the counts are right and no delivery arrived. The owner calls the
counts unreliable in both directions (D-1's reason), and 261 of the 1,518 products he sells
show a negative count (`catalogue.json`, 2026-09-24). Deliveries between snapshots are not
recorded. The daily figure would be invented. The System Design already records
snapshot-delta velocity as inert (§4, S14).

### Divide the monthly reports into days
Forbidden three times over: CLAUDE.md rule 13 (weekday cycles are not measurable), Task 0.6
(the deleted `units_sold_30d`), and ADR-028 §4. It is also F8-S1 INV-070.

### Keep the directory ignored, and force-add every file
That is how the monthly files got in (a3aca1e). For a file arriving every day it is a trap.
A forgotten `-f` is refused, with a warning that is easy to miss in a batch of seven files.
The file stays out, and the engine then reads a missing day.

### Accept weekly reports as well
A week's total cannot size a daily order cycle without dividing it. F8-S1 is per-day only
(FR-143). Weekly *batches of daily files* stay allowed (Decision 1).

### Pull sales from the POS by API
It would be a second POS integration, which D-12 still excludes (D-22 changed only its user
clause). It would also put a live POS credential in the nightly run. The export is manual
today, and the owner's commitment (PRD §7) is an export, not an integration.

## Consequences

**We accept:**
- Someone must export the daily files and commit them at least weekly (F8-S1 FR-144). A
  missing day is tolerated, not required. Until OQ-904 is answered, F8 publishes nothing.
- The daily files are committed to the repository, with the same exposure the monthly ones
  already have.

**We gain:**
- Per-day demand without inventing it.
- Deliveries per day, which let a stock count be carried forward. That works only for
  products that sell every day, because the report lists no one else (Decision 2). Every
  other suggestion is gross.
- One importer shape for both grains.

**We will know it was wrong if:**
- The POS cannot run its sales report for a single day.
- A daily report covers different departments from the monthly one.
- Exports arrive so irregularly that the window rarely holds 21 report days.

## Reversibility

Easy. The daily importer is additive. Removing it returns F8 to "waiting for sales per day",
and nothing else reads its table.

## Binds

| F# | How this constrains it |
|---|---|
| F8 | FR-143, FR-144 and FR-149 read `sales_daily.parquet` and `vintages.sales_daily`, never the monthly tables |
| F2, F4 | Unchanged: they keep the monthly reports |
