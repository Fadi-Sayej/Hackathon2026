---
ID: ADR-022
Title: A barcode-less row is identified by its name, under ADR-019's rule
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-13
Parent: [System Design](../system-design.md) §19
Related Specs: F2-S1, F6-S1
Inputs: [ADR-009, ADR-019, issue #89, src/engine/inputs.py _resolve_identity, src/engine/reconciliation.py]
Updated: 2026-09-13
Amends: ADR-019 — the sentence "A barcode-less row cannot be grouped and is kept as itself"
---

# ADR-022 — A barcode-less row is identified by its name, under ADR-019's rule

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

ADR-019 groups rows by barcode: rows that agree on every field are the same row twice and
collapse; rows that disagree leave the population and are published as
`hygiene.conflicting_duplicate`. It exempted one case in a single sentence:

> A barcode-less row cannot be grouped and is kept as itself — `hygiene.no_identifier`
> already reports it.

That was safe only while barcode-less names were unique. **On the pilot they are not.** Of
308 barcode-less rows, 27 names are listed more than once — tuna sandwich at the drive
counter and at the barista counter, avocado sandwich three times, salmon bagel twice.

"Kept as itself" then fails in the one place it cannot afford to. `entry_id` falls back to
the name when there is no barcode, so rows sharing a name publish their findings under **one
id**. The artefact carried 43 such ids over 54 surplus entries (#89). `ownerState.js` keys
the owner's outcomes by id and `compose.js` treats any entry whose id has an outcome as
settled — so **the owner marking one of them done silently settles the others**, during the
pilot, with nothing on screen to say so.

## What the data can and cannot tell apart

Checked against the export rather than assumed, because the fix depends entirely on it:

| Candidate identity | Separates the duplicates? |
|---|---|
| name | no — it is the thing that repeats |
| name + department | no — salmon bagel is twice in the same department |
| name + department + shelf price | no — both at 34.90 |
| position in the export | **yes, within one export — but not across exports** |

Position is the only field that separates them, and ADR-009 requires an id stable across
runs. An id built on position re-attaches the owner's recorded decision to whichever row
lands in that position next week — which is worse than a collision, because it is silent in
both directions.

**So there is no stable identity that tells these rows apart.** That is not a gap in the
code; it is a fact about the records.

## Decision

**A barcode-less row is identified by its `product_name`, and grouped under exactly
ADR-019's rule.**

- Rows sharing a name that agree on every identity field are the same row twice and collapse.
- Rows sharing a name that disagree leave the product population and are published as
  `hygiene.conflicting_duplicate`, carrying the disagreeing fields and every value.
- A barcode-less row with a unique name is unaffected.
- A conflict record's id falls back to the name, the same way `_hygiene_entries` already
  does. `entry_id(family, None)` would give **every** barcode-less conflict one shared id —
  #89 again, inside the one record that exists to report it.

This is not a new rule. It is ADR-019's rule, applied to the identity the engine was already
using for these rows everywhere except `_resolve_identity`.

## Why the owner is better served, not just the id

Two rows named «כריך אבוקدو» with different departments and different stock are not two
findings. They are one question: *is this the same product listed twice?* Before, he saw
several separate "no identifier" and "negative stock" findings that shared an id, and
settling one settled the rest. Now he sees one record that names the disagreement. That is
both honest and the more useful thing to act on.

## Measured effect

The full engine, run in print mode over one copy of the pilot data, `main` against this
change. No capability changed status; every capability's findings are identical except
`hygiene`'s.

| Figure | before | after |
|---|---|---|
| duplicate entry ids / surplus entries | 43 / 54 | **0 / 0** |
| `hygiene.conflicting_duplicate` | 42 | 68 |
| `hygiene.negative_stock` | 614 | 578 |
| `hygiene.no_identifier` | 308 | 248 |
| `catalogue_lifecycle.excluded_no_identifier` | 308 | 248 |
| `competitor_position.catalogue` | 7,583 | 7,523 |
| `competitor_position.structurally_uncomparable` | 782 | 722 |

`npm run check:signals:v1` and `check:independence` both pass over the same data.

**The last row moves an owner-facing figure** that `docs/pilot/owner-conversation-2026-09.md`
and the readiness gate's run 3 both quote. Those are corrected in the same change.

## Rejected options

### Keep them "as itself" and make the ids unique
Needs a stable field that separates the rows, and the table above shows there is none. Every
way of making the ids unique either uses position, which breaks ADR-009 silently, or hashes
something that also repeats.

### Group by name and department
Stops at the first counter-example in the data: the salmon bagel is duplicated inside one
department. It would also split tuna-at-drive from tuna-at-barista, which may or may not be
two products — and deciding that is exactly the question this record asks the owner instead
of answering for him.

### Leave it until the owner fixes his listings
The collision is live in the artefact now. It does not reach the daily surface today only
because `hygiene` is last in `unvalued_order` — that is ordering, not safety.

## Consequences

**We accept:** 60 barcode-less rows leave the product population and appear as 26 conflict
records instead, so three published hygiene counts, one catalogue count and two competitor
counts fall. A name that is genuinely two products — two counters selling a same-named
sandwich — is reported as a conflict until the owner distinguishes them. That errs toward
asking, which is D-3's direction.

**We gain:** no entry id is shared, so no owner decision can settle a finding he never saw.

**We will know it was wrong if:** the owner confirms that many same-named barcode-less rows
are genuinely different products. Then the honest fix is on his side — a barcode or a
distinct name — and this record is what tells him which rows need one.

## Binds

| F# | How this constrains it |
|---|---|
| F2 | `hygiene.conflicting_duplicate` covers barcode-less names; its id is the barcode or, failing that, the name |
| F6 | No two surface candidates share an id; an outcome cannot settle an entry the owner did not act on |
