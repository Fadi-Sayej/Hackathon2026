---
ID: NIGHTLY-2026-09-13
Title: The first nightly after the Phase 0/1 merge, and what it was hiding
Status: Ready for review
Owner: smartshelf-platform
Parent: [docs/operations/deployment.md](../operations/deployment.md)
Inputs: [.github/workflows/collect-daily.yml, scripts/refresh_pipeline.py, src/recommendations/product_recommendations.py, src/engine/run.py, public/data/dashboard.json, GitHub Actions run 34732869694]
Updated: 2026-09-13
---

# The first nightly after the Phase 0/1 merge

`collect daily market snapshot` had been green every night since 2026-09-04. It went red on
run [34732869694](https://github.com/Fadi-Sayej/Hackathon2026/actions/runs/34732869694),
2026-09-13T02:22Z — the first scheduled run after the Phase 0/1 work merged to `main` on
09-12 between 16:47 and 17:09.

The red build was the smaller of the two faults it exposed.

## 1. What went red

```
step product_recommendations  status readiness_only
  missing POS table: yomyom_sales.parquet
step dashboard_export         status error
  EmptyExportError: refusing to overwrite public/data/operational.json with an
  empty export: zero competitor recommendations
```

`src/recommendations/product_recommendations.py` lists four required silver tables in
`POS_FILES`, one of which is `silver_pos/yomyom_sales.parquet`. **Task 0.6 deleted that
table on purpose.** `tests/internal_pos/test_pos_importer.py:29` asserts it must not
exist. The sales importer now writes `sales_monthly.parquet` and `sales_summary.parquet`
instead.

So the recommender asked for a table the repository has decided should not exist, got
nothing, returned `readiness_only`, and the exporter correctly refused to write an empty
`operational.json` (rule 10 working as designed).

### Why it cannot be repaired

Not a rename. The recommender needs two columns that the new tables deliberately do not
carry:

| Column | Where it came from | Why it is gone |
|---|---|---|
| `units_sold_30d` | the old sales importer | Synthesised from a **monthly mean**. The seven reports are monthly and cover 24.3% of the catalogue — rule 13. Task 0.6 removed the synthesis, not the name |
| `demand_per_day_corrected` | `scripts/build_velocity_from_snapshots.py` | That script has **never** been run by this workflow, so `corrected_monthly_demand()` has always returned `None` on a runner |

Rebuilding the table re-introduces exactly the invented figure Phase 0 removed. Passing
`--allow-no-competitor` to get a green export is rule 10. There is no third option, so
`refresh_pipeline.py` **stops running in the nightly** rather than being propped up.

`public/data/operational.json` freezes at its last good value. That is the correct state
for a rollback target (design §20.2): after the Task 2.7 cut-over no V1 page imports
`loadOperationalData` — only `src/telemetry/` does — so nothing the owner opens reads it.
Phase 4 deletes the chain.

## 2. What it was hiding — the serious one

Two faults that the red build made visible, neither of which would have failed a build:

**The engine ran after the gate.** `run_engine()` drives its own market chain
(`market_context`, `rehydrate_silver`, `competitor_signals`, `product_matching`) and its
own sales import, and reads nothing `refresh_pipeline.py` produces — verified by grepping
`src/engine/` for any reference to `data/recommendations/`: there is none. Yet the engine
step sat *after* `Fail on a degraded refresh`. A failure in a chain the engine does not use
stopped the engine from running at all.

**Nothing ever committed the artefact.** The engine published `public/data/dashboard.json`
into the runner's workspace every night, `check_v1_signals.py` read it, and the job then
threw it away. No step added it to a commit — `git add` named only
`operational.json`, `market-context.json` and `sources.json`.

Before the cut-over that was invisible, because the browser read `operational.json`. After
it, the owner's screen could only ever show whatever artefact a human last committed by
hand. The committed `dashboard.json` at the time of this incident carried
`generated_at: 2026-09-12T13:21:36Z`, from commit `4ffcd5f` — a hand publish.

**This is rule 12 at the top of the pipeline.** The engine ran nightly, produced a correct
artefact, and moved nothing.

## 3. What changed

`ebbe58f`, `.github/workflows/collect-daily.yml`:

| | Before | After |
|---|---|---|
| Engine position | after the legacy gate | first, gated on nothing |
| `dashboard.json` | never committed | committed nightly, with `market-context.json` |
| `check_v1_signals.py` | `continue-on-error: true` | **blocking** |
| `check_independence.py` | `continue-on-error: true` | **blocking** |
| `refresh_pipeline.py` | ran nightly | removed |
| `import_yomyom_sales.py` | called, then called again by the engine | removed; the engine's own import does it |

The two probes were made blocking because the note already in the file said they would
become so at the cut-over. Both run in `mode="print"` against `tempfile.TemporaryDirectory`
copies, so neither can touch the file about to be committed. Both had **never run in CI** —
the 09-12 nightly predates the merge that added them — so both were verified locally first
(exit 0), and the probe skips any capability that is not `available` at baseline rather than
failing on it.

Verified on the runner by `workflow_dispatch`
[34753047653](https://github.com/Fadi-Sayej/Hackathon2026/actions/runs/34753047653).

## 4. Findings not fixed here

**F-1 — `sources.json` has two writers that disagree about what a row is.** The legacy
exporter recorded 17,165,316 `alonit_prices` rows and 161,270 `wolt_delivery_catalog` rows;
the engine's own `competitor_product_signals` step records 560,596 and 7,414 for the same
33 committed snapshot days, after dedup. A factor of 30 and 22. Whichever number the owner
is shown, nobody can currently source it (rule 11), so the file is deliberately **not** added
to the nightly commit and stays frozen. *Someone must decide which figure is the honest one
before this file is published again.*

**F-2 — `data/owner/owner_state.json` is tracked and drifts.** It is the engine's mirror of
the Firestore owner state, rewritten on every run that pulls with a credential, and it is
tracked despite the `data/**` ignore. Nothing commits it, so it only produces a dirty
working tree after `npm run test:py`. Decide whether the mirror belongs in the repository at
all.

**F-3 — `check_signals_live.mjs` guards a path the owner no longer sees.** It reads
`public/data/market-context.json` and exercises the legacy JS ranking
(`reorderEngine.js` → REORDER recommendations). It passes, and it still guards a file the
nightly commits, so it stays for now — but after the cut-over it proves nothing about the
surface the owner opens. Phase 4 should either repoint it at `dashboard.json` or remove it
with the rest of the chain.

**F-4 — `CLAUDE.md` rule 5 is stale.** Its table says `dashboard.json` is "read by nothing
yet — the front end still reads the old artefact", and that "the front end moving onto
`dashboard.json` is not planned work — Phases 2–4 are not written". Task 2.7 happened; the
phases are written and three are executed. Rule 5 is upstream of this role, so it is
reported rather than edited.

## Timeline

| Time (UTC) | Event |
|---|---|
| 2026-09-12 16:47–17:09 | Phase 0/1 work merges to `main` |
| 2026-09-13 02:22 | Scheduled nightly starts |
| 02:38 | `product_recommendations` → `readiness_only` |
| 02:39 | `dashboard_export` → `EmptyExportError`, job exits 1 |
| ~10:40 | Investigated; root cause and the two hidden faults identified |
| 10:54 | `ebbe58f` pushed, workflow dispatched to verify |
