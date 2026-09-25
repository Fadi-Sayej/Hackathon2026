---
ID: ADR-034
Title: An order suggestion is identified by its product and order day; a disagreement is a question keyed by its product
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-25
Parent: [System Design](../system-design.md) §19
Related Specs: F8-S1 (FR-158, FR-159, FR-161, FR-162, FR-163, INV-075, INV-078, C-67, C-68, AC-154); F5-S1 (FR-089, FR-090); F13-S1
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, D-20, ADR-001, ADR-003, ADR-009, ADR-016, ADR-027, system-design.md §10.1, src/engine/owner_questions.py, src/owner/ownerState.js]
Updated: 2026-09-25
---

# ADR-034 — An order suggestion is identified by its product and order day; a disagreement is a question keyed by its product

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

Two identity schemes already exist (§10.1):
- **An entry's** id is `sha256(signal_family ‖ barcode ‖ variant)[:16]`, with a permanent
  `signal_family` (ADR-009). Its outcome's status is one of `acted`, `declined` or `deferred`
  (`ownerState.js`), and the snapshot carries the family (ADR-016).
- **A question's** id is `sha256(fact ‖ barcode)`. Its answer lives at
  `answers[barcode][fact]`, with status `answered` or `deferred` (`owner_questions.py`,
  `ownerState.js`), and F5-S1 FR-090's revise path works on it.

F8-S1 needs both kinds of thing:
- **Suggestions are entries.** Each is one entry every night until its order day, and an
  approval holds for it (FR-163, INV-078).
- **The disagreement is a question** in F5's panel (FR-158, C-68, AC-150). It is raised once
  per product, ever (D-20, INV-075), and it can be revised (FR-159).

## Decision

1. **A suggestion is an entry of a new permanent family, `order.suggestion`.** Its variant is
   the order day as an ISO date. The id is the same on every night before that day, and
   different after it.
2. **Its outcomes map onto the existing statuses.**
   - Approve means `acted`. The snapshot is `{signal_family, capability: "order_quantity",
     barcode, order_day, kind: "net" | "gross", suggested_quantity, approved_quantity?}`,
     with no ₪ field (D-1). `approved_quantity` is his quantity when he changed it (FR-161).
   - Dismiss means `declined`.
   - `deferred` means not now; the suggestion stays open until its order day.
3. **The disagreement is a question with a new fact, `market_disagreement`.** Its id is
   `sha256("market_disagreement" ‖ barcode)`, and his answer lives at
   `answers[barcode]["market_disagreement"]`. The engine suppresses the question for good
   once it is answered (D-20, which prevails over FR-089's re-ask, F8-S1 C-67). FR-090's
   revise path still works.
4. **A schedule change is detected and published by the engine.** A department's schedule
   can change after an approval recorded for a pending order day. The engine then publishes
   `schedule_changed` on the new suggestion, and the page shows it (ADR-001). An outcome
   never carries to the new day.
5. **Approved orders is a projection.** The page lists the `acted` suggestion outcomes,
   grouped by department. The CSV export writes those same fields: product, barcode,
   quantity, order day. Listing recorded outcomes computes no business rule.

## Rejected options

### Suggestion variant = the run's date
A new id every night. A weekly department's order would be suggested seven times, and an
approval given on Thursday would not hold on Friday (INV-078).

### Suggestion variant = a cycle number
Cycle numbers depend on the schedule. Editing a schedule would renumber every cycle, and
every recorded outcome would stop matching, silently. That is the failure ADR-009 exists to
prevent.

### The disagreement as an entry of an `order.disagreement` family
F8-S1 makes it a question in F5's panel (FR-158, AC-150). Questions are identified by fact
and barcode, and their answers are revised through `answers`. A second scheme would hold one
question in two stores, and the revise path would not reach it.

### Key the disagreement by date
It would raise the same disagreement again on a later date, and D-20 forbids asking about
that product again.

## Consequences

**We accept:** a pending approval does not follow a schedule change. The engine says so
(Decision 4).

**We gain:**
- Approvals that hold across nights.
- No double suggestion.
- A disagreement that uses F5's question machinery, revise path included, and cannot come
  back.

**We will know it was wrong if:** the owner approves orders for a day other than the
suggestion's order day, for example by ordering early. Identity would then need the actual
order date he chose, and a superseding ADR.

## Reversibility

Easy before the first outcome or answer is recorded. After that, the family and the fact are
permanent, like every name in §10.1.

## Binds

| F# | How this constrains it |
|---|---|
| F8 | FR-158, FR-159, FR-161, FR-162 and FR-163 use these ids |
| F5 | The question kind `market_disagreement` joins the population FR-084's limit governs |
| F13 | Measurement groups outcomes by `signal_family` (ADR-016); `order.suggestion` is its V2 group |
