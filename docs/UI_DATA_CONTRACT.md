# UI Data Contract — `App.jsx` → `src/pages/`

**Owner:** Anas (Track C) · **Consumer:** Malik (Track D) · **Issue:** C-0 (#14) · **Drafted:** 2026-08-02

This is an agreement, not a specification. It fixes the one boundary that file-level ownership
cannot protect: `App.jsx` computes, `src/pages/` renders. Neither side changes this boundary
without changing this file first.

**Sign-off**

| | |
|---|---|
| C drafted | ☑ Anas — 2026-08-02 |
| D agreed | ☐ Malik — _(date: ____)_ |

---

## 0. Rules

1. `App.jsx` builds **one** `pageProps` object (`src/App.jsx:387-425`) and spreads it into every
   page: `<DashboardPage {...pageProps} />`. Every page receives every prop. A page destructures
   only what it uses.
2. **A page never re-derives analytics.** No sales math, no margin math, no status classification
   in `src/pages/`. If a screen needs a number that isn't here, ask for it — don't compute it.
3. **Adding a prop is a contract change.** Anas updates this file and tells Malik before the prop
   lands. Malik does the same for a field he needs. Silent additions are how the tracks drift.
4. Everything is **already sorted and already rounded** by `App.jsx`. Pages format, they don't
   round.
5. `PlanogramPage` is **out of scope for the pilot** (`PLAN.md` §7 item 2). `planogramItems`,
   `shelfGroups`, `planogramSummary`, `affinitySuggestions`, `affinitySummary` stay in `pageProps`
   and the engines stay in place, unwired. Malik removes the nav entry (D-6); Anas does not delete
   the engine.

---

## 1. Props each page may use

| Prop | Type | Used by |
|---|---|---|
| `analyzedProducts` | `AnalyzedProduct[]` (§2) | Products, Dashboard, Report |
| `recommendations` | `Recommendation[]` (§3) | Recommendations, Dashboard, Report |
| `approvedOrders` | `Recommendation[]` — those with `status === 'APPROVED'` | Recommendations, ApprovedOrders |
| `productIndex` | `Map<string, Product>` — raw (pre-analytics) product by `id` | Recommendations, ApprovedOrders |
| `operationalData` | `OperationalData` (§4) | **Operational (home)**, Expiry |
| `operationalStatus` | `'loading' \| 'ready'` | Operational, Expiry |
| `dashboardStats` | `InventorySummary` + `estimatedOrderCost`, `highRiskStockouts`, `reorderSuggestions`, **+ `belowCostAlerts`, `priceGapAlerts`, `negativeStockAlerts`, `thinMarginAlerts`, `actionableRecommendations`, `valueAtStake` after C-2c** | Dashboard, Report |
| `inventorySummary` | `{ totalProducts, stockoutRisks, lowStock, overstocked, wasteRisk, highPriority, totalSalesLast30Days, estimatedInventoryValue }` — **+ `noVelocityData` after C-2a** | Dashboard, Report |
| `competitorSummary` | `{ priceLeaderCount, competitorOOSCount, priceProtectionCount, productsWithCoverage }` | Dashboard, Report |
| `priceLeaderProducts` / `stockoutOpportunities` / `priceProtectionAlerts` | `AnalyzedProduct[]` | Dashboard, (D-3 price-gap screen) |
| `marketContext` | `{ weather, weekend, holiday, localEvent, season, sourceLabel, … }` | Dashboard, Report |
| `dataProvenance` | `{ catalog, catalogCount, catalogLabel, hasSalesHistory, competitor, competitorStoreCount, liveMarketContext }` **+ `salesHistoryCount`, `velocityBreakdown: { none, low, medium, high }` after C-2c** | Dashboard, AppShell |
| `storeData` | `{ products, validationIssues, source, connectorMode, fileName, loadedAt }` | DataSource |
| `connectorStatus` | `{ state: 'ready'\|'loading'\|'error', message, hint?, mode? }` | DataSource |
| `planogramItems`, `shelfGroups`, `planogramSummary`, `affinitySuggestions`, `affinitySummary` | — | **hidden for pilot** (rule 5) |

Callbacks are in §6.

---

## 2. The analyzed product

**Analytics are nested under `product.analytics`, not top-level.** This is the single most common
mistake against this contract. `product.margin` is `undefined`; `product.analytics.margin` is the
number. Source: `src/lib/analytics/inventoryEngine.js:43-64`.

```js
{
  // canonical fields, top-level (src/lib/types.js)
  id, name, category, currentStock, shelfQuantity, shelfCapacity,
  salesLast7Days, salesLast30Days, price, cost, expiryDate?,
  supplier, leadTimeDays, returnedUnits, damagedUnits,
  velocityConfidence,          // 'none' | 'low' | 'medium' | 'high'  — added by C-6

  competitor: { … } | undefined, // injected by analyzeLocalMarket()

  analytics: {
    avgDailySales7, avgDailySales30, weightedAvgDailySales,  // number
    daysUntilStockout,        // number | null   ← null today for all 7,451 products
    margin,                   // number (₪)
    marginRate,               // number 0..1  (0.22 = 22%)
    primaryStatus,            // string, display-ready — render as-is
    statuses,                 // string[], display-ready
    competitorBoost,          // number, 1 = no signal
    riskScore,                // number 0..100
    velocityConfidence,       // 'none' | 'low' | 'medium' | 'high'  — added by C-2a
    hasVelocity,              // boolean                              — added by C-2a
  }
}
```

`primaryStatus` and `statuses` are **already human-readable English**: `"Healthy"`, `"Low stock"`,
`"Stockout risk"`, `"Overstocked"`, `"Slow moving"`, `"Near expiry"`, `"High priority"`, and after
C-2a `"Not enough sales history yet"`. Render the string; do not map it through a lookup table, and
do not add new status text in `src/pages/`.

Product `name`, `category` and `supplier` are Hebrew. Every element rendering them needs
`dir="auto"` (C-1a / C-1b).

---

## 3. The recommendation

Source: `makeRecommendation()`, `src/lib/analytics/reorderEngine.js:161-186`.

```js
{
  productId, productName, category,     // productName is Hebrew → dir="auto"
  type,                                 // see table below
  urgency,                              // 'LOW' | 'MEDIUM' | 'HIGH'
  status,                               // 'PENDING' | 'APPROVED' | 'REJECTED' | 'EDITED'
  confidence,                           // number 0..0.95  — model certainty, NOT data quality
  reason,                               // string, display-ready, distinct per product
  explanation,                          // string | undefined  (AI layer; see §5)
  recommendedOrderQuantity,             // number | undefined — REORDER only
  recommendedShelfQuantity,             // number | undefined — SHELF_* only

  velocityConfidence,                   // 'none'|'low'|'medium'|'high'  ← C-2b, top-level
  valueAtStake,                         // number (₪)                    ← C-2b, top-level

  metrics: { currentStock, weightedAvgDailySales, daysUntilStockout,
             safetyStock, leadTimeDays, margin, marginRate, demandMultiplier },
  context: { weather, weekend, holiday, localEvent, season },   // each may be null
}
```

### Types

| `type` | Meaning | Status |
|---|---|---|
| `REORDER` | Buy more | exists — **0 emitted** until real velocity |
| `REDUCE_STOCK` | Order less | exists — 0 emitted; suppressed at `velocityConfidence: 'none'` |
| `PROMOTION` | Discount / push | exists — **suppressed** at `'none'` by C-2b |
| `SHELF_INCREASE` / `SHELF_DECREASE` | Planogram | exists — pilot-hidden |
| `BELOW_COST` | `price < cost` | **new (C-2b)** — ~60 products |
| `PRICE_GAP` | Our price vs. competitor | **new (C-2b)** — from 14,406 barcode matches |
| `NEGATIVE_STOCK` | `currentStock < 0` | **new (C-2b)** — ~625 products |
| `THIN_MARGIN` | `marginRate < 0.20` | **new (C-2b)** — ~232 products |

The four new types and both new fields do **not exist in code yet** (C-2b, C-6). They are in this
contract so Malik can build D-1 against them without waiting.

### Two confidences — do not conflate them

- `confidence` (0..0.95) — how sure the *model* is. Existing field.
- `velocityConfidence` — how much *sales history* the number rests on. `'none'` means we have no
  history at all, which is the pilot's starting state and different from "sold zero".

**A recommendation with `velocityConfidence: 'none'` must never display a velocity claim** — no
"sells 3/day", no "will run out in N days". Show the type's own evidence (price, cost, stock,
competitor price) instead.

### Ordering

`recommendations` arrives sorted by ₪ at stake, then urgency (C-2b extends `sortRecommendations()`).
Pages render in array order. D-1 shows the top ~20; the rest go behind a filter.

---

## 4. `operationalData` — the home screen's data

Loaded from `public/data/operational.json`, a **build artifact** produced by
`npm run data:dashboard`. It is not committed; a clean clone gets `EMPTY_OPERATIONAL_DATA`
(`src/lib/dataAdapters/loadOperationalData.js:5-31`) — every count `0`, every array empty. **That is
a normal state, not an error.** Never render a spinner forever; show the empty state once
`operationalStatus === 'ready'`.

```js
{
  meta:      { generatedAt: string|null, status, competitorSignals, competitorRecommendations, scrapingStatus },
  posHealth: { totalProducts, missingBarcode, zeroPrice, zeroCost, negativeStock,
               woltPriceGaps, marginRisks, sourceFile: string|null },
  expiry:    { totalScans, actionable,
               buckets: { expired, critical_7d, warning_14d, upcoming_30d, later },
               alerts: [ { productName, barcode, expiryDate, daysToExpiry, … } ] },
  byType:    { [type]: count },
  byFamily:  { [family]: count },
  sources:   [ … ],
  recommendations: [ {
    id, family, type, barcode, productName, category,
    confidence, reason, severity,
    metricValue, sellingPrice, woltPrice, costPrice, currentStock,
    marginPct, daysToExpiry, expiryDate,
  } ],
}
```

Types present today: `CHECK_WOLT_PRICE_GAP` (1,147), `CHECK_NEGATIVE_STOCK` (625),
`VERIFY_UNKNOWN_BARCODE` (307), `CHECK_MARGIN` (104). **Every numeric field here is nullable** — the
Python exporter passes `None` through unchanged for any column missing in the source row. §5 applies
to all of them.

Competitor prices in this file are **Kaggle 2024 data**. Any screen showing them must date-stamp
them (`malik.md` D-3). Never present a 2024 price as today's price.

---

## 5. Nullability — the part that matters most

`analytics.daysUntilStockout` is `null` for **all 7,451 products** right now. A page that assumes a
number prints `null` to a store manager. Rules, in priority order:

**Never render a raw `null`, `undefined`, `NaN`, or `Infinity`. Never render `0` as if it were a
measurement when the truth is "we don't know".**

| Field | Null when | Page must render |
|---|---|---|
| `analytics.daysUntilStockout` | no velocity (always, today) | `"Not enough sales history yet"` — or `—` in a dense table cell. **Never a number, never `0`, never "∞"** |
| `analytics.velocityConfidence` `=== 'none'` | always, today | suppress every velocity-derived figure on that row |
| `analytics.primaryStatus` | never null | render the string as-is |
| `analytics.margin` / `.marginRate` | never null (`marginRate` is `0` when `price === 0`) | `marginRate === 0` **and** `price === 0` → `"No price on file"`, not `"0%"` |
| `analytics.riskScore` | never null | safe to render |
| `product.expiryDate` | usually undefined | `"No expiry recorded"` — the POS does not carry expiry; that gap is what D-2 exists to fill |
| `product.currentStock` | never null; **can be negative** (625 rows) | negative → `"Stock count wrong (−4)"`, never a plain negative quantity |
| `recommendation.recommendedOrderQuantity` | `undefined` for every non-`REORDER` type | hide the quantity control entirely; do not default to `1` in the UI |
| `recommendation.recommendedShelfQuantity` | `undefined` outside `SHELF_*` | hide |
| `recommendation.explanation` | `undefined` whenever the LLM path is off (**always today**, C-3) | fall back to `reason`, which is always present |
| `recommendation.metrics.daysUntilStockout` | same as above | same as above |
| `recommendation.context.*` | `null` when live context is off (default) | omit the chip; no "unknown weather" placeholder |
| `recommendation.valueAtStake` | `0` when not computable | sort last; show no ₪ figure rather than `₪0` |
| `dashboardStats.valueAtStake` | never null; `0` on a clean clone | ₪ sum across all live (non-rejected) recommendations — the PLAN.md §5 headline; `0` is an honest empty state |
| `dashboardStats.*Alerts` / `reorderSuggestions` | never null; `0` when none | counts of live recommendations by type; `reorderSuggestions` stays `0` until real velocity exists |
| `dataProvenance.salesHistoryCount` / `velocityBreakdown` | `0` / all-`none` today | `salesHistoryCount === 0` → state "no sales history yet"; `velocityBreakdown` is the per-band product count behind that claim |
| `operationalData.meta.generatedAt` | `null` before first pipeline run | `"Pipeline has not run yet"` |
| `operationalData.*` counts | `0` on a clean clone | empty state, not a spinner |
| `operational rec.*` numerics | any may be `null` | omit that detail line; the row still renders on `productName`/`barcode` |
| `rec.productName` | may be empty | fall back `barcode` → `"Unknown item"` (already done in `OperationalPage.jsx:209`) |
| `dataProvenance.hasSalesHistory` | `false` today | Dashboard must say so on the face of the number, not in a tooltip |
| `storeData.fileName` | `null` unless CSV | omit |
| `connectorStatus.hint` | usually absent | omit |

---

## 6. Callback signatures

Already implemented in `App.jsx`, stable — Malik can wire these today:

```js
onApprove(recommendation)                              // → status 'APPROVED', quantity normalized ≥1
onEditQuantity(recommendation, recommendedOrderQuantity) // number|string; non-finite → 1, rounded, min 1
onReject(recommendation)                               // → status 'REJECTED'

onSelectDemoSource()                    // → Promise<void>
onSelectCsvSource(file)                 // File → Promise<boolean>  — false means the load failed;
                                        //   the caller must clear its file input (DataSourcePage:24-27)
onSelectComaxSource()                   // → Promise<void> — always resolves to an error status (stub)
```

All three recommendation callbacks take the **whole recommendation object**, not an id. They are
fire-and-forget (`void`), they persist through `src/lib/persistence/persistence.js`, and the new
`status` arrives back on the next render via `recommendationOverrides` keyed
`` `${productId}:${type}` ``. **Do not keep local approval state in a page** — read `status` off the
recommendation.

### Done / Dismiss / Snooze (D-1 → Nagham's B-2/B-3) — proposed, not yet implemented

These act on `operationalData.recommendations` (§4), which have no `status` field. Proposed shape,
to be added to `pageProps` in C-2c once Nagham's adapter exists:

```js
onOperationalDone(rec)                  // acted on
onOperationalDismiss(rec, { reason })   // reason: 'wrong_data' | 'not_worth_it' | 'already_handled'
onOperationalSnooze(rec, { untilDays }) // number, default 7
```

Each writes `{ id, type, family, productId|barcode, valueAtStake, decision, reason?, decidedAt }`.
`onOperationalDismiss` **requires** a reason — the button opens the picker, it does not fire without
one. That feedback is the pilot's most valuable output (`malik.md` D-1, `nagham.md` B-3): it tells
us which recommendation types to keep.

Until Nagham's adapter lands, Malik may stub these locally; the signatures above are what will be
passed down, so no rewiring will be needed.

---

## 7. Changing this contract

Whoever needs the change edits this file and says so in the team channel before the code lands.
C-2c (#20) is the issue that makes `pageProps` match this document — "no more, no less".
