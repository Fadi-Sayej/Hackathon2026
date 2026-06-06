# SmartShelf AI — Mocks and Assumptions

This document lists every element in the running app that is simulated, mocked, or approximated. Each entry includes why it is mocked, what a real version would require, and safe wording to use during the demo.

---

## 1. AI Explanations (rule-based by default)

**What it looks like:** Each recommendation card shows an "AI explanation" text block.

**What is actually happening:** The `mockExplanationProvider` generates deterministic text from product metrics (stock, velocity, margin, urgency). No LLM is called by default.

**Why mocked:** An LLM call requires a backend proxy to avoid exposing API keys in the browser. The proxy is built (`src/api/llm_proxy.py`, Gemini-2.0-flash) but requires the team to run `uvicorn` locally and set `VITE_LLM_PROXY_URL`.

**What the real version needs:** `uvicorn src.api.llm_proxy:app --port 8000 --reload` running, and `VITE_LLM_PROXY_URL=http://localhost:8000/explain` set in `.env`.

**Safe demo wording:** "The analytics engine generates explanations from the product data. The architecture supports Gemini-powered explanations through a backend proxy — we can show that running locally too."

---

## 2. Competitor Price Data (mock neighborhood)

**What it looks like:** The Market Intelligence panel shows price comparisons with Paz Yellow, Delek Menta, Sonol, and Dor Alon.

**What is actually happening:** `src/data/mockMarketData.js` contains a hand-crafted snapshot of 6 barcodes × 4 stores. Numbers are plausible but not from a live feed.

**Why mocked:** The Israeli retail price transparency portal (Hok HaMazon) requires per-chain credentials. Real barcode matching from the Kaggle dataset also requires the `barcode_matches.parquet` pipeline step, which has not yet run.

**What the real version needs:** Portal credentials per chain, or running `scripts/export_competitor_market_data.py` after barcode matching is complete.

**Safe demo wording:** "Competitor prices come from Israel's mandatory food price transparency law — every chain publishes XML feeds. In the demo we've modeled a realistic neighborhood snapshot. The pipeline to pull live data is built."

---

## 3. Market Context (static fallback by default)

**What it looks like:** The Market Context panel shows weather, holiday, and news signals with a source label.

**What is actually happening:** Unless `VITE_ENABLE_LIVE_MARKET_CONTEXT=true` is set, the app uses `src/lib/context/fallbackMarketContext.js` — a realistic static snapshot. The label distinguishes live from fallback.

**Why mocked:** Demo stability. Live API calls can fail or return unexpected data during a presentation.

**What the real version needs:** Set `VITE_ENABLE_LIVE_MARKET_CONTEXT=true`. Open-Meteo and Nager.Date are free with no keys required.

**Safe demo wording:** "Market context uses Open-Meteo weather and Israeli holiday calendars — both free, no API key. We run with a stable static snapshot during demo to avoid live API variance, but it's one env variable to switch on."

---

## 4. Supplier Order Transmission ("Send to Supplier" button)

**What it looks like:** Each supplier group in Approved Orders has a "Send to [Supplier]" button that shows a success toast.

**What is actually happening:** The toast fires immediately; no HTTP request is made, no email is sent, no order reaches any supplier.

**Why mocked:** Supplier API integration is a Phase 7 SaaS feature. No supplier credentials or API contract exists.

**Safe demo wording:** "Clicking Send triggers the confirmation flow. In production this would POST to the supplier's order API or send a structured email. We've built the UI and workflow; the actual transmission is a post-hackathon integration step."

---

## 5. Shelf Compliance Vision Analysis

**What it looks like:** The Planogram page has a "Shelf Compliance Analysis" section with a photo upload and an "Analyze" button that runs for 1.8 seconds and shows a compliance report.

**What is actually happening:** `generateMockDetectedShelf()` in `src/lib/analytics/complianceEngine.js` generates a synthetic detected shelf. No image is actually analyzed.

**Why mocked:** Real vision analysis requires a cloud vision API (e.g., Google Vision, GPT-4 Vision). No backend or API key is wired for this.

**Safe demo wording:** "This shows what the compliance analysis workflow looks like — upload a shelf photo, the model identifies product placement against the planogram. The actual vision model integration is the next engineering step."

---

## 6. Comax POS Connector

**What it looks like:** The Data Source page offers a "Comax" connector option.

**What is actually happening:** `createComaxConnectorStub()` immediately returns an error with a message saying it is not yet implemented.

**Why mocked:** Comax requires backend authentication. No API contract has been established.

**Safe demo wording:** "Comax is the leading Israeli retail POS system. This is the integration slot — once Comax credentials are available, the connector drops in without changing the rest of the app."

---

## 7. Demo Product Sales Data

**What it looks like:** Products show `salesLast7Days` and `salesLast30Days` figures used in analytics.

**What is actually happening:** Sales figures are synthetic. The real YomYom POS export contains inventory and prices, but not a rolling sales history in the frontend demo dataset.

**Why mocked:** Real sales history requires a time-series import from the POS. The Python pipeline skeleton for this exists but the frontend still loads demo products for the UI.

**Safe demo wording:** "Sales velocity figures in the demo are representative — a real POS export provides actuals. The adapter layer is designed to accept that data directly."

---

## Summary Table

| Mock Element | Label in UI | Real Version Status |
|---|---|---|
| AI explanations | "AI explanation" label on cards | Proxy built, needs uvicorn running |
| Competitor prices | Market Intelligence panel | Pipeline built, needs barcode_matches.parquet |
| Market context | Source label (live/fallback) | Free APIs ready, needs env var |
| Supplier transmission | "Send to Supplier" toast | Phase 7 SaaS feature |
| Vision compliance | "Shelf Compliance Analysis" | Needs cloud vision API |
| Comax connector | Data Source page | Needs backend + credentials |
| Demo sales figures | Sales stats on product cards | Needs time-series POS import |
