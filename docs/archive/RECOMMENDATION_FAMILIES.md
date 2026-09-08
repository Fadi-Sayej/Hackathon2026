> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# Recommendation Families — How They Fit Together

The project produces recommendations from **three** code paths. They are complementary,
not duplicates. This note exists so they don't get confused or re-implemented.

| Family | Module | Needs competitor data? | Output | Surfaced in |
|--------|--------|------------------------|--------|-------------|
| **Operational** | `src/recommendations/operational_recommendations.py` | No | `data/recommendations/operational_recommendations/*.parquet` | Operational Risks page (`family: operational`) |
| **Competitor** | `src/recommendations/product_recommendations.py` | Yes (matching + signals) | `data/recommendations/product_recommendations/*.parquet` | Operational Risks page (`family: competitor`) |
| **Reorder / planogram** | `src/lib/analytics/*.js` (frontend) | No | computed in-browser | Dashboard / Recommendations / Planogram pages |

## What each is for

- **Operational** — internal POS hygiene + risk: expiry, WOLT-vs-shelf price gaps,
  negative stock, thin/negative margin, missing barcodes. Works on the real POS export
  today, no competitor data required. The demo-safe, always-available family.
- **Competitor** — needs `data/matching/*` linking YomYom products to competitor signals.
  Emits PRICE_CHECK / REORDER / WATCH_PRODUCT once scraping + matching complete.
- **Reorder/planogram (JS engines)** — the original frontend analytics, driven by the
  product catalog (synthetic demo today; switches to real YomYom via Person C's C-3).

## The single dashboard contract

`scripts/export_dashboard_data.py` merges the **Operational** and **Competitor** families
into one JSON (`public/data/operational.json`), tagging every row with
`recommendation_family`. The Operational Risks page filters by family, so the two never
collide. The JS reorder engine stays on its own pages.

## Avoiding duplication

- Price gaps come from **two** angles on purpose: `CHECK_WOLT_PRICE_GAP` (internal shelf
  vs the store's own WOLT price) is **not** the same as competitor `PRICE_CHECK` (YomYom
  vs a rival chain). Keep both; label them by family in the UI.
- Reorder logic lives in the JS engine only — do not add a Python REORDER to the
  operational engine. (The competitor family may emit REORDER from competitor demand.)
