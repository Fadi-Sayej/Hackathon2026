---
ID: PILOT-NEXT-STORE
Title: What the next store must send
Status: Ready for review
Owner: smartshelf-pm
Parent: [D-23](../product/intent-register.md#3-decisions-already-made-by-the-intent-layer)
Inputs: [docs/product/intent-register.md (D-14, D-18, D-22, D-23, D-24), docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md (FR-143, FR-144, FR-155, ASM-065), docs/architecture/decisions/ADR-030-own-sales-arrive-as-daily-reports.md, ADR-033-store-facts-are-a-committed-file.md, configs/store_facts.yaml, configs/store_types.yaml, configs/delivery_targets.yaml, configs/pos_schema_mapping.yaml, public/data/dashboard.json and measurement.json (2026-09-29), docs/reviews/F1…F13-validation.md, issue #66]
Updated: 2026-09-30 (the importers' new names, ADR-036)
---

# What the next store must send

The pilot with YomYom ended on 2026-09-27 (D-23). The product was finished on the data it
had, and nothing was simulated to stand in for what a store sends. This page lists what
that data lacked, so the next store can be asked for it on day one. Each row names what
it unlocks and where it goes. How to set the store's copy up, step by step, is
[`docs/operations/new-store.md`](../operations/new-store.md); `npm run check:store` checks each row.

Nothing on this list may be simulated while it is missing (D-23).

## 1. Before the first night: the team sets up

| What | Unlocks | Where it goes |
|---|---|---|
| The store's location and format | The nearby market that F3's prices, F8's boost and F9's findings read (D-18) | The store's own entry in `configs/store_types.yaml` (`role: client`, its format), and the nearby delivery venues in `configs/delivery_targets.yaml`. YomYom's venues were those within about 5 km |
| A format for each nearby store | Which prices may set a reference. An unclassified store only ever counts as context: 57 AM-PM shops sat unused until 2026-09-29 (#250) | `configs/store_types.yaml`, `verified: manual`. Ask; never guess a format |
| The owner's sign-in | Only the owner account records decisions. Team accounts see everything read-only (D-22, ADR-029) | The edge gate's accounts |

## 2. From the store's POS

| What | How often | Unlocks | Where it goes |
|---|---|---|---|
| **The inventory export** (prices, cost, stock) | At the start, then whenever it changes | F1's price checks, F2's reconciliation, F4's catalogue, F5's questions. YomYom's only export is dated **2026-06-06**, and every finding still describes that day | `scripts/import_pos.py`, which reads `configs/store.yaml`'s `pos.export`. It was written for YomYom's export; a different POS's column names go in `configs/pos_schema_mapping.yaml`, and `scripts/inspect_pos_file.py` checks a file before it is imported |
| **Monthly sales reports** | Monthly | F2's reconciliation window, F4's idle products, the money at stake on F5's questions. YomYom sent seven, 2026-01 … 2026-07 | `data/internal/raw_pos/yomyom/sales/`, read by `scripts/import_sales.py` |
| **Daily sales reports, with the deliveries column** | At least weekly | F8's order quantities. F8 needs 21 report days in the last 28, with one in each week, and the latest no more than 7 days old (F8-S1 FR-144). A monthly report never counts, because it is never divided into days (FR-143). YomYom sent none, so `order_quantity` stays `unavailable (no_daily_sales)` | `data/internal/raw_pos/yomyom/sales_daily/` (ADR-030), read by `src/internal_pos/sales_daily_importer.py` |

## 3. From the owner, in their own words

| What | Unlocks | Where it goes |
|---|---|---|
| **For each department: the days it is ordered, and how many days it keeps** | F8's quantities. A department without both facts gets no quantity, and F8 says which fact is missing (FR-155) | `configs/store_facts.yaml`, recorded by the team with the date it was said (ADR-033). No department is listed today |
| **GAP-009:** name twenty products missing from a monthly report, and confirm they sold nothing | Whether F4 may ever show the owner "no longer sold" (D-14). The same question for the daily reports is F8's ASM-065 | #66; the gaps register |
| **GAP-011:** is the ceiling the engine derives (18% at YomYom) the owner's own pricing policy? | F1 keeps everything under the ceiling silent. A stated number replaces the derived one, which stays published beside it | `policy.owner_declared_ceiling_pct`; #66 |
| **Time for three questions a day** | F5 asks for costs from the owner's invoices, three at a time. At YomYom none were answered, so nothing F5 exists to change ever changed | The app |

## 4. What the pilot measured, for comparison

Read from `public/data/measurement.json` (2026-09-29): 4 devices opened the app, the last on
2026-09-24. There was **1 decision** in the whole pilot, a "Later" on a price card on
2026-09-17, and 0 marked done. F13 has no target to reach (D-24), so the next store's
figures are read against these, not against a threshold.

## Still open, whatever the store sends

- The subscription price: to be discussed later (D-24).
