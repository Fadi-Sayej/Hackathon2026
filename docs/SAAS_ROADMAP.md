# SmartShelf AI — SaaS Roadmap

Post-hackathon evolution path. Each phase builds on the previous one without breaking it.

---

## Phase 1 — Local-First Prototype (CURRENT)

**Status:** Complete. This is the running app today.

- Single-user, browser-only
- 7,674 real YomYom SKUs loaded at startup
- Full analytics pipeline: inventory risk, reorder recommendations, planogram
- Approve/reject/edit quantity workflow
- localStorage persistence (survives refresh)
- Rule-based AI explanations (Gemini proxy available locally)
- Mock competitor pricing (neighborhood snapshot, 6 barcodes × 4 chains)
- Market context (live free APIs or static fallback)
- CSV export and print for approved orders
- No backend, no auth, no database

**Value delivered:** Proves the core decision workflow end-to-end.

---

## Phase 2 — Portable Data Import

**Status:** Architecture ready, not yet deployed.

- CSV schema auto-detection (Comax, Priority ERP, and generic POS exports)
- Column mapping UI (owner maps their column names once)
- Store profile setup (store name, location, product category mix)
- Validation report on import: missing barcodes, negative stock, price anomalies
- Support multiple POS export formats without code changes

**Value delivered:** Any store can plug in their own data without engineering help.

---

## Phase 3 — Cloud Persistence and Store Accounts

**Status:** Persistence abstraction built (`src/lib/persistence/persistence.js`); Supabase adapter not yet wired.

- Supabase backend: stores, products, inventory snapshots, sales history, recommendations, approved orders
- Email/password or Google SSO auth
- Manager vs. staff permission levels
- Order history and approval audit trail
- Cross-device access (tablet in store, laptop in office)

**Tables:** `stores`, `products`, `inventory_snapshots`, `sales_history`, `recommendations`, `approved_orders`

**Value delivered:** Store owner can check status from any device; order history creates institutional memory.

---

## Phase 4 — Live Market Signals

**Status:** Adapter architecture complete (`src/lib/context/marketContextAdapter.js`); live APIs work with one env variable.

- Open-Meteo weather (free, no key) → affects cold drink and seasonal product urgency
- Nager.Date Israeli holiday calendar (free) → affects pre-holiday stocking
- GDELT news/events (free) → local event demand spikes
- Israeli retail price portal (Hok HaMazon XML feeds) → real hourly competitor prices per chain

**Value delivered:** Recommendations reflect actual market conditions, not static assumptions.

---

## Phase 5 — RAG-Based Explanations

**Status:** Corpus structure built (`data/processed/rag/`); vector search not yet implemented.

- Embed product knowledge, category playbooks, reorder rules, and planogram rules
- Semantic retrieval of relevant context before Gemini call
- Confidence-ranked chunks injected into prompt
- Explanation quality improves as corpus grows
- No behavior change for offline or no-proxy mode (rule-based fallback unchanged)

**Value delivered:** Explanations become more contextual, more specific to the store's category mix.

---

## Phase 6 — Multi-Store Analytics

**Status:** Not started. Architecture not yet designed.

- Chain-level dashboard: aggregate KPIs across all owned locations
- Store comparison: which location runs out of which category fastest
- Shared planogram templates: chain-level rules with per-store overrides
- Category performance benchmarking: compare store against chain average

**Value delivered:** A gas station chain owner can manage 10 stores from one screen.

---

## Phase 7 — Supplier Integration

**Status:** Not started. UI placeholder exists ("Send to Supplier" button).

- Direct purchase order submission via supplier EDI or email API
- Order confirmation and delivery tracking
- Automated reorder trigger when stock crosses threshold (configurable per SKU)
- Supplier catalog sync (price updates flow in automatically)

**Value delivered:** Ordering becomes fully automated for high-confidence, high-frequency SKUs.

---

## Timeline Hypothesis

| Phase | Estimated Effort | Milestone |
|---|---|---|
| Phase 1 | Done | Hackathon demo |
| Phase 2 | 2–3 weeks | Pilot onboarding (any store can use it) |
| Phase 3 | 4–6 weeks | First paying stores |
| Phase 4 | 2 weeks | Differentiation from manual tools |
| Phase 5 | 4–6 weeks | Explanation quality competitive with human analyst |
| Phase 6 | 6–8 weeks | Chain-level product launch |
| Phase 7 | 3–4 months | Full automation for routine orders |
