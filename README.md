# SmartShelf AI

واجهة Hackathon لبناء طبقة قرار ذكية فوق بيانات متجر/كازية من أجل:

- اقتراح طلبات شراء ذكية.
- تحليل المخزون والمخاطر.
- تنظيم الرفوف بصرياً عبر `Planogram`.
- شرح التوصيات بصيغة `Mock AI`.

## Project Docs

- الخطة الأصلية: [SmartShelf_AI_Hackathon_Plan.md](/C:/Users/mshar/Desktop/hackathonsj/SmartShelf_AI_Hackathon_Plan.md)
- خطة السبرنتات: [SPRINTS.md](/C:/Users/mshar/Desktop/hackathonsj/SPRINTS.md)

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
scripts/
  init_storage.py     ← one-time folder bootstrap
  smoke_test_storage.py ← end-to-end pipeline smoke test
```

### Quick start (Python backend)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create all storage folders (idempotent — safe to re-run)
python scripts/init_storage.py

# 3. Verify the full pipeline end-to-end
python scripts/smoke_test_storage.py
```

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
