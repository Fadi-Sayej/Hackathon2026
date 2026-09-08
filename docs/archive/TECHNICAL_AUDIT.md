> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# SmartShelf AI — Deep Technical Audit

*Read and verified June 2026. All claims have been traced to source code.*

---

## 1. RUNNABLE ENTRY POINTS

### npm scripts (`package.json`)

| Command | What it does | Status |
|---|---|---|
| `npm run dev` | Vite dev server at `http://localhost:5173`. Loads React SPA. | **Works standalone** — demo data is hardcoded JS, no server needed |
| `npm run build` | Vite production build | **Works standalone** |
| `npm run lint` | ESLint only | **Works standalone** |
| `npm run preview` | Serves the production build | **Needs `npm run build` first** |
| `npm run sprint7` | `normalize:data && lint && build` | **Runs but the normalize step falls back to hardcoded data** |

**`normalize-datasets.mjs` (called by sprint7):** Scans `data/raw/` recursively for `.csv` / `.json` files. Currently `data/raw/` contains only `.gitkeep` files. The `discoverDataFiles()` function explicitly skips `.gitkeep`, finds nothing, and calls `buildFallbackSource()` which is a hardcoded 30-product retail store dataset embedded in the script itself (lines 494–569). The result is written to `src/data/demoProducts.js` (currently 28 products from this fallback). Running `npm run sprint7` regenerates `demoProducts.js` from that same hardcoded fallback, not from any real data.

---

### Python scripts

#### `init_storage.py`
```
python scripts/init_storage.py
```
Creates these folders (all idempotent, adds `.gitkeep`): `data/internal/raw_pos/yomyom/`, `data/internal/silver_pos/`, `data/external/raw/`, `data/external/bronze/`, `data/external/silver/`, `data/matching/`, `data/signals/`, `data/recommendations/`, `data/quality/`, `data/logs/`. **Status: Works standalone, no prerequisites.**

#### `smoke_test_storage.py`
```
python scripts/smoke_test_storage.py
```
Simulates a full collector run with hardcoded fake data. Writes to `data/external/raw/smoke_test/`, `data/external/bronze/smoke_test_*.parquet`, `data/external/silver/products/smoke_test/`, and `data/quality/smoke_test_*.json`. **Status: Works standalone — no network calls, no credentials.**

#### `generate_fake_yomyom_pos.py`
```
python scripts/generate_fake_yomyom_pos.py
```
Generates 134 rows (CATALOG + DUPLICATES, random seed 42) in English with these columns: `barcode`, `product_name`, `category`, `brand`, `supplier`, `selling_price`, `cost_price`, `current_stock`, `units_sold_7d`, `units_sold_30d`, `sales_amount_30d`, `gross_profit_30d`, `margin_pct`, `last_sale_date`, `last_purchase_date`. Writes to `data/internal/raw_pos/yomyom/sample_yomyom_pos.csv`. **Status: Works standalone.**

#### `import_yomyom_pos.py`
```
python scripts/import_yomyom_pos.py --input data/internal/raw_pos/yomyom/sample_yomyom_pos.csv
```
Runs `src/internal/pos_importer.py` which does: load CSV → apply schema mapping (`configs/pos_schema_mapping.yaml`) → validate → write 4 silver Parquets (`yomyom_products.parquet`, `yomyom_sales.parquet`, `yomyom_inventory.parquet`, `yomyom_margins.parquet` in `data/internal/silver_pos/`) → quality report → 6 business signals JSON in `data/signals/yomyom/`. **Status: Works with the fake CSV. Fails with real `yomyom-inventory.csv` — see Section 2.**

#### `download_kaggle_datasets.py`
```
python scripts/download_kaggle_datasets.py
```
Downloads the dataset `erlichsefi/israeli-supermarkets-2024` from Kaggle API. Requires `KAGGLE_API_TOKEN` in `.env`. Saves extracted files to `data/raw/kaggle/israeli-supermarkets-2024/`. Uses `httpx` directly (no kaggle CLI needed). **Status: Needs data — `data/raw/kaggle/` currently has only `.gitkeep`. Will fail without `KAGGLE_API_TOKEN`.**

#### `import_kaggle_supermarkets.py`
```
python scripts/import_kaggle_supermarkets.py
```
Reads from `data/raw/kaggle/israeli-supermarkets-2024/` — specifically files `price_full_file_dor_alon.csv`, `price_full_file_rami_levy.csv`, `price_full_file_shufersal.csv` and corresponding `store_file_*.csv`. Maps to `ExternalProductObservation`, writes bronze + silver Parquet to `data/external/silver/products/kaggle_dor_alon/`, `kaggle_rami_levy/`, `kaggle_shufersal/`. **Status: Broken — input data does not exist on disk. `data/raw/kaggle/` is empty.**

#### `run_alonit_collector.py`
```
python scripts/run_alonit_collector.py
```
Hits the Israeli government FTP price-transparency feed (`https://url.retail.publishedprices.co.il/`) for Dor Alon branches in Kafr Qasim and Einat. No credentials needed. Downloads `Stores.xml.gz`, `PriceFull.xml.gz`, `PromoFull.xml.gz`. Writes bronze parquet + silver parquet to `data/external/silver/alonit_prices/`. **Status: Works standalone — no auth needed. Data already collected (silver exists at `data/external/silver/alonit_prices/alonit/`).**

#### `run_alonit_signal_pipeline.py`
```
python scripts/run_alonit_signal_pipeline.py
```
Runs a multi-phase pipeline: network discovery (Playwright), delivery venue catalog collection (Wolt), and the Alonit FTP collector. Much heavier than `run_alonit_collector.py` alone. Requires Playwright browsers installed. **Status: Needs Playwright — more complex, used for discovery.**

#### `run_delivery_venue_connector.py`
```
python scripts/run_delivery_venue_connector.py
```
Scrapes Wolt venue catalogs using Playwright. Default target: `https://wolt.com/en/isr/petah-tikva/venue/super-alonit-kibbutz-einat`. Writes silver Parquet to `data/external/silver/products/delivery_catalog/`. **Status: Needs Playwright. Data already collected (silver exists at `data/external/silver/products/delivery_catalog/2026/05/`).**

#### `run_delivery_to_firestore.py`
```
python scripts/run_delivery_to_firestore.py --dry-run
```
Reads `configs/delivery_targets.yaml` (9 Wolt venues: YomYom + 8 competitors). Runs `run_delivery_venue_collection()` for each, then calls `firestore_writer.write_target_to_firestore()` for non-dry-run. **Requires Firestore credentials** (`FIREBASE_SERVICE_ACCOUNT_PATH` or `FIREBASE_SERVICE_ACCOUNT_JSON`) unless `--dry-run` is passed. **Status: Needs Playwright + Firestore credentials for full run. Dry-run works without Firestore.**

#### `run_mcp_price_lookup.py`
```
python scripts/run_mcp_price_lookup.py --products "7290000123456"
```
Queries `data/external/silver/alonit_prices/` Parquet files via `mcp_price_adapter.py`. Uses barcode exact match, name exact match, substring match, or fuzzy (difflib ≥ 0.72) matching. Returns a coverage report + matched observations. **Status: Works standalone — no MCP server needed. Reads Alonit silver data that already exists.**

#### `build-rag-corpus.mjs`
Not in `package.json` scripts — must be run directly:
```
node scripts/build-rag-corpus.mjs
```
**Data source: hardcoded JS — calls `loadDemoStoreData()` which reads `src/data/demoProducts.js`** (the 28-product fallback file). Also reads `src/data/marketContext.js` (a hardcoded `{ currentDate: '2026-05-15', weather: 'hot', ... }` object). Writes JSONL files to `data/processed/rag/` (these already exist). **Not connected to any LLM, embedding model, or vector database** — the README inside `data/processed/rag/` explicitly says "This folder is RAG-ready only. It does not include a vector database, embeddings, or LLM calls." Has no consumer — nothing reads `data/processed/rag/`.

#### `normalize-datasets.mjs`
```
npm run normalize:data   # or: node scripts/normalize-datasets.mjs
```
Scans `data/raw/` for CSV/JSON, scores and picks the best source, normalizes to the canonical product shape, and writes `src/data/demoProducts.js`. Currently always falls back to the 30-product hardcoded inline dataset because `data/raw/` is empty. **It would also pick up the Kaggle CSVs if they were placed in `data/raw/` — but the Kaggle price-transparency format (price per store per product) is not the right shape for this normalizer (which expects product-level inventory/sales).**

#### `discover-alonit-network.mjs`
```
npm run discover:alonit-network
```
Uses Playwright to load three default target URLs (easy.co.il Alonit listing, easy.co.il Alonit Einat page, Wolt Alonit Einat venue). Intercepts XHR/fetch responses, scores them for product-like JSON fields, saves results to `data/debug/network/<source_id>/`. **Status: Needs Playwright. Pure discovery/debug tool — no output consumed by anything else.**

---

### MCP Server (`src/mcp_server/price_server.py`)

Registered in `.mcp.json` as `yomyom-prices`. Exposes 3 tools:
- `lookup_prices(products, chains)` — full observations + coverage report
- `get_price_summary(products, chains)` — one row per product, best price
- `explain_coverage(products, chains)` — plain-text coverage narrative

All 3 delegate to `src/external/mcp_price_adapter.py → run_mcp_price_lookup()`, which reads `data/external/silver/alonit_prices/` Parquets using `polars`. Requires `mcp>=1.0` Python package. If not installed, the tools still can't be registered but the adapter functions work. **The server is for Claude/AI assistant use only — the frontend React app does not call it.**

---

## 2. THE REAL DATA THAT EXISTS

### `yomyom-inventory.csv` (project root)

**What it is:** Real YomYom POS inventory export, 7,674 data rows + 1 header = 7,675 total.

**Exact column headers (with trailing spaces — this matters):**

| Raw header | Meaning | Notes |
|---|---|---|
| `קוד פריט ` | Item code | Internal sequential ID (2, 5, 6, …) |
| `ברקוד ` | Barcode | 307 rows empty or `"0"` |
| `תאור פריט ` | Product description/name | **Hebrew, not in YAML candidates** |
| `סוג פריט ` | Item type | Always `"רגיל"` (regular) in sample |
| `מלאי נוכחי ` | Current stock | 627 rows are negative |
| `מחיר קניה ` | Purchase/cost price | Matches YAML `מחיר קניה` |
| `מחיר מכירה ` | Selling price | Matches YAML `מחיר מכירה` |
| `WOLT` | Wolt delivery price | Not in YAML at all |
| `שם מחלקה ` | Department name | Appears **twice** (duplicate column), **not in YAML** |
| `יחידת מידה ` | Unit of measure | Not in YAML |
| `` (blank) | Trailing empty column | Artifact of Excel export |

**Is it imported anywhere?** No. Not referenced in any `.py`, `.js`, or `.jsx` file anywhere in the repo.

**Schema mismatch with `pos_schema_mapping.yaml`:** The importer's column resolution would succeed for `ברקוד`, `מחיר קניה`, `מחיר מכירה` (all strip to match YAML candidates). It would **fail to match** these 3 fields:

| Field | Real CSV column | YAML candidates (none match) |
|---|---|---|
| `product_name` (required) | `תאור פריט` | `שם מוצר`, `שם פריט`, `description`, `item_name` |
| `category` | `שם מחלקה` | `קטגוריה`, `מחלקה`, `קבוצה`, `department` |
| `current_stock` | `מלאי נוכחי` | `מלאי`, `כמות במלאי`, `stock`, ... |

Since `product_name` is `required: true`, the importer would call `return {"status": "error", "reason": "missing_required_columns"}` at `pos_importer.py:824` — before processing a single row.

**Additional issues:**
- 627 rows have negative `מלאי נוכחי`. YAML rule `non_negative_fields: [current_stock]` would reject these rows.
- No sales data columns (`units_sold_7d`, `units_sold_30d`, `sales_amount_30d`, `gross_profit_30d`, `margin_pct`) — these would all be null, making most signals empty.
- Duplicate `שם מחלקה` column — Python `csv.DictReader` will likely rename the second occurrence.

---

### `data/external/silver/products/delivery_catalog/`

Wolt catalog data collected at `data/external/silver/products/delivery_catalog/2026/05/`. Fields are `ExternalProductObservation` fields from `src/common/schema.py`:

`source_id`, `observed_at`, `barcode` (often None), `sku`, `product_name`, `brand`, `category`, `subcategory`, `unit`, `country_of_origin`, `price`, `sale_price`, `currency`, `price_per_unit`, `store_name`, `store_id`, `store_chain`, `city`, `raw_file_path`, `source_type` (= `"delivery_catalog"`), `branch_confidence`, `rank_in_category`, `most_ordered`, `source_product_url`, `appears_in_price_file`, `is_online_available`, `is_in_catalog`.

**Is this read by anything?** No. Not imported by any frontend file or any export script. It exists in Parquet only.

---

### `data/external/silver/alonit_prices/`

Alonit / Dor Alon FTP price-transparency data at `data/external/silver/alonit_prices/alonit/` (2025 and 2026 subdirectories present).

**Is it read by anything?** Only by `src/external/mcp_price_adapter.py` which is called by `run_mcp_price_lookup.py` and `src/mcp_server/price_server.py`. **Not connected to the frontend in any way.** `mcp_price_adapter.py` is not called by any export script or frontend code.

---

### `data/internal/silver_pos/`

Four Parquet tables exist: `yomyom_products.parquet`, `yomyom_sales.parquet`, `yomyom_inventory.parquet`, `yomyom_margins.parquet`. These were generated from the **fake 134-row CSV** (the `generate_fake_yomyom_pos.py` output), not from the real `yomyom-inventory.csv`.

**Is this read by anything?** No. No frontend code, no export script, no `normalize-datasets.mjs` reads these files. They are completely isolated.

---

### `data/signals/yomyom/pos_signals_latest.json`

Contains 6 signals: `top_sellers`, `top_profit_products`, `low_stock_fast_movers`, `slow_movers`, `high_margin_impulse_candidates`, `category_sales_summary`. Generated from the fake POS import.

**Is this read by anything?** No. No frontend code reads this file. It has no consumer.

---

## 3. THE FRONTEND — REAL vs MOCKED

### Competitor intelligence

**Source:** `src/data/mockMarketData.js`, imported at `App.jsx:18`.

`COMPETITOR_STORES` is a hardcoded array of **4 stores** with **6 barcodes each**: Paz Yellow (200m), Delek Menta (450m), Sonol So Good (1.1km), Dor Alon Alonit (1.4km). The `filterStoresByRadius()` call in `App.jsx:138` with `1000`m radius keeps only Yellow and Menta. All prices are fabricated integers (e.g., Red Bull at 7.90₪, 8.20₪).

The `BARCODE_TO_PRODUCT_ID` map at `mockMarketData.js:29` has 6 entries linking EAN-13 barcodes to the demo product IDs (`rb-001`, `xl-002`, etc.). These barcodes are not the real barcodes from `yomyom-inventory.csv`.

**What it takes to swap real data:** Export `data/matching/barcode_matches.parquet` to `src/data/marketData.js` in the same shape, then change `App.jsx:18` to `import { COMPETITOR_STORES, OUR_STORE } from './data/marketData.js'`.

---

### AI explanations (`src/lib/ai/`)

**Active provider:** `mockExplanationProvider`. `getDefaultExplanationProvider()` at `explanationProvider.js:41` unconditionally returns `mockExplanationProvider`. It is a rule-based text generator in `src/lib/analytics/mockAI.js`.

**`llmExplanationProvider`** (`src/lib/ai/llmExplanationProvider.js`): `enabled: false` hardcoded at line 4. `getLLMExplanationProviderStatus()` returns `enabled: false` with the string `"Disabled until a backend/proxy is available"`. This function is not called anywhere — it exists as a status query utility only.

**Critical signature bug:** `llmExplanationProvider.generateExplanation(payload, options)` expects `options.enabled` and `options.proxyUrl`. But the caller in `annotateRecommendationsWithExplanations()` (`explanationProvider.js:22`) calls `provider.generateExplanation({ marketContext, product, recommendation })` with no second argument. Even if you set `enabled: true` on the object, it would always fall through to the disabled path because `options` would be `{}`.

**`VITE_LLM_PROXY_URL`**: Declared in `.env.example` but **never read anywhere in the source code**. There is no `import.meta.env.VITE_LLM_PROXY_URL` anywhere in `src/`.

**`VITE_LLM_EXPLANATIONS_ENABLED`**: Same — declared in `.env.example` but **never read anywhere** in the source code.

**`gemini.js`** (`src/lib/ai/gemini.js`): Not imported anywhere. The file exports 3 functions that all return errors/stubs. Pure dead code.

---

### Report generation (`ReportPage.jsx` + `reportBuilder.js`)

The 2.2-second delay at `ReportPage.jsx:23` is a **`setTimeout`**. No async operation. `buildOptimizationReport()` is a **synchronous template function** that formats markdown from the in-memory analyzed products data. No LLM is called. The report is 100% rule-based text.

---

### Shelf image upload (`PlanogramPage.jsx`)

`handleAnalyze` at `PlanogramPage.jsx:43` is a `setTimeout(..., 1800)`. Calls `generateMockDetectedShelf(planogramItems)` which inverts the expected planogram layout with random noise, then `analyzeCompliance()` compares it. **Both are local mock functions in `src/lib/analytics/complianceEngine.js`.** No vision model, no network call, no backend.

---

### Comax connector (`comaxConnectorStub.js`)

`connect()` **always returns `ok: false`**. If `VITE_COMAX_PROXY_URL` is not set (and it is not, since `.env` doesn't set it), returns `"Backend proxy required"`. If it is set, returns `"live mode is not yet enabled in this build"`. There is no code path where `connect()` returns `ok: true`. The `load()` function unconditionally throws.

---

### Market context

With `VITE_ENABLE_LIVE_MARKET_CONTEXT=false` (the default, set in `.env.example`), `buildMarketContext()` at `marketContextAdapter.js:127` immediately returns `fallbackMarketContext`. That resolves to `src/data/marketContext.js`:

```js
{
  currentDate: '2026-05-15',  // hardcoded, stale
  weather: 'hot',
  weekend: true,
  holiday: false,
  localEvent: 'football match nearby',
  season: 'summer',
  demandSignals: { 'Cold Drinks': 1.18, 'Energy Drinks': 1.16, Water: 1.2, Snacks: 1.1, 'Ice Cream': 1.15 }
}
```

When live mode is enabled, it calls Open-Meteo (weather), Nager.Date (holidays), and GDELT (news). The default `.env.example` has `VITE_HOLIDAY_COUNTRY=AT` (Austria) and `VITE_NEWS_QUERY=Jordan` — these are placeholder values, not Israel-specific.

---

## 4. ENVIRONMENT VARIABLES — WIRED vs DEAD

| Variable | Status | Where read |
|---|---|---|
| `VITE_ENABLE_LIVE_MARKET_CONTEXT` | **Wired** | `App.jsx:114` |
| `VITE_LLM_PROXY_URL` | **Dead** — declared in `.env.example`, never read in source code | Nowhere in `src/` |
| `VITE_LLM_EXPLANATIONS_ENABLED` | **Dead** — declared in `.env.example`, never read in source code | Nowhere in `src/` |
| `VITE_HOLIDAY_COUNTRY` | **Wired** | `App.jsx:115`, `holidays.js:13` |
| `VITE_WEATHER_LAT` | **Wired** | `App.jsx:117`, `weather.js:11` |
| `VITE_WEATHER_LON` | **Wired** | `App.jsx:118`, `weather.js:12` |
| `VITE_NEWS_QUERY` | **Wired** | `App.jsx:120`, `news.js:15` |
| `VITE_COMAX_PROXY_URL` | **Wired but inert** | `comaxConnectorStub.js:23` — checked but `connect()` still returns `ok: false` even when set |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | **Wired** | `src/external/firestore_writer.py` |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | **Wired** | `src/external/firestore_writer.py` |
| `FIREBASE_PROJECT_ID` | **Wired** | `src/external/firestore_writer.py` |
| `KAGGLE_API_TOKEN` | **Wired** | `download_kaggle_datasets.py` only |
| `TENBIS_BEARER_TOKEN` | **Wired but disabled** | `tenbis_connector.py` (imported by `delivery_venue_connector.py`) — ToS violation risk documented in `.env.example` |

---

## 5. DEAD CODE AND UNNECESSARY FILES

### Definitely dead

| Item | Why |
|---|---|
| `src/lib/ai/gemini.js` | Not imported anywhere. All 3 functions are stubs that return errors. No `import ... from './gemini.js'` exists in the codebase. |
| `src/assets/hero.png`, `react.svg`, `vite.svg` | Not imported in any JS/JSX/CSS file. Likely Vite scaffolding leftovers. |
| `VITE_LLM_PROXY_URL` in `.env.example` | Declared but `import.meta.env.VITE_LLM_PROXY_URL` is never read anywhere. The LLM proxy URL would need to be passed programmatically to the provider, not via env var. |
| `VITE_LLM_EXPLANATIONS_ENABLED` in `.env.example` | Same — not read anywhere. |

### Effectively dead until wired

| Item | Why |
|---|---|
| `data/internal/silver_pos/*.parquet` | Generated from fake POS data. Not read by any frontend code or export script. |
| `data/signals/yomyom/pos_signals_latest.json` | Not read by any frontend code or export script. |
| `data/external/silver/products/delivery_catalog/` | Not read by any frontend code or export script. The 366 SKUs from 9 Wolt venues are sitting in Parquet files with no consumer. |
| `data/external/silver/alonit_prices/` | Only read by `mcp_price_adapter.py` (MCP tool). Not connected to frontend. |
| `data/processed/rag/*.jsonl` | RAG corpus files. Not embedded, not indexed, not queried. No consumer. |
| `build-rag-corpus.mjs` | Produces the RAG corpus but there's no embedding/vector-DB step wired to consume it. |
| `src/mcp_server/price_server.py` | MCP server that queries Alonit prices. Useful for Claude assistant lookups, but completely disconnected from the React frontend. |

### Superseded

| Item | Why |
|---|---|
| `data/internal/raw_pos/yomyom/sample_yomyom_pos.csv` | 134-row fake CSV generated by `generate_fake_yomyom_pos.py`. The real `yomyom-inventory.csv` (7,674 rows, project root) supersedes it, but is not yet imported. |

### Effectively disabled

`tenbis_connector.py` is imported by `delivery_venue_connector.py` but the TenBis path is permanently disabled (no bearer token, ToS reasons). The code is referenced but never executes.

### Console statements

Four legitimate uses found (not debug spam): `ErrorBoundary.jsx:15` (`console.error` on render errors), `liveMarketContext.js:123` (`console.warn` on source failure), `localStorageAdapter.js:69,103` (`console.warn` on persistence failures). All are at exception boundaries — appropriate.

---

## 6. THE CRITICAL MISSING CONNECTIONS

### Step 1: Import `yomyom-inventory.csv` into the pipeline

**File to change:** `configs/pos_schema_mapping.yaml`

Add these 3 `candidate_names` entries to resolve the schema mismatch:

```yaml
# product_name — add:
      - תאור פריט        # Hebrew: item description (YomYom real CSV column)

# category — add:
      - שם מחלקה         # Hebrew: department name (YomYom real CSV column)

# current_stock — add:
      - מלאי נוכחי       # Hebrew: current inventory (YomYom real CSV column)
```

Also add `WOLT` as a new column mapping in the YAML if you want to capture Wolt prices:

```yaml
  - raw_name:       wolt_price
    canonical_name: wolt_price
    dtype:          decimal
    required:       false
    normalizers:    [strip_whitespace, null_if_empty]
    candidate_names:
      - WOLT
```

**Fix the negative stock validation:** In `configs/pos_schema_mapping.yaml`, the rule at `validation.non_negative_fields` includes `current_stock`. Remove it or add a normalizer that clamps negatives to 0. Currently 627 rows (8.2%) would be rejected.

**Fix the duplicate column:** The real CSV has `שם מחלקה` twice. Python's `csv.DictReader` will silently rename the second to a variant. The schema mapping will claim the first occurrence and leave the second unmapped. This is fine.

**Then run:**
```bash
python scripts/import_yomyom_pos.py \
    --input yomyom-inventory.csv \
    --config configs/pos_schema_mapping.yaml
```

Note: the real CSV has no sales data (`units_sold_7d`, `units_sold_30d`, etc.). All signal thresholds in the YAML depend on those fields. The `low_stock_fast_movers` and `high_margin_impulse` signals will be empty.

---

### Step 2: Download + import Kaggle competitor prices

```bash
# Set KAGGLE_API_TOKEN in .env
python scripts/download_kaggle_datasets.py
python scripts/import_kaggle_supermarkets.py
```

Output: `data/external/silver/products/kaggle_dor_alon/`, `kaggle_rami_levy/`, `kaggle_shufersal/`. Prerequisite: `KAGGLE_API_TOKEN`. No code changes needed.

---

### Step 3: Barcode join — write a new script

**New file:** `scripts/join_yomyom_kaggle.py`

```python
# Reads: yomyom-inventory.csv barcodes (ברקוד  column)
# Reads: data/external/silver/products/kaggle_*/  (barcode field)
# Writes: data/matching/barcode_matches.parquet
#   columns: barcode, yomyom_product_name, yomyom_price, yomyom_cost,
#            chain, kaggle_product_name, kaggle_price, price_gap_ils, price_gap_pct
```

Key join condition: `yomyom_barcode == kaggle_barcode` (EAN-13 string match after stripping whitespace and leading zeros). The ~6,902 YomYom rows with barcodes need to be matched against the Kaggle silver barcodes. This join does not exist yet.

---

### Step 4: Export script — write a new script

**New file:** `scripts/export_competitor_market_data.py`

Reads `data/matching/barcode_matches.parquet`. Writes `src/data/marketData.js` in the same shape as `mockMarketData.js`:

```js
export const OUR_STORE = { ... }
export const COMPETITOR_STORES = [
  {
    brand: 'Rami Levy',
    storeId: '...',
    distance_m: ...,
    snapshot: {
      '7290001020001': { price: 8.90, isAvailable: true },
      ...
    }
  },
  ...
]
```

The `snapshot` object maps EAN-13 barcode → `{ price, isAvailable }`. The delivery catalog data from Wolt (`data/external/silver/products/delivery_catalog/`) can populate `isAvailable` (field `is_online_available`). Kaggle data provides the price.

---

### Step 5: Update `App.jsx`

**File:** `src/App.jsx:18`

Change:
```js
import { COMPETITOR_STORES, OUR_STORE } from './data/mockMarketData.js'
```
to:
```js
import { COMPETITOR_STORES, OUR_STORE } from './data/marketData.js'
```

No other changes needed — the competitor engine (`competitorEngine.js`) accepts the same `COMPETITOR_STORES` shape.

---

### Step 6: LLM proxy — enable real AI explanations

**Two bugs to fix before writing the proxy:**

**Bug 1** — Signature mismatch in `explanationProvider.js:22`. The call is:
```js
provider.generateExplanation({ marketContext, product, recommendation })
```
But `llmExplanationProvider.generateExplanation(payload, options)` checks `options.enabled` and `options.proxyUrl`. Fix: change `getDefaultExplanationProvider()` to return a wrapper or pass options inline.

**Bug 2** — `VITE_LLM_PROXY_URL` is not read anywhere. It needs to be read inside `getDefaultExplanationProvider()`.

**What to build:**

1. `src/api/llm_proxy.py` — FastAPI endpoint receiving a `buildLLMExplanationPayload` JSON object (from `llmExplanationProvider.js:27`), calling `claude-sonnet-4-6`, returning `{ shortExplanation, riskReason, businessImpact, confidenceNote }`.

2. Fix `explanationProvider.js:41`:
```js
export function getDefaultExplanationProvider() {
  const proxyUrl = import.meta.env.VITE_LLM_PROXY_URL
  if (proxyUrl) {
    return {
      ...llmExplanationProvider,
      generateExplanation(payload) {
        return llmExplanationProvider.generateExplanation(payload, { enabled: true, proxyUrl })
      }
    }
  }
  return mockExplanationProvider
}
```

3. Set `VITE_LLM_PROXY_URL=http://localhost:8000/explain` in `.env`.
