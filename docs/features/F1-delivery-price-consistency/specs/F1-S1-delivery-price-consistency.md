---
ID: F1-S1
Title: Delivery-Platform Price Consistency
Status: Approved — passed the Intent → Spec conformance gate (run 2, CONDITIONAL PASS)
Version: 1.1
Parent: [F1 — Delivery-Platform Price Consistency](../intent.md)
Related Intents: INT-001
Legacy ID: SPEC-001 (in the pre-migration monolithic `specs.md` v1.1)
Answered by: [System Design](../../../architecture/system-design.md) §21
---

> **Identifier note.** The requirement identifiers inside this document (`FR-…`, `INV-…`,
> `NFR-…`, `AC-…`, `SCN-…`, `C-…`, `ASM-…`, `OQ-…`) are **unchanged** from `specs.md` v1.1
> and remain globally unique across the specification layer. They are the ids used by the
> two gate reports, by the System Design's traceability matrix (§21) and by the
> implementation plan. Where a fully-qualified form is wanted, prefix with the spec id:
> `F1-S1.FR-001`. Nothing was renumbered by the documentation migration.

# F1-S1 — Delivery-Platform Price Consistency

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-001, INT-NS, INT-PROV

---

### 1. Purpose

Defines when a difference between a product's shelf price and the same product's
price on the store's own delivery platform is surfaced to the owner, how it is
characterised, and what the system must never claim about it.

---

### 2. Intent Traceability

- **INT-001** — "I do not want to lose money on every sale."
- **INT-NS** — contributes ranked entries to the daily surface (SPEC-006).
- **INT-PROV** — every threshold and count here is recomputable (SPEC-007).

---

### 3. Scope

#### In Scope

- Comparison of a product's shelf price with that same product's delivery-platform
  price **within the same store**.
- Deciding which differences are surfaced and which are silent.
- The characterisation of a surfaced difference (confirmed loss vs. question).
- Derivation of the store's own markup ceiling from its own data.

#### Out of Scope

- Comparison against any other store (SPEC-003).
- Margin against cost price — a different signal with a different threshold.
- Recommending a specific corrected price.
- Any change to prices in any external system.

---

### 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | Store owner, reviewing the daily surface |
| **Trigger** | A new point-of-sale export is ingested |
| **Precondition** | A product record carries both a shelf price and a delivery-platform price, both greater than zero |

No owner action initiates this analysis; it is a consequence of ingestion.

---

### 5. Domain Terms

| Term | Definition |
|---|---|
| **Shelf price** | The price charged to a customer buying in the physical store |
| **Delivery price** | The price charged for the same product through the store's own delivery-platform listing. It originates in the store's own export, not from any competitor's data |
| **Markup** | `(delivery price ÷ shelf price) − 1`, expressed as a percentage. Defined only where shelf price > 0 |
| **Markup ceiling** | The highest markup that is consistent with the owner's own observed pricing behaviour. Derived from data (FR-004), never assumed |
| **Inverted price** | Delivery price strictly below shelf price |

---

### 6. Functional Requirements

#### Classification

**FR-001** — The system MUST classify every product that has both a shelf price and a
delivery price into exactly one of four states: *identical*, *within ceiling*,
*above ceiling*, *inverted*.

**FR-002** — The system MUST NOT surface products classified *identical* or *within
ceiling*. These represent the owner's own pricing policy operating normally.

**FR-003** — The system MUST surface products classified *inverted* and *above
ceiling*, and MUST distinguish them from one another.

#### The ceiling

**FR-004** — The markup ceiling MUST be derived from the distribution of the store's
own observed markups, not from a constant representing an assumed platform
commission.

**FR-005** — The derivation of the ceiling MUST be reproducible from the same input
data, and the derived value MUST be reportable alongside any count that depends on it.

**FR-006** — When the observed markup distribution does not exhibit a distinguishable
ceiling, the system MUST NOT substitute a default value. It MUST report that the
ceiling is undetermined and MUST suppress the *above ceiling* signal until one is
determined. The *inverted* signal is unaffected and MUST continue to be surfaced.

#### Characterisation

**FR-007** — An *inverted* product MUST be characterised as a confirmed loss, and the
characterisation MUST state that the loss is compounded by the platform's commission.

**FR-008** — An *above ceiling* product MUST be characterised as a **question** —
whether the difference is deliberate — and MUST NOT be characterised as a loss, an
error, or a recommendation to change the price.

**FR-009** — Every surfaced product MUST expose the shelf price, the delivery price,
and their difference, so the owner can verify the claim without leaving the surface.

#### Exclusions

**FR-010** — A product whose price pair matches the data-entry artefact definition
(D-4: shelf price below ₪0.50, or cost exceeding twice the shelf price) MUST be
excluded from this signal, and the count of exclusions MUST be reportable.

**FR-011** — A product missing either price MUST be excluded from this signal and MUST
NOT be reported as having a zero difference.

#### Money

**FR-012** — Any monetary figure produced by this specification MUST be expressed as a
per-sale recurring amount and MUST be labelled as recurring.

**FR-013** — A monetary figure from this specification MUST NOT be added to any
standing one-time figure (D-2), including for the purpose of producing a headline
total.

---

### 7. Behavioral Invariants

**INV-001** — A price difference MUST NOT be described as a loss unless the delivery
price is strictly below the shelf price.

**INV-002** — The markup ceiling MUST always be traceable to the store's own observed
data for the period in question.

**INV-003** — The count of surfaced products MUST always be strictly less than the
count of products having both prices. A state in which every priced product is
surfaced indicates a broken threshold and MUST NOT be presented.

**INV-004** — Products classified *identical* MUST NOT appear in any surfaced count,
under any threshold setting.

**INV-005** — No output of this specification may assert a velocity claim (units per
day, days until stockout, projected revenue). This signal is derived from prices
alone and carries no evidence about sales.

---

### 8. Behavioral Scenarios

**SCN-001 — Identical prices are silent**
GIVEN a product priced identically on the shelf and on the delivery platform
WHEN the daily surface is produced
THEN the product does not appear, and it is not counted as a difference.

**SCN-002 — A markup inside the owner's own policy is silent**
GIVEN a product whose delivery price is above its shelf price by less than the derived ceiling
WHEN the daily surface is produced
THEN the product does not appear.

**SCN-003 — An inverted price is a confirmed loss**
GIVEN a product whose delivery price is below its shelf price
WHEN the daily surface is produced
THEN the product is surfaced as a confirmed loss, states that commission compounds it, and shows both prices.

**SCN-004 — A markup above the ceiling is a question**
GIVEN a product whose markup exceeds the derived ceiling
WHEN the daily surface is produced
THEN the product is surfaced as a question about intent, and is not described as an error.

**SCN-005 — A data-entry artefact is excluded**
GIVEN a product whose shelf price is ₪0.01 and whose cost is ₪2.28
WHEN classification runs
THEN the product is excluded, and the exclusion is counted and reportable.

**SCN-006 — Missing delivery price**
GIVEN a product with a shelf price but no delivery price
WHEN classification runs
THEN the product is excluded, and is not reported as a zero-difference product.

**SCN-007 — The ceiling cannot be determined**
GIVEN a markup distribution with no distinguishable ceiling
WHEN classification runs
THEN the *above ceiling* signal is suppressed and reported as undetermined, while inverted products continue to be surfaced.

**SCN-008 — The owner challenges a figure**
GIVEN the owner disputes a surfaced count
WHEN the figures are recomputed from current data (SPEC-007)
THEN the same classification rules produce the count, and the ceiling used is reported with it.

**SCN-009 — Ceiling moves between ingestions**
GIVEN a newly derived ceiling differs from the previous one
WHEN the daily surface is produced
THEN classification uses the new ceiling, and products whose classification changed as a result are not presented as newly occurring price changes.

---

### 9. Inputs and Observable Outputs

**Inputs (semantic):** per product — identity, shelf price, delivery price, cost price
(for artefact exclusion only), department.

**Outputs (semantic):**
- A classification per product, one of four states.
- For each surfaced product: both prices, their difference, and which of the two
  characterisations applies.
- Aggregate counts per state, including the excluded-artefact count.
- The derived ceiling, or an explicit statement that it is undetermined.
- Any monetary figure, labelled recurring.

---

### 10. State / Lifecycle Semantics

A product's classification is derived fresh from each ingestion and holds no history.
It is not a lifecycle state and MUST NOT be treated as one: a product may move between
the four states as prices change, and no transition is illegal.

Owner decisions recorded against a surfaced product (SPEC-006) are separate from the
classification and MUST survive reclassification.

---

### 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| Delivery price absent for a product | Exclude that product; surface the rest (FR-011) |
| Delivery prices absent for the whole catalogue | Report the signal as unavailable; do not report zero differences |
| Ceiling underivable | FR-006 — suppress *above ceiling*, keep *inverted* |
| Shelf price zero or negative | Exclude from this signal; belongs to data hygiene (SPEC-002) |
| Ingestion interrupted mid-way | Do not present a partial classification as complete; the previous complete result remains authoritative |

---

### 12. Edge Cases

| Edge case | Resolution |
|---|---|
| Prices differ by a rounding-sized amount | Requires a materiality floor — **OQ-101**, unresolved |
| Delivery price equals shelf price exactly | *Identical* (FR-002); silent |
| A product is both inverted and a data-entry artefact | Artefact exclusion takes precedence (FR-010) |
| Extreme markup on a very low-priced item (₪1.00 → ₪2.90) | Surfaced as *above ceiling*; the intent notes small-basket delivery economics may explain it, which is why FR-008 makes it a question |
| Every product identical (owner mirrors all prices) | Zero surfaced; valid, not an error state |
| Owner deliberately runs an inverted promotional price | Still surfaced (FR-007). Suppressing it would require a recorded owner answer — **OQ-102** |

---

### 13. Non-Functional Requirements

**NFR-001 (Explainability)** — Every surfaced product MUST carry enough on-surface
evidence for the owner to verify it against his own point-of-sale system without
assistance.

**NFR-002 (Determinism)** — The same input data MUST produce the same classification
and the same ceiling.

**NFR-003 (Signal density)** — The proportion of price-paired products surfaced by this
specification MUST NOT exceed 10%. Above that, the threshold is describing normal
pricing rather than exceptions, and INV-003 is at risk.

---

### 14. Compatibility and External Constraints

- **C-1** — The delivery price originates in the store's own point-of-sale export. It
  MUST NOT be treated as, or blended with, competitor pricing (SPEC-003).
- **C-2** — D-7: nothing in this specification may write a price to any external
  system.
- **C-3** — The existing contract that no recommendation displays a velocity claim
  without sales evidence remains binding (INV-005).
- **C-4** — Owner decisions already recorded against price signals MUST remain valid
  and retrievable after a threshold change.

---

### 15. Acceptance Criteria

**AC-001** — Given a catalogue in which the majority of products are priced identically
on both channels, those products appear in no surfaced count. *(FR-002, INV-004)*

**AC-002** — Inverted products are surfaced as confirmed losses and are distinguishable
from above-ceiling products in the output. *(FR-003, FR-007)*

**AC-003** — No above-ceiling product is labelled a loss anywhere in the output.
*(FR-008, INV-001)*

**AC-004** — The ceiling is reported alongside every count that depends on it, and
recomputing from the same data reproduces both. *(FR-005, NFR-002)*

**AC-005** — With a distribution having no distinguishable ceiling, the above-ceiling
count is reported as undetermined rather than as zero, and inverted products still
appear. *(FR-006, SCN-007, D-3)*

**AC-006** — Products matching the artefact definition are absent from surfaced output,
and their count is retrievable. *(FR-010, SCN-005)*

**AC-007** — No output of this specification contains a per-day or days-remaining
claim. *(INV-005)*

**AC-008** — Surfaced products never exceed 10% of price-paired products on the pilot
catalogue. *(NFR-003, INV-003)*

**AC-009** — A recorded owner decision remains retrievable after the ceiling changes
and the product's classification changes with it. *(C-4)*

---

### 16. Assumptions

**ASM-001** — The delivery-platform column in the store's export represents that
store's own listing, and not a price observed elsewhere. Supported by the column
living inside the owner's own inventory export; not stated explicitly by the owner.

**ASM-002** — A markup within the owner's observed ceiling is deliberate policy rather
than accumulated drift. This is the premise of FR-002 and has not been confirmed with
the owner.

**ASM-003** — The commission the delivery platform charges is not available to the
system, so the ceiling is inferred from behaviour rather than computed from cost.

**ASM-004** — Price pairs in a single export are contemporaneous; neither price is
stale relative to the other.

---

### 17. Open Questions

**OQ-101 (P1) — Is there a materiality floor below which a difference is ignored?**
A ₪0.02 difference is arithmetically a difference. Without a floor, trivial differences
consume slots on a surface limited to 10 entries. Affects FR-003 and NFR-003.

**OQ-102 (P1) — Can the owner mark an inverted price as deliberate, and does that
suppress it?**
The intent makes inverted prices a confirmed loss, but a deliberate promotional price
is legitimate. Without an answer, the same item may be surfaced every day after the
owner has already decided. Affects FR-007 and the interaction with SPEC-006.

**OQ-103 (P2) — Should the ceiling be derived per department or once for the store?**
Electronics and confectionery show different markup behaviour. A single ceiling may
over-surface one department and under-surface another. Affects FR-004.

**OQ-104 (P2) — Should a monetary figure be attached to this signal at all?**
The intent replaced "₪X lost per sale" with counts. A per-unit difference summed
across products is not a realisable amount unless one unit of each sells. Affects
FR-012 and what SPEC-006 ranks by.

---

### 18. Non-Goals

- Recommending what the corrected price should be.
- Modelling the delivery platform's commission structure.
- Detecting price changes over time, or alerting on them.
- Comparing against any store other than this one.
- Judging whether the owner's pricing policy is commercially sound.

---

### 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-001 | FR-001, FR-002 | SCN-001, SCN-002 | AC-001 |
| INT-001 | FR-003, FR-007 | SCN-003 | AC-002 |
| INT-001 | FR-008, INV-001 | SCN-004 | AC-003 |
| INT-001 | FR-004, FR-005 | SCN-008 | AC-004 |
| INT-001 | FR-006 | SCN-007 | AC-005 |
| INT-001 (D-4) | FR-010 | SCN-005 | AC-006 |
| INT-001 (D-3) | FR-006, FR-011 | SCN-006, SCN-007 | AC-005 |
| INT-NS | NFR-003, INV-003 | — | AC-008 |
| INT-PROV | FR-005, NFR-002 | SCN-008 | AC-004 |
| Protected behavior | INV-005 | — | AC-007 |
| Protected behavior | C-4 | SCN-009 | AC-009 |
