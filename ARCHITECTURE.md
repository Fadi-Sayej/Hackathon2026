# SmartShelf — Architecture

Two pipelines that never import each other. They meet only as **files on disk**,
globbed by mtime. Traced from real imports and file reads on 2026-09-05; anything
not verified reachable is omitted.

## Data flow

```
INTERNAL (POS)                          MARKET (competitors)
yomyom-inventory.csv                    src/external/*_connector.py  (CI, daily 00:00 UTC)
    │                                       │
    ▼ src/internal_pos/pos_importer.py      ▼ data/external/snapshots/  [committed]
    │                                       │  └─ scripts/rehydrate_silver.py ─► silver/
data/internal/silver_pos/*.parquet          │
  products·inventory·margins·sales          ▼ src/signals/competitor_product_signals.py
    │                    │              data/signals/competitor_product_signals/*.parquet
    │                    │                  │
    │      products.parquet ────────────►   ▼ src/matching/product_matching.py
    │                                   data/matching/product_matches.parquet
    ▼ src/recommendations/                  │
      operational_recommendations.py        ▼ src/recommendations/product_recommendations.py
data/recommendations/                   data/recommendations/
  operational_recommendations/*.parquet   product_recommendations/*.parquet
    │                                       │
    └───────────────┬───────────────────────┘
                    ▼  scripts/export_dashboard_data.py   ← globs NEWEST of each, by mtime
            public/data/operational.json                  ← only pipeline output the UI reads (committed)
                    ▼  src/lib/dataAdapters/loadOperationalData.js  (fetch)
            src/App.jsx ──► src/pages/OperationalPage.jsx
                    ▼  src/lib/analytics/actionPriority.js          ← ranks by ₪; money vs data-hygiene

MARKET CONTEXT (decided once, in Python)
src/context/{weather,hebrew,islamic}.py ─► src/context/demand_signals.py
        └─► public/data/market-context.json  [committed]
                ├─► src/recommendations/product_recommendations.py   (applies the multiplier)
                └─► src/lib/dataAdapters/loadMarketContext.js ─► reorderEngine.js (renders only)
```

`scripts/refresh_pipeline.py` (`npm run data:refresh`) is the only thing that runs
both halves in order. Steps are best-effort: one that throws is recorded and the run
continues as `partial`.

## The files that are the product

| File | Job |
|---|---|
| `scripts/refresh_pipeline.py` | Runs both pipelines in dependency order, then the exporter. |
| `scripts/rehydrate_silver.py` | Rebuilds `data/external/silver/` from the committed snapshots so a clone has market data. |
| `src/context/build.py` | Fetches weather + both calendars once per run → `public/data/market-context.json`. |
| `src/snapshots/censored_demand.py` | Corrects demand for months a product was off the shelf, so stockouts stop hiding reorders. |
| `src/internal_pos/pos_importer.py` | POS CSV → the four silver parquet tables. The **live** importer. |
| `src/recommendations/operational_recommendations.py` | Silver POS + expiry → the 5 operational recommendation types. |
| `src/signals/competitor_product_signals.py` | Alonit prices + Wolt catalog → one unified competitor signal table. |
| `src/matching/product_matching.py` | Our products ↔ competitor signals, by barcode then normalized name. |
| `src/recommendations/product_recommendations.py` | Matches → `WATCH_PRODUCT` / `REORDER`. |
| `scripts/export_dashboard_data.py` | Merges both halves into `public/data/operational.json`. |
| `src/lib/analytics/actionPriority.js` | Ranks recommendations by ₪; holds the credibility rules. |

## Filesystem seams — where this breaks silently

1. **Producer ↔ exporter, by glob.** The exporter takes the newest
   `operational_recommendations_*.parquet` and `product_recommendations_*.parquet`
   by mtime, not run id. A missing directory is not an error, which hid the whole
   market half until 2026-09-05. **Now guarded:** the exporter raises
   `EmptyExportError` before writing if either family is empty, so an empty run
   cannot overwrite a good `operational.json`. `--allow-no-competitor` is the
   deliberate POS-only escape hatch.
2. **`data/**` is gitignored; `public/data/operational.json` is committed.** A fresh
   clone has the dashboard JSON and nothing to regenerate it from.
3. **CI commits `data/external/snapshots/` only.** The collector also writes
   `bronze/` and `silver/`, but only `snapshots/` is `git add -f`'d, and the signal
   builder reads `silver/`. Verified on a clean clone: the export came back with 0
   recommendations and exit 0. **Now closed:** `scripts/rehydrate_silver.py` runs
   first in `data:refresh` and rebuilds `silver/` from the committed snapshots —
   the exact inverse of `seal_snapshot.py`, adding no committed bytes. `bronze/` is
   still clone-stale; nothing downstream reads it.
4. **Two unrelated matching artifacts in one directory.** `product_matching.py`
   writes `product_matches.parquet` (feeds recommendations); `join_yomyom_kaggle.py`
   writes `barcode_matches.parquet` (feeds `src/data/marketData.js`). Different
   schemas, neither reads the other.
5. **`normalize:data` overwrites committed frontend data from gitignored input.**
   Without `silver_pos/` it falls back to a ~30-product demo set and would overwrite
   `src/data/demoProducts.js` plus five committed files. Refuses unless
   `-- --allow-demo-fallback`.
6. **Expiry parquets are globbed by two consumers independently**
   (`operational_recommendations.py` and the exporter); a run landing between them
   makes them disagree.

7. **Market context is decided in Python, rendered in JS.** `demandSignals` comes
   from `public/data/market-context.json`; `reorderEngine.js` applies it and must not
   reintroduce a table of its own. The previous in-browser table was keyed in English
   against a Hebrew catalog, so it matched nothing and every multiplier was 1.
8. **`market_context` must run before `product_recommendations`** in
   `refresh_pipeline.py` — the recommender reads the artifact, so the wrong order
   decides today's orders on yesterday's context.

## npm scripts — product path

| Script | Role |
|---|---|
| `data:refresh` | Both pipelines + exporter. **The** command after new POS data or a scrape. |
| `data:dashboard` | Exporter only; leaves the market half wherever it was. |
| `dev` / `build` / `preview` | Vite frontend. |
| `normalize:data` | Regenerates committed `src/data/*.js` from silver POS. See seam 5. |
| `test` / `test:py` | 377 JS tests, 270 Python tests. |

## Tooling — not the product path

`lint`, `discover:alonit-network`, `collect:delivery-venue`, `collect:alonit-signals`,
`check:firebase-live`, `check:firebase`, `preflight`, `data:velocity`, `data:lead-times`,
`check:restocks`, `data:quality`, `pilot:daily`, `data:store-types`, `classify:store-types`,
`audit:store-format`, `data:snapshots`, `test:watch`, `test:pipeline`, `test:e2e`,
`test:all`, `doctor`, `audit:ui`, and `sprint2`/`sprint3`/`sprint4`/`sprint7`
(historical aliases that just re-run `normalize:data` + lint + build).

`src/snapshots/velocity.py` is **not** in the product path despite the name: it is
read only by `check:restocks`, `data:quality` and tests. Nothing in the
recommendation or export chain imports it.
