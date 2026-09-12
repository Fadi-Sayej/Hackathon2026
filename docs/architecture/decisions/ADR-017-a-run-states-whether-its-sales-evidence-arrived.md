---
ID: ADR-017
Title: A run states whether its sales evidence arrived
Status: Draft
Owner: smartshelf-architect
Date: 2026-09-12
Parent: [System Design](../system-design.md) §19
Related Specs: F2-S1 (SPEC-002 §11), F7-S1 (provenance), F6-S1 (the surface renders the window)
Inputs: [docs/reviews/phase-0-1-execution-report.md, src/engine/run.py, src/internal_pos/sales_importer.py]
Updated: 2026-09-12
---

# ADR-017 — A run states whether its sales evidence arrived

**Status:** Draft · **Recorded in:** [System Design](../system-design.md) §19

## Related Specs

F2-S1 §11 (detection is unavailable without sales evidence), F7-S1 (every figure carries
its provenance), F6-S1 (every count renders its window — ARCH-DRIVER-007).

## Context

Found while building the Task 1.9 independence probe, and measured on the real data rather
than reasoned about.

`import_sales` over a directory with no monthly reports returns `monthly_rows: 0`,
`window: None`, and **writes nothing**. The previous run's `sales_summary.parquet` and
`sales_monthly.parquet` stay on disk, `load_inputs` reads them, and the run continues on
the older evidence. Observed output of exactly that run:

| | value |
|---|---|
| `sales_import` step status | **`ok`** |
| `vintages.sales.months` | `2026-01 … 2026-07` — the stale window, reported as this run's |
| `reconciliation` | `available`, **460 flagged**, `notes: []` |

**The artefact is indistinguishable from a run where the reports did arrive.** Nothing
compares the window to the run date, the step that imported nothing calls itself `ok`, and
the vintage block — the one place a reader would look — states the stale months as fact.

This is not the coupling SPEC-002 §11 forbids; that independence is now proven across the
real boundary by `scripts/check_independence.py`. It is the quieter failure underneath it:
the pipeline looks healthy on a day it received nothing.

CLAUDE.md rule 12 is about a signal that is built and moves nothing. This is its
converse — a signal that keeps moving after its input stopped arriving — and the pilot is
the worst place to discover it, because a late report is normal and a wrong count is not.

## Decision

**A run states whether this run's sales evidence arrived, and a run that continued on
older evidence is never `ok`.**

Three parts, all in the orchestrator and the vintage block:

1. `_sales_import` contributing **no rows** is reported as step status `degraded`, not
   `ok`, with the reason.
2. The run verdict is at least `degraded` in that case — the same treatment an unreachable
   owner state already gets, for the same reason: it ran, and something is not as it
   should be.
3. `vintages.sales` gains **`imported_this_run: boolean`**. Without it the artefact cannot
   distinguish "these are the months we just imported" from "these are the months still on
   disk", and no consumer can recover the difference afterwards.

Detection keeps publishing. A July stock discrepancy is still a discrepancy in September;
what changes is that its age is now stated rather than implied.

## Rejected options

### Leave it — the vintage block already carries the months
It carries them without saying when they arrived, which is the whole defect. A reader
would have to compare `vintages.sales.last` against `generated_at` and know that the gap
means the import failed rather than that the store had a quiet month. Nothing in the
artefact says which. "Recoverable by a sufficiently suspicious reader" is not provenance.

### Detection refuses stale evidence and publishes `unavailable`
Too blunt, and it destroys real findings. The 460 flagged products are genuinely flagged;
their evidence is older than today, not wrong. Refusing would empty the daily surface on
every late-report day — which, for a store owner emailing CSVs by hand, is a normal day.
It would also teach the owner that the product breaks when he is slow, which is the
opposite of the pilot's purpose.

### Have `import_sales` clear the silver tables when no reports arrive
Deletes evidence because it is old. The tables are the only copy the engine has; a late
report would destroy the previous window rather than extend it, and a run that arrived
after a collector hiccup would surface nothing at all.

## Consequences

**We accept:** a nightly run on a late-report day is `degraded`, so `degraded` becomes a
state the operator sees routinely and must be able to read the reason for. That is the
cost of the run status meaning something.

**We gain:** the artefact distinguishes the two runs; a stale window is visible in the one
block that already travels with every figure; and the surface can render the age of the
evidence it is reasoning from, which is what ARCH-DRIVER-007 requires of every count.

**We will know it was wrong if:** operators start ignoring `degraded` because it fires so
often that it carries no information — in which case the reasons need separating, not the
rule removing.

## Implementation

Not yet scheduled. The change is in `src/engine/run.py` and the vintage assembly in
`src/engine/inputs.py`; it belongs with the nightly workflow in **Phase 3**, which is not
yet written. It must land before the pilot's first late-report day, whichever comes first.

## Binds

| F# | How this constrains it |
|---|---|
| F2 | Detection publishes on older evidence, and the run says the evidence is older |
| F6 | The surface may render the evidence window's age; it is available in the artefact |
| F7 | `vintages.sales` gains a field, so provenance states arrival as well as coverage |
