# UI Data Contract — `App.jsx` → `src/pages/`

**Owner:** Anas (Track C) · **Consumer:** Malik (Track D) · **Issue:** C-0 (#14)
**Drafted:** 2026-08-02 · **Revised against `main` @ `06c2bf7`:** 2026-08-06

This is an agreement, not a specification. It fixes the one boundary that file-level ownership
cannot protect: `App.jsx` computes, `src/pages/` renders. Neither side changes this boundary
without changing this file first.

**Sign-off**

| | |
|---|---|
| C drafted | ☑ Anas — 2026-08-02, revised 2026-08-06 |
| D agreed | ☐ Malik — _(date: ____)_ |

> The `D agreed` box and the matching `PLAN.md` §7 item 6 box are ticked **only** after Malik
> approves in writing on the PR that lands this file. Neither box may be pre-ticked.

---

## 0. How to read this document

The Track C work that this contract was originally written against lives on
`integration/c-wave`, which is **18 commits ahead of `main` and not merged**. `main` meanwhile
carries 6 commits of Track A and Track D work that `c-wave` does not have. The two lines have
genuinely diverged, and they disagree about things this contract describes.

So every claim below carries a status marker. **Do not build against a marker you have not read.**

| Marker | Meaning |
|:---:|---|
| 🟢 **main** | Implemented and merged into `main` @ `06c2bf7`. Safe to build against today. |
| 🟠 **c-wave** | Implemented on `integration/c-wave` only. **Not on `main`.** Will change behaviour when that branch merges — and merging it is not yet scheduled. |
| 🔵 **planned** | Agreed here, implemented nowhere. Build the shape, expect no data. |
| 🔴 **mismatch** | `main` and this contract, or `main` and `c-wave`, actively disagree. Listed in §9. Needs a decision before it is safe to rely on. |

A page that must work on `main` today should use only 🟢 fields.

---

## 1. Rules

1. `App.jsx` builds **one** `pageProps` object and spreads it into every page:
   `<DashboardPage {...pageProps} />`. Every page receives every prop; a page destructures only
   what it uses.
   *Source of truth:* `src/App.jsx:464-505` on `main` (was `:413` on `c-wave`).
2. **A page never re-derives analytics.** No sales math, no margin math, no status classification
   in `src/pages/`. If a screen needs a number that isn't here, ask for it — don't compute it.
3. **Adding a prop is a contract change.** Whoever needs it edits this file and says so before the
   prop lands. Silent additions are how the tracks drift — §9 is the evidence.
4. Everything is **already sorted and already rounded** by `App.jsx`. Pages format, they don't round.
5. `PlanogramPage` is **out of scope for the pilot** (`PLAN.md` §7 item 2). `planogramItems`,
   `shelfGroups`, `planogramSummary`, `affinitySuggestions`, `affinitySummary` stay in `pageProps`
   and the engines stay in place, unwired. Malik removes the nav entry (D-6); Anas does not delete
   the engine.
6. **The UI may not invent a fact the data does not carry.** If a value is absent, the screen says
   it is absent. It never substitutes `0`, a dash that reads as a measurement, or a plausible
   guess. §6 is the enforceable form of this rule and outranks visual polish.

---

## 2. Canonical entities, identifiers and ownership

| Entity | Canonical shape | Stable identifier | Produced by | Owner |
|---|---|---|---|---|
| `Product` | `src/lib/types.js` | `id` — string, `"ym-<POS item code>"` for real catalog rows | `scripts/normalize-datasets.mjs` → `src/data/demoProducts.js` | Fadi (data), Anas (adapter) |
| `AnalyzedProduct` | `Product` + `.analytics` (§3) | same `id` | `src/lib/analytics/inventoryEngine.js` | Anas |
| `Recommendation` | §4 | `` `${productId}:${type}` `` — see below | `src/lib/analytics/reorderEngine.js` | Anas |
| `OperationalRecommendation` | §5 | `id` — string from the Python exporter | `scripts/export_dashboard_data.py` → `public/data/operational.json` | Fadi |
| `Decision` | §8 | `id` — equals the recommendation `id` it decides | `src/lib/persistence/persistence.js` | Nagham |

**Identifier rules**

- `product.id` is stable across pipeline runs as long as the POS item code is stable. It is **not**
  a barcode; ~300 catalog rows have no barcode at all.
- A recommendation has **no `id` field**. Its identity is the composite
  `` `${productId}:${type}` ``, built by `getRecommendationKey()` in `src/App.jsx`, and that is
  the key `recommendationOverrides` and the persistence layer use. A page must not synthesise its
  own key.
- 🔴 `operationalData.recommendations[].id` **is** a real field, and it is a different namespace
  from the composite key above. The two must never be compared or used interchangeably. See §9.4.
- Never key React lists on array index — the arrays re-sort.

---

## 3. Props each page may use

| Prop | Type | Status | Used by |
|---|---|:---:|---|
| `analyzedProducts` | `AnalyzedProduct[]` (§3.1) | 🟢 main | Products, Dashboard, Report |
| `products` | alias of `analyzedProducts`, same array reference | 🔴 main only — see §9.1 | (none) |
| `recommendations` | `Recommendation[]` (§4) | 🟢 main | Recommendations, Dashboard, Report |
| `approvedOrders` | `Recommendation[]` where `status === 'APPROVED'` | 🟢 main | Recommendations, ApprovedOrders |
| `productIndex` | `Map<string, Product>` — raw (pre-analytics) product by `id` | 🟢 main | Recommendations, ApprovedOrders |
| `operationalData` | `OperationalData` (§5) | 🟢 main | **Operational (home)**, Expiry |
| `operationalStatus` | `'loading' \| 'ready'` | 🟢 main | Operational, Expiry |
| `decisions` | `Record<string, Decision>` keyed by operational rec `id` | 🔴 main only — see §9.2 | Operational |
| `dashboardStats` | `InventorySummary` + `estimatedOrderCost`, `highRiskStockouts`, `reorderSuggestions` | 🟢 main | Dashboard, Report |
| ↳ + `belowCostAlerts`, `priceGapAlerts`, `negativeStockAlerts`, `thinMarginAlerts`, `actionableRecommendations`, `valueAtStake` | | 🟠 c-wave | Dashboard |
| `inventorySummary` | `{ totalProducts, stockoutRisks, lowStock, overstocked, wasteRisk, highPriority, totalSalesLast30Days, estimatedInventoryValue }` | 🟢 main | Dashboard, Report |
| ↳ + `noVelocityData` | | 🟠 c-wave | Dashboard |
| `competitorSummary` | `{ priceLeaderCount, competitorOOSCount, priceProtectionCount, productsWithCoverage }` | 🟢 main | Dashboard, Report |
| `priceLeaderProducts` / `stockoutOpportunities` / `priceProtectionAlerts` | `AnalyzedProduct[]` | 🟢 main | Dashboard, PriceGap |
| `marketContext` | `{ weather, weekend, holiday, localEvent, season, sourceLabel, … }` | 🟢 main | Dashboard, Report |
| `dataProvenance` | `{ catalog, catalogCount, catalogLabel, hasSalesHistory, competitor, competitorStoreCount, liveMarketContext }` | 🟢 main | Dashboard, AppShell |
| ↳ + `salesHistoryCount`, `velocityBreakdown: { none, low, medium, high }` | | 🟠 c-wave | Dashboard |
| `storeData` | `{ products, validationIssues, source, connectorMode, fileName, loadedAt }` | 🟢 main | DataSource |
| `connectorStatus` | `{ state: 'ready'\|'loading'\|'error', message, hint?, mode? }` | 🟢 main | DataSource |
| `planogramItems`, `shelfGroups`, `planogramSummary`, `affinitySuggestions`, `affinitySummary` | — | 🟢 main, **pilot-hidden** (rule 5) | none |

Callbacks are in §8.

### 3.1 The analyzed product

**Analytics are nested under `product.analytics`, not top-level.** This is the single most common
mistake against this contract. `product.margin` is `undefined`; `product.analytics.margin` is the
number. *Source:* `src/lib/analytics/inventoryEngine.js:43-64`.

```js
{
  // canonical fields, top-level (src/lib/types.js)                        🟢 main
  id, name, category, currentStock, shelfQuantity, shelfCapacity,
  salesLast7Days, salesLast30Days, price, cost, expiryDate?,
  supplier, leadTimeDays, returnedUnits, damagedUnits,

  velocityConfidence,          // 'none'|'low'|'medium'|'high'             🟠 c-wave (C-6)

  competitor: { … } | undefined,  // injected by analyzeLocalMarket()      🟢 main

  analytics: {
    avgDailySales7, avgDailySales30, weightedAvgDailySales,  // number     🟢 main
    daysUntilStockout,        // number | null                            🟢 main
    margin,                   // number (₪)                               🟢 main
    marginRate,               // number 0..1  (0.22 = 22%)                🟢 main
    primaryStatus,            // string, display-ready — render as-is      🟢 main
    statuses,                 // string[], display-ready                   🟢 main
    competitorBoost,          // number, 1 = no signal                     🟢 main
    riskScore,                // number 0..100                             🟢 main

    velocityConfidence,       // 'none'|'low'|'medium'|'high'             🟠 c-wave (C-2a)
    hasVelocity,              // boolean                                   🟠 c-wave (C-2a)
  }
}
```

🔴 On `main`, `daysUntilStockout` is `Number.isFinite(x) ? round(x) : null` — it is **not** gated on
having real velocity. On `c-wave` it is additionally gated on `hasVelocity`. The rendered result is
the same today (`null` either way, because there is no sales history), but the guarantee is weaker
on `main`: if partial velocity ever arrives, `main` will emit a number where `c-wave` would emit
`null`. Treat `null` as the only safe assumption.

### 3.2 Inventory status semantics

`primaryStatus` and `statuses` are **already human-readable English**. Render the string; do not map
it through a lookup table, and do not add new status text in `src/pages/`.

| Status string | Meaning | Status |
|---|---|:---:|
| `"Healthy"` | Nothing flagged | 🟢 main |
| `"Low stock"` | Below reorder point | 🟢 main |
| `"Stockout risk"` | Projected to run out inside lead time | 🟢 main |
| `"Overstocked"` | Well above expected cover | 🟢 main |
| `"Slow moving"` | Low velocity relative to stock | 🟢 main |
| `"Near expiry"` | `expiryDate` inside the warning window | 🟢 main |
| `"High priority"` | Composite escalation flag | 🟢 main |
| `"Not enough sales history yet"` | No velocity to judge on | 🟠 c-wave (C-2a) |

🔴 **This is the contract's most consequential open risk.** On `main` there is no
`"Not enough sales history yet"` status and no `hasVelocity` flag, so with a zero-sales catalog
every product falls through to `"Slow moving"` — a claim the data does not support and a direct
violation of rule 6 and of `PLAN.md` §4 ("No product shows 'Slow moving' without real sales history
behind it"). The fix exists on `c-wave` (C-2a) and is **not on `main`**. Until that branch merges,
no screen may present `"Slow moving"` as a finding. See §9.3.

---

## 4. The recommendation

*Source:* `makeRecommendation()`, `src/lib/analytics/reorderEngine.js:157-187` on `main`.

```js
{
  productId, productName, category,     // productName is Hebrew → dir="auto"   🟢 main
  type,                                 // see table below                      🟢 main
  urgency,                              // 'LOW' | 'MEDIUM' | 'HIGH'            🟢 main
  status,                               // 'PENDING'|'APPROVED'|'REJECTED'|'EDITED'  🟢 main
  confidence,                           // number 0..0.95                       🟢 main
  reason,                               // string, display-ready                🟢 main
  explanation,                          // string | undefined (AI layer)        🟢 main
  recommendedOrderQuantity,             // number | undefined — REORDER only    🟢 main
  recommendedShelfQuantity,             // number | undefined — SHELF_* only    🟢 main

  velocityConfidence,                   // 'none'|'low'|'medium'|'high'         🟠 c-wave (C-2b)
  valueAtStake,                         // number (₪)                           🟠 c-wave (C-2b)

  metrics: { currentStock, weightedAvgDailySales, daysUntilStockout,
             safetyStock, leadTimeDays, margin, marginRate, demandMultiplier },  // 🟢 main
  context: { weather, weekend, holiday, localEvent, season },   // each nullable 🟢 main
}
```

### 4.1 Types (enum)

| `type` | Meaning | Status |
|---|---|:---:|
| `REORDER` | Buy more | 🟢 main — **0 emitted** until real velocity |
| `REDUCE_STOCK` | Order less | 🟢 main — 0 emitted |
| `PROMOTION` | Discount / push | 🟢 main — emitted; 🟠 suppressed at `'none'` on c-wave |
| `SHELF_INCREASE` / `SHELF_DECREASE` | Planogram | 🔵 planned — declared in the c-wave enum, not emitted; pilot-hidden |
| `BELOW_COST` | `price < cost` | 🟠 c-wave (C-2b) — ~60 products |
| `PRICE_GAP` | Our price vs. competitor | 🟠 c-wave (C-2b) — from 14,406 barcode matches |
| `NEGATIVE_STOCK` | `currentStock < 0` | 🟠 c-wave (C-2b) — ~625 products |
| `THIN_MARGIN` | `marginRate < 0.20` | 🟠 c-wave (C-2b) — ~232 products |

The canonical enum object is `RECOMMENDATION_TYPES` in `src/lib/analytics/recommendationTypes.js`
— 🟠 **that file exists only on `c-wave`.** On `main` the four types are string literals inside
`reorderEngine.js` and the last four types do not exist at all.

🔴 On `main` today the only type actually emitted in volume is `PROMOTION`. The "2,742 identical
PROMOTION cards" problem that C-2b (#16) fixed is **still present on `main`**.

`urgency` is `'LOW' | 'MEDIUM' | 'HIGH'`. `status` is
`'PENDING' | 'APPROVED' | 'REJECTED' | 'EDITED'`. Both are closed enums; a page must not invent a
member, and must render an unrecognised value as unknown rather than crashing.

### 4.2 Two confidences — do not conflate them

- `confidence` (0..0.95) — how sure the *model* is. 🟢 Exists on `main`.
- `velocityConfidence` — how much *sales history* the number rests on. `'none'` means we have no
  history at all, which is the pilot's starting state and is different from "sold zero".
  🟠 Exists on `c-wave` only.

**A recommendation with `velocityConfidence: 'none'` must never display a velocity claim** — no
"sells 3/day", no "will run out in N days". Show the type's own evidence (price, cost, stock,
competitor price) instead.

🔴 Because `velocityConfidence` does not reach the frontend on `main` at all (§9.3), a page on
`main` cannot check this and must therefore behave as if every recommendation were `'none'`.

### 4.3 Ordering

🟢 On `main`, `recommendations` is sorted by urgency then confidence.
🟠 On `c-wave`, C-2b extends `sortRecommendations()` to sort by ₪ `valueAtStake` first, then urgency.
Pages render in array order and must not re-sort. D-1 shows the top ~20; the rest go behind a filter.

Ordering is **not** part of the stable contract for any other array: treat every other list as
unordered unless this document says otherwise.

---

## 5. `operationalData` — the home screen's data

Loaded from `public/data/operational.json`, a **build artifact** produced by
`npm run data:dashboard`. It is not committed; a clean clone gets `EMPTY_OPERATIONAL_DATA`
(`src/lib/dataAdapters/loadOperationalData.js:5-31`) — every count `0`, every array empty. **That is
a normal state, not an error.** Never render a spinner forever; show the empty state once
`operationalStatus === 'ready'`. 🟢 All of §5 is on `main`.

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
Python exporter passes `None` through unchanged for any column missing in the source row. §6 applies
to all of them.

Competitor prices in this file are **Kaggle 2024 data**. Any screen showing them must date-stamp
them (`malik.md` D-3). Never present a 2024 price as today's price.

### 5.1 Ranking on `main`

🟢 `main` ranks these through `rankActions()` in `src/lib/analytics/actionPriority.js`, which
returns `{ money, data }` — money-impacting actions and data-quality actions, split. It also exports
`ACTION_GROUP`, `credibleLoss()`, `estimateImpact()`, `actionGroup()`, `priorityScore()` and
`totalImpact()`. `OperationalPage` calls it directly.

🔴 This is a **second, parallel prioritisation model** to the `valueAtStake` sort in §4.3, and the
two do not share code, thresholds, or vocabulary. `actionPriority.js` does not exist on `c-wave`.
Merging `c-wave` will put two ranking systems in the same app. See §9.5.

---

## 6. State model — loading, empty, error, stale, partial

Every screen must be able to answer "why is this blank?" without the user guessing.

| State | Trigger | Required render |
|---|---|---|
| **Loading** | `operationalStatus === 'loading'` | Skeleton or spinner **plus** the app shell. Never a blank page. Never longer than the fetch. |
| **Empty (legitimate)** | `operationalStatus === 'ready'` and the relevant array is `[]` | An explicit empty message naming what is empty and why (e.g. "Pipeline has not run yet"). **Not** a spinner, **not** `0` presented as a finding. |
| **Error** | fetch threw, or non-2xx | An honest error with a retry affordance. 🔴 `loadOperationalData()` currently swallows both cases and returns `EMPTY_OPERATIONAL_DATA`, so **a failed fetch is indistinguishable from an empty dataset** — see §9.6. |
| **Stale** | `meta.generatedAt` older than 24h | Render the data **with** its age visible. Competitor prices are Kaggle 2024 and are *always* stale — they must always carry a date. |
| **Partial** | Some fields `null` inside an otherwise valid row | Render the row; omit the missing detail lines. Never drop the whole row for one missing field, and never fill the gap with `0`. |

`operationalStatus` has exactly two members: `'loading'` and `'ready'`. **There is no `'error'`
member** — that is the gap behind §9.6, not an omission in this document.

---

## 7. Nullability — the part that matters most

`analytics.daysUntilStockout` is `null` for **all 7,451 products** right now. A page that assumes a
number prints `null` to a store manager.

**Never render a raw `null`, `undefined`, `NaN`, or `Infinity`. Never render `0` as if it were a
measurement when the truth is "we don't know".**

| Field | Null when | Page must render | Status |
|---|---|---|:---:|
| `analytics.daysUntilStockout` | no velocity (always, today) | `"Not enough sales history yet"` — or `—` in a dense table cell. **Never a number, never `0`, never "∞"** | 🟢 main |
| `analytics.velocityConfidence === 'none'` | always, today | suppress every velocity-derived figure on that row | 🟠 c-wave |
| `analytics.primaryStatus` | never null | render the string as-is | 🟢 main |
| `analytics.margin` / `.marginRate` | never null (`marginRate` is `0` when `price === 0`) | `marginRate === 0` **and** `price === 0` → `"No price on file"`, not `"0%"` | 🟢 main |
| `analytics.riskScore` | never null | safe to render | 🟢 main |
| `product.expiryDate` | usually undefined | `"No expiry recorded"` — the POS does not carry expiry; that gap is what D-2 exists to fill | 🟢 main |
| `product.currentStock` | never null; **can be negative** (625 rows) | negative → `"Stock count wrong (−4)"`, never a plain negative quantity | 🟢 main |
| `recommendation.recommendedOrderQuantity` | `undefined` for every non-`REORDER` type | hide the quantity control entirely; do not default to `1` in the UI | 🟢 main |
| `recommendation.recommendedShelfQuantity` | `undefined` outside `SHELF_*` | hide | 🟢 main |
| `recommendation.explanation` | `undefined` whenever the LLM path is off (**always today**) | fall back to `reason`, which is always present | 🟢 main |
| `recommendation.metrics.daysUntilStockout` | same as above | same as above | 🟢 main |
| `recommendation.context.*` | `null` when live context is off (default) | omit the chip; no "unknown weather" placeholder | 🟢 main |
| `recommendation.valueAtStake` | `0` when not computable | sort last; show no ₪ figure rather than `₪0` | 🟠 c-wave |
| `dashboardStats.valueAtStake` | never null; `0` on a clean clone | `0` is an honest empty state | 🟠 c-wave |
| `dashboardStats.*Alerts` | never null; `0` when none | counts by type | 🟠 c-wave |
| `dashboardStats.reorderSuggestions` | never null; `0` when none | stays `0` until real velocity exists | 🟢 main |
| `dataProvenance.salesHistoryCount` / `velocityBreakdown` | `0` / all-`none` today | `salesHistoryCount === 0` → state "no sales history yet" | 🟠 c-wave |
| `dataProvenance.hasSalesHistory` | `false` today | Dashboard must say so on the face of the number, not in a tooltip | 🟢 main |
| `operationalData.meta.generatedAt` | `null` before first pipeline run | `"Pipeline has not run yet"` | 🟢 main |
| `operationalData.*` counts | `0` on a clean clone | empty state, not a spinner | 🟢 main |
| operational `rec.*` numerics | any may be `null` | omit that detail line; the row still renders on `productName`/`barcode` | 🟢 main |
| operational `rec.productName` | may be empty | fall back `barcode` → `"Unknown item"` | 🟢 main |
| `storeData.fileName` | `null` unless CSV | omit | 🟢 main |
| `connectorStatus.hint` | usually absent | omit | 🟢 main |

**Missing-field rule:** a field absent from the payload is treated exactly as `null`. Pages read
with `?.` and `??`; they never assume presence. Adding a field is backward-compatible, removing or
retyping one is not (§11).

---

## 8. Callback signatures

🟢 All of §8.1 is implemented on `main` and stable — Malik can wire these today.

### 8.1 Recommendation callbacks

```js
onApprove(recommendation)                               // → status 'APPROVED', quantity normalized ≥1
onEditQuantity(recommendation, recommendedOrderQuantity) // number|string; non-finite → 1, rounded, min 1
onReject(recommendation)                                // → status 'REJECTED'

onSelectDemoSource()                    // → Promise<void>
onSelectCsvSource(file)                 // File → Promise<boolean> — false means the load failed;
                                        //   the caller must clear its file input
onSelectComaxSource()                   // → Promise<void> — always resolves to an error status (stub)
```

All three recommendation callbacks take the **whole recommendation object**, not an id. They are
fire-and-forget (`void`), they persist through `src/lib/persistence/persistence.js`, and the new
`status` arrives back on the next render via `recommendationOverrides` keyed
`` `${productId}:${type}` ``. **Do not keep local approval state in a page** — read `status` off the
recommendation.

### 8.2 Operational decisions

🔴 This section was written as 🔵 *planned* and has since been implemented on `main` with a
**different shape**. `main` is authoritative; the proposal below it is superseded.

**As implemented on `main`** (`src/App.jsx:131-140`, `src/components/operational/ActionCard.jsx:61-75`):

```js
onDecide(decision)      // one callback for every outcome — not three
decisions               // Record<operationalRecId, Decision>, prop on pageProps

// the object ActionCard passes:
{ id, status, reason, type, productName, barcode, impactIls }
// App.jsx then adds: { source: 'operational', decidedAt: <ISO string> }
```

A decided recommendation is filtered **out** of the open list by `OperationalPage` via
`!decisions[rec.id]`. `reason` is passed through but is **not enforced** — `ActionCard` can call
`decide(status)` with `reason` undefined.

**Superseded proposal** (kept only so the divergence is legible — do not build against it):

```js
onOperationalDone(rec)
onOperationalDismiss(rec, { reason })   // 'wrong_data'|'not_worth_it'|'already_handled'
onOperationalSnooze(rec, { untilDays })
```

🔴 The dismissal **reason** is what `PLAN.md` §5 and `nagham.md` B-3 grade the pilot on — "which
alert types are worth keeping". `main` collects a free-form optional `reason` rather than the closed
enum this contract specified, and never collects a snooze. That is a real telemetry gap, not a
cosmetic difference. See §9.2.

---

## 9. Known mismatches — decisions required

Each row is one of: **contract decision required** · **implementation follow-up** ·
**integration branch not yet merged** · **intentionally unsupported**.

| # | Mismatch | Evidence | Classification |
|:---:|---|---|---|
| 9.1 | `pageProps.products` is an undocumented alias of `analyzedProducts` | `src/App.jsx:486` | **contract decision required** — keep the alias and document it, or drop it. No page consumes it today. |
| 9.2 | `onDecide` / `decisions` shipped on `main` with a shape this contract did not specify; no enum reason, no snooze | `src/App.jsx:131-140,487-488`; `ActionCard.jsx:61-75` | **contract decision required** — §8.2 now documents `main` as authoritative. Whether to add the reason enum is Malik + Nagham's call (B-3). |
| 9.3 | `velocityConfidence` reaches Parquet but never the frontend on `main`; every product can therefore read as `"Slow moving"` | producer `src/snapshots/velocity.py:353,398,410`; no consumer in `main`'s `src/` or `scripts/` | **integration branch not yet merged** — C-6 + C-2a fix it on `c-wave`. Blocks `PLAN.md` §4 honesty gate. |
| 9.4 | Two id namespaces: composite `` `${productId}:${type}` `` vs operational `rec.id` | `getRecommendationKey()` vs `operational.json` | **implementation follow-up** — documented in §2; no code change needed, but they must never be joined. |
| 9.5 | Two parallel ranking models: `actionPriority.rankActions()` on `main` vs `valueAtStake` sort on `c-wave` | `src/lib/analytics/actionPriority.js` (main only); `reorderEngine.js:320` (c-wave) | **contract decision required** — merging `c-wave` lands both. Pick one before the merge, not after. |
| 9.6 | `loadOperationalData()` returns the empty payload for **both** a failed fetch and a genuinely empty file | `src/lib/dataAdapters/loadOperationalData.js:36-53` | **implementation follow-up** — needs an `'error'` member on `operationalStatus`. Violates §6 as written. |
| 9.7 | `PriceGapPage` exists on `main` but not on `c-wave`; `utils/format.js` + `utils/rtl.js` exist on `c-wave` but not `main` | `git diff origin/main origin/integration/c-wave --stat` | **integration branch not yet merged** — a real merge conflict surface, flagged for whoever runs the integration. |
| 9.8 | The four new recommendation types are contract-agreed but absent from `main` | §4.1 | **integration branch not yet merged** |

**None of these are fixed in this PR.** This issue is documentation only; fixing feature code here
would put `src/App.jsx` in a docs PR and collide with Track C's open work.

---

## 10. Formatting, locale and RTL

| Concern | Rule | Status |
|---|---|:---:|
| **Currency** | `₪` prefix, 2 decimals, thin space: `₪12.90`. Never `NIS`, never a bare number. `App.jsx` rounds; pages format only. | 🟢 main |
| **Quantity** | Integer, no decimals. Negative stock is a data error, not a quantity — render per §7. | 🟢 main |
| **Percentage** | `marginRate` is `0..1`; multiply by 100 at render and append `%` with 0 or 1 decimals. Never render the raw ratio. | 🟢 main |
| **Units** | The POS `יחידת מידה` column is not in the canonical product shape. Do not display a unit you did not receive. | 🟢 main |
| **Dates** | ISO 8601 strings in transit; render as `DD/MM/YYYY` (Israeli convention). | 🟢 main |
| **Timestamps** | `meta.generatedAt` and `decidedAt` are ISO 8601 **UTC** (`new Date().toISOString()`). Render in the **browser's local timezone**; the store is `Asia/Jerusalem`. Never render a raw ISO string, and never assume the string is already local. | 🟢 main |
| **Hebrew text** | `name`, `category`, `supplier`, `productName` are Hebrew. Every element rendering them needs `dir="auto"`. | 🟢 main |
| **Layout direction** | The UI is **English LTR** (`PLAN.md` §7 item 1). No RTL page flip, no i18n. `dir="auto"` is applied per-element, on the text node only. | 🟢 main |
| **Alignment** | Hebrew columns in a table align right; their English headers stay left. Mixed Hebrew/Latin/digit strings need `dir="auto"` on the *innermost* element or the digits reorder. | 🟠 c-wave — helpers in `src/lib/utils/rtl.js` |
| **Sorting** | Hebrew-aware collation via `Intl.Collator('he')`. Naive `<` on Hebrew strings is wrong. | 🟠 c-wave — `src/lib/utils/format.js` |

🔴 The `rtl.js` / `format.js` helpers that C-1a/C-1b built are on `c-wave` only. On `main`, pages
must apply `dir="auto"` by hand.

---

## 11. Compatibility and versioning

- This document is the version marker. It has **no** semver field and `operational.json` carries no
  schema version — 🔴 that is a known gap, worth one line in the exporter if the pilot outlives the
  handover.
- **Backward-compatible** (no sign-off needed): adding an optional field; adding an enum member that
  pages already render defensively; adding a new prop to `pageProps`.
- **Breaking** (needs a new sign-off round): removing a field; changing a field's type; changing a
  status or type string; changing sort order that a page relies on; changing a callback signature.
- Pages must tolerate **unknown enum members** and **extra fields** without crashing. Producers must
  not rely on consumers rejecting them.
- On a breaking change: update this file, get Malik's sign-off again, then land the code. Not the
  other way round.

---

## 12. Representative payloads

### 12.1 Valid — one `AnalyzedProduct` as `main` emits it today

```json
{
  "id": "ym-4213",
  "name": "במבה אסם 80 גרם",
  "category": "חטיפים מלוחים",
  "price": 5.9,
  "cost": 4.1,
  "currentStock": 24,
  "shelfQuantity": 0,
  "shelfCapacity": 10,
  "salesLast7Days": 0,
  "salesLast30Days": 0,
  "supplier": "YomYom",
  "leadTimeDays": 3,
  "returnedUnits": 0,
  "damagedUnits": 0,
  "analytics": {
    "avgDailySales7": 0, "avgDailySales30": 0, "weightedAvgDailySales": 0,
    "daysUntilStockout": null,
    "margin": 1.8, "marginRate": 0.31,
    "primaryStatus": "Slow moving",
    "statuses": ["Slow moving"],
    "competitorBoost": 1, "riskScore": 12
  }
}
```

Note `"primaryStatus": "Slow moving"` on zero sales history — §3.2's 🔴 risk, reproduced from real
output rather than hypothesised.

### 12.2 Degraded — a row where almost everything is missing

```json
{
  "id": "ym-9987",
  "name": "",
  "category": null,
  "price": 0,
  "cost": 0,
  "currentStock": -4,
  "salesLast7Days": 0,
  "salesLast30Days": 0,
  "supplier": "YomYom",
  "leadTimeDays": 3,
  "analytics": {
    "avgDailySales7": 0, "avgDailySales30": 0, "weightedAvgDailySales": 0,
    "daysUntilStockout": null,
    "margin": 0, "marginRate": 0,
    "primaryStatus": "Slow moving", "statuses": ["Slow moving"],
    "competitorBoost": 1, "riskScore": 0
  }
}
```

Required render: name → `"Unknown item"`; `marginRate` → `"No price on file"` (not `"0%"`);
`currentStock` → `"Stock count wrong (−4)"`; `daysUntilStockout` → `"Not enough sales history yet"`.
The row still renders — §6 partial-data rule.

### 12.3 Degraded — `operationalData` on a clean clone

```json
{
  "meta": { "generatedAt": null, "status": "unavailable", "competitorSignals": 0,
            "competitorRecommendations": 0, "scrapingStatus": "not_started" },
  "posHealth": { "totalProducts": 0, "missingBarcode": 0, "zeroPrice": 0, "zeroCost": 0,
                 "negativeStock": 0, "woltPriceGaps": 0, "marginRisks": 0, "sourceFile": null },
  "expiry": { "totalScans": 0, "actionable": 0,
              "buckets": { "expired": 0, "critical_7d": 0, "warning_14d": 0,
                           "upcoming_30d": 0, "later": 0 }, "alerts": [] },
  "byType": {}, "byFamily": {}, "sources": [], "recommendations": []
}
```

Required render: `"Pipeline has not run yet"` once `operationalStatus === 'ready'`.
🔴 This is byte-identical to what a **failed fetch** produces — §9.6.

---

## 13. Which pages consume which parts

| Page | File | Consumes | Runs on `main` today |
|---|---|---|:---:|
| Operational (home) | `src/pages/OperationalPage.jsx` | `operationalData`, `operationalStatus`, `decisions`, `onDecide` | ✅ |
| Expiry | `src/pages/ExpiryPage.jsx` | `operationalData.expiry` | ✅ |
| Products | `src/pages/ProductsPage.jsx` | `analyzedProducts` | ✅ |
| Recommendations | `src/pages/RecommendationsPage.jsx` | `recommendations`, `approvedOrders`, `productIndex`, `onApprove`/`onEditQuantity`/`onReject` | ✅ |
| Dashboard | `src/pages/DashboardPage.jsx` | `dashboardStats`, `inventorySummary`, `competitorSummary`, `dataProvenance`, `marketContext` | ✅ |
| Price gap | `src/pages/PriceGapPage.jsx` | `priceLeaderProducts`, `priceProtectionAlerts`, `stockoutOpportunities` | ✅ **main only** — absent from `c-wave` |
| Report | `src/pages/ReportPage.jsx` | `analyzedProducts`, `recommendations`, `dashboardStats`, `marketContext` | ✅ |
| Approved orders | `src/pages/ApprovedOrdersPage.jsx` | `approvedOrders`, `productIndex` | ✅ |
| Data source | `src/pages/DataSourcePage.jsx` | `storeData`, `connectorStatus`, `onSelect*Source` | ✅ |
| Planogram | `src/pages/PlanogramPage.jsx` | planogram props | ⛔ pilot-hidden (rule 5) |

### 13.1 Producer → consumer map

| Contract area | Producer (exact path) | Consumer (exact path) | Status |
|---|---|---|---|
| Product catalog | `scripts/normalize-datasets.mjs` → `src/data/demoProducts.js` | `src/lib/dataAdapters/loadDemoStoreData.js` | **main** |
| Inventory state | `src/lib/analytics/inventoryEngine.js:43-64` | `src/pages/ProductsPage.jsx`, `DashboardPage.jsx` | **main** |
| Inventory state — `"Not enough sales history yet"`, `hasVelocity` | `src/lib/analytics/inventoryEngine.js` (c-wave) | same | **integration-only** |
| Inventory summary | `src/lib/analytics/inventoryEngine.js` `summarizeInventory()` | `DashboardPage.jsx`, `ReportPage.jsx` | **main** |
| Inventory summary — `noVelocityData` | `inventoryEngine.js` (c-wave) | `DashboardPage.jsx` | **integration-only** |
| Recommendation type — `REORDER`/`REDUCE_STOCK`/`PROMOTION` | `src/lib/analytics/reorderEngine.js:83,95,106,115` | `src/pages/RecommendationsPage.jsx` | **main** |
| Recommendation type — `BELOW_COST`/`PRICE_GAP`/`NEGATIVE_STOCK`/`THIN_MARGIN` | `src/lib/analytics/recommendationTypes.js` (c-wave) | `RecommendationsPage.jsx`, `DashboardPage.jsx` | **integration-only** |
| Velocity (`velocity_confidence`) — Python side | `src/snapshots/velocity.py:353,398,410` | *(none — stops at Parquet)* | **main, unconsumed** |
| Velocity passthrough to JS | `scripts/normalize-datasets.mjs` (c-wave, C-6) | `inventoryEngine.js`, `reorderEngine.js` | **integration-only** |
| Confidence — `confidence` (model) | `src/lib/analytics/reorderEngine.js:166` | `RecommendationsPage.jsx` | **main** |
| Confidence — `velocityConfidence` (data) | `reorderEngine.js:212,222` (c-wave) | `RecommendationsPage.jsx` | **integration-only** |
| `valueAtStake` (per rec + dashboard total) | `reorderEngine.js:223`, `App.jsx:503-520` (c-wave) | `DashboardPage.jsx` | **integration-only** |
| Operational recommendations | `scripts/export_dashboard_data.py` → `public/data/operational.json` | `src/lib/dataAdapters/loadOperationalData.js` → `OperationalPage.jsx` | **main** |
| Operational ranking | `src/lib/analytics/actionPriority.js` `rankActions()` | `src/pages/OperationalPage.jsx:53` | **main only** |
| Decisions / telemetry | `src/App.jsx:131-140` → `src/lib/persistence/persistence.js` | `src/pages/OperationalPage.jsx:43-66`, `ActionCard.jsx:61-75` | **main only** |
| Competitor prices | `src/data/marketData.js` (from `data/matching/barcode_matches.parquet`) | `src/lib/analytics/competitorEngine.js` → `PriceGapPage.jsx` | **main** |
| Hebrew formatting / collation | `src/lib/utils/format.js`, `src/lib/utils/rtl.js` (c-wave) | all pages | **integration-only** |
| Expiry | `scripts/export_dashboard_data.py` → `operationalData.expiry` | `src/pages/ExpiryPage.jsx` | **main** |

---

## 14. Changing this contract

Whoever needs the change edits this file and says so in the team channel before the code lands.
A breaking change (§11) needs a fresh sign-off from Malik; a compatible one does not.

`main` is the reference for "what exists". `integration/c-wave` is the reference for "what Track C
built and has not landed". When those two disagree, this document says so explicitly rather than
picking a winner — resolving §9 is a team decision, not a documentation one.
