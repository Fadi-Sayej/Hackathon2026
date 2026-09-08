# SPEC-000 — Intent Register and Specification Index

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Source of intents:** [`intent.md`](../../intent.md)

This file assigns stable identifiers to the intents so every requirement in every
specification can be traced back to one. It defines no behavior of its own.

Specifications are written in English because their audience is a system designer
and a coding agent working in a repository whose code and technical documents are
English. The intent layer stays in Arabic because its audience includes the store
owner.

---

## 1. Intent identifiers

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

## 2. Specification index

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

## 3. Decisions already made by the intent layer

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

## 4. Intents deliberately not specified in this phase

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
