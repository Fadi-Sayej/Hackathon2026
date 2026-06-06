Read these files before doing anything:
- CLAUDE.md
- STATUS.md
- sprint_plan.md
- configs/pos_schema_mapping.yaml
- src/internal/pos_importer.py

You are working on Person A's tasks from sprint_plan.md: getting the real YomYom inventory through the pipeline and producing the barcode match file.

ALREADY DONE (do not redo):
- A-2 is complete. configs/pos_schema_mapping.yaml already has the Hebrew candidates (תאור פריט, שם מחלקה, מלאי נוכחי). The importer already strips trailing spaces from headers and clamps negative stock to 0.
- The import was already run against the root yomyom-inventory.csv and produced 6,289 rows across 4 Parquet files in data/internal/silver_pos/.

YOUR REMAINING TASKS IN ORDER:

A-0: Run `python scripts/init_storage.py` to make sure all data directories exist.

A-1: Copy yomyom-inventory.csv from the project root to the canonical pipeline location:
  cp yomyom-inventory.csv data/internal/raw_pos/yomyom/yomyom_inventory_real.csv
Then re-run the import against this canonical path:
  python scripts/import_yomyom_pos.py --input data/internal/raw_pos/yomyom/yomyom_inventory_real.csv
Confirm 4 Parquet files exist in data/internal/silver_pos/.

A-3: Write reports/yomyom_real_import_notes.md. Use polars to read data/internal/silver_pos/yomyom_products.parquet and report: total rows imported, rows with negative stock (should be 0 after clamping), rows with null barcode, rows with null category. Also note that sales columns (units_sold_7d, units_sold_30d) are all null since the inventory CSV doesn't have sales history.

A-4: Create scripts/join_yomyom_kaggle.py exactly as specified in sprint_plan.md (the full script is already written out there — copy it verbatim). Do not run it yet — it depends on Person B completing B-2 first. When Person B says B-2 is done, run: python scripts/join_yomyom_kaggle.py and confirm data/matching/barcode_matches.parquet is produced with >0 rows.

Only work on tasks A-0 through A-4. Do not touch frontend files, App.jsx, or any file not mentioned here.