Read these files before doing anything:

- CLAUDE.md
- STATUS.md
- sprint_plan.md
- src/lib/ai/explanationProvider.js
- src/lib/ai/llmExplanationProvider.js
- .env.example
- requirements.txt

You are working on Person D's tasks from sprint_plan.md: making real LLM explanations work. D-4, D-1, and D-3 all have zero dependencies — do all three on day 1.

YOUR TASKS IN ORDER:

D-4 (no dependencies):
In .env.example, add this block (coordinate with Person C who is removing VITE_LLM_EXPLANATIONS_ENABLED=false): # ── LLM proxy (FastAPI, enables real AI explanations) ──────────────────────── # Get your key at Google Cloud Console → APIs & Services → Credentials
GEMINI_API_KEY=

    # URL of the running llm_proxy.py server
    VITE_LLM_PROXY_URL=http://localhost:8000/explain

In requirements.txt, add fastapi, uvicorn, and anthropic if not already listed.
Also add ANTHROPIC_API_KEY= to your local .env (get the real key from the team).

D-1 (no dependencies):
Fix two bugs in src/lib/ai/explanationProvider.js:
Bug 1: getDefaultExplanationProvider() unconditionally returns mockExplanationProvider and never reads VITE_LLM_PROXY_URL.
Bug 2: The caller passes one argument to generateExplanation, but llmExplanationProvider.generateExplanation(payload, options) needs options.proxyUrl and options.enabled in the second argument — so it always falls through.
Fix by replacing getDefaultExplanationProvider() with:
export function getDefaultExplanationProvider() {
const proxyUrl = import.meta.env.VITE_LLM_PROXY_URL
if (proxyUrl) {
return {
...llmExplanationProvider,
generateExplanation(payload) {
return llmExplanationProvider.generateExplanation(payload, { enabled: true, proxyUrl })
},
}
}
return mockExplanationProvider
}
Done when: setting VITE_LLM_PROXY_URL in .env causes the frontend to POST to that URL (visible in browser DevTools → Network). Without the proxy running, it should fall back gracefully without crashing.

D-3 (no dependencies):
Create src/api/**init**.py (empty file) and src/api/llm_proxy.py as specified in sprint_plan.md (adapted for Gemini). It requires `GEMINI_API_KEY` env var and runs on port 8000.
Start it with: uvicorn src.api.llm_proxy:app --port 8000 --reload
Test with: curl -s http://localhost:8000/health → should return {"status":"ok"}
Test explain: curl -s -X POST http://localhost:8000/explain -H "Content-Type: application/json" -d '{"product":"test"}' → should return all four fields (shortExplanation, riskReason, businessImpact, confidenceNote).

D-5 (wait for Person A to confirm A-2 is done — it already is, so you can start now):
Read scripts/build-rag-corpus.mjs, then add the real-data loader as described in sprint_plan.md. It exports data/internal/silver_pos/yomyom_products.parquet to JSON via a Python subprocess, then maps fields to the canonical product shape. Fall back to loadDemoStoreData() if the Parquet doesn't exist.
Done when: node scripts/build-rag-corpus.mjs produces JSONL in data/processed/rag/ with 7,000+ lines of Hebrew product names.

Only work on the files mentioned here. Do not touch the Python pipeline (scripts/import*\*, scripts/join*\*) or App.jsx.
