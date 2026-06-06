Read these files before doing anything:
- CLAUDE.md
- STATUS.md
- sprint_plan.md
- scripts/download_kaggle_datasets.py
- scripts/import_kaggle_supermarkets.py
- src/external/kaggle_supermarket_importer.py

You are working on Person B's tasks from sprint_plan.md: downloading Kaggle competitor price data, importing it, and writing the export script.

YOUR TASKS IN ORDER:

B-1: Check that KAGGLE_API_TOKEN is set in .env. If it's missing, stop and ask the team for it — nothing else works without it. Once set, run:
  python scripts/download_kaggle_datasets.py
Verify these files exist in data/raw/kaggle/israeli-supermarkets-2024/:
  price_full_file_dor_alon.csv, price_full_file_rami_levy.csv, price_full_file_shufersal.csv
  store_file_dor_alon.csv, store_file_rami_levy.csv, store_file_shufersal.csv

B-2: Run:
  python scripts/import_kaggle_supermarkets.py
Verify Parquet files exist in all three directories:
  data/external/silver/products/kaggle_dor_alon/
  data/external/silver/products/kaggle_rami_levy/
  data/external/silver/products/kaggle_shufersal/
Once B-2 is done, tell Person A — they are waiting to run join_yomyom_kaggle.py.

B-3: Create scripts/export_competitor_market_data.py exactly as specified in sprint_plan.md (the full script is already written there — copy it verbatim). Do not run it yet — it depends on Person A completing A-4 first (produces data/matching/barcode_matches.parquet). When Person A says A-4 is done, run:
  python scripts/export_competitor_market_data.py
Confirm src/data/marketData.js is created with at least one competitor store and barcodes. Then run npm run build to make sure the frontend still compiles. Once done, tell Person C — they are waiting to switch the import in App.jsx.

Only work on tasks B-1 through B-3. Do not touch frontend files or Python pipeline files not mentioned here.