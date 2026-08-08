# SmartShelf AI LLM Explanation Adapter

Sprint C6 makes real AI explanations pluggable later while keeping mock explanations stable today.

> **Update (2026-08-07, B-4): the backend proxy is now implemented** at `src/api/llm_proxy.py`
> (`/explain`, `/report`, `/health`), hardened with an in-memory TTL/LRU cache (no re-billing per
> render), an upstream timeout on both endpoints, CORS origins from `LLM_ALLOWED_ORIGINS`, and
> graceful startup without a key (503, not a crash). Tests: `tests/test_llm_proxy.py` (6 cases).
> The **frontend LLM path is still disabled**, gated on three things: the Gemini key needs credits
> (429), the proxy must be deployed and `VITE_LLM_PROXY_URL` set, and the async bug in
> `explanationProvider.js` (Track C) must be fixed. Mock explanations remain the default.

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
- ~~No backend proxy implementation.~~ **Superseded by B-4 — the proxy now exists (see the update note at the top); it is deployed/wired separately and still gated on the Gemini key + the Track-C async fix.**
- No vector retrieval execution.
- No prompt UI.
