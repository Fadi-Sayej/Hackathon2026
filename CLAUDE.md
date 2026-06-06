# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

### AI explanations (`src/lib/ai/`)

`getDefaultExplanationProvider()` returns `mockExplanationProvider` (rule-based text). The `llmExplanationProvider` exists but is permanently disabled until a backend proxy is available (`VITE_LLM_PROXY_URL`). Do not enable it without a proxy.

### Persistence

`src/lib/persistence/persistence.js` delegates to `localStorageAdapter`. The design supports swapping in a Supabase adapter without changing callers (see `docs/TECH_PERSISTENCE_AND_SUPABASE.md`).

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
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Python | Firestore credentials file path |
| `FIREBASE_PROJECT_ID` | Python | Firebase project (`hackathon26-a6ebd`) |
| `KAGGLE_API_TOKEN` | Python | For downloading Israeli supermarket datasets |

---

## Key Constraints

- Competitor price data on the frontend is **mock-only** (`src/data/mockMarketData.js`). Real data requires the OpenIsraeliSupermarkets Kaggle dataset + a connector in `src/external/`.
- All state is **browser localStorage only** — no backend, no database in production.
- No test suite exists; ESLint is the only automated check.
- The app targets Israeli convenience stores; product data and UI may contain Hebrew text.

---

## Data Pipeline Status

### Real data collected

#### Internal — YomYom inventory (REAL, not fake)

`yomyom-inventory.csv` (project root) — real inventory export from YomYom's POS system.
- **7,678 products**, Hebrew names, real prices
- Columns: `קוד פריט` (item code), `ברקוד` (barcode), `תאור פריט` (name), `סוג פריט` (type), `מלאי נוכחי` (current stock), `מחיר קניה` (purchase price), `מחיר מכירה` (selling price), `WOLT` (Wolt price), `שם מחלקה` (department), `יחידת מידה` (unit)
- ~6,902 rows have barcodes — matchable against Kaggle competitor data
- Departments include: מוצרי מכולת (grocery), חטיפים מתוקים (sweet snacks), משקאות (beverages), מוצרי מקרר (refrigerated), חטיפים מלוחים (salty snacks), and ~20 others
- **Not yet imported** into the pipeline — needs `import_yomyom_pos.py` adapted for this schema, or a new importer

> The old fake 121-row `data/internal/raw_pos/yomyom/sample_yomyom_pos.csv` should be replaced by this real file.

#### External — Competitor prices (collected, not yet wired to frontend)

| Source | Script | Output | Status |
|---|---|---|---|
| Wolt (9 venues, 366 SKUs) | `scripts/run_delivery_venue_connector.py` | `data/external/bronze/delivery_catalog/` + `data/external/silver/products/delivery_catalog/` | ✅ Collected |
| Alonit / Dor Alon FTP XML | `scripts/run_alonit_collector.py` | `data/external/bronze/alonit/` + `data/external/silver/alonit_prices/` | ✅ Collected |
| Kaggle: Israeli Supermarkets 2024 | `scripts/download_kaggle_datasets.py` then `scripts/import_kaggle_supermarkets.py` | `data/raw/kaggle/israeli-supermarkets-2024/` → `data/external/silver/products/kaggle_*/` | ⚠️ Script ready, data not yet downloaded |

**Kaggle pipeline detail:**
- `download_kaggle_datasets.py` — downloads from Kaggle API using `KAGGLE_API_TOKEN`. Saves raw CSVs to `data/raw/kaggle/israeli-supermarkets-2024/`. Requires `KAGGLE_API_TOKEN` in `.env`. Run once, re-run with `--force` to refresh.
- `import_kaggle_supermarkets.py` — reads those CSVs, maps to `ExternalProductObservation`, writes bronze + silver Parquet. Supports `dor_alon`, `rami_levy`, `shufersal`. Expects price CSV + store CSV per chain from `src/external/kaggle_supermarket_importer.py`.
- **`data/raw/` is in `.gitignore`** — raw data is never committed. Run the download script after cloning.

**None of this external data is connected to the frontend yet.** The frontend still reads hardcoded mock data from `src/data/mockMarketData.js`.

#### Internal POS pipeline (fake data)

| Source | Script | Output | Status |
|---|---|---|---|
| YomYom POS CSV (fake, seed=42) | `scripts/import_yomyom_pos.py` | `data/internal/silver_pos/*.parquet` + `data/signals/yomyom/` | ✅ Done (fake data) |

Silver tables: `yomyom_products`, `yomyom_sales`, `yomyom_inventory`, `yomyom_margins`.
Business signals: top sellers, low-stock fast-movers, slow movers, high-margin impulse, category summary.

---

### What's next (in priority order)

#### 1. Import real YomYom inventory
**File:** `yomyom-inventory.csv` (project root, 7,678 rows, Hebrew)

- Move to `data/internal/raw_pos/yomyom/yomyom_inventory_real.csv`
- Adapt `import_yomyom_pos.py` (or write a new importer) for this schema — columns are Hebrew, schema differs from the fake CSV
- Column mapping needed: `ברקוד` → barcode, `תאור פריט` → product_name, `מלאי נוכחי` → current_stock, `מחיר קניה` → cost_price, `מחיר מכירה` → selling_price, `שם מחלקה` → category
- Note: stock values can be negative (POS artifact — treat negative as 0 or flag for review)

#### 2. Download and import Kaggle competitor prices
```bash
# Set KAGGLE_API_TOKEN in .env first
python scripts/download_kaggle_datasets.py
python scripts/import_kaggle_supermarkets.py
```
Output lands in `data/external/silver/products/kaggle_dor_alon/`, `kaggle_rami_levy/`, `kaggle_shufersal/`.

#### 3. Barcode match: YomYom ↔ Kaggle
**Output:** `data/matching/barcode_matches.parquet`

Join `yomyom-inventory.csv` barcodes against Kaggle silver barcodes. This produces the competitor price-gap table (e.g. "YomYom sells Coca-Cola at 8₪, Shufersal sells it at 6.90₪").

#### 4. Export real competitor data to frontend
Write `scripts/export_competitor_market_data.py` that reads the barcode match table and outputs `src/data/marketData.js` in the same shape as `mockMarketData.js`. Update `App.jsx` to import it.

#### 5. Build the LLM proxy (enable real AI explanations)
**Files to change:** `src/lib/ai/llmExplanationProvider.js` (set `enabled: true`), `.env` (`VITE_LLM_PROXY_URL`)

Write `src/api/llm_proxy.py` — FastAPI endpoint receiving `buildLLMExplanationPayload` JSON, calls Claude API (`claude-sonnet-4-6`), returns `{ shortExplanation, riskReason, businessImpact, confidenceNote }`.

#### 6. Rebuild RAG corpus from real data
**File:** `scripts/build-rag-corpus.mjs`

Currently reads `loadDemoStoreData()` (hardcoded JS). Should read real silver Parquets once step 1–3 are done.
