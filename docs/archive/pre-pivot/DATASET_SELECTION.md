# Dataset Selection

This document captures the Sprint 1 selection outcome for SmartShelf AI.

## Selected sources

### Primary MVP source

- `anirudhchauhan/retail-store-inventory-forecasting-dataset`

Why:

- Most aligned with inventory, sales, and reorder reasoning.
- Best candidate for mapping into the SmartShelf product schema with minimal distortion.
- Likely to reduce the amount of synthetic field generation required.

### Backup MVP source

- `andrexibiza/grocery-sales-dataset`

Why:

- Good fallback if the primary source has missing structure or awkward column semantics.
- Still close enough to retail sales logic to support a believable SmartShelf demo.

### Secondary analytics and RAG source

- `Dingdong-Inc/FreshRetailNet-50K`

Why:

- Useful as a richer reference source for future summaries, product context, and retrieval-oriented documents.
- Better reserved for analytics and RAG preparation than for direct MVP app rendering.

## Deferred sources

- `m5-forecasting-accuracy`
- `favorita-grocery-sales-forecasting`
- `demand-forecasting-kernels-only`
- `retailrocket/ecommerce-dataset`

These remain useful references, but they are not the fastest path to the first SmartShelf demo slice.

## Storage policy

For now:

- raw files stay in `data/raw/`
- normalized outputs go to `data/processed/`
- app-ready exports go to `data/exports/sample-app-data/`

Later:

- if RAG and persistent backend become real requirements, move to Supabase
- do not introduce Firebase unless a separate product requirement appears
