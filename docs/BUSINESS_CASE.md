# SmartShelf AI — Business Case

---

## Target Customer

**Primary:** Gas station convenience stores and mini-markets in Israel.

- Store size: 80–400 sqm floor space, 500–3,000 active SKUs
- Owner profile: independent operator or franchisee of a major fuel brand (Paz, Delek, Sonol, Dor Alon)
- Current tooling: Excel spreadsheets, WhatsApp to suppliers, manual shelf walks
- Pain: daily time cost of ordering decisions, stockouts on fast-moving SKUs, expiry waste in chilled and bakery categories

**Secondary:** Small supermarkets and neighborhood grocery stores (makolot) with similar operational pain.

**Not targeted initially:** Large supermarket chains (Shufersal, Rami Levy) — they have dedicated logistics and ERP teams. SmartShelf AI is built for the owner-operator who is also the cashier.

---

## Why Now

1. **Price transparency is mandatory.** Israeli law (Hok HaMazon, 2022) requires every major retail chain to publish product prices hourly in standardized XML. Competitor price data is free and publicly available — we just use it.

2. **POS exports are standard.** Every POS system used in Israeli convenience stores (Comax, Priority, YomYom) can export a CSV. The data exists — no hardware required.

3. **AI explanation cost has dropped.** Gemini-2.0-flash costs fractions of a cent per explanation. Running AI-assisted ordering for 500 SKU recommendations per day costs less than ₪1 in API fees.

4. **The problem is universal.** Stockouts and overstock are a global convenience retail problem. Israel is a bounded, well-regulated market to prove the model before expanding.

---

## Pricing Hypothesis

| Stage | Price | Rationale |
|---|---|---|
| Pilot (30 days) | Free | Remove barrier to first data. Store provides POS export weekly. |
| Starter | ₪199/month | Up to 1,000 active SKUs. Core reorder + planogram. |
| Standard | ₪299/month | Up to 3,000 SKUs. Competitor intelligence + expiry tracking. |
| Pro | ₪499/month | Unlimited SKUs. Multi-store view. Priority support. |

**Unit economics assumption:** If SmartShelf AI prevents 2 stockouts per week on SKUs with ₪15–20 margin, that is ₪120–160 of recovered margin per week = ₪480–640/month. The Starter plan pays for itself on one prevented stockout.

---

## Measurable Value

| Value Driver | How Measured | Target |
|---|---|---|
| Fewer stockouts | Count of high-risk products going to zero before reorder | -30% over 90 days |
| Less overstock | Count of products exceeding 120% of 30-day demand | -20% over 90 days |
| Fewer expired products | Waste items logged and cleared before expiry | -40% vs. unassisted baseline |
| Faster ordering | Time from opening dashboard to approved purchase order | Under 5 minutes (vs. 30–60 minutes manual) |
| Better shelf allocation | Revenue per sqm in eye-level vs. lower shelves | +10% vs. unoptimized baseline |

---

## Competitive Landscape

| Tool | Who uses it | Gap |
|---|---|---|
| Excel / WhatsApp | Most small stores today | No intelligence, no competitor data, no planogram |
| Comax built-in reports | Comax POS customers | Basic reorder alerts only, no AI, no competitor context |
| Large ERP systems | Chains like Shufersal | Too expensive, too complex for single-store operators |
| SmartShelf AI | Owner-operators | Right-sized: AI-assisted without requiring an IT department |

---

## Risk Factors

| Risk | Mitigation |
|---|---|
| Store owner resistant to new tools | Pilot is free, onboarding is one CSV upload, no hardware required |
| POS export format varies | CSV adapter with column-mapping UI (Phase 2) handles variation |
| Competitor price data changes format | Standardized XML schema is mandated by law — stable |
| Store owner does not trust AI | Explanations are transparent; all recommendations show the reasoning; owner always approves manually |
