# UI Data Contract — `App.jsx` → `src/pages/`

**Owner:** Anas (Track C) · **Consumer:** Malik (Track D) · **Issue:** C-0 (#14)
**Drafted:** 2026-08-02 · **Revised against `main` @ `67e7ba0`:** 2026-08-06

This is an agreement, not a specification. It fixes the one boundary that file-level ownership
cannot protect: `App.jsx` computes, `src/pages/` renders. Neither side changes this boundary
without changing this file first.

**Sign-off**

| | |
|---|---|
| C drafted | ☑ Anas — 2026-08-02, revised 2026-08-06 |
| D agreed | ☑ **Project-owner override** — Anas, 2026-08-06 (PR #35) |

> **This was not signed off by Malik.** D-0b asked for Malik's written agreement; a review was
> requested from `@malekdi` on PR #35 and none was given. Anas, as Track C owner, authorized this
> revision as the UI implementation baseline without it, and the `PLAN.md` §7 item 6 box was ticked
> on that basis.
>
> What that costs: §9 lists the open mismatches, two classified *contract decision required*
> (§9.1, §9.2). Those are precisely the questions a Track D review would have answered, and they
> are still open. Treat §9 as unreviewed by its consumer.

---

## 0. How to read this document

`integration/c-wave` **has now been merged into `main`** (PR #36, merge `67e7ba0`). Everything
Track C built in slots 0–2 — the four new recommendation types, `velocityConfidence`, the honest
inventory states, the Hebrew helpers — is on `main` as of this revision. An earlier revision of this
document described that work as unmerged; that is no longer true and the markers below have been
re-verified against `67e7ba0`.

Every claim still carries a status marker. **Do not build against a marker you have not read.**

| Marker | Meaning |
|:---:|---|
| 🟢 **main** | Implemented and merged into `main` @ `67e7ba0`. Safe to build against today. |
| 🔵 **planned** | Agreed here, implemented nowhere. Build the shape, expect no data. |
| 🔴 **mismatch** | `main` and this contract actively disagree, or `main` disagrees with itself. Listed in §9. Needs a decision before it is safe to rely on. |

The merge kept **both** sides wholesale — Track C's engines *and* Track D's `actionPriority.js` /
`PriceGapPage.jsx` / `ActionCard.jsx`. That resolved most of the old divergence but created one new
problem: two prioritisation models now ship side by side (§9.5).

---

## 1. Rules

1. `App.jsx` builds **one** `pageProps` object and spreads it into every page:
   `<DashboardPage {...pageProps} />`. Every page receives every prop; a page destructures only
   what it uses. *Source of truth:* `src/App.jsx:490-531`.
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
| `AnalyzedProduct` | `Product` + `.analytics` (§3.1) | same `id` | `src/lib/analytics/inventoryEngine.js` | Anas |
| `Recommendation` | §4 | `` `${productId}:${type}` `` — see below | `src/lib/analytics/reorderEngine.js` | Anas |
| `OperationalRecommendation` | §5 | `id` — string from the Python exporter | `scripts/export_dashboard_data.py` → `public/data/operational.json` | Fadi |
| `Decision` | §8.2 | `id` — equals the operational recommendation `id` it decides | `src/lib/persistence/persistence.js` | Nagham |

**Identifier rules**

- `product.id` is stable across pipeline runs as long as the POS item code is stable. It is **not**
  a barcode; ~300 catalog rows have no barcode at all.
- A `Recommendation` has **no `id` field**. Its identity is the composite
  `` `${productId}:${type}` ``, built by `getRecommendationKey()` in `src/App.jsx`, and that is the
  key `recommendationOverrides` and the persistence layer use. A page must not synthesise its own key.
- 🔴 `operationalData.recommendations[].id` **is** a real field, and it is a different namespace
  from the composite key above. The two must never be compared or used interchangeably. See §9.4.
- Never key React lists on array index — the arrays re-sort.

---

## 3. Props each page may use

| Prop | Type | Status | Used by |
|---|---|:---:|---|
| `analyzedProducts` | `AnalyzedProduct[]` (§3.1) | 🟢 main | Products, Dashboard, Report |
| `products` | alias of `analyzedProducts`, same array reference | 🔴 see §9.1 | (no page) |
| `recommendations` | `Recommendation[]` (§4) | 🟢 main | Recommendations, Dashboard, Report |
| `approvedOrders` | `Recommendation[]` where `status === 'APPROVED'` | 🟢 main | Recommendations, ApprovedOrders |
| `productIndex` | `Map<string, Product>` — raw (pre-analytics) product by `id` | 🟢 main | Recommendations, ApprovedOrders |
| `operationalData` | `OperationalData` (§5) | 🟢 main | **Operational (home)**, Expiry |
| `operationalStatus` | `'loading' \| 'ready'` | 🟢 main | Operational, Expiry |
| `decisions` | `Record<operationalRecId, Decision>` | 🟢 main — shape differs from §8.2's original proposal, see §9.2 | Operational |
| `dashboardStats` | `InventorySummary` + `estimatedOrderCost`, `highRiskStockouts`, `reorderSuggestions`, `belowCostAlerts`, `priceGapAlerts`, `negativeStockAlerts`, `thinMarginAlerts`, `actionableRecommendations`, `productValueAtStake` | 🟢 main | Dashboard, Report |
| `inventorySummary` | `{ totalProducts, stockoutRisks, lowStock, overstocked, wasteRisk, highPriority, totalSalesLast30Days, estimatedInventoryValue, noVelocityData }` | 🟢 main | Dashboard, Report |
| `competitorSummary` | `{ priceLeaderCount, competitorOOSCount, priceProtectionCount, productsWithCoverage }` | 🟢 main | Dashboard, Report |
| `priceLeaderProducts` / `stockoutOpportunities` / `priceProtectionAlerts` | `AnalyzedProduct[]` | 🟢 main | Dashboard, PriceGap |
| `marketContext` | `{ weather, weekend, holiday, localEvent, season, sourceLabel, … }` | 🟢 main | Dashboard, Report |
| `dataProvenance` | `{ catalog, catalogCount, catalogLabel, hasSalesHistory, salesHistoryCount, velocityBreakdown, competitor, competitorStoreCount, liveMarketContext }` | 🟢 main | Dashboard, AppShell |
| `storeData` | `{ products, validationIssues, source, connectorMode, fileName, loadedAt }` | 🟢 main | DataSource |
| `connectorStatus` | `{ state: 'ready'\|'loading'\|'error', message, hint?, mode? }` | 🟢 main | DataSource |
| `planogramItems`, `shelfGroups`, `planogramSummary`, `affinitySuggestions`, `affinitySummary` | — | 🟢 main, **pilot-hidden** (rule 5) | none |

Callbacks are in §8.

### 3.1 The analyzed product

**Analytics are nested under `product.analytics`, not top-level.** This is the single most common
mistake against this contract. `product.margin` is `undefined`; `product.analytics.margin` is the
number. *Source:* `src/lib/analytics/inventoryEngine.js:54-75`.

```js
{
  // canonical fields, top-level (src/lib/types.js)                        🟢 main
  id, name, category, currentStock, shelfQuantity, shelfCapacity,
  salesLast7Days, salesLast30Days, price, cost, expiryDate?,
  supplier, leadTimeDays, returnedUnits, damagedUnits,

  velocityConfidence,          // 'none'|'low'|'medium'|'high'             🟢 main

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
    velocityConfidence,       // 'none'|'low'|'medium'|'high'             🟢 main
    hasVelocity,              // boolean                                   🟢 main
  }
}
```

`daysUntilStockout` is now gated on `hasVelocity` (`inventoryEngine.js:36-39`): with no sales
history it is `null`, never a number. Treat `null` as the normal case.

### 3.2 Inventory status semantics

`primaryStatus` and `statuses` are **already human-readable English**. Render the string; do not map
it through a lookup table, and do not add new status text in `src/pages/`.

| Status string | Meaning | Status |
|---|---|:---:|
| `"High priority"` | Composite escalation flag | 🟢 main |
| `"Stockout risk"` | Projected to run out inside lead time | 🟢 main |
| `"Near expiry"` | `expiryDate` inside the warning window | 🟢 main |
| `"Low stock"` | Below reorder point | 🟢 main |
| `"Overstocked"` | Well above expected cover | 🟢 main |
| `"Slow moving"` | Low velocity relative to stock — **requires real velocity** | 🟢 main |
| `"Not enough sales history yet"` | No velocity to judge on | 🟢 main |
| `"Healthy"` | Nothing flagged, and we have velocity to say so | 🟢 main |

The table is in `pickPrimaryStatus()` precedence order (`inventoryEngine.js:126-140`).

**This was the contract's biggest risk and it is now closed.** Every velocity-derived status is
gated on `hasVelocity` (`inventoryEngine.js:36-39`), and `"Not enough sales history yet"` ranks
above `"Healthy"` — so a zero-sales catalog reports honestly instead of labelling all 7,451 products
`"Slow moving"`. That satisfies the `PLAN.md` §4 honesty gate. Before PR #36 it did not.

Product `name`, `category` and `supplier` are Hebrew. Every element rendering them needs
`dir="auto"` (§10).

---

## 4. The recommendation

*Source:* `makeRecommendation()`, `src/lib/analytics/reorderEngine.js:210-230`.

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
  velocityConfidence,                   // 'none'|'low'|'medium'|'high'         🟢 main
  valueAtStake,                         // number (₪)                           🟢 main

  metrics: { currentStock, weightedAvgDailySales, daysUntilStockout,
             safetyStock, leadTimeDays, margin, marginRate, demandMultiplier },  // 🟢 main
  context: { weather, weekend, holiday, localEvent, season },   // each nullable 🟢 main
}
```

### 4.1 Types (enum)

Canonical enum: `RECOMMENDATION_TYPES` in `src/lib/analytics/recommendationTypes.js` 🟢 main.

| `type` | Meaning | Status |
|---|---|:---:|
| `REORDER` | Buy more | 🟢 main — **0 emitted** until real velocity |
| `REDUCE_STOCK` | Order less | 🟢 main — 0 emitted; suppressed at `velocityConfidence: 'none'` |
| `PROMOTION` | Discount / push | 🟢 main — suppressed at `'none'` |
| `SHELF_INCREASE` / `SHELF_DECREASE` | Planogram | 🔵 planned — in the enum, not emitted; pilot-hidden |
| `BELOW_COST` | `price < cost` | 🟢 main — ~60 products |
| `PRICE_GAP` | Our price vs. competitor | 🟢 main — from 14,406 barcode matches |
| `NEGATIVE_STOCK` | `currentStock < 0` | 🟢 main — ~625 products |
| `THIN_MARGIN` | `marginRate < 0.20` | 🟢 main — ~232 products |
| `ASSORTMENT_GAP` | Competitors carry it, we don't | 🟢 main — from 156 comparable branches |

#### `ASSORTMENT_GAP` is the one type about a product we do not stock

Every other type describes something already on our shelves. This one does not, and
three fields behave differently as a result:

- **`productId` is a competitor barcode**, not one of our product ids. There is no
  matching row in `products`, so a page must not try to look one up.
- **`metrics` is `null`.** Every field in the block — `currentStock`,
  `weightedAvgDailySales`, `daysUntilStockout`, `margin` — is about a product we
  carry. Emitting zeros there would read as measured facts about a real shelf.
  Read `evidence` instead: `branchesCarrying`, `branchesCompared`, `coverageRatio`,
  `competitorPriceMedian`, `priceBand`.
- **`velocityConfidence` is always `'none'`, permanently.** We have never sold these
  products, so §4.2 binds absolutely: no units per day, no days-until-stockout, no
  projected revenue. The only honest evidence is branch coverage and the competitor's
  price.

`confidence` is capped at **0.7**. One snapshot proves competitors stock a product;
it never proves the product sells.

Two extra fields ride along, both optional:

- **`segments`** — what kind of product this is (`alcohol`, `tobacco`, `pork`,
  `high_ticket`, …), from `configs/product_segments.yaml`. A tag, never a judgement.
  Whether a store carries a segment is decided per store in `configs/store_policy.yaml`
  and **defaults to carrying everything**; SmartShelf must work for a shop that sells
  alcohol and one that refuses it, with neither treated as the normal case.
- **`reviewRequired`** — segments matched by an ambiguous keyword rule. Hebrew has no
  regex-safe word boundaries, so e.g. `ארק` also matches `טונה סטארקיסט`. These are
  surfaced for a human rather than acted on, and are resolved by the per-product
  classification in issue #51.

*Produced by* `scripts/build_assortment_gap.py` → `scripts/export_assortment_gap.py`
→ `public/data/assortment_gap.json`.

Ranked by **branch coverage alone**. A margin-weighted ranker was built and measured
against it (`scripts/measure_gap_ranking.py`) and lost decisively — it surfaced 0%
convenience-band items against the baseline's 90%, because without sales history an
assumed margin is not evidence of anything, while coverage across 156 comparable
branches is.

`urgency` is `'LOW' | 'MEDIUM' | 'HIGH'`. `status` is
`'PENDING' | 'APPROVED' | 'REJECTED' | 'EDITED'`. Both are closed enums; a page must not invent a
member, and must render an unrecognised value as unknown rather than crashing.

### 4.2 Two confidences — do not conflate them

- `confidence` (0..0.95) — how sure the *model* is.
- `velocityConfidence` — how much *sales history* the number rests on. `'none'` means we have no
  history at all, which is the pilot's starting state and is different from "sold zero".

Both are 🟢 on `main`.

**A recommendation with `velocityConfidence: 'none'` must never display a velocity claim** — no
"sells 3/day", no "will run out in N days". Show the type's own evidence (price, cost, stock,
competitor price) instead. Today that is *every* recommendation, because the POS export carries no
sales history.

### 4.3 Ordering

🟢 `recommendations` arrives sorted by ₪ `valueAtStake` first, then urgency
(`reorderEngine.js`). Pages render in array order and must not re-sort. D-1 shows the top ~20;
the rest go behind a filter.

🟢 **Ranking authority (resolved #39).** Per-sale defensible impact — `actionPriority.js`
(§5.1) — is the authoritative definition of "most important". `valueAtStake` is a compatible
*exposure* view (per-unit signal × stock), not a competing one: as of #39 both run through the
**same credibility guards** (`src/lib/analytics/credibility.js`: `credibleLoss` / `credibleGap`,
thresholds `MIN_CREDIBLE_PRICE` / `MAX_CREDIBLE_GAP_PCT` / `MAX_CREDIBLE_COST_RATIO`). So
`valueAtStake` can never state a loss or gap the action list would refuse (a per-case cost
recorded against a per-unit price is withheld in both), and a negative-stock item carries **no**
₪ in either surface. When a guard withholds, `valueAtStake` is `0` (sort last, show no figure) —
the alert itself still appears.

Ordering is **not** part of the stable contract for any other array: treat every other list as
unordered unless this document says otherwise.

---

## 5. `operationalData` — the home screen's data

Loaded from `public/data/operational.json`, a **build artifact** produced by
`npm run data:dashboard`. It is not committed; a clean clone gets `EMPTY_OPERATIONAL_DATA`
(`src/lib/dataAdapters/loadOperationalData.js:5-33`) — every count `0`, every array empty. **That is
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
Python exporter passes `None` through unchanged for any column missing in the source row. §7 applies
to all of them.

Competitor prices in this file are **Kaggle 2024 data**. Any screen showing them must date-stamp
them (`malik.md` D-3). Never present a 2024 price as today's price.

### 5.1 Ranking

🟢 `OperationalPage` ranks these through `rankActions()` in `src/lib/analytics/actionPriority.js`,
which returns `{ money, data }` — money-impacting actions and data-quality actions, split. It also
exports `ACTION_GROUP`, `credibleLoss()`, `estimateImpact()`, `actionGroup()`, `priorityScore()` and
`totalImpact()`.

🟢 **Authoritative (resolved #39).** `rankActions()` — defensible ₪-per-sale impact with the
credibility guards, and the deliberate money/data split — is the pilot's committed definition of
"most important". This is the surface the store manager works top-down, so it wins where the two
could disagree. It is *not* a rival to `valueAtStake` (§4.3): as of #39 the guards themselves live
in the shared `credibility.js` and are applied by both, so `credibleLoss()` here and the
`valueAtStake` exposure figure never contradict each other on whether a loss/gap is real. The
vocabularies still differ by design — `actionPriority` runs on the real `operationalData` types
(`CHECK_MARGIN`, `CHECK_WOLT_PRICE_GAP`, …), `reorderEngine` on the demo/reorder types
(`BELOW_COST`, `PRICE_GAP`, …) — but they no longer disagree about what is defensible.

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

All rows below are 🟢 on `main` unless marked.

| Field | Null when | Page must render |
|---|---|---|
| `analytics.daysUntilStockout` | no velocity (always, today) | `"Not enough sales history yet"` — or `—` in a dense table cell. **Never a number, never `0`, never "∞"** |
| `analytics.velocityConfidence === 'none'` | always, today | suppress every velocity-derived figure on that row |
| `analytics.hasVelocity === false` | always, today | same; this is the boolean form of the line above |
| `analytics.primaryStatus` | never null | render the string as-is |
| `analytics.margin` / `.marginRate` | never null (`marginRate` is `0` when `price === 0`) | `marginRate === 0` **and** `price === 0` → `"No price on file"`, not `"0%"` |
| `analytics.riskScore` | never null | safe to render |
| `product.expiryDate` | usually undefined | `"No expiry recorded"` — the POS does not carry expiry; that gap is what D-2 exists to fill |
| `product.currentStock` | never null; **can be negative** (625 rows) | negative → `"Stock count wrong (−4)"`, never a plain negative quantity |
| `recommendation.recommendedOrderQuantity` | `undefined` for every non-`REORDER` type | hide the quantity control entirely; do not default to `1` in the UI |
| `recommendation.recommendedShelfQuantity` | `undefined` outside `SHELF_*` | hide |
| `recommendation.explanation` | `undefined` whenever the LLM path is off (**always today**) | fall back to `reason`, which is always present |
| `recommendation.metrics.daysUntilStockout` | same as above | same as above |
| `recommendation.context.*` | `null` when live context is off (default) | omit the chip; no "unknown weather" placeholder |
| `recommendation.valueAtStake` | `0` when not computable **or withheld by a credibility guard (#39)** | sort last; show no ₪ figure rather than `₪0` |
| `dashboardStats.productValueAtStake` | never null; `0` on a clean clone | renamed from `valueAtStake` (#30); **deduplicated per-product** net exposure — each product counted once by its greatest single-signal value. `0` is an honest empty state |
| `dashboardStats.*Alerts` | never null; `0` when none | counts of live (non-rejected) recommendations by type |
| `dashboardStats.reorderSuggestions` | never null; `0` when none | stays `0` until real velocity exists |
| `inventorySummary.noVelocityData` | never null; equals `totalProducts` today | the count behind "we cannot judge these yet" |
| `dataProvenance.salesHistoryCount` / `velocityBreakdown` | `0` / all-`none` today | `salesHistoryCount === 0` → state "no sales history yet"; `velocityBreakdown` is the per-band product count behind that claim |
| `dataProvenance.hasSalesHistory` | `false` today | Dashboard must say so on the face of the number, not in a tooltip |
| `operationalData.meta.generatedAt` | `null` before first pipeline run | `"Pipeline has not run yet"` |
| `operationalData.*` counts | `0` on a clean clone | empty state, not a spinner |
| operational `rec.*` numerics | any may be `null` | omit that detail line; the row still renders on `productName`/`barcode` |
| operational `rec.productName` | may be empty | fall back `barcode` → `"Unknown item"` |
| `storeData.fileName` | `null` unless CSV | omit |
| `connectorStatus.hint` | usually absent | omit |

**Missing-field rule:** a field absent from the payload is treated exactly as `null`. Pages read
with `?.` and `??`; they never assume presence. Adding a field is backward-compatible, removing or
retyping one is not (§11).

---

## 8. Callback signatures

### 8.1 Recommendation callbacks

🟢 Implemented on `main` and stable.

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

🔴 This section was originally written as *planned* with three callbacks. It shipped on `main` with a
**different shape**. `main` is authoritative; the proposal below it is superseded.

**As implemented** (`src/App.jsx:133-140`, `src/components/operational/ActionCard.jsx:61-75`):

```js
onDecide(decision)      // one callback for every outcome — not three     🟢 main
decisions               // Record<operationalRecId, Decision>              🟢 main

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
**intentionally unsupported**.

| # | Mismatch | Evidence | Classification |
|:---:|---|---|---|
| 9.1 | `pageProps.products` is an undocumented alias of `analyzedProducts`; no page consumes it | `src/App.jsx:512` | **contract decision required** — keep and document, or drop. |
| 9.2 | `onDecide` / `decisions` shipped with a shape this contract did not specify; no reason enum, no snooze | `src/App.jsx:133-140,512-514`; `ActionCard.jsx:61-75` | **contract decision required** — §8.2 documents `main` as authoritative. Whether to add the closed reason enum is Malik + Nagham's call (B-3). |
| 9.4 | Two id namespaces: composite `` `${productId}:${type}` `` vs operational `rec.id` | `getRecommendationKey()` vs `operational.json` | **implementation follow-up** — documented in §2; no code change needed, but they must never be joined. |
| 9.5 | Two parallel ranking models now ship together: `actionPriority.rankActions()` and the `valueAtStake` sort | `src/lib/analytics/actionPriority.js` + `OperationalPage.jsx`; `reorderEngine.js` | **resolved #39** — `actionPriority` (per-sale defensible impact) is authoritative (§4.3, §5.1); the credibility guards now live in shared `credibility.js` and are applied by both, so `valueAtStake` can no longer state a figure the action list would refuse. Vocabularies stay distinct by design; the *defensibility* judgement is shared. |
| 9.6 | `loadOperationalData()` returns the empty payload for **both** a failed fetch and a genuinely empty file | `src/lib/dataAdapters/loadOperationalData.js:35-54` | **implementation follow-up** — needs an `'error'` member on `operationalStatus`. Violates §6 as written. |

### Resolved by PR #36 (kept for audit)

| # | Was | Now |
|:---:|---|---|
| 9.3 | `velocityConfidence` reached Parquet but never the frontend, so every product read as `"Slow moving"` | **Resolved.** `scripts/normalize-datasets.mjs:96` passes it through; `inventoryEngine.js:36-39` gates every velocity status on `hasVelocity`. |
| 9.7 | `PriceGapPage` on `main` only; `format.js`/`rtl.js` on `c-wave` only | **Resolved.** The merge kept both sides. |
| 9.8 | The four new recommendation types were absent from `main` | **Resolved.** `recommendationTypes.js` is on `main`. |

**None of the open mismatches are fixed in this PR.** This issue is documentation only; fixing them
would put `src/App.jsx` in a docs PR.

---

## 10. Formatting, locale and RTL

All 🟢 on `main`; the helpers live in `src/lib/utils/format.js` and `src/lib/utils/rtl.js`.

| Concern | Rule |
|---|---|
| **Currency** | `₪` prefix, 2 decimals: `₪12.90`. Never `NIS`, never a bare number. `App.jsx` rounds; pages format only. |
| **Quantity** | Integer, no decimals. Negative stock is a data error, not a quantity — render per §7. |
| **Percentage** | `marginRate` is `0..1`; multiply by 100 at render and append `%` with 0 or 1 decimals. Never render the raw ratio. |
| **Units** | The POS `יחידת מידה` column is not in the canonical product shape. Do not display a unit you did not receive. |
| **Dates** | ISO 8601 strings in transit; render as `DD/MM/YYYY` (Israeli convention). |
| **Timestamps** | `meta.generatedAt` and `decidedAt` are ISO 8601 **UTC** (`new Date().toISOString()`). Render in the **browser's local timezone**; the store is `Asia/Jerusalem`. Never render a raw ISO string, and never assume the string is already local. |
| **Hebrew text** | `name`, `category`, `supplier`, `productName` are Hebrew. Every element rendering them needs `dir="auto"`. |
| **Layout direction** | The UI is **English LTR** (`PLAN.md` §7 item 1). No RTL page flip, no i18n. `dir="auto"` is applied per-element, on the text node only. |
| **Alignment** | Hebrew columns in a table align right; their English headers stay left. Mixed Hebrew/Latin/digit strings need `dir="auto"` on the *innermost* element or the digits reorder. |
| **Sorting** | Hebrew-aware collation via `Intl.Collator('he')`. Naive `<` on Hebrew strings is wrong. |

---

## 11. Compatibility and versioning

- This document is the version marker. It has **no** semver field and `operational.json` carries no
  schema version — 🔴 a known gap, worth one line in the exporter if the pilot outlives the handover.
- **Backward-compatible** (no sign-off needed): adding an optional field; adding an enum member that
  pages already render defensively; adding a new prop to `pageProps`.
- **Breaking** (needs a new sign-off round): removing a field; changing a field's type; changing a
  status or type string; changing sort order that a page relies on; changing a callback signature.
- Pages must tolerate **unknown enum members** and **extra fields** without crashing. Producers must
  not rely on consumers rejecting them.
- On a breaking change: update this file, get sign-off, then land the code. Not the other way round.

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
  "velocityConfidence": "none",
  "analytics": {
    "avgDailySales7": 0, "avgDailySales30": 0, "weightedAvgDailySales": 0,
    "daysUntilStockout": null,
    "margin": 1.8, "marginRate": 0.31,
    "primaryStatus": "Not enough sales history yet",
    "statuses": ["Not enough sales history yet"],
    "competitorBoost": 1, "riskScore": 12,
    "velocityConfidence": "none", "hasVelocity": false
  }
}
```

Note `primaryStatus` — before PR #36 this same row reported `"Slow moving"`. That is the honesty
fix §3.2 describes, shown against a real product.

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
  "velocityConfidence": "none",
  "analytics": {
    "avgDailySales7": 0, "avgDailySales30": 0, "weightedAvgDailySales": 0,
    "daysUntilStockout": null,
    "margin": 0, "marginRate": 0,
    "primaryStatus": "Not enough sales history yet",
    "statuses": ["Not enough sales history yet"],
    "competitorBoost": 1, "riskScore": 0,
    "velocityConfidence": "none", "hasVelocity": false
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

| Page | File | Consumes |
|---|---|---|
| Operational (home) | `src/pages/OperationalPage.jsx` | `operationalData`, `operationalStatus`, `decisions`, `onDecide` |
| Expiry | `src/pages/ExpiryPage.jsx` | `operationalData.expiry` |
| Products | `src/pages/ProductsPage.jsx` | `analyzedProducts` |
| Recommendations | `src/pages/RecommendationsPage.jsx` | `recommendations`, `approvedOrders`, `productIndex`, `onApprove`/`onEditQuantity`/`onReject` |
| Dashboard | `src/pages/DashboardPage.jsx` | `dashboardStats`, `inventorySummary`, `competitorSummary`, `dataProvenance`, `marketContext` |
| Price gap | `src/pages/PriceGapPage.jsx` | `priceLeaderProducts`, `priceProtectionAlerts`, `stockoutOpportunities` |
| Report | `src/pages/ReportPage.jsx` | `analyzedProducts`, `recommendations`, `dashboardStats`, `marketContext` |
| Approved orders | `src/pages/ApprovedOrdersPage.jsx` | `approvedOrders`, `productIndex` |
| Data source | `src/pages/DataSourcePage.jsx` | `storeData`, `connectorStatus`, `onSelect*Source` |
| Planogram | `src/pages/PlanogramPage.jsx` | planogram props — ⛔ pilot-hidden (rule 5) |

All ten pages are present on `main` @ `67e7ba0`.

### 13.1 Producer → consumer map

| Contract area | Producer (exact path) | Consumer (exact path) | Status |
|---|---|---|---|
| Product catalog | `scripts/normalize-datasets.mjs` → `src/data/demoProducts.js` | `src/lib/dataAdapters/loadDemoStoreData.js` | **main** |
| Inventory state | `src/lib/analytics/inventoryEngine.js:54-75` | `src/pages/ProductsPage.jsx`, `DashboardPage.jsx` | **main** |
| Inventory state — `"Not enough sales history yet"`, `hasVelocity` | `src/lib/analytics/inventoryEngine.js:36-39,126-140` | same | **main** |
| Inventory summary | `inventoryEngine.js` `summarizeInventory()` | `DashboardPage.jsx`, `ReportPage.jsx` | **main** |
| Recommendation types (all 9) | `src/lib/analytics/recommendationTypes.js` | `RecommendationsPage.jsx`, `DashboardPage.jsx` | **main** |
| Velocity — Python side | `src/snapshots/velocity.py:353,398,410` | `scripts/normalize-datasets.mjs:96` | **main** |
| Velocity — JS passthrough | `scripts/normalize-datasets.mjs:96` | `inventoryEngine.js`, `reorderEngine.js` | **main** |
| Confidence — `confidence` (model) | `src/lib/analytics/reorderEngine.js` | `RecommendationsPage.jsx` | **main** |
| Confidence — `velocityConfidence` (data) | `reorderEngine.js:222`, `velocityConfidence.js` | `RecommendationsPage.jsx` | **main** |
| `valueAtStake` (per rec) + `productValueAtStake` (dashboard, deduped #30) — both credibility-guarded #39 | `reorderEngine.js`, `credibility.js`, `App.jsx` | `DashboardPage.jsx` | **main** |
| Operational recommendations | `scripts/export_dashboard_data.py` → `public/data/operational.json` | `loadOperationalData.js` → `OperationalPage.jsx` | **main** |
| Operational ranking (authoritative) | `src/lib/analytics/actionPriority.js` `rankActions()` + shared `credibility.js` | `src/pages/OperationalPage.jsx` | **main** — 🟢 §9.5 resolved #39 |
| Decisions / telemetry | `src/App.jsx:133-140` → `src/lib/persistence/persistence.js` | `OperationalPage.jsx:44-45`, `ActionCard.jsx:61-75` | **main** — 🔴 §9.2 |
| Competitor prices | `src/data/marketData.js` (from `data/matching/barcode_matches.parquet`) | `src/lib/analytics/competitorEngine.js` → `PriceGapPage.jsx` | **main** |
| Hebrew formatting / collation | `src/lib/utils/format.js`, `src/lib/utils/rtl.js` | all pages | **main** |
| Expiry | `scripts/export_dashboard_data.py` → `operationalData.expiry` | `src/pages/ExpiryPage.jsx` | **main** |

---

## 14. Changing this contract

Whoever needs the change edits this file and says so in the team channel before the code lands.
A breaking change (§11) needs a fresh sign-off round; a compatible one does not.

`main` is the reference for "what exists". Where `main` and this document disagree, §9 says so
explicitly rather than picking a winner — resolving those is a team decision, not a documentation
one.
