# YomYom Real Import — Quality Notes (A-3)

Quality summary of the real YomYom POS import into the silver layer.

- **Source file:** `all4shop_Mlai.csv` (canonical path: `data/internal/raw_pos/yomyom/all4shop_Mlai.csv`)
- **Imported at:** 2026-06-06T11:51:58Z
- **Silver tables:** `data/internal/silver_pos/yomyom_{products,inventory,sales,margins}.parquet`

## Row counts

| Metric | Count | Source table |
|--------|------:|--------------|
| Total rows imported | **7,674** | products |
| Rows with negative stock | **625** | inventory (`current_stock < 0`) |
| Rows with missing/empty barcode | **307** | products (`barcode` null/empty) |
| Rows with no category | **0** | products |
| Rows with zero/null selling price | **223** | products |
| Rows with zero/null cost price | **1,270** | products (1,268 zero + 2 null) |

## Notes

- **Negative stock (625):** kept as-is in the silver layer (not clamped to 0) so downstream
  quality checks and the `CHECK_NEGATIVE_STOCK` operational recommendation can surface them.
  This is close to the expected ~627.
- **Missing barcode (307):** these items cannot be matched against competitor data or scanned
  for expiry; they drive the `VERIFY_UNKNOWN_BARCODE` recommendation. Matches expected ~307.
- **Zero/null cost (1,270):** large share of the catalog has no cost price, so margin-based
  signals are only available for the ~84% of rows that do carry a cost.
- **Sales columns are all null:** `units_sold_7d` and `units_sold_30d` have **0** non-null
  values — the inventory CSV carries no sales history. Any signal that depends on sales
  velocity (reorder, slow/fast movers) will be empty until a sales export is provided.

## How to reproduce

```python
import polars as pl
prod = pl.read_parquet("data/internal/silver_pos/yomyom_products.parquet")
inv  = pl.read_parquet("data/internal/silver_pos/yomyom_inventory.parquet")
print(len(prod))                                                   # 7674
print(inv.filter(pl.col("current_stock") < 0).height)              # 625 negative stock
print(prod.filter(pl.col("barcode").is_null()).height)             # 307 missing barcode
print(prod.filter(pl.col("category").is_null()).height)            # 0 no category
```
