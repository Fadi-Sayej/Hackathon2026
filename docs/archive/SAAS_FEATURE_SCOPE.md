> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# SmartShelf AI — Feature Scope

## Current MVP (exists in the running app today)

Everything listed below is demonstrable in the running app at `http://localhost:5173`.

### Data Layer
- Demo dataset: 7,674 real YomYom Hebrew product records (loaded at startup)
- CSV upload connector: owner can upload their own POS export
- Competitor price dataset: mock neighborhood snapshot (6 barcodes, 4 chains, real price format)
- Market context: live Open-Meteo weather + Nager.Date holidays with static fallback

### Analytics
- Inventory risk scoring (stockout days, velocity, overstock ratio)
- Reorder recommendation engine (prioritized list with confidence scores)
- Planogram engine (shelf assignment by velocity, margin, capacity)
- Affinity / cross-merchandising engine
- Competitor intelligence (price leaders, stockout opportunities, price-protection alerts)

### User Workflow
- Dashboard with 6 KPI cards
- Product search + category filter
- Approve / reject / edit quantity on each recommendation
- Approved Orders: supplier grouping, subtotals, total, CSV export, print
- Planogram: visual shelf layout, slot detail panel, photo upload (mock vision)
- Expiry tracking (manual barcode + date entry)
- Operational risk view
- AI Report page

### AI Explanations
- Rule-based explanations (default, always available)
- Gemini-2.0-flash explanations via proxy (available when `VITE_LLM_PROXY_URL` is set)

### Persistence
- Browser localStorage: approved orders, recommendation decisions persist across refresh
- Reset demo state button clears all overrides

---

## SaaS Roadmap (planned, not built)

These features do not exist in the current app. They appear here only as a credible post-hackathon direction.

### Phase 2 — Portable Data Import
- CSV schema auto-detection (support Comax, Priority, and generic POS exports)
- Store profile creation (store name, location, category mix)

### Phase 3 — Cloud Persistence and Accounts
- Supabase backend: store accounts, product snapshots, order history
- Manager vs. staff permission levels
- Order history and approval audit trail

### Phase 4 — Live Market Signals (architecture already present)
- Live weather integration (Open-Meteo, free)
- Live holiday calendar (Nager.Date, free)
- GDELT news events integration (free)
- Israeli retail price portal (Hok HaMazon XML feed) — real competitor prices

### Phase 5 — RAG-Based Explanations (corpus structure already present)
- Vector embeddings of product knowledge, category playbooks, and reorder rules
- Semantic retrieval before LLM explanation generation
- Confidence-ranked context injection

### Phase 6 — Multi-Store Analytics
- Chain-level dashboard (aggregate across multiple store locations)
- Store comparison (which store runs out of which category fastest)
- Shared planogram templates

### Phase 7 — Supplier Integration
- Direct purchase order submission via supplier API
- Order confirmation and delivery tracking
- Automated reorder triggers when stock crosses threshold

---

## Separation Guarantee

No SaaS roadmap feature has been partially built. The boundary is explicit: Phase 1 = current app. Everything after Phase 1 is future work.
