# SmartShelf AI — Do Not Say List

Phrases to avoid on stage, and what to say instead. Every substitution is accurate and defensible.

---

| Do NOT say | Say instead | Why |
|---|---|---|
| "This uses Claude / ChatGPT" | "This uses a Gemini-powered backend when running with the proxy, and deterministic retail analytics in offline mode." | Neither Claude nor ChatGPT is wired into this app. Gemini (gemini-2.0-flash) is the actual LLM in the proxy. |
| "The AI decides everything" | "The analytics engine calculates the recommendations. AI adds plain-language explanations on top." | Recommendations come from deterministic rule engines, not an LLM. Saying "AI decides" is overclaiming and is a direct rule violation (absolute rule #6). |
| "This is production-ready" | "This is a working prototype designed to validate the workflow end-to-end." | There is no backend, no auth, no multi-store, and persistence is localStorage. A judge will see through "production-ready" instantly. |
| "We have thousands of users" | "We have a real inventory dataset from YomYom — 7,674 products, real Hebrew names, real prices." | There are no users. This is a hackathon project. Claiming users is a credibility-destroying lie. |
| "The AI is live and running" | "The analytics are always running. The Gemini explanation layer is available when the proxy is running locally." | The proxy may or may not be running during the demo. Do not claim it is live unless you can prove it right now. |
| "We compared prices to Shufersal in real time" | "We've modeled competitor prices in the Israeli transparency law format and imported 61,000 Shufersal SKUs into the pipeline." | Live competitor price comparison is not wired to the frontend yet — only the mock neighborhood is. |
| "The shelf compliance vision is AI-powered" | "The compliance workflow shows what the vision analysis would look like. The actual vision model integration is the next engineering step." | The vision analysis is `generateMockDetectedShelf()` — a synthetic simulation, not a real vision model. |
| "We process real-time data" | "We load data at startup from a real POS export. Live streaming is a post-hackathon phase." | The app loads data once into memory. There is no real-time feed. |
| "The app sends orders to suppliers automatically" | "The app generates a purchase order. The manager reviews it and sends it — we've built the approval workflow, the actual transmission is a next step." | The "Send to Supplier" button fires a toast with no real API call. |
| "This will save stores millions" | "Based on industry benchmarks, eliminating one stockout per week can cover the monthly subscription cost several times over." | "Millions" is unsubstantiated. Specific, modest claims are more credible and harder to challenge. |

---

## General Rules

1. Only claim what the running app can demonstrate right now.
2. If a feature is mocked, say it is mocked — then explain why and what the real version needs.
3. If a question requires a number, use a real number from the app (7,674 products, 4 competitors, 6 barcodes) or say "we don't have that data yet."
4. If an API is not running, do not say "the AI is running."
5. Confidence is good. Honesty is better. The combination is winning.
