---
ID: PLAN-PHASE-4
Title: Phase 4 — Removal
Status: Ready for review
Owner: smartshelf-architect
Version: 1.0 (2026-09-12)
Parent: [Implementation Plan](plan.md)
Related Specs: F6-S1, F7-S1
Inputs: [docs/architecture/system-design.md §20.1, §20.2, §22, docs/reviews/checkpoint-3-reproduction.md]
Updated: 2026-09-24
---

# Phase 4 — Removal

**Depends on:** Checkpoint 3, and on the browser cut-over (Task 2.7) having happened.

**Delivers:** the repository stops carrying two of everything. Tag `v1-attic`, delete
§20.1's REMOVE list, stop writing `operational.json`, drop the migrations, and bring the
bundle inside its budget.

**Checkpoint 4:** `index.html` — the owner's entry — **under 500 KB**, and the
total-output ratchet lowered to the new measured size; CI green; `git grep` finds no
reference to anything removed.

---

## Why this phase is dangerous, and how that is handled

Every other phase added. This one deletes, and it deletes the fallback: after Task 4.2
there is no `operational.json` to roll back to. Three rules govern the whole phase.

1. **Tag before deleting.** `v1-attic` is cut first and pushed. Everything removed here
   stays reachable at that tag forever, so "we might need it" is answered before it is
   asked.
2. **Nothing is deleted while something still reads it.** Each task greps for callers
   first and stops if it finds one. A file with no readers is dead; a file with one reader
   is a task nobody finished.
3. **The bundle guard is the gate, not the goal.** `check:bundle`'s ceiling comes down with
   each removal. If a deletion does not move it, the deletion did not do what it claimed.

## Ordering

```
4.0 tag v1-attic ── 4.1 delete the REMOVE list ── 4.2 stop operational.json ── 4.3 drop migrations ── 4.4 Checkpoint 4
```

Strictly sequential. Each task's verification is the next task's precondition.

---

### Task 4.0: Tag `v1-attic` before anything is deleted

**Files:** none — a git tag.

- [x] `git tag -a v1-attic` at the commit **before** the first deletion
- [x] push the tag
- [x] record the tag's sha in this file

Nothing else in this phase may start until the tag exists on the remote. A tag that lives
only on one machine is not a rollback.

> **Done. Verified 2026-09-15.**
>
> | | |
> |---|---|
> | tag object | `80fd2574f4400698387e85741558ed7e231174d2` |
> | tagged commit | `bf1d47a640c029382493cc496e174adc7512c7f4` (2026-09-12) |
> | on the remote | yes — `git ls-remote --tags origin v1-attic` returns the same object |
>
> **The tag was cut on 09-12, three days before Checkpoint 3 closed, so it does not sit at
> the commit immediately before the first deletion.** That is harmless here, and it was
> checked rather than assumed: `git diff v1-attic..main` over every §20.1 REMOVE path — the
> demo spine, the V2/V4 analytics, the planogram, the LLM layer, telemetry, the MCP server,
> the scripts and `operational.json` — returns **nothing**. The tag preserves the same bytes
> Phase 4 deletes.
>
> If any REMOVE path is modified before Task 4.1 starts, that stops being true, and the tag
> should be re-cut rather than trusted. Re-run that diff before the first deletion.

> **Re-cut on 2026-09-24, before the first deletion under ADR-028.** The diff was re-run over
> ADR-028's 91 files: 86 were identical at `v1-attic`, 4 had changed since it was cut
> (`PlacementReasonPanel.jsx`, `DashboardPage.jsx`, `OperationalPage.jsx`,
> `RecommendationsPage.jsx`), and `artefactToOperational.js` did not exist in it. So a second
> tag holds them:
>
> | | |
> |---|---|
> | tag | `v1-attic-2026-09-24` |
> | tag object | `1fdeee603b1e2f96a9fecec1b533ea44ac7d75bd` |
> | tagged commit | `959a572` (main, the merge of ADR-028) |
> | holds | all 91 of ADR-028's files, verified with `git cat-file -e` per path |
>
> `v1-attic` is left where it is. It is history, and it still holds 86 of the 91 as they were.

---

### Task 4.1: Delete the §20.1 REMOVE list

> **Re-scoped by [ADR-028](../architecture/decisions/ADR-028-the-nav-is-the-owners-and-only-unshipped-code-leaves.md) (accepted by the repository owner, 2026-09-24).** The list below predates the owner's nav decisions of 2026-09-16 … 2026-09-24. It names three things that are live: `PriceGapPage`, `ProductsPage` and `inventoryEngine`. This task's file list is now ADR-028's 91 unshipped modules, less whatever a script, the nightly or a live harness still reads. The nav entries behind the awaiting shells stay. #74 and #75's "do not action as written" is lifted for exactly that list.

**Files:** §20.1's REMOVE rows — the demo spine (`src/data/*.js`, `normalize-datasets.mjs`,
`loadDemoStoreData`, `posConnectors/*`), the V2/V4 analytics (`reorderEngine`,
`inventoryEngine`, `demandEngine`, `competitorEngine`, `planogram/*` and their pages), the
LLM layer (`src/lib/ai/*`, `src/api/llm_proxy.py`), telemetry, the MCP server, and the
17 unreferenced scripts.

**Interfaces:** none produced. This task only removes.

- [x] **Step 1: Prove each is unread.** For every path, `git grep` for importers **outside
      the removal set**. Anything with a live reader comes off the list and is reported —
      it is not dead, it is unfinished.

> **Step 1 run 2026-09-12, after the cut-over.** All ten V2/V4 pages are unreachable from
> the app: `RecommendationsPage`, `ApprovedOrdersPage`, `DashboardPage`, `ReportPage`,
> `PriceGapPage`, `ProductsPage`, `AssortmentGapPage`, `PlanogramPage`, `StoreLayoutPage`,
> and `ShelfPlanPage` (referenced only by `StoreLayoutPage`, which is itself unreachable —
> the pair is dead together). The LLM layer's only importer outside itself is `ReportPage`,
> so it goes with that group.
>
> **Two came off the list.**
>
> `src/telemetry/` is **not dead**. `docs/operations/deployment.md` §"Internal telemetry
> page (B-3)" documents it as the live internal pilot dashboard — alerts shown against
> acted-on, acceptance by type, ₪ impact — reading decisions from Firestore. It is the only
> thing that measures the pilot, and PRD §8's entire go/no-go rests on measuring it. This is
> ARCH-GATE-003, which the readiness gate already raised and the System Design has not
> recorded: *"the design removes the telemetry surface that SPEC-000 §4 relied on and builds
> nothing in its place."* Deleting it would remove the pilot's own instrument. **Raised as
> P4-OQ-3.**
>
> `.mcp.json` and `src/mcp_server/` stay pending **P4-OQ-2** — `.mcp.json` launches the
> local price server, so removing it is a developer-workflow change.

> **P4-OQ-2 answered 2026-09-13: the MCP group is deleted with the rest.**
>
> The whole of it is a closed set that nothing else reaches — `.mcp.json`,
> `src/mcp_server/`, `src/external/mcp_price_adapter.py` and
> `scripts/run_mcp_price_lookup.py` import each other and nothing in the product imports
> any of them. The engine drives its own market chain (`market_context`,
> `competitor_signals`, `product_matching`) and has never used this path.
>
> The developer-workflow objection is real but small, and it cuts the other way once
> stated plainly: a tool that no test, workflow or product path exercises is a tool nobody
> notices has broken. This repository has been bitten by precisely that four times — rule
> 12 exists because of it — and an ad-hoc price lookup that silently stops working is the
> same failure in a smaller costume. The price data it queries is in the committed
> snapshots either way, so the capability is not lost, only the convenience wrapper.
>
> It stays reachable at `v1-attic` if the convenience turns out to be missed.

> **Step 1 run 2, 2026-09-13, at `aa1d9f7`.** Re-run because run 1 predates the cut-over
> deploying and the nightly changes of 09-13, and because "verify rather than assume" is
> this phase's own instruction. Method: for every REMOVE token, `git grep` for lines that
> are actual `import` / `from … import` / `require(` statements in files **outside** the
> removal set — a mention in a comment, a config or `.gitignore` is not a reader.
>
> **11 files outside the set import into it.** Five are tests of their own subject, which
> Step 4 already handles by deleting each with the code it covers:
> `pages.component.test.jsx`, `shelfPlanning.integration.test.jsx`,
> `velocityClaimContract.test.js` (→ `mockAI`), `loadMarketContext.test.js`
> (→ `reorderEngine`), `tests/test_llm_cache_key.py` (→ `llm_proxy`).
>
> **Six are scripts, and three of those are a problem the REMOVE list does not name:**
>
> | Script | Imports from | Status |
> |---|---|---|
> | `scripts/check_signals_live.mjs` | demo spine, `reorderEngine` | **live twice over** — `npm run check:signals` *and* `collect-daily.yml:192`, where it is a nightly gate |
> | `scripts/doctor.mjs` | demo spine, `src/lib/planogram/` | **live** — `npm run doctor` |
> | `scripts/build-rag-corpus.mjs` | demo spine, `loadDemoStoreData` | not npm-scripted, but not on the REMOVE list either |
> | `scripts/run_mcp_price_lookup.py` | `mcp_price_adapter` | not on the list; its import target is. Goes with the MCP group or blocks it |
> | `scripts/compare_explanations.mjs` | demo spine, `reorderEngine`, `src/lib/ai/` | already on the list (LLM row) — no action |
> | `scripts/report_reorder_explanations.mjs` | demo spine, `reorderEngine` | already on the list (LLM row) — no action |
>
> So **Task 4.1 cannot delete the demo spine while `check:signals` and `doctor` exist as
> written.** That is this phase's rule 2 exactly: a file with one reader is a task nobody
> finished. It is also F-3 from the 09-13 incident record, which asked the softer question
> — the probe guards a path the owner no longer sees — and this is the hard one: it blocks
> the phase.
>
> **A path in §20.1 is wrong.** The V2/V4 row lists `explainReorder.js` among
> `src/lib/analytics/*`. It is at `src/lib/i18n/explainReorder.js`; there is no
> `src/lib/analytics/explainReorder.js`. Deleting by the listed path would silently remove
> nothing. **smartshelf-architect.**
>
> **A fourth reader, and the grep could not have found it (2026-09-15, #91).**
> `scripts/audit-store-format.mjs` reads the demo spine through a **dynamic** `import()` built
> from a joined path, inside a function:
>
> ```js
> const demo = await import(path.join(rootDir, 'src/data/demoProducts.js'))
> ```
>
> Every sweep this phase used — `git grep "^import"`, grepping the module name — returns
> nothing for it, because the three readers it did find all use top-level static imports. The
> script was npm-scripted (`audit:store-format`) and passing. **So Step 1's instruction to
> "re-run the grep rather than trust the list" does not go far enough: the grep is the weak
> part, not the list's age.** Before Task 4.1 deletes anything, sweep for dynamic `import(`
> and for `readFileSync` over a source path as well.
>
> **Resolved by deleting it, not repointing it**, and the reasoning matters because it is the
> opposite of the answer `doctor.mjs` got in #68. The doctor checks the real catalogue and had
> a V1 home to move to. This script runs the **V2 reorder engine** over the **demo spine** —
> both deleted here — to guard one rule: no finding may rest on a store format we are not
> comparable to (ADR-008).
>
> That rule is emphatically still live. The engine enforces it (`o["affinity"] >= floor`) and
> publishes `comparability_floor`, and it is load-bearing to a degree worth stating: in the
> 2026-09-15 artefact **161 of 164 observed stores sit below the 0.3 floor**. But **no Python
> test named it**, so deleting the script would have dropped the only artefact guarding it.
> Two tests in `test_competitor_position.py` now do, and they were proven to guard rather than
> to pass: with `min_affinity` set to `0.0` in `configs/store_types.yaml`, exactly one fails.

> **MCP group deleted 2026-09-16 (Task 4.1c, first group).** `src/mcp_server/`,
> `src/external/mcp_price_adapter.py`, `scripts/run_mcp_price_lookup.py` and `.mcp.json`,
> which held only that one server entry.
>
> Swept the way #91 says to, not the way that missed it: every reference to `mcp_server`,
> `mcp_price_adapter`, `run_mcp_price_lookup` or `price_server` anywhere in the tree. All
> that remained were **documentation** mentions — no code, no workflow, no npm script, no
> test. The group imports only itself, and the engine's own market chain
> (`market_context` → `competitor_signals` → `product_matching`) never used it.
>
> **The bundle does not move, and that is correct here.** Rule 3 — "a group that does not
> move the bundle deleted nothing that shipped" — is about browser code. This group is
> Python and one JSON config; none of it was ever in a chunk. `CEILING_KB` stays where it is.

> **The scripts row audited 2026-09-16 (Task 4.1c, second group). Four files deleted, eleven
> held.** §20.1's dead row names eighteen paths and then "17 unreferenced scripts". Four of
> the named ones — the MCP group — went in the first group. This pass swept the remaining
> fourteen the way #91 says to: every mention anywhere in the tree, then each mention read to
> see whether it is an import, an invocation, or prose. **Eleven of the fourteen are not dead**,
> and three of those are live in a way the row's "no execution path from `package.json`,
> `.github/`, `collect_daily.sh`, or any live module" claim contradicts directly.
>
> **Deleted — the closed subsets, where every reference outside the file is prose or is
> itself being removed:**
>
> | Path | Its only readers |
> |---|---|
> | `src/external/firestore_writer.py` | `run_delivery_to_firestore.py`, deleted with it |
> | `scripts/run_delivery_to_firestore.py` | one comment line in `configs/delivery_targets.yaml`, corrected in this commit |
> | `scripts/export_market_params.py` | one `Regenerate:` comment in the file it generates |
> | `src/data/marketParams.js` | **nothing** — zero importers in the tree |
>
> `firestore_writer.py` is S27's "second Firestore schema", and the sweep confirms the
> phrase: it writes top-level `stores`, `products` and `price_snapshots` documents, while V1
> reads only `stores/yomyom-kafr-qasim/ownerState` (`src/owner_state/pull.py`). Nothing reads
> what it wrote. The nightly's delivery step is `run_delivery_venue_connector.py`
> (`collect_daily.sh:112`) — a different script that never touches it. The three
> `FIREBASE_SERVICE_ACCOUNT_*` variables stay live for `src/engine/run.py`,
> `src/owner_state/pull.py` and `check_firestore_rules.py`, so nothing in `.env.example` or
> the deployment doc is orphaned by this.
>
> `marketParams.js` is listed in the S26 demo-spine row rather than here, and is taken with
> its generator anyway because it has no importers at all: it is not part of what blocks that
> group, and a generated file whose generator is gone is the stale state this phase keeps
> creating. 1,083 lines, tree-shaken out of the bundle already, so the bundle does not move —
> rule 3 is about browser code, and the same reasoning as the MCP group applies. `CEILING_KB`
> stays.
>
> **Held, and why. The row is wrong about three of these.**
>
> | Path | Held on |
> |---|---|
> | `src/external/tenbis_connector.py` | **live in the nightly.** `src/external/delivery_venue_connector.py:41` imports `TenBisCollectionResult` and `collect_tenbis_venue` at module top level, and `collect_daily.sh:112` runs it every night. S27 calls this an "unreachable branch" — the *branch* at line 543 may be, but the *import* is not, so deleting the module breaks the collector on import, before any branch is evaluated |
> | `scripts/run_alonit_signal_pipeline.py`, `src/external/alonit_signal_pipeline.py` | **live npm script** — `collect:alonit-signals` (`package.json:17`). Not in CI; the script is the whole execution path |
> | `scripts/export_store_types.py` | **live npm script** — `data:store-types` (`package.json:31`) |
> | `scripts/export_competitor_market_data.py` | imported by `tests/test_store_types.py:196` (`CHAIN_META`, `OUR_STORE`) — a test of the **store-types config**, not of this script, so Step 4's "delete the test with its subject" does not apply. Also `pilot_daily.sh:98` |
> | `scripts/join_yomyom_kaggle.py` | `pilot_daily.sh:97`, which `npm run pilot:daily` runs |
> | `src/external/kaggle_supermarket_importer.py`, `scripts/import_kaggle_supermarkets.py` | the only producers of `data/external/silver/products/kaggle_*`, which `join_yomyom_kaggle.py:44` reads. Deleting them while that script lives would not break it — it globs, finds nothing, and writes a delivery-only `barcode_matches.parquet`. A smaller number, no error. That is rule 12 in the data direction, so the Kaggle chain is held with its consumer |
> | `scripts/build_assortment_gap.py`, `export_assortment_gap.py`, `measure_gap_ranking.py` | their only reader outside themselves is `src/pages/AssortmentGapPage.jsx` (via `public/data/assortment_gap.json` and the `gap.emptyDetail` string, which names both scripts in all three dictionaries). The page is in the V2/V4 row; `src/lib/i18n/*` is **REUSE**, so deleting the scripts first leaves a shipped dictionary telling the owner to run something that does not exist. Held for the page's commit |
>
> So `pilot_daily.sh` — not named anywhere in §20.1 — is what pins four of the eleven. It is the
> legacy pipeline that ends in `public/data/operational.json`, which is Task 4.2's subject and
> is deliberately frozen until Phase 4 ends. **Those four cannot go before Task 4.2, and
> Task 4.2 cannot start yet.**
>
> *(Corrected 2026-09-16: this said the freeze is because "ADR-009's one-shot id translation
> still needs it". It does not — that translation was never built. See the Task 4.2 note
> below. The four are still pinned, by `pilot_daily.sh`; only the stated reason for the
> freeze was wrong.)*
>
> **And "17 unreferenced scripts" cannot be executed as written.** It names no paths, so
> there is nothing to grep, nothing to verify and nothing to delete by path — and this sweep
> shows the row's own named entries are wrong about three files, which is the strongest
> argument against trusting an unnamed remainder. `scripts/` holds **67** files after this
> commit — 52 `.py`, 12 `.mjs`, 3 `.sh`, counted with `ls`, not read off another document —
> and the System Design §7 names the handful that are the product; the difference is not 17.
> **smartshelf-architect: the row needs the paths enumerated, `tenbis_connector.py`,
> `run_alonit_signal_pipeline.py` and `export_store_types.py` moved off "dead", and
> `pilot_daily.sh` named as the blocker it is.**

> **The LLM group swept 2026-09-16 (Task 4.1c, third group). Nothing deleted — it has a
> second blocker, and the grep that missed `audit-store-format.mjs` would have missed this
> one too.**
>
> Step 1 run 1 concluded: *"The LLM layer's only importer outside itself is `ReportPage`, so
> it goes with that group."* That is wrong. **`scripts/check_signals_live.mjs:154` imports
> `src/lib/ai/factsGuard.js`**, and `collect-daily.yml:192` runs that script every night, in
> the step immediately before the artefact is committed. The import is dynamic and sits
> inside a function:
>
> ```js
> const { validateExplanationResult } = await import('../src/lib/ai/factsGuard.js')
> ```
>
> This is the third time the same shape has hidden a reader — #91 found it for
> `audit-store-format.mjs` and told this phase to sweep for dynamic `import(` and for
> `readFileSync` over a source path. That instruction had not been carried out; this is it,
> run over the whole tree rather than one group, so no later group has to repeat it:
>
> | Site | Target | Consequence |
> |---|---|---|
> | `scripts/check_signals_live.mjs:154` | `src/lib/ai/factsGuard.js` | **the finding above** |
> | `src/pages/__tests__/RecommendationsPage.cap.test.js:11` | `readFileSync('src/pages/RecommendationsPage.jsx')` | the page is in the V2/V4 row; this test reads it as **text**, so a grep for an import of it finds nothing. Must be deleted in the same commit as the page (Step 4) |
> | `src/pages/__tests__/RecommendationsPage.cap.test.js:34` | `../../lib/i18n/dictionaries/${lang}.js` | template-literal path; the dictionaries are **REUSE**, so no action — recorded because no fixed-string grep can see it |
> | `src/lib/analytics/__tests__/reorderEngine.test.js:293` | `../actionPriority.js` | `reorderEngine` is REMOVE, `actionPriority.js` is **live** (`OperationalPage.jsx`, `src/telemetry/telemetryModel.js`). Deleting the test is safe; deleting its target is not |
> | `src/test/setup.js:25` | `@testing-library/react` | a package, not a source path |
>
> **How close the `factsGuard` one is to biting.** `checkLlmSignal()` returns early when
> neither `VITE_LLM_PROXY_URL` nor `LLM_PROXY_URL` is set, so the import does not execute
> today: neither variable appears in `collect-daily.yml`, `vercel.json` or `vite.config.js` —
> only in `.env.example`, blank. So deleting `factsGuard.js` would not break tonight's
> nightly. It would leave the gate **one environment variable away** from throwing, in the
> step that decides whether `dashboard.json` is committed, and the throw would look like a
> data failure rather than a missing file. That is not a risk worth taking to delete a file
> that has to wait for `ReportPage` anyway.
>
> **So the LLM group is held on two things, and both are named.** `ReportPage` (#74), and
> `check_signals_live.mjs`, which §20.2 retires in **Task 4.2** together with the reorder
> engine it exercises. Task 4.2 is itself blocked. The group moves when whichever of those
> lands last lands.
>
> **The Python half was considered separately and held.** `src/api/llm_proxy.py`,
> `src/api/__init__.py`, `tests/test_llm_proxy.py` and `tests/test_llm_cache_key.py` are a
> closed set — nothing outside their own tests imports them, and §3 records that nothing
> launches the server. It could go alone. It should not: the browser client
> (`src/lib/ai/llmExplanationProvider.js`, reading `VITE_LLM_PROXY_URL`) stays until
> `ReportPage` goes, and deleting the server while its client ships is the exact inverse of
> the MCP group, which was defensible **because** it took client and server together. One
> commit, when the group unblocks.
>
> **smartshelf-architect:** §20.1's LLM row and S23 both describe this layer as reaching
> nothing but `ReportPage`. The nightly gate belongs in that row as a second reader.

> **Fixed 2026-09-13.** §20.1's row now names `src/lib/i18n/explainReorder.js` directly.
> The same pass also added `scripts/build-rag-corpus.mjs` and
> `scripts/run_mcp_price_lookup.py` to their rows — both were readers of REMOVE-listed
> code (the demo spine and `mcp_price_adapter` respectively) that Step 1 run 2 found above
> but that were not themselves on the list, so a Task 4.1 deletion would have hit the same
> "one reader left" trap the demo-spine group already hit.
>
> **Task 4.2 is partly done already, by the 09-13 incident fix (`ebbe58f`, `25a3b84`):**
> the `refresh_pipeline.py` step is out of `collect-daily.yml`, and
> `public/data/sources.json` is deleted along with its three writers. What remains of 4.2
> is deleting `refresh_pipeline.py`, `export_dashboard_data.py`,
> `loadOperationalData.js` and `public/data/operational.json` — and the last of those is
> still needed by ADR-009's one-shot outcome-id translation until Phase 4 ends.

> **ADR-009's one-shot id translation does not exist in code. Verified 2026-09-16.**
>
> Task 4.2's remaining work has been described as blocked on `public/data/operational.json`,
> which §20.2's "Outcome ids" row keeps alive until the end of Phase 4 because *"one-shot
> legacy id translation in `ownerState.js` (ADR-009), needs the last `operational.json` to be
> fetchable"*. CLAUDE.md rule 5 repeated it. **Neither was true.**
>
> ADR-009 describes the mechanism precisely:
>
> > On first load after cut-over, `ownerState.js` maps legacy ids by `(legacy type →
> > capability, barcode)` from the last `operational.json` it can still fetch and rewrites
> > them; the mapping runs once and is then deleted (no permanent adapter).
>
> What `migrate()` does instead: reads the three legacy localStorage keys and copies each
> outcome under **its legacy id, verbatim** — `state.outcomes[id] = outcome`. It is
> synchronous, so it structurally cannot fetch anything, and `git grep operational` across
> `src/owner/` returns no reference at all. There is no mapping and nothing to delete.
>
> **The two id spaces do not meet.** Measured on the committed artefacts at `a559357`:
>
> | | ids |
> |---|---|
> | `dashboard.json`, union of `capabilities[*].entries[*].id` | **3,464** |
> | `operational.json` | **4,359** |
> | intersection | **0** |
>
> So a legacy outcome carried over by `migrate()` matches no V1 entry, suppresses nothing,
> and the owner is shown a recommendation he already actioned. Rule 12's shape exactly:
> specified, documented as live in two authoritative places, and it changes nothing.
>
> **What it costs today, and what changed.** The committed owner-state mirror holds
> `answers: {}` and `outcomes: {}`, so there is nothing to translate and nothing is lost yet.
> That was a safe accident while the browser wrote only to localStorage. **#95 merged on
> 09-15 and the write-through now deploys**, so from the next legacy-carrying device that
> opens the app, orphan ids reach Firestore. ADR-016's snapshot records them with
> `signal_family: null` — deliberately, for legacy records — so F13 can still tell them
> apart, which is the one part of this that was built as designed.
>
> **Consequences for this phase.**
>
> - `operational.json` is **not** held by ADR-009. Its last reader is
>   `src/telemetry/TelemetryDashboard.jsx` (plus `EMPTY_OPERATIONAL_DATA` in a page test),
>   which F13 (#83) replaces. That, and nothing else, is what Task 4.2 waits on.
> - Whether the translation should be **built or withdrawn** is ADR-009's author's call, not
>   this file's. Both are defensible: with zero recorded outcomes there is nothing to
>   translate, so withdrawing costs nothing today — but the restore of the pre-V1 nav
>   (in flight on `restore/old-ui`) may make legacy-shaped ids a live source again rather
>   than a historical one, and that decides it. **smartshelf-architect.**
> - Until then, do not delete `operational.json` and do not cite ADR-009 as the reason it
>   stays. CLAUDE.md rule 5 has been corrected; §20.2's row and ADR-009 itself have not been
>   touched, because they are not this role's to edit.

**Not started, and deliberately.** Deleting the fallback before the replacement has run for
a day is the risk this phase's three rules exist to prevent, and `vercel rollback` restores
a deployment rather than a source tree.

Two of the three preconditions are now met and one is not, as of 2026-09-13:

| Precondition | State |
|---|---|
| The cut-over has been live for one release | **met** — deployed 2026-09-12; Vercel auto-deploys from `main`, the pilot URL answers 401 |
| `dashboard.json` committed nightly | **met** — first at `49f9e0c`, `engine: artefact for 2026-09-13` |
| Checkpoint 3 green | **not met** — one condition left, two consecutive green nightlies. 09-13's scheduled run failed and its re-run was green, so the next chances are 09-14 and 09-15 |

And Step 1 run 2 above adds a fourth, which is code rather than calendar: `check:signals`
and `doctor` still import the demo spine, so Task 4.1's largest group cannot start until
they are repointed or removed.
- [x] **Step 2: Delete, in groups, one commit per group** — demo spine, V2/V4 analytics,
      LLM, telemetry, MCP, scripts. A single 200-file commit cannot be reviewed or
      reverted selectively.
- [x] **Step 3:** after each group, `npm run lint && npx vitest run && npm run build &&
      npm run check:bundle`, and **lower `CEILING_KB`** to the new measured size. A group
      that does not move the bundle deleted nothing that shipped.
- [x] **Step 4:** delete the e2e specs covering removed pages (`shelf-planning.spec.js`,
      the V2/V4 parts of `navigation.spec.js`) **in the same commit as their subject**, so
      no commit leaves a test pointing at nothing.

**The 4.36 MB demo spine is the whole budget.** `src/data/*.js` compiles pipeline data into
the bundle (§20.1, S26). Checkpoint 4's 500 KB is unreachable until it goes and trivially
reachable afterwards.

> **No longer true, measured 2026-09-13 at `0f3a86f`.** The cut-over already achieved it.
> Nothing reachable imports the demo spine or the planogram, so Vite tree-shakes both out —
> `grep` across `dist/assets` for `demoProducts`, `loadDemoStoreData`, `packageGeometry`,
> `FIXTURE_PRESETS` and `allocationEngine` returns **zero hits in every chunk**.
>
> What a browser actually downloads:
>
> | Entry | Size | Against the 500 KB target |
> |---|---|---|
> | `index.html` — the owner's app | **496 KB** (`main` 309 + `format` 187) | **under** |
> | `telemetry.html` — the team only | 619 KB (`telemetry` 432 + `format` 187) | over, and nobody but us opens it |
>
> `check_bundle_size.mjs` had been summing both entries and comparing 928 KB to the 500 KB
> target, which is not a number anyone downloads. It now resolves each HTML entry to the
> chunks that entry references and reports per entry; the ratchet still gates on the total.
>
> **So Task 4.1 is repo hygiene, not a bundle fix.** That is a materially weaker reason to
> hurry it, and it removes the argument for deleting anything before Checkpoint 3 is green.
> Whether Checkpoint 4's "bundle < 500 KB" means the owner's entry or the whole build output
> is a wording question the guard now surfaces but does not answer. **smartshelf-architect.**

> **Answered 2026-09-13 — the target governs the owner's entry; the total is a ratchet.**
> The 500 KB exists for one reason: what the store owner's phone downloads before he can
> read today's work. `index.html` is that download. `telemetry.html` is an internal
> instrument the team opens on a desk, it is a separate Vite entry, and **no browser ever
> loads both** — so summing them measures a page that does not exist, which is what the
> guard was doing when it reported 928 KB.
>
> Checkpoint 4 therefore reads: **`index.html` under 500 KB.** Measured today it is 496 KB
> and already passes, which is a consequence of the cut-over, not of any deletion.
>
> **That is 4 KB of headroom, and it is worth saying out loud.** 187 KB of the 496 is the
> shared vendor chunk (React, carried by both entries) and 309 KB is `main`. Now that the
> target gates rather than prints, the next component added to the owner's app plausibly
> fails CI. Two honest readings, and the team should pick one deliberately rather than
> discover it in a red build: either the target is real and the owner's entry needs weight
> taken off it — which restores some of the argument for Task 4.1 that the bundle
> measurement took away — or 500 KB was chosen when the number meant something else and
> should be re-set against what `index.html` actually costs. **This note does not decide
> that.**
>
> The total-output ratchet stays, and is not the same instrument. It catches a regression
> anywhere in the build — including in `telemetry.html`, which no target governs but which
> still ships from this repository. A ceiling that only watched `index.html` would let the
> other entry grow without limit. So: **one target on the owner's entry, one ratchet on
> everything**, and `check_bundle_size.mjs` already implements both.
>
> This does not weaken Checkpoint 4. Task 4.1's deletions must still move the ratchet —
> the phase's rule 3 is unchanged: a group that deletes nothing that shipped did not do
> what it claimed.
>
> **And the target is now enforced, which it was not.** `check_bundle_size.mjs` printed
> `under` / `OVER` per entry and failed only on the total: `index.html` could have crossed
> 500 KB and the guard would still have exited 0 while the ratchet had room. A criterion
> that only prints is the failure this repository keeps finding — rule 12, in a guard
> rather than in a signal. It now exits 1 when the owner's entry is over target, and when
> `index.html` is missing from the build altogether. Verified in all three directions:
> 496 KB against a 500 KB target exits 0; the same build against a 400 KB target exits 1;
> a build with no `index.html` exits 1.
>
> Status of this answer: it is written by `smartshelf-architect` into an artefact that is
> `Ready for review`. It is not approved, and Checkpoint 4's wording is not settled until a
> human accepts it (handover rule 2).

> **Correction, later on 2026-09-13 — the owner's entry is 369 KB, not 496 KB, and the
> "4 KB of headroom" argument above is wrong.** Mine to correct: I measured 496 KB, wrote
> it into the table above as a standing fact, and then argued from it. #88 moved the motion
> layer off the critical path between that measurement and the argument, and I did not
> re-measure before reasoning.
>
> Measured at `0659474`:
>
> | Entry | Size | Headroom against 500 KB |
> |---|---|---|
> | `index.html` — the owner's app | **369 KB** (`format` 187 + `main` 182) | **131 KB** |
> | `telemetry.html` — the team only | 619 KB (`telemetry` 432 + `format` 187) | over; no browser loads both |
> | lazy, off every critical path | 128 KB (`gsap` 68, `ScrollTrigger` 42, `lenis` 18) | — |
>
> `main` fell 309 → 182 KB because those three are now loaded on demand.
>
> **What it changes.** The paragraph above asks the team to choose between "the target is
> real and the owner's entry needs weight taken off it" and "500 KB was chosen when the
> number meant something else". With 131 KB of headroom that choice is not pressing and
> should not be presented as though it were: the next component added does not plausibly
> fail CI. Everything else in that answer stands — the target governs `index.html`, the
> ratchet governs the total, and the target is now enforced rather than printed.
>
> **What it does not change.** Task 4.1 is still repo hygiene rather than a bundle fix, and
> the case for it is now weaker still, not stronger.
>
> The lesson is the one this repository keeps relearning, and I was the one quoting it:
> a measured figure has a timestamp. Re-measure before arguing from it, especially in a
> tree where another session is landing work.

> **Done under ADR-028, 2026-09-24: six groups, one PR each, and not one byte of the build
> moved.**
>
> | Group | PR | Removed |
> |---|---|---|
> | 1 | #173 | `V1Spine.jsx` and `surface/pages.js`, once `check:surface` rendered `App` |
> | 2 | #174 | the eleven pre-V1 page components: the eight behind the awaiting shells, `OperationalPage`, `DataSourcePage`, `ExpiryPage` |
> | 3 | #175 | the planogram libraries and components, and `e2e/shelf-planning.spec.js` |
> | 4 | #176 | the components, questions code and adapters nothing imported |
> | 5 | #178 | the V2/V4 analytics (the reorder, demand, competitor, affinity, compliance and planogram engines and their helpers), `explainReorder.js`, and the LLM layer with its proxy |
> | 6 | #180 | the demo spine, its generator, the POS connectors, the adapters that read them, and the browser's market context |
>
> #177 went between groups 4 and 5. It is Task 4.2's retirement of `check_signals_live.mjs`,
> the last reader groups 5 and 6 had. Before ADR-028 the MCP group (#115), the Firestore
> writer and market-params generator (#117) and `audit-store-format.mjs` (`6567976`) had gone.
>
> **Rule 3, read against ADR-028.** The ratchet did not move, and here that is the claim
> rather than a failure of it. ADR-028 deletes exactly what the production build does not
> ship, so a build that changed would have meant something shipped had been taken. Measured
> by building each side and hashing every file in `dist/`:
>
> | Span | Before → after | `dist/` |
> |---|---|---|
> | groups 1–4 | `c7fdb29` → `603ba60` | all 20 files byte-identical |
> | #177, groups 5–6 | `6ebc575` → `b0ce7ba` | all 20 files byte-identical |
>
> The one merge between the two spans, #179, is a wording change and not a deletion.
> `CEILING_KB` stays at 1000 KB for the reason its own comment gives: it moves when bytes
> leave, and none did. It is re-measured when Checkpoint 4 closes.
>
> **What is left of this task is §20.1's scripts row**, split there on 2026-09-24. The Kaggle
> chain and `export_competitor_market_data.py` run only from `pilot_daily.sh` and go with
> Task 4.2. The assortment-gap trio and `public/data/assortment_gap.json` are unblocked,
> because #174 removed their only reader. `tenbis_connector.py` and the alonit pipeline are
> live and stay. "17 unreferenced scripts" names no paths, so there is nothing to act on.

---

### Task 4.2: Stop writing `operational.json`

> **The legacy probe is retired, 2026-09-24 (#77).** `scripts/check_signals_live.mjs` and the
> `check:signals:legacy` script are deleted, and `collect-daily.yml` no longer runs it (nor
> sets up Node, which only it needed). It was the last reader of the reorder engine, the demo
> data and `src/lib/ai/factsGuard.js`, so ADR-028's remaining groups can now go.
> `check:signals` runs the two V1 probes, which stay blocking in the nightly. **Still open in
> this task:** `refresh_pipeline.py`, `export_dashboard_data.py`, and `loadOperationalData.js`
> with `operational.json`. The last two wait on F13 (#83), because the telemetry surface
> still reads them.

> **Where the steps stand, 2026-09-24, after the ADR-028 groups.** Step 2 is met: the nightly
> committed `dashboard.json` on each of the twelve days 2026-09-13 … 09-24
> (`git log -- public/data/dashboard.json`). Step 4 is done (#177). Step 1 is not:
> `src/telemetry/TelemetryDashboard.jsx` still imports `loadOperationalData`, and F13 (#83)
> replaces it.
>
> **The writers need not wait for F13.** The telemetry surface reads the frozen file, not
> the code that wrote it. `refresh_pipeline.py` has not run since 2026-09-13, and
> `pilot_daily.sh` (`npm run pilot:daily`), which ends in `export_dashboard_data.py`, is run
> by no workflow. `pilot_daily.sh` also broke today in a small way: its soft
> `export_competitor_market_data.py` step now fails at the write, because #180 removed
> `src/data/`. So this task splits cleanly. The writers go now, with the scripts only
> `pilot_daily.sh` runs and CLAUDE.md rules 4, 5 and 10, which describe them. The file and
> its reader go after F13. **smartshelf-architect**, for the split; the owner, only if he
> still runs `npm run pilot:daily` by hand.

**Files:**
- Modify: `.github/workflows/collect-daily.yml` — drop the `refresh_pipeline.py` step
- Delete: `scripts/refresh_pipeline.py`, `scripts/export_dashboard_data.py`,
  `src/lib/dataAdapters/loadOperationalData.js`
- Delete: `public/data/operational.json`, `public/data/sources.json`

**Precondition, and it is not negotiable:** the browser has been reading `dashboard.json`
in production for **at least one release** (§20.2), and `dashboard.json` is committed
nightly by Task 3.4. Until both are true this task does not start.

- [ ] **Step 1:** confirm no `loadOperationalData` caller remains (Task 2.7 removed the
      last one; verify rather than assume)
- [x] **Step 2:** confirm the nightly has committed `dashboard.json` on consecutive days
- [ ] **Step 3:** delete, run everything, lower the ceiling
- [x] **Step 4:** `check:signals` loses its reorder probes with the engine; `check:signals:v1`
      becomes `check:signals`

---

### Task 4.3: Drop the migrations

**Files:**
- Modify: `src/owner/ownerState.js` — remove the one-shot legacy migration
- Delete: the legacy-id translation against the last `operational.json`

**Precondition:** every pilot device has opened the app at least once since the cut-over,
so `smartshelf.ownerState.v2` exists everywhere. **This is not knowable from here.** The
pilot is one store and a handful of devices; the answer is "ask, then delete", not "assume
a quarter has passed".

> **It is knowable from here now — ADR-021 is implemented (#84, 2026-09-16).** The artefact
> carries the register at **`vintages.owner_state.devices`**, as
> `{status, reason, count, last_seen_at}`, and Step 1 below is no longer a question asked
> from memory.
>
> **What it reads today, from the artefact rather than from this file:** running
> `python3 scripts/run_engine.py` on this branch publishes
>
> ```json
> "devices": { "status": "unavailable", "reason": "not_registered", "count": null, "last_seen_at": [] }
> ```
>
> — and that is correct, not a fault. Nothing has registered because the browser half ships
> with **#95, which is held**. The first nightly after #95 deploys is the first that can
> report a number, and until then the honest reading of this precondition is unchanged.
> `count` is `null` rather than `0` deliberately: nobody having opened the app and nobody
> having registered are different facts, and only one of them is known here
> (ARCH-DRIVER-002, rule 8).

> **Step 1's evidence, read 2026-09-24** off `public/data/dashboard.json` (`run_at`
> 2026-09-24T02:46Z): `devices` is `available`, `count` **4**, last seen 2026-09-16,
> 09-17, 09-22 and 09-23. So four browser profiles have written owner state since #95
> deployed. Per ADR-021's finding 4 that is neither a floor nor a ceiling on the physical
> devices. What is left is the owner's confirmation that every device he uses is among
> them, and it was put to him on 2026-09-24.
>
> **Step 1 becomes:** read `count` and `last_seen_at` off `public/data/dashboard.json`, show
> the owner that list of dates, and ask him to confirm it covers every device he uses. The
> confirmation is still his — what changed is that he confirms against evidence.
>
> **Correction to P4-OQ-1's row below.** It says the count "gives a floor and a date". It
> does not, and ADR-021's own review recorded that as finding 4: clearing site data mints a
> new id and two browsers on one phone count twice, so the number can **exceed** the physical
> fleet. It is neither a floor nor a ceiling — it is the number of distinct browser profiles
> that have written. Stating the wrong bound is worse than stating none (rule 13's own
> distinction), and the row still states it. **smartshelf-architect.**

- [ ] **Step 1:** confirm with the owner that every device has been used since the cut-over
- [ ] **Step 2:** remove the migration and its tests; keep the three legacy keys **unread
      but not deleted** — removing the migration is reversible, deleting a user's data is not
- [ ] **Step 3:** full suite, bundle, commit

---

### Task 4.4: Checkpoint 4

- [ ] `npm run check:bundle` — **`index.html` under 500 KB** (the owner's entry; see the
      2026-09-13 answer under Task 4.1), and `CEILING_KB` — the ratchet on total build
      output — lowered to the new measured size
- [ ] `npm run lint`, `npx vitest run`, `npm run test:py`, `npm run build` all green
- [ ] `npm run check:surface`, `check:signals`, `check:independence` green
- [ ] `git grep` finds no reference to anything removed, in code **or** in docs outside
      `docs/archive/`
- [ ] `v1-attic` resolves on the remote and builds

> **Where it stands, 2026-09-24.** Not closable yet. Task 4.2 keeps `operational.json` and
> `loadOperationalData.js` until F13 (#83) rebuilds the telemetry surface, and Task 4.3
> waits on the owner. Each check as it reads today, on `phase4/checkpoint-4` over `b0ce7ba`:
>
> | Check | Result |
> |---|---|
> | `check:bundle` | `index.html` **417 KB**, under the 500 KB target; total **976 KB**, under `CEILING_KB` 1000. Not lowered, because no deletion moved it (Task 4.1 above). Lowered when this checkpoint closes, after Task 4.2 and F13 have changed what ships |
> | lint, vitest, `test:py`, build | green: vitest 479/479, pytest 585 passed and 7 skipped |
> | `check:surface`, `check:signals`, `check:independence` | green. `check:signals` needs `data/internal/silver_pos/`, and refuses without it, correctly |
> | `git grep` for anything removed | swept: `810d9b3` (code, 33 files) and `f7c54d3` (docs, 5 files). See below |
> | `v1-attic`, `v1-attic-2026-09-24` | both resolve on the remote (`bf1d47a`, `959a572`) and build |
>
> **How the grep criterion was read.** Taken literally it cannot pass: this file, ADR-028,
> §20.1 and every dated review exist to name what was removed. So the sweep asked a
> narrower question of each hit: does it present a removed file as present, as the thing
> that reads, enforces or consumes something now, or as a command to run? Those were
> rewritten, and history was left as history. Method: every file deleted since `v1-attic`
> outside `data/` (133, `git diff --diff-filter=D`), searched by name (by path where the
> name is generic or still in use elsewhere) over the tree outside `docs/archive/` and
> `data/`. 96 code lines and 332 documentation lines matched.
>
> **Left for their owners:**
>
> - F3's intent (line 44) names `storeFormat.js` as the gate that labels a supermarket
>   comparison. The engine does that now (`competitor_position.py`, `role: comparable |
>   context`). **smartshelf-pm.**
> - `.ai-codex/lib.md` is an export index generated on 2026-08-02 that nothing regenerates,
>   and much of it lists removed modules. Regenerate it or delete it, whoever uses it.
> - `src/App.css` still carries rules for the removed components, and the three
>   dictionaries still carry strings for the removed pages (`sp.*`, the reorder
>   explanation, `gap.*`). Unlike the modules, these **ship**, so they are the one deletion
>   left that can move the ratchet. It needs its own unit, with a usage sweep that counts
>   keys built at runtime.

---

## Open questions

| id | Question | Owner | Blocks |
|---|---|---|---|
| ~~P4-OQ-1~~ | **Answered 2026-09-13 — the artefact publishes a device count.** Not "ask the owner": what Task 4.3 deletes is irreversible, and a recollection is unverifiable afterwards. Specified in [ADR-021](../architecture/decisions/ADR-021-the-artefact-states-how-many-devices-wrote-owner-state.md), which is `Ready for review` — Task 4.3 waits on its acceptance **and** its implementation. Note the ADR's own limit: the count gives a floor and a date, not proof of completeness, so the owner still confirms "that is all of them" — now against a number rather than from memory | smartshelf-architect | Task 4.3 |
| ~~P4-OQ-2~~ | **Answered 2026-09-13 — it goes with the group.** See below. | smartshelf-architect | — |
| ~~P4-OQ-3~~ | **Answered 2026-09-13 — telemetry stays and is rebuilt against `dashboard.json`; it comes off §20.1's REMOVE list.** The question's premise did not survive checking: the page has measured nothing since the cut-over (frozen source, incompatible id namespace, pre-V1 decision store — see `deployment.md` §Internal telemetry page). So deleting it would not have cost the pilot its instrument, because it had already lost one. Rebuilding it is **F13 in substance**, and SPEC-000 §4's reason for never specifying F13 — *"already measured by an existing surface"* — is now known to be false. **smartshelf-pm owes F13 a spec**, and its three numbers are owner decisions (F13 intent §Solution) | smartshelf-pm, then architect | no longer blocks Task 4.1c |
