---
ID: F6-S1
Title: Daily Action Surface
Status: Approved — passed the Intent → Spec conformance gate (run 2, CONDITIONAL PASS)
Version: 1.1
Parent: [F6 — Daily Action Surface](../intent.md)
Related Intents: INT-NS
Legacy ID: SPEC-006 (in the pre-migration monolithic `specs.md` v1.1)
Answered by: [System Design](../../../architecture/system-design.md) §21
---

> **Identifier note.** The requirement identifiers inside this document (`FR-…`, `INV-…`,
> `NFR-…`, `AC-…`, `SCN-…`, `C-…`, `ASM-…`, `OQ-…`) are **unchanged** from `specs.md` v1.1
> and remain globally unique across the specification layer. They are the ids used by the
> two gate reports, by the System Design's traceability matrix (§21) and by the
> implementation plan. Where a fully-qualified form is wanted, prefix with the spec id:
> `F6-S1.FR-001`. Nothing was renumbered by the documentation migration.

# F6-S1 — Daily Action Surface

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
is **actionable today**. A capability states an entry actionable today when all of the
following hold, and each producing specification MUST expose the flag:

1. the entry's condition is present in the most recent complete ingestion;
2. every piece of evidence its own specification requires is available for it, so the
   owner can verify it without leaving the surface (FR-110);
3. no owner outcome recorded against it still stands (FR-114);
4. it clears any materiality floor its own specification defines. Where a specification
   defines none, no floor applies and the omission is that specification's open question
   (OQ-101, OQ-202), not a licence for the surface to invent one.

An entry that fails any of these is not admitted and is not counted as unshown (FR-101).

**FR-104** — Entries carrying a monetary value MUST be ordered by that value, descending.

**FR-105** — A recurring value and a standing value MUST NOT be compared as if
equivalent, and MUST NOT be summed to produce an ordering key (D-2).

Whether a single monetary ordering is well defined is a **derived** fact, not an
assertion, and MUST be re-derived whenever a capability changes: it holds only while
exactly one value kind is produced across all admitted capabilities. As of version 1.1 it
holds — SPEC-002 produces no monetary figure (FR-023) and SPEC-004 produces none either,
its idle set being ordered by unit cost with no stock-derived amount (FR-069, FR-069a,
D-11) — leaving SPEC-001's recurring per-sale figure as the only monetary value in V1. A
capability that later introduces a standing value re-opens the allocation question
(GAP-002), and FR-106's explicit allocation is the mechanism that answers it.

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
| Questions (SPEC-005) and actions compete for the same attention | The questions sit in their own panel above the action list and take none of its ten places — **OQ-503**, resolved 2026-09-23 (SPEC-005 §17) |
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

**AC-110a** — No admitted entry fails any of FR-103's four conditions, and an entry whose
required evidence is unavailable is absent from the surface rather than shown without it.
*(FR-103, FR-110)*

**AC-110b** — Every entry names the capability that produced it, so a confirmed loss is
distinguishable from a question. *(FR-107, SCN-108)*

> **2026-09-28, the repository owner:** the card's characterisation line («خسارة مؤكدة»,
> «أرقام لا تتطابق», …) satisfies this. It already separates a confirmed loss from a
> question, which is the criterion's purpose; no card also names its capability.
> (F6 validation, AC-110b.)

**AC-110c** — Every entry states an action the owner can physically perform, and carries
on the surface itself the evidence its producing specification requires. *(FR-109,
FR-110, NFR-051)*

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

**OQ-601 — RESOLVED (2026-09-08, re-verified 1.1).** The question asked how recurring and
standing values rank against one another. It is moot **for V1 only, and only because two
capabilities were changed**: SPEC-002 produces no monetary figure (FR-023), and SPEC-004's
idle set carries none either (FR-069a, D-11). Version 1.0 closed this question on the
first change alone and was wrong to — the idle set was a standing monetary value that
nobody had counted. FR-105 now requires the single-kind premise to be re-derived rather
than asserted, so the same error cannot recur silently.

**OQ-602 (P1, reduced from P0) — How many of the ten places are allocated to unvalued
entries, and by what key are they ordered among themselves?**
FR-106 settles that unvalued entries do not compete on money and require an explicit
allocation; it does not fix the number. Design can proceed on the allocation mechanism
while the number is decided from observation of the owner. SPEC-002 supplies gap ratio
as its own ordering key (FR-024); other unvalued capabilities need one under FR-106a.

> **2026-09-29:** the order among the unvalued places is **D-26**. F9 keeps one place (F9-S1
> FR-171), the other kinds take turns one place each, rotating with the nightly's date, and each
> kind keeps its own stated order (FR-106a), which `surface.engine_ordered` publishes. The number
> of places, three, remains provisional.

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
| INT-NS | FR-103 | — | AC-110a |
| INT-NS | FR-107, FR-109, FR-110 | SCN-108 | AC-110b, AC-110c |
| INT-002B | FR-106, INV-054 | — | AC-103 |
| Protected behavior | INV-055, C-54 | — | AC-111 |
| Protected behavior | C-53 | — | AC-112 |
| Protected behavior | C-50, C-52 | SCN-105 | AC-106 |
