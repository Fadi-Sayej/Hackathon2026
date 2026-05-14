# SmartShelf AI LLM Explanation Adapter

Sprint C6 makes real AI explanations pluggable later while keeping mock explanations stable today.

## Current Default

The app uses:

```txt
src/lib/ai/explanationProvider.js
src/lib/ai/mockExplanationProvider.js
```

Mock explanations remain the default and are generated synchronously from product metrics, recommendation data, and market context.

## Provider Files

- `explanationProvider.js`: app-facing annotation helper and provider selection point.
- `mockExplanationProvider.js`: deterministic local explanation provider.
- `llmExplanationProvider.js`: disabled-by-default backend/proxy provider shape.

## LLM Provider Safety

`llmExplanationProvider` is disabled unless a backend/proxy endpoint exists. It does not read frontend API keys and does not call a model provider directly from the browser.

The deprecated `gemini.js` file now refuses direct frontend Gemini calls and falls back to recommendation reason text.

## Request Payload Shape

The LLM payload is built from:

```js
{
  productMetrics: {
    id,
    name,
    category,
    currentStock,
    shelfQuantity,
    shelfCapacity,
    salesLast7Days,
    salesLast30Days,
    price,
    cost,
    leadTimeDays,
    expiryDate
  },
  recommendation: {
    type,
    urgency,
    confidence,
    recommendedOrderQuantity,
    recommendedShelfQuantity,
    metrics,
    reason
  },
  marketContext: {
    currentDate,
    weather,
    weekend,
    holiday,
    localEvent,
    season,
    sourceLabel
  },
  relevantRagChunks: [
    { id, type, category, text, tags, metadata }
  ],
  responseSchema: {
    shortExplanation: 'string',
    riskReason: 'string',
    businessImpact: 'string',
    confidenceNote: 'string'
  }
}
```

## Response Shape

The provider expects:

```js
{
  shortExplanation: string,
  riskReason: string,
  businessImpact: string,
  confidenceNote: string
}
```

## Demo Reliability

- Mock remains stable.
- LLM path is disabled by default.
- No frontend API keys are used.
- If a future proxy fails, UI should keep showing mock/fallback explanations.
- No LLM call should block the demo workflow.

## Not Included In C6

- No Gemini wiring.
- No paid APIs.
- No backend proxy implementation.
- No vector retrieval execution.
- No prompt UI.
