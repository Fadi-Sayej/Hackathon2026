---
ID: ADR-028
Title: The nav is the owner's, and §20.1 removes only the code no screen runs
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-24
Parent: [System Design](../system-design.md) §19, §20.1
Related Specs: F5-S1, F6-S1
Inputs: [docs/architecture/system-design.md §20.1, docs/implementation/phase-4-removal.md, ADR-024, ADR-025, #124, #152, #153, #158, #170, the production build's source maps on 2026-09-24]
Updated: 2026-09-24
---

# ADR-028 — The nav is the owner's, and §20.1 removes only the code no screen runs

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19 ·
proposed by `smartshelf-architect` to unblock Phase 4. A role may not approve its own output
(HANDOVER rule 2), so this waits for the repository owner.

## Context

§20.1 was written on 2026-09-08 for a V1 of ten nav entries, and it marks the pre-V1 pages
REMOVE. The repository owner has since decided the nav himself, one step at a time:

| date | his decision | where |
|---|---|---|
| 2026-09-16 | restore the twelve pre-V1 entries, because Reorder and the planogram screens are what the business is being built around; those with nothing honest to show say what they wait for | #124 |
| 2026-09-17 | keep the V1 daily surface beside them | `2d1f63a` |
| 2026-09-23 | one Today: the old Today page goes | #152 |
| 2026-09-23 | the six capability pages behind one collapsible heading | #153 |
| 2026-09-23 | the cost questions at the top of Today | #158 |
| 2026-09-24 | the receiving capture on the Expiry page | #170 |

Two pre-V1 pages were rebuilt on the engine along the way: Products on the catalogue
(ADR-024, #135) and Prices on the comparison (ADR-025, #155, #166).

§20.1 records none of it. It marks `PriceGapPage` and `ProductsPage` REMOVE, and both are
live. It marks `inventoryEngine.js` REMOVE, and Products runs on its `analyzeProducts`. It
describes a ten-item nav with the questions and receiving as entries of their own, and
lists the restored pages for deletion. Phase 4 Task 4.1 deletes by this table. That is why
#74 and #75 carry *"do not action this as written"*: the document and the owner disagree
in writing, and the plan cannot move until the document does.

## Measured before deciding

The production build, with source maps, lists every module that reaches the owner's
screens, including the ones loaded on demand. That is the measure used here. A grep missed
a dynamic `import()` three times in this repository (#91, #119), and the build cannot.

On `main` at `6805493` (after #170), 2026-09-24:

| | JS/JSX source files |
|---|---:|
| in `src/`, excluding tests and fixtures | 145 |
| shipped to the owner's screens | 54 |
| **not shipped by any screen** | **91** |

The 91, by group:

| group | files |
|---|---:|
| pre-V1 page components: the eight behind the awaiting shells, plus `OperationalPage`, `DataSourcePage`, `ExpiryPage` | 11 |
| V2/V4 analytics: reorder, demand, competitor, affinity, compliance, planogram engines, `storeFormat`, `mockAI`, `reorderFacts`, `recommendationTypes`, `affinityRules` | 11 |
| planogram libraries and components | 19 |
| demo data (`src/data/*.js`) and POS connectors | 11 |
| LLM layer (`src/lib/ai/*`) | 5 |
| browser market context (`src/lib/context/*`) | 8 |
| pre-V1 data adapters, including `artefactToOperational` | 9 |
| pre-V1 questions (`src/lib/questions/*`, `components/questions/QuestionPanel.jsx`) | 4 |
| `V1Spine.jsx` and `surface/pages.js`, which only tests mount | 2 |
| other components and helpers nothing renders | 11 |

## Decision

1. **The nav is the owner's, and §20.1 records it as it is:** Today (with the cost questions
   above the actions), Reorder, Approved orders, Prices, Assortment gaps, Store layout, Shelf
   plan, Products, Expiry (with the receiving capture), Overview, Report, the six findings
   pages behind one heading, and Data. An entry with nothing honest to show renders
   `PageAwaitingData`. That shell *is* the entry, not a placeholder for the pre-V1 page
   behind it.
2. **A module is REMOVE when the production build does not ship it.** No screen runs it. The
   91 above are the list. A test that covers only such a module goes with it: a test of code
   no screen runs is not coverage, it is a reason to keep dead code alive.
3. **Phase 4's rule 2 still governs each deletion.** Anything a script, the nightly or a live
   test harness still imports comes off the list until that reader is retired. Swept on
   2026-09-24 over `scripts/`, `.github/` and `e2e/`, the readers are:
   - scripts that are themselves on §20.1's REMOVE rows and go with their group:
     - `build-rag-corpus.mjs` and `normalize-datasets.mjs`, with the demo spine
     - `compare_explanations.mjs` and `report_reorder_explanations.mjs`, with the LLM layer
     - `export_competitor_market_data.py`, with the dead scripts
   - two readers that must be retired first:
     - `check_signals_live.mjs`, which the nightly runs. It imports the reorder engine, the
       demo data and `src/lib/ai/factsGuard.js`, and retires in #77
     - `check:surface`, which renders through `V1Spine` and is pointed at `App` first

   Step 1's grep is re-run before each group, and anything new it finds is reported rather
   than deleted.
4. **The page components behind the awaiting shells go; the entries stay.** That covers
   Recommendations, ApprovedOrders, Dashboard, Report, AssortmentGap, StoreLayout, ShelfPlan
   and Planogram, with the engines only they ran. They only ever ran on demo data (App.jsx's
   `AWAITING` note, rule 13). V2 builds these features on real per-day demand, not on this
   code.
5. **KEEP, because it ships:**
   - `PriceGapPage`, rebuilt on ADR-025
   - `ProductsPage`, with `inventoryEngine.analyzeProducts`, `catalogueToProducts` and `loadCatalogue`
   - `ReceivingPage` and its capture form
   - `src/questions/QuestionPanel.jsx`
   - `DailyPage`, `CapabilityPage`, `DataPage`, `PageAwaitingData`, `AppShell`, and the rest of the 54
6. **§20.1's rows change to match**, and **Phase 4 Task 4.1 is re-scoped to this list.** The
   *"do not action as written"* on #74 and #75 is lifted for exactly what is listed here.

## Rejected options

### Keep §20.1 as written, and delete the restored pages
The owner's decision outranks the System Design (the authority order in `docs/README.md`).
Deleting nav entries he asked for is not the architect's call, and the table would still be
wrong about Prices and Products, which are live.

### Keep the unshipped code "for V2"
It ran only on demo data, and V2 builds on real demand. The code that serves V2 is not this
code, which already failed on the real catalogue once: the planogram, as `navGroups.js`
records. The tag preserves it. And carrying 91 unshipped files beside 54 live
ones is how two lost screens, the cost questions and the receiving capture, stayed invisible
for a week. Code that looks live and is not is what hid them.

### Delete the awaiting shells too
Those entries are the owner's decision (#124). A page that says what it is waiting for is
the product he chose, not debris.

### Decide reachability with `git grep`
It has already missed a dynamic `import()` three times here (#91, #119). The build's source
maps list what ships, dynamic chunks included. The grep remains the check for scripts and
the nightly, which the build does not cover.

## Consequences

**We accept:** Phase 4 deletes more than §20.1 named. That includes shared components nothing
renders, such as `MetricCard` and `DataProvenanceBanner`, and the browser's market-context
code, whose Python counterpart stays and keeps publishing `market-context.json` for V2.

**We gain:** Phase 4 can proceed on a list the document and the owner agree on. Checkpoint 4
has a finish line. The tree stops carrying a second app that nobody runs.

**We will know it was wrong if:** V2 needs something removed here and its copy at the tag
does not serve. Then it is restored from the tag, not rebuilt from memory.

## Reversibility

Easy, with one condition from Task 4.0. `v1-attic` was cut on 2026-09-12, and some files on
this list were added or changed after it, `artefactToOperational.js` for one. The tag
therefore does not hold everything deleted. Re-run `git diff v1-attic..main` over the list
before the first deletion, and re-cut the tag at that commit if anything differs, as Task
4.0 already requires.

## Binds

| | How this constrains it |
|---|---|
| Phase 4 Task 4.1 | Its file list is this ADR's 91, less whatever a script, the nightly or a live harness still reads. Each group is one commit, with its tests, as the task already says |
| System Design §20.1 | The nav row, the pages row, the questions and receiving rows, and new rows for `V1Spine` and the remaining unshipped modules |
| F5, F6 | Unchanged in behaviour. The questions and the receiving capture stay where the owner put them |
