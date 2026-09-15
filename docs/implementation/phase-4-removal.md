---
ID: PLAN-PHASE-4
Title: Phase 4 — Removal
Status: Ready for review
Owner: smartshelf-architect
Version: 1.0 (2026-09-12)
Parent: [Implementation Plan](plan.md)
Related Specs: F6-S1, F7-S1
Inputs: [docs/architecture/system-design.md §20.1, §20.2, §22, docs/reviews/checkpoint-3-reproduction.md]
Updated: 2026-09-13
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

---

### Task 4.1: Delete the §20.1 REMOVE list

**Files:** §20.1's REMOVE rows — the demo spine (`src/data/*.js`, `normalize-datasets.mjs`,
`loadDemoStoreData`, `posConnectors/*`), the V2/V4 analytics (`reorderEngine`,
`inventoryEngine`, `demandEngine`, `competitorEngine`, `planogram/*` and their pages), the
LLM layer (`src/lib/ai/*`, `src/api/llm_proxy.py`), telemetry, the MCP server, and the
17 unreferenced scripts.

**Interfaces:** none produced. This task only removes.

- [ ] **Step 1: Prove each is unread.** For every path, `git grep` for importers **outside
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
- [ ] **Step 2: Delete, in groups, one commit per group** — demo spine, V2/V4 analytics,
      LLM, telemetry, MCP, scripts. A single 200-file commit cannot be reviewed or
      reverted selectively.
- [ ] **Step 3:** after each group, `npm run lint && npx vitest run && npm run build &&
      npm run check:bundle`, and **lower `CEILING_KB`** to the new measured size. A group
      that does not move the bundle deleted nothing that shipped.
- [ ] **Step 4:** delete the e2e specs covering removed pages (`shelf-planning.spec.js`,
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

---

### Task 4.2: Stop writing `operational.json`

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
- [ ] **Step 2:** confirm the nightly has committed `dashboard.json` on consecutive days
- [ ] **Step 3:** delete, run everything, lower the ceiling
- [ ] **Step 4:** `check:signals` loses its reorder probes with the engine; `check:signals:v1`
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

---

## Open questions

| id | Question | Owner | Blocks |
|---|---|---|---|
| ~~P4-OQ-1~~ | **Answered 2026-09-13 — the artefact publishes a device count.** Not "ask the owner": what Task 4.3 deletes is irreversible, and a recollection is unverifiable afterwards. Specified in [ADR-021](../architecture/decisions/ADR-021-the-artefact-states-how-many-devices-wrote-owner-state.md), which is `Ready for review` — Task 4.3 waits on its acceptance **and** its implementation. Note the ADR's own limit: the count gives a floor and a date, not proof of completeness, so the owner still confirms "that is all of them" — now against a number rather than from memory | smartshelf-architect | Task 4.3 |
| ~~P4-OQ-2~~ | **Answered 2026-09-13 — it goes with the group.** See below. | smartshelf-architect | — |
| ~~P4-OQ-3~~ | **Answered 2026-09-13 — telemetry stays and is rebuilt against `dashboard.json`; it comes off §20.1's REMOVE list.** The question's premise did not survive checking: the page has measured nothing since the cut-over (frozen source, incompatible id namespace, pre-V1 decision store — see `deployment.md` §Internal telemetry page). So deleting it would not have cost the pilot its instrument, because it had already lost one. Rebuilding it is **F13 in substance**, and SPEC-000 §4's reason for never specifying F13 — *"already measured by an existing surface"* — is now known to be false. **smartshelf-pm owes F13 a spec**, and its three numbers are owner decisions (F13 intent §Solution) | smartshelf-pm, then architect | no longer blocks Task 4.1c |
