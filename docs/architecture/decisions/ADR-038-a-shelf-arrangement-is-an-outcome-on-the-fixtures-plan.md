---
ID: ADR-038
Title: A shelf arrangement is the owner's "acted" outcome on that fixture's plan entry
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-10-04
Parent: [System Design](../system-design.md) §19
Related Specs: F12-S1 (FR-201 … FR-207, INV-089, AC-190)
Inputs: [docs/features/F12-planogram/specs/F12-S1-planogram.md, ADR-003, ADR-009, ADR-029, ADR-034, D-1, D-22]
Updated: 2026-10-04
---

# ADR-038 — A shelf arrangement is the owner's "acted" outcome on that fixture's plan entry

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

F12-S1 measures what a plan did in his store (FR-201 … FR-207, the owner's "yes" of 2026-10-04).
The measurement splits each arrangement's sales into a before window and an after window, so
it needs the date he rearranged a fixture, recorded by him on the day. Owner state already
holds his outcomes on entries, written only by the browser and only by the owner (ADR-003,
ADR-029). Reorder's approvals reuse that model (ADR-034).

## Decision

1. **Each fixture's plan is an entry of a new permanent family, `shelf.plan`.** Its variant is the
   plan's date (ISO). Its id follows ADR-009's construction, with the fixture's id where a
   product's barcode goes. The id is the same every night that publishes the same plan date, and
   different for a later plan.
2. **"I've arranged this shelf" records the existing `acted` status on that entry.** The snapshot
   is `{signal_family: "shelf.plan", capability: "shelf_plan", fixture, plan_date, facings:
   {barcode: n}}`: the facings he followed, with no ₪ field (D-1) and no name (D-22). The time
   of the outcome is the arrangement's date.
3. **Nothing else maps onto it.** `declined` and `deferred` are not offered on a plan.
4. **The engine reads arrangements** from the pulled owner state, as it reads every outcome
   (ADR-003). The measurement uses only `acted` outcomes of `shelf.plan`.

## Rejected options

### A new kind of owner-state record for arrangements
It would need new Firestore rules, new pull code and new tests, to hold what the outcome model
already holds: who acted, on what, and when. ADR-034 reused outcomes for the same reason.

### The team records the arrangement date in the layout file
The date is the boundary between the two windows, so the whole measurement rests on it. It has to
be his act, recorded when he does it. A date the team writes down later, from a message, moves
the boundary by however many days the message took, and nothing would show the error.

### Infer the arrangement from the sales
That is circular. A change in sales would be both the evidence that he rearranged the shelf and
the effect being measured.

## Consequences

**We accept:** the plan publishes one entry per fixture, which the capability's entries were not
otherwise needed for.

**We gain:** no new storage, rules or pull code, and arrangements fall under the existing role
rule: the team cannot write them (ADR-029).

**We will know it was wrong if:** he rearranges fixtures without pressing the button, so
measurements never start. Then a reminder on the plan, or the photograph check F12-S1 leaves out
of scope, becomes the next decision.

## Reversibility

Easy. Outcomes are additive, and a different recording would only change where the engine reads
the date.

## Binds

| F# | How this constrains it |
|---|---|
| F12 | Arrangements are `acted` outcomes on `shelf.plan` entries (F12-S1 FR-201) |
| F13 | The pilot measurement counts outcomes; `shelf.plan` is a family it will see |
