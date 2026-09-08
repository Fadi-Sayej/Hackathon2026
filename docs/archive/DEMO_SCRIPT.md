> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# SmartShelf AI — Demo Script

A 5-minute walkthrough that tells one story: *the store owner hands us a POS export and
records expiry dates at receiving; the system surfaces real risks, price gaps, and
actions — without changing the POS.*

## 0. Before the demo (once)

```bash
bash setup.sh                              # deps + browsers + folders
npm run data:refresh                       # build all dashboard inputs from real POS
npm run dev                                # http://localhost:5173
```

## 1. The hook (30s)

> "This is YomYom, a real market in Kafr Qasim. They gave us one file — their POS export,
> `all4shop_Mlai.csv`, 7,674 products. No integration, no API. Watch what we get out of it."

## 2. Operational Risks page (2 min) — the core

Open **Operational Risks**. Talk through the metric cards (all from real data):

- **1,147 WOLT price gaps** — shelf price vs the store's own WOLT delivery price differs >5%.
- **625 negative stock** — POS data the owner must verify.
- **104 margin risks** — items sold at/below cost.
- **307 missing barcodes** — can't be scanned, matched, or tracked.

> "Every one of these is a concrete action, not a chart. Filter by type —"
Click a type filter (e.g. *WOLT price gap*) and show top items with the exact numbers.

Point at the **Data sources** strip:
> "This is honest about what's real. POS: complete. Wolt + Alonit: complete. Kaggle
> competitor prices: still scraping. The dashboard never pretends data is live when it isn't."

## 3. Expiry Tracking page (1.5 min) — the human-in-the-loop

Open **Expiry Tracking**.

> "The POS has no expiry dates. So at receiving, the worker scans one barcode and a date —
> that's the entire ask."

- Type a barcode + pick a date → **Add to queue** → **Download CSV**.
- Show the two commands that ingest it:
  ```bash
  python scripts/record_expiry_scan.py --input-csv <downloaded.csv>
  npm run data:refresh
  ```
- Refresh: the item appears in the buckets (Expired / 0–7 / 8–14 / 15–30 days).

> "Note the wording: this is *expiry risk*, not a batch count. We use current stock as the
> estimate — honest about its limits."

## 4. It updates as the data grows (45s)

> "Competitor scraping is still running. The moment those signals land, competitor
> recommendations appear in the same view — `npm run data:refresh`, nothing else changes.
> And every new POS export is snapshotted, so we compare exports over time —"

```bash
npm run data:snapshots        # added/removed products, price moves, stock movement proxy
```

## 5. Close (15s)

> "One file in. Real risks, price gaps, expiry alerts, and prioritized actions out —
> with one command: `npm run data:refresh`. No POS replacement, no lock-in."

## One-command sanity check before you present

```bash
npm run test:pipeline         # 6/6 PASS expected
npm run build                 # frontend compiles
```
