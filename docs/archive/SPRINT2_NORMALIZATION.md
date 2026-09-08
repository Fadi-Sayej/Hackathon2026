> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# Sprint 2 Normalization

Sprint 2 converts raw retail datasets into the SmartShelf application schema.

## Command

```bash
npm run normalize:data
```

## What the script does

1. scans `data/raw/` recursively for `.csv` and `.json` files
2. scores the discovered files based on filename and header fit
3. chooses the best source for SmartShelf normalization
4. maps it into the SmartShelf product schema
5. writes outputs to:
   - `data/processed/demo/demo-products.json`
   - `data/processed/analytics/normalized-products.json`
   - `data/processed/analytics/analytics-summary.json`
   - `data/processed/analytics/normalization-report.json`
   - `data/exports/sample-app-data/demo-products.json`

## Important behavior

If no raw dataset files exist yet, the script uses a built-in fallback retail sample.

This fallback is intentional so Sprint 2 can execute cleanly today, while still allowing the same pipeline to switch to real raw files later without changing the command.

## Expected raw file placement

Use these locations when you download real datasets:

- Hugging Face: `data/raw/huggingface/`
- Kaggle: `data/raw/kaggle/`

## SmartShelf schema target

Each normalized product is mapped to:

- `id`
- `name`
- `category`
- `currentStock`
- `shelfQuantity`
- `shelfCapacity`
- `salesLast7Days`
- `salesLast30Days`
- `price`
- `cost`
- `expiryDate`
- `supplier`
- `leadTimeDays`
- `returnedUnits`
- `damagedUnits`

## Generated values

If the source does not contain enough fields, the script safely generates:

- `cost`
- `leadTimeDays`
- `shelfCapacity`
- `shelfQuantity`
- `supplier`
- `expiryDate` for perishable categories

All generated-field decisions are recorded in `normalization-report.json`.
