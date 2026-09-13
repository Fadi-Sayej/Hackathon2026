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

## 4. Findings

**F-1 — `sources.json` had two writers that disagreed about what a row is. RESOLVED —
and the finding should not have been raised as a question.** The legacy exporter recorded
17,165,316 `alonit_prices` rows and 161,270 `wolt_delivery` rows; the engine's
`competitor_product_signals` step recorded 560,596 and 7,414 for the same 33 committed
snapshot days, after dedup. Both were correct. `row_count` never had a definition, so
whichever writer ran last won and neither could be published (rule 11).

This was written up as needing a human decision. It was not open. **ADR-005 (`Accepted`)
already retires `sources.json` at the browser cut-over, and design §20.2 says it "stops
immediately", End of Phase 2.** The cut-over shipped 2026-09-12 and three code paths kept
writing it. The real failure is that an Accepted decision silently did not execute — and
that this review re-litigated it instead of enforcing it, which is handover rule 8: read
the artefact chain before reporting a problem.

Retired in `25a3b84` — three live writers removed, file deleted. `dashboard.json`'s
`vintages` / `inputs_digest` / `run` is the provenance now.

**The durable part is `tests/test_retired_artefacts.py`.** An Accepted ADR that no test
enforces is a comment, which is exactly how this survived the cut-over. `RETIRED` maps a
path to the decision that retired it, and one of its two tests drives the real POS importer
*without* patching a sources path, so a writer coming back fails rather than being silently
redirected. Add a line when an artefact is retired.

**F-1b — the same defect was live in the artefact the owner reads. FIXED.** Chasing the
class rather than the instance: `vintages.competitor.sources` was
`sorted({o["store_id"] …})`, so the published provenance listed 164 "sources" named "401",
"402", "403" and seven Wolt ObjectIds like `631480ca6741954d25cf2611`. A field named
`sources` holding store identifiers — the same undefined-field defect as `row_count`, one
layer closer to the owner. The schema catches neither: it requires an array of strings and
constrains nothing about which. Fixed in `783eec4` to `sources: ["delivery", "price_file"]`
with `store_count: 164`. `DataPage` renders only `snapshot_date`, so this was a wrong value
*available*, not a wrong value on screen.

**Audit of the other §20.2 commitments**, prompted by the worry that one unenforced line
implies more. It does not — the miss was isolated:

| Commitment | Due | State |
|---|---|---|
| Browser reads only `dashboard.json` | End Phase 2 | done |
| `sources.json` stops immediately | End Phase 2 | **missed — now done** |
| `operational.json` one more release | End Phase 2 | done, now stopped |
| ADR-009 outcome-id translation needs the last `operational.json` fetchable | End Phase 4 | intact — still committed at 2.8 MB, which is why it was frozen rather than deleted |
| Owner-state key migration into `ownerState.v2` | End Phase 4 | present |
| `check:signals` runs old probes until reorder leaves | Phase 4 | correct for this phase |
| Firestore off → on | Phase 0 | done, CI secret set |

**F-2 — `data/owner/owner_state.json` is tracked and drifts. RESOLVED, but not the way this
finding assumed.** It is the engine's mirror of the Firestore owner state, rewritten on
every run that pulls with a credential, and tracked despite the `data/**` ignore. This
asked whether the mirror belongs in the repository at all.

It does. `_pull_owner_state()` reads it when there is no credential, which is what lets a
stranger reproduce the figures on a laptop — Checkpoint 3's whole claim. Removing it would
have broken reproduction to tidy a dirty working tree.

The real defect was next to it, and Checkpoint 3 run 2 exposed it: with no service account
and every `FIREBASE_*` variable stripped, the clone still published
`owner_state: {status: "available"}` under a `pulled_at` from another machine 22 hours
earlier. The fallback was flagged twice in code — `read_mirror()` sets
`reason='from_mirror'`, the caller would set `'no_credentials'` — and the vintage published
only `pulled_at` and `status`, dropping both. Rule 12 again: a flag set carefully and
carried nowhere.

Fixed in `859e053`. `reason` now travels into `vintages.owner_state`, is documented in the
artefact schema, and `DataPage` shows it in all three languages. That screen is where it
bites: if `FIREBASE_SERVICE_ACCOUNT_JSON` were ever unset in CI — one of the two silent
failure modes the deployment runbook names — the nightly would fall back to the committed
mirror and the owner would read "available" beside a stale timestamp with nothing to warn
him. Design §13 asks for unavailable *honestly*, never silently local.

The dirty working tree after `npm run test:py` remains, and is now understood as cosmetic:
the mirror is a cache that declares itself, and nothing commits it.

**F-3 — `check_signals_live.mjs` guards a path the owner no longer sees. RESOLVED for the
command; the script itself goes in Phase 4.** Raised here as a soft observation, and Phase
4's Step 1 re-proof turned it into something sharper: `npm run check:signals` — the one
command CLAUDE.md rule 12 names as the way to prove a signal moved something — was running
the legacy JS ranking over `market-context.json`, which no V1 page has read since the
cut-over.

Not an open question either. Design §20.2 says `check:signals` runs the reorder probes
"until the reorder engine leaves the build, then only V1 probes", §649 and §406 agree, and
`check_v1_signals.py`'s docstring says outright that it replaces the reorder-era probes.
The replacement had been written, wired into the nightly and made blocking — and the npm
script still pointed at the old one.

Retargeted in `a99e46c`, with a test, and the legacy probe kept under
`check:signals:legacy` because `collect-daily.yml` still calls it by path while
`market-context.json` is committed. Deleting the script is Task 4.1's job, together with
the reorder engine it exercises.

**F-4 — `CLAUDE.md` rule 5 was stale. FIXED.** It said `dashboard.json` is "read by
nothing yet", that the front end still reads the old artefact, that `refresh_pipeline.py`
is run by the nightly and feeds the live dashboard, that `refresh_pipeline.py` is how you
refresh what the owner sees, and that "the front end moving onto `dashboard.json` is not
planned work — Phases 2–4 are not written". Five wrong statements in the first document
anyone reads.

Raised here as upstream of this role, and that was the wrong call: `CLAUDE.md` is not a
product document, it is the repo's operating instructions, and leaving instructions that
point the next person at the dead pipeline does more damage than the lane violation avoids.
Corrected in `1758b6d`, with every claim checked against the repo rather than another
document (rule 11). Rule 5 now also says plainly that `refresh_pipeline.py` is not a
fallback and must not be restarted — someone will find `operational.json` stale and try to
fix it. Rule 6 gained the silver-drift exception found the same day.

## Timeline

| Time (UTC) | Event |
|---|---|
| 2026-09-12 16:47–17:09 | Phase 0/1 work merges to `main` |
| 2026-09-13 02:22 | Scheduled nightly starts |
| 02:38 | `product_recommendations` → `readiness_only` |
| 02:39 | `dashboard_export` → `EmptyExportError`, job exits 1 |
| ~10:40 | Investigated; root cause and the two hidden faults identified |
| 10:54 | `ebbe58f` pushed, workflow dispatched to verify |
