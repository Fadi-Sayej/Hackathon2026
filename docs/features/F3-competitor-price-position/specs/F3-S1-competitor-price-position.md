---
ID: F3-S1
Title: Competitor Price Position
Status: Approved — passed the Intent → Spec conformance gate (run 2, CONDITIONAL PASS)
Version: 1.1
Parent: [F3 — Competitor Price Position](../intent.md)
Related Intents: INT-003
Legacy ID: SPEC-003 (in the pre-migration monolithic `specs.md` v1.1)
Answered by: [System Design](../../../architecture/system-design.md) §21
---

> **Identifier note.** The requirement identifiers inside this document (`FR-…`, `INV-…`,
> `NFR-…`, `AC-…`, `SCN-…`, `C-…`, `ASM-…`, `OQ-…`) are **unchanged** from `specs.md` v1.1
> and remain globally unique across the specification layer. They are the ids used by the
> two gate reports, by the System Design's traceability matrix (§21) and by the
> implementation plan. Where a fully-qualified form is wanted, prefix with the spec id:
> `F3-S1.FR-001`. Nothing was renumbered by the documentation migration.

# F3-S1 — Competitor Price Position

**Status:** Draft. GAP-001 and OQ-301 are resolved (2026-09-08): the capability is
governed by a declared pricing policy measured against a balanced reference, and gated by
a cost floor that precedes every comparison.
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
| **Attention threshold** | The premium over the reference at which a policy breach warrants same-day attention rather than unhurried review. Declared, not derived. Currently **+100%** |
| **Pricing policy** | The maximum premium over the reference price the owner accepts, declared by him rather than derived from the observed distribution. Currently **+60%** |
| **Balanced reference** | The midpoint of the cheapest supermarket price and the cheapest same-format price for a product. Where no same-format price exists, the supermarket price plus a **format allowance** |
| **Format allowance** | The typical premium of same-format stores over supermarkets, measured from products for which both prices are held. Measured, never assumed |
| **Cost floor** | The minimum margin a reference price must leave over our purchase cost before it may be used to recommend a price reduction. Currently **10%** |

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

#### The cost floor — evaluated before any comparison

**FR-043a** — The system MUST NOT surface a price-reduction signal for a product whose
reference price fails to exceed our purchase cost by at least the cost floor.

*Rationale: a competitor's price is not evidence that our price is wrong. The competitor
may buy at a lower cost, or may be selling at a loss deliberately. In the pilot data, 43
of 144 products exceeding the policy would have produced a recommendation that puts the
owner below or barely above cost — one where the reference price is a third of our own
purchase cost.*

**FR-043b** — The cost floor MUST be evaluated before the policy comparison, and a
product failing it MUST NOT be reinstated by any magnitude of price difference.

**FR-043c** — A product failing the cost floor MUST be re-characterised as a **purchase
cost** finding — the competitor sells below our cost — and MUST NOT be presented as a
pricing fault.

**FR-043d** — Where a product has no purchase cost, the system MUST NOT evaluate it
against the policy at all, and MUST NOT substitute an assumed cost (D-3).

#### The reference price

**FR-044** — The reference price MUST be the midpoint of the cheapest supermarket price
and the cheapest same-format price where both are held.

**FR-044a** — Where no same-format price is held, the reference MUST be the supermarket
price increased by the format allowance, and the substitution MUST be visible on the
resulting signal.

**FR-044b** — The format allowance MUST be measured from products for which both a
supermarket and a same-format price are held. It MUST NOT be an assumed constant, and
MUST be reportable.

**FR-044c** — Where neither price is held, no comparison MUST be produced (D-3).

#### The policy

**FR-045** — The policy threshold MUST be a declared maximum premium over the reference
price, settable as a product decision, and MUST NOT be derived from the observed
distribution.

**FR-045a** — Every product exceeding the policy MUST be recorded as a policy breach,
whatever the surface it is later shown on.

**FR-045b** — The system MUST separate policy breaches into those warranting same-day
attention and those for unhurried review. The separating threshold is the **attention
threshold**, currently a premium of **+100%** over the reference price, and it MUST be
stated wherever the separation is presented. Like the policy threshold it is declared,
not derived (FR-045). This separation governs **where** a breach appears, never
**whether** it is a breach.

**FR-046** — The policy threshold, the cost floor, the format allowance and the
attention-separating threshold MUST all be reportable alongside any count that depends on
them.

#### Characterisation

**FR-047** — A policy breach warranting same-day attention MUST be characterised as a
price to verify, not as overcharging.

**FR-048** — A policy breach for unhurried review MUST be characterised as a departure
from the owner's declared policy, and MUST state the policy it departs from.

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

**INV-025** — The system MUST NEVER recommend a price that fails to exceed our purchase
cost by at least the cost floor. No difference, however large, may override this.

**INV-026** — A reference price MUST NEVER be a single competitor's price where a
balanced reference is obtainable.

**INV-023** — Coverage claims MUST always be expressed against the full catalogue, not
against the matched subset.

**INV-024** — The store's own price MUST NOT serve as its own benchmark (D-5).

---

### 8. Behavioral Scenarios

**SCN-039a — The cost floor blocks a losing recommendation**
GIVEN a product we sell at ₪158.21 and buy at ₪147.11, whose cheapest competitor price is ₪54.00
WHEN the comparison runs
THEN no price-reduction signal is produced, and the product is re-characterised as a purchase-cost finding.

**SCN-039b — A thin margin is treated as a failure of the floor**
GIVEN a reference price exceeding our cost by less than the cost floor
WHEN the comparison runs
THEN the product is excluded from the policy comparison exactly as if the reference were below cost.

**SCN-039c — Missing cost blocks judgement entirely**
GIVEN a product with no recorded purchase cost
WHEN the comparison runs
THEN it is not evaluated against the policy, and no assumed cost is substituted.

**SCN-039d — Balanced reference from two sources**
GIVEN a product priced ₪3.90 at the cheapest supermarket and ₪4.90 at the cheapest same-format store
WHEN the reference is computed
THEN it is their midpoint, and the policy is measured against that.

**SCN-039e — Same-format price unavailable**
GIVEN a product with a supermarket price and no same-format price
WHEN the reference is computed
THEN it is the supermarket price plus the measured format allowance, and the signal shows that the allowance was applied.

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
- The four declared values in force: the pricing policy, the attention threshold, the
  cost floor and the measured format allowance (FR-046).
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
| Format allowance not measurable — no product holds both a supermarket and a same-format price | No reference may be substituted for a product lacking a same-format price; report those products as having no comparison (FR-044c, D-3) |
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
- **C-24** — No recommendation produced anywhere in the system may direct the owner to a
  price that fails to exceed his purchase cost by the stated floor. This binds every
  capability, present and future, not only this one.

---

### 15. Acceptance Criteria

**AC-040** — No surfaced recommendation is traceable to an excluded source, verified by
the existing acceptance check. *(FR-040, INV-020, C-20)*

**AC-041** — No surfaced recommendation is traceable solely to a context-only source
while OQ-301 is unresolved. *(FR-041, C-21)*

**AC-042** — Every displayed competitor observation shows the observing store's format.
*(FR-042, INV-021)*

**AC-043** — All four values named in FR-046 — the pricing policy, the attention
threshold, the cost floor and the measured format allowance — are reported with any count
derived from them, and recomputation reproduces both the values and the counts.
*(FR-046, FR-045b, NFR-021)*

**AC-044** — Coverage is stated against the full catalogue and separates structurally
uncomparable items. *(FR-050, FR-052, INV-023)*

**AC-045** — A product with no comparison shows "no comparison", never a zero
difference. *(FR-051, SCN-044)*

**AC-046** — The store's position against its comparable peer is reportable, including
when favourable. *(FR-053, SCN-043)*

**AC-047** — No output characterises a difference as an error without owner
confirmation, and every unhurried-review breach names the declared policy it departs
from. *(FR-048, FR-049)*

**AC-047a** — A difference wholly attributable to store format is not characterised as a
fault anywhere in the output. *(INV-022)*

**AC-047b** — No reference price, and no figure any recommendation is measured against,
is the store's own price. *(INV-024, C-23, D-5)*

**AC-049** — No price-reduction signal exists whose reference price fails to exceed our
purchase cost by the cost floor. *(FR-043a, INV-025, SCN-039a, SCN-039b)*

**AC-050** — A product failing the cost floor appears as a purchase-cost finding, not as
a pricing fault, whatever the size of the difference. *(FR-043b, FR-043c)*

**AC-051** — A product without a purchase cost is absent from the policy comparison, and
no assumed cost appears anywhere. *(FR-043d, SCN-039c)*

**AC-052** — Where both a supermarket and a same-format price are held, the reference is
their midpoint. *(FR-044, SCN-039d)*

**AC-053** — Where no same-format price is held, the applied format allowance is visible
on the signal and is reproducible from the products holding both prices. *(FR-044a,
FR-044b, SCN-039e)*

**AC-054** — Every product exceeding the policy is recorded as a breach regardless of
which surface displays it. *(FR-045a, FR-045b)*

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

**ASM-024** — The recorded purchase cost is the true cost of acquiring the product,
excluding rebates, volume terms and supplier credits that would lower it. If cost is
overstated, the cost floor suppresses recommendations that would in fact be profitable.

**ASM-025** — The format allowance measured from products holding both prices
generalises to products holding only a supermarket price. Those 426 products may not be
representative of the 1,215 they stand in for.

**ASM-026** — A competitor's observed price reflects its own cost structure rather than a
temporary promotion. Where it is a promotion, the cost floor still protects the owner,
but the reference is understated.

---

### 17. Open Questions

**OQ-301 — RESOLVED (2026-09-08).**
The question was whether a source of a different store format may drive a signal, given
that existing behavior forbids it and only 4 of 165 candidates survived.

**Decision: it may, but never alone and never as a bare price.** A cross-format price
enters only as one half of a balanced reference (FR-044), paired with a same-format price
or adjusted by a measured format allowance (FR-044a). The comparison is then made against
a declared policy the owner sets, not against another store's price.

This preserves what the format rule protects — the owner is never told he is expensive
because a hypermarket is cheaper — while letting a genuine outlier through, because a
product priced at more than double a balanced reference is not explained by format.

**A stronger constraint arrived with it, and it changes the capability more than the
format question did:** FR-043a's cost floor. A competitor's price is not evidence that
ours is wrong — the competitor may buy cheaper, or sell at a loss. In the pilot data 43
of 144 policy breaches would have recommended a price at or below our own purchase cost.
Those are now excluded before any comparison and re-characterised as purchase-cost
findings.

**Net effect on the pilot data:** 1,970 compared → 144 exceed the policy → **97 survive
the cost floor**, of which roughly 15 warrant same-day attention.

**OQ-302 — RESOLVED (2026-09-08) by FR-044.** The benchmark is never one store: it is
the midpoint of the cheapest supermarket price and the cheapest same-format price, or the
cheapest supermarket price plus the measured format allowance where no same-format price
exists. "Cheapest within each format" settles which observation is used; nothing else is
selected between.

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
| INT-003 (D-5) | INV-024, C-23 | — | AC-047b |
| INT-003 | INV-022 | SCN-042 | AC-047a |
| INT-003 | FR-050, FR-052 | SCN-045 | AC-044 |
| INT-003 (D-3) | FR-051 | SCN-044, SCN-046 | AC-045 |
| INT-003 | FR-053 | SCN-043 | AC-046 |
| INT-PROV | NFR-021 | — | AC-043 |
| Protected behavior | C-20, C-21, INV-020 | SCN-041 | AC-040, AC-041 |
| Protected behavior | NFR-022 | SCN-047 | AC-048 |
