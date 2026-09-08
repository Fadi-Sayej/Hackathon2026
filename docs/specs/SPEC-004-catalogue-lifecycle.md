# SPEC-004 — Catalogue Lifecycle

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Related Intents:** INT-009, INT-NS, INT-PROV

---

## 1. Purpose

Defines how a product in the catalogue is classified as living, dead or idle from sales
evidence; which of those may be withdrawn from the working catalogue without asking the
owner; and how a withdrawn product returns.

---

## 2. Intent Traceability

- **INT-009** — "Clean my catalogue of dead products."
- **INT-NS** — a smaller catalogue is what makes a 10-item surface reachable.
- **INT-PROV** — every count recomputable (SPEC-007).

---

## 3. Scope

### In Scope

- Classifying catalogue entries by sales evidence over an observation window.
- Automatically withdrawing entries that meet a strict condition.
- Returning a withdrawn entry when evidence contradicts the withdrawal.
- Presenting entries that require the owner's judgement, ranked.
- Producing a list the owner can act on in his own system.

### Out of Scope

- Deleting or modifying anything in the owner's point-of-sale system (D-7).
- Deciding whether idle stock should be discounted, returned or written off.
- Determining why a product stopped selling.
- Any pricing signal (SPEC-001, SPEC-003).

---

## 4. Actors and Triggers

| | |
|---|---|
| **Primary actor** | Store owner |
| **Trigger** | Ingestion of a point-of-sale export together with sales history covering the observation window |
| **Precondition** | Sales history covering the window is available; without it no classification may be produced |

---

## 5. Domain Terms

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

## 6. Functional Requirements

### Classification

**FR-060** — The system MUST classify every catalogue entry with a usable product
identifier as living, withdrawable, or idle, using sales evidence over the observation
window.

**FR-061** — The observation window MUST be stated wherever a classification or count is
presented.

**FR-062** — An entry whose recorded stock is negative MUST NOT be classified
withdrawable. It belongs to data hygiene (SPEC-002).

### Automatic withdrawal

**FR-063** — The system MUST withdraw withdrawable entries without requiring an owner
decision.

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

### Idle entries

**FR-069** — Idle entries MUST be presented for the owner's judgement, ranked by the
value of the stock recorded against them.

**FR-070** — For each idle entry the system MUST offer distinguishable outcomes
covering at least: the stock is genuinely present and unsold; the recorded quantity is
wrong; the product is no longer carried.

**FR-071** — The system MUST NOT state which outcome is correct.

### Implausible quantities

**FR-072** — The system MUST identify idle entries whose recorded stock valuation is
implausible against the store's scale and MUST present them as a **question** to the
owner.

**FR-073** — An implausible quantity MUST NOT be asserted as a fact about the owner's
capital or as an accusation of mismanagement (D-10).

### Effect on other capabilities

**FR-074** — Withdrawn entries MUST be excluded from other capabilities' populations,
and every count those capabilities publish MUST reflect the exclusion.

**FR-075** — The system MUST produce, on request, a list of withdrawn entries suitable
for the owner to act on in his own system.

### Honesty about the window

**FR-076** — Where the observation window does not span a full annual cycle, the system
MUST state that seasonal products may be misclassified as dead, and MUST state this
wherever the dead count is presented.

---

## 7. Behavioral Invariants

**INV-030** — An entry with recorded stock above zero MUST NEVER be withdrawn
automatically (D-6).

**INV-031** — Withdrawal MUST NEVER be irreversible.

**INV-032** — A withdrawn entry that records a sale MUST NEVER remain withdrawn.

**INV-033** — Withdrawal MUST NEVER change anything outside this system (D-7).

**INV-034** — The living, withdrawable and idle sets MUST partition the classified
population exactly.

**INV-035** — An implausible quantity MUST NEVER be presented as an established fact.

**INV-036** — No classification may be produced when sales evidence for the window is
absent; absence of evidence MUST NOT be read as absence of sales.

---

## 8. Behavioral Scenarios

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

## 9. Inputs and Observable Outputs

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

## 10. State / Lifecycle Semantics

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

## 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| Sales evidence absent | FR/INV-036 — no classification, nothing withdrawn, capability reported unavailable |
| Sales evidence covers a shorter window than configured | Classify against the actual window and state it (FR-061), with the seasonal caveat (FR-076) |
| Entry has no usable product identifier | Out of the classified population; it is a hygiene record (SPEC-002) |
| Recorded stock absent (not zero) | Not withdrawable; absence is not zero |
| Cost price absent for an idle entry | Rank without a value and show no value — not zero (D-3) |
| Ingestion interrupted | Prior state remains authoritative |

---

## 12. Edge Cases

| Edge case | Resolution |
|---|---|
| Seasonal product, zero stock, out of season | Withdrawn by FR-063, revived on its first sale. The exposure is that a withdrawn product may never be reordered and so never sells — **OQ-401**, the most serious open question here |
| A newly introduced product with no sales yet | Would be withdrawn on the first ingestion. Requires an introduction grace period — **OQ-402** |
| A product both dead and carrying unaccounted value (SPEC-002) | Precedence undefined — **OQ-203** (shared) |
| Owner revives a product that then never sells | Stays living for the window (FR-067); a repeated-revival policy is **OQ-404** |
| Very large withdrawn set on first run | Volume is expected; it is why withdrawal is automatic. Requires that the withdrawn list stay reviewable rather than being presented item by item |
| Idle entry with implausible quantity **and** no cost price | Cannot be valued or ranked; present without value (D-3) |

---

## 13. Non-Functional Requirements

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

## 14. Compatibility and External Constraints

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

## 15. Acceptance Criteria

**AC-060** — No entry with recorded stock above zero is ever withdrawn automatically.
*(INV-030, SCN-062)*

**AC-061** — Every withdrawn entry is listable with its evidence and can be returned to
the working catalogue. *(FR-065, NFR-033)*

**AC-062** — A withdrawn entry that records a sale returns without owner action.
*(FR-066, INV-032, SCN-063)*

**AC-063** — A manually revived entry is not automatically withdrawn again within the
same window. *(FR-067, SCN-064)*

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

## 16. Assumptions

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

## 17. Open Questions

**OQ-401 (P0) — How does a withdrawn seasonal product ever sell again?**
Revival depends on a sale; a withdrawn product is absent from ordering surfaces, so it
may not be reordered, so it may not be stocked, so it may never sell. The revival rule
may be unreachable for exactly the products it is meant to protect. This blocks the
design of withdrawal, because it determines whether withdrawal may affect ordering
surfaces at all.

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

**OQ-406 (P2) — Should the observation window be a product decision or follow the
available evidence?**
The intent names seven months because that is what exists, and expects two years. Whether
the window is fixed or elastic affects FR-061 and FR-076.

---

## 18. Non-Goals

- Deciding the commercial fate of idle stock.
- Explaining why a product stopped selling.
- Forecasting whether a dead product would sell if restocked.
- Managing assortment breadth as a strategy.
- Deleting anything anywhere outside this system.

---

## 19. Traceability Matrix

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
