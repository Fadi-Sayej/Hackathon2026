---
ID: PLAN-PHASE-4
Title: Phase 4 — Removal
Status: Ready for review
Owner: smartshelf-architect
Version: 1.0 (2026-09-12)
Parent: [Implementation Plan](plan.md)
Related Specs: F6-S1, F7-S1
Inputs: [docs/architecture/system-design.md §20.1, §20.2, §22, docs/reviews/checkpoint-3-reproduction.md]
Updated: 2026-09-12
---

# Phase 4 — Removal

**Depends on:** Checkpoint 3, and on the browser cut-over (Task 2.7) having happened.

**Delivers:** the repository stops carrying two of everything. Tag `v1-attic`, delete
§20.1's REMOVE list, stop writing `operational.json`, drop the migrations, and bring the
bundle inside its budget.

**Checkpoint 4:** bundle **under 500 KB**; CI green; `git grep` finds no reference to
anything removed.

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

- [ ] `git tag -a v1-attic -m "Everything V1 removed in Phase 4, reachable here"` at the
      commit **before** the first deletion
- [ ] push the tag
- [ ] record the tag's sha in this file

Nothing else in this phase may start until the tag exists on the remote. A tag that lives
only on one machine is not a rollback.

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

- [ ] `npm run check:bundle` — **under 500 KB**, and `CEILING_KB` lowered to match
- [ ] `npm run lint`, `npx vitest run`, `npm run test:py`, `npm run build` all green
- [ ] `npm run check:surface`, `check:signals`, `check:independence` green
- [ ] `git grep` finds no reference to anything removed, in code **or** in docs outside
      `docs/archive/`
- [ ] `v1-attic` resolves on the remote and builds

---

## Open questions

| id | Question | Owner | Blocks |
|---|---|---|---|
| P4-OQ-1 | Task 4.3 needs to know every pilot device has opened the app since the cut-over. Nothing measures that today — the outcome store is per-device and the engine only sees what Firestore holds. Is "ask the owner" the answer, or does the artefact need a device count? | smartshelf-pm | Task 4.3 |
| P4-OQ-2 | §20.1 lists `src/mcp_server/` and `.mcp.json` as REMOVE, but `.mcp.json` is what launches the price server for local development. Removing it is a developer-workflow change, not just a deletion | smartshelf-architect | Task 4.1 |
