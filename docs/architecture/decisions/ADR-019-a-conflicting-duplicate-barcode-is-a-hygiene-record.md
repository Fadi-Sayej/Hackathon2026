---
ID: ADR-019
Title: A conflicting duplicate barcode is a hygiene record, never a silent pick
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-12
Parent: [System Design](../system-design.md) §19
Related Specs: F2-S1 (hygiene), F1-S1, F6-S1 (AC-109)
Inputs: [docs/features/gaps-and-open-questions.md GAP-010, data/internal/silver_pos/yomyom_products.parquet, public/data/dashboard.json]
Updated: 2026-09-12
---

# ADR-019 — A conflicting duplicate barcode is a hygiene record, never a silent pick

**Status:** Accepted (2026-09-12) · **Recorded in:** [System Design](../system-design.md) §19

## Context

[GAP-010](../features/gaps-and-open-questions.md), measured 2026-09-12: 48 barcodes appear
twice in the POS export. **Seven pairs are byte-identical; 41 disagree** — on department
(one product filed under both `חטיפים מתוקים` and `מוצרי אלקטרונים`), and in some cases on
shelf price (`4062139003150` carries both **₪15.90 and ₪16.90**).

The engine shapes one product per **row**, so a duplicated barcode becomes two products.
Today `price_consistency` publishes **108 entries for 107 products**, two byte-identical and
sharing one `entry_id`, so the capability's `counts.above` disagrees with its own entry list.

`compose` will deduplicate for AC-109. That satisfies the acceptance criterion and **hides
the defect**: the owner stops seeing the product twice and never learns that his catalogue
says it costs two different amounts.

## Decision

**Product identity is resolved once, in `inputs.py`, and a conflict is reported rather
than resolved.**

1. Rows sharing a barcode whose every shaped field is equal are **collapsed**. Nothing is
   lost — it is the same row twice.
2. Rows sharing a barcode that disagree on any shaped field make that barcode
   **conflicting**. A conflicting barcode is:
   - **excluded from every capability population**, counted as `excluded_conflicting_duplicate`,
   - published as one hygiene record, `signal_family: hygiene.conflicting_duplicate`,
     action `fix_record`, carrying **the field names that disagree and both values**, and
     carrying **no money** (D-1, and the prices are precisely what is in doubt).
3. **No field is picked.** Not first-row, not last-row, not highest, not lowest. A product
   with two shelf prices has no shelf price the system can state, and D-3 says where a
   figure cannot be stated honestly the surface shows none.

This adds a twelfth signal family to the enumeration frozen in Task 0.2, and a value to the
schema's `signal_family` enum. That enumeration is frozen against *renaming and reuse*
(ADR-009, so `entry_id` stays stable); appending a new family breaks no existing id.

## Rejected options

### Pick one row — first, last, or highest price
Silent and unevidenced. `4062139003150` becomes ₪15.90 or ₪16.90 by arrival order, and a
markup, a ceiling contribution and possibly a surfaced finding are computed from a number
nobody chose. This is the failure D-3 exists to prevent, and it would be invisible.

### Deduplicate in `compose` only, for AC-109
Satisfies the acceptance criterion and loses the finding. The conflict is in the owner's
catalogue and only the owner can fix it; a browser that quietly shows one of the two
guarantees he never will. It also leaves the artefact internally inconsistent — counts
disagreeing with entries — for every consumer other than the surface.

### Exclude conflicting barcodes silently
Honest about the number, silent about the cause. 41 products vanish from every count with
no way for anyone to ask why. Exclusion is right; unreported exclusion is not.

### Resolve per field — use the agreed fields, exclude only the disputed ones
Most precise, and it makes a product's population membership depend on which capability is
asking. A product would be inside `price_consistency` and outside `catalogue_lifecycle` on
the same run, which no count could then be explained against. Rejected for the same reason
ADR-014 makes a capability the smallest unavailable unit: partial presence is not a state
the artefact can express honestly.

## Consequences

**Measured after implementation: 42, not 41.** The hand count compared the POS columns;
the implementation compares the *shaped* fields, which include `recorded_stock`. One pair
agrees on every product field and disagrees on stock. That is kept deliberately — a barcode
with two recorded stocks is as unusable as one with two prices, and D-6 restricts automatic
withdrawal to zero recorded stock, so the wrong row could withdraw a product that is on the
shelf.

**We accept:** 42 products (0.5% of the catalogue) leave every capability population until
the owner fixes them, and one new hygiene reason appears on his screen. The seven identical
pairs collapse invisibly, which is correct — there is nothing to tell him.

A twelfth signal family means the schema enum and `SIGNAL_FAMILIES` change together, and
Phase 2's fixture must be rebuilt.

**We gain:** counts that match their entry lists; a conflict the owner can actually fix; and
no price stated that the catalogue does not agree on.

**We will know it was wrong if:** the hygiene record is never acted on and the same 41
products are excluded month after month — which would mean the owner cannot fix it in the
POS, and the resolution belongs upstream in the export rather than in his hands.

## Binds

| F# | How this constrains it |
|---|---|
| F2 | A twelfth hygiene reason, `conflicting_duplicate`, carrying the disagreeing fields and no money |
| F1 | A conflicting barcode contributes to no ceiling, no count and no entry |
| F6 | AC-109 is satisfied upstream; `compose` still deduplicates defensively but is no longer the only thing preventing it |
