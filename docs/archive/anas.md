# Anas — Track C: Frontend Core & Honest Analytics

> 📋 **Read `PLAN.md` first** — phases, integration gates, go/no-go criteria, and the cut line.
> This file is only your slice of it.
>
> ✅ **DECIDED: the UI stays English for the pilot.** C-1 is therefore much smaller than originally
> scoped — no full i18n, no RTL layout flip. But Hebrew *data* still has to render correctly inside
> an English layout. See C-1 below.

> **You own (nobody else edits):** `src/App.jsx`, `src/lib/` (all JS engines), `index.html`,
> `src/index.css`, `src/App.css`, `scripts/normalize-datasets.mjs`, `scripts/build-rag-corpus.mjs`
> **Never touch:** `src/pages/`, `src/components/` (Malik), `scripts/*.py` (Fadi),
> `src/api/` (Nagham)

Read first: `CLAUDE.md`, `src/App.jsx`, `src/lib/analytics/inventoryEngine.js`,
`src/lib/analytics/reorderEngine.js`, `src/lib/ai/explanationProvider.js`

---

## What we are handing YomYom

A deployed web app a store manager opens each morning that says **what to act on today**, computed
from their own real data. The pilot measures whether acting on those alerts makes money.

## Your mission

**The analytics currently produce output that looks broken.** I ran the engine chain
against the real data — here is exactly what a customer would see:

| What the UI shows | Reality |
|---|---|
| "Slow moving" | **7,451 of 7,451 products (100%)** |
| `daysUntilStockout` | computed for **0** products |
| Stockout risk / low stock / overstocked / waste risk | **all 0** |
| Reorder recommendations | 2,742 — **all type `PROMOTION`**, identical text |

All of it traces to `salesLast30Days = 0` everywhere. Fadi is deriving real velocity from
snapshot deltas, but **that will take days of pilot data to become meaningful** — so the UI must
behave honestly in the meantime, and forever after for products with thin history.

---

### C-0 (P0 — DAY 1, DO THIS BEFORE ANY CODE) — Write the UI data contract

**You own this.** You compute the data in `App.jsx`; Malik renders it in `src/pages/`. That
boundary is the only real coupling in the whole four-way split, and it is where you two will
collide if it isn't written down first.

Create **`docs/UI_DATA_CONTRACT.md`** defining exactly what `App.jsx` passes into each page:

- The prop shape per page (`OperationalPage`, `ProductsPage`, `RecommendationsPage`, `ExpiryPage`,
  `DashboardPage`, `ReportPage`, `ApprovedOrdersPage`).
- The **analyzed product** shape — note it is nested: `product.analytics.primaryStatus`,
  `.daysUntilStockout`, `.margin`, `.marginRate`, `.riskScore`, not top-level fields.
- The **recommendation** shape, including the new types replacing `PROMOTION` (below-cost,
  price-gap, negative-stock, thin-margin) and where `velocity_confidence` surfaces.
- Which fields can be `null`, and what the page must render when they are. **This is the part that
  matters most** — `daysUntilStockout` is null for every product today, and a page that assumes a
  number will show `null` to a store manager.
- The accept/dismiss callback signatures Malik wires to Nagham's persistence.

**Done when:** the file is committed and Malik has explicitly agreed to it (D-0b). Get their
sign-off in writing — a "yeah looks fine" in chat counts, silence does not.

Keep it short. This is a one-page agreement, not a spec — an hour's work that saves both of you a
day of rework.

### C-1 (P0) — Hebrew data inside an English UI

The UI stays English (team decision). **This does not mean there is no work here** — all 7,451
product names are Hebrew and will render badly by default inside an LTR layout.

- Keep `<html lang="en">`. No RTL flip, no i18n module. Scope is small — do it fast.
- Put `dir="auto"` on **every element that renders product data** — names, categories, supplier.
  Without it, a Hebrew name next to a number renders in a confusing order (the `1.5` in
  `פריגת בטעם טרופי 1.5 ליטר` will jump to the wrong end of the string).
- Test with real values: `פריגת בטעם טרופי 1.5 ליטר`, `אבזרי סלולר ו חשמל`, `מוצרי מכולת`.
- Right-align Hebrew text columns in tables; keep ₪ amounts, %, dates and barcodes left-aligned
  and LTR. Mixed-direction table cells are the thing that will look broken if you skip it.
- Sorting and search must work on Hebrew strings — check `localeCompare('he')`.

⚠️ **Flag for the team, don't solve alone:** an English UI is fine if the *manager* is the only
user, since they're the one exporting the CSV. The moment floor staff are expected to use it, this
becomes the top adoption risk. Raise it at the pilot review — it is a real finding, not a nitpick.

### ⚠️ From Fadi (A-1 is built) — read before writing C-2

The velocity engine now writes these columns into `yomyom_sales.parquet`:

| Column | Meaning |
|---|---|
| `units_sold_7d` / `units_sold_30d` | **Observed sums over available history** — NOT full-window totals |
| `units_per_day` | The authoritative rate, already normalised by `observed_days` |
| `observed_days` | How much history actually backs the numbers |
| `max_gap_days` | Largest gap between snapshots |
| `velocity_confidence` | `none` / `low` / `medium` / `high` |

🔴 **Do not compute a rate as `units_sold_30d / 30`.** Early in the pilot that column may
cover only 4 days, so dividing by 30 understates velocity ~7x and a product selling 5/day
reads as dead stock. **Use `units_per_day`.**

🔴 **`null` units and `0` units are different facts.** `null` + `velocity_confidence: 'none'`
means *we have no history for this product* — that is the state the whole catalog is in today
(all 7,674 rows). `0` means *we observed it and it genuinely did not move*. Collapsing them is
exactly what makes 100% of products show "Slow moving".

Build C-2 against `velocity_confidence: 'none'` — that is the state the pilot starts in, and it
is what the UI will show until YomYom sends a second, genuinely new export.

### C-2 (P0) — Make the analytics honest

Never show a computed number we cannot stand behind.

- `inventoryEngine` must treat "no velocity history" as a **distinct state** from "zero sales".
  Fadi ships `velocity_confidence` (`none` / `low` / `medium` / `high`) — consume it.
- When confidence is `none`, do not classify the product as "Slow moving". Show
  **"Not enough sales history yet"** and suppress `daysUntilStockout` rather than rendering null.
- `reorderEngine` must stop emitting 2,742 identical PROMOTION cards. When velocity is unavailable,
  fall back to recommendation types we have **real** data for:
  - **Selling below cost** — 60 products, genuinely losing money on every unit
  - **Priced above competitor** — backed by 14,406 real barcode matches
  - **Negative stock** — 625 products, a data-integrity action for staff
  - **Thin margin** — 232 products under 20%
- Surface confidence in the UI. A recommendation from 2 days of history and one from 30 must not
  look equally certain.

### C-3 (P1) — Fix the LLM async bug

`annotateRecommendationsWithExplanations()` in `explanationProvider.js:22` calls
`provider.generateExplanation()` **synchronously**, but `llmExplanationProvider`'s version is
`async`. The Promise is never awaited, so `result.explanation` is always `undefined` and proxy
errors surface as unhandled rejections. The mock provider is sync, which is why it has always
appeared to work.

Fix: make the function async and move the recommendations `useMemo` in `App.jsx` to
`useEffect` + state. Keep the mock provider as a **graceful fallback** — if the proxy is slow, down,
or out of credits, the store manager still sees rule-based text, never a spinner or a blank card.

`VITE_LLM_PROXY_URL` is commented out in `.env` on purpose until this is fixed. Nagham owns the
billing and the deployed proxy — **coordinate, don't both edit this file.**

### C-4 (P1) — Store-floor layout

Responsive CSS exists (`@media` at 1220/860/560px) but was never tested for real use. Staff will
hold a phone in one hand. Verify every page at 390px wide, ensure tap targets are finger-sized, and
make sure tables of 7,451 Hebrew product rows don't blow out horizontally.

### C-5 (P2) — Performance

The bundle is **2.65 MB** (335 KB gzipped) because `demoProducts.js` is a 2.8 MB JS module compiled
into it. On a store's mobile connection that is a slow first load, and every data refresh means a
full redeploy. Move product data to a fetched JSON file — same pattern Nagham uses for
`operational.json`.

---

## Contract with the rest of the team

- **Malik owns `src/pages/` and `src/components/`; you own `App.jsx` and everything under
  `src/lib/`.** You compute and pass data down; Malik renders it. Agree the prop shape with them
  **before** either of you starts, or you will collide in `App.jsx`.
- Fadi guarantees these column names through `normalize-datasets.mjs`: `barcode`,
  `product_name`, `category`, `selling_price`, `cost_price`, `current_stock`, `units_sold_7d`,
  `units_sold_30d`, `velocity_confidence`.
- Do not start C-2 by waiting on real velocity data. Build against `velocity_confidence: 'none'` —
  that is the state the pilot begins in anyway.

## Done when

- The app reads naturally right-to-left with Hebrew product names and correct ₪ formatting.
- No screen shows "Slow moving" for a product we have no sales history for.
- Recommendation types reflect real signals (below-cost, price gap, negative stock, thin margin),
  not one repeated placeholder.
