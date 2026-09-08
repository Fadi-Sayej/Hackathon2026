---
ID: F2-S1
Title: Stock Reconciliation and Data Hygiene
Status: Approved — passed the Intent → Spec conformance gate (run 2, CONDITIONAL PASS)
Version: 1.1
Parent: [F2 — Stock Truth](../intent.md)
Related Intents: INT-002, INT-002B
Legacy ID: SPEC-002 (in the pre-migration monolithic `specs.md` v1.1)
Answered by: [System Design](../../../architecture/system-design.md) §21
---

> **Identifier note.** The requirement identifiers inside this document (`FR-…`, `INV-…`,
> `NFR-…`, `AC-…`, `SCN-…`, `C-…`, `ASM-…`, `OQ-…`) are **unchanged** from `specs.md` v1.1
> and remain globally unique across the specification layer. They are the ids used by the
> two gate reports, by the System Design's traceability matrix (§21) and by the
> implementation plan. Where a fully-qualified form is wanted, prefix with the spec id:
> `F2-S1.FR-001`. Nothing was renumbered by the documentation migration.

# F2-S1 — Stock Reconciliation and Data Hygiene

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-002, INT-002B, INT-NS, INT-PROV

---

### 1. Purpose

Defines how the system detects that a product's recorded quantities cannot be
arithmetically consistent, how much of that finding may be expressed in money, and how
records that are merely wrong are separated from records that indicate missing value.

---

### 2. Intent Traceability

- **INT-002** — "Where is my stock disappearing?" — products whose recorded quantities
  cannot all be true. Carries no money figure (FR-023).
- **INT-002B** — the same question as data hygiene, deliberately carrying no money.
- **INT-NS** — contributes ranked entries to the daily surface (SPEC-006).
- **INT-PROV** — every figure recomputable (SPEC-007).

---

### 3. Scope

#### In Scope

- Detecting products whose recorded stock, receipts and sales cannot all be true.
- Deciding which detections may carry a monetary figure and which may not.
- Separating detection (certain) from magnitude (conditional).
- Records that are structurally invalid: negative quantities, unmatchable identifiers,
  absent prices.

#### Out of Scope

- Deciding what the correct quantity is.
- Instructing the owner how to correct his point-of-sale records.
- Any correction written to an external system (D-7).
- Products that never sold (SPEC-004) — absence of sales is not an inconsistency.

---

### 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | Store owner or a staff member performing a shelf count |
| **Trigger** | A new point-of-sale export is ingested |
| **Precondition** | The product has a recorded receipt quantity greater than zero (FR-021) |

---

### 5. Domain Terms

| Term | Definition |
|---|---|
| **Recorded stock** | The quantity the point-of-sale system currently reports on hand. **Treated as unreliable** — the owner has stated it is wrong in both directions |
| **Receipts** | Quantity recorded as delivered into the store over the observed period |
| **Units sold** | Quantity recorded as sold over the same period |
| **Implied opening balance** | `recorded stock − receipts + units sold`. A negative value is physically impossible and therefore proves inconsistency |
| **Unaccounted quantity** | The absolute size of a negative implied opening balance |
| **Gap ratio** | The unaccounted quantity as a proportion of receipts over the period. The ordering key for this capability, replacing money |

---

### 6. Functional Requirements

#### Detection

**FR-020** — The system MUST flag a product as inconsistent when its implied opening
balance is negative.

**FR-021** — The system MUST NOT flag a product with no recorded receipts in the
observed period. Without receipts, there is no arithmetic to close.

**FR-022** — The detection MUST be presented as arithmetically certain, independently
of the reliability of any single input.

#### Magnitude, and why it carries no money

**FR-023** — The system MUST NOT attach a monetary figure to any product flagged by this
specification, whatever the sign of its recorded stock.

*Rationale, and the reason this replaces an earlier two-tier rule: the arithmetic uses
the recorded stock in every case, not only where it is negative. A positive recorded
stock is not thereby a trustworthy one. In the pilot data the highest-valued flagged
product records 1,533 units on hand while the arithmetic claims 4,274 units
unaccounted — positive, and impossible. The underlying file has never been reviewed by
the owner, so no partition of it yields a defensible figure.*

**FR-024** — The system MUST order flagged products by gap ratio, descending.

**FR-025** — The system MUST NOT present any monetary total for the flagged set, whether
combined, partitioned, or bounded.

**FR-026** — Where the owner asks the size of the loss, the system MUST state that the
amount is not determinable before a physical count, and MUST NOT offer a figure as an
upper bound or an illustration.

**FR-027** — The system MUST report, per flagged product, the three quantities and the
resulting unaccounted quantity, so the finding is verifiable without a monetary figure.

#### Hygiene signals — no money, by decision

**FR-028** — The system MUST surface records that are structurally invalid — negative
recorded stock, unmatchable product identifier, absent price — as work items.

**FR-029** — A hygiene signal MUST NOT carry a monetary figure, under any
circumstances (D-1). This includes derived, estimated, or illustrative figures.

**FR-030** — Hygiene signals MUST be distinguishable in the output from money-bearing
signals, so that neither is presented as the other.

#### Money semantics

**FR-031** — This specification produces no monetary figures (FR-023). Consequently it
contributes no standing amount to any surface.

**FR-032** — Because no figure is produced, the prohibition on summing a standing amount
with a recurring one (D-2) cannot be breached by this capability. The prohibition itself
remains in force for any capability that later produces a standing amount.

**FR-033** — The action attached to a flagged product MUST be to count the product
physically. The system MUST NOT state what the correct quantity is.

---

### 7. Behavioral Invariants

**INV-010** — A monetary figure MUST NEVER be attached to any product flagged by this
specification (D-1, applied without exception).

**INV-011** — No aggregate produced by this specification may be expressed in currency.

**INV-012** — The detection claim ("these quantities cannot all be true") MUST remain
valid regardless of the sign or magnitude of any input, and MUST NOT be weakened by the
absence of a monetary figure.

**INV-013** — No hygiene signal may ever carry a monetary figure (D-1).

**INV-014** — A per-sale figure and a standing figure MUST NOT appear as a single
summed value anywhere in the system (D-2).

**INV-015** — The system MUST NOT assert where the missing stock went. Theft, breakage,
mis-scanning and recording error are indistinguishable from this evidence.

---

### 8. Behavioral Scenarios

**SCN-020 — Consistent product is silent**
GIVEN a product whose implied opening balance is non-negative
WHEN reconciliation runs
THEN the product is not flagged.

**SCN-021 — Positive recorded stock earns no money figure**
GIVEN a product recording 1,533 units on hand whose arithmetic claims 4,274 unaccounted
WHEN reconciliation runs
THEN it is flagged and ordered by gap ratio, and no monetary figure is attached despite the stock being positive.

**SCN-022 — Negative recorded stock is treated identically**
GIVEN a product with recorded stock of −716, receipts of 62 and sales of 663
WHEN reconciliation runs
THEN it is flagged on the same basis as SCN-021, with no monetary figure and no separate tier.

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

### 9. Inputs and Observable Outputs

**Inputs (semantic):** per product — identity, recorded stock, receipts over the period,
units sold over the period, cost price (optional), department.

**Outputs (semantic):**
- The flagged set, each with its unaccounted quantity and the arithmetic that produced it.
- The gap ratio per flagged product, which is the ordering key (FR-024).
- **No monetary figure and no monetary total, for any flagged product or for the set** (FR-023, FR-025).
- The hygiene set, with a reason per record and **no** monetary figure.
- An action per flagged product: count this product.

---

### 10. State / Lifecycle Semantics

Flag status is derived per ingestion and holds no history. A product may be flagged in
one ingestion and not the next; this is a normal correction, not a state transition
requiring modelling.

Owner decisions recorded against a flagged product persist independently and MUST
survive the product ceasing to be flagged (SCN-028).

---

### 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| Receipts data unavailable for the period | The detection signal is unavailable; report it as unavailable, not as zero findings. Hygiene signals are unaffected |
| Sales data unavailable | Same as above |
| Cost price missing for a flagged product | Irrelevant here — no capability of this specification consumes cost (ASM-012) |
| Recorded stock absent (not zero) | Exclude from the detection signal; treat as a hygiene record |
| Period boundaries of stock, receipts and sales do not align | The arithmetic is unsound — **OQ-201**, unresolved |

---

### 12. Edge Cases

| Edge case | Resolution |
|---|---|
| Unaccounted quantity is 1–2 units | Rounding-sized. Needs a materiality floor — **OQ-202** |
| Product sold more than ever received, stock zero | Flagged; the arithmetic is exactly what the signal is for |
| Recorded stock negative **and** no receipts | Not flagged (FR-021); appears as hygiene (FR-028) |
| Cost price present but implausible (a carton cost against a unit price) | Excluded by D-4 from carrying money, consistent with SPEC-001 FR-010 |
| Product later archived as dead (SPEC-004) while flagged | Both signals are true; precedence undefined — **OQ-203** |
| Same product flagged in consecutive ingestions with a changed magnitude | Not a new event; must not be presented as a worsening trend without period evidence |

---

### 13. Non-Functional Requirements

**NFR-010 (Explainability)** — Every flagged product MUST show the three quantities and
the resulting arithmetic, in a form the owner can check against his own records.

**NFR-011 (Determinism)** — The same inputs MUST produce the same flagged set and the
same gap-ratio ordering.

**NFR-012 (Honesty of aggregation)** — The only aggregate this specification may publish
is a **count**. No aggregate it produces may be expressed in currency (INV-011).

---

### 14. Compatibility and External Constraints

- **C-10** — D-1 binds our own derivations, not only the owner's numbers. This is the
  reason no monetary figure is produced at all (FR-023).
- **C-11** — D-7: no correction is written to any external system.
- **C-12** — Existing behavior treats negative stock as a reported, money-free hygiene
  count. That behavior MUST be preserved (FR-028, FR-029).
- **C-13** — Recorded owner decisions MUST remain retrievable across ingestions.

---

### 15. Acceptance Criteria

**AC-020** — A product whose implied opening balance is negative is flagged; a product
whose implied opening balance is non-negative is not; and a product with no recorded
receipts in the period is not flagged whatever its recorded stock. The flagged set is
ordered by gap ratio, descending. *(FR-020, FR-021, FR-022, FR-024, SCN-020, SCN-021,
SCN-023)*

**AC-021** — No product flagged by this specification carries a monetary figure anywhere
in the output, whatever the sign of its recorded stock. *(FR-023, INV-010, SCN-021,
SCN-022)*

**AC-022** — No aggregate produced by this specification is expressed in currency.
*(FR-025, INV-011)*

**AC-023** — Asked the size of the loss, the system states it is not determinable before
a count and offers no figure as a bound or an illustration. *(FR-026)*

**AC-024** — Every flagged product shows the three quantities and the unaccounted
quantity. *(FR-027, NFR-010)*

**AC-025** — No hygiene record anywhere carries a monetary figure. *(FR-029, INV-013)*

**AC-026** — No surface presents a recurring figure and a standing figure summed.
*(FR-032, INV-014, SCN-026)*

**AC-027** — No output states or implies a cause for the missing stock. *(INV-015,
SCN-027)*

**AC-028** — Recomputation from the same data reproduces the flagged set and its
gap-ratio ordering. *(NFR-011)*

**AC-029** — A decision recorded against a flagged product is still retrievable after
the product ceases to be flagged. *(C-13, SCN-028)*

---

### 16. Assumptions

**ASM-010** — Receipts and sales quantities are more reliable than recorded stock
levels, because they are flows recorded at the moment of an event rather than a running
balance. This asymmetry is why detection is claimed as certain while magnitude is not
claimed at all. It has not been confirmed with the owner.

**ASM-011** — The observed period for receipts and sales is the same period the
recorded stock reflects. If not, the arithmetic is unsound (OQ-201).

**ASM-012** — Cost price is not used by this specification, since no valuation is
produced. Should a monetary figure ever be reinstated, cost stability within the period
would become an assumption again.

**ASM-013** — The owner's stated unreliability of quantities ("the report may say 8, the
shelf has 1") applies across the catalogue rather than to particular departments.

---

### 17. Open Questions

**OQ-201 (P1, reduced from P0) — Do recorded stock, receipts and sales cover the same
period?**
Recorded stock is a current snapshot; receipts and sales come from monthly reports
covering January–July. Misalignment would distort the unaccounted *quantity*. Since
FR-023 no longer states a monetary figure and FR-024 orders by gap ratio, a distortion
affects ordering rather than a published amount — so this no longer blocks design. It
still matters: severe misalignment could flag consistent products, so it must be
established before the flagged list is put in front of the owner.

**OQ-202 (P1) — What is the materiality floor for an unaccounted quantity?**
Without one, rounding-sized mismatches compete for slots on a 10-item surface. Affects
FR-020 and SPEC-006 ranking.

**OQ-203 (P1) — When a product is both flagged here and dead in SPEC-004, which
governs?**
A dead product scheduled for automatic archiving may also carry unaccounted value.
Archiving it would remove a money-bearing signal. Affects both specifications.

**OQ-204 (P2) — After a physical count establishes real quantities, may a monetary
figure be reinstated?**
FR-023 forbids money because the recorded quantities are unreviewed. Once the owner has
counted a product, that objection no longer applies to it. Whether counted products
graduate into a money-bearing signal affects FR-023 and what SPEC-006 ranks.
*(This question replaces an earlier one about which tier to surface; the tiers were
removed.)*

---

### 18. Non-Goals

- Determining the correct stock quantity.
- Attributing a cause (theft, breakage, error).
- Recommending a process change in the store.
- Correcting the owner's records.
- Predicting future discrepancies.

---

### 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-002 | FR-020, FR-021, FR-022 | SCN-020, SCN-021, SCN-023 | AC-020 |
| INT-002 (D-1) | FR-023, FR-024, INV-010 | SCN-021, SCN-022 | AC-021 |
| INT-002 | FR-025, FR-026, INV-011 | SCN-027 | AC-022, AC-023 |
| INT-002 (D-3) | FR-027 | SCN-024 | AC-024 |
| INT-002 (D-2) | FR-031, FR-032 | SCN-026 | AC-026 |
| INT-002 | FR-033, INV-015 | SCN-027 | AC-027 |
| INT-002B | FR-028, FR-029, FR-030 | SCN-025 | AC-025 |
| INT-PROV | NFR-011 | — | AC-028 |
| Protected behavior | C-12, C-13 | SCN-028 | AC-029 |
