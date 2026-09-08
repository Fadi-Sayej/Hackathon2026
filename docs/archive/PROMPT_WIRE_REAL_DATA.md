> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# Claude Code Prompt — Wire Frontend to Real Data

Paste this entire prompt into Claude Code.

---

Read these files before doing anything:

- src/lib/analytics/competitorEngine.js
- src/data/marketData.js
- src/data/mockMarketData.js
- src/data/demoProducts.js
- scripts/normalize-datasets.mjs
- src/lib/dataAdapters/loadDemoStoreData.js
- src/lib/posConnectors/demoDataConnector.js
- src/App.jsx

You are fixing two issues that prevent the frontend from using real data. Both are quick and well-defined. Work through them in order.

---

## FIX 1 — competitorEngine.js imports PRODUCT_ID_TO_BARCODE from the wrong file

**File:** `src/lib/analytics/competitorEngine.js` line 14

The real `marketData.js` exports `PRODUCT_ID_TO_BARCODE` with 5,687 real barcodes matched against Shufersal, Rami Levy, and Dor Alon. But `competitorEngine.js` still imports it from `mockMarketData.js` which only has 6 hardcoded barcodes.

**Fix — change line 14:**
```js
// FROM:
import { PRODUCT_ID_TO_BARCODE } from '../../data/mockMarketData.js'
// TO:
import { PRODUCT_ID_TO_BARCODE } from '../../data/marketData.js'
```

**Done when:** `grep "PRODUCT_ID_TO_BARCODE" src/lib/analytics/competitorEngine.js` shows `marketData.js`, not `mockMarketData.js`.

---

## FIX 2 — App loads 28 fake English products on startup instead of 7,674 real Hebrew ones

The app calls `loadDemoStoreData()` on startup which reads `src/data/demoProducts.js` — a file with 28 hardcoded English products (Coca Cola 500ml, Mineral Water, etc.). The real 7,674-product YomYom inventory is in `data/internal/silver_pos/yomyom_products.parquet` but never reaches the frontend.

`scripts/normalize-datasets.mjs` is the script that regenerates `src/data/demoProducts.js`. It currently only reads from `data/raw/` CSV files and falls back to a hardcoded English list. It needs to be updated to read from the real silver Parquet first.

**What to add to `scripts/normalize-datasets.mjs`:**

At the top of the file, after the existing imports, add:

```js
import { existsSync, readFileSync } from 'node:fs'
import { execSync } from 'node:child_process'

const SILVER_PARQUET = path.join(rootDir, 'data', 'internal', 'silver_pos', 'yomyom_products.parquet')
const SILVER_JSON_CACHE = path.join(rootDir, 'data', 'internal', 'silver_pos', 'yomyom_products_export.json')

function loadYomYomSilver() {
  if (!existsSync(SILVER_PARQUET)) return null
  try {
    execSync(
      `python3 -c "import polars as pl, json; df=pl.read_parquet('${SILVER_PARQUET}'); open('${SILVER_JSON_CACHE}','w',encoding='utf-8').write(df.write_json())"`,
      { stdio: 'pipe', cwd: rootDir }
    )
    const raw = JSON.parse(readFileSync(SILVER_JSON_CACHE, 'utf-8'))
    return raw
      .filter(row => row.selling_price && row.selling_price > 0 && row.product_name)
      .map(row => ({
        id: row.barcode ? `ym-${String(row.barcode).replace(/^0+/, '')}` : `ym-${row.product_name}`,
        name: row.product_name,
        category: row.category ?? 'Uncategorized',
        price: Number(row.selling_price) || 0,
        cost: Number(row.cost_price) || 0,
        currentStock: Math.max(0, Number(row.current_stock) || 0),
        shelfQuantity: 0,
        shelfCapacity: 10,
        salesLast7Days: 0,
        salesLast30Days: 0,
        supplier: 'YomYom',
        leadTimeDays: 3,
        returnedUnits: 0,
        damagedUnits: 0,
        expiryDate: undefined,
      }))
  } catch (err) {
    process.stderr.write(`Warning: could not load YomYom silver Parquet: ${err.message}\n`)
    return null
  }
}
```

Then in the `main()` function, replace the existing source-discovery block:

```js
// BEFORE (existing code):
const discovered = await discoverDataFiles(rawDir)
const source = discovered.length > 0 ? await chooseBestSource(discovered) : buildFallbackSource()
const normalized = normalizeSource(source)
const demoProducts = buildDemoSlice(normalized.products)

// AFTER (add real-data loader before discovery):
const yomyomProducts = loadYomYomSilver()

let demoProducts
let normalized
let source

if (yomyomProducts && yomyomProducts.length > 0) {
  // Real YomYom silver data available — use it directly, skip CSV discovery
  demoProducts = yomyomProducts
  normalized = { products: yomyomProducts, generatedFields: [], notes: [] }
  source = { label: `YomYom silver Parquet (${yomyomProducts.length} products)`, rowCount: yomyomProducts.length }
  process.stdout.write(`Using real YomYom inventory: ${yomyomProducts.length} products\n`)
} else {
  // Fall back to CSV discovery or hardcoded demo
  const discovered = await discoverDataFiles(rawDir)
  source = discovered.length > 0 ? await chooseBestSource(discovered) : buildFallbackSource()
  normalized = normalizeSource(source)
  demoProducts = buildDemoSlice(normalized.products)
  process.stdout.write(`Falling back to demo data: ${demoProducts.length} products\n`)
}

const analyticsSummary = buildAnalyticsSummary(normalized.products)
const report = buildReport(source, normalized.products, normalized.generatedFields ?? [], normalized.notes ?? [])
```

**Important:** The existing code after this block writes files using `demoProducts`, `analyticsSummary`, and `report` — leave all of that unchanged. Only replace the source-discovery + normalization block above.

**Run it:**
```bash
node scripts/normalize-datasets.mjs
```

**Done when:**
- The script prints "Using real YomYom inventory: 7674 products" (not "Falling back to demo data")
- `src/data/demoProducts.js` contains Hebrew product names (e.g. grep for any Hebrew character: `grep -c "מ\|ח\|ש\|ב\|כ" src/data/demoProducts.js`)
- The file has 7,000+ products: `node -e "import('./src/data/demoProducts.js').then(m => console.log(m.demoProducts.length))"`

---

## After both fixes

Run:
```bash
npm run lint
```

Commit:
```
fix: wire real YomYom products to frontend, fix competitorEngine barcode import
```

The app will now load 7,674 real Hebrew products on startup and use 5,687 real competitor barcodes for price gap analysis — no manual CSV upload needed.
