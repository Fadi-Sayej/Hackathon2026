# SPEC-002 — Stock Reconciliation and Data Hygiene

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-002, INT-002B, INT-NS, INT-PROV

---

## 1. Purpose

Defines how the system detects that a product's recorded quantities cannot be
arithmetically consistent, how much of that finding may be expressed in money, and how
records that are merely wrong are separated from records that indicate missing value.

---

## 2. Intent Traceability

- **INT-002** — "Where is my stock disappearing?" — the money.
- **INT-002B** — the same question as data hygiene, deliberately carrying no money.
- **INT-NS** — contributes ranked entries to the daily surface (SPEC-006).
- **INT-PROV** — every figure recomputable (SPEC-007).

---

## 3. Scope

### In Scope

- Detecting products whose recorded stock, receipts and sales cannot all be true.
- Deciding which detections may carry a monetary figure and which may not.
- Separating detection (certain) from magnitude (conditional).
- Records that are structurally invalid: negative quantities, unmatchable identifiers,
  absent prices.

### Out of Scope

- Deciding what the correct quantity is.
- Instructing the owner how to correct his point-of-sale records.
- Any correction written to an external system (D-7).
- Products that never sold (SPEC-004) — absence of sales is not an inconsistency.

---

## 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | Store owner or a staff member performing a shelf count |
| **Trigger** | A new point-of-sale export is ingested |
| **Precondition** | For the money signal: the product has a recorded receipt quantity greater than zero |

---

## 5. Domain Terms

| Term | Definition |
|---|---|
| **Recorded stock** | The quantity the point-of-sale system currently reports on hand. **Treated as unreliable** — the owner has stated it is wrong in both directions |
| **Receipts** | Quantity recorded as delivered into the store over the observed period |
| **Units sold** | Quantity recorded as sold over the same period |
| **Implied opening balance** | `recorded stock − receipts + units sold`. A negative value is physically impossible and therefore proves inconsistency |
| **Unaccounted quantity** | The absolute size of a negative implied opening balance |
| **Confirmed magnitude** | An unaccounted quantity computed where recorded stock is non-negative |
| **Estimated magnitude** | An unaccounted quantity computed where recorded stock is itself negative, and therefore rests on an impossible input |

---

## 6. Functional Requirements

### Detection

**FR-020** — The system MUST flag a product as inconsistent when its implied opening
balance is negative.

**FR-021** — The system MUST NOT flag a product with no recorded receipts in the
observed period. Without receipts, there is no arithmetic to close.

**FR-022** — The detection MUST be presented as arithmetically certain, independently
of the reliability of any single input.

### Magnitude, and its two tiers

**FR-023** — The system MUST partition flagged products into **confirmed magnitude**
and **estimated magnitude** according to whether the recorded stock used in the
computation is non-negative or negative.

**FR-024** — The system MUST report the monetary total of each tier separately, and
MUST label the estimated tier as an estimate.

**FR-025** — The system MUST NOT present a single combined monetary total without the
two tiers being visible alongside it.

**FR-026** — The estimate label MUST be presented before the owner questions the
figure, not in response to being questioned (D-10).

**FR-027** — Where a flagged product has no cost price, the system MUST report the
unaccounted quantity without a monetary figure, and MUST NOT substitute zero or an
inferred cost (D-3).

### Hygiene signals — no money, by decision

**FR-028** — The system MUST surface records that are structurally invalid — negative
recorded stock, unmatchable product identifier, absent price — as work items.

**FR-029** — A hygiene signal MUST NOT carry a monetary figure, under any
circumstances (D-1). This includes derived, estimated, or illustrative figures.

**FR-030** — Hygiene signals MUST be distinguishable in the output from money-bearing
signals, so that neither is presented as the other.

### Money semantics

**FR-031** — Monetary figures from this specification MUST be expressed as a standing
one-time amount and labelled as such.

**FR-032** — A figure from this specification MUST NOT be summed with any recurring
per-sale figure (D-2).

**FR-033** — The action attached to a flagged product MUST be to count the product
physically. The system MUST NOT state what the correct quantity is.

---

## 7. Behavioral Invariants

**INV-010** — A monetary figure MUST NOT be attached to a product whose recorded stock
is negative **without** that figure being in the estimated tier.

**INV-011** — The confirmed and estimated tiers MUST partition the flagged set exactly:
every flagged product belongs to exactly one, and their monetary totals sum to the
combined total.

**INV-012** — The detection claim ("these quantities cannot all be true") MUST remain
valid regardless of which tier a product falls in.

**INV-013** — No hygiene signal may ever carry a monetary figure (D-1).

**INV-014** — A per-sale figure and a standing figure MUST NOT appear as a single
summed value anywhere in the system (D-2).

**INV-015** — The system MUST NOT assert where the missing stock went. Theft, breakage,
mis-scanning and recording error are indistinguishable from this evidence.

---

## 8. Behavioral Scenarios

**SCN-020 — Consistent product is silent**
GIVEN a product whose implied opening balance is non-negative
WHEN reconciliation runs
THEN the product is not flagged.

**SCN-021 — Confirmed magnitude**
GIVEN a product with non-negative recorded stock whose implied opening balance is negative
WHEN reconciliation runs
THEN it is flagged, placed in the confirmed tier, and its value contributes to the confirmed total.

**SCN-022 — Estimated magnitude**
GIVEN a product with recorded stock of −716, receipts of 62 and sales of 663
WHEN reconciliation runs
THEN it is flagged, placed in the estimated tier, and its magnitude is labelled an estimate before any challenge.

**SCN-023 — No receipts**
GIVEN a product with no recorded receipts in the period
WHEN reconciliation runs
THEN it is not flagged, whatever its recorded stock.

**SCN-024 — Flagged but no cost price**
GIVEN a flagged product with no cost price
WHEN the result is produced
THEN the unaccounted quantity is reported and no monetary figure appears — not zero.

**SCN-025 — Negative stock as hygiene**
GIVEN a product whose recorded stock is negative and which is not flagged for inconsistency
WHEN the result is produced
THEN it appears as a hygiene work item carrying no monetary figure.

**SCN-026 — Headline totals stay separate**
GIVEN both a recurring per-sale total and a standing reconciliation total exist
WHEN any summary is produced
THEN the two are presented separately and never as one figure.

**SCN-027 — Owner asks where the stock went**
GIVEN a flagged product
WHEN the owner asks the cause
THEN the system states the arithmetic and that the cause is not determinable from this evidence.

**SCN-028 — Owner counts and the next export corrects the record**
GIVEN a flagged product that the owner counted and corrected
WHEN the next export is ingested and the arithmetic closes
THEN the product is no longer flagged, and the owner's recorded decision remains retrievable.

---

## 9. Inputs and Observable Outputs

**Inputs (semantic):** per product — identity, recorded stock, receipts over the period,
units sold over the period, cost price (optional), department.

**Outputs (semantic):**
- The flagged set, each with its unaccounted quantity and the arithmetic that produced it.
- Tier membership per flagged product.
- Two monetary totals, separately labelled: confirmed and estimated.
- The hygiene set, with a reason per record and **no** monetary figure.
- An action per flagged product: count this product.

---

## 10. State / Lifecycle Semantics

Flag status is derived per ingestion and holds no history. A product may be flagged in
one ingestion and not the next; this is a normal correction, not a state transition
requiring modelling.

Owner decisions recorded against a flagged product persist independently and MUST
survive the product ceasing to be flagged (SCN-028).

---

## 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| Receipts data unavailable for the period | The money signal is unavailable; report it as unavailable, not as zero. Hygiene signals are unaffected |
| Sales data unavailable | Same as above |
| Cost price missing for a flagged product | FR-027 — quantity without money |
| Cost price missing for the entire flagged set | Report the flagged count and no total; do not report ₪0 |
| Recorded stock absent (not zero) | Exclude from the money signal; treat as a hygiene record |
| Period boundaries of stock, receipts and sales do not align | The arithmetic is unsound — **OQ-201**, unresolved |

---

## 12. Edge Cases

| Edge case | Resolution |
|---|---|
| Unaccounted quantity is 1–2 units | Rounding-sized. Needs a materiality floor — **OQ-202** |
| Product sold more than ever received, stock zero | Flagged, confirmed tier; the arithmetic is exactly what the signal is for |
| Recorded stock negative **and** no receipts | Not flagged (FR-021); appears as hygiene (FR-028) |
| Cost price present but implausible (a carton cost against a unit price) | Excluded by D-4 from carrying money, consistent with SPEC-001 FR-010 |
| Product later archived as dead (SPEC-004) while flagged | Both signals are true; precedence undefined — **OQ-203** |
| Same product flagged in consecutive ingestions with a changed magnitude | Not a new event; must not be presented as a worsening trend without period evidence |

---

## 13. Non-Functional Requirements

**NFR-010 (Explainability)** — Every flagged product MUST show the three quantities and
the resulting arithmetic, in a form the owner can check against his own records.

**NFR-011 (Determinism)** — The same inputs MUST produce the same flags, tiers and
totals.

**NFR-012 (Honesty of aggregation)** — No aggregate presented anywhere may mix the two
tiers without labelling, nor mix this specification's total with a recurring total.

---

## 14. Compatibility and External Constraints

- **C-10** — D-1 binds our own derivations, not only the owner's numbers. This is the
  reason the two tiers exist.
- **C-11** — D-7: no correction is written to any external system.
- **C-12** — Existing behavior treats negative stock as a reported, money-free hygiene
  count. That behavior MUST be preserved (FR-028, FR-029).
- **C-13** — Recorded owner decisions MUST remain retrievable across ingestions.

---

## 15. Acceptance Criteria

**AC-020** — Every flagged product belongs to exactly one tier, and the two tier totals
sum to the combined total. *(INV-011)*

**AC-021** — No product with negative recorded stock contributes to the confirmed
total. *(FR-023, INV-010)*

**AC-022** — The estimated total is labelled an estimate in every place it appears,
including summaries. *(FR-024, FR-026)*

**AC-023** — The combined total never appears without both tiers visible. *(FR-025)*

**AC-024** — A flagged product without a cost price shows a quantity and no monetary
figure — not ₪0. *(FR-027, SCN-024, D-3)*

**AC-025** — No hygiene record anywhere carries a monetary figure. *(FR-029, INV-013)*

**AC-026** — No surface presents a recurring figure and a standing figure summed.
*(FR-032, INV-014, SCN-026)*

**AC-027** — No output states or implies a cause for the missing stock. *(INV-015,
SCN-027)*

**AC-028** — Recomputation from the same data reproduces flags, tiers and both totals.
*(NFR-011)*

**AC-029** — A decision recorded against a flagged product is still retrievable after
the product ceases to be flagged. *(C-13, SCN-028)*

---

## 16. Assumptions

**ASM-010** — Receipts and sales quantities are more reliable than recorded stock
levels, because they are flows recorded at the moment of an event rather than a running
balance. This asymmetry is the basis of the two-tier split and has not been confirmed
with the owner.

**ASM-011** — The observed period for receipts and sales is the same period the
recorded stock reflects. If not, the arithmetic is unsound (OQ-201).

**ASM-012** — A single cost price per product is adequate for valuation; cost changes
within the period are not modelled.

**ASM-013** — The owner's stated unreliability of quantities ("the report may say 8, the
shelf has 1") applies across the catalogue rather than to particular departments.

---

## 17. Open Questions

**OQ-201 (P0) — Do recorded stock, receipts and sales cover the same period?**
The implied-opening-balance arithmetic is only valid if they do. Recorded stock is a
current snapshot; receipts and sales come from monthly reports covering January–July.
If the snapshot post-dates the reports, every magnitude in this specification is wrong
by the intervening activity. This blocks the money signal entirely.

**OQ-202 (P1) — What is the materiality floor for an unaccounted quantity?**
Without one, rounding-sized mismatches compete for slots on a 10-item surface. Affects
FR-020 and SPEC-006 ranking.

**OQ-203 (P1) — When a product is both flagged here and dead in SPEC-004, which
governs?**
A dead product scheduled for automatic archiving may also carry unaccounted value.
Archiving it would remove a money-bearing signal. Affects both specifications.

**OQ-204 (P2) — Should the estimated tier be surfaced to the owner at all, or held
back as internal evidence?**
The intent argues that volunteering the weakness buys trust. An alternative is to
surface only the confirmed tier and mention the estimate only if asked. Affects FR-024
and what SPEC-006 ranks.

---

## 18. Non-Goals

- Determining the correct stock quantity.
- Attributing a cause (theft, breakage, error).
- Recommending a process change in the store.
- Correcting the owner's records.
- Predicting future discrepancies.

---

## 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-002 | FR-020, FR-021, FR-022 | SCN-020, SCN-021, SCN-023 | AC-020 |
| INT-002 (D-1) | FR-023, FR-024 | SCN-022 | AC-021, AC-022 |
| INT-002 | FR-025 | SCN-026 | AC-023 |
| INT-002 (D-3) | FR-027 | SCN-024 | AC-024 |
| INT-002 (D-2) | FR-031, FR-032 | SCN-026 | AC-026 |
| INT-002 | FR-033, INV-015 | SCN-027 | AC-027 |
| INT-002B | FR-028, FR-029, FR-030 | SCN-025 | AC-025 |
| INT-PROV | NFR-011 | — | AC-028 |
| Protected behavior | C-12, C-13 | SCN-028 | AC-029 |
