# SmartShelf AI — Codex SaaS Execution Track

## Role

This file is for Codex only.

Codex owns implementation. Claude owns product, QA, pitch, and acceptance. Do not let both agents edit the same area in the same sprint.

Current state: React + Vite local-first MVP with dashboard, products, recommendations, planogram, approved orders, mock AI explanations, and local state.

Goal: evolve the MVP toward SaaS readiness without breaking the demo.

---

## Codex Owns

- App architecture
- Functional fixes
- Data adapters
- API adapters
- Persistence abstraction
- Recommendation/planogram integration
- RAG-ready file generation
- Optional LLM adapter architecture
- Build/lint/deploy stability

## Codex Must Not Own

- Pitch wording
- Judge Q&A
- Business model text
- Persona documents
- Demo script wording
- Product roadmap language beyond technical notes

---

## Absolute Rules

1. Do not break the current demo.
2. Do not redesign unless explicitly asked.
3. Do not add paid services.
4. Do not expose API keys in frontend.
5. Every visible action must work or be clearly labeled demo/mock.
6. Prefer adapters over rewrites.
7. Run `npm run lint` and `npm run build` after every sprint.
8. Return a handoff report after every sprint.
9. Do not touch Claude-owned docs unless asked.
10. Keep every sprint reviewable.

---

# Sprint C1 — Demo Reliability Lock

## Goal

Make the current MVP safe for live demo.

## Tasks

- Prevent invalid approved orders:
  - no empty quantity
  - no negative quantity
  - no NaN
  - no zero quantity
- Make approved recommendations no longer look pending.
- Ensure rejected recommendations do not reappear during session.
- Ensure Approved Orders totals are correct.
- Ensure CSV export works.
- Ensure print uses `window.print()`.
- Ensure product search/filter empty state exists.
- Ensure planogram empty state exists.
- Ensure all currency uses shared formatter.
- Ensure static/mock market context is labeled honestly.
- Add optional reset-demo-state button only if it does not clutter UI.

## Files Likely Touched

- `src/App.jsx`
- `src/pages/RecommendationsPage.jsx`
- `src/pages/ApprovedOrdersPage.jsx`
- `src/pages/ProductsPage.jsx`
- `src/pages/PlanogramPage.jsx`
- `src/components/shared/formatters.js`
- `src/App.css`

## Do Not Touch

- `src/lib/analytics/*`
- `scripts/*`
- `data/processed/*`
- `src/data/demoProducts.js`

## Done Criteria

- All visible actions work or are labeled.
- No invalid approved order can be created.
- Approve/reject/edit flow is obvious.
- Lint/build pass.

---

# Sprint C2 — Data Adapter Layer

## Goal

Make the app data-source agnostic before adding backend.

## Tasks

- Create `src/lib/dataAdapters/`.
- Add product adapter:
  - raw input to normalized Product.
- Add inventory adapter.
- Add sales adapter.
- Add validation helpers:
  - missing product name
  - missing category
  - invalid stock
  - invalid price/cost
  - invalid expiry date
- Add `loadDemoStoreData()` that returns current demo data through adapter pathway.
- Keep UI consuming normalized data only.
- Document accepted schema.

## New Files

- `src/lib/dataAdapters/productAdapter.js`
- `src/lib/dataAdapters/inventoryAdapter.js`
- `src/lib/dataAdapters/salesAdapter.js`
- `src/lib/dataAdapters/validation.js`
- `src/lib/dataAdapters/loadDemoStoreData.js`
- `docs/TECH_DATA_ADAPTERS.md`

## Done Criteria

- Current demo still works.
- UI does not care if data comes from local file, CSV, or future backend.
- Invalid rows are handled safely.
- Lint/build pass.

---

# Sprint C3 — Free Market Signals Adapter

## Goal

Prepare live context using free APIs while preserving fallback stability.

## Free APIs

- Open-Meteo: weather, no key.
- Nager.Date: holidays, no key for basic use.
- GDELT: news/events, no key.

## Tasks

- Create `src/lib/context/marketContextAdapter.js`.
- Add:
  - `fetchWeatherContext(location)`
  - `fetchHolidayContext(countryCode)`
  - `fetchEventContext(query)`
  - `buildMarketContext()`
- Add timeout and fallback.
- Add source labels:
  - `live`
  - `static-fallback`
  - `mock`
- Ensure app never breaks if APIs fail.
- Do not add Gemini here.
- Do not add paid APIs.

## New Files

- `src/lib/context/marketContextAdapter.js`
- `src/lib/context/fallbackMarketContext.js`
- `docs/TECH_MARKET_CONTEXT.md`

## Done Criteria

- App works offline.
- App can optionally use live free signals.
- UI shows whether context is live or mock.
- No secrets required.
- Lint/build pass.

---

# Sprint C4 — RAG-Ready Knowledge Corpus

## Goal

Prepare RAG structure without vector DB or real LLM.

## Tasks

- Create `scripts/build-rag-corpus.mjs`.
- Generate JSONL chunks into `data/processed/rag/`.
- Chunk types:
  - product chunks
  - category playbooks
  - planogram rules
  - reorder rules
  - market context templates
- Each chunk must include:
  - `id`
  - `source`
  - `type`
  - `category`
  - `text`
  - `tags`
  - `metadata`
- Add README explaining future embedding path.

## New Files

- `scripts/build-rag-corpus.mjs`
- `data/processed/rag/products.jsonl`
- `data/processed/rag/category-playbooks.jsonl`
- `data/processed/rag/planogram-rules.jsonl`
- `data/processed/rag/reorder-rules.jsonl`
- `data/processed/rag/market-context-templates.jsonl`
- `data/processed/rag/README.md`
- `docs/TECH_RAG_READINESS.md`

## Done Criteria

- Valid JSONL corpus exists.
- No vector DB yet.
- No LLM calls yet.
- RAG path is technically documented.
- Lint/build pass.

---

# Sprint C5 — Persistence Abstraction

## Goal

Prepare for SaaS persistence without committing to backend immediately.

## Tasks

- Create persistence interface:
  - `saveApprovedOrder(order)`
  - `listApprovedOrders()`
  - `saveRecommendationDecision(decision)`
  - `loadStoreProducts(storeId)`
  - `resetDemoState()`
- Implement localStorage adapter first.
- Persist:
  - approved orders
  - edited quantities
  - rejected recommendation ids
- Document future Supabase tables:
  - stores
  - products
  - inventory_snapshots
  - sales_history
  - recommendations
  - approved_orders
  - rag_documents
  - rag_chunks
  - embeddings

## New Files

- `src/lib/persistence/persistence.js`
- `src/lib/persistence/localStorageAdapter.js`
- `docs/TECH_PERSISTENCE_AND_SUPABASE.md`

## Done Criteria

- Refresh can preserve approved orders if enabled.
- Reset demo state exists.
- No Supabase required yet.
- Future backend path documented.
- Lint/build pass.

---

# Sprint C6 — Safe LLM Explanation Adapter

## Goal

Make real AI pluggable later while mock remains stable.

## Tasks

- Keep mock explanation as default.
- Create provider abstraction:
  - `mockExplanationProvider`
  - `llmExplanationProvider`
- LLM provider must be disabled unless backend/proxy exists.
- Define request payload:
  - product metrics
  - recommendation
  - market context
  - relevant RAG chunks
- Define response:
  - short explanation
  - risk reason
  - business impact
  - confidence note
- If LLM fails, fallback to mock.
- Never block UI during demo.
- Never expose frontend API keys.

## New Files

- `src/lib/ai/explanationProvider.js`
- `src/lib/ai/mockExplanationProvider.js`
- `src/lib/ai/llmExplanationProvider.js`
- `docs/TECH_LLM_EXPLANATIONS.md`

## Done Criteria

- Mock remains stable.
- LLM path is safely disabled or proxied.
- No secrets committed.
- Lint/build pass.

---

# Final Technical SaaS Definition of Done

SmartShelf AI is technically SaaS-ready when:

- UI consumes normalized data only.
- Data adapter layer exists.
- Recommendation and planogram engines work on normalized data.
- Market context supports live/fallback modes.
- RAG-ready corpus exists.
- Persistence abstraction exists.
- LLM adapter is safe and optional.
- No secrets are committed.
- Build/lint pass consistently.
- Every visible action works or is labeled demo/mock.

---

# Codex Handoff Format

After every sprint, return:

```txt
SPRINT: C#
STATUS: PASS / PARTIAL / BLOCKED

FILES CHANGED:
-

WHAT CHANGED:
-

HOW TO TEST:
-

COMMAND RESULTS:
- npm run lint:
- npm run build:

RISKS:
-

NEXT RECOMMENDED ACTION:
-
```
