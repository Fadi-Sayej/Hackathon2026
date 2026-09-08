# SmartShelf AI — Final Handoff

Single-page summary for the team. Read this before going on stage.

---

## What the App Does

SmartShelf AI is a browser-based inventory intelligence tool for Israeli convenience store owners. It loads a real POS export (7,674 YomYom SKUs), runs inventory analytics to identify stockout risks and reorder needs, presents ranked recommendations with plain-language explanations, and lets the manager approve or adjust purchase orders in seconds. The approved order is exported as a CSV or printed. A separate planogram engine assigns shelf positions based on velocity and margin, with affinity suggestions for cross-merchandising.

---

## What Is Real vs. Mocked

| Element | Status |
|---|---|
| 7,674 YomYom product records | REAL — actual POS export |
| Inventory risk analytics | REAL — deterministic calculations |
| Reorder recommendations | REAL — deterministic engine |
| Planogram engine | REAL — deterministic placement scoring |
| AI explanation text | MOCK by default (rule-based) — Gemini proxy is built but needs uvicorn running |
| Competitor prices | MOCK — neighborhood snapshot of 6 barcodes × 4 chains |
| Market context (weather, holidays) | MOCK by default — live free APIs available with one env var |
| Supplier order transmission | MOCK — toast only, no API call |
| Shelf compliance vision | MOCK — synthetic detected shelf, no real vision model |
| Comax POS connector | STUB — returns error, no backend wired |

---

## Commands to Start

```bash
cd /Users/nagham/Documents/Hackathon2026
npm install          # only needed first time or after a pull
npm run dev          # starts at http://localhost:5173
```

To enable Gemini explanations (optional):
```bash
uvicorn src.api.llm_proxy:app --port 8000 --reload
# and set VITE_LLM_PROXY_URL=http://localhost:8000/explain in .env
```

---

## Safe Demo Sequence

1. Open `http://localhost:5173` — app lands on Dashboard
2. Point to 6 KPI cards, Market Context panel, Market Intelligence panel
3. Navigate to **Smart Reorder** — explain one HIGH-urgency recommendation card
4. Click **Approve** — card fades, badge changes to APPROVED
5. Navigate to **Approved Orders** — show supplier grouping, totals, Export CSV button
6. Navigate to **Shelf Optimization** — click one shelf slot, show Placement Reason panel
7. Close the demo. Take questions.

**Reset before demo:** Click "Reset Demo State" in the top bar (appears when any override exists), or clear localStorage via DevTools → Application → Local Storage → Clear All.

---

## Three Things to Never Say on Stage

1. **"This uses Claude / ChatGPT"** → Say: "The explanation layer uses Gemini through a backend proxy, and deterministic retail analytics in offline mode."

2. **"The AI decides everything"** → Say: "The analytics engine calculates the recommendations. AI adds the plain-language explanation on top."

3. **"This is production-ready"** → Say: "This is a working prototype that proves the end-to-end workflow. The next step is a three-store pilot."

---

## Claude's Final Verdict

```
QA PASS: P5 / Final Pre-Demo

VERDICT: READY WITH NOTES

TESTED (by code inspection):
- All 9 pages render or show EmptyState
- Approve/reject/edit quantity logic is correct (normalizeOrderQuantity clamps to min 1)
- CSV export and print are wired correctly
- localStorage persistence works for recommendation decisions and approved orders
- Reset demo state clears all overrides
- EmptyState components exist on all pages that can have empty data
- Market context source label is exposed in the UI
- Competitor intelligence panel is present on Dashboard

PASS:
- Core approve/reject/edit workflow is correctly implemented
- Approved Orders totals are calculated correctly (qty × unit cost per item, sum per supplier, grand total)
- CSV export produces correct output with header row and escaped values
- Print calls window.print() correctly
- Planogram renders shelf groups and supports item selection
- EmptyState exists on: Dashboard risk list, Recommendations, Planogram, Approved Orders, Products (search/filter)
- normalizeOrderQuantity prevents NaN, 0, and negative values

RISKS:
- AI explanations are rule-based by default — must be disclosed honestly if asked
- Competitor prices are mock — must be disclosed honestly if asked
- "Send to Supplier" is a toast only — must be disclosed if judges probe
- Shelf compliance vision is simulated — must be disclosed if judges probe
- Comax connector shows an error — avoid clicking it during demo

DEMO SAFE FLOW:
Dashboard → Smart Reorder (approve one card) → Approved Orders (show total + Export CSV) → Shelf Optimization (click one slot)

AVOID:
- Data Source page (Comax error visible)
- CSV upload during demo
- Explaining shelf compliance as real vision AI
- Claiming AI explanations are live Gemini unless proxy is confirmed running

NOTES:
The app is structurally correct. No crashes, no broken flows, no invalid state from code inspection. All mock elements have honest labels or fallback explanations. The team is demo-ready if they follow SAFE_DEMO_FLOW.md and DO_NOT_SAY.md.
```
