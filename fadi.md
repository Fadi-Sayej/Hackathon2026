# Fadi — Track A: Data Pipeline & Velocity Engine

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

---

## ✅ Status — A-1, A-2, A-4 are BUILT

| Task | State | Where |
|---|---|---|
| A-1 velocity engine | ✅ done, 22 tests passing | `src/snapshots/velocity.py`, `scripts/build_velocity_from_snapshots.py` |
| A-2 daily routine | ✅ done, runs clean | `scripts/pilot_daily.sh` (`npm run pilot:daily`) |
| A-4 quality gate | ✅ done, blocks bad imports | `scripts/check_import_quality.py` (`npm run data:quality`) |
| A-0 chase Malik | 🟡 answered — sales report confirmed to exist, not yet sent |
| A-3 sales adapter | ✅ **done** — on-ramp built, waiting only on the file |
| A-5 competitor data | ✅ done — rebuilt, dated, de-staled |

**A-5 outcome.** Wolt collector re-ran successfully (285 fresh observations today). The Alonit FTP
collector authenticates but its data channel is blocked here — passive `NLST` times out and active
mode returns `500 Port command invalid`, so it returned 0 observations. **Worth retrying from a
normal network before assuming the code is broken.**

The join and export were rebuilt because they were producing misleading output:

- `observed_at` was **discarded at the join**, so price age was unknowable downstream and could
  never be labelled in the UI. It now flows through as `price_age_days` / `observedAt`.
- The join emitted every barcode × store × date combination (~4.7 rows per barcode, 14,406 total
  from just 3,094 products) and could surface a decade-old price when a current one existed. It now
  keeps the **most recent** observation per (barcode, chain).
- Prices older than a year are **excluded by default** (`--max-age-days`, `--include-stale`).
  16.6% of what we were showing was pre-2025, including observations from 2015.
- Live Wolt scrapes were being **ignored entirely** by the join. They are now a first-class source,
  and a live price beats the static dump for the same brand.
- 🔴 The export wrote `isAvailable: false` for any barcode we simply hadn't checked. We hold
  availability data for 427 barcodes and **every one was observed as available** — we have never
  observed a competitor stockout. That fabricated 1,860 "competitor out of stock" flags, granted
  them a 25% demand boost, and — because `competitorEngine` excludes `isAvailable === false` from
  price comparison — **suppressed the real price gaps**. Now `null` when unobserved.

Net effect: 2,911 rows across 2,023 products, **100% of prices under a year old**, and real
comparisons went from 158 to **2,018** (614 where we are cheapest, 1,404 where we are dearer).

⚠️ Chains with no verified branch (Victory, King Store, Wolt Market — 31 rows) are skipped rather
than given invented coordinates. Add real store metadata to `CHAIN_META` if we want them.

**Current real state:** all 7,674 products report `velocity_confidence: 'none'` with NULL units.
That is correct and honest — the two snapshots we hold both come from the *same* import, so
**no velocity can exist yet**. It stays that way until YomYom sends a genuinely new export.
Everything downstream is built and waiting for that one file.

Run `npm run test:py` before pushing anything in this track.

Guards that are already in place and must not be removed:
- Interval normalisation by actual elapsed days (a 6-day gap read as 1 day = 6x overstatement)
- Restocks clamped to zero, never negative sales
- Snapshots <12h apart rejected as duplicate imports
- **Snapshots from the same import rejected** — re-running the pipeline must not manufacture
  fake "zero sales" history or let confidence grow from re-runs alone
- A run that derives nothing **clears** stale velocity rather than leaving it to age silently

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
  `high` (30+ days). **Anas renders this in the UI — do not skip it.**
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
  Hand this to Malik for the training material.

### A-0 (P0 — DAY 1) — Chase the two answers you depend on

**Malik owns asking YomYom (task D-0); you own making sure it actually happens.** Two answers
change your work:

1. **Does the POS export sales/transactions?** If yes, A-3 outranks A-1 and the reorder engine
   works immediately. If no, the snapshot proxy is the product.
2. **Will the CSV arrive daily?** If it stays irregular, your interval normalisation (A-1) and the
   `velocity_confidence` bands carry the entire accuracy story.

**Do not wait for either.** A-1 is deliberately designed to work without both answers — build it
against irregular intervals from day one. But ask Malik on day 1 whether the message went out,
and check back until the answers are recorded in `PLAN.md` §7.

### A-3 — ✅ DONE (2026-08-08)

Two pieces, both testable without the file:

**`scripts/detect_sales_columns.py`** — run it the moment YomYom sends anything.
Exit 0 = usable sales columns, the importer will pick them up. Exit 2 = sales-like
columns present but unmapped, and it prints the exact YAML to paste (a config change,
not a rewrite — which is what A-3 asked for). Exit 1 = no sales in this file, ask again.
Handles semicolon CSVs and rejects Excel with an instruction.

**A guard against destroying the data on arrival.** `velocity.py` rewrites the whole
sales table, so the first `pilot_daily` run after importing a real sales report would
have replaced measured units with nulls — silently, on the day the data finally showed
up. `has_real_sales()` now detects sales that came from the POS (rows carrying units
without our `velocity_source` stamp) and `build_velocity()` stands down rather than
overwrite them. 13 pytest cases in `tests/test_sales_adapter.py`.

### A-3 (original brief) — Real sales export adapter

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

Anas consumes your Parquet through `scripts/normalize-datasets.mjs`. **Do not rename these
columns:** `barcode`, `product_name`, `category`, `selling_price`, `cost_price`, `current_stock`,
`units_sold_7d`, `units_sold_30d`, `velocity_confidence`. Additions are fine; renames break the app.

Announce in the team channel the moment `velocity_confidence` first lands — Anas is blocked on
its existence (not its correctness) for the UI states.

## Done when

- `bash scripts/pilot_daily.sh` runs clean on a fresh clone with only a POS CSV as input.
- `yomyom_sales.parquet` has non-null velocity for products that actually moved.
- Two snapshots ≥24h apart produce velocity numbers you can defend out loud to the customer.
