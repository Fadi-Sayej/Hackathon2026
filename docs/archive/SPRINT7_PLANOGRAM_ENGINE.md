# Sprint 7 Planogram Engine

Sprint 7 adds the first SmartShelf planogram engine.

## Output

The engine lives in:

- `src/lib/analytics/planogramEngine.js`

It exports:

- `generatePlanogram(products, marketContext)`
- `groupPlanogramByShelf(planogramItems)`
- `summarizePlanogram(planogramItems)`

## Rules implemented

Each product receives a planogram score from:

- sales velocity
- product margin
- stockout risk
- expiry risk
- impulse category boost
- slow-moving penalty

Products are assigned to:

- `EYE_LEVEL`
- `MIDDLE`
- `TOP`
- `BOTTOM`

Each planogram item includes:

- `productId`
- `productName`
- `category`
- `shelfLevel`
- `shelfLabel`
- `facings`
- `score`
- `scoreBreakdown`
- `reason`

## Verification

Run:

```bash
npm run sprint7
```

This regenerates app data, runs lint, and builds the app.
