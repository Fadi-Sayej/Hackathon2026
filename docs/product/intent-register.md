---
ID: SPEC-000
Title: Intent Register, Settled Decisions and Feature Index
Status: Approved
Version: 0.1 (content unchanged from `specs.md` v1.1)
Parent: [PRD](PRD.md)
Related Specs: every F#-S# document under `docs/features/`
Owner: smartshelf-pm
Updated: 2026-10-03 (D-30: F12, the planogram, is unlocked for specification)
---

> **Migration note.** This is `SPEC-000` from the pre-migration monolithic `specs.md`,
> moved verbatim. It is the register that binds intents to specifications, and its §3 is
> the settled-decision list (D-1 … D-13) that every layer below it must honour. The
> feature-id column added by the 2026-09-08 documentation migration is in
> [`PRD.md` §3](PRD.md#3-feature-register) — this file's own content was not edited.

# SPEC-000 — Intent Register and Specification Index

**Status:** Draft
**Version:** 0.1 (2026-09-08)
**Source of intents:** [`PRD.md`](PRD.md) and the feature intents

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
| **INT-002** | "Where is my stock disappearing?" — **products whose quantities cannot reconcile**, deliberately carrying no money figure | V1 | SPEC-002 |
| **INT-002B** | "Where is my stock disappearing?" — **data hygiene**, deliberately carrying no money figure | V1 | SPEC-002 |
| **INT-003** | "Are my prices reasonable against my neighbours?" | V1 | SPEC-003 |
| **INT-004** | "What do I order today, and how much?" | V2 | F8-S1 |
| **INT-005** | "What does the market sell that I don't?" | V2 | F9-S1 (Approved 2026-09-28) |
| **INT-006** | "Arrange my shelves so I earn more" | V4 | Not specified — see §4 |
| **INT-007** | "How much do I order so it does not spoil?" | V2 | Not specified — see §4 |
| **INT-008** | "When does each supplier actually deliver?" | V3 | Not specified — see §4 |
| **INT-009** | "Clean my catalogue of dead products" | V1 | SPEC-004 |
| **INT-010** | "Complete my missing data — with minimum disturbance" | V1 | SPEC-005 |
| **INT-NS** | The fixed north star: one morning screen, actions ranked by money, **no more than 10** | V1 | SPEC-006 |
| **INT-PROV** | Every figure must be recomputable on demand; no figure asserted from a stale document | V1 | SPEC-007 |
| **INT-MEAS** | The pilot's decision criterion: after 30 days of V1, how much ₪ recovered — corrected prices, explained stock, cleaned catalogue — measured automatically | V1 | Not specified — see §4 |
| **INT-EXPL** | The promise made to the client: an assistant that explains each decision — one reason beside every recommendation, built only from figures the engine published | V2 (with F8) | Not specified — see §4 |

`INT-MEAS` is stated in `intent.md` §11.1, which describes it as measured automatically by
an existing surface. It is registered here rather than left unnamed, because a capability
the intent layer relies on must be traceable even when it is not newly specified.

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
| **SPEC-003** | Competitor Price Position | Draft — GAP-001 resolved (2026-09-08) |
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
| D-1 | No monetary figure may be attached to a signal derived from a stock quantity — **including our own derivations**. A *unit* cost or price, which is not a quantity, is unaffected | `intent.md` §1, §12 rule 1, §4ب |
| D-2 | A recurring per-sale amount and a standing one-time amount are never summed | `intent.md` §2 |
| D-3 | Where a figure cannot be stated honestly, the surface shows **no figure** — not zero | `intent.md` §12 rule 3 |
| D-4 | A shelf price below ₪0.50, or a cost above twice the price, is a data-entry artefact and not a loss | `intent.md` §12 rule 2 |
| D-5 | The store's own price is never its own benchmark | `intent.md` §3 |
| D-6 | Automatic archiving is restricted to products with zero recorded stock | `intent.md` §4 |
| D-7 | The system never writes to the owner's point-of-sale system | `intent.md` §9.6 |
| D-8 | At most three questions are put to the owner on screen at once | `intent.md` §5 |
| D-9 | The daily surface shows at most 10 actions | `intent.md` preamble |
| D-10 | An uncertain figure is labelled uncertain **before** it is questioned, not after | `intent.md` §2, §4 |
| D-11 | Idle stock carries **no** monetary figure and is ordered by **unit cost**, descending. The aggregate value of idle stock is never stated | `intent.md` §4ب |
| D-12 | The product is **single-store, single-user, single-POS-import**. Multiple stores, user accounts and further point-of-sale integrations are out of scope until one store has proven value. **"Single-user" and "user accounts" are superseded by D-22 (2026-09-25); single store and single POS import stand. More stores, each in its own copy, are D-28 (2026-09-30)** | `intent.md` §9.2 |
| D-13 | Real-time shelf monitoring by fixed sensors or cameras is **permanently excluded**, not deferred | `intent.md` §9.1 |
| D-14 | **No figure put in front of the owner may depend on automatic withdrawal until GAP-009 is closed.** Withdrawal rests on "absent from the monthly reports" meaning "sold nothing" — true of 3,932 of 3,932 withdrawable products, of which exactly one appears in the reports with an observed zero. That is the none-vs-zero conflation rule 13 and D-3 forbid, applied to 51% of the catalogue | GAP-009; decided 2026-09-12 |
| D-15 | **F14 explains order suggestions — the quantities F8 will recommend — not V1's findings.** "The decision" in the promise to the client is the order. V1's findings keep showing their evidence as they do. F14 therefore cannot be specified before F8 exists | GAP-012 decision 1; decided by the repository owner 2026-09-24 |
| D-16 | **The reason sentence is written by a language model once a night, from the suggestion's published facts, and published with it — never at request time.** Three conditions come with it: a paid model account; a monthly spending ceiling with an alert; and a mechanical check, before publishing, that the sentence states no figure its suggestion's facts do not carry (the successor to `factsGuard.js`, tag `v1-attic-2026-09-24`) | GAP-012 decision 2; decided by the repository owner 2026-09-24 |
| D-17 | **F14 has no due date.** It follows F8 in V2, and no date is committed | GAP-012 decision 3; decided by the repository owner 2026-09-24 |
| D-18 | **F8's market is the nearby stores the collector follows (`configs/delivery_targets.yaml`), under the format floor the engine already applies: a store below it is context only and never drives a quantity (F3-S1 C-21, `configs/store_types.yaml`).** Today that leaves three of the eight: Wolt Market, Rami Levy in the Neighbourhood and Super Alonit Einat. They list 410 of the 7,275 products in his catalogue that carry a barcode (2026-09-24; the measurement is under GAP-008). Stores of his format elsewhere in the country, the national Alonit price file among them, are not F8's market | GAP-008 decision 1, as it was put to him: "nearby stores only … 410 products at most"; decided by the repository owner 2026-09-24 |
| D-19 | **His own sales set the quantity; the market only adjusts it, and the reason is shown with it.** When the market (D-18) runs out of a product he sells, its quantity rises by one fixed, stated amount, the same for every product: today 15% (`stockout_demand_lift` in `configs/demand_windows.yaml`, which calls it a starting figure, not a measurement). **That fixed amount is superseded by D-21 (2026-09-25); the rest of D-19 stands.** A product with no sales row gets no quantity (D-3). Where the market (D-18) gives a signal for it, the signal is put to him as a question instead (D-8) | GAP-008 decision 2; decided by the repository owner 2026-09-24 |
| D-21 | **When the market (D-18) runs out of a product, how much its order rises is picked per product by a language model, once a night, and published with the suggestion as the model's estimate — never at request time.** It replaces D-19's one fixed amount; D-19's trigger and the rest of it stand. It needs a paid model account and a monthly spending cap. A pick is accepted only from 0% to 25%: one outside that range gives no rise at all, and the suggestion says the pick was rejected. The pick cannot be recomputed from the evidence, so it is recorded, with the model's reason, and the quantity is replayed from it | Decided by the repository owner 2026-09-25, in F8-S1's review, replacing D-19's fixed amount |
| D-22 | **One store, two roles, and real sign-in.** Sign-in is by Google or by an email link. A *team* account sees everything: the owner's app and the telemetry page. It is read-only in the owner's app, so nothing a team member presses is saved as the owner's decision. An *owner* account sees his app and not the telemetry page. The team is two named people, and the owner's account is added before launch. Roles live on the accounts, never in the documents, and no one's email is recorded here. It supersedes D-12's "single-user" in part: it is still one store and one POS import, and multiple stores stay out of scope | Decided by the repository owner 2026-09-25 (confirmed to this session directly); built by ADR-029 |
| D-20 | **When the market and his own sales disagree about a product, he is asked on screen, his answer is saved, and he is not asked about that product again.** Questions come at most three at a time (D-8). Letting an answer change future quantities automatically is left for later. This settles F8's case only; F9's decision (INT-005, §4) is not taken by it | GAP-008 decision 3; decided by the repository owner 2026-09-24 |
| D-23 | **The pilot with the YomYom store ended on 2026-09-27. The project is finished on the data already held, and nothing is made up to stand in for what a store would send: no daily sales, store facts or owner answers are simulated. What needs a store owner waits for another store and its owner.** The data held, read from `public/data/dashboard.json` generated 2026-09-27: the POS inventory export as of 2026-06-06, the seven monthly sales reports (2026-01 … 2026-07), and the competitor snapshots the nightly collector keeps adding. No daily sales report and no store fact was ever received **D-24 supersedes it in part, the same day: F13 has no success number, so that does not wait. The rest of D-23 stands.** | Decided by the repository owner 2026-09-27, in his words: "we broke up with yomyom owner , but we will carry on finishing the project on the data we have until we get another market with new owner , no mock up" |
| D-24 | **F13 has no success number, and its subscription price will be discussed later.** The pilot is not judged against a ₪ figure it must reach: the measurement shows how much success there is, and no target is set. This supersedes D-23 in one respect only: the success number no longer waits for another store's owner, because there is none. The price stays open, as D-23 left it, and with no number, when a subscription starts is not decided either. The data cadence still waits for another store (D-23). What the measurement may contain is still OQ-801 | Decided by the repository owner 2026-09-27, directly in the session that recorded it, in his words: "we don't really need a success number we just need to measure how much success there is no limit we need to get to, and for the subscription price you can avoid for now i don't think you need it fill it with 'will be discussed later'" |
| D-25 | **F9 points out the products he does not stock that the market (D-18) has run out of, and each one is an entry on his daily surface where he records whether he will try it.** A finding is a product the market lists and he does not stock that ran out at a market store on at least one recent night, by ADR-031's rule, the one F8 uses. On 2026-09-28 that was 132 over the 45 nights held, of the 995 products the market lists that are not in his catalogue. Each takes a place among his ten (D-9), where he records "I'll try it" or "Not for my store". It carries no ₪ figure, because he has no sales of the product to size it with (D-1, D-3). Until a new store's owner signs in (D-23), no one can record an answer: the team's accounts are read-only (D-22). Left to the spec: how many nights count as recent, which of his catalogued but idle products count as not stocked, and where the entry ranks among the ten **D-27 supersedes it in part (2026-09-29): a third answer, and the market's listed price on the card.** | GAP-013, both decisions as they were put to him in the F9 brief: 1 "B — What the market ran out of … 132 over the 45 nights held", 2 "A — An entry on the daily surface … where he records 'I'll try it' or 'Not for my store'"; decided by the repository owner 2026-09-28 ("1b 2a") |
| D-26 | **Today's places for work without a ₪ figure take turns.** F9 keeps its one place (F9-S1 FR-171). The other two go to the other kinds of work in a daily rotation, one place each: stock gaps, competitor prices, idle products and record fixes. That is two kinds a day, each kind two days in four, turning with the date of the nightly data, so every device shows the same Today. A kind gets a second place only on a day no other kind has work. Within a kind the most important comes first, in the order its own spec states (F6-S1 FR-106a): the biggest stock gap ("the biggest first", the same day), the highest premium, the one quantity question and then the highest unit cost, and the record fixes in their own order. It answers OQ-602's question of order; its number of places, three, is unchanged | Decided by the repository owner 2026-09-29: "b", to the option put to him as "Take turns: each kind of work gets a place in rotation", after being told that Today's three places were always F9 and stock gaps, so competitor prices, 1,632 idle products and 1,117 record fixes never reached Today |
| D-27 | **F9's card offers a third answer, "I already sell it", and states what the nearby stores list the product at.** "I already sell it" is for a finding that is another size or pack of something he sells (F9-S1 OQ-1001), kept apart from "Not for my store". The price is each nearby store's delivery-app price, with its sale price when there is one and the day it was listed (OQ-1002). It is evidence of what the market charges, never money at stake: the entry still has no value, and nothing is summed. It supersedes D-25 in two respects only: the card had exactly two answers, and carried no ₪ figure | Decided by the repository owner 2026-09-29: "1 yes yes", to the two questions put to him as "'I already sell it' as a third answer?" and "Show the nearby store's price on the card?" |
| D-28 | **Each store gets its own copy of SmartShelf, with its own data, for privacy, and a new store is set up by configuration, never by changing code.** One copy serves one store: its own site, database, sign-in accounts, committed data and nightly. No store's data, owner state or accounts ever reach another store's copy. What makes a copy a particular store's is one settings file, so setting up a store means filling it in and supplying the store's inputs ([`docs/pilot/next-store.md`](../pilot/next-store.md)). It supersedes D-12 in one respect only: more stores are now in scope, each as its own copy. Within a copy, D-12's single store and single POS import stand | Decided by the repository owner 2026-09-30: "each store gets a copy with its own data for privacy , and yes do all these you said you'll build", choosing between the options "own copy per store" (recommended) and "several stores share one app" |
| D-29 | **While Reorder and Approved orders wait for daily sales reports, each may show an example of itself, inside a clearly marked preview.** "See how this page looks" opens the real page filled from a test shop, built from the order probe's fixture world by `scripts/build_order_example.py`. A banner on every screen of it says it is an example and not the store's data. Nothing in it can be approved, changed, saved, exported or sent, and the engine, the published artefacts, the owner state and the pilot measurement never read it. It supersedes D-23 and CLAUDE.md rule 7 in this one respect only: everywhere else nothing is simulated, and no other page shows an example | Decided by the repository owner 2026-10-03: "a", choosing between "a live example" (recommended), "pictures only" (the approved mockup screenshots) and "leave them as they are" |
| D-30 | **F12 (the planogram) is unlocked for specification now, with the plan waiting for daily sales the way F8 does:** it shows why it is waiting, never an empty or invented plan, until the store's daily sales reports arrive. As the option was put to him, the owner's own inputs (shelf photographs, shelf measurements, his arrangement rules) would not wait for sales. D-13 stands: no fixed cameras or sensors. Not decided here: building it, which follows his approval of the spec and its mockups; a marked example while the plan waits, which needs a decision of its own because D-29 confines examples to the order pages; and whether a first version reads shelves from photographs or takes them by hand, for the spec to propose and the owner to approve (reading a shelf photograph is untested; the PRD's one-day trial was never run) | Decided by the repository owner 2026-10-03: "unlock", answering "should F12 be unlocked for specification now, with the plan waiting for sales the way F8 does?" |

---

### 4. Intents deliberately not specified in this phase

**INT-007, INT-008 (V2/V3) and INT-006 (V4)** are not given specifications here.
INT-004 and INT-005 now are (F8-S1, 2026-09-25; F9-S1, 2026-09-28); their entries below keep
the record of how their decisions were taken. INT-006 was unlocked for specification by D-30
(2026-10-03); its spec is to come.

The reason is not scheduling. Each rests on a product decision that the intent layer
has explicitly left open, and writing requirements now would mean inventing those answers
rather than surfacing them:

- **INT-004** had three open decisions (GAP-008), and the owner took them on 2026-09-24
  as **D-18 … D-20**: the market is the nearby stores of a format comparable to his; his
  own sales set the quantity and the market only adjusts it; a disagreement is asked once,
  saved, and not asked again. On 2026-09-25 he asked for its spec:
  [F8-S1](../features/F8-order-quantity/specs/F8-S1-order-quantity.md), which he approved the same day.
  Its dependencies on F10's shelf-life cap and F4's sales evidence stand. The
  decisions leave the architect one design question, recorded under GAP-008: the "running
  out" signal D-19 needs does not exist yet for the nearby stores (GAP-008e). The brief that
  posed the questions is kept, `Superseded`, as the record:
  [F8 brief](open-decisions/F8-ordering.md).
- **INT-005** depended on what the owner is expected to *do* with a "strong in the
  market, weak here" finding. `intent.md` §6 phrases it as a conversation opener, which
  is not yet a decision the system can record. The repository owner took it on 2026-09-28
  as **D-25**: a finding is a product he does not stock that the market (D-18) has run out
  of, and it is an entry on his daily surface, where he records whether he will try it.
  Products he stocks are F8's (D-19, F8-S1 FR-158). The brief that posed the questions is
  kept, `Superseded`, as the record:
  [F9 brief](open-decisions/F9-assortment-gap.md). He asked for its spec the same day:
  [F9-S1](../features/F9-assortment-gap/specs/F9-S1-assortment-gap.md), which he approved.
- **INT-007** depends on shelf-life data that does not exist until store staff have
  recorded receipts for 30 days.
- **INT-008** depends on three deliveries per supplier being observed; the intent notes
  its timeline is calendar-bound, not engineering-bound.
- **INT-006** depends on three inputs that do not exist yet (shelf photographs with
  dimensions, real demand from V2, the owner's own arrangement rules). Its deferral does
  **not** reopen D-13: when INT-006 is specified, the sensor and fixed-camera approach
  remains excluded permanently, not merely postponed.
  *(2026-10-03: unlocked for specification by **D-30**, with the plan waiting for daily sales
  the way F8 does. The three inputs above are still required; D-13 stands.)*

**INT-MEAS** *(2026-09-28: now specified as F13-S1, approved by the repository owner, with no
success number, D-24; what follows is the record of why it was not.)* It was not specified here for a different reason: `intent.md` §11.1 states it is
already measured by an existing surface, so no new capability is being designed. Two
obligations follow and are recorded rather than assumed:

- Whatever that surface states is a figure, so SPEC-007 governs it in full — provenance,
  reproduction, and no figure rather than zero (FR-120, FR-124, FR-128, C-62).
- Its money component «مخزون مفسّر» ("stock explained") cannot be expressed in money under
  D-1 and SPEC-002 FR-023. What that component may contain instead — a count of products
  counted and closed, rather than an amount — is **OQ-801 (P1)**.

On 2026-09-27 the repository owner answered two of PRD §8's three numbers as **D-24**: there is
no success number, only a measure of how much success there is; and the subscription price
will be discussed later. The third, the data cadence, waits for another store's owner (D-23),
and is the same question as F8-S1 OQ-904. F13-S1 stays `Blocked` on it, on OQ-801 and on its
§14 item 5.

**INT-EXPL** (registered 2026-09-24) had three open decisions, and the owner took them the
same day as **D-15 … D-17**. It explains F8's order suggestions. A language model writes the
sentence once a night, under three conditions. There is no due date. It is still not
specified, but F8's reason no longer holds: F8-S1 was approved on 2026-09-25, and it names the
facts each order suggestion publishes (F8-S1 FR-154). F14's spec now waits only on the owner
asking for it. The sentence adds no figure and no cause that its suggestion's own facts do not
carry (D-1, D-3, D-10, D-16). The brief that posed the questions is kept,
`Superseded`, as the record: [F14 brief](open-decisions/F14-decision-explanations.md).

**The pilot store (D-23, 2026-09-27).** The pilot with the YomYom store has ended. Everything
that waited on the store owner now waits on another store's owner, and nothing is filled in
meanwhile (D-3): F8's daily reports and department facts (F8-S1 OQ-903, OQ-904, OQ-908),
F13's success number, price and data cadence (F13-S1 §14), GAP-009 and GAP-011, and D-22's
owner account. F8 is built and publishes `order_quantity` unavailable, saying what it waits
for. *(D-24, the same day: F13 has no success number, so that one no longer waits.)*

These are tracked as open questions in SPEC-GAPS at P1/P2. They must be specified
before their releases are designed, not before V1 is designed.
