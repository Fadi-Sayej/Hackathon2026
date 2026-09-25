---
ID: ADR-031
Title: "Running out" is read from the market's daily catalogues, as a short absence after steady presence
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-25
Parent: [System Design](../system-design.md) §19
Related Specs: F8-S1 (FR-147, FR-148, FR-158, OQ-905); GAP-008e
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, D-18, D-19, D-21, ADR-008, ADR-014, src/market/presence.py, src/market/concentration.py, src/context/competitor_stockouts.py, configs/store_types.yaml, data/external/snapshots/*/delivery_catalog/]
Updated: 2026-09-25
---

# ADR-031 — "Running out" is read from the market's daily catalogues, as a short absence after steady presence

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

A boost applies only when the market runs out of a product (D-19, D-21). The market is the
three nearby stores at or above the format floor (D-18): Wolt Market, Rami Levy in the
Neighbourhood and Super Alonit Einat.

Today's stockout classification (`src/market/concentration.py`) cannot be reused. It tells a
stockout from a delisting by how synchronised the drops are across **one chain's 157
branches**. D-18's market is three stores of three chains, so there is no such population
(F8-S1 OQ-905, GAP-008e).

Measured on 2026-09-25 from the committed delivery-catalogue snapshots, over his products at
those three stores:

| Fact | Value |
|---|---|
| Usable days in the presence series (`load_presence(source_id="delivery_catalog")`) | 42, 2026-08-13 … 2026-09-24 (4 skipped) |
| Listed product-days with `is_online_available` false (listed but not orderable) | **7 of 22,287**, on 3 products |
| Product-store pairs | 858 |
| Temporary gaps: absent, then listed again | **300, on 187 products**. By length in usable days: 1: 79, 2: 59, 3: 28, 4: 26, 5: 20, 6: 13, 7: 9, 8 or more: 66 |
| Pairs absent for their last 3 or more usable days | 383 |

The stores do not mark sold-out items; they drop them. So running out has to be read from
**absence**, and the only question is which absences mean it.

## Decision

1. **A product is running out at a market store** on the latest usable day when both hold:
   - it was listed there on at least **10 of the 14 usable days** before its absence began;
   - it has been absent for at least **2** and at most **7** consecutive usable days, ending on
     the latest usable day.

   A listed item marked not orderable (`is_online_available` false) counts as absent that
   day.
2. **A one-day absence is not counted.** 79 of the 300 gaps are one day long, and a one-day
   gap cannot be told from a partial scrape.
3. **An absence longer than seven days is no longer read as running out.** It may be a
   delisting, and boosting a product the market is walking away from is the error
   `competitor_stockouts.py` warns against. It never boosts.
4. **The market is running out of a product when at least one of its three stores is.** How
   many stores are (one to three), and for how many days, are published as facts, and the
   boost model is given them (ADR-032).
5. **Usable days follow `presence.py`.** A day whose collection failed is not a day of
   absence; the series skips it.
6. **The signal is a capability of its own (ADR-014).** It is unavailable when fewer than 10
   of the last 14 calendar days are usable, or when the latest usable day is more than 2 days
   before the run. F8-S1 FR-148 then applies: suggestions publish, unadjusted, saying why.
7. **The values are policy, provisional, and published with the signal.** They are 14, 10,
   2, 7 and 2, and are calibrated after the first month in which per-day sales exist (F8-S1
   OQ-906).

## Rejected options

### Reuse the chain-synchronisation test (`concentration.py`)
Its null hypothesis is independent drops across many branches of one chain. It needs a
population of branches to call a drop synchronised. Its own docstring says that with three
branches, even all three dropping on the same day "is unremarkable". So on three stores of
three chains it could never tell a stockout from a delisting.

### Rely on the availability flag alone
It would be the most direct signal, but it fired 7 times in 22,287 listed product-days.
F8's boost would almost never apply, while 187 products showed real temporary absences.

### Count every absence, from one day to indefinitely
One-day gaps include scrape noise. Long absences cannot be told from delistings, and 383
pairs are currently in that state. Boosting on either would raise orders for noise, or for
a product the market is dropping.

### Use the national Alonit price file
D-18 excludes it from F8's market. And it records listing, not availability (`presence.py`,
rule 2).

## Consequences

**We accept:**
- The first two days of a real stockout are missed.
- A stockout longer than seven days stops counting.
- A delisting can look like running out for up to seven days. The boost is bounded by D-21's
  25% and by the shelf-life cap.

**We gain:**
- A signal that exists on today's data: 187 products had temporary gaps in 42 days.
- It needs no chain population, and is fully recomputable from committed snapshots.

**We will know it was wrong if:** once per-day sales exist, products flagged as running out
show no more rise in his sales than unflagged ones over the same days. That becomes
measurable then (F8-S1 OQ-911).

## Reversibility

Easy. It is one capability with policy values. Changing the rule changes which products are
flagged, and nothing is stored.

## Binds

| F# | How this constrains it |
|---|---|
| F8 | FR-147 and FR-158 fire only on this signal, and FR-148 applies when it is unavailable |
| F9 | Not bound. F9's own decision stays open (D-20) |
