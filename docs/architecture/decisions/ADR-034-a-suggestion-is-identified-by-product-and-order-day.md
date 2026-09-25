---
ID: ADR-034
Title: An order suggestion is identified by its product and order day; a disagreement by its product
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-25
Parent: [System Design](../system-design.md) §19
Related Specs: F8-S1 (FR-159, FR-161, FR-162, FR-163, INV-075, INV-078, AC-154); F13-S1
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, D-20, ADR-001, ADR-003, ADR-009, ADR-016, system-design.md §10.1]
Updated: 2026-09-25
---

# ADR-034 — An order suggestion is identified by its product and order day; a disagreement by its product

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

ADR-009 makes an entry's identity `sha256(signal_family ‖ barcode ‖ variant)[:16]`. Here
`signal_family` is a permanent string, never renamed or reused (§10.1). Outcomes in owner
state are keyed on that id, and ADR-016 makes their snapshot carry the family.

F8-S1 requires three things of identity:
- A suggestion is **one entry every night until its order day**, and an approval holds for
  it (FR-163, INV-078).
- Once that day has passed, the next order day's suggestion is **new**.
- A disagreement is raised **once per product, ever** (D-20, INV-075).

## Decision

1. **Two new permanent families**, added to §10.1:
   - **`order.suggestion`**, variant = the order day as an ISO date. The id is the same on
     every night before that day, and different after it.
   - **`order.disagreement`**, variant = `""`. There is one id per product, for good.
2. **The suggestion outcome snapshot** is `{signal_family, capability: "order_quantity",
   barcode, order_day, kind: "net" | "gross", suggested_quantity, approved_quantity?}`.
   - `approved_quantity` is his quantity when he changed it (F8-S1 FR-161).
   - The snapshot carries no ₪ field (D-1).
3. **The disagreement outcome** is his answer, recorded as owner state (ADR-003), keyed on
   the disagreement's id. The engine suppresses every later raising of that id (FR-159).
4. **Approved orders is a projection.** The page lists the approved suggestion outcomes,
   grouped by department. The CSV export writes those same fields: product, barcode,
   quantity, order day. Listing recorded outcomes computes no business rule, so ADR-001
   holds.

## Rejected options

### Variant = the run's date
A new id every night. A weekly department's order would be suggested seven times. An
approval given on Thursday would not hold on Friday, which F8-S1 INV-078 forbids.

### Variant = a cycle number
Cycle numbers depend on the schedule. Editing a department's schedule would renumber every
cycle, and every recorded outcome would stop matching, silently. That is the failure ADR-009
was written to prevent.

### No variant
One outcome per product for good. Approving one order would suppress every later order of
that product.

### Key the disagreement by date
It would raise the same disagreement again on a later date, and D-20 forbids asking about
that product again.

## Consequences

**We accept:** a pending suggestion's order day changes if the owner changes that
department's schedule. Its outcome then does not carry to the new day, and the page says the
schedule changed.

**We gain:**
- Approvals that hold across nights.
- No double suggestion.
- A disagreement that cannot come back.
- Both families stay usable by F13's grouping (ADR-016).

**We will know it was wrong if:** the owner approves orders for a day other than the
suggestion's order day, for example by ordering early. Identity would then need the actual
order date he chose, and a superseding ADR.

## Reversibility

Easy until the first outcome is recorded. After that the two families are permanent, like
every family in §10.1.

## Binds

| F# | How this constrains it |
|---|---|
| F8 | FR-159, FR-161, FR-162 and FR-163 use these ids |
| F13 | Measurement groups outcomes by `signal_family` (ADR-016). The two new families are its V2 groups |
