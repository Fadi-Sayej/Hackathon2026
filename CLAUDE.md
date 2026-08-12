# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Codebase Context
Read this FIRST before exploring the codebase:
- `.ai-codex/lib.md` -- library exports and core logic

## Project Overview

SmartShelf AI is a hackathon project: a smart inventory and shelf management tool for convenience stores (targeting the Israeli market). It has two independent parts:

- **Frontend** — a React/Vite SPA (`src/`, `index.html`, `vite.config.js`)
- **Python data pipeline** — standalone scripts that collect, clean, and store competitor price data and internal POS data (`scripts/`, `src/common/`, `src/external/`, `src/internal/`, `src/mcp_server/`)

The two parts share no runtime coupling. The frontend consumes only `data/` files (Parquet/JSON) and browser localStorage. The Python scripts write those files.

---

## Commands

### Frontend (JavaScript/React)

```bash
npm install          # install deps
npm run dev          # Vite dev server (http://localhost:5173)
npm run build        # production build
npm run lint         # ESLint
npm run preview      # preview the build

# Data pipeline helpers (run normalization, then lint/build)
npm run sprint7      # normalize:data + lint + build

# Publish measured supplier lead times from the receiving ledger (see docs/RECEIVING_LEDGER.md)
npm run data:lead-times
```

### Python data pipeline

```bash
pip install -r requirements.txt

# One-time: create all data/ folders
python scripts/init_storage.py

# Verify storage layer end-to-end
python scripts/smoke_test_storage.py

# Generate a reproducible fake YomYom POS CSV (seed=42)
python scripts/generate_fake_yomyom_pos.py

# Import a POS CSV → silver Parquet + signals
python scripts/import_yomyom_pos.py \
    --input data/internal/raw_pos/yomyom/sample_yomyom_pos.csv

# Collect Alonit competitor prices (FTP, no credentials needed)
python scripts/run_alonit_collector.py
python scripts/run_alonit_signal_pipeline.py

# Collect Wolt/10bis delivery prices to Firestore
python scripts/run_delivery_venue_connector.py

# MCP price-lookup server
python scripts/run_mcp_price_lookup.py
```

---

## Frontend Architecture

### Single-page routing

There is no router library. Navigation is a single `activePage` string in `App.jsx` state; `AppShell` renders the active page component.

Pages: `dashboard`, `products`, `recommendations`, `planogram`, `report`, `orders`, `data-source`.

### Data flow in App.jsx

All analytics run in `useMemo` chains. The order matters:

```
raw products (from connector)
  → enrichedProducts  (competitor price/stock flags injected via analyzeLocalMarket)
  → analyzedProducts  (inventory status, days-until-stockout, margins via analyzeProducts)
  → recommendations   (reorder suggestions + explanation annotations)
  → planogramItems    (shelf slot assignments)
  → affinitySuggestions (cross-merchandising)
  → dashboardStats    (summary counts)
```

`enrichedMarketContext` merges live/static market context with competitor boost maps so downstream engines pick them up without knowing their source.

### Canonical product shape

All engines expect this normalized shape (defined in `src/lib/types.js` and enforced by `src/lib/dataAdapters/validation.js`):

```js
{
  id, name, category,
  currentStock, shelfQuantity, shelfCapacity,
  salesLast7Days, salesLast30Days,
  price, cost,
  expiryDate?,          // ISO string or undefined
  supplier, leadTimeDays,
  returnedUnits, damagedUnits
}
```

Raw data enters through **adapters** in `src/lib/dataAdapters/` (`productAdapter.js`, `inventoryAdapter.js`, `salesAdapter.js`) that tolerate many alias names (see `docs/TECH_DATA_ADAPTERS.md`). Never pass un-adapted data into analytics engines.

### POS connectors (`src/lib/posConnectors/`)

Three connectors exist:
- `createDemoDataConnector()` — loads `src/data/demoProducts.js`
- `createCsvConnector({ file })` — parses an uploaded CSV
- `createComaxConnectorStub()` — returns an error (backend not yet implemented)

Each connector implements `{ connect() → {ok, message}, load() → {products, validationIssues, source} }`.

### Store format filter (`src/lib/analytics/storeFormat.js`)

YomYom is a `gas_convenience` forecourt shop. Comparing it to a hypermarket produces
recommendations the manager instantly recognises as absurd, so every competitor entry
passes a format-affinity gate before any engine sees it:

- **affinity 0.0** → dropped entirely (hypermarket vs. forecourt shop)
- **0.0 < affinity < 0.3** → context only; never the basis of a recommendation
- **affinity ≥ 0.3** → comparable; the price-protection threshold widens as affinity falls

Reference data is `configs/store_types.yaml` (hand-edited, with the 5-format scale and
the affinity matrix). Each branch carries two separate fields: `verified` (who decided
— `manual` is final and no script overwrites it) and `basis` (what the decision rests
on — `branch_known` first-hand vs `chain_format` desk knowledge). Only YomYom, Alonit
and the YomYom Wolt venue are `branch_known`; the rest are reasoned from chain format
and will be wrong for a branch that is unusual for its chain. Machine-inferred
classifications go to `configs/store_types.inferred.yaml` and never override the
hand-written file.
`npm run data:store-types` publishes both to the generated `src/data/storeTypes.js`.
`npm run classify:store-types` infers formats from distinct-SKU counts;
`npm run audit:store-format` is the acceptance check (exits non-zero if any
recommendation is sourced from an affinity-0.0 store).

Today that excludes **Shufersal Deal** (hypermarket, 677 prices) outright and demotes
**Rami Levy** (supermarket, affinity 0.1) to context — 457 of 2,101 recommendations are
competitor-sourced, all from Alonit.

### AI explanations (`src/lib/ai/`)

`getDefaultExplanationProvider()` returns `mockExplanationProvider` (rule-based text) unless `VITE_LLM_PROXY_URL` is set — that variable is the only switch. (`VITE_LLM_EXPLANATIONS_ENABLED` exists in `.env` but nothing in `src/` reads it.)

The async/sync bug that used to block this path is **fixed**: `annotateRecommendationsWithExplanations()` is now `async` with bounded concurrency, and `App.jsx` upgrades the mock batch from a `useEffect` (line ~314). The remaining blocker is billing — the Gemini key in `.env` has no prepayment credits (429) — plus deploying the proxy and pointing `VITE_LLM_PROXY_URL` at it.

#### Cost controls (do not remove these without doing the arithmetic)

Every `/explain` call is billed, and a full batch is ~2,100 recommendations. Four guards keep that from becoming a per-render bill:

1. **Per-pass budget.** `annotateRecommendationsWithExplanations({ maxRemoteExplanations })` sends only the top N rows to the paid provider (default **40**, override with `VITE_LLM_MAX_EXPLANATIONS`). Recommendations arrive pre-sorted by value at stake, so the head of the list is what a manager actually reads; everything below keeps its rule-based text. This is worth ~98% of the savings.
2. **Cheap model by default.** `GEMINI_MODEL` defaults to `gemini-2.5-flash-lite` ($0.10/1M in, $0.40/1M out, thinking off). `gemini-2.5-flash` costs $2.50/1M output **and thinks by default** — thinking tokens bill as output, and the pinned `google-generativeai` 0.8.6 SDK cannot disable them. Use the server-side `GEMINI_MODEL`, not `VITE_GEMINI_MODEL` (a `VITE_` prefix inlines the value into the browser bundle).
3. **Bounded JSON output.** `/explain` requests `response_mime_type: application/json` with `max_output_tokens: 400`.
4. **Cache sized above one pass.** `LLM_CACHE_MAX_ENTRIES` defaults to **3000**. At the old 500 the LRU evicted the head of a pass before the next pass reached it — a ~0% hit rate that re-billed everything.

Order of magnitude with these in place: **$1–5/month per store**, against $200–650 without them.

The proxy itself (`src/api/llm_proxy.py`, Gemini via `/explain` and `/report`) is hardened (B-4): it starts cleanly **even without a key** (503 instead of crashing at import), caches identical payloads, applies an upstream timeout to both endpoints, and reads CORS origins from `LLM_ALLOWED_ORIGINS`. Covered by `tests/test_llm_proxy.py` (9 cases).

### Persistence

`src/lib/persistence/persistence.js` delegates to an adapter chosen at load: **`firestoreAdapter` when the `VITE_FIREBASE_*` config is present, otherwise `localStorageAdapter`** (see `docs/TECH_PERSISTENCE_AND_SUPABASE.md`). The Firestore adapter (B-2) is local-first — reads are served synchronously from a localStorage mirror, writes go through localStorage and mirror to Firestore in the background, and it reconciles both ways (last-write-wins) on load/reconnect. Callers are unchanged. **It is inactive until the Firebase console values are set**, so the default today is still localStorage. The team went with Firestore, not Supabase.

---

## Python Pipeline Architecture

### Common layer (`src/common/`)

| Module | Purpose |
|---|---|
| `paths.py` | Single source of truth for all file paths — import this, never hardcode paths |
| `raw_storage.py` | `save_raw_response()`, `save_raw_file()` — write raw HTTP responses |
| `parquet_writer.py` | `write_bronze_parquet()`, `write_silver_parquet()` |
| `schema.py` | Pydantic models (`ExternalProductObservation`, etc.) |
| `quality.py` | `generate_basic_quality_report()` |

### POS import pipeline (`src/internal/pos_importer.py`)

Steps: load CSV → apply schema mapping (from YAML) → validate rows → write 4 silver Parquet tables → quality report → 6 business signals JSON. Column mapping and signal thresholds live in `configs/pos_schema_mapping.yaml`, not in code.

### External collectors (`src/external/`)

- `alonit_connector.py` — Dor Alon FTP price-transparency XML (public, no auth)
- `delivery_venue_connector.py` — Wolt/delivery platform prices
- `tenbis_connector.py` — 10bis (disabled; requires bearer token)
- `firestore_writer.py` — writes collected data to Firestore
- `mcp_price_adapter.py` — feeds price data into the MCP server

### MCP server (`src/mcp_server/price_server.py`)

Registered in `.mcp.json` as `yomyom-prices`. Exposes barcode/product-name price-lookup tools to Claude using the Model Context Protocol.

---

## Environment Variables

Copy `.env.example` to `.env` before running locally.

| Variable | Used by | Purpose |
|---|---|---|
| `VITE_ENABLE_LIVE_MARKET_CONTEXT` | Frontend | Fetch live weather/holidays/news (default `false`) |
| `VITE_LLM_PROXY_URL` | Frontend | Backend proxy URL for LLM explanations |
| `VITE_FIREBASE_*` | Frontend | Client Firebase web config (B-2). Set these to activate Firestore persistence; unset ⇒ localStorage only |
| `VITE_STORE_ID` | Frontend | Firestore store namespace (default `yomyom-kafr-qasim`) |
| `LLM_ALLOWED_ORIGINS` / `LLM_*` | Python | LLM proxy CORS origins, timeout, and cache settings (B-4) |
| `GEMINI_MODEL` | Python | Gemini model for the proxy (default `gemini-2.5-flash-lite` — see cost controls) |
| `VITE_LLM_MAX_EXPLANATIONS` | Frontend | Max rows upgraded to a paid LLM explanation per pass (default `40`) |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Python | Firestore credentials file path |
| `FIREBASE_PROJECT_ID` | Python | Firebase project (`hackathon26-a6ebd`) |
| `KAGGLE_API_TOKEN` | Python | For downloading Israeli supermarket datasets |

---

## Key Constraints

- Competitor price data on the frontend is **real** — `src/data/marketData.js` is generated from `data/matching/barcode_matches.parquet` (14,406 matched barcodes). `src/data/mockMarketData.js` is now **orphaned**; nothing imports it.
- **The POS export itself still has no sales history** — `units_sold_7d`/`units_sold_30d`/`last_sale_date` are null in all 7,674 rows of `yomyom_sales.parquet`. But sales velocity is no longer uniformly absent: `src/snapshots/velocity.py` reconstructs it from stock deltas between POS snapshots, and it now covers **1,565 of 7,674 products** (`velocity_confidence` `high` for 504, `medium` for 1,061, `none` for the remaining 6,109). Velocity-derived features work for that 1,565-product subset and are suppressed elsewhere — every consumer must check `velocityConfidence`/`hasVelocity` before showing a velocity claim (see `docs/UI_DATA_CONTRACT.md` §4.2), not assume it is present.
- `shelfQuantity` (0), `shelfCapacity` (10), `returnedUnits`/`damagedUnits` (0) are **hardcoded constants** for every product — the planogram runs on these, not real shelf data. `leadTimeDays` and `supplier` are **no longer hardcoded**: they resolve from `data/internal/receiving/supplier_lead_times.json` (built by the receiving ledger, T7 — see `docs/RECEIVING_LEDGER.md`) when that file is present, and fall back to `3` / `"YomYom"` when it is absent, which is still the case for every product today since no supplier has reached the 3-delivery threshold for a measured lead time.
- State defaults to **browser localStorage**, but a **Firestore adapter (B-2) exists behind the persistence interface** and takes over once `VITE_FIREBASE_*` is configured (local-first, with localStorage fallback). No SQL database in production.
- A test suite now exists: **Vitest** (`npm test` — 117 tests incl. persistence reconcile + telemetry) and **pytest** (`npm run test:py` — LLM proxy). ESLint is still the release gate.
- The app targets Israeli convenience stores; product data and UI may contain Hebrew text.
- Use `python3`, not `python` (npm scripts were updated accordingly).

---

## Data Pipeline Status

### Real data collected

#### Internal — YomYom inventory (REAL, not fake)

`yomyom-inventory.csv` (project root) — real inventory export from YomYom's POS system.
- **7,678 products**, Hebrew names, real prices
- Columns: `קוד פריט` (item code), `ברקוד` (barcode), `תאור פריט` (name), `סוג פריט` (type), `מלאי נוכחי` (current stock), `מחיר קניה` (purchase price), `מחיר מכירה` (selling price), `WOLT` (Wolt price), `שם מחלקה` (department), `יחידת מידה` (unit)
- ~6,902 rows have barcodes — matchable against Kaggle competitor data
- Departments include: מוצרי מכולת (grocery), חטיפים מתוקים (sweet snacks), משקאות (beverages), מוצרי מקרר (refrigerated), חטיפים מלוחים (salty snacks), and ~20 others
- ✅ **Imported.** Lives at `data/internal/raw_pos/yomyom/all4shop_Mlai.csv` (7,674 rows) and is the source of all four `data/internal/silver_pos/*.parquet` tables. The fake seed=42 CSV is no longer used.
- Stock is **negative for 625 rows** (POS artifact). `normalize-datasets.mjs` clamps these to 0; 2,797 rows have genuine positive stock.
- The export contains **no sales columns** — see the sales constraint above.

#### External — Competitor prices (collected AND wired to frontend)

| Source | Script | Output | Status |
|---|---|---|---|
| Wolt (9 venues, 366 SKUs) | `scripts/run_delivery_venue_connector.py` | `data/external/bronze/delivery_catalog/` + `data/external/silver/products/delivery_catalog/` | ✅ Collected |
| Alonit / Dor Alon FTP XML | `scripts/run_alonit_collector.py` | `data/external/bronze/alonit/` + `data/external/silver/alonit_prices/` | ✅ Collected |
| Kaggle: Israeli Supermarkets 2024 | `scripts/download_kaggle_datasets.py` then `scripts/import_kaggle_supermarkets.py` | `data/raw/kaggle/israeli-supermarkets-2024/` → `data/external/silver/products/kaggle_*/` | ✅ Imported — 16,547 Dor Alon / 21,849 Rami Levy / 22,759 Shufersal |

**Kaggle pipeline detail:**
- `download_kaggle_datasets.py` — downloads from Kaggle API using `KAGGLE_API_TOKEN`. Saves raw CSVs to `data/raw/kaggle/israeli-supermarkets-2024/`. Requires `KAGGLE_API_TOKEN` in `.env`. Run once, re-run with `--force` to refresh.
- `import_kaggle_supermarkets.py` — reads those CSVs, maps to `ExternalProductObservation`, writes bronze + silver Parquet. Supports `dor_alon`, `rami_levy`, `shufersal`. Expects price CSV + store CSV per chain from `src/external/kaggle_supermarket_importer.py`.
- **`data/raw/` is in `.gitignore`** — raw data is never committed. Run the download script after cloning.

**Kaggle silver is fully wired through to the frontend.** `barcode_matches.parquet` (14,406 matched rows) has been produced and `export_competitor_market_data.py` has been run — `src/data/marketData.js` is a 707 KB generated file of real competitor prices, and `App.jsx` imports it. This is no longer a stub and there is no mock fallback in play.

#### Internal POS pipeline (real data)

| Source | Script | Output | Status |
|---|---|---|---|
| YomYom POS CSV (real, 7,674 rows) | `scripts/import_yomyom_pos.py` | `data/internal/silver_pos/*.parquet` | ✅ Done |

Silver tables: `yomyom_products`, `yomyom_sales`, `yomyom_inventory`, `yomyom_margins` — 7,674 rows each.

⚠️ `yomyom_sales` is **structurally empty** (all velocity columns null) because the source export has no sales history. Consequently `data/signals/` is empty — the five business signals (top sellers, low-stock fast-movers, slow movers, high-margin impulse, category summary) all key off `units_sold_30d` and cannot be generated.

---

### What's next (in priority order)

#### ✅ 1. Import real YomYom inventory — DONE
Imported as `data/internal/raw_pos/yomyom/all4shop_Mlai.csv` → 4 silver Parquet tables, 7,674 rows each.

#### ✅ 2. Download and import Kaggle competitor prices — DONE
Silver Parquets written:
- `data/external/silver/products/kaggle_dor_alon/` — 16,547 products
- `data/external/silver/products/kaggle_rami_levy/` — 21,849 products
- `data/external/silver/products/kaggle_shufersal/` — 22,759 products

#### ✅ 3. Barcode match: YomYom ↔ Kaggle — DONE
`data/matching/barcode_matches.parquet` — 14,406 matched rows with columns `barcode_norm`, `yomyom_product_name`, `yomyom_selling_price`, `yomyom_cost_price`, `kaggle_product_name`, `kaggle_price`, `chain`, `price_gap_ils`.

#### ✅ 4. Export real competitor data to frontend — DONE
`export_competitor_market_data.py` has been run. `src/data/marketData.js` holds real `OUR_STORE` + `COMPETITOR_STORES` snapshots.

#### ✅ 5. Wire real stock into the frontend — DONE
`normalize-datasets.mjs` previously read only `yomyom_products.parquet`, which has **no `current_stock` column** — so every product reached the UI with `currentStock: 0`. It now joins `yomyom_inventory.parquet` on barcode (falling back to product name for the ~300 barcode-less rows). Result: 2,742 products with real stock, 89,119 units total.

#### ✅ 6. Operational dashboard data — DONE
`npm run data:dashboard` generates `public/data/operational.json`. Current output: 2,183 recommendations — 1,147 `CHECK_WOLT_PRICE_GAP`, 625 `CHECK_NEGATIVE_STOCK`, 307 `VERIFY_UNKNOWN_BARCODE`, 104 `CHECK_MARGIN`. **Re-run this after any POS re-import** — it is a build artifact and is not committed.

#### ✅ 7. RAG corpus updated
`scripts/build-rag-corpus.mjs` reads real YomYom silver Parquet, falls back to demo data if Parquet not present.

---

### Still open

#### 🔴 1. No sales data (biggest gap)
The POS export is an inventory snapshot only. Until YomYom provides a sales/transaction export, velocity-based features cannot work. Two options: obtain a real sales export, or reframe recommendations around what does exist — stock levels, margin, and competitor price gaps (the genuinely strong signal, backed by 14,406 barcode matches).

#### 🔴 2. LLM explanations blocked
See the AI explanations section above. The Track-C async fix has landed and the cost controls are in place; what remains is an unfunded Gemini key and an undeployed proxy. `VITE_LLM_PROXY_URL` stays empty until both are resolved, so the app runs on the mock provider.

### Track B (deployment / persistence / telemetry) — status

- ✅ **B-3 pilot telemetry** — read-only dashboard at `/telemetry.html` (second Vite entry), `src/telemetry/`. Alerts shown vs acted-on, acceptance by type, ₪ impact, dismissal-reason breakdown. Verified.
- ✅ **B-6 snapshot durability** — `.gitignore` exception commits `data/internal/snapshots/**` (the only velocity source). See `docs/SNAPSHOT_DURABILITY.md`.
- ✅ **B-5 env hygiene** — `.env.example` geo corrected to Kafr Qasim (32.114/34.972).
- ⏸ **B-2 persistence** — Firestore adapter written; needs Firebase console activation.
- ⏸ **B-1 deploy** — Vercel config committed; live deploy on a teammate's account.

See `nagham.md` for the full per-task status.

#### 🟡 3. Shelf data is synthetic
`shelfQuantity`/`shelfCapacity` are still hardcoded constants, so the planogram is not driven by real shelf measurements. (`leadTimeDays`/`supplier` are no longer in this category — see the Key Constraints bullet above and `docs/RECEIVING_LEDGER.md`.)

#### 🟡 4. Geo/context config points at the wrong country
`.env` has `VITE_HOLIDAY_COUNTRY=AT` (Austria), `VITE_WEATHER_LAT/LON=31.95/35.93` (Amman, Jordan) and `VITE_NEWS_QUERY=Jordan`, but the store is YomYom Kafr Qasim, Israel (32.114/34.972). Currently harmless because `VITE_ENABLE_LIVE_MARKET_CONTEXT=false`, but it must be corrected before enabling live context.
