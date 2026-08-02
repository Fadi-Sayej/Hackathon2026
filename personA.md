# Person A — Data Pipeline & Velocity Engine

> 📋 **Read `PLAN.md` first** — phases, integration gates, go/no-go criteria, and the cut line.
> This file is only your slice of it.

> **You own (nobody else edits):** `scripts/*.py`, `src/internal/`, `src/snapshots/`,
> `src/common/`, `src/external/`, `src/mcp_server/`, `configs/`, `data/`
> **Never touch:** `src/App.jsx`, `src/pages/`, `src/components/`, `src/lib/` (JS),
> `src/api/`, `scripts/*.mjs`

Read first: `CLAUDE.md`, `README.md` (§YomYom POS Readiness), `src/internal/pos_importer.py`,
`src/snapshots/pos_snapshots.py`, `configs/pos_schema_mapping.yaml`

---

## What we are handing YomYom

A deployed web app a store manager opens each morning that says **what to act on today** —
mispriced items, loss-making items, low stock, expiring stock — computed from their own real data,
refreshed from a daily POS export. The pilot measures whether acting on those alerts makes money.

## Your mission

**The biggest hole in the product is that we have no sales velocity.** The POS export is an
inventory snapshot: `units_sold_7d` / `units_sold_30d` are null in all 7,674 rows. As a result
100% of products classify as "Slow moving", `daysUntilStockout` is null for every single product,
and the reorder engine emits 2,742 identical "consider a promo" cards.

You will fix this **without waiting on YomYom for sales data**, by deriving velocity from
day-over-day stock deltas.

---

### A-1 (P0) — Snapshot-delta velocity engine

`src/snapshots/pos_snapshots.py` already computes "an inventory movement proxy derived from stock
deltas". Promote that proxy into real velocity columns.

- New script: `scripts/build_velocity_from_snapshots.py`
- Per barcode, across consecutive dated snapshots: `sold ≈ max(0, prev_stock - curr_stock)`
- **A stock increase is a delivery, not negative sales.** Clamp to 0 and record it separately as a
  `restock_event`, so receipts can be subtracted properly later.

🔴 **The manager sends the CSV irregularly, not daily. Design for that from the start.**

- **Never assume one snapshot = one day.** Always divide by the actual elapsed time:
  `units_per_day = max(0, prev_stock - curr_stock) / days_between(prev, curr)`.
  Assuming daily intervals is the single most likely way this engine produces confidently wrong
  numbers — a 6-day gap read as 1 day overstates velocity by 6×.
- Store the raw delta *and* the interval, not just the derived rate, so a wrong assumption can be
  recomputed later without re-importing.
- **Longer gaps are less accurate, not more.** A 14-day gap hides restocks that happened in
  between — stock can go down, up, and down again, and you only see the endpoints. Factor gap
  length into `velocity_confidence`: a 14-day gap is `low` confidence no matter how many snapshots
  you have.
- Reject snapshots less than ~12h apart as duplicates rather than computing a wild daily rate from
  a two-hour gap. (This is exactly what the 5 existing test snapshots would do.)

- Aggregate into `units_sold_7d`, `units_sold_30d`, `last_sale_date`; write them into
  `data/internal/silver_pos/yomyom_sales.parquet`, replacing the null columns.
- Emit `velocity_confidence` per product: `none` (<2 snapshots), `low` (2–6), `medium` (7–29),
  `high` (30+ days). **Person C renders this in the UI — do not skip it.**
- `units_sold_30d = 0` and `velocity_confidence = 'none'` are **different facts**. A product that
  genuinely didn't sell is not the same as one we have no history for. Never conflate them; the
  whole credibility of the pilot rests on this distinction.

⚠️ The 5 snapshots in `data/internal/snapshots/` are all from 2026-06-06 within ~2 hours. They are
test runs and will produce meaningless velocity. Use them only to prove the code executes.

### A-2 (P0) — Daily snapshot capture

Velocity only exists if a snapshot is captured **every single day** of the pilot.

- Make `npm run data:refresh` idempotent — safe to run twice on the same file.
- Snapshot on every import, keyed by **date**, never overwriting a previous day.
- Write `scripts/pilot_daily.sh`: import → snapshot → velocity → expiry → operational recs →
  `public/data/operational.json`. One command, exit 0/1, human-readable summary at the end.
- Document the exact 30-second routine YomYom staff follow each morning to export and drop the CSV.
  Hand this to Person D for the training material.

### A-0 (P0 — DAY 1) — Chase the two answers you depend on

**Person D owns asking YomYom (task D-0); you own making sure it actually happens.** Two answers
change your work:

1. **Does the POS export sales/transactions?** If yes, A-3 outranks A-1 and the reorder engine
   works immediately. If no, the snapshot proxy is the product.
2. **Will the CSV arrive daily?** If it stays irregular, your interval normalisation (A-1) and the
   `velocity_confidence` bands carry the entire accuracy story.

**Do not wait for either.** A-1 is deliberately designed to work without both answers — build it
against irregular intervals from day one. But ask Person D on day 1 whether the message went out,
and check back until the answers are recorded in `PLAN.md` §7.

### A-3 (P1) — Real sales export adapter

If YomYom *can* provide a transaction export, it beats the proxy. Build the on-ramp now so adopting
it is a config change, not a rewrite: `scripts/inspect_yomyom_pos_file.py` should detect sales
columns and prefer them over the snapshot proxy when present. Always record which source was used.

### A-4 (P1) — Data quality gate

Per import, write `reports/quality/`: rows in/out, null barcodes (currently 307), zero price (223),
zero cost (1,270), negative stock (625), unmatched barcodes. **Fail loudly** if row count drops
>20% versus the previous import — that means a broken export, and silently serving it to a paying
customer is the worst outcome available to us.

### A-5 (P2) — Refresh competitor data

The Kaggle snapshot is from 2024. Re-run the Alonit FTP and Wolt collectors so the price gaps we
show a real customer are current, then re-run `join_yomyom_kaggle.py` and
`export_competitor_market_data.py`. **Stale price claims are worse than no price claims** — if we
tell YomYom they're overpriced versus a 2024 Shufersal price, we lose their trust permanently.

---

## Contract you must not break

Person C consumes your Parquet through `scripts/normalize-datasets.mjs`. **Do not rename these
columns:** `barcode`, `product_name`, `category`, `selling_price`, `cost_price`, `current_stock`,
`units_sold_7d`, `units_sold_30d`, `velocity_confidence`. Additions are fine; renames break the app.

Announce in the team channel the moment `velocity_confidence` first lands — Person C is blocked on
its existence (not its correctness) for the UI states.

## Done when

- `bash scripts/pilot_daily.sh` runs clean on a fresh clone with only a POS CSV as input.
- `yomyom_sales.parquet` has non-null velocity for products that actually moved.
- Two snapshots ≥24h apart produce velocity numbers you can defend out loud to the customer.
