# SmartShelf AI

واجهة Hackathon لبناء طبقة قرار ذكية فوق بيانات متجر/كازية من أجل:

- اقتراح طلبات شراء ذكية.
- تحليل المخزون والمخاطر.
- تنظيم الرفوف بصرياً عبر `Planogram`.
- شرح التوصيات بصيغة `Mock AI`.

## Project Docs

- الخطة الأصلية: [SmartShelf_AI_Hackathon_Plan.md](/C:/Users/mshar/Desktop/hackathonsj/SmartShelf_AI_Hackathon_Plan.md)
- خطة السبرنتات: [SPRINTS.md](/C:/Users/mshar/Desktop/hackathonsj/SPRINTS.md)

### Source Semantics

- [Alonit / Super Alonit signal source](docs/sources/alonit_signal_source.md) — what the Dor Alon price-transparency and Wolt delivery catalog sources provide, what they cannot prove, confirmed store IDs, and recommended field semantics

### Competitor Signal Layer

```bash
# Build unified competitor-product signals (Alonit price file + Wolt delivery catalog)
python scripts/build_competitor_product_signals.py

# Print quality metrics after building
python scripts/build_competitor_product_signals.py --print-quality

# Backfill with a fixed timestamp
python scripts/build_competitor_product_signals.py --run-at 2025-05-25T10:00:00+00:00
```

Output: `data/signals/competitor_product_signals/competitor_product_signals_<ts>.parquet`

### YomYom POS Readiness

```bash
# Inspect an incoming YomYom POS CSV before import
python scripts/inspect_yomyom_pos_file.py --input <path-to-pos.csv>

# Import a YomYom POS CSV into internal silver tables
python scripts/import_yomyom_pos.py --input <path-to-pos.csv>

# Generate product recommendations when real POS + matching + competitor signals exist
python scripts/generate_product_recommendations.py

# One command after every new POS export or scrape:
# import (optional) → expiry report → operational recs → dashboard JSON + sources.json
npm run data:refresh                 # or: python scripts/refresh_pipeline.py
npm run data:refresh -- --input data/internal/raw_pos/yomyom/all4shop_Mlai.csv

# Export only the dashboard JSON (public/data/operational.json + sources.json)
npm run data:dashboard               # or: python scripts/export_dashboard_data.py
```

Import outputs:

- `data/internal/silver_pos/yomyom_products.parquet`
- `data/internal/silver_pos/yomyom_sales.parquet`
- `data/internal/silver_pos/yomyom_inventory.parquet`
- `data/internal/silver_pos/yomyom_margins.parquet`
- `reports/quality/yomyom_pos_quality_<timestamp>.json`

Recommendation outputs:

- `data/recommendations/product_recommendations/product_recommendations_<timestamp>.parquet`
- `reports/recommendations/product_recommendations_<timestamp>.md`

### Expiry Tracking at Receiving

The POS inventory export does not include product expiry dates, so expiry is
tracked as a tiny manual layer during receiving. The operator only needs to
record barcode + expiry date; the system joins product name, category, stock,
and prices from the latest POS silver tables.

```bash
# Record one received product expiry
python scripts/record_expiry_scan.py \
  --barcode 7290000041445 \
  --expiry-date 2026-07-20

# Or import a CSV with barcode,expiry_date rows
python scripts/record_expiry_scan.py --input-csv path/to/expiry_scans.csv

# Build expiry alerts and a Markdown report
python scripts/build_expiry_report.py
```

Inputs:

- `data/internal/expiry/expiry_scans.csv`

Outputs:

- `data/signals/expiry/expiry_alerts_<timestamp>.parquet`
- `reports/expiry/expiry_report_<timestamp>.md`

## Current Stack

- React
- Vite
- JavaScript

## Run Locally

```bash
npm install
npm run dev
```

## Current Goal

تحويل هذا الريبو من قالب Vite افتراضي إلى MVP قابل للعرض باسم `SmartShelf AI` يحتوي على:

- Dashboard
- Products view
- Reorder recommendations
- Planogram view
- Approved orders flow

---

## YomYom Market-Intelligence — Python Storage Layer

A local, automated storage foundation for raw data, bronze/silver Parquet, quality
reports, and logs.  **No scraping is included** — this layer is purely the
infrastructure that every future collector will use.

### Folder layout

```
data/
  internal/
    raw_pos/          ← YomYom POS CSV exports (raw)
    silver_pos/       ← cleaned POS Parquet
  external/
    raw/              ← raw HTTP responses & files, partitioned by source/YYYY/MM/DD
    bronze/           ← lightly-typed Parquet per collection run
    silver/           ← cleaned, cross-source Parquet
  matching/           ← barcode / product-name matching tables
  signals/            ← market signals (price gaps, trends, …)
  recommendations/    ← product & planogram recommendation outputs
reports/
  quality/            ← per-run JSON quality reports
logs/                 ← loguru log files (future)
src/
  common/
    paths.py          ← single source of truth for all file paths
    raw_storage.py    ← save_raw_response() / save_raw_file()
    parquet_writer.py ← write_bronze_parquet() / write_silver_parquet()
    schema.py         ← Pydantic models (ExternalProductObservation, …)
    quality.py        ← generate_basic_quality_report()
  internal/
    pos_importer.py   ← full POS import pipeline (schema-map → validate → Parquet → signals)
configs/
  pos_schema_mapping.yaml  ← column mapping, types, validation rules, signal thresholds
scripts/
  init_storage.py             ← one-time folder bootstrap
  smoke_test_storage.py       ← end-to-end storage smoke test
  generate_fake_yomyom_pos.py ← generate realistic fake POS CSV (seed=42, reproducible)
  import_yomyom_pos.py        ← CLI: import a POS CSV into silver Parquet + signals
data/
  internal/
    raw_pos/yomyom/sample_yomyom_pos.csv  ← 121-row fake POS dataset
    silver_pos/
      yomyom_products.parquet   ← master product catalog (barcode, name, category, price…)
      yomyom_sales.parquet      ← sales data (units_sold_7d/30d, revenue)
      yomyom_inventory.parquet  ← stock levels + last purchase date
      yomyom_margins.parquet    ← margin analysis (selling, cost, profit, margin_pct)
  signals/yomyom/
    pos_signals_latest.json     ← always the most recent signal snapshot
    pos_signals_<timestamp>.json← timestamped archive
reports/quality/yomyom_pos/
    yomyom_pos_<timestamp>_quality.json ← per-run quality report
```

### Quick start (Python backend)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create all storage folders (idempotent — safe to re-run)
python scripts/init_storage.py

# 3. Verify the storage layer end-to-end
python scripts/smoke_test_storage.py

# 4. (Re-)generate the fake YomYom POS CSV
python scripts/generate_fake_yomyom_pos.py

# 5. Import the POS CSV → silver Parquet + signals
python scripts/import_yomyom_pos.py \
    --input data/internal/raw_pos/yomyom/sample_yomyom_pos.csv

# with a custom config or fixed timestamp:
python scripts/import_yomyom_pos.py \
    --input       data/internal/raw_pos/yomyom/sample_yomyom_pos.csv \
    --config      configs/pos_schema_mapping.yaml \
    --imported-at 2025-05-25T08:00:00+00:00
```

### POS Import Pipeline — `src/internal/pos_importer.py`

```
CSV
 │
 ├─[1] load_csv()              raw string rows
 │
 ├─[2] apply_schema_mapping()  rename + normalise + type-cast  (driven by YAML)
 │
 ├─[3] validate_rows()         hard rejects + soft warnings
 │       ├─ required fields present
 │       ├─ positive prices / non-negative stock
 │       ├─ margin_pct range [0,100]
 │       └─ cross-field warnings (7d ≤ 30d, cost < sell, margin consistency)
 │
 ├─[4] write_silver_tables()   4 × Parquet (products / sales / inventory / margins)
 │
 ├─[5] generate_pos_quality_report()   enriched JSON quality snapshot
 │       completeness, duplicate names, price stats, margin stats, category dist.
 │
 └─[6] generate_signals()      6 × business signals → JSON
         top_sellers              (top N by units_sold_30d)
         top_profit_products      (top N by gross_profit_30d)
         low_stock_fast_movers    (stock ≤ 15 AND sold_30d ≥ 30)
         slow_movers              (sold_30d ≤ 10)
         high_margin_impulse      (margin ≥ 35% AND impulse category)
         category_sales_summary   (SUM revenue / profit / units per category)
```

All thresholds are in `configs/pos_schema_mapping.yaml` under `signals:`.  
To adapt for the real Comax/Priority CSV: update only the `columns[].raw_name` fields in the YAML.

### Fake POS CSV — `data/internal/raw_pos/yomyom/sample_yomyom_pos.csv`

121 rows across 12 product categories for a neighbourhood market in Kafr Qasim.
Generated with a fixed seed (42) — output is fully reproducible.

| Metric | Value |
|---|---|
| Total rows | 121 |
| Categories | energy_drinks, soft_drinks, water, snacks, chocolate, dairy, coffee_tea, bakery, household, ready_to_eat, juice, candy_gum |
| Missing barcode | ~12 % of rows |
| Missing supplier | ~17 % of rows |
| Duplicate product names | 4 name pairs (data-entry error simulation) |
| Low-stock fast-movers | 5 products (reorder alert candidates) |
| Dead-stock rows | 4 products (0–5 units sold in 30 days) |

Columns: `barcode`, `product_name`, `category`, `brand`, `supplier`,
`selling_price`, `cost_price`, `current_stock`, `units_sold_7d`,
`units_sold_30d`, `sales_amount_30d`, `gross_profit_30d`, `margin_pct`,
`last_sale_date`, `last_purchase_date`

### How a future collector uses this layer

```python
from src.common.raw_storage    import save_raw_response
from src.common.parquet_writer import write_bronze_parquet, write_silver_parquet
from src.common.quality        import generate_basic_quality_report

# 1. Fetch data (your collector logic)
response = httpx.get("https://...")

# 2. Save raw
save_raw_response("wolt", response.url, "GET", response.status_code,
                  dict(response.headers), response.content,
                  response.headers.get("content-type"), observed_at)

# 3. Parse → list of dicts
records = parse(response.content)

# 4. Write Parquet
write_bronze_parquet(records, "wolt", observed_at)
write_silver_parquet(records, "products", observed_at, source_id="wolt")

# 5. Quality report
generate_basic_quality_report(records, "wolt", observed_at)
```
