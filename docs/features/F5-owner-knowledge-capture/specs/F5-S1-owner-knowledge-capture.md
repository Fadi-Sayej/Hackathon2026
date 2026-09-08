---
ID: F5-S1
Title: Owner Knowledge Capture
Status: Approved — passed the Intent → Spec conformance gate (run 2, CONDITIONAL PASS)
Version: 1.1
Parent: [F5 — Owner Knowledge Capture](../intent.md)
Related Intents: INT-010
Legacy ID: SPEC-005 (in the pre-migration monolithic `specs.md` v1.1)
Answered by: [System Design](../../../architecture/system-design.md) §21
---

> **Identifier note.** The requirement identifiers inside this document (`FR-…`, `INV-…`,
> `NFR-…`, `AC-…`, `SCN-…`, `C-…`, `ASM-…`, `OQ-…`) are **unchanged** from `specs.md` v1.1
> and remain globally unique across the specification layer. They are the ids used by the
> two gate reports, by the System Design's traceability matrix (§21) and by the
> implementation plan. Where a fully-qualified form is wanted, prefix with the spec id:
> `F5-S1.FR-001`. Nothing was renumbered by the documentation migration.

# F5-S1 — Owner Knowledge Capture

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

**FR-082a** — A question about a product classified **idle** (SPEC-004) MUST NOT be
presented while it remains idle. It is neither answered nor discarded: it returns to the
answerable population if the product sells again. *(In the pilot this defers 5 of the 17
non-living cost questions, leaving the 12 the intent names.)*

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

**AC-081** — No question is presented about a withdrawn product, and none about an idle
one. *(FR-082, FR-082a, INV-041, SCN-080)*

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
