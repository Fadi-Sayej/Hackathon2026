# SPEC-003 — Competitor Price Position

**Status:** **Draft — BLOCKED.** See GAP-001. The requirements below are stated so the
blocking conflict is precise, but this specification MUST NOT be handed to system
design until OQ-301 is answered.
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-003, INT-NS, INT-PROV

---

## 1. Purpose

Defines when the store's price for a product is surfaced as out of line with prices at
nearby stores, and how the difference in store format is accounted for so that a
legitimate forecourt premium is not reported as a fault.

---

## 2. Intent Traceability

- **INT-003** — "Are my prices reasonable against my neighbours?"
- **INT-NS** — contributes ranked entries to the daily surface (SPEC-006).
- **INT-PROV** — every threshold and count recomputable (SPEC-007).

---

## 3. Scope

### In Scope

- Comparison of the store's shelf price against prices for the same product at other
  stores.
- Accounting for store format when interpreting a difference.
- Deciding which differences are surfaced, and how they are characterised.
- Stating the coverage limits of the comparison.

### Out of Scope

- The store's own delivery-platform price (SPEC-001).
- Recommending a corrected price.
- Products the market carries and this store does not (INT-005, unspecified).
- Any judgement of a competitor's pricing.

---

## 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | Store owner |
| **Trigger** | Ingestion of a new competitor price observation set, or of a new store export |
| **Precondition** | A product is identified at both this store and at least one other store by a shared product identifier |

---

## 5. Domain Terms

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

## 6. Functional Requirements

### Source discipline — protected behavior

**FR-040** — The system MUST NOT base a surfaced recommendation on an excluded source.

**FR-041** — The system MUST NOT base a surfaced recommendation on a context-only
source **unless OQ-301 resolves otherwise**. Until then this requirement stands as
existing protected behavior.

**FR-042** — Where an observation is displayed for context, the system MUST label the
observing store's format and MUST state that part of any difference is attributable to
format.

**FR-043** — The system MUST record, per surfaced item, which source drove it, so that
compliance with FR-040 and FR-041 is verifiable.

### Thresholds

**FR-044** — The statistical outlier threshold MUST be derived from the observed
distribution of differences, not assumed.

**FR-045** — The commercial threshold MUST be expressed as a stated multiple of the
observed median difference against comparable sources, so that it moves with the market
rather than being a fixed percentage.

**FR-046** — Both thresholds MUST be reportable alongside any count that depends on
them.

### Characterisation

**FR-047** — An item exceeding the statistical outlier threshold MUST be characterised
as an anomaly warranting verification of the price, not as overcharging.

**FR-048** — An item exceeding the commercial threshold but not the statistical one
MUST be characterised as a question about intent.

**FR-049** — The system MUST NOT characterise any difference as an error without owner
confirmation.

### Coverage honesty

**FR-050** — The system MUST state what proportion of the catalogue has any comparable
price at all, and MUST NOT present the comparison as covering the catalogue.

**FR-051** — For a product with no comparison available, the system MUST show that no
comparison exists rather than showing no difference (D-3).

**FR-052** — The system MUST distinguish products that are structurally uncomparable —
services and internally-coded items that no other retailer sells — from products merely
not yet matched, and MUST NOT count the former as a coverage failure.

### Position reporting

**FR-053** — The system MUST be able to report the store's overall price position
against each comparable source, including when the store is cheaper.

---

## 7. Behavioral Invariants

**INV-020** — No surfaced recommendation may be traceable to an excluded source.

**INV-021** — Every displayed competitor observation carries its store's format.

**INV-022** — A difference explained by format alone MUST NOT be characterised as a
fault.

**INV-023** — Coverage claims MUST always be expressed against the full catalogue, not
against the matched subset.

**INV-024** — The store's own price MUST NOT serve as its own benchmark (D-5).

---

## 8. Behavioral Scenarios

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

## 9. Inputs and Observable Outputs

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

## 10. State / Lifecycle Semantics

Comparison results are derived per ingestion and hold no lifecycle state. Observation
freshness is a property of the input, not a state of the product.

---

## 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| No comparable-format source available at all | The recommendation-driving signal is unavailable; report it as unavailable, not as zero findings |
| Observation set stale beyond the freshness bound | Do not drive recommendations from it; mark age where displayed (SCN-047) |
| Product identifier matched but products differ in size or pack | Comparison invalid — **OQ-303**, unresolved |
| A store's format is unknown | Treat as the existing unknown-format affinity; do not assume comparability |
| Threshold underivable from the distribution | Suppress the derived-threshold signal and report it as undetermined (D-3) |
| Competitor data absent entirely | Report the whole capability as unavailable; other specifications unaffected |

---

## 12. Edge Cases

| Edge case | Resolution |
|---|---|
| The store is *cheaper* than a comparable peer by a large margin | Not a fault. May be a margin signal, which belongs to a different capability — out of scope here |
| Only one comparable-format store exists in range | A single source drives every comparable signal; the concentration MUST be visible in output (FR-043) |
| A competitor runs a temporary promotion | Indistinguishable from a price change with current evidence — **OQ-304** |
| The same product is observed at several stores with different prices | Which observation is the benchmark is undefined — **OQ-302** |
| A comparable store is geographically far while an excluded one is adjacent | Format governs, not distance, under current protected behavior. Whether distance should also bound the set is **OQ-305** |

---

## 13. Non-Functional Requirements

**NFR-020 (Explainability)** — Every surfaced item MUST name the store it was compared
against and that store's format.

**NFR-021 (Determinism)** — The same observation set and the same store classifications
MUST produce the same surfaced set and thresholds.

**NFR-022 (Freshness)** — An observation older than the freshness bound MUST NOT drive
a recommendation. The bound itself is **OQ-306**.

---

## 14. Compatibility and External Constraints

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

## 15. Acceptance Criteria

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

## 16. Assumptions

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

## 17. Open Questions

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

## 18. Non-Goals

- Recommending a corrected price.
- Matching products across stores by name or description.
- Tracking competitor price history or trends.
- Assessing competitors' pricing strategy.
- Expanding the observed store set.

---

## 19. Traceability Matrix

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
