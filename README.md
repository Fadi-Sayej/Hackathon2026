# SmartShelf AI

واجهة Hackathon لبناء طبقة قرار ذكية فوق بيانات متجر/كازية من أجل:

- اقتراح طلبات شراء ذكية.
- تحليل المخزون والمخاطر.
- تنظيم الرفوف بصرياً عبر `Planogram`.
- شرح التوصيات بصيغة `Agentic AI`.

## Documentation

**Start at [docs/README.md](docs/README.md)** — the map, with the authority chain
PRD → feature intents → feature specs → system design + ADRs → implementation plan.

| Looking for | Go to |
|---|---|
| What the product is, and what is out of scope | [PRD](docs/product/PRD.md) |
| What a feature must observably do | [`docs/features/F#-*/specs/`](docs/features/) |
| How the system is built, and why | [System Design](docs/architecture/system-design.md) · [ADRs](docs/architecture/decisions/) |
| What gets built next, in what order | [Implementation plan](docs/implementation/plan.md) |
| How to deploy and run it | [Operations](docs/operations/deployment.md) |
| What the store owner receives | [Pilot](docs/pilot/handover-yomyom-ar.md) |
| Where the competitor data comes from | [Alonit signal source](docs/sources/alonit_signal_source.md) |
| The rules for working in this repo | [CLAUDE.md](CLAUDE.md) |

Anything under [`docs/archive/`](docs/archive/) is **legacy and non-authoritative**.

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

# One command after every new POS export or scrape: the engine rebuilds silver
# from the committed snapshots, runs its own market chain and sales import, and
# publishes public/data/dashboard.json and catalogue.json (CLAUDE.md rule 5)
npm run data:refresh
npm run data:refresh -- --input data/internal/raw_pos/yomyom/all4shop_Mlai.csv
```

Import outputs:

- `data/internal/silver_pos/yomyom_products.parquet`
- `data/internal/silver_pos/yomyom_inventory.parquet`
- `data/internal/silver_pos/yomyom_margins.parquet`
- `reports/quality/yomyom_pos_quality_<timestamp>.json`

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

- React + Vite (frontend)
- Python 3 + pyarrow/polars (data pipelines) — no virtualenv; see `setup.sh`

## Run Locally

```bash
npm install
npm run dev
```

## YomYom Market-Intelligence — Python Storage Layer

A local, automated storage foundation for raw data, bronze/silver Parquet, quality
reports, and logs. The collectors that use it now run daily in
`.github/workflows/collect-daily.yml`.

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
  internal_pos/
    pos_importer.py   ← POS CSV → silver Parquet + quality report (the live importer)
configs/
  pos_schema_mapping.yaml  ← column mapping, types, validation rules, signal thresholds
scripts/
  init_storage.py             ← one-time folder bootstrap
  smoke_test_storage.py       ← end-to-end storage smoke test
  generate_fake_yomyom_pos.py ← generate realistic fake POS CSV (seed=42, reproducible)
  import_yomyom_pos.py        ← CLI: import a POS CSV into silver Parquet + signals
data/
  internal/
    silver_pos/
      yomyom_products.parquet   ← master product catalog (barcode, name, category, price…)
      yomyom_sales.parquet      ← sales data (units_sold_7d/30d, revenue)
      yomyom_inventory.parquet  ← stock levels + last purchase date
      yomyom_margins.parquet    ← margin analysis (selling, cost, profit, margin_pct)
reports/quality/
    yomyom_pos_<timestamp>.json ← per-run quality report
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

### POS Import Pipeline — `src/internal_pos/pos_importer.py`

CSV → schema mapping (`configs/pos_schema_mapping.yaml`) → validation → four silver
Parquet tables + a quality report in `reports/quality/`. To adapt it for a different
POS export, change only the `columns[].raw_name` fields in the YAML.

Where it sits in the wider flow: [System Design §3](docs/architecture/system-design.md).

### How a collector uses this layer

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
