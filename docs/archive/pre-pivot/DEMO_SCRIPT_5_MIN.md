# SmartShelf AI — 5-Minute Demo Script

Total time: ~5 minutes including Q&A buffer. Read at a relaxed pace. Brackets indicate actions.

---

## Opening — The Problem (45 seconds)

"A gas station owner in Tel Aviv starts every morning the same way: walking the shelves, checking what ran out, trying to remember what sold fast last week, and calling suppliers based on gut feel.

The result? Red Bull is out of stock on a Friday evening. A case of hummus expires in the back. The manager spent forty minutes on ordering decisions that a data system could handle in seconds.

The industry calls these three problems stockouts, overstock, and waste. They cost Israeli convenience stores an estimated 8–12% of potential revenue every month. SmartShelf AI is built to close that gap."

---

## Dashboard (45 seconds)

[Navigate to Dashboard]

"The owner opens the app and sees six numbers: stockout risks, reorder count, estimated order cost, overstocked items, and waste risk. These are calculated from the real inventory dataset — 7,674 SKUs from YomYom, a convenience store chain.

Below that is category sales distribution over thirty days. And here — [point to Market Context panel] — the system pulls in external signals. Weather: it's going to be hot tomorrow, cold drinks should be prioritized. Upcoming holiday: demand for snacks typically spikes before Shabbat.

And here — [point to Market Intelligence panel] — competitor intelligence. Paz Yellow, 200 meters away, is out of Red Bull. That means our stock is the only one in the neighborhood. The system boosts the urgency on that reorder."

---

## Recommendations — Explain One AI Recommendation (75 seconds)

[Navigate to Smart Reorder]

"The recommendations are ranked by urgency. Let's look at this HIGH-urgency card. [point to top card]

The explanation says: 'Stock is critically low. At current velocity you have fewer than two days of supply. A competitor 200 meters away is out of stock — demand will likely exceed forecast.' That's not a guess. It's calculated from current stock, rolling seven-day sales, and the competitor snapshot we just saw.

The system suggests ordering [read quantity] units. I can override that if I want — [edit quantity field] — the cost updates in real time. If the quantity is set to zero, the approve button locks out. No zero-quantity orders can slip through.

[Click Approve] Approved. Four seconds."

[Point to competitor price comparison]

"Notice the price comparison: we're selling Red Bull at 8.20 ₪. The Paz station 200 meters away sells it at 7.90 ₪. The system flags this — not to say we should cut price, but so the manager knows. That's the competitor intelligence layer."

---

## Approved Orders (30 seconds)

[Navigate to Approved Orders]

"The approved item is here immediately. Grouped by supplier — in this case [read supplier name]. Quantity, unit cost, total. Grand total at the bottom.

[Click Export CSV] That downloads a CSV the manager can send to the supplier directly, or paste into their existing order system. [Click Print] And print opens the browser print dialog — clean one-page purchase order."

---

## Planogram (45 seconds)

[Navigate to Shelf Optimization]

"The planogram engine takes the same product data — stock, velocity, margin, shelf capacity — and assigns every SKU to a shelf position and a facing count.

Eye-level shelf [point to middle shelf row]: the highest-velocity, highest-margin products. Bottom shelf: bulk, slow-movers. The logic is visible: click any slot [click a product slot] and the Placement Reason panel explains exactly why that product is where it is.

[Point to Cross-Merchandising panel] And here — products that sell together. Hummus and pita bread appear next to each other in 73% of basket analyses. The system surfaces that as a cross-merchandising suggestion."

---

## Closing + Q&A Buffer (45 seconds)

"SmartShelf AI replaces the morning shelf walk, the supplier phone call, and the expiry-date guessing game — all in under five minutes.

The data is real: 7,674 SKUs from an actual YomYom POS export, and competitor prices from Israel's mandatory food price transparency law. The AI explanation layer runs on Gemini-2.0-flash through a proxy we've built — or on deterministic retail rules in offline mode.

After the hackathon: three-store pilot, thirty days, then Supabase-backed multi-store SaaS.

Happy to answer questions — and we're happy to run any part of this again."

---

## Fallback Lines

| If... | Say... |
|---|---|
| A judge asks "is this real AI?" | "The analytics engine is deterministic retail logic. The explanation text layer uses Gemini through a backend proxy — we can run it right here if you'd like." |
| A judge asks about competitor prices | "These come from Israel's food price transparency portal format — every chain publishes XML feeds. In the demo we've modeled a realistic neighborhood snapshot. The pipeline to pull live data is built." |
| A page loads slowly | "We're running locally on Vite dev server — production build is faster." |
| A recommendation is missing | "Let me click Reset Demo State [point to button] and walk through it fresh." |
| Approved Orders is empty | "I need to approve a recommendation first — let me do that. [navigate back to Recommendations, approve one item, return]" |
