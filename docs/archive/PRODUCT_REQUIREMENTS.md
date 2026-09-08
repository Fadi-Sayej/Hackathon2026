# SmartShelf AI — Product Requirements

## One-liner

SmartShelf AI turns a convenience store owner's inventory spreadsheet into a live dashboard that tells them what to reorder, how much to order, and where to put it on the shelf.

---

## 30-Second Explanation (for judges)

A gas station or mini-market owner today makes ordering decisions by walking the shelves and guessing. SmartShelf AI takes their POS export, runs it through inventory analytics, and produces a prioritized reorder list with plain-language explanations. The owner approves or adjusts quantities with one click, sees the total purchase order cost, and gets a data-driven shelf layout — all without any backend or subscription. The whole workflow takes under five minutes.

---

## MVP Feature List (exists today)

| Feature | Where |
|---|---|
| Inventory risk dashboard (stockouts, overstock, waste risk, reorder count, order cost) | Dashboard page |
| Sales distribution by category (30-day view) | Dashboard → Category bars |
| Market context panel (weather, holidays, news — live or static fallback) | Dashboard |
| Competitor intelligence panel (price leaders, stockout opportunities, price-protection alerts) | Dashboard |
| Full product list with search and filter by category and status | Products page |
| Prioritized reorder recommendations with AI-generated explanations | Recommendations page |
| Approve / reject / edit quantity workflow per recommendation | Recommendations page |
| Approved orders grouped by supplier with subtotals and grand total | Approved Orders page |
| Export approved orders as CSV | Approved Orders page |
| Print approved orders via browser print | Approved Orders page |
| Visual shelf planogram (shelf-by-shelf layout, facings, eye-level scoring) | Planogram page |
| Click a planogram slot to see placement reasoning | Planogram page |
| Cross-merchandising (affinity) suggestions | Planogram page |
| Shelf compliance photo upload and mock vision analysis | Planogram page |
| Operational risk view (Wolt price gaps, margins, negative stock, unknown barcodes) | Operational page |
| Expiry tracking (record barcode + expiry date at receiving) | Expiry page |
| AI Report (comprehensive optimization report) | Report page |
| Data source switching (demo data / CSV upload / Comax stub) | Data Source page |
| Reset demo state | Top-bar button |

---

## Out-of-Scope (not in MVP)

- Real POS integration (Comax, Priority) — stub only
- Supplier ordering API — "Send to supplier" shows a toast, no actual transmission
- User authentication and store accounts
- Multi-store view
- Cloud persistence (all state is browser localStorage)
- Real-time price feed from Israeli retail portal (mock neighborhood data used)
- Vector search / embeddings for RAG (corpus structure is ready, search is not)
- Mobile app
- Hebrew-language UI

---

## User Journey

1. **Owner opens dashboard** — sees today's stockout risks, pending reorders, estimated order cost, and market context in one screen.
2. **Reviews inventory risks** — scans the highest-risk product list and urgent recommendations panel.
3. **Opens Recommendations** — reads AI explanation for each flagged item, adjusts quantity if needed.
4. **Edits / approves order** — clicks Approve on each item; Reject removes it from view.
5. **Views Approved Orders** — sees grouped purchase order by supplier with totals; exports CSV or prints.
6. **Checks Planogram** — sees shelf layout generated from velocity, margin, and capacity data; understands why each product is placed where it is.

---

## Success Metrics

| Metric | Definition |
|---|---|
| Fewer stockouts | High-risk stockout count decreases after owners act on recommendations |
| Less overstock | Overstocked item count decreases over rolling periods |
| Fewer expired products | Waste-risk items flagged and cleared before expiry date |
| Faster order decisions | Time from opening dashboard to approved purchase order under 5 minutes |
| Better shelf allocation | Eye-level shelf slots filled by highest-velocity, highest-margin SKUs |
