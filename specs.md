# SmartShelf — Specification Layer

**Status:** Draft · **Version:** 0.3 · **Updated:** 2026-09-08
**Intent layer:** [`intent.md`](intent.md) — the source this specification is derived from.

The reasoning layers are kept strictly separate:

```
INTENTS  ->  SPECS  ->  SYSTEM DESIGN  ->  IMPLEMENTATION PLAN  ->  CODE
             ^ you are here
```

This file is the whole specification layer in one place. It defines **what must
become observably true**, not how to build it. It contains no implementation
choices; where one appeared to be needed, the decision was recorded as an open
question instead.

Specifications are in English because their audience is a system designer and a
coding agent working in a repository whose code and technical documents are
English. The intent layer stays in Arabic because its audience includes the store
owner.

**Design-readiness: NOT READY FOR SYSTEM DESIGN** — one P0 question remains, not five. Version 0.2 removed the monetary figure from stock reconciliation entirely
(SPEC-002 FR-023), because a positive recorded stock proved no more trustworthy than a
negative one in a file the owner has never reviewed. That single change left V1 with one
monetary kind, which dissolved the ordering conflict on the daily surface. Version 0.3
then settled catalogue withdrawal: it is not a one-time event but a rule re-evaluated on
every ingestion, whose strength follows the evidence window (SPEC-004 FR-060a, FR-063a–c).

What still blocks design: **OQ-301** — whether a competitor of a different store format
may drive a surfaced signal. Under existing protected behavior it may not, and only 4 of
165 candidate items survive.

---

## Contents

1. [SPEC-000 — Intent Register and Specification Index](#spec-000-intent-register-and-specification-index)
2. [SPEC-001 — Delivery-Platform Price Consistency](#spec-001-delivery-platform-price-consistency)
3. [SPEC-002 — Stock Reconciliation and Data Hygiene](#spec-002-stock-reconciliation-and-data-hygiene)
4. [SPEC-003 — Competitor Price Position](#spec-003-competitor-price-position)
5. [SPEC-004 — Catalogue Lifecycle](#spec-004-catalogue-lifecycle)
6. [SPEC-005 — Owner Knowledge Capture](#spec-005-owner-knowledge-capture)
7. [SPEC-006 — Daily Action Surface](#spec-006-daily-action-surface)
8. [SPEC-007 — Figure Provenance and Reproducibility](#spec-007-figure-provenance-and-reproducibility)
9. [SPEC-GAPS — Gaps, Open Questions and Assumptions](#spec-gaps-gaps-open-questions-and-assumptions)

---

## SPEC-000 — Intent Register and Specification Index

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Source of intents:** [`intent.md`](intent.md)

This file assigns stable identifiers to the intents so every requirement in every
specification can be traced back to one. It defines no behavior of its own.

Specifications are written in English because their audience is a system designer
and a coding agent working in a repository whose code and technical documents are
English. The intent layer stays in Arabic because its audience includes the store
owner.

---

### 1. Intent identifiers

| ID | Intent (owner's words, from `intent.md` §1) | Release | Specified in |
|---|---|---|---|
| **INT-001** | "I do not want to lose money on every sale" — shelf price against the store's own delivery-platform price | V1 | SPEC-001 |
| **INT-002** | "Where is my stock disappearing?" — **the money** | V1 | SPEC-002 |
| **INT-002B** | "Where is my stock disappearing?" — **data hygiene**, deliberately carrying no money figure | V1 | SPEC-002 |
| **INT-003** | "Are my prices reasonable against my neighbours?" | V1 | SPEC-003 |
| **INT-004** | "What do I order today, and how much?" | V2 | Not specified — see §4 |
| **INT-005** | "What does the market sell that I don't?" | V2 | Not specified — see §4 |
| **INT-006** | "Arrange my shelves so I earn more" | V4 | Not specified — see §4 |
| **INT-007** | "How much do I order so it does not spoil?" | V2 | Not specified — see §4 |
| **INT-008** | "When does each supplier actually deliver?" | V3 | Not specified — see §4 |
| **INT-009** | "Clean my catalogue of dead products" | V1 | SPEC-004 |
| **INT-010** | "Complete my missing data — with minimum disturbance" | V1 | SPEC-005 |
| **INT-NS** | The fixed north star: one morning screen, actions ranked by money, **no more than 10** | V1 | SPEC-006 |
| **INT-PROV** | Every figure must be recomputable on demand; no figure asserted from a stale document | V1 | SPEC-007 |

`INT-NS` and `INT-PROV` are not numbered in `intent.md`. They are stated there as
cross-cutting rules — the "fixed north star" in the preamble, and the boxed warning
in §12 plus the three code rules. They govern behavior across every other intent, so
they are registered as intents in their own right rather than duplicated into each
specification.

---

### 2. Specification index

| Spec | Capability | Status |
|---|---|---|
| **SPEC-001** | Delivery-Platform Price Consistency | Draft |
| **SPEC-002** | Stock Reconciliation and Data Hygiene | Draft |
| **SPEC-003** | Competitor Price Position | **Draft — blocked**, see GAP-001 |
| **SPEC-004** | Catalogue Lifecycle | Draft |
| **SPEC-005** | Owner Knowledge Capture | Draft |
| **SPEC-006** | Daily Action Surface | Draft |
| **SPEC-007** | Figure Provenance and Reproducibility | Draft |
| **SPEC-GAPS** | Specification gaps, open questions, assumptions | Living |

---

### 3. Decisions already made by the intent layer

These are settled. A specification may operationalize them; it may not reopen them.

| # | Decision | Source |
|---|---|---|
| D-1 | No monetary figure may be attached to a signal derived from a stock quantity — **including our own derivations** | `intent.md` §1, §12 rule 1 |
| D-2 | A recurring per-sale amount and a standing one-time amount are never summed | `intent.md` §2 |
| D-3 | Where a figure cannot be stated honestly, the surface shows **no figure** — not zero | `intent.md` §12 rule 3 |
| D-4 | A shelf price below ₪0.50, or a cost above twice the price, is a data-entry artefact and not a loss | `intent.md` §12 rule 2 |
| D-5 | The store's own price is never its own benchmark | `intent.md` §3 |
| D-6 | Automatic archiving is restricted to products with zero recorded stock | `intent.md` §4 |
| D-7 | The system never writes to the owner's point-of-sale system | `intent.md` §9.6 |
| D-8 | At most three questions are put to the owner on screen at once | `intent.md` §5 |
| D-9 | The daily surface shows at most 10 actions | `intent.md` preamble |
| D-10 | An uncertain figure is labelled uncertain **before** it is questioned, not after | `intent.md` §2, §4 |

---

### 4. Intents deliberately not specified in this phase

**INT-004, INT-005, INT-007, INT-008 (V2/V3) and INT-006 (V4)** are not given
specifications here.

The reason is not scheduling. Each rests on a product decision that the intent layer
has explicitly left open, and writing requirements now would mean inventing those
answers rather than surfacing them:

- **INT-004** depends on how market movement and the store's own movement combine into
  one quantity, and on what geographic radius defines "the market". Both open —
  `intent.md` §6 states the ordering of inputs, not the rule.
- **INT-005** depends on what the owner is expected to *do* with a "strong in the
  market, weak here" finding. `intent.md` §6 phrases it as a conversation opener, which
  is not yet a decision the system can record.
- **INT-007** depends on shelf-life data that does not exist until store staff have
  recorded receipts for 30 days.
- **INT-008** depends on three deliveries per supplier being observed; the intent notes
  its timeline is calendar-bound, not engineering-bound.
- **INT-006** depends on three inputs that do not exist yet (shelf photographs with
  dimensions, real demand from V2, the owner's own arrangement rules).

These are tracked as open questions in SPEC-GAPS at P1/P2. They must be specified
before their releases are designed, not before V1 is designed.

---

## SPEC-001 — Delivery-Platform Price Consistency

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

---

## SPEC-002 — Stock Reconciliation and Data Hygiene

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

- **INT-002** — "Where is my stock disappearing?" — the money.
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
| **Precondition** | For the money signal: the product has a recorded receipt quantity greater than zero |

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
valid regardless of which tier a product falls in.

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
- Tier membership per flagged product.
- Two monetary totals, separately labelled: confirmed and estimated.
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
| Receipts data unavailable for the period | The money signal is unavailable; report it as unavailable, not as zero. Hygiene signals are unaffected |
| Sales data unavailable | Same as above |
| Cost price missing for a flagged product | FR-027 — quantity without money |
| Cost price missing for the entire flagged set | Report the flagged count and no total; do not report ₪0 |
| Recorded stock absent (not zero) | Exclude from the money signal; treat as a hygiene record |
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

**NFR-011 (Determinism)** — The same inputs MUST produce the same flags, tiers and
totals.

**NFR-012 (Honesty of aggregation)** — No aggregate presented anywhere may mix the two
tiers without labelling, nor mix this specification's total with a recurring total.

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

**AC-020** — Every flagged product belongs to exactly one tier, and the two tier totals
sum to the combined total. *(INV-011)*

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

**AC-028** — Recomputation from the same data reproduces flags, tiers and both totals.
*(NFR-011)*

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

---

## SPEC-003 — Competitor Price Position

**Status:** **Draft — BLOCKED.** See GAP-001. The requirements below are stated so the
blocking conflict is precise, but this specification MUST NOT be handed to system
design until OQ-301 is answered.
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-003, INT-NS, INT-PROV

---

### 1. Purpose

Defines when the store's price for a product is surfaced as out of line with prices at
nearby stores, and how the difference in store format is accounted for so that a
legitimate forecourt premium is not reported as a fault.

---

### 2. Intent Traceability

- **INT-003** — "Are my prices reasonable against my neighbours?"
- **INT-NS** — contributes ranked entries to the daily surface (SPEC-006).
- **INT-PROV** — every threshold and count recomputable (SPEC-007).

---

### 3. Scope

#### In Scope

- Comparison of the store's shelf price against prices for the same product at other
  stores.
- Accounting for store format when interpreting a difference.
- Deciding which differences are surfaced, and how they are characterised.
- Stating the coverage limits of the comparison.

#### Out of Scope

- The store's own delivery-platform price (SPEC-001).
- Recommending a corrected price.
- Products the market carries and this store does not (INT-005, unspecified).
- Any judgement of a competitor's pricing.

---

### 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | Store owner |
| **Trigger** | Ingestion of a new competitor price observation set, or of a new store export |
| **Precondition** | A product is identified at both this store and at least one other store by a shared product identifier |

---

### 5. Domain Terms

| Term | Definition |
|---|---|
| **Store format** | A classification of a retail outlet by size and assortment (forecourt shop, urban minimarket, mid-size grocery, supermarket, hypermarket) |
| **Format affinity** | A value in `[0, 1]` expressing how comparable two formats are. Existing behavior treats `0` as never comparable and a value below the comparability floor as context only |
| **Comparable source** | An observation from a store whose affinity to this store is at or above the comparability floor. Existing behavior permits only such a source to drive a recommendation |
| **Context-only source** | An observation from a store with affinity above zero but below the floor. Existing behavior permits display but forbids driving a recommendation |
| **Excluded source** | An observation from a store with affinity zero. Existing behavior drops it before any engine sees it |
| **Statistical outlier threshold** | The point at which the observed distribution of differences breaks (derived, not assumed) |
| **Commercial threshold** | A lower, product-chosen bound expressing what premium is acceptable regardless of format |

---

### 6. Functional Requirements

#### Source discipline — protected behavior

**FR-040** — The system MUST NOT base a surfaced recommendation on an excluded source.

**FR-041** — The system MUST NOT base a surfaced recommendation on a context-only
source **unless OQ-301 resolves otherwise**. Until then this requirement stands as
existing protected behavior.

**FR-042** — Where an observation is displayed for context, the system MUST label the
observing store's format and MUST state that part of any difference is attributable to
format.

**FR-043** — The system MUST record, per surfaced item, which source drove it, so that
compliance with FR-040 and FR-041 is verifiable.

#### Thresholds

**FR-044** — The statistical outlier threshold MUST be derived from the observed
distribution of differences, not assumed.

**FR-045** — The commercial threshold MUST be expressed as a stated multiple of the
observed median difference against comparable sources, so that it moves with the market
rather than being a fixed percentage.

**FR-046** — Both thresholds MUST be reportable alongside any count that depends on
them.

#### Characterisation

**FR-047** — An item exceeding the statistical outlier threshold MUST be characterised
as an anomaly warranting verification of the price, not as overcharging.

**FR-048** — An item exceeding the commercial threshold but not the statistical one
MUST be characterised as a question about intent.

**FR-049** — The system MUST NOT characterise any difference as an error without owner
confirmation.

#### Coverage honesty

**FR-050** — The system MUST state what proportion of the catalogue has any comparable
price at all, and MUST NOT present the comparison as covering the catalogue.

**FR-051** — For a product with no comparison available, the system MUST show that no
comparison exists rather than showing no difference (D-3).

**FR-052** — The system MUST distinguish products that are structurally uncomparable —
services and internally-coded items that no other retailer sells — from products merely
not yet matched, and MUST NOT count the former as a coverage failure.

#### Position reporting

**FR-053** — The system MUST be able to report the store's overall price position
against each comparable source, including when the store is cheaper.

---

### 7. Behavioral Invariants

**INV-020** — No surfaced recommendation may be traceable to an excluded source.

**INV-021** — Every displayed competitor observation carries its store's format.

**INV-022** — A difference explained by format alone MUST NOT be characterised as a
fault.

**INV-023** — Coverage claims MUST always be expressed against the full catalogue, not
against the matched subset.

**INV-024** — The store's own price MUST NOT serve as its own benchmark (D-5).

---

### 8. Behavioral Scenarios

**SCN-040 — Same-format comparison drives a signal**
GIVEN a product priced above the same product at a comparable-format store beyond both thresholds
WHEN the surface is produced
THEN it is surfaced, and the driving source is recorded as comparable.

**SCN-041 — Excluded source never drives**
GIVEN a product whose only above-threshold difference is against an excluded source
WHEN the surface is produced
THEN the product is not surfaced as a recommendation.

**SCN-042 — Context-only source, current behavior**
GIVEN a product whose only above-threshold difference is against a context-only source
WHEN the surface is produced
THEN the product is not surfaced as a recommendation, and the observation may appear as labelled context.

**SCN-043 — Store is cheaper than its true peer**
GIVEN the store is cheaper than the comparable forecourt on most matched products
WHEN a position summary is produced
THEN that position is reportable.

**SCN-044 — No comparison available**
GIVEN a product with no matching observation anywhere
WHEN the surface is produced
THEN it shows that no comparison exists, not a zero difference.

**SCN-045 — Structurally uncomparable item**
GIVEN a service item with an internal code and no retail identifier
WHEN coverage is reported
THEN it is excluded from the comparable population and does not count against coverage.

**SCN-046 — Owner asks about an uncovered product**
GIVEN the owner names a product with no comparison
WHEN he asks its market position
THEN the system states that this product is outside the comparable set, consistent with the coverage stated up front.

**SCN-047 — Only stale observations exist**
GIVEN the newest observation for a product is older than the freshness bound
WHEN the surface is produced
THEN the product is not surfaced as a recommendation, and any display marks the observation's age.

---

### 9. Inputs and Observable Outputs

**Inputs (semantic):** the store's shelf price per product; competitor observations
(product identity, price, observing store, observation time); each store's format and
its affinity to this store's format.

**Outputs (semantic):**
- Per surfaced product: the store's price, the compared price, the difference, the
  observing store with its format, and which characterisation applies.
- Both thresholds in force.
- Coverage: comparable population, matched count, and the structurally uncomparable
  count, all expressed against the full catalogue.
- Overall position per comparable source.

---

### 10. State / Lifecycle Semantics

Comparison results are derived per ingestion and hold no lifecycle state. Observation
freshness is a property of the input, not a state of the product.

---

### 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| No comparable-format source available at all | The recommendation-driving signal is unavailable; report it as unavailable, not as zero findings |
| Observation set stale beyond the freshness bound | Do not drive recommendations from it; mark age where displayed (SCN-047) |
| Product identifier matched but products differ in size or pack | Comparison invalid — **OQ-303**, unresolved |
| A store's format is unknown | Treat as the existing unknown-format affinity; do not assume comparability |
| Threshold underivable from the distribution | Suppress the derived-threshold signal and report it as undetermined (D-3) |
| Competitor data absent entirely | Report the whole capability as unavailable; other specifications unaffected |

---

### 12. Edge Cases

| Edge case | Resolution |
|---|---|
| The store is *cheaper* than a comparable peer by a large margin | Not a fault. May be a margin signal, which belongs to a different capability — out of scope here |
| Only one comparable-format store exists in range | A single source drives every comparable signal; the concentration MUST be visible in output (FR-043) |
| A competitor runs a temporary promotion | Indistinguishable from a price change with current evidence — **OQ-304** |
| The same product is observed at several stores with different prices | Which observation is the benchmark is undefined — **OQ-302** |
| A comparable store is geographically far while an excluded one is adjacent | Format governs, not distance, under current protected behavior. Whether distance should also bound the set is **OQ-305** |

---

### 13. Non-Functional Requirements

**NFR-020 (Explainability)** — Every surfaced item MUST name the store it was compared
against and that store's format.

**NFR-021 (Determinism)** — The same observation set and the same store classifications
MUST produce the same surfaced set and thresholds.

**NFR-022 (Freshness)** — An observation older than the freshness bound MUST NOT drive
a recommendation. The bound itself is **OQ-306**.

---

### 14. Compatibility and External Constraints

- **C-20** — Existing protected behavior: an affinity-zero store is dropped before any
  engine sees it, and an existing acceptance check fails the build if any recommendation
  is sourced from one. This constraint is binding and is the source of GAP-001.
- **C-21** — Existing protected behavior: a store below the comparability floor is
  context only and may not drive a recommendation.
- **C-22** — Store classifications carry a provenance distinction between first-hand
  knowledge of a branch and desk knowledge of a chain; a manually decided
  classification is final and MUST NOT be overwritten by inference.
- **C-23** — D-5: the store's own price is never its own benchmark.

---

### 15. Acceptance Criteria

**AC-040** — No surfaced recommendation is traceable to an excluded source, verified by
the existing acceptance check. *(FR-040, INV-020, C-20)*

**AC-041** — No surfaced recommendation is traceable solely to a context-only source
while OQ-301 is unresolved. *(FR-041, C-21)*

**AC-042** — Every displayed competitor observation shows the observing store's format.
*(FR-042, INV-021)*

**AC-043** — Both thresholds are reported with any count derived from them, and
recomputation reproduces them. *(FR-046, NFR-021)*

**AC-044** — Coverage is stated against the full catalogue and separates structurally
uncomparable items. *(FR-050, FR-052, INV-023)*

**AC-045** — A product with no comparison shows "no comparison", never a zero
difference. *(FR-051, SCN-044)*

**AC-046** — The store's position against its comparable peer is reportable, including
when favourable. *(FR-053, SCN-043)*

**AC-047** — No output characterises a difference as an error without owner
confirmation. *(FR-049)*

**AC-048** — An observation beyond the freshness bound drives no recommendation.
*(NFR-022, SCN-047)*

---

### 16. Assumptions

**ASM-020** — A shared product identifier denotes the same sellable unit at both
stores, including pack size. Contradicted where identifiers are reused across pack
sizes (OQ-303).

**ASM-021** — An observed competitor price was actually charged, not an aspirational or
list price.

**ASM-022** — The existing format affinity values encode a considered product judgement
about comparability and are not merely a data-quality filter. GAP-001 turns on whether
this is true.

**ASM-023** — Observation sets refresh often enough that the freshness bound is rarely
binding. Unverified.

---

### 17. Open Questions

**OQ-301 (P0) — May a context-only source drive a surfaced signal when the difference
is extreme?**
This is the blocking question; see GAP-001. Existing behavior says no. The intent's
analysis derives thresholds from a population dominated by context-only and excluded
sources. Under current behavior, **4 of 165** items above the commercial threshold and
**1 of 24** above the statistical threshold may be surfaced. Either the intent's
thresholds describe a signal that cannot be shown, or the affinity policy must change.
Both the requirement set and the value of the capability depend on the answer.

**OQ-302 (P1) — When several stores observe the same product, which is the benchmark?**
Cheapest, nearest, most comparable by format, or a central value. Changes every
difference and therefore every count. Affects FR-044, FR-045.

**OQ-303 (P1) — How are pack-size mismatches handled?**
A shared identifier may denote different sellable units. A false match produces a
spurious extreme difference — precisely the items the thresholds select for. Affects
FR-047 and the credibility of the anomaly signal.

**OQ-304 (P2) — Should a competitor promotion be distinguished from a price change?**
Currently indistinguishable. Affects whether repeated surfacing of the same item is
correct.

**OQ-305 (P2) — Should a distance bound apply in addition to format affinity?**
The intent speaks of "neighbours" and of a radius; existing behavior bounds only by
format. Affects the comparable population.

**OQ-306 (P2) — What is the observation freshness bound?**
NFR-022 requires one; no value is stated anywhere. Affects which observations may drive
recommendations.

---

### 18. Non-Goals

- Recommending a corrected price.
- Matching products across stores by name or description.
- Tracking competitor price history or trends.
- Assessing competitors' pricing strategy.
- Expanding the observed store set.

---

### 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-003 | FR-040, FR-041 | SCN-041, SCN-042 | AC-040, AC-041 |
| INT-003 | FR-042, FR-043 | SCN-040 | AC-042 |
| INT-003 | FR-044, FR-045, FR-046 | SCN-040 | AC-043 |
| INT-003 | FR-047, FR-048, FR-049 | SCN-040 | AC-047 |
| INT-003 | FR-050, FR-052 | SCN-045 | AC-044 |
| INT-003 (D-3) | FR-051 | SCN-044, SCN-046 | AC-045 |
| INT-003 | FR-053 | SCN-043 | AC-046 |
| INT-PROV | NFR-021 | — | AC-043 |
| Protected behavior | C-20, C-21, INV-020 | SCN-041 | AC-040, AC-041 |
| Protected behavior | NFR-022 | SCN-047 | AC-048 |

---

## SPEC-004 — Catalogue Lifecycle

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-009, INT-NS, INT-PROV

---

### 1. Purpose

Defines how a product in the catalogue is classified as living, dead or idle from sales
evidence; which of those may be withdrawn from the working catalogue without asking the
owner; and how a withdrawn product returns.

---

### 2. Intent Traceability

- **INT-009** — "Clean my catalogue of dead products."
- **INT-NS** — a smaller catalogue is what makes a 10-item surface reachable.
- **INT-PROV** — every count recomputable (SPEC-007).

---

### 3. Scope

#### In Scope

- Classifying catalogue entries by sales evidence over an observation window.
- Automatically withdrawing entries that meet a strict condition.
- Returning a withdrawn entry when evidence contradicts the withdrawal.
- Presenting entries that require the owner's judgement, ranked.
- Producing a list the owner can act on in his own system.

#### Out of Scope

- Deleting or modifying anything in the owner's point-of-sale system (D-7).
- Deciding whether idle stock should be discounted, returned or written off.
- Determining why a product stopped selling.
- Any pricing signal (SPEC-001, SPEC-003).

---

### 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | Store owner |
| **Trigger** | Ingestion of a point-of-sale export together with sales history covering the observation window |
| **Precondition** | Sales history covering the window is available; without it no classification may be produced |

---

### 5. Domain Terms

| Term | Definition |
|---|---|
| **Observation window** | The trailing period over which sales evidence is assessed |
| **Living** | Sold at least one unit within the window |
| **Dead** | Sold nothing within the window |
| **Withdrawable** | Dead **and** recorded stock is zero |
| **Idle** | Dead **and** recorded stock is above zero |
| **Withdrawn** | Hidden from working surfaces and excluded from other signals, while remaining recoverable |
| **Revival** | Return of a withdrawn entry to living on the first evidence of a sale |
| **Working catalogue** | The set of entries that other capabilities operate on |
| **Implausible quantity** | A recorded stock whose valuation is inconsistent with the store's scale by a stated margin |

---

### 6. Functional Requirements

#### Classification

**FR-060** — The system MUST classify every catalogue entry with a usable product
identifier as living, withdrawable, or idle, using sales evidence over the observation
window.

**FR-060a** — Classification MUST be re-evaluated on every ingestion of new sales
evidence, against the window then available. It MUST NOT be a one-time event whose
result is thereafter fixed.

**FR-060b** — The system MUST determine whether the available sales evidence spans a
**full annual cycle**, and MUST make that determination available to every requirement
that depends on it (FR-063a, FR-076).

**FR-061** — The observation window MUST be stated wherever a classification or count is
presented.

**FR-062** — An entry whose recorded stock is negative MUST NOT be classified
withdrawable. It belongs to data hygiene (SPEC-002).

#### Automatic withdrawal

**FR-063** — The system MUST withdraw withdrawable entries without requiring an owner
decision.

**FR-063a** — Where the available evidence does **not** span a full annual cycle, every
withdrawal MUST be accompanied by a statement that the evidence is insufficient to
distinguish a seasonal product from a dead one, and that a product may therefore have
been withdrawn wrongly. The statement MUST accompany the withdrawal itself, not only a
summary of it (D-10).

**FR-063b** — Where the evidence **does** span a full annual cycle, withdrawal MUST be
made on that basis and the insufficiency statement MUST NOT be shown.

**FR-063c** — When newly ingested evidence extends the window across a full annual
cycle, the system MUST re-evaluate every existing withdrawal against the longer window,
and MUST return any entry that the longer evidence shows to be seasonal rather than
dead.

**FR-064** — The system MUST NOT automatically withdraw an idle entry (D-6).

**FR-065** — Withdrawal MUST be reversible, and every withdrawn entry MUST remain
listable with the evidence that caused it.

**FR-066** — The system MUST revive a withdrawn entry on the first recorded sale of it,
without an owner decision.

**FR-067** — The owner MUST be able to revive a withdrawn entry manually, and a manual
revival MUST NOT be reversed by a subsequent automatic withdrawal within the same
observation window. *(Rationale: otherwise the system overrules an explicit human
decision on the next ingestion.)*

**FR-068** — Withdrawal MUST NOT alter any record in the owner's point-of-sale system
(D-7).

#### Idle entries

**FR-069** — Idle entries MUST be presented for the owner's judgement, ranked by the
value of the stock recorded against them.

**FR-070** — For each idle entry the system MUST offer distinguishable outcomes
covering at least: the stock is genuinely present and unsold; the recorded quantity is
wrong; the product is no longer carried.

**FR-071** — The system MUST NOT state which outcome is correct.

#### Implausible quantities

**FR-072** — The system MUST identify idle entries whose recorded stock valuation is
implausible against the store's scale and MUST present them as a **question** to the
owner.

**FR-073** — An implausible quantity MUST NOT be asserted as a fact about the owner's
capital or as an accusation of mismanagement (D-10).

#### Effect on other capabilities

**FR-074** — Withdrawn entries MUST be excluded from other capabilities' populations,
and every count those capabilities publish MUST reflect the exclusion.

**FR-075** — The system MUST produce, on request, a list of withdrawn entries suitable
for the owner to act on in his own system.

#### Honesty about the window

**FR-076** — Where the observation window does not span a full annual cycle, the system
MUST state that seasonal products may be misclassified as dead, and MUST state this
wherever the dead count is presented.

---

### 7. Behavioral Invariants

**INV-030** — An entry with recorded stock above zero MUST NEVER be withdrawn
automatically (D-6).

**INV-031** — Withdrawal MUST NEVER be irreversible.

**INV-031a** — A withdrawal made on evidence shorter than a full annual cycle MUST NEVER
be presented as settled. Its provisional character MUST travel with it.

**INV-032** — A withdrawn entry that records a sale MUST NEVER remain withdrawn.

**INV-033** — Withdrawal MUST NEVER change anything outside this system (D-7).

**INV-034** — The living, withdrawable and idle sets MUST partition the classified
population exactly.

**INV-035** — An implausible quantity MUST NEVER be presented as an established fact.

**INV-036** — No classification may be produced when sales evidence for the window is
absent; absence of evidence MUST NOT be read as absence of sales.

---

### 8. Behavioral Scenarios

**SCN-060 — A living product is untouched**
GIVEN a product that sold at least one unit within the window
WHEN classification runs
THEN it remains in the working catalogue.

**SCN-061 — Automatic withdrawal**
GIVEN a product with no sales in the window and zero recorded stock
WHEN classification runs
THEN it is withdrawn without an owner decision, and remains listable with its evidence.

**SCN-062 — Idle product is never auto-withdrawn**
GIVEN a product with no sales in the window and recorded stock above zero
WHEN classification runs
THEN it is not withdrawn, and is presented for the owner's judgement ranked by stock value.

**SCN-063 — Automatic revival**
GIVEN a withdrawn product
WHEN a subsequent ingestion records a sale of it
THEN it returns to the working catalogue without an owner decision.

**SCN-064a — Withdrawal on partial evidence is declared provisional**
GIVEN sales evidence covering seven months, less than a full annual cycle
WHEN entries are withdrawn
THEN each withdrawal states that the evidence cannot separate a seasonal product from a dead one.

**SCN-064b — A longer window reverses a wrong withdrawal**
GIVEN a product withdrawn under a seven-month window, and evidence later extending to two years showing it sold in one season each year
WHEN the longer evidence is ingested
THEN the product is returned to the working catalogue without an owner decision, and the withdrawal is not repeated.

**SCN-064c — A longer window confirms a withdrawal**
GIVEN a product withdrawn under a short window, and longer evidence showing no sales in any season
WHEN the longer evidence is ingested
THEN the product remains withdrawn and the insufficiency statement is no longer shown.

**SCN-064 — Manual revival is respected**
GIVEN the owner manually revived a withdrawn product
WHEN the next ingestion still shows no sales and zero stock
THEN the product is not withdrawn again within the same window.

**SCN-065 — Implausible quantity is a question**
GIVEN an idle product whose recorded stock valuation is implausible against the store's scale
WHEN it is presented
THEN it appears as a question about the number's correctness, not as a claim about tied-up capital.

**SCN-066 — Negative stock is not withdrawable**
GIVEN a dead product whose recorded stock is negative
WHEN classification runs
THEN it is not withdrawn and appears as a hygiene record.

**SCN-067 — Sales history unavailable**
GIVEN no sales evidence for the window
WHEN classification is attempted
THEN no classification is produced and the capability reports itself unavailable; nothing is withdrawn.

**SCN-068 — Partial window**
GIVEN sales evidence covering less than a full annual cycle
WHEN a dead count is presented
THEN the seasonal-misclassification limitation is stated with it.

**SCN-069 — Downstream counts follow**
GIVEN products have been withdrawn
WHEN another capability publishes a count
THEN that count excludes withdrawn entries.

**SCN-070 — Handover list**
GIVEN withdrawn entries exist
WHEN the owner requests a list to act on in his own system
THEN a list of those entries is produced, and no external system is modified.

---

### 9. Inputs and Observable Outputs

**Inputs (semantic):** catalogue entries with identity, recorded stock, cost price,
department; sales evidence per product over the window; prior withdrawal state and
prior manual revivals.

**Outputs (semantic):**
- A classification per entry, with the evidence behind it.
- The withdrawn set, listable and reversible.
- The idle set, ranked by recorded stock value, each with the available outcomes.
- Implausible quantities, framed as questions.
- Counts per class, with the observation window stated.
- A handover list on request.

---

### 10. State / Lifecycle Semantics

Unlike the other V1 capabilities, withdrawal **is** a lifecycle state, because it
persists across ingestions and changes what other capabilities see.

Behavioral states: **in catalogue** ↔ **withdrawn**.

| Transition | Trigger | Legal |
|---|---|---|
| in catalogue → withdrawn | Dead and zero recorded stock | Yes, automatic (FR-063) |
| withdrawn → in catalogue | A recorded sale | Yes, automatic (FR-066) |
| withdrawn → in catalogue | Owner action | Yes (FR-067) |
| in catalogue → withdrawn | Owner action | **OQ-403**, unresolved |
| in catalogue → withdrawn | Dead with stock above zero | **Illegal** (INV-030) |
| withdrawn → withdrawn again | Automatic, after a manual revival in the same window | **Illegal** (FR-067) |

If ingestion is interrupted, no partial withdrawal set may take effect: the prior state
remains authoritative until a complete classification is produced.

---

### 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| Sales evidence absent | FR/INV-036 — no classification, nothing withdrawn, capability reported unavailable |
| Sales evidence covers a shorter window than configured | Classify against the actual window and state it (FR-061), with the seasonal caveat (FR-076) |
| Entry has no usable product identifier | Out of the classified population; it is a hygiene record (SPEC-002) |
| Recorded stock absent (not zero) | Not withdrawable; absence is not zero |
| Cost price absent for an idle entry | Rank without a value and show no value — not zero (D-3) |
| Ingestion interrupted | Prior state remains authoritative |

---

### 12. Edge Cases

| Edge case | Resolution |
|---|---|
| Seasonal product, zero stock, out of season | Withdrawn by FR-063, but the withdrawal is declared provisional while the evidence is short (FR-063a) and re-examined when a full annual cycle is available (FR-063c). Residual exposure until then is accepted knowingly; whether to keep such entries visible on ordering surfaces meanwhile is OQ-407 |
| A newly introduced product with no sales yet | Would be withdrawn on the first ingestion. Requires an introduction grace period — **OQ-402** |
| A product both dead and carrying unaccounted value (SPEC-002) | Precedence undefined — **OQ-203** (shared) |
| Owner revives a product that then never sells | Stays living for the window (FR-067); a repeated-revival policy is **OQ-404** |
| Very large withdrawn set on first run | Volume is expected; it is why withdrawal is automatic. Requires that the withdrawn list stay reviewable rather than being presented item by item |
| Idle entry with implausible quantity **and** no cost price | Cannot be valued or ranked; present without value (D-3) |

---

### 13. Non-Functional Requirements

**NFR-030 (Owner effort)** — Automatic withdrawal MUST require no owner action.
Reviewing the idle set MUST be possible incrementally, so that acting on the highest-
value entries does not require processing the whole set.

**NFR-031 (Reversibility)** — Every withdrawal MUST be reversible for as long as the
entry exists in the source data.

**NFR-032 (Determinism)** — The same catalogue, sales evidence and prior state MUST
produce the same classification and the same withdrawal set.

**NFR-033 (Explainability)** — Every withdrawn entry MUST carry the evidence that
caused it: the window, the absence of sales, and the recorded stock.

---

### 14. Compatibility and External Constraints

- **C-30** — D-7: no write to the owner's point-of-sale system. "Withdrawal" is local
  to this system plus a list handed to the owner.
- **C-31** — Withdrawn entries MUST be excluded consistently, so that counts published
  by other capabilities remain internally consistent with the catalogue they describe.
- **C-32** — Existing behavior clamps negative stock to zero at the data boundary for
  downstream consumers while reporting the count separately. Withdrawal decisions MUST
  be made against the recorded value, not the clamped one, or a negative-stock product
  would appear withdrawable (INV-030 would be violated silently).
- **C-33** — Owner decisions recorded against a product MUST survive withdrawal and
  revival.

---

### 15. Acceptance Criteria

**AC-060** — No entry with recorded stock above zero is ever withdrawn automatically.
*(INV-030, SCN-062)*

**AC-061** — Every withdrawn entry is listable with its evidence and can be returned to
the working catalogue. *(FR-065, NFR-033)*

**AC-062** — A withdrawn entry that records a sale returns without owner action.
*(FR-066, INV-032, SCN-063)*

**AC-063** — A manually revived entry is not automatically withdrawn again within the
same window. *(FR-067, SCN-064)*

**AC-063a** — Every withdrawal made on evidence shorter than a full annual cycle carries
the insufficiency statement at the point of withdrawal. *(FR-063a, INV-031a, SCN-064a)*

**AC-063b** — Extending the evidence across a full annual cycle causes every existing
withdrawal to be re-evaluated, and returns those the longer evidence shows to be
seasonal. *(FR-063c, SCN-064b, SCN-064c)*

**AC-063c** — Once the evidence spans a full annual cycle, withdrawals no longer carry
the insufficiency statement. *(FR-063b, SCN-064c)*

**AC-064** — No external system is modified by any withdrawal. *(FR-068, INV-033)*

**AC-065** — The living, withdrawable and idle sets partition the classified population
with no overlap and no remainder. *(INV-034)*

**AC-066** — With sales evidence absent, no classification is produced and nothing is
withdrawn. *(INV-036, SCN-067)*

**AC-067** — Every presentation of a dead count states the observation window and, where
the window is under a full annual cycle, the seasonal limitation. *(FR-061, FR-076,
SCN-068)*

**AC-068** — Counts published by other capabilities exclude withdrawn entries.
*(FR-074, C-31, SCN-069)*

**AC-069** — An implausible quantity is presented as a question in every place it
appears. *(FR-072, FR-073, INV-035, SCN-065)*

**AC-070** — A negative-stock dead entry is never withdrawn. *(FR-062, C-32, SCN-066)*

**AC-071** — Idle entries are ranked by recorded stock value, and an entry without a cost
price is ranked without a value rather than as zero. *(FR-069, D-3)*

---

### 16. Assumptions

**ASM-030** — Absence of a product from the sales evidence means it did not sell, rather
than that its sale was not recorded. If sales evidence is itself incomplete, withdrawal
removes products that do sell. This is the strongest assumption in this specification.

**ASM-031** — A product with zero recorded stock and no sales is already absent from the
shelf, so withdrawing it reflects reality rather than changing it. This is the entire
justification for D-6.

**ASM-032** — Product identifiers are stable across the observation window; a re-coded
product would appear dead under its old identifier.

**ASM-033** — The owner does not require notification before automatic withdrawal, only
the ability to review and reverse it.

**ASM-034** — Recorded stock in the export is contemporaneous with the end of the
observation window.

---

### 17. Open Questions

**OQ-401 — RESOLVED (2026-09-08).**
The question was how a withdrawn seasonal product ever returns, given that revival
depends on a sale and a withdrawn product may never be restocked.

**Decision: withdrawal is not settled while the evidence is short, and the evidence
itself is what changes.** Rather than weakening withdrawal permanently, the rule is
re-evaluated on every ingestion (FR-060a) and its strength follows the window: below a
full annual cycle every withdrawal is declared provisional (FR-063a); at a full annual
cycle the declaration stops (FR-063b) and every earlier withdrawal is re-examined
against the longer evidence, returning those that prove seasonal (FR-063c).

This is why the resolution is not "hold withdrawal until two years arrive": the
catalogue cleanup is worth having now, and the two-year evidence is already requested
from the owner. What the short window costs is certainty, and that cost is stated rather
than hidden.

**Residual exposure, accepted knowingly:** between now and the longer evidence, a
seasonal product with zero stock may be withdrawn and, if it is never restocked, may not
revive on its own. FR-063c repairs this when the evidence arrives. Whether withdrawal
should additionally remain visible on ordering surfaces in the meantime is **OQ-407**
(P1) — a narrowing of this question, not a blocker.

**OQ-407 (P1) — Should a withdrawn entry remain visible on ordering and assortment
surfaces, marked, while the evidence is short?**
Withdrawal serves attention: it stops the owner reviewing thousands of dead entries. It
need not also remove a product from the surfaces where he decides what to buy. Keeping
withdrawn entries visible there, marked with their evidence, would close the residual
exposure in OQ-401 before the longer evidence arrives. Affects FR-074's scope. Design can
begin without it, since it narrows an exclusion rather than changing the withdrawal rule.

**OQ-402 (P1) — Is there an introduction grace period for new products?**
Without one, a product introduced days before ingestion is classified dead and
withdrawn immediately. Affects FR-060 and FR-063.

**OQ-403 (P1) — May the owner withdraw a product manually?**
The state model has no such transition. An owner who knows he has stopped carrying an
idle product has no way to say so. Affects FR-070 and the state model.

**OQ-404 (P2) — What happens to a revived product that still does not sell?**
Repeated revival then withdrawal would surface the same product indefinitely. Affects
FR-067.

**OQ-405 (P2) — What defines "implausible" for a recorded quantity?**
FR-072 requires a stated margin against the store's scale; no value exists. Affects
FR-072 and how many questions reach the owner.

**OQ-406 — RESOLVED (2026-09-08).** The window follows the available evidence, not a
fixed product choice: FR-060a re-evaluates on every ingestion against the window then
available, and FR-060b makes the full-annual-cycle test the switch that governs how
strongly a withdrawal is stated. What remains open is only the threshold's exact
definition — whether "a full annual cycle" means twelve consecutive months of evidence or
coverage of every calendar month — tracked as **OQ-408** (P2).

**OQ-408 (P2) — What exactly constitutes a full annual cycle?**
Twelve consecutive months of evidence, or evidence covering each calendar month however
gathered. Affects FR-060b and therefore when FR-063a stops applying.

---

### 18. Non-Goals

- Deciding the commercial fate of idle stock.
- Explaining why a product stopped selling.
- Forecasting whether a dead product would sell if restocked.
- Managing assortment breadth as a strategy.
- Deleting anything anywhere outside this system.

---

### 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-009 | FR-060, FR-061 | SCN-060 | AC-065, AC-067 |
| INT-009 (D-6) | FR-063, FR-064, INV-030 | SCN-061, SCN-062 | AC-060 |
| INT-009 | FR-065, FR-066, FR-067 | SCN-063, SCN-064 | AC-061, AC-062, AC-063 |
| INT-009 (D-7) | FR-068, FR-075 | SCN-070 | AC-064 |
| INT-009 | FR-069, FR-070, FR-071 | SCN-062 | AC-071 |
| INT-009 (D-10) | FR-072, FR-073 | SCN-065 | AC-069 |
| INT-009 | FR-062 | SCN-066 | AC-070 |
| INT-009 | FR-076 | SCN-068 | AC-067 |
| INT-NS | FR-074 | SCN-069 | AC-068 |
| INT-009 | INV-036 | SCN-067 | AC-066 |
| INT-PROV | NFR-032 | — | AC-065 |

---

## SPEC-005 — Owner Knowledge Capture

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-010, INT-NS

---

### 1. Purpose

Defines how the system asks the owner for information only he holds, how few questions
may be put to him, how they are selected, and how his answers change subsequent
behavior.

---

### 2. Intent Traceability

- **INT-010** — "Complete my missing data — with minimum disturbance."
- **INT-NS** — questions compete with actions for the owner's limited attention.

---

### 3. Scope

#### In Scope

- Identifying facts the system cannot determine on its own and that materially change
  its output.
- Selecting which of them to ask about, and in what order.
- Bounding how many questions are presented at once.
- Suppressing questions that other capabilities have made unnecessary.
- The effect of an answer, and of a refusal.

#### Out of Scope

- Any question that is not required to change system behavior.
- Interrogating the owner about his commercial reasoning.
- Correcting the owner's records for him (D-7).
- The specific facts required by unspecified V2/V4 intents.

---

### 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | Store owner — the only actor who can answer |
| **Trigger** | The owner opens a surface that presents questions |
| **Precondition** | At least one open question exists whose answer would change output |

---

### 5. Domain Terms

| Term | Definition |
|---|---|
| **Open question** | A fact the system cannot derive, whose absence measurably degrades output |
| **Answerable population** | Open questions that survive suppression (FR-082) |
| **Question yield** | The number of products whose output would change if the question were answered |
| **Presentation limit** | The maximum number of questions shown at once |
| **Answer** | A recorded statement by the owner, treated as authoritative |
| **Deferral** | The owner declining to answer now, without asserting anything |

---

### 6. Functional Requirements

#### What may be asked

**FR-080** — The system MUST NOT present a question whose answer would not change any
output.

**FR-081** — Every presented question MUST concern a fact the system cannot derive from
available data.

**FR-082** — Before a question is presented, the system MUST suppress it if another
capability has already made it moot — in particular, a question about a product that
has been withdrawn from the working catalogue (SPEC-004) MUST NOT be asked.

**FR-083** — The system MUST be able to report, for any question class, how many
candidate questions were suppressed and how many remain, so the reduction in owner
effort is verifiable.

#### How many, and in what order

**FR-084** — The system MUST NOT present more than the presentation limit at one time.
The limit MUST be at most three (D-8).

**FR-085** — Questions MUST be ordered by expected value, defined as the money at stake
multiplied by the question yield, so that a question resolving many products outranks a
high-value question resolving one.

**FR-086** — The system MUST NOT present the remaining questions as a queue, a total, or
a progress indicator that implies a backlog the owner is expected to clear.

#### Answers

**FR-087** — An owner's answer MUST be treated as authoritative and MUST NOT be
overwritten by inference.

**FR-088** — An answer MUST take effect on the outputs it governs without requiring the
owner to take any further action.

**FR-089** — The system MUST NOT re-ask an answered question unless the owner revises
the answer or the underlying fact demonstrably changes.

**FR-090** — The owner MUST be able to revise a previously given answer.

**FR-091** — A deferral MUST NOT be recorded as an answer, and MUST NOT be treated as a
denial of the fact.

**FR-092** — Where a question remains unanswered, dependent outputs MUST behave as
specified for missing information in their own specifications — showing no figure
rather than a substituted one (D-3).

#### Effect on other capabilities

**FR-093** — Where an answer supplies a fact that other capabilities require, those
capabilities MUST use it, and MUST NOT continue to report the fact as missing.

---

### 7. Behavioral Invariants

**INV-040** — The number of questions presented at once MUST NEVER exceed the
presentation limit (D-8).

**INV-041** — A question MUST NEVER be presented about a product withdrawn from the
working catalogue.

**INV-042** — An owner's recorded answer MUST NEVER be silently overwritten.

**INV-043** — A deferral MUST NEVER be interpreted as content.

**INV-044** — The system MUST NEVER present a question whose answer changes nothing.

**INV-045** — No question may require the owner to consult a system other than his own
knowledge or his own records.

---

### 8. Behavioral Scenarios

**SCN-080 — Suppression before asking**
GIVEN a large set of products missing a required fact, most of which are withdrawn from the working catalogue
WHEN questions are selected
THEN only the non-withdrawn products yield questions, and the reduction is reportable.

**SCN-081 — The limit binds**
GIVEN more answerable questions than the presentation limit
WHEN questions are presented
THEN no more than the limit appear, and no backlog total is shown.

**SCN-082 — Ordering by yield**
GIVEN one question that would resolve many products and one high-value question that would resolve a single product
WHEN questions are ordered
THEN the broad question ranks first.

**SCN-083 — An answer takes effect**
GIVEN the owner supplies a missing fact
WHEN outputs depending on it are next produced
THEN they use the answer, and no longer report the fact as missing.

**SCN-084 — Answers are not overwritten**
GIVEN the owner has answered
WHEN a later process could infer a different value
THEN the owner's answer stands.

**SCN-085 — Deferral**
GIVEN the owner defers a question
WHEN outputs are produced
THEN dependent outputs behave as for missing information, and the deferral is not recorded as content.

**SCN-086 — Revision**
GIVEN the owner revises an earlier answer
WHEN dependent outputs are next produced
THEN they reflect the revised answer.

**SCN-087 — No pointless question**
GIVEN a fact is missing for a product whose outputs would be identical either way
WHEN questions are selected
THEN no question about it is presented.

**SCN-088 — Withdrawal after answering**
GIVEN the owner answered a question about a product that is later withdrawn
WHEN the product is withdrawn
THEN the answer remains recorded and is not discarded.

---

### 9. Inputs and Observable Outputs

**Inputs (semantic):** the set of facts the system needs but lacks, per product; each
product's participation in the working catalogue; the money at stake per product; prior
answers and deferrals.

**Outputs (semantic):**
- At most the presentation limit of questions, ordered, each stating the product, the
  fact sought, and why it matters.
- The effect of each answer on subsequent outputs.
- On request: how many candidate questions existed, how many were suppressed, and how
  many remain.

---

### 10. State / Lifecycle Semantics

Per question: **open** → **answered** or **deferred**.

| Transition | Legal |
|---|---|
| open → answered | Yes |
| open → deferred | Yes |
| deferred → open | Yes, on a later presentation |
| answered → answered (revised) | Yes (FR-090) |
| answered → open | **Illegal** without owner revision or a demonstrable change in the fact (FR-089) |
| open → suppressed | Yes, when another capability makes it moot (FR-082) |

Answers persist independently of the question's presentation state and of the
product's catalogue state (SCN-088).

---

### 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| No answerable questions remain | Present none; do not present an empty prompt or a completion score |
| The owner answers implausibly (e.g. a cost exceeding the selling price by a wide margin) | Record it, and let the receiving capability apply its own artefact rules (D-4). Do not silently discard the answer |
| An answer is supplied for a product that has since been withdrawn | Record it; do not present the question again (SCN-088) |
| Answer storage is unavailable | Do not present questions that cannot be recorded; an unrecorded answer wastes the owner's only scarce resource |
| The same fact is required by several capabilities | Ask once; the answer serves all (FR-093) |

---

### 12. Edge Cases

| Edge case | Resolution |
|---|---|
| A single answer would resolve a whole category | Exactly what FR-085 ranks first |
| The owner does not know the answer | Distinct from deferral — **OQ-501** |
| An answered fact later changes in reality | FR-089 permits re-asking only on demonstrable change; how change is demonstrated is **OQ-502** |
| Questions from several capabilities compete for the same limit | The limit is global, not per capability (INV-040). Cross-capability ordering follows FR-085 |
| Question surfaces compete with the 10-action surface for attention | Relationship undefined — **OQ-503** |
| Answering makes a product newly eligible for a money-bearing signal | Correct and expected; the signal appears at the next production |

---

### 13. Non-Functional Requirements

**NFR-040 (Owner effort)** — The total questions reaching the owner MUST be bounded by
suppression, not only by the presentation limit. A capability that suppresses nothing
and relies on the limit alone converts a bounded ask into an unbounded queue.

**NFR-041 (Determinism)** — The same open set, yields and prior answers MUST produce the
same ordering.

**NFR-042 (Durability)** — A recorded answer MUST survive across sessions and MUST NOT
be lost by ordinary use of the application.

---

### 14. Compatibility and External Constraints

- **C-40** — Existing behavior already bounds on-screen questions to three, with the
  stated rationale that a fourth turns the surface into a form and a form is abandoned.
  That bound is preserved (FR-084).
- **C-41** — Existing behavior ranks questions by money at stake multiplied by the
  number of products an answer would affect. That ranking is preserved (FR-085).
- **C-42** — D-7: answers do not propagate to the owner's point-of-sale system.
- **C-43** — Recorded answers share the durability guarantees of recorded decisions.

---

### 15. Acceptance Criteria

**AC-080** — No more than three questions are presented at once, under any input volume.
*(FR-084, INV-040)*

**AC-081** — No question is presented about a withdrawn product. *(FR-082, INV-041,
SCN-080)*

**AC-082** — The suppressed and remaining counts are reportable for any question class.
*(FR-083)*

**AC-083** — Given a broad question and a high-value narrow one, the broad question is
presented first. *(FR-085, SCN-082)*

**AC-084** — An answer changes dependent outputs at the next production without further
owner action. *(FR-088, SCN-083)*

**AC-085** — A recorded answer is not overwritten by any inference. *(FR-087, INV-042,
SCN-084)*

**AC-086** — A deferral leaves dependent outputs in their missing-information behavior
and records no content. *(FR-091, INV-043, SCN-085)*

**AC-087** — An answered question is not re-presented absent revision or demonstrable
change. *(FR-089)*

**AC-088** — No presented question is one whose answer changes no output. *(FR-080,
INV-044, SCN-087)*

**AC-089** — No backlog total or progress indicator is displayed alongside questions.
*(FR-086)*

**AC-090** — A recorded answer survives the product being withdrawn. *(SCN-088, NFR-042)*

---

### 16. Assumptions

**ASM-040** — The owner is the only available source for these facts; no external source
could supply them.

**ASM-041** — Answering three questions is acceptable to the owner within a session that
is already bounded at about ten minutes.

**ASM-042** — The owner's answer is more accurate than any inference the system could
make. This underpins FR-087 and is untested.

**ASM-043** — Suppression by catalogue withdrawal is sound: a product not worth keeping
is not worth asking about. Depends on SPEC-004's withdrawal being correct, and
therefore inherits OQ-401.

---

### 17. Open Questions

**OQ-501 (P1) — Is "I don't know" a distinct answer from a deferral?**
A deferral implies "later"; "I don't know" implies never. Without the distinction the
system re-presents a question the owner cannot answer. Affects FR-089, FR-091 and the
state model.

**OQ-502 (P1) — What constitutes a demonstrable change that permits re-asking?**
FR-089 allows re-asking on change but does not define it. Without a definition, either
answers ossify or the owner is re-interrogated. Affects FR-089.

**OQ-503 (P1) — Do questions occupy slots on the ten-action surface, or a separate
place?**
Both compete for the same limited attention, and both are bounded. If they share the
surface, the effective action budget is smaller than ten. Affects SPEC-006 and FR-084.

**OQ-504 (P2) — Does an answer expire?**
A cost price answered once may drift. Affects FR-089 and whether answers carry a
validity period.

**OQ-505 (P2) — May a member of staff answer, or only the owner?**
FR-087 grants answers authority over inference. If staff may answer, that authority
extends to them. Affects who may act on the question surface.

---

### 18. Non-Goals

- Building a general data-entry facility for the catalogue.
- Achieving complete cost coverage as an objective in itself.
- Teaching the owner to maintain his records.
- Asking about anything that does not change output.
- Measuring or scoring the owner's data quality.

---

### 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-010 | FR-080, FR-081 | SCN-087 | AC-088 |
| INT-010 | FR-082, FR-083 | SCN-080 | AC-081, AC-082 |
| INT-010 (D-8) | FR-084, FR-086 | SCN-081 | AC-080, AC-089 |
| INT-010 | FR-085 | SCN-082 | AC-083 |
| INT-010 | FR-087, FR-088 | SCN-083, SCN-084 | AC-084, AC-085 |
| INT-010 | FR-089, FR-090 | SCN-086 | AC-087 |
| INT-010 (D-3) | FR-091, FR-092 | SCN-085 | AC-086 |
| INT-010 | FR-093 | SCN-083 | AC-084 |
| INT-NS | NFR-040 | SCN-080 | AC-082 |
| Protected behavior | C-40, C-41 | SCN-081, SCN-082 | AC-080, AC-083 |
| Protected behavior | NFR-042 | SCN-088 | AC-090 |

---

## SPEC-006 — Daily Action Surface

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-NS, and every signal-producing intent (INT-001, INT-002,
INT-002B, INT-003, INT-009, INT-010)

---

### 1. Purpose

Defines the single surface the owner opens each morning: what may appear on it, how
many entries it may hold, how they are ordered when they are not measured in the same
units, and what he can do with each.

This specification governs **selection and presentation**. It does not define how any
individual signal is computed; each producing specification does that.

---

### 2. Intent Traceability

- **INT-NS** — one morning screen, ranked by money, no more than ten entries.
- Consumes entries produced under INT-001, INT-002, INT-002B, INT-003, INT-009,
  INT-010.

---

### 3. Scope

#### In Scope

- The bound on how many entries appear.
- Admission: which candidate entries may compete for a place.
- Ordering across signals measured in different units.
- The outcomes available to the owner per entry.
- Persistence and effect of those outcomes.
- What must be shown when there is nothing to act on.

#### Out of Scope

- How any signal is computed or thresholded.
- Any other screen in the application, including detail and browsing surfaces.
- Reporting on outcomes over time.
- Notifying the owner outside the application.

---

### 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | Store owner, once per day |
| **Secondary actor** | Store staff, where permitted to act — **OQ-603** |
| **Trigger** | The owner opens the surface |
| **Precondition** | At least one producing capability has published entries, or all have reported themselves unavailable |

---

### 5. Domain Terms

| Term | Definition |
|---|---|
| **Entry** | One thing the owner could act on today, produced by one capability, concerning one product |
| **Bound** | The maximum number of entries the surface may present. Ten (D-9) |
| **Admission** | The rule deciding which candidates may compete for a place |
| **Recurring value** | An amount realised on each sale |
| **Standing value** | An amount realised once |
| **Unvalued entry** | An entry that carries no monetary figure, by decision (D-1) or for want of data (D-3) |
| **Outcome** | The owner's recorded response to an entry |

---

### 6. Functional Requirements

#### The bound

**FR-100** — The surface MUST NOT present more than ten entries (D-9).

**FR-101** — The surface MUST NOT present a count of unshown entries, a backlog, or a
completion proportion. *(Rationale: the bound exists to make the day's work finishable;
displaying the remainder restores the firehose the bound removes.)*

**FR-102** — The owner MUST be able to reach the full set of entries for a capability
deliberately, on a surface other than this one.

#### Admission and ordering

**FR-103** — An entry MUST NOT be admitted unless its producing capability has stated it
is actionable today.

**FR-104** — Entries carrying a monetary value MUST be ordered by that value, descending.

**FR-105** — A recurring value and a standing value MUST NOT be compared as if
equivalent, and MUST NOT be summed to produce an ordering key (D-2). In V1 no capability
produces a standing value, so a single monetary ordering is well defined; this
requirement binds any capability that later introduces one.

**FR-106** — Unvalued entries MUST be admissible, and MUST NOT compete on the monetary
ordering. The surface MUST allocate places to unvalued entries explicitly rather than
ranking them against valued ones, and the allocation MUST be stated.

**FR-106a** — Unvalued entries MUST be ordered among themselves by a stated key
appropriate to their capability, and that key MUST NOT be a monetary proxy.

**FR-107** — Where an entry is admitted, the surface MUST show which capability produced
it, so that a confirmed loss is distinguishable from a question.

**FR-108** — The surface MUST NOT present the same product more than once at a time. Where
several capabilities produce entries for one product, one is presented; the selection
rule is part of **OQ-601**.

#### Per entry

**FR-109** — Every entry MUST state the action requested in terms of something the owner
can physically do.

**FR-110** — Every entry MUST carry the evidence its producing specification requires,
sufficient for the owner to verify it without leaving the surface.

**FR-111** — An entry whose value is an estimate MUST be labelled an estimate wherever
it appears on the surface (D-10).

**FR-112** — The owner MUST be able to record an outcome per entry that distinguishes at
least: acted upon; declined; deferred.

**FR-113** — A recorded outcome MUST persist and MUST NOT be lost by ordinary use of the
application.

**FR-114** — An entry with a recorded outcome MUST NOT reappear on the surface while
that outcome stands. The conditions under which a deferral lapses are **OQ-604**.

**FR-115** — A recorded outcome MUST survive its entry ceasing to be produced, and MUST
survive changes to the thresholds that produced it.

#### Aggregates

**FR-116** — Any summary figure the surface presents MUST obey the separation of
recurring from standing values (D-2), and MUST NOT present a single combined total.

**FR-117** — Where a capability has reported itself unavailable, the surface MUST show it
as unavailable rather than as producing no entries (D-3).

#### Empty state

**FR-118** — Where no entries are admitted and no capability is unavailable, the surface
MUST state that there is nothing to act on today. This MUST be distinguishable from an
error and from unavailability.

---

### 7. Behavioral Invariants

**INV-050** — The surface MUST NEVER present more than ten entries.

**INV-051** — A recurring and a standing value MUST NEVER appear summed.

**INV-052** — An estimated value MUST NEVER appear unlabelled.

**INV-053** — A recorded outcome MUST NEVER be lost by ordinary use.

**INV-054** — A hygiene entry MUST NEVER carry a monetary figure on this surface
(inherited from SPEC-002 INV-013).

**INV-055** — No entry may display a velocity claim unless its producing specification
supplies sales evidence for it (inherited protected behavior).

**INV-056** — The same product MUST NEVER occupy two places at once.

**INV-057** — An unavailable capability MUST NEVER be rendered as zero findings.

---

### 8. Behavioral Scenarios

**SCN-100 — The bound holds**
GIVEN hundreds of candidate entries
WHEN the surface is presented
THEN at most ten appear, and no count of the remainder is shown.

**SCN-101 — Ordering within one unit**
GIVEN several entries all carrying recurring values
WHEN the surface is presented
THEN they appear in descending order of that value.

**SCN-102 — Mixed units are not summed**
GIVEN entries carrying recurring values and entries carrying standing values
WHEN any summary is presented
THEN the two are shown separately and never as one total.

**SCN-103 — An estimate is labelled**
GIVEN an admitted entry whose value is an estimate
WHEN it appears
THEN it is labelled an estimate on the surface itself, not only in a detail view.

**SCN-104 — Outcome persists**
GIVEN the owner records an outcome
WHEN he returns later, including after a reload
THEN the outcome is still recorded and the entry does not reappear.

**SCN-105 — Outcome survives threshold change**
GIVEN the owner acted on an entry, and the producing threshold later changes so the entry is no longer produced
WHEN outcomes are reviewed
THEN the recorded outcome is still retrievable.

**SCN-106 — A capability is unavailable**
GIVEN a capability cannot produce entries because its inputs are missing
WHEN the surface is presented
THEN it is shown as unavailable, not as having found nothing.

**SCN-107 — Nothing to do**
GIVEN no entries are admitted and every capability is available
WHEN the surface is presented
THEN it states there is nothing to act on today.

**SCN-108 — One product, two signals**
GIVEN one product produces entries from two capabilities
WHEN the surface is presented
THEN the product occupies one place, and the producing capability of the shown entry is identified.

**SCN-109 — Full list on demand**
GIVEN the owner wants everything a capability found
WHEN he navigates deliberately to that capability
THEN the full set is available there, outside this surface's bound.

---

### 9. Inputs and Observable Outputs

**Inputs (semantic):** admitted candidate entries from each producing capability, each
with product identity, requested action, evidence, an optional value with its kind
(recurring or standing) and its certainty (confirmed or estimated), and the producing
capability; each capability's availability; previously recorded outcomes.

**Outputs (semantic):**
- At most ten entries, ordered, each with action, evidence, producing capability, and
  value where one exists with its kind and certainty.
- Availability status per capability.
- Recorded outcomes.
- An explicit empty state where applicable.

---

### 10. State / Lifecycle Semantics

Per entry: **presented** → **acted upon** / **declined** / **deferred**.

| Transition | Legal |
|---|---|
| presented → acted upon / declined / deferred | Yes |
| deferred → presented | Yes, when the deferral lapses (**OQ-604**) |
| acted upon → presented | Only if the underlying condition recurs after being resolved |
| declined → presented | **OQ-605** — does declining suppress permanently or for a period? |

Outcomes persist independently of entry production (FR-115).

---

### 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| One capability unavailable, others fine | Present the others; mark the unavailable one (FR-117) |
| Every capability unavailable | State that the surface cannot be produced; do not present an empty success state |
| Outcome cannot be recorded | Do not present the outcome as recorded; the owner must not believe he has acted when nothing is stored |
| Entry data incomplete (missing evidence a specification requires) | Do not admit it; an unverifiable entry costs one of ten places |
| Fewer than ten candidates | Present what exists; the bound is a maximum, not a target |
| Input data stale | Present the age of the data; the entries remain valid as of that data |

---

### 12. Edge Cases

| Edge case | Resolution |
|---|---|
| All ten places filled by one capability | Permitted by the bound; whether the surface should diversify is **OQ-606** |
| An unvalued hygiene entry outranks nothing because it has no value | The reason FR-106 and OQ-602 exist; hygiene work would otherwise never surface |
| A very large standing value dominates every recurring value permanently | The reason FR-105 and OQ-601 exist |
| The owner declines an entry that reappears with a changed value | Whether a changed value reopens a declined entry is part of **OQ-605** |
| Questions (SPEC-005) and actions compete for the same attention | **OQ-503**, shared with SPEC-005 |
| The owner acts in his own system without recording an outcome here | The entry persists until the underlying data changes; not an error |

---

### 13. Non-Functional Requirements

**NFR-050 (Completability)** — The surface MUST be reviewable in about ten minutes. This
is what the bound in FR-100 exists to protect, and it is the measurable expression of
the intent's own claim about the owner's daily commitment.

**NFR-051 (Explainability)** — Every entry MUST be verifiable by the owner against his
own records without assistance.

**NFR-052 (Durability)** — Recorded outcomes MUST survive session end, reload, and
ordinary use.

**NFR-053 (Determinism)** — The same candidate set, availability status and recorded
outcomes MUST produce the same surface.

---

### 14. Compatibility and External Constraints

- **C-50** — Existing behavior presents an unbounded ranked list of daily actions, and
  existing recorded decisions are keyed to entries in it. Introducing the bound MUST NOT
  invalidate previously recorded decisions (FR-115).
- **C-51** — Existing behavior makes the full set of findings reachable per capability.
  That reachability MUST be preserved (FR-102).
- **C-52** — Existing protected behavior: recorded decisions persist across sessions and
  survive clearing of transient state.
- **C-53** — Existing protected behavior: every surface renders in Arabic, Hebrew and
  English with no untranslated key reaching the screen, no horizontal overflow on a
  phone, and no number split across lines. The bound and the new entry kinds MUST NOT
  break these.
- **C-54** — Inherited: no velocity claim without sales evidence (INV-055).

---

### 15. Acceptance Criteria

**AC-100** — Under any candidate volume the surface presents at most ten entries.
*(FR-100, INV-050, SCN-100)*

**AC-101** — No count of unshown entries, backlog, or completion proportion appears.
*(FR-101, SCN-100)*

**AC-102** — Entries sharing a value kind appear in descending value order. *(FR-104,
SCN-101)*

**AC-103** — No summary presents a recurring and a standing value summed. *(FR-116,
INV-051, SCN-102)*

**AC-104** — Every estimated value is labelled on the surface itself. *(FR-111,
INV-052, SCN-103)*

**AC-105** — A recorded outcome survives reload and session end, and the entry does not
reappear. *(FR-113, FR-114, INV-053, SCN-104)*

**AC-106** — A recorded outcome remains retrievable after its entry ceases to be
produced. *(FR-115, C-50, SCN-105)*

**AC-107** — An unavailable capability is shown as unavailable, never as zero findings.
*(FR-117, INV-057, SCN-106)*

**AC-108** — With no entries and no unavailability, an explicit nothing-to-do state
appears, distinguishable from an error. *(FR-118, SCN-107)*

**AC-109** — No product appears twice at once. *(FR-108, INV-056, SCN-108)*

**AC-110** — The full set per capability remains reachable away from this surface.
*(FR-102, C-51, SCN-109)*

**AC-111** — No entry displays a velocity claim absent sales evidence. *(INV-055, C-54)*

**AC-112** — The surface renders in all three supported languages with no untranslated
key, no horizontal overflow on a phone viewport, and no number split across lines.
*(C-53)*

---

### 16. Assumptions

**ASM-050** — Ten entries is the right bound. It comes from the intent, not from
observation of the owner, and has not been tested with him.

**ASM-051** — Money at stake is the right ordering principle for what the owner should do
first. Urgency and effort are not modelled.

**ASM-052** — The owner reviews the surface roughly daily; entries are not designed for a
weekly or monthly rhythm.

**ASM-053** — Ten entries can be reviewed in about ten minutes (NFR-050). Untested.

**ASM-054** — Recording an outcome here is worth the owner's effort even though it
changes nothing in his own system.

---

### 17. Open Questions

**OQ-601 — RESOLVED (2026-09-08).** The question asked how recurring and standing values
rank against one another. It is moot: SPEC-002 no longer produces a monetary figure, so
V1 has one monetary kind and FR-104 alone orders it. FR-105 is retained to bind any
future standing-value capability.

**OQ-602 (P1, reduced from P0) — How many of the ten places are allocated to unvalued
entries, and by what key are they ordered among themselves?**
FR-106 settles that unvalued entries do not compete on money and require an explicit
allocation; it does not fix the number. Design can proceed on the allocation mechanism
while the number is decided from observation of the owner. SPEC-002 supplies gap ratio
as its own ordering key (FR-024); other unvalued capabilities need one under FR-106a.

**OQ-603 (P1) — May staff act on entries, or only the owner?**
Counting stock is plausibly a staff task; changing a price is plausibly not. Affects
FR-112 and what outcomes mean.

**OQ-604 (P1) — When does a deferral lapse?**
FR-114 suppresses a deferred entry while the deferral stands, but nothing defines its
duration. Without it, deferral is indistinguishable from permanent dismissal.

**OQ-605 (P1) — Does declining suppress an entry permanently?**
And does a materially changed value reopen it? Affects whether the owner must decline
the same item repeatedly.

**OQ-606 (P2) — Should the surface guarantee variety across capabilities?**
One capability may fill all ten places for a long period, starving the others. Affects
admission.

**OQ-607 (P2) — Should the surface distinguish today's new entries from carried-over
ones?**
Affects whether the owner can see progress without a completion indicator, which FR-101
forbids.

---

### 18. Non-Goals

- Reporting on outcomes over time (a separate, existing capability).
- Notifying the owner outside the application.
- Assigning work to staff.
- Replacing the per-capability browsing surfaces.
- Measuring the owner's compliance.

---

### 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-NS (D-9) | FR-100, FR-101 | SCN-100 | AC-100, AC-101 |
| INT-NS | FR-104 | SCN-101 | AC-102 |
| INT-NS (D-2) | FR-105, FR-116 | SCN-102 | AC-103 |
| INT-NS (D-10) | FR-111 | SCN-103 | AC-104 |
| INT-NS | FR-112, FR-113, FR-114 | SCN-104 | AC-105 |
| INT-NS | FR-115 | SCN-105 | AC-106 |
| INT-NS (D-3) | FR-117, FR-118 | SCN-106, SCN-107 | AC-107, AC-108 |
| INT-NS | FR-108 | SCN-108 | AC-109 |
| INT-NS | FR-102 | SCN-109 | AC-110 |
| INT-002B | FR-106, INV-054 | — | AC-103 |
| Protected behavior | INV-055, C-54 | — | AC-111 |
| Protected behavior | C-53 | — | AC-112 |
| Protected behavior | C-50, C-52 | SCN-105 | AC-106 |

---

## SPEC-007 — Figure Provenance and Reproducibility

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-PROV, and every figure-producing intent

---

### 1. Purpose

Defines the conditions under which the system may state a number, what must accompany
it, and how any number it states can be reproduced on demand in front of the person
questioning it.

---

### 2. Intent Traceability

- **INT-PROV** — every figure recomputable; no figure asserted from a stale document;
  the three code rules in `intent.md` §12.
- Applies to figures produced under INT-001, INT-002, INT-002B, INT-003, INT-009,
  INT-010.

---

### 3. Scope

#### In Scope

- The conditions under which a figure may be stated.
- What must accompany a stated figure.
- Reproduction of any stated figure on demand.
- Behavior when a figure cannot be stated honestly.
- Marking figures whose inputs have changed.

#### Out of Scope

- How any individual figure is computed.
- Presentation formatting.
- Any figure produced outside this system.

---

### 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | The team, stating figures to the owner |
| **Secondary actor** | The owner, challenging a figure |
| **Trigger** | Any presentation of a figure; or a demand to reproduce one |
| **Precondition** | The underlying data is available |

---

### 5. Domain Terms

| Term | Definition |
|---|---|
| **Stated figure** | Any number the system presents as describing the business |
| **Provenance** | The inputs, the rule and the input vintage that produced a figure |
| **Input vintage** | The point in time the underlying data represents |
| **Reproduction** | Recomputing a figure from current data by the same rule |
| **Stale figure** | A figure whose input vintage precedes the current available data |
| **Unstatable figure** | A figure whose inputs do not support an honest value |

---

### 6. Functional Requirements

#### Statement

**FR-120** — Every stated figure MUST be accompanied by its input vintage.

**FR-121** — Every stated figure MUST be reproducible from its inputs by a stated rule.

**FR-122** — A figure MUST NOT be stated whose provenance cannot be given.

**FR-123** — Where a figure depends on a derived threshold, the threshold in force MUST
be stated with it.

#### Reproduction

**FR-124** — The system MUST provide a means of recomputing all stated figures on
demand, in one action, without preparation.

**FR-125** — Reproduction MUST read current data rather than any recorded value of a
previous computation.

**FR-126** — Reproduction MUST NOT fall back to a remembered constant when an input is
unavailable. It MUST report the figure as unavailable (D-3).

**FR-127** — Reproduction MUST state both the input vintage and the time of
reproduction, so that a stale input is visible even when the reproduction is current.

#### Unstatable figures

**FR-128** — Where inputs do not support an honest value, the system MUST present no
figure. It MUST NOT present zero (D-3).

**FR-129** — The absence of a figure MUST be distinguishable from a figure of zero
wherever it appears.

**FR-130** — Where a figure rests on an input known to be unreliable, it MUST be marked
as an estimate at the point of statement, before it is challenged (D-10).

#### Staleness

**FR-131** — Where a document or surface states a figure, it MUST direct the reader to
reproduction rather than presenting the stated value as current.

**FR-132** — Where inputs refresh on a schedule independent of the reader, that fact
MUST be stated with any figure derived from them.

#### Composition

**FR-133** — A figure composed of others MUST be decomposable into them.

**FR-134** — A composite MUST NOT combine figures of different kinds — recurring with
standing, confirmed with estimated — without the components remaining visible (D-2).

---

### 7. Behavioral Invariants

**INV-060** — A figure MUST NEVER be stated without its input vintage.

**INV-061** — A missing figure MUST NEVER be rendered as zero.

**INV-062** — Reproduction MUST NEVER return a value that current data does not support.

**INV-063** — An estimated figure MUST NEVER appear unlabelled anywhere.

**INV-064** — A composite MUST NEVER hide the kinds of its components.

**INV-065** — The rule producing a figure MUST NEVER differ between the surface the
owner sees and the reproduction used to defend it.

---

### 8. Behavioral Scenarios

**SCN-120 — A figure is challenged**
GIVEN the owner disputes a stated figure
WHEN reproduction is performed in front of him
THEN the figure is recomputed from current data by the same rule, and its input vintage and reproduction time are stated.

**SCN-121 — Inputs have refreshed since the figure was written**
GIVEN a figure written in a document and inputs that have since refreshed
WHEN the figure is next used
THEN reproduction supplies the current value, and the document's role is to direct the reader to reproduction.

**SCN-122 — An input is unavailable**
GIVEN an input required for a figure is unavailable
WHEN reproduction is performed
THEN the figure is reported unavailable, and no remembered value is substituted.

**SCN-123 — A figure cannot be stated honestly**
GIVEN a product for which a value cannot be computed
WHEN it is presented
THEN no figure appears, and its absence is distinguishable from zero.

**SCN-124 — An estimate is marked before challenge**
GIVEN a figure resting on an unreliable input
WHEN it is first stated
THEN it is already labelled an estimate.

**SCN-125 — A composite is decomposed**
GIVEN a composite figure
WHEN it is presented
THEN its components and their kinds are visible with it.

**SCN-126 — Surface and reproduction agree**
GIVEN the same current data
WHEN a figure is read from the surface and from reproduction
THEN both give the same value by the same rule.

**SCN-127 — A threshold changed since the last statement**
GIVEN a derived threshold has moved
WHEN a dependent figure is reproduced
THEN the new threshold is stated with the figure, and the change is not presented as a change in the business.

---

### 9. Inputs and Observable Outputs

**Inputs (semantic):** the underlying business data with its vintage; the rules producing
each figure; the thresholds in force.

**Outputs (semantic):**
- Each figure with its input vintage, and its threshold where one applies.
- For composites: the components and their kinds.
- For unstatable figures: an explicit unavailability, distinguishable from zero.
- On reproduction: all figures, the input vintage, and the reproduction time.

---

### 10. State / Lifecycle Semantics

Figures hold no state. Provenance is a property of each statement, not of a stored
object. Nothing here is a lifecycle.

---

### 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| Underlying data absent | Report unavailability and name what is missing; produce no figures |
| One input among several absent | Produce the figures that input does not affect; report the rest unavailable |
| Data present but empty | Distinguish "no data" from "data showing nothing"; do not present zero for the former |
| A rule cannot be applied | State that the figure cannot be produced; do not approximate |
| Reproduction disagrees with a previously stated figure | The reproduction governs; the discrepancy is itself reportable |

---

### 12. Edge Cases

| Edge case | Resolution |
|---|---|
| A figure is quoted in a document intended for print | FR-131: the document directs to reproduction; the printed value carries its vintage |
| Inputs refresh between reproduction and the conversation using it | Vintage and reproduction time are both stated (FR-127), so the gap is visible |
| A figure is legitimately zero | Zero is stated as zero; only *unstatable* figures are absent (FR-129) |
| A composite has one unstatable component | The composite is unstatable; a partial composite would misstate the whole |
| A threshold changes and a count moves sharply | The count is not a business change; FR-123 and SCN-127 make the cause visible |

---

### 13. Non-Functional Requirements

**NFR-060 (Reproduction latency)** — Reproduction MUST complete quickly enough to be
performed during a conversation without the participants waiting on it.

**NFR-061 (Determinism)** — The same data and rules MUST produce the same figures.

**NFR-062 (Zero preparation)** — Reproduction MUST require no setup, no arguments and no
prior state beyond the data already present.

**NFR-063 (Coverage)** — Every figure stated in an owner-facing document or surface MUST
be reproducible. A figure that cannot be reproduced MUST be removed from that document
or surface rather than left standing.

---

### 14. Compatibility and External Constraints

- **C-60** — Some inputs refresh on an automated schedule independent of the team, so no
  stated figure remains valid indefinitely. This is the reason this specification exists.
- **C-61** — Some inputs are not carried in the repository and are regenerated locally.
  A figure derived from such an input is not reproducible on a fresh copy, and under
  NFR-063 MUST NOT be stated until it is. *(This currently affects the competitor
  comparison coverage figures.)*
- **C-62** — The three rules stated in `intent.md` §12 are binding: no money on a
  stock-derived signal; the data-entry artefact exclusion; no figure rather than zero.

---

### 15. Acceptance Criteria

**AC-120** — Every figure stated on an owner-facing surface or document carries its input
vintage. *(FR-120, INV-060)*

**AC-121** — Reproduction of all figures is available in one action with no preparation.
*(FR-124, NFR-062)*

**AC-122** — Reproduction with an input removed reports that figure unavailable and
substitutes no remembered value. *(FR-126, INV-062, SCN-122)*

**AC-123** — An unstatable figure appears as absent and is distinguishable from zero.
*(FR-128, FR-129, INV-061, SCN-123)*

**AC-124** — Every estimated figure is labelled at every point of statement. *(FR-130,
INV-063, SCN-124)*

**AC-125** — Reproduction states both input vintage and reproduction time. *(FR-127,
SCN-121)*

**AC-126** — Every composite shows its components and their kinds. *(FR-133, FR-134,
INV-064, SCN-125)*

**AC-127** — A figure read from the surface equals the figure from reproduction on the
same data. *(INV-065, SCN-126)*

**AC-128** — Every figure stated in the owner-facing intent document is reproducible; any
that is not has been removed. *(NFR-063, C-61)*

**AC-129** — A derived threshold is stated with every figure that depends on it.
*(FR-123, SCN-127)*

---

### 16. Assumptions

**ASM-060** — Reproducing a figure in front of the owner ends the dispute. This is the
intent's central claim about trust, and it is untested.

**ASM-061** — The data available at reproduction is the same data the surface used. If
the surface reads a published snapshot while reproduction reads source data, the two may
diverge without either being wrong.

**ASM-062** — Input vintage is knowable for every input.

**ASM-063** — The team has access to reproduction at the moment of challenge.

---

### 17. Open Questions

**OQ-701 (P1) — Which figures must be reproducible: those in owner-facing documents, or
every figure the system displays?**
NFR-063 currently binds owner-facing statements. Extending it to every displayed figure
is a far larger obligation. Affects FR-121 and NFR-063.

**OQ-702 (P1) — When reproduction and a published surface disagree, which is shown to the
owner?**
FR-125 makes reproduction authoritative, but the owner may be looking at the surface.
Affects INV-065 and the handling of ASM-061.

**OQ-703 (P2) — How far back must an input vintage be traceable?**
Whether the vintage is the data's own timestamp or the ingestion time affects what
FR-120 states.

**OQ-704 (P2) — Should reproduction record its own history?**
Comparing today's figures with last week's would show movement, but the intent does not
ask for trend reporting. Affects whether reproduction is stateless.

---

### 18. Non-Goals

- Trend reporting or figure history.
- Auditing who stated which figure when.
- Reproducing figures produced outside this system.
- Certifying the correctness of the underlying business data.

---

### 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-PROV | FR-120, FR-123 | SCN-127 | AC-120, AC-129 |
| INT-PROV | FR-121, FR-124, FR-125 | SCN-120 | AC-121, AC-127 |
| INT-PROV (D-3) | FR-126, FR-128, FR-129 | SCN-122, SCN-123 | AC-122, AC-123 |
| INT-PROV (D-10) | FR-130 | SCN-124 | AC-124 |
| INT-PROV | FR-127, FR-131, FR-132 | SCN-121 | AC-125 |
| INT-PROV (D-2) | FR-133, FR-134 | SCN-125 | AC-126 |
| INT-PROV | NFR-063 | — | AC-128 |
| Protected behavior | C-62 | — | AC-123, AC-124 |

---

## SPEC-GAPS — Gaps, Open Questions and Assumptions

**Status:** Living
**Version:** 0.1 (2026-09-08)
**Scope:** All specifications in this directory, against the intents in
[`intent.md`](intent.md)

This file records where the intent layer is contradictory, under-decided, or in
conflict with behavior the repository already protects. Nothing here has been resolved
by guessing.

---

### Part 1 — Specification Gaps Found

#### GAP-001 — The competitor-comparison intent contradicts protected behavior, and almost nothing survives the conflict

**Source:** `intent.md` §3 (INT-003) against existing store-format behavior enforced in
the repository and by an existing acceptance check.

**Problem:**
The intent derives its thresholds (a statistical break at 90%, a commercial bound at
60%) from a population of 1,970 comparisons drawn from three competitors. Existing
protected behavior classifies those three very differently:

| Competitor | Format | Existing treatment |
|---|---|---|
| The nearby forecourt shop | Same format as our store | May drive a recommendation |
| The supermarket | Below the comparability floor | **Context only — may not drive a recommendation** |
| The hypermarket | Affinity zero | **Dropped before any engine sees it** |

Applying the intent's thresholds under existing behavior:

| Threshold | Items above it | May drive a recommendation | Context-only source | Excluded source only |
|---|---:|---:|---:|---:|
| Commercial (60%) | 165 | **4** | 141 | 20 |
| Statistical (90%) | 24 | **1** | 22 | 1 |

An existing acceptance check fails the build when any recommendation is sourced from an
affinity-zero store, so this is not a matter of preference.

**Why it matters:**
INT-003 is a V1 intent. As specified it produces four actionable items, not 165. Either
the capability is far smaller than the intent implies, or the format policy must change.
The entire content of SPEC-003 turns on this, and so does whether INT-003 belongs in V1
at all.

**Recommended resolution:**
Split the capability. Keep the same-format comparison as the recommendation-driving
signal — it is small but defensible, and it carries the genuinely strong finding that
the store is 11% cheaper than its true peer. Treat cross-format differences as a
distinct, clearly labelled observation that never drives an action, and decide
separately whether an extreme cross-format difference (the 90% band) may be promoted to
an action with its format stated. Do not silently lower the comparability floor: it was
introduced precisely to stop absurd comparisons reaching the owner.

**Confidence:** High — the numbers are measured, not estimated.

---

#### GAP-002 — The daily surface cannot be ordered, because the intent forbids the only common unit

**Source:** `intent.md` preamble (INT-NS) against §2 (D-2).

**Problem:**
The surface must present "at most 10 actions, ranked by money". But the intent also
forbids ever combining a recurring per-sale amount with a standing one-time amount, and
separately requires that hygiene signals carry no money at all. So the surface must
produce one ordered list from three incommensurable kinds: recurring values, standing
values, and no value.

There is no rule anywhere for ranking them against one another.

**Why it matters:**
Without it, the ten-item bound cannot be applied. This is the surface the whole product
is organised around, and it cannot be built from the intents as written.

**Recommended resolution:**
Rank within kind, and allocate places across kinds explicitly — for example a fixed
number of places reserved for standing-value work and for unvalued hygiene work, with
the rest going to recurring value. An explicit allocation is defensible to the owner
("two of your ten are counting tasks"), whereas an implicit conversion between kinds
would breach D-2 by the back door.

**Confidence:** High on the gap; Medium on the specific allocation, which is a product
decision.

---

#### GAP-003 — Automatic withdrawal may make its own reversal unreachable

**Source:** `intent.md` §4 (INT-009).

**Problem:**
Withdrawal is justified by being reversible: a withdrawn product returns "on its first
sale". But a withdrawn product is absent from working surfaces, therefore absent from
ordering, therefore may not be restocked, therefore cannot sell. For seasonal products —
the exact case the zero-stock restriction was designed to protect against — the revival
condition may be unreachable in principle.

**Why it matters:**
It determines whether withdrawal may affect ordering surfaces at all, or only
attention-facing ones. That is a scope question, not an implementation one, and it
governs the shape of INT-009 and later INT-004.

**Status: RESOLVED (2026-09-08).** Not by weakening withdrawal, but by making its
strength follow the evidence. Withdrawal is re-evaluated on every ingestion (FR-060a);
while the window is shorter than a full annual cycle every withdrawal is declared
provisional (FR-063a); when the evidence reaches a full cycle the declaration stops and
earlier withdrawals are re-examined, returning those that prove seasonal (FR-063c).

The two-year sales evidence that closes this has already been requested from the owner,
so the gap has a dated resolution rather than an indefinite one. The residual exposure
in the interim is stated in OQ-401 and accepted.

**Confidence:** High.

---

#### GAP-004 — The reconciliation arithmetic assumes period alignment that has not been established

**Source:** `intent.md` §1 (INT-002) and the arithmetic it describes.

**Problem:**
The inconsistency test computes an implied opening balance from recorded stock,
receipts and sales. It is valid only if all three describe the same period. Recorded
stock is a current snapshot; receipts and sales come from monthly reports covering
January to July. If the snapshot post-dates the reports, every magnitude is wrong by the
activity in between — and the sign of the error is unknown.

**Why it matters:**
It affects both monetary totals in INT-002. The *detection* may survive (a negative
implied opening balance still indicates something is wrong), but the *magnitude* — and
therefore both the confirmed and the estimated figure — may not.

**Recommended resolution:**
Establish the vintage of each input before the flagged list is shown. **Partly overtaken
(2026-09-08):** the magnitude is no longer stated at all, so the exposure is now confined
to ordering and to the risk of flagging a consistent product. Establish the vintages;
where they cannot be aligned, state the window the flags rest on.

**Confidence:** Medium — the misalignment is plausible from the data vintages but has
not been confirmed.

---

#### GAP-005 — A V1 figure rests on data that is not reproducible

**Source:** `intent.md` §3 and §12 (INT-003, INT-PROV).

**Problem:**
The coverage figures for the competitor comparison derive from a matching artefact that
is not carried in the repository and is regenerated locally. Reproduction on a fresh
copy cannot produce them. This directly violates the intent's own rule that every stated
figure be reproducible on demand.

**Why it matters:**
The rule exists so a challenged figure can be recomputed in front of the owner. A figure
that cannot be is the exact failure the rule was written to prevent — and it appears in
a V1 intent.

**Recommended resolution:**
Either bring the derivation within reproduction, or remove the coverage figures from
owner-facing material until it is. Do not state them from the document.

**Confidence:** High — verified by inspection.

---

#### GAP-006 — "Data hygiene" is in V1 but cannot compete for a place on the only V1 surface

**Source:** `intent.md` §1 (INT-002B) against the preamble (INT-NS).

**Problem:**
INT-002B is deliberately money-free. The surface ranks by money. Strict ranking excludes
hygiene work permanently, so an intent that is in V1 has no route to the owner. The
intent does not say where this work is meant to appear.

**Why it matters:**
Either hygiene work needs reserved places on the surface, or it belongs somewhere else
entirely. Left unresolved, it will be built and then never seen.

**Recommended resolution:**
Resolve with GAP-002 as one allocation decision. Reserving a small number of places is
consistent with the intent treating hygiene as real work rather than as noise.

**Confidence:** High on the gap; the resolution follows GAP-002.

---

#### GAP-007 — The intent claims a ten-minute daily commitment that nothing verifies

**Source:** `intent.md` §10, and the ten-item bound in the preamble.

**Problem:**
"Ten minutes each morning" appears as an owner commitment, and the ten-item bound is
justified by it. Neither has been observed. Ten items each requiring the owner to walk
to a shelf and count is not a ten-minute task.

**Why it matters:**
The bound is the core product decision of V1, and the acceptance criterion for the
surface (NFR-050) is stated in terms of this claim. If the claim is wrong, the bound is
wrong.

**Recommended resolution:**
Measure it during the pilot rather than asserting it. Until measured, treat ten as a
provisional bound and state it as provisional in owner-facing material.

**Confidence:** Medium.

---

#### GAP-008 — The V2 ordering intent states an order of inputs, not a rule

**Source:** `intent.md` §6 (INT-004).

**Problem:**
The intent establishes that ordering starts from market movement, is then compared with
the store's own movement, and is capped by shelf life. That is a sequence of inputs. It
is not a rule: it does not say how the three combine into a quantity, nor what
geographic extent defines "the market", nor what happens when market movement and the
store's own movement disagree.

**Why it matters:**
INT-004 is described as carrying the largest value in the product. It cannot be
specified, and therefore cannot be designed, from a sequence of inputs.

**Recommended resolution:**
Do not specify INT-004 yet. Resolve the radius, the combination rule and the
disagreement case as explicit product decisions first. Its release is far enough out
that this does not block V1.

**Confidence:** High.

---

### Part 2 — Open Questions by Priority

#### P0 — blocks system design

| ID | Question | Spec |
|---|---|---|
| **OQ-301** | May a context-only competitor source drive a surfaced signal when the difference is extreme? | SPEC-003 |

**Resolved or downgraded since version 0.1**, all by one decision — SPEC-002 no longer
produces a monetary figure:

| ID | Now |
|---|---|
| ~~OQ-601~~ | **Moot.** With no standing amount in V1 there is one monetary kind, and FR-104 alone orders it |
| ~~OQ-602~~ | **P1.** The principle is settled (FR-106: unvalued work gets a stated allocation, not a rank); only the number of places is open |
| ~~OQ-201~~ | **P1.** Period alignment governed the magnitude, which is no longer stated. Detection does not depend on it |
| ~~OQ-401~~ | **Resolved.** Withdrawal is re-evaluated on every ingestion and its strength follows the evidence window; a full annual cycle triggers re-examination of earlier withdrawals. Narrowed to OQ-407 (P1) |
| ~~OQ-406~~ | **Resolved.** The window follows available evidence. Narrowed to OQ-408 (P2) |

#### P1 — important, but design can begin

| ID | Question | Spec |
|---|---|---|
| OQ-101 | Is there a materiality floor for a price difference? | SPEC-001 |
| OQ-102 | Can the owner mark an inverted price as deliberate, suppressing it? | SPEC-001 |
| OQ-202 | What is the materiality floor for an unaccounted quantity? | SPEC-002 |
| OQ-203 | When a product is both flagged for discrepancy and dead, which governs? | SPEC-002 / SPEC-004 |
| OQ-302 | When several stores observe one product, which is the benchmark? | SPEC-003 |
| OQ-303 | How are pack-size mismatches on a shared identifier handled? | SPEC-003 |
| OQ-402 | Is there an introduction grace period for new products? | SPEC-004 |
| OQ-407 | Should a withdrawn entry stay visible on ordering surfaces while the evidence is short? | SPEC-004 |
| OQ-403 | May the owner withdraw a product manually? | SPEC-004 |
| OQ-501 | Is "I don't know" distinct from a deferral? | SPEC-005 |
| OQ-502 | What constitutes a demonstrable change permitting a question to be re-asked? | SPEC-005 |
| OQ-503 | Do questions occupy places on the ten-action surface, or a separate place? | SPEC-005 / SPEC-006 |
| OQ-603 | May staff act on entries, or only the owner? | SPEC-006 |
| OQ-604 | When does a deferral lapse? | SPEC-006 |
| OQ-605 | Does declining suppress an entry permanently? | SPEC-006 |
| OQ-701 | Which figures must be reproducible — owner-facing, or all? | SPEC-007 |
| OQ-702 | When reproduction and a surface disagree, which is shown? | SPEC-007 |

#### P2 — safely deferred

| ID | Question | Spec |
|---|---|---|
| OQ-103 | Should the markup ceiling be per department or per store? | SPEC-001 |
| OQ-104 | Should the delivery-price signal carry a monetary figure at all? | SPEC-001 |
| OQ-204 | After a physical count, may a monetary figure be reinstated for counted products? | SPEC-002 |
| OQ-304 | Should a competitor promotion be distinguished from a price change? | SPEC-003 |
| OQ-305 | Should a distance bound apply in addition to format affinity? | SPEC-003 |
| OQ-306 | What is the observation freshness bound? | SPEC-003 |
| OQ-404 | What happens to a revived product that still does not sell? | SPEC-004 |
| OQ-405 | What defines an implausible recorded quantity? | SPEC-004 |
| OQ-408 | What exactly constitutes a full annual cycle? | SPEC-004 |
| OQ-504 | Does an owner's answer expire? | SPEC-005 |
| OQ-505 | May staff answer questions, or only the owner? | SPEC-005 |
| OQ-606 | Should the surface guarantee variety across capabilities? | SPEC-006 |
| OQ-607 | Should new entries be distinguished from carried-over ones? | SPEC-006 |
| OQ-703 | How far back must an input vintage be traceable? | SPEC-007 |
| OQ-704 | Should reproduction record its own history? | SPEC-007 |

---

### Part 3 — Assumptions Introduced

None of these is stated by the intents. Each was necessary to make a specification
coherent, and each is a candidate to be confirmed with the owner.

| ID | Assumption | Spec | Risk if wrong |
|---|---|---|---|
| ASM-001 | The delivery-price column is the store's own listing | SPEC-001 | The whole signal compares the wrong two things |
| ASM-002 | A markup within the observed ceiling is deliberate policy, not drift | SPEC-001 | Real pricing drift is suppressed as policy |
| ASM-003 | Platform commission is unavailable, so the ceiling is inferred from behaviour | SPEC-001 | The ceiling encodes habit rather than economics |
| ASM-004 | Both prices in one export are contemporaneous | SPEC-001 | Stale pairs produce phantom differences |
| ASM-010 | Flow quantities are more reliable than stock levels | SPEC-002 | The two-tier split has no basis |
| ASM-011 | Stock, receipts and sales cover the same period | SPEC-002 | See GAP-004 — magnitudes wrong |
| ASM-012 | One cost price per product is adequate for valuation | SPEC-002 | Valuations drift with cost changes |
| ASM-013 | Quantity unreliability is catalogue-wide, not departmental | SPEC-002 | Over- or under-flagging by department |
| ASM-020 | A shared identifier denotes the same sellable unit | SPEC-003 | False matches produce spurious extremes |
| ASM-021 | Observed competitor prices were actually charged | SPEC-003 | Comparison against list prices |
| ASM-022 | Format affinity encodes product judgement, not data quality | SPEC-003 | GAP-001's resolution changes |
| ASM-023 | Observations refresh often enough that freshness rarely binds | SPEC-003 | Stale comparisons drive actions |
| ASM-030 | Absence from sales evidence means the product did not sell | SPEC-004 | Withdrawal removes selling products |
| ASM-031 | Zero stock plus no sales means already absent from the shelf | SPEC-004 | The justification for automatic withdrawal fails |
| ASM-032 | Product identifiers are stable across the window | SPEC-004 | Re-coded products appear dead |
| ASM-033 | The owner needs no notice before automatic withdrawal | SPEC-004 | Withdrawal feels like data loss |
| ASM-034 | Recorded stock is contemporaneous with the window's end | SPEC-004 | Misclassification at the boundary |
| ASM-040 | The owner is the only source for the facts asked | SPEC-005 | Avoidable questions reach him |
| ASM-041 | Three questions fit inside a ten-minute session | SPEC-005 | Questions displace actions |
| ASM-042 | The owner's answer beats any inference | SPEC-005 | Wrong answers become authoritative |
| ASM-043 | A product not worth keeping is not worth asking about | SPEC-005 | Inherits GAP-003 |
| ASM-050 | Ten is the right bound | SPEC-006 | The core V1 decision is wrong |
| ASM-051 | Money is the right ordering principle | SPEC-006 | Urgent low-value work is never done |
| ASM-052 | The owner reviews roughly daily | SPEC-006 | Entries stale between reviews |
| ASM-053 | Ten entries take about ten minutes | SPEC-006 | See GAP-007 |
| ASM-054 | Recording an outcome is worth the owner's effort | SPEC-006 | Outcomes go unrecorded, measurement fails |
| ASM-060 | Reproducing a figure ends a dispute | SPEC-007 | The trust strategy does not work |
| ASM-061 | Reproduction and the surface read the same data | SPEC-007 | They can disagree without either being wrong |
| ASM-062 | Input vintage is knowable for every input | SPEC-007 | Some figures cannot carry provenance |
| ASM-063 | Reproduction is available at the moment of challenge | SPEC-007 | The defence is unavailable when needed |

---

### Part 4 — Contradictions Between Intents

**CON-001 — "Ranked by money" against "hygiene carries no money."**
INT-NS orders the surface by money; INT-002B forbids money on hygiene signals and places
them in V1. Both cannot hold under strict ranking. Tracked as GAP-006 and OQ-602.

**CON-002 — "Recurring and standing are never summed" against "one ranked list."**
INT-002's D-2 and INT-NS's single ordered surface. Tracked as GAP-002 and OQ-601.

**CON-003 — "Withdrawal is reversible on the first sale" against "withdrawn products are
excluded from other capabilities."**
INT-009 states both. **Resolved (2026-09-08):** revival no longer depends solely on a
sale. Extending the evidence to a full annual cycle re-examines every withdrawal and
returns those that prove seasonal (FR-063c), so the reversal path does not require the
product to be on a shelf. Whether withdrawn entries should also stay visible on ordering
surfaces meanwhile is OQ-407.

**CON-004 — "Every figure is reproducible" against a V1 figure that is not.**
INT-PROV and INT-003. Tracked as GAP-005.

---

### Part 5 — Repository Behavior That Contradicts an Intent

**REPO-001 — Competitor comparison.**
The intent's §3 analysis treats all three competitors as usable sources. The repository
drops one entirely and forbids another from driving a recommendation, and an existing
acceptance check enforces it. See GAP-001.

**REPO-002 — The unbounded daily list.**
Existing behavior presents every actionable finding on the daily surface. INT-NS bounds
it at ten. This is an intended change, recorded here so the compatibility obligation is
explicit: previously recorded decisions must survive the change (SPEC-006 FR-115, C-50).

**REPO-003 — Negative stock is clamped at the data boundary.**
Existing behavior clamps negative stock to zero for downstream consumers while reporting
the count separately. SPEC-004's withdrawal rule must read the recorded value, not the
clamped one; otherwise a negative-stock product would appear to have zero stock and
become withdrawable, silently violating INV-030. Recorded as SPEC-004 C-32.
