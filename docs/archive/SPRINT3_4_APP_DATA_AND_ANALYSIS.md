> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# Sprint 3 and 4

This handoff covers app-ready demo data and the first inventory analysis engine.

## Sprint 3 output

The normalization pipeline now exports app data to:

- `src/data/demoProducts.js`
- `src/data/marketContext.js`

Run:

```bash
npm run sprint3
```

This regenerates `src/data/demoProducts.js` from the current normalized demo dataset.

## Sprint 4 output

The inventory analysis engine lives in:

- `src/lib/analytics/inventoryEngine.js`

It provides:

- `analyzeProduct(product, context)`
- `analyzeProducts(products, context)`
- `summarizeInventory(analyzedProducts)`

Computed fields include:

- `avgDailySales7`
- `avgDailySales30`
- `weightedAvgDailySales`
- `daysUntilStockout`
- `margin`
- `marginRate`
- `primaryStatus`
- `statuses`
- `riskScore`

## Status rules

Products can be tagged as:

- `Healthy`
- `Low stock`
- `Stockout risk`
- `Overstocked`
- `Slow moving`
- `Near expiry`
- `High priority`

## Verification

Run:

```bash
npm run sprint4
```

This regenerates app data, runs lint, and builds the app.
