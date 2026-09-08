# SPEC-007 — Figure Provenance and Reproducibility

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-PROV, and every figure-producing intent

---

## 1. Purpose

Defines the conditions under which the system may state a number, what must accompany
it, and how any number it states can be reproduced on demand in front of the person
questioning it.

---

## 2. Intent Traceability

- **INT-PROV** — every figure recomputable; no figure asserted from a stale document;
  the three code rules in `intent.md` §12.
- Applies to figures produced under INT-001, INT-002, INT-002B, INT-003, INT-009,
  INT-010.

---

## 3. Scope

### In Scope

- The conditions under which a figure may be stated.
- What must accompany a stated figure.
- Reproduction of any stated figure on demand.
- Behavior when a figure cannot be stated honestly.
- Marking figures whose inputs have changed.

### Out of Scope

- How any individual figure is computed.
- Presentation formatting.
- Any figure produced outside this system.

---

## 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | The team, stating figures to the owner |
| **Secondary actor** | The owner, challenging a figure |
| **Trigger** | Any presentation of a figure; or a demand to reproduce one |
| **Precondition** | The underlying data is available |

---

## 5. Domain Terms

| Term | Definition |
|---|---|
| **Stated figure** | Any number the system presents as describing the business |
| **Provenance** | The inputs, the rule and the input vintage that produced a figure |
| **Input vintage** | The point in time the underlying data represents |
| **Reproduction** | Recomputing a figure from current data by the same rule |
| **Stale figure** | A figure whose input vintage precedes the current available data |
| **Unstatable figure** | A figure whose inputs do not support an honest value |

---

## 6. Functional Requirements

### Statement

**FR-120** — Every stated figure MUST be accompanied by its input vintage.

**FR-121** — Every stated figure MUST be reproducible from its inputs by a stated rule.

**FR-122** — A figure MUST NOT be stated whose provenance cannot be given.

**FR-123** — Where a figure depends on a derived threshold, the threshold in force MUST
be stated with it.

### Reproduction

**FR-124** — The system MUST provide a means of recomputing all stated figures on
demand, in one action, without preparation.

**FR-125** — Reproduction MUST read current data rather than any recorded value of a
previous computation.

**FR-126** — Reproduction MUST NOT fall back to a remembered constant when an input is
unavailable. It MUST report the figure as unavailable (D-3).

**FR-127** — Reproduction MUST state both the input vintage and the time of
reproduction, so that a stale input is visible even when the reproduction is current.

### Unstatable figures

**FR-128** — Where inputs do not support an honest value, the system MUST present no
figure. It MUST NOT present zero (D-3).

**FR-129** — The absence of a figure MUST be distinguishable from a figure of zero
wherever it appears.

**FR-130** — Where a figure rests on an input known to be unreliable, it MUST be marked
as an estimate at the point of statement, before it is challenged (D-10).

### Staleness

**FR-131** — Where a document or surface states a figure, it MUST direct the reader to
reproduction rather than presenting the stated value as current.

**FR-132** — Where inputs refresh on a schedule independent of the reader, that fact
MUST be stated with any figure derived from them.

### Composition

**FR-133** — A figure composed of others MUST be decomposable into them.

**FR-134** — A composite MUST NOT combine figures of different kinds — recurring with
standing, confirmed with estimated — without the components remaining visible (D-2).

---

## 7. Behavioral Invariants

**INV-060** — A figure MUST NEVER be stated without its input vintage.

**INV-061** — A missing figure MUST NEVER be rendered as zero.

**INV-062** — Reproduction MUST NEVER return a value that current data does not support.

**INV-063** — An estimated figure MUST NEVER appear unlabelled anywhere.

**INV-064** — A composite MUST NEVER hide the kinds of its components.

**INV-065** — The rule producing a figure MUST NEVER differ between the surface the
owner sees and the reproduction used to defend it.

---

## 8. Behavioral Scenarios

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

## 9. Inputs and Observable Outputs

**Inputs (semantic):** the underlying business data with its vintage; the rules producing
each figure; the thresholds in force.

**Outputs (semantic):**
- Each figure with its input vintage, and its threshold where one applies.
- For composites: the components and their kinds.
- For unstatable figures: an explicit unavailability, distinguishable from zero.
- On reproduction: all figures, the input vintage, and the reproduction time.

---

## 10. State / Lifecycle Semantics

Figures hold no state. Provenance is a property of each statement, not of a stored
object. Nothing here is a lifecycle.

---

## 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| Underlying data absent | Report unavailability and name what is missing; produce no figures |
| One input among several absent | Produce the figures that input does not affect; report the rest unavailable |
| Data present but empty | Distinguish "no data" from "data showing nothing"; do not present zero for the former |
| A rule cannot be applied | State that the figure cannot be produced; do not approximate |
| Reproduction disagrees with a previously stated figure | The reproduction governs; the discrepancy is itself reportable |

---

## 12. Edge Cases

| Edge case | Resolution |
|---|---|
| A figure is quoted in a document intended for print | FR-131: the document directs to reproduction; the printed value carries its vintage |
| Inputs refresh between reproduction and the conversation using it | Vintage and reproduction time are both stated (FR-127), so the gap is visible |
| A figure is legitimately zero | Zero is stated as zero; only *unstatable* figures are absent (FR-129) |
| A composite has one unstatable component | The composite is unstatable; a partial composite would misstate the whole |
| A threshold changes and a count moves sharply | The count is not a business change; FR-123 and SCN-127 make the cause visible |

---

## 13. Non-Functional Requirements

**NFR-060 (Reproduction latency)** — Reproduction MUST complete quickly enough to be
performed during a conversation without the participants waiting on it.

**NFR-061 (Determinism)** — The same data and rules MUST produce the same figures.

**NFR-062 (Zero preparation)** — Reproduction MUST require no setup, no arguments and no
prior state beyond the data already present.

**NFR-063 (Coverage)** — Every figure stated in an owner-facing document or surface MUST
be reproducible. A figure that cannot be reproduced MUST be removed from that document
or surface rather than left standing.

---

## 14. Compatibility and External Constraints

- **C-60** — Some inputs refresh on an automated schedule independent of the team, so no
  stated figure remains valid indefinitely. This is the reason this specification exists.
- **C-61** — Some inputs are not carried in the repository and are regenerated locally.
  A figure derived from such an input is not reproducible on a fresh copy, and under
  NFR-063 MUST NOT be stated until it is. *(This currently affects the competitor
  comparison coverage figures.)*
- **C-62** — The three rules stated in `intent.md` §12 are binding: no money on a
  stock-derived signal; the data-entry artefact exclusion; no figure rather than zero.

---

## 15. Acceptance Criteria

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

## 16. Assumptions

**ASM-060** — Reproducing a figure in front of the owner ends the dispute. This is the
intent's central claim about trust, and it is untested.

**ASM-061** — The data available at reproduction is the same data the surface used. If
the surface reads a published snapshot while reproduction reads source data, the two may
diverge without either being wrong.

**ASM-062** — Input vintage is knowable for every input.

**ASM-063** — The team has access to reproduction at the moment of challenge.

---

## 17. Open Questions

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

## 18. Non-Goals

- Trend reporting or figure history.
- Auditing who stated which figure when.
- Reproducing figures produced outside this system.
- Certifying the correctness of the underlying business data.

---

## 19. Traceability Matrix

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
