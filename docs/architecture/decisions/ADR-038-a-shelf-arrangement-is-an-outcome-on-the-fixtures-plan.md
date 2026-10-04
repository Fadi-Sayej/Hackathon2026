---
ID: ADR-038
Title: A shelf arrangement is the owner's "acted" outcome on that fixture's plan entry
Status: Accepted
Owner: smartshelf-architect
Date: 2026-10-04
Parent: [System Design](../system-design.md) §19
Related Specs: F12-S1 (FR-192, FR-201 … FR-209, INV-089, AC-190, AC-196)
Inputs: [docs/features/F12-planogram/specs/F12-S1-planogram.md, ADR-003, ADR-009, ADR-016, ADR-029, ADR-034, D-1, D-22]
Updated: 2026-10-04
---

# ADR-038 — A shelf arrangement is the owner's "acted" outcome on that fixture's plan entry

**Status:** Accepted (2026-10-04, by the repository owner: "approved", with F12-S1, whose requirements are written on it) · **Recorded in:** [System Design](../system-design.md) §19

## Context

F12-S1 measures what a plan did in his store (FR-201 … FR-209, the owner's "yes" of 2026-10-04).
The measurement splits each arrangement's sales into a before window and an after window, so it
needs the date he rearranged a fixture, recorded by him on the day. It also needs the plan's
window, because the before window ends where that window begins, and the facings he followed.
Owner state already holds his outcomes on entries, written only by the browser and only by the
owner (ADR-003, ADR-029). Reorder's approvals reuse that model (ADR-034).

## Decision

1. **Each fixture's plan is an entry of a new permanent family, `shelf.plan`**, enumerated in
   §10.1 and in the engine's `SIGNAL_FAMILIES`. The plan's date is the date of the nightly run
   that published it, so each night's plan is a new entry.
2. **Its id is ADR-009's construction with no barcode**, and the variant
   `<fixture id>|<plan date>`. The fixture id never passes through the barcode normalisation,
   which strips leading zeros and would make fixtures "01" and "1" one entry.
3. **The entry's fields** (§11.3):
   - `barcode`, `product_name` and `department` are null: the entry is a fixture, not a
     product;
   - `action` is `arrange_shelf`, a new value;
   - `characterisation` is `shelf_plan`;
   - `evidence` carries the fixture, the plan's date, the plan's window, and per shelf its
     products with their facings;
   - `value` is null, and `ordering_key` is the fixture's order in the layout file.

   The artefact's schema admits these values for `shelf.plan` only.
4. **"I've arranged this shelf" records the existing `acted` status on that entry.** The
   snapshot is:

   ```
   { signal_family: "shelf.plan", capability: "shelf_plan", barcode: null,
     fixture, plan_date, plan_window: {first, last}, arranged_on,
     placements: { [barcode]: { shelf, facings, eye_level } } }
   ```

   It has no ₪ field (D-1) and no name (D-22). `arranged_on` is the day his device's calendar
   shows when he presses, and it is the boundary of the measurement. `recordOutcome` gains a
   `shelf.plan` branch, as it gained an `order.suggestion` one (ADR-034).
5. **The date is written once, on the device that records it.** For every other family, a
   second `recordOutcome` on the same entry rewrites `at`. On an acted `shelf.plan` entry, it
   changes nothing. `clearOutcome` (his undo) removes the arrangement, and its measurement with
   it.
6. **Every device shows the published arrangement.** The browser does not read owner state
   back (System Design §11.5; `remoteOwnerState.js`), so a device knows only its own presses.
   Shelf plan therefore shows each fixture's latest arrangement from `shelf_measurement`'s
   published output, and a device's own record only until the nightly has read it. While a
   fixture's measurement is running, the button warns that arranging it again ends it.
7. **Nothing else maps onto it.** `declined` and `deferred` are not offered on a plan.
8. **The engine reads arrangements** from the pulled owner state, as it reads every outcome
   (ADR-003). Only `acted` outcomes of `shelf.plan` are used, by `shelf_measurement` (F12-S1
   FR-208). An outcome whose entry is no longer published is still read: its snapshot carries
   everything the measurement needs, so no past artefact is read.
9. **The seam is tested.** `ownerStateContract.test.js` records one `shelf.plan` outcome through
   the real `recordOutcome`. The engine's reader and F12-S1's probe read that fixture, so both
   are tested against the shape the browser writes.

## Rejected options

### A new kind of owner-state record for arrangements
It would need new Firestore rules, new pull code and new tests, to hold what the outcome model
already holds: who acted, on what, and when. ADR-034 reused outcomes for the same reason.

### The fixture's id in the barcode slot
§11.3 reads `barcode` as a product's, and the id's construction normalises it as one. Fixture
"01" and fixture "1" would share an entry, and every reader of `barcode` would have to know that
some barcodes are fixtures.

### Enforce "written once" in `firestore.rules`
Outcomes are fields of one document, keyed by entry id. The rules cannot tell which family a
changed key belongs to, so enforcing it on that document would also freeze every other outcome.
Arrangements could move to a map document of their own, where an update passes only when no
existing key changes: adding or deleting one passes, rewriting one fails. It would cost:
- a new owner-state document, in the browser's record documents and in the engine's pull;
- an undo that deletes the field rather than writing a null;
- a `pushAll` that writes that document key by key, so one refused key does not block the rest.

That is the new kind of record rejected above, for one case. Decision 6 makes the published
arrangement the one every device shows instead, and F12-S1 ASM-082 states the case that
remains.

### Keep the latest press's time, as other outcomes do
The date is the boundary between the two windows. A second press a week later would move a week
of sales from before to after, and nothing would show it.

### The team records the arrangement date in the layout file
The whole measurement rests on the date, so it has to be his act, recorded when he does it. A
date the team writes down later, from a message, moves the boundary by however many days the
message took, and nothing would show the error.

### Infer the arrangement from the sales
That is circular. A change in sales would be both the evidence that he rearranged the shelf and
the effect being measured.

## Consequences

**We accept:**
- the plan publishes one entry per fixture per night, which the capability's entries were not
  otherwise needed for;
- the entry contract gains a case with no product and one action value;
- `recordOutcome` gains a family-specific branch, and one family whose date is written once;
- until the browser reads owner state back, an undo on one device can be reversed by another
  that also pressed, because `pushAll` re-sends a device's records on every load (F12-S1
  ASM-082).

**We gain:** no new storage, rules or pull code, and arrangements fall under the existing role
rule: the team cannot write them (ADR-029).

**We will know it was wrong if:** he rearranges fixtures without pressing the button, so
`shelf_measurement` stays `no_arrangement_recorded`. Then a reminder on the plan, or the
photograph check F12-S1 leaves out of scope, becomes the next decision.

## Reversibility

Easy before the first arrangement is recorded. After that, the family and its snapshot are
permanent, like every name in §10.1.

## Binds

| F# | How this constrains it |
|---|---|
| F12 | Arrangements are `acted` outcomes on `shelf.plan` entries (F12-S1 FR-201), read by `shelf_measurement` (FR-208) |
| F13 | The pilot measurement counts outcomes by family; `shelf.plan` is one it will see, with one entry per fixture per night |
