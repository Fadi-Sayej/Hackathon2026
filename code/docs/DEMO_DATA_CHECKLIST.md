# Pre-Demo Data Checklist (Person 1 — Data Pipeline + POS + Expiry)

Run this top-to-bottom before the demo to guarantee the data layer is real and consistent.

## 0. One official command (does everything)

```bash
# Import the store POS export → expiry report → operational recs → dashboard JSON + sources.json
npm run data:refresh -- --input data/internal/raw_pos/yomyom/all4shop_Mlai.csv
```

If the canonical CSV is missing, copy it first:
```bash
mkdir -p data/internal/raw_pos/yomyom
cp yomyom-inventory.csv data/internal/raw_pos/yomyom/all4shop_Mlai.csv
```

## 1. Expiry sample (so the Expiry page is not empty)

```bash
python3 scripts/record_expiry_scan.py --input-csv samples/sample_expiry_scans.csv
npm run data:refresh        # re-export so buckets/alerts update
```
Committed sample lives at `samples/sample_expiry_scans.csv` (5 rows across all buckets + 1 unknown barcode).

## 2. Smoke test — must be 6/6

```bash
npm run test:pipeline
```
Expect: `6/6 passed`, including `snapshot_comparison status=ok` (needs ≥2 POS imports).

## 3. Expected numbers (real `all4shop_Mlai.csv`, 2026-06-06)

| Artifact | Expected |
|----------|----------|
| POS products | **7,674** |
| Recommendations total | ~**2,340** (operational ~2,188 + competitor 152) |
| CHECK_WOLT_PRICE_GAP | 1,147 |
| CHECK_NEGATIVE_STOCK | 625 |
| CHECK_MARGIN | 104 |
| VERIFY_UNKNOWN_BARCODE | 308 (307 no-barcode + 1 unknown expiry scan) |
| PROMOTE_EXPIRING_PRODUCT | 4 (known-in-POS scans) |
| Expiry buckets | expired 1 · critical 2 · warning 1 · upcoming 1 |
| Barcode matches (competitor) | 7,203 (dor_alon 2,602 · rami_levy 2,415 · shufersal 2,186) |

## 4. Source status must read true

```bash
python3 -c "import json; d=json.load(open('public/data/sources.json')); print(d['scraping_status']); [print(s['source_id'], s['status'], s['row_count']) for s in d['sources'].values()]"
```
Expect `scraping_status: complete` with: yomyom_pos, kaggle_* (×3), wolt_delivery, alonit_prices = `complete`; expiry_scans = `complete` after step 1.

## 5. Files that must exist before the demo

- `data/internal/silver_pos/yomyom_{products,inventory,sales,margins}.parquet`
- `data/matching/barcode_matches.parquet` (competitor join — Person 3 / Kaggle)
- `public/data/operational.json` + `public/data/sources.json`
- `reports/yomyom_real_import_notes.md`
- `src/data/marketData.js` (real competitor data — Person 3)

> Note: `public/data/*.json`, `data/**`, and `src/data/marketData.js` are gitignored — they are generated locally. Always run step 0 on the demo machine.

## 6. Frontend

```bash
npm run dev        # http://localhost:5173 → Operational Risks + Expiry Tracking pages
```
