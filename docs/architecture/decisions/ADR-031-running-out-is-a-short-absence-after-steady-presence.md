---
ID: ADR-031
Title: "Running out" is read from the market's daily catalogues, as a short absence after steady presence
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-25
Parent: [System Design](../system-design.md) §19
Related Specs: F8-S1 (FR-147, FR-148, FR-158, OQ-905); GAP-008e
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, D-18, D-19, D-20, D-21, ADR-008, ADR-014, src/market/presence.py, src/market/concentration.py, src/context/competitor_stockouts.py, configs/store_types.yaml, data/external/snapshots/*/delivery_catalog/]
Updated: 2026-09-25
---

# ADR-031 — "Running out" is read from the market's daily catalogues, as a short absence after steady presence

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

A boost applies only when the market runs out of a product (D-19, D-21). The market is the
three nearby stores at or above the format floor (D-18): Wolt Market, Rami Levy in the
Neighbourhood and Super Alonit Einat. A false signal costs twice. It raises an order, and
through F8-S1 FR-158 it spends the product's only disagreement question (D-20).

Today's stockout classification (`src/market/concentration.py`) cannot be reused. It tells a
stockout from a delisting by how synchronised the drops are across **one chain's 157
branches**. D-18's market is three stores of three chains (F8-S1 OQ-905, GAP-008e).

Measured on 2026-09-25 from the committed delivery-catalogue snapshots, over his products at
those three stores:

| Fact | Value |
|---|---|
| Usable days in the presence series (`load_presence(source_id="delivery_catalog")`) | 42, 2026-08-13 … 2026-09-24 (4 skipped) |
| Listed product-store-days on usable days, and those marked not orderable (`is_online_available` false) | 20,853, of which **5** were marked, on 3 products |
| Product-store pairs | 858 |
| Temporary gaps: absent, then listed again | **300, on 187 products**. By length in usable days: 1: 79, 2: 59, 3: 28, 4: 26, 5: 20, 6: 13, 7: 9, 8 or more: 66 |
| Share of a store's steady listings that vanish on one day | On ordinary days, a few percent: at the 90th percentile, 2.9% at Rami Levy and 3.2% at Super Alonit. At the maximum, 7.5% and 3.8%. Wolt Market: **37.1% on 2026-09-15** (209 of 564), 18.9% on 08-31, 17.3% on 09-01 |

The stores do not mark sold-out items; they drop them. So running out has to be read from
absence. And on 2026-09-15 Wolt Market replaced a third of its range in one day, keeping its
size (661 → 674 listings) while changing what it listed. **A stockout is scattered; a
catalogue change is synchronised within one store.** That is the test this rule can make,
where the chain-level one cannot.

## Decision

1. **A product is running out at a market store** on the latest usable day when all three
   hold:
   - it was listed there on at least **10 of the 14 usable days** before its absence began;
   - it has been absent for at least **2** and at most **7** consecutive usable days, ending
     on the latest usable day;
   - its absence did not begin on one of that store's excluded days (Decision 2).

   A listed item marked not orderable counts as absent that day.
2. **Two kinds of day are excluded, store by store.**
   - **A catalogue change.** On such a day more than **10%** of the store's steady listings
     (those listed on at least 10 of the prior 14 usable days) vanish at once. Absences that
     begin on that day are never read as running out.
   - **A thin collection.** On such a day the store's listed count is below half its own
     median. This matters because `presence.py` judges a day usable across all venues
     together, so one store's failed scrape would otherwise read as every product there
     being absent.
3. **Absences outside 2 to 7 days never boost.**
   - A one-day absence is not counted. 79 of the 300 gaps are one day long, and a one-day gap
     cannot be told from a partial scrape.
   - An absence longer than seven days may be a delisting. Boosting a product the market is
     walking away from is the error `competitor_stockouts.py` warns against.
4. **The market is running out of a product when at least one of its three stores is.** How
   many stores are (one to three), and for how many days, are published as facts, and the
   boost model is given them (ADR-032).
5. **The signal is a capability of its own (ADR-014).** It is unavailable when fewer than 10
   of the last 14 calendar days are usable, or when the latest usable day is more than 2 days
   before the run. F8-S1 FR-148 then applies.
6. **The values are policy, provisional, and published with the signal.** They are 14, 10,
   2, 7, 10% and one half. They are calibrated after the first month in which per-day sales
   exist (F8-S1 OQ-906).

**The rule, replayed over the committed snapshots** (his products, one count per night,
2026-08-29 … 2026-09-24):

| | Products flagged per night | Distinct products |
|---|---|---|
| Without Decision 2 | 10 to 93, and **89 to 93 on each night 09-16 … 09-21**, after Wolt Market's change | — |
| With Decision 2 at 10% | **10 to 40, a median of about 30**. It excludes exactly three store-days: Wolt Market 08-31, 09-01 and 09-15 | 141 |
| With Decision 2 at 15% | The same as at 10% | 141 |
| With Decision 2 at 5% | 7 to 29, median 21. It also excludes six ordinary store-days | 109 |

## Rejected options

### Reuse the chain-synchronisation test (`concentration.py`)
Its null hypothesis is independent drops across many branches of one chain. Its docstring
notes that with three branches, all three dropping on the same day "is unremarkable" when
the per-branch stockout rate is high. Three stores of three chains cannot supply the
population it needs to tell a stockout from a delisting.

### Rely on the availability flag alone
It is the most direct signal, but it was set on 5 of 20,853 listed product-store-days. F8's
boost would almost never apply, while 187 products showed real temporary absences.

### Count every short absence, with no per-store guard
The replay shows the cost. One catalogue change at one store made about 90 of his products
"run out" on each of six nights. Each of those would have raised an order and spent its
product's one disagreement question.

### Use the national Alonit price file
D-18 excludes it from F8's market. It also records listing, not availability (`presence.py`,
rule 2).

## Consequences

**We accept:**
- The first two days of a real stockout are missed.
- A stockout longer than seven days stops counting.
- A real stockout that begins on one of a store's catalogue-change days is missed.
- A change spread over several days, each under 10%, passes the guard. So does the
  aftershock of one: Wolt Market lost 7.8% of its steady listings on 09-16, the day after its
  change.
- A delisting can look like running out for up to seven days. The boost is bounded by D-21's
  25% and by the shelf-life cap.

**We gain:**
- A signal that exists on today's data, recomputable from committed snapshots.
- A catalogue reshuffle cannot pass as a wave of stockouts.

**We will know it was wrong if:**
- Once per-day sales exist, products flagged as running out show no more rise in his sales
  than unflagged ones over the same days (F8-S1 OQ-911).
- The nightly count of flagged products jumps without any store crossing the 10% line.

## Reversibility

Easy. It is one capability with policy values, and nothing is stored. Changing the rule
changes which products are flagged.

## Binds

| F# | How this constrains it |
|---|---|
| F8 | FR-147 and FR-158 fire only on this signal, and FR-148 applies when it is unavailable |
| F9 | Not bound. F9's own decision stays open (D-20) |
