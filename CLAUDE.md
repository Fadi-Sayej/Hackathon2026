# CLAUDE.md

Guidance for Claude Code working in this repo.

**Read [ARCHITECTURE.md](ARCHITECTURE.md) first.** It is the only traced description
of how the pipelines fit together. This file is the rules; that file is the map.

Anything in `docs/archive/` is retained for history and is **out of date** — it
describes modules that no longer exist. Do not act on it.

## The 10 rules

1. **Run Python from the repo root.** Scripts insert the repo root into `sys.path`
   themselves (`sys.path.insert(0, ROOT)`); `src` is a namespace package with no
   install step. `cd` elsewhere and every `from src...` import fails.

2. **There is no virtualenv.** `setup.sh` installs with
   `pip install -r requirements.txt --break-system-packages`. CI pins Python 3.11;
   local 3.9.6 works (Google libs emit a FutureWarning — harmless). Do not add venv
   activation to instructions; nothing in the repo creates one.

3. **The live POS importer is `src/internal_pos/pos_importer.py`.** The 892-line
   `src/internal/pos_importer.py` was deleted on 2026-09-05 as unreachable. Its
   siblings `src/internal/receiving.py` and `restock_reconcile.py` are live — do not
   confuse the package with the deleted module.

4. **The pipelines couple through the filesystem, by mtime.**
   `export_dashboard_data.py` globs the newest `operational_recommendations_*.parquet`
   and `product_recommendations_*.parquet`. **A missing directory is not an error** —
   the export succeeds and silently reports `competitorSignals: 0`. If the dashboard
   looks thin, check the directories exist before debugging the code.

5. **`npm run data:refresh` is the one command** after new POS data or a scrape. It
   runs the competitor-signal → matching → product-recommendation chain, then expiry,
   then the exporter — in dependency order, because each stage reads the previous
   stage's parquet. `--skip-market` does a POS-only refresh. `data:dashboard` runs the
   exporter alone and leaves the market half stale.

6. **`data/**` is gitignored; `public/data/operational.json` is committed.** A fresh
   clone has the dashboard JSON and nothing to rebuild it from. Regenerating requires
   importing the POS CSV first (`scripts/import_yomyom_pos.py --input <csv>`).

7. **`normalize:data` will overwrite committed frontend data.** With
   `data/internal/silver_pos/` absent (its normal state on a fresh clone) it falls
   back to a ~30-product demo set and overwrites `src/data/demoProducts.js` and five
   other committed generated files. It refuses unless you pass
   `-- --allow-demo-fallback`. Never pass that flag to "make it run".

8. **Never sum a per-sale figure with a one-off figure.** `actionPriority.js` splits
   them deliberately (`IMPACT_KIND`). Adding them once produced a meaningless
   "₪106,164 per sale" headline. Related: signals derived from stock *quantities*
   carry no shekel figure at all, because the store manager told us the counts are
   unreliable in both directions. When a number cannot be stated honestly, the UI
   shows **no number**, not zero.

9. **CI commits only `data/external/snapshots/`.** The daily collector also writes
   `bronze/` and `silver/`, but the workflow `git add -f`s just `snapshots/`. The
   signal builder reads `silver/`, so daily collection does **not** reach the product
   on its own — `silver/` only advances when someone runs the collectors locally.

10. **Verify before you document.** Counts in this repo drifted badly: docs claimed
    14,406 barcode matches where the artifact holds 2,848, and 2,183 recommendations
    where the exporter emits 3,035. Read the parquet or the JSON, never another
    markdown file.

## Layout

- `src/` (Python) — `internal_pos/` POS import · `signals/` competitor signals ·
  `matching/` product matching · `recommendations/` both recommendation families ·
  `external/` connectors · `common/` paths and status · `expiry/`, `internal/`
  receiving · `mcp_server/` price server (launched by `.mcp.json`).
- `src/` (JS) — `pages/` one file per screen · `lib/analytics/` ranking and money
  rules · `lib/dataAdapters/` reads `public/data/*.json` · `lib/i18n/` he/en · `data/`
  generated, committed.
- `scripts/` — 57 entry points. Only the handful in ARCHITECTURE.md are the product.

## Commands

```bash
npm run dev            # Vite dev server
npm run data:refresh   # rebuild every dashboard input (see rule 5)
npm run test           # 377 JS tests
npm run test:py        # 270 Python tests
npm run lint
git mine               # log without the daily snapshot commits
```

Commit style: small, imperative subject, body explains *why*. The daily
`snapshot: market data` commits are machine-authored — `git mine` hides them.
