# CLAUDE.md

Guidance for Claude Code working in this repo.

**Read [ARCHITECTURE.md](ARCHITECTURE.md) first.** It is the only traced description
of how the pipelines fit together. This file is the rules; that file is the map.

Anything in `docs/archive/` is retained for history and is **out of date** — it
describes modules that no longer exist. Do not act on it.

## The 13 rules

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

9. **CI commits only `data/external/snapshots/`; `silver/` is derived, never
   committed.** The signal builder reads `silver/`, so `data:refresh` rebuilds it
   from those snapshots first (`scripts/rehydrate_silver.py`). Do not "fix" a stale
   market half by committing `silver/` — the same bytes are already in the
   snapshots. If competitor counts look wrong, run `data:refresh`, not the
   collector.

10. **An empty export is a failure, not a result.** `export_dashboard_data.py`
    raises `EmptyExportError` before writing when either recommendation family is
    empty — a clean clone once overwrote a committed 3,035-recommendation file with
    0 and exited 0. Pass `--allow-no-competitor` only for a deliberate POS-only run.

11. **Verify before you document.** Counts in this repo drifted badly: docs claimed
    14,406 barcode matches where the artifact holds 2,848, and 2,183 recommendations
    where the exporter emits 3,035. Read the parquet or the JSON, never another
    markdown file.

12. **A new signal is not done until it has moved something.** Four times now a
    signal has been built, unit-tested, labelled working, and changed nothing:
    the market pipeline nobody ran, demand multipliers keyed in English against a
    Hebrew catalogue, owner answers keyed on the product id while Python keys on
    barcode, and the shelf-life table dropped by the context adapter. Every unit
    test passed through all four, because each supplied the input directly and
    never crossed the boundary where it was lost. Run `npm run check:signals`: it
    diffs real recommendations with the signal on and off and fails when a present
    input changes nothing. When the input is legitimately absent today it injects
    a synthetic probe instead, so the wiring is proven before the real data
    arrives. It runs in `collect-daily.yml` before the dashboard is committed.

13. **The seven sales reports are MONTHLY, and that caps what T8 can claim.** One
    row per product per month, no date column in any of the seven files — so STL
    decomposition (7 points, needs 2 seasonal cycles) and weekday/payday cycles
    are **not measurable**, which is different from "measured and not
    significant". `scripts/analyse_sales_movement.py` reports which of the two it
    is. Calendar effects are measured on a department's **share** of monthly
    volume (store-wide volume swings ~40% month to month) and **controlled for a
    linear time trend** — that control is load-bearing: Ramadan falls in months
    2-3 of a Jan-Jul series, so exposure is nearly collinear with seasonal drift,
    and beverages read as a ×0.82 Ramadan suppression when they were simply
    rising into summer. Windows live in `configs/calendars.yaml`, unverified
    until someone signs the `verified_by` field. The reports cover **24.3% of the
    catalogue**; the other 75.7% have no sales rows and are reported as `none`,
    never as zero.


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
npm run test           # 457 JS tests
npm run test:py        # 317 Python tests
npm run lint
python3 scripts/analyse_sales_movement.py   # T8: measured calendar weights
git mine               # log without the daily snapshot commits
```

Commit style: small, imperative subject, body explains *why*. The daily
`snapshot: market data` commits are machine-authored — `git mine` hides them.
