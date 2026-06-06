# SmartShelf AI — State Update + Team Sprint Plan

*Generated June 6, 2026. Based on TECHNICAL_AUDIT.md, CLAUDE.md, STATUS.md, and live codebase inspection.*

---

## PART 1: State Update — What's Changed Since the Audit

**Short answer: nothing substantive.** The only commit since `9eb71d6 deep audit of current project status` was the `anas` PR (#6), which was a repo cleanup: removed large debug JSON blobs from git tracking, added `.gitkeep` files to create directory stubs (`data/matching/`, `data/recommendations/`, `data/signals/`, `reports/quality/`), and added `docs/sources/alonit_signal_source.md`. No pipeline code changed.

Specific checks:

| Audit finding | Status today |
|---|---|
| `yomyom-inventory.csv` not referenced anywhere | **Same.** Still at project root. No importer touches it. `data/internal/raw_pos/yomyom/` directory does not even exist — `init_storage.py` has not been run since the audit. |
| Hebrew columns missing from `pos_schema_mapping.yaml` (`תאור פריט`, `שם מחלקה`, `מלאי נוכחי`) | **Same.** No Hebrew candidates added. `import_yomyom_pos.py` would still bail on `missing_required_columns`. |
| Kaggle data not downloaded | **Same.** `data/raw/kaggle/` contains only `.gitkeep`. No CSV files. |
| `data/external/silver/products/kaggle_*/` directories absent | **Same.** `kaggle_dor_alon`, `kaggle_rami_levy`, `kaggle_shufersal` all missing. |
| `data/matching/barcode_matches.parquet` absent | **Same.** Directory now has a `.gitkeep` (from anas PR) but no Parquet. |
| `src/data/marketData.js` absent | **Same.** Does not exist. |
| `App.jsx:18` imports `mockMarketData.js` | **Same.** Unchanged. |
| `VITE_LLM_PROXY_URL` not read in source | **Same.** Zero occurrences of `import.meta.env.VITE_LLM_PROXY_URL` anywhere in `src/`. |
| `getDefaultExplanationProvider()` unconditionally returns `mockExplanationProvider` | **Same.** Line 41 of `explanationProvider.js` is identical to what the audit documented. |
| `gemini.js` is dead code | **Same.** File exists, not imported anywhere. |
| Dead assets (`hero.png`, `react.svg`, `vite.svg`) | **Same.** All three still in `src/assets/`. |
| `marketContext.js` stale date `2026-05-15` | **Same.** |
| `.env.example` defaults `VITE_HOLIDAY_COUNTRY=AT`, `VITE_NEWS_QUERY=Jordan` | **Same.** |
| `ANTHROPIC_API_KEY` absent from `.env.example` | **Same.** No `ANTHROPIC_API_KEY` entry. |
| `scripts/join_yomyom_kaggle.py` absent | **Same.** Does not exist. |
| `scripts/export_competitor_market_data.py` absent | **Same.** Does not exist. |
| `src/api/llm_proxy.py` absent | **Same.** `src/api/` directory does not exist. |

**New since audit:**
- `data/matching/.gitkeep` — directory stub only
- `reports/quality/.gitkeep` — directory stub only
- `docs/sources/alonit_signal_source.md` — documentation
- `.gitignore` updated to exclude more generated files

**Zero lines of implementation code written since the audit.** The starting line for the sprint is identical to what the audit described.

---

## PART 2: Sprint Plan — 4 People Working in Parallel

The plan is structured so Day 1 work for each person is independent. Handoffs are explicitly called out. Each person works in their own branch (`person-a`, `person-b`, `person-c`, `person-d`).

---

### Person A — Python pipeline: real YomYom data

**Goal:** Get the 7,678-row real inventory file through the pipeline and produce `data/matching/barcode_matches.parquet`.

---

#### A-0: One-time setup (do first, 5 minutes)

```bash
python scripts/init_storage.py
```

This creates the missing `data/internal/raw_pos/yomyom/` directory (and others). The anas PR added `.gitkeep` stubs for some dirs but not this one.

- [ ] **Done when:** `ls data/internal/raw_pos/yomyom/` succeeds.

---

#### A-1: Move the real CSV into the pipeline path

Move `yomyom-inventory.csv` from the project root to the canonical pipeline location:

```bash
cp yomyom-inventory.csv data/internal/raw_pos/yomyom/yomyom_inventory_real.csv
```

- [ ] **Done when:** `data/internal/raw_pos/yomyom/yomyom_inventory_real.csv` exists and `wc -l` reports 7,676 lines (header + 7,675 data rows).

---

#### A-2: Fix `configs/pos_schema_mapping.yaml` — add Hebrew column candidates

**File:** `configs/pos_schema_mapping.yaml`

The audit identified three fields that fail to resolve because their Hebrew column names are absent from `candidate_names`. Make these three additions:

Under `product_name` → `candidate_names`, append:
```yaml
      - "תאור פריט"         # YomYom real CSV: item description
```

Under `category` → `candidate_names`, append:
```yaml
      - "שם מחלקה"          # YomYom real CSV: department name
```

Under `current_stock` → `candidate_names`, append:
```yaml
      - "מלאי נוכחי"        # YomYom real CSV: current inventory level
```

Also add a new optional field mapping for Wolt price (after the last field mapping block):
```yaml
  - raw_name:       wolt_price
    canonical_name: wolt_price
    dtype:          decimal
    required:       false
    normalizers:    [strip_whitespace, null_if_empty]
    candidate_names:
      - WOLT
```

Then fix the negative-stock rejection. Find `non_negative_fields` (around line 253) and **remove `current_stock`** from the list. In the `current_stock` field definition, add `clamp_negative_to_zero` to its `normalizers` list (or if that normalizer doesn't exist, simply remove `current_stock` from `non_negative_fields` — the import will then accept negative values and Person A can document them in A-3).

- [ ] **Done when:** `python scripts/import_yomyom_pos.py --input data/internal/raw_pos/yomyom/yomyom_inventory_real.csv` completes without `missing_required_columns` error and writes 4 Parquet files to `data/internal/silver_pos/`:
  - `yomyom_products.parquet`
  - `yomyom_sales.parquet`
  - `yomyom_inventory.parquet`
  - `yomyom_margins.parquet`

---

#### A-3: Document import quality — write `reports/yomyom_real_import_notes.md`

After A-2 succeeds, run a quick quality check:

```python
import polars as pl
df = pl.read_parquet("data/internal/silver_pos/yomyom_products.parquet")
print(len(df))
print(df.filter(pl.col("current_stock") < 0).shape[0])   # negative stock
print(df.filter(pl.col("barcode").is_null()).shape[0])    # missing barcodes
```

Write `reports/yomyom_real_import_notes.md` with:
- Total rows imported
- Rows with negative stock (expected ~627)
- Rows with missing/zero barcode (expected ~307)
- Rows with no category (if any)
- Note that sales columns (`units_sold_7d`, `units_sold_30d`) are all null — signals depending on them will be empty

- [ ] **Done when:** `reports/yomyom_real_import_notes.md` exists with the above row counts.

---

#### A-4: Write `scripts/join_yomyom_kaggle.py` — barcode join

**Depends on:** A-2 complete AND Person B step B-2 complete. Write the script first; run it once B-2 is done.

**File to create:** `scripts/join_yomyom_kaggle.py`

```python
"""
Join YomYom barcodes against Kaggle competitor silver Parquets.
Output: data/matching/barcode_matches.parquet
"""
import polars as pl
from pathlib import Path

KAGGLE_SILVER = Path("data/external/silver/products")
YOMYOM_SILVER = Path("data/internal/silver_pos/yomyom_products.parquet")
OUTPUT = Path("data/matching/barcode_matches.parquet")

def normalize_barcode(series: pl.Series) -> pl.Series:
    return series.cast(pl.Utf8).str.strip_chars().str.lstrip_chars("0")

def load_kaggle_chain(chain_dir: Path, chain_name: str) -> pl.DataFrame:
    files = list(chain_dir.glob("*.parquet"))
    if not files:
        return pl.DataFrame()
    df = pl.concat([pl.read_parquet(f) for f in files])
    return df.select([
        pl.col("barcode").pipe(normalize_barcode).alias("barcode_norm"),
        pl.col("product_name").alias("kaggle_product_name"),
        pl.col("price").alias("kaggle_price"),
        pl.lit(chain_name).alias("chain"),
    ]).drop_nulls("barcode_norm")

def main():
    yomyom = pl.read_parquet(YOMYOM_SILVER).select([
        pl.col("barcode").pipe(normalize_barcode).alias("barcode_norm"),
        pl.col("product_name").alias("yomyom_product_name"),
        pl.col("selling_price").alias("yomyom_selling_price"),
        pl.col("cost_price").alias("yomyom_cost_price"),
    ]).drop_nulls("barcode_norm").filter(pl.col("barcode_norm") != "")

    chains = []
    for chain_name in ["kaggle_dor_alon", "kaggle_rami_levy", "kaggle_shufersal"]:
        chain_dir = KAGGLE_SILVER / chain_name
        if chain_dir.exists():
            chains.append(load_kaggle_chain(chain_dir, chain_name))

    if not chains:
        print("ERROR: No Kaggle silver data found. Run import_kaggle_supermarkets.py first.")
        return

    kaggle = pl.concat(chains)
    matched = yomyom.join(kaggle, on="barcode_norm", how="inner")
    matched = matched.with_columns([
        (pl.col("yomyom_selling_price") - pl.col("kaggle_price")).alias("price_gap_ils"),
        ((pl.col("yomyom_selling_price") - pl.col("kaggle_price")) / pl.col("kaggle_price") * 100)
            .alias("price_gap_pct"),
        pl.col("barcode_norm").alias("barcode"),
    ])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    matched.write_parquet(OUTPUT)
    print(f"Wrote {len(matched)} matches to {OUTPUT}")
    print(matched.group_by("chain").len().sort("chain"))

if __name__ == "__main__":
    main()
```

- [ ] **Done when:** `data/matching/barcode_matches.parquet` exists and `python -c "import polars as pl; df=pl.read_parquet('data/matching/barcode_matches.parquet'); print(len(df), df['chain'].unique())"` shows >0 rows across at least one chain.

---

### Person B — Python pipeline: Kaggle data + export script

**Goal:** Download Kaggle competitor prices, import them, and export a `marketData.js` the frontend can consume.

---

#### B-1: Download Kaggle dataset

**Prerequisite:** `KAGGLE_API_TOKEN` must be set in `.env`. Get it from kaggle.com → Settings → API → Create New Token.

```bash
python scripts/download_kaggle_datasets.py
```

- [ ] **Done when:** These files exist in `data/raw/kaggle/israeli-supermarkets-2024/`:
  - `price_full_file_dor_alon.csv`
  - `price_full_file_rami_levy.csv`
  - `price_full_file_shufersal.csv`
  - `store_file_dor_alon.csv`, `store_file_rami_levy.csv`, `store_file_shufersal.csv`

---

#### B-2: Import all three Kaggle chains

```bash
python scripts/import_kaggle_supermarkets.py
```

- [ ] **Done when:** Parquet files exist in all three directories:
  - `data/external/silver/products/kaggle_dor_alon/`
  - `data/external/silver/products/kaggle_rami_levy/`
  - `data/external/silver/products/kaggle_shufersal/`

> **Handoff to A-4:** Once B-2 is done, tell Person A to run `join_yomyom_kaggle.py`.

---

#### B-3: Write `scripts/export_competitor_market_data.py`

**Depends on:** A-4 complete (produces `data/matching/barcode_matches.parquet`). Write the script first; run it once A-4 is done.

**File to create:** `scripts/export_competitor_market_data.py`

```python
"""
Export competitor price data to src/data/marketData.js.
Reads: data/matching/barcode_matches.parquet
       data/external/silver/products/delivery_catalog/
Writes: src/data/marketData.js
"""
import polars as pl
import json
from pathlib import Path
from datetime import datetime

MATCHES = Path("data/matching/barcode_matches.parquet")
DELIVERY_SILVER = Path("data/external/silver/products/delivery_catalog")
OUTPUT = Path("src/data/marketData.js")

CHAIN_META = {
    "kaggle_dor_alon": {
        "brand": "Dor Alon",
        "storeName": "Alonit Kafr Qasim",
        "storeId": "dor-alon-kq-01",
        "coords": {"lat": 32.114, "lon": 34.978},
        "distance_m": 1400,
    },
    "kaggle_rami_levy": {
        "brand": "Rami Levy",
        "storeName": "Rami Levy Petah Tikva",
        "storeId": "rami-levy-pt-01",
        "coords": {"lat": 32.089, "lon": 34.887},
        "distance_m": 2100,
    },
    "kaggle_shufersal": {
        "brand": "Shufersal",
        "storeName": "Shufersal Deal Petah Tikva",
        "storeId": "shufersal-pt-01",
        "coords": {"lat": 32.093, "lon": 34.890},
        "distance_m": 1800,
    },
}

OUR_STORE = {
    "brand": "YomYom",
    "storeName": "YomYom Kafr Qasim",
    "storeId": "yomyom-kq-01",
    "coords": {"lat": 32.114, "lon": 34.972},
}


def load_wolt_availability() -> set:
    available = set()
    parquet_files = list(DELIVERY_SILVER.rglob("*.parquet"))
    if not parquet_files:
        return available
    df = pl.concat([pl.read_parquet(f) for f in parquet_files])
    if "barcode" in df.columns and "is_online_available" in df.columns:
        online = df.filter(
            pl.col("is_online_available") == True,
            pl.col("barcode").is_not_null(),
        )
        available = set(online["barcode"].cast(pl.Utf8).to_list())
    return available


def main():
    if not MATCHES.exists():
        print("ERROR: data/matching/barcode_matches.parquet not found. Run join_yomyom_kaggle.py first.")
        return

    matches = pl.read_parquet(MATCHES)
    wolt_available = load_wolt_availability()

    competitor_stores = []
    barcode_to_product_id = {}
    product_id_to_barcode = {}

    for chain, meta in CHAIN_META.items():
        chain_rows = matches.filter(pl.col("chain") == chain)
        if len(chain_rows) == 0:
            continue

        snapshot = {}
        for row in chain_rows.iter_rows(named=True):
            barcode = str(row["barcode"])
            price = row["kaggle_price"]
            if price is None or price <= 0:
                continue
            snapshot[barcode] = {
                "price": round(float(price), 2),
                "isAvailable": barcode in wolt_available,
            }
            if barcode not in barcode_to_product_id:
                product_id = f"ym-{barcode}"
                barcode_to_product_id[barcode] = product_id
                product_id_to_barcode[product_id] = barcode

        competitor_stores.append({**meta, "snapshot": snapshot})

    js_content = f"""// AUTO-GENERATED by scripts/export_competitor_market_data.py
// Generated: {datetime.utcnow().isoformat()}Z
// Source: data/matching/barcode_matches.parquet

export const OUR_STORE = {json.dumps(OUR_STORE, ensure_ascii=False, indent=2)}

export const COMPETITOR_STORES = {json.dumps(competitor_stores, ensure_ascii=False, indent=2)}

export const BARCODE_TO_PRODUCT_ID = {json.dumps(barcode_to_product_id, ensure_ascii=False, indent=2)}

export const PRODUCT_ID_TO_BARCODE = {json.dumps(product_id_to_barcode, ensure_ascii=False, indent=2)}
"""

    OUTPUT.write_text(js_content, encoding="utf-8")
    total_barcodes = sum(len(s["snapshot"]) for s in competitor_stores)
    print(f"Wrote {OUTPUT}: {len(competitor_stores)} stores, {total_barcodes} barcode entries")


if __name__ == "__main__":
    main()
```

- [ ] **Done when:** `src/data/marketData.js` exists, exports `COMPETITOR_STORES` with at least one store and one barcode entry, and `npm run build` passes.

> **Handoff to C-1:** Once B-3 is done, tell Person C to switch the import in `App.jsx`.

---

### Person C — Frontend wiring and cleanup

**Goal:** Connect real data to the UI, remove dead code, fix stale defaults. C-4 (dead code removal) has zero dependencies — start there immediately.

---

#### C-4: Dead code removal (no dependencies — do first)

**C-4a:** Delete `src/lib/ai/gemini.js`

Verify it's not imported anywhere first:
```bash
grep -r "gemini" src/ --include="*.js" --include="*.jsx"
```
Expected: zero results. Then delete the file.

**C-4b:** Delete unused static assets:
```bash
rm src/assets/hero.png src/assets/react.svg src/assets/vite.svg
```

Verify nothing imports them:
```bash
grep -r "hero.png\|react.svg\|vite.svg" src/ --include="*.js" --include="*.jsx" --include="*.css"
```
Expected: zero results.

**C-4c:** Remove the dead env var from `.env.example`. Find and delete this line:
```
VITE_LLM_EXPLANATIONS_ENABLED=false
```
Leave `VITE_LLM_PROXY_URL=` in place — Person D will add a comment to it in D-4.

- [ ] **Done when:** `npm run lint` and `npm run build` both pass after all three sub-tasks.

---

#### C-2: Fix stale defaults in `src/data/marketContext.js` and `.env.example`

**File 1:** `src/data/marketContext.js` line 2 — change:
```js
currentDate: '2026-05-15',
```
to:
```js
currentDate: new Date().toISOString().split('T')[0],
```

**File 2:** `.env.example` — change `VITE_HOLIDAY_COUNTRY=AT` to `VITE_HOLIDAY_COUNTRY=IL` and `VITE_NEWS_QUERY=Jordan` to `VITE_NEWS_QUERY=Israel supermarket prices`.

- [ ] **Done when:** `src/data/marketContext.js` no longer contains the string `2026-05-15`, and `.env.example` shows `IL` and `Israel supermarket prices`.

---

#### C-1: Add `src/data/marketData.js` stub + switch import in `App.jsx`

**Depends on:** Person B step B-3 complete.

**Step 1 — create the stub** `src/data/marketData.js` so the build never breaks:

```js
// Stub — overwritten by scripts/export_competitor_market_data.py when real data is available
export { COMPETITOR_STORES, OUR_STORE, BARCODE_TO_PRODUCT_ID, PRODUCT_ID_TO_BARCODE } from './mockMarketData.js'
```

**Step 2 — update `src/App.jsx` line 18:**
```js
// change:
import { COMPETITOR_STORES, OUR_STORE } from './data/mockMarketData.js'
// to:
import { COMPETITOR_STORES, OUR_STORE } from './data/marketData.js'
```

**Step 3 — add `src/data/marketData.js` to `.gitignore`** so the generated real file is never committed.

- [ ] **Done when:** `npm run build` passes with the stub. After running `python scripts/export_competitor_market_data.py`, reloading the dev server shows real competitor data.

---

#### C-3: Update `scripts/normalize-datasets.mjs` to read real YomYom data

**Depends on:** Person A step A-2 complete.

**File:** `scripts/normalize-datasets.mjs`

Add a pre-check before `discoverDataFiles()` that reads the YomYom silver Parquet via a Python subprocess (since Node.js can't read Parquet natively):

```js
import { execSync } from 'child_process'
import { existsSync, readFileSync } from 'fs'

const YOMYOM_SILVER = 'data/internal/silver_pos/yomyom_products.parquet'
const YOMYOM_JSON_CACHE = 'data/internal/silver_pos/yomyom_products_export.json'

function exportYomYomToJson() {
  if (!existsSync(YOMYOM_SILVER)) return null
  try {
    execSync(
      `python -c "import polars as pl, json; df=pl.read_parquet('${YOMYOM_SILVER}'); open('${YOMYOM_JSON_CACHE}','w',encoding='utf-8').write(df.write_json())"`,
      { stdio: 'inherit' }
    )
    return YOMYOM_JSON_CACHE
  } catch {
    return null
  }
}
```

Field mapping from YomYom silver → canonical product shape:
- `barcode` → id
- `product_name` → name
- `category` → category
- `selling_price` → price
- `cost_price` → cost
- `current_stock` → currentStock (clamp to 0 if negative)
- Defaults for missing fields: `shelfQuantity: 0`, `shelfCapacity: 10`, `salesLast7Days: 0`, `salesLast30Days: 0`, `supplier: 'Unknown'`, `leadTimeDays: 3`, `returnedUnits: 0`, `damagedUnits: 0`

- [ ] **Done when:** `npm run sprint7` produces `src/data/demoProducts.js` with 7,000+ products with Hebrew names. Verify: `grep -c "name:" src/data/demoProducts.js`

---

### Person D — LLM proxy and real AI features

**Goal:** Make AI explanations call real Claude. D-4, D-1, and D-3 all have zero dependencies — do them all on day 1.

---

#### D-4: Fix `.env.example` — add `ANTHROPIC_API_KEY` and clarify `VITE_LLM_PROXY_URL`

In `.env.example`, replace the bare `VITE_LLM_PROXY_URL=` line with a commented block. Also remove `VITE_LLM_EXPLANATIONS_ENABLED=false` (coordinate with Person C / C-4c). Add:

```
# ── LLM proxy (FastAPI, enables real AI explanations) ────────────────────────
# Get your key at console.anthropic.com → API Keys
ANTHROPIC_API_KEY=

# URL of the running llm_proxy.py server. Set this to enable real LLM explanations
# instead of the rule-based mock. Must point to a running src/api/llm_proxy.py instance.
VITE_LLM_PROXY_URL=http://localhost:8000/explain
```

Also add `fastapi`, `uvicorn`, and `anthropic` to `requirements.txt` if not already present.

- [ ] **Done when:** `.env.example` has `ANTHROPIC_API_KEY=` and `VITE_LLM_PROXY_URL=http://localhost:8000/explain` with clear comments, and `requirements.txt` lists the three new packages.

---

#### D-1: Fix two bugs in `src/lib/ai/explanationProvider.js`

**File:** `src/lib/ai/explanationProvider.js`

**Bug 1:** `getDefaultExplanationProvider()` (line 41) unconditionally returns `mockExplanationProvider` and never reads `VITE_LLM_PROXY_URL`.

**Bug 2:** `annotateRecommendationsWithExplanations()` (line 22) calls `provider.generateExplanation({ marketContext, product, recommendation })` with one argument, but `llmExplanationProvider.generateExplanation(payload, options)` reads `options.enabled` and `options.proxyUrl` from the second argument — so `options` is always `undefined` and it always falls through to the disabled path.

**Fix — replace `getDefaultExplanationProvider()`:**

```js
export function getDefaultExplanationProvider() {
  const proxyUrl = import.meta.env.VITE_LLM_PROXY_URL
  if (proxyUrl) {
    return {
      ...llmExplanationProvider,
      generateExplanation(payload) {
        return llmExplanationProvider.generateExplanation(payload, { enabled: true, proxyUrl })
      },
    }
  }
  return mockExplanationProvider
}
```

The wrapper captures `proxyUrl` in its closure and passes it as the second argument — no change needed at the call site.

- [ ] **Done when:** Setting `VITE_LLM_PROXY_URL=http://localhost:8000/explain` in `.env` and running `npm run dev` causes the frontend to make POST requests to that URL (visible in browser DevTools → Network tab). Without the proxy running, errors fall back gracefully without crashing.

---

#### D-3: Write `src/api/llm_proxy.py`

Create `src/api/__init__.py` (empty) and `src/api/llm_proxy.py`:

```python
"""
LLM proxy — receives explanation payloads from the frontend,
calls Claude, returns structured explanation fields.

Run:  uvicorn src.api.llm_proxy:app --port 8000 --reload
Requires: ANTHROPIC_API_KEY env var
          pip install fastapi uvicorn anthropic
"""
import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import anthropic

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a retail inventory analyst for an Israeli convenience store.
Given product metrics and a reorder recommendation, produce a concise JSON explanation.
Respond ONLY with valid JSON matching this schema exactly:
{
  "shortExplanation": "one-sentence summary for the store owner",
  "riskReason": "why acting / not acting carries risk",
  "businessImpact": "estimated revenue/waste impact in ILS",
  "confidenceNote": "how confident the recommendation is and why"
}
Keep each field under 120 characters. Use Israeli context (ILS currency, Hebrew product names OK).
"""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/explain")
def explain(payload: dict):
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Product and recommendation data:\n{payload}"}],
        )
        result = json.loads(message.content[0].text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Done when:** With `ANTHROPIC_API_KEY` set, running `uvicorn src.api.llm_proxy:app --port 8000` and then `curl -s http://localhost:8000/health` returns `{"status":"ok"}`, and a POST to `/explain` with any JSON body returns all four fields.

---

#### D-5: Update `scripts/build-rag-corpus.mjs` to read real data

**Depends on:** Person A step A-2 complete.

**File:** `scripts/build-rag-corpus.mjs`

Replace the `loadDemoStoreData()` call with a real-data loader that exports the YomYom silver Parquet to JSON via a Python subprocess:

```js
import { execSync } from 'child_process'
import { existsSync, readFileSync } from 'fs'

const SILVER_PARQUET = 'data/internal/silver_pos/yomyom_products.parquet'
const EXPORT_JSON = 'data/internal/silver_pos/yomyom_products_export.json'

function loadRealProducts() {
  if (!existsSync(SILVER_PARQUET)) return null
  execSync(
    `python -c "import polars as pl; df=pl.read_parquet('${SILVER_PARQUET}'); open('${EXPORT_JSON}','w',encoding='utf-8').write(df.write_json())"`,
    { stdio: 'inherit' }
  )
  const raw = JSON.parse(readFileSync(EXPORT_JSON, 'utf-8'))
  return raw.map(row => ({
    id: `ym-${row.barcode ?? row.product_name}`,
    name: row.product_name ?? '',
    category: row.category ?? 'Uncategorized',
    price: row.selling_price ?? 0,
    cost: row.cost_price ?? 0,
    currentStock: Math.max(0, row.current_stock ?? 0),
    salesLast7Days: 0,
    salesLast30Days: 0,
  }))
}

// In the main corpus-building function, replace loadDemoStoreData():
const products = loadRealProducts() ?? loadDemoStoreData()
console.log(`Building RAG corpus from ${products.length} products`)
```

- [ ] **Done when:** `node scripts/build-rag-corpus.mjs` produces JSONL files in `data/processed/rag/` and `grep -c "." data/processed/rag/products.jsonl` shows 7,000+ lines with Hebrew product names.

---

## PART 3: Quick Wins (any person, <30 minutes each, no dependencies)

Pick these up between larger tasks. Each is self-contained.

- [ ] **Fix stale date** — `src/data/marketContext.js` line 2: change `'2026-05-15'` to `new Date().toISOString().split('T')[0]`
- [ ] **Fix `.env.example` locale defaults** — `VITE_HOLIDAY_COUNTRY=IL`, `VITE_NEWS_QUERY=Israel supermarket prices`
- [ ] **Delete `src/lib/ai/gemini.js`**
- [ ] **Delete `src/assets/hero.png`, `react.svg`, `vite.svg`**
- [ ] **Move `yomyom-inventory.csv`** from project root → `data/internal/raw_pos/yomyom/yomyom_inventory_real.csv`
- [ ] **Add `ANTHROPIC_API_KEY=` to `.env.example`** with a comment pointing to console.anthropic.com
- [ ] **Add `fastapi`, `uvicorn`, `anthropic` to `requirements.txt`**
- [ ] **Run `npm run lint`** and fix any pre-existing warnings unrelated to new work
- [ ] **Run `python scripts/init_storage.py`** to create all missing data directories

---

## Dependency Graph

```
A-0: init_storage.py ─────────────────────────── (day 1, no deps)
A-1: move CSV ────────────────────────────────── (day 1, no deps)
A-2: fix YAML (Hebrew columns) ───────────────── (day 1, no deps)
  │
  ├──→ A-3: quality report (after A-2)
  ├──→ C-3: normalize-datasets.mjs (after A-2)
  └──→ D-5: build-rag-corpus.mjs (after A-2)
  │
  └── A-4: join_yomyom_kaggle.py ──────────────── (needs A-2 + B-2)
        │
        └──→ B-3: export_competitor_market_data.py ──→ C-1: App.jsx switch

B-1: download Kaggle ─────────────────────────── (day 1, needs KAGGLE_API_TOKEN)
  │
  └──→ B-2: import Kaggle chains
              │
              └── [handoff to A-4]

C-4: dead code removal ───────────────────────── (day 1, no deps)
C-2: fix stale defaults ──────────────────────── (day 1, no deps)
C-1: App.jsx switch ──────────────────────────── (needs B-3)

D-4: .env.example + requirements.txt ────────── (day 1, no deps)
D-1: fix explanationProvider.js bugs ────────── (day 1, no deps)
D-3: write llm_proxy.py ─────────────────────── (day 1, no deps)
D-5: build-rag-corpus.mjs update ────────────── (needs A-2)
```

**Critical path (longest chain):**
```
B-1 → B-2 → [handoff] → A-4 → B-3 → C-1
              (also needs A-2 before A-4 can run)
```

**Everything on Person D is independent** — D-1, D-3, D-4 can all land on day 1 without waiting for any pipeline work.

**Person C's C-4 and C-2** are also fully independent — do them in the first hour.

**The only true serialization:** B-1 → B-2 (must be sequential), then both A-2 and B-2 must be done before A-4, then A-4 before B-3, then B-3 before C-1. Communicate via team chat when each step completes.
