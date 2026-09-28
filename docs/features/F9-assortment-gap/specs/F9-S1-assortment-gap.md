---
ID: F9-S1
Title: Assortment Gap — what the nearby market runs out of that he does not stock
Status: Approved — by the repository owner, 2026-09-28
Owner: smartshelf-architect
Version: 0.1 (2026-09-28)
Parent: [F9 — Assortment Gap](../intent.md)
Related Intents: INT-005
Inputs: [docs/features/F9-assortment-gap/intent.md, docs/product/intent-register.md (D-1, D-3, D-9, D-18, D-22, D-23, D-25), docs/product/open-decisions/F9-assortment-gap.md (Superseded; the record of D-25), F6-S1 (FR-103, FR-106, AC-107, OQ-601, OQ-602, OQ-605), F7-S1, F8-S1 (§3, FR-158), ADR-009, ADR-014, ADR-029, ADR-031, configs/policy.yaml, src/market/running_out.py, src/surface/compose.js, public/data/catalogue.json and dashboard.json (2026-09-28), data/external/snapshots/*/delivery_catalog (2026-08-13 … 2026-09-28)]
Updated: 2026-09-28
---

# F9-S1 — Assortment Gap

> **Approved by the repository owner on 2026-09-28.** It builds D-25. It decides the three
> things D-25 left to it: the window, the "does not stock" boundary and where the entry sits
> among the ten. It adds one that D-25 did not name: a finding must still be sold. Each of the
> four is marked **(decided here)**, and his approval confirmed them.

---

### 1. Purpose

Put in front of the owner, on his daily surface, a product he does not stock that a nearby
store (D-18) has recently run out of and still sells. He records "I'll try it" or "Not for my
store" (D-25).

The finding is an observation, not a forecast. We never see what a competitor sells, only
what it lists and when an item drops out. So the entry says what was seen: which stores ran
out of it, and on how many nights. It carries no ₪ figure (D-25, D-1, D-3).

It runs on data already held: the delivery-catalogue snapshots the nightly keeps adding and
his catalogue. Nothing is simulated (D-23).

### 2. Intent Traceability

| Source | Where it lands |
|---|---|
| INT-005 — «ماذا يبيع السوق ولا أبيعه أنا؟» | FR-165 … FR-177 |
| D-25, decision 1 (what the market ran out of) | FR-165 … FR-168, INV-080, INV-082 |
| D-25, decision 2 (an entry among his ten; "I'll try it" / "Not for my store") | FR-169 … FR-177, INV-081, INV-083 |
| D-23 (no store owner; data held only) | FR-177, SCN-158 |

### 3. Scope

**In scope:** a new engine capability, `assortment_gap`, and its entries; its place on the
daily surface; the owner's two answers.

**Out of scope:**
- Products he stocks. They are F8's (D-19, F8-S1 FR-158); F8-S1 §3 hands F9 only the rest.
- Any price or amount on the entry (D-25).
- Matching one product across pack sizes (OQ-303, OQ-1001).
- Why a product sells, or whether it would sell here. The intent wants that as a
  conversation (*"نفكّر معاً"*), and nothing here models it.
- Ordering the product. Once he stocks it, it is F8's.

### 4. Actors and Triggers

| Actor | Does | When |
|---|---|---|
| The nightly engine run | Publishes `assortment_gap` in `dashboard.json` | Every night, after the delivery-catalogue collection |
| The store owner | Records "I'll try it", "Not for my store" or "Later" on an entry | When it is on his daily surface. Under D-23 there is no store owner today |
| A team account | Sees the entry, cannot record anything (D-22, ADR-029) | Any time |

### 5. Domain Terms

| Term | Meaning |
|---|---|
| **The market** | D-18's stores: the delivery-catalogue stores at or above the format floor, less the client (`market_store_ids`). Today Wolt Market, Rami Levy In The Neighborhood and Super Alonit Einat |
| **Ran out, on a night** | ADR-031's rule, `running_out` in `src/market/running_out.py`, flags the product at one or more market stores for that night. The same rule, market and policy values as F8's `market_running_out` |
| **Recent** **(decided here)** | The usable nights among the last 14 calendar days, ending on the run's night. That is ADR-031's own fortnight: the span its signal must cover (`SIGNAL_LOOKBACK_DAYS`) and the history that makes a listing "steady" (`prior_days: 14`) |
| **Still sold** **(decided here)** | Listed at a market store on at least one of the last `max_absent` usable days (7 today), or running out tonight. ADR-031 stops counting an absence after `max_absent` days, because it is then more likely the store dropped the product. F9 does not point at what the market has stopped selling. *(Clarified 2026-09-28, before any code: "or running out tonight" was missing. A product absent for exactly `max_absent` days is running out tonight but listed on none of the last `max_absent` days, and INV-082 requires it. §9's 138 was measured with the clause.)* |
| **Does not stock** **(decided here)** | Its barcode is not in his catalogue (`catalogue.json`). Every catalogued product is F8's, with or without sales rows (D-19). So F9 and F8 never speak about the same product |
| **Finding** | A product that he does not stock, that ran out on at least one recent night, and that is still sold |

### 6. Functional Requirements

**FR-165** — The engine MUST publish a capability `assortment_gap` whose entries are exactly
the findings for the run's night (§5).

**FR-166** — "Does not stock" MUST be decided by barcode against the catalogue, as the engine
matches everywhere else. A market listing without a barcode is never a finding.

**FR-167** — "Ran out" MUST be ADR-031's rule as `src/market/running_out.py` implements it,
run for each usable night of the recent window, over the same market and the same policy
values F8 reads. F9 MUST NOT carry a definition of its own. Two definitions would decide one
fact twice, and F8 and F9 could then disagree about the same night.

**FR-168** — Each entry MUST publish its evidence:
- `stores_ran_out` — the market stores it ran out at in the window;
- `nights_ran_out` — how many of the window's usable nights flagged it;
- `last_ran_out` — the latest such night;
- `listed_at` — the market stores listing it on the latest usable night, which may be none
  when it is running out tonight;
- `window` — the first and last day of the window, and how many of its days were usable;
- `market_name` — the product's name as the market lists it. He has no name of his own
  for a product he does not stock.

`stores_ran_out`, `nights_ran_out`, `last_ran_out` and `window` are the evidence the surface
requires before the entry is actionable (FR-103, `REQUIRED_EVIDENCE`).

**FR-169** — An entry MUST carry no value: no ₪ amount, no price, no quantity. The capability's
value policy is `none` (D-25, D-1, D-3).

**FR-170** — The entry's `signal_family` MUST be `assortment.market_ran_out`, and its id MUST
derive from the barcode alone (ADR-009), through `entry_id(signal_family, barcode)` with no
variant. An answer recorded against a product then keeps applying on later nights.

*(Corrected 2026-09-28, in Task 6.2, before any code merged. This said the family was
`assortment_gap`, the capability's id. Families are `<area>.<kind>` identities enumerated in
`SIGNAL_FAMILIES` and the artefact schema, and entry ids are `entry_id`'s hash (design §11).
Nothing the owner sees changes.)*

**FR-171 — Placement (decided here).** `assortment_gap` MUST take at most **one** of the
daily surface's unvalued places (FR-106). When it has an actionable entry, it MUST take the
**first** of them. The other unvalued capabilities share the remaining places in
`unvalued_order`, as today. Both the cap and the position are policy
(`configs/policy.yaml`), not code.

*Why:* D-25 says each finding takes a place among his ten. The three unvalued places are
handed out in strict capability order. On 2026-09-28 reconciliation alone had 355 actionable
unvalued entries, so any place in that order would never show an F9 entry. Put first and
uncapped, F9's findings (138 that night) would displace reconciliation for months. One place
shows a finding every day, and reconciliation keeps two of its three on such days.

**FR-172** — Among F9's entries the order MUST be the following. The engine publishes its entries in it, and the surface keeps it (F6-S1 FR-106a):
1. more nights ran out first;
2. then more stores ran out at;
3. then the more recent `last_ran_out`;
4. then the barcode, so the order is deterministic.

**FR-173** — The answers MUST be recorded with owner state's existing outcome statuses, and
no new status is added:
- "I'll try it" is `acted`;
- "Not for my store" is `declined`, with no reason;
- the surface's "Later" is `deferred`, as on every entry.

How long a declined entry stays settled is F6-S1's rule (OQ-605), not F9's. The labels are
this capability's card wording (FR-175).

**FR-174** — `assortment_gap` MUST require `products` (the catalogue) and the market signal.
Without either it is unavailable, with the registry's input reason (ADR-014). When the market
signal is stale it MUST be unavailable with `market_signal_stale`, decided by the same
`is_stale` as `market_running_out`, so the two can never disagree about a night.

**FR-175** — The capability is published before its card is approved, and stays in
`NOT_YET_SHOWN` until the repository owner approves the card, as F8's did (Phase 5 Task 5.0).
The card states:
- the product's market name;
- which stores ran out of it, and on how many of the recent nights;
- whether a market store lists it tonight;
- "I'll try it", "Not for my store" and "Later", in the three languages.

The card shows no other number.

**FR-176** — The entry's figures, nights and stores, are figures under F7-S1. They MUST be
reproducible by the engine's print mode from the committed snapshots and catalogue, and the
entry MUST state its window.

**FR-177** — A team account MUST see the entry with its answers disabled, and nothing it
presses is recorded (D-22, ADR-029). With no store owner (D-23) the entries are still
published and shown.

### 7. Behavioral Invariants

**INV-080** — A product whose barcode is in his catalogue is never an `assortment_gap` entry.

**INV-081** — No `assortment_gap` entry carries a value, a price or a quantity.

**INV-082** — On the run's night, a product that `market_running_out` lists and that is not
in his catalogue is an `assortment_gap` entry with that night as `last_ran_out`. Every entry
whose `last_ran_out` is the run's night is in `market_running_out`'s list.

**INV-083** — The daily surface never shows more than one `assortment_gap` entry.

### 8. Behavioral Scenarios

**SCN-152** — Wolt Market ran out of a product he does not carry on 6 of the last 14 nights,
and lists it again tonight. It is an entry, and it ranks above one flagged on 2 nights.

**SCN-153** — Rami Levy ran out of a product 10 days ago, and it has been absent from all
three stores for the 9 usable days since. It is not a finding: the market has probably
dropped it.

**SCN-154** — A multipack of a product he sells in another size is a finding, because the
barcodes differ. He answers "Not for my store", and F6-S1's rule for `declined` then applies.
The false finding is OQ-303's cost, stated rather than hidden.

**SCN-155** — No delivery catalogue has been usable for three days. `assortment_gap` is
unavailable with `market_signal_stale`, and Today says so (AC-107). It does not show as
"nothing to try".

**SCN-156** — Reconciliation has 355 actionable entries and F9 has 138. The three unvalued
places hold one F9 entry and two reconciliation entries.

**SCN-157** — He records "I'll try it", and a later catalogue import includes the barcode. He
now stocks it, so F9 stops publishing it (INV-080), whatever his answer was. It is F8's from
then on.

**SCN-158** — A team member opens Today. The F9 card is there with its answers disabled.

### 9. Inputs and Observable Outputs

| Input | Source | Absent ⇒ |
|---|---|---|
| The market's listings per night | `data/external/snapshots/*/delivery_catalog`, through `load_presence` | unavailable (the market signal's input reason) |
| His catalogue | `catalogue.json` / the products input | unavailable (`products`) |
| ADR-031's thresholds, the window, the placement | `configs/policy.yaml` | the run fails, as for any missing policy line |

**Output:** `capabilities.assortment_gap` in `dashboard.json`, carrying:
- its status and entries (FR-168 … FR-170);
- its thresholds: the window, `max_absent`, and ADR-031's values;
- counts: findings, stores, usable nights.

**Measured on 2026-09-28**, with the engine's code over the committed snapshots:
- 45 usable days, 2026-08-13 … 2026-09-28; 13 usable nights in the recent window;
- 248 products not in his catalogue ran out on a recent night;
- 110 of those have been absent from every market store for more than 7 usable days;
- **138 are findings**, and 58 of them are running out tonight.

The replay reproduces the 79 products `market_running_out` published that night.

The brief's 132 (D-25) is a different count. It took products listed on 2026-09-28 that ran
out on any of the 45 nights. That leaves out anything running out that night, which is
unlisted by definition, and keeps anything that ran out a month ago. The count here is the
one this spec's definitions produce.

### 10. Failure and Recovery

- The market signal is too thin (fewer than `signal_min_usable` of the last 14 days usable):
  unavailable with the input reason, as `market_running_out`.
- The market signal is stale: unavailable, `market_signal_stale` (FR-174).
- A snapshot day is unusable: `load_presence` drops it, and the window counts only usable
  nights. `window` states how many there were.
- No finding on a night with a usable signal: available, with no entries. That is an
  observation, not a missing input.

### 11. Non-Functional Requirements

**NFR-070** — The same snapshots, catalogue and policy MUST give the same entries in the same
order. No clock is read except the run's date.

**NFR-071** — Replaying the rule for the recent window MUST keep Checkpoint 3's budget: on a
fresh clone, `npm run figures` still completes within 2 minutes.

### 12. Acceptance Criteria

**AC-164** — A run for 2026-09-28 over the committed snapshots and catalogue publishes 138
`assortment_gap` entries. None has a barcode in `catalogue.json` (INV-080).

**AC-165** — `npm run check:signals` covers `assortment_gap` (rule 12):
- withholding the delivery-catalogue snapshots makes it unavailable, and `market_running_out`
  with it;
- withholding the catalogue makes it unavailable, while `market_running_out` stays available.

**AC-166** — No entry has a `value`, and no entry's evidence has an amount or a price
(INV-081).

**AC-167** — A composed Today where reconciliation has three or more actionable entries and
F9 at least one shows exactly one F9 entry, in the first unvalued place, and two
reconciliation entries (FR-171, INV-083).

**AC-168** — "I'll try it" and "Not for my store" write `acted` and `declined` through
`recordOutcome`, and the entry leaves Today. A team account's buttons are disabled
(FR-173, FR-177).

**AC-169** — For the run's night, every product in `market_running_out` that is not in the
catalogue is an F9 entry with that night as `last_ran_out`, and the other way round (INV-082).

**AC-170** — While `assortment_gap` is in `NOT_YET_SHOWN`, no page shows it (FR-175).

**AC-171** — The order of entries follows FR-172 exactly, pinned on a fixture that ties on
each key in turn.

### 13. Open Questions

| ID | Question | Priority |
|---|---|---|
| OQ-1001 | A multipack of a product he sells in another size is a finding (OQ-303). Should there be a third answer, "I already sell it"? D-25 names two, so adding one is the repository owner's decision | P2 |
| OQ-1002 | Should the card show the market's price? D-25 says the entry carries no ₪ figure. A listed price is evidence rather than money at stake, but it is still a ₪ figure on the card, so it is left out until he says otherwise | P2 |
| OQ-1003 | After "I'll try it", nothing checks that he did. SCN-157 is the only trace: the barcode enters his catalogue. Whether F13 should count that is F13's question | P2 |

### 14. Non-Goals

- Explaining why the market runs out of a product, or predicting whether it would sell here.
- Suggesting a quantity. When he stocks it, F8 applies.
- Any store outside D-18's market, or the national price file.
- Products he stocks, however weakly they sell (F8-S1 FR-158).
