---
ID: PLAN-PHASE-3
Title: Phase 3 — Reproduction and gates
Status: Ready for review
Owner: smartshelf-architect
Version: 1.0 (2026-09-12)
Parent: [Implementation Plan](plan.md)
Related Specs: F7-S1 (AC-120 … AC-128), F2-S1, F6-S1
Inputs: [docs/architecture/system-design.md §11.6, §17, §18, §22, docs/features/F7-figure-provenance/specs/F7-S1-figure-provenance.md, docs/architecture/decisions/ADR-017-a-run-states-whether-its-sales-evidence-arrived.md]
Updated: 2026-09-12
---

# Phase 3 — Reproduction and gates

**Depends on:** Phases 1 and 2. The engine publishes 46 figures and the browser renders
them; nothing yet proves a figure can be **recomputed** by someone who did not run it.

**Delivers:** `scripts/figures.py` as the engine's print mode, content addressing for the
artefact, ADR-017's `imported_this_run`, V1 signal probes replacing the reorder-era ones,
and a nightly workflow that runs the engine rather than `refresh_pipeline.py`.

**Checkpoint 3:** a fresh clone runs `npm run figures`, exits 0 in under two minutes, and
its figures equal the committed artefact's `figures{}` (AC-127). Nightly green two nights
running.

---

## What this phase is really for

The PRD's own banner says it: **«لا تقرأ هذه الأرقام من الورق — شغّل `npm run figures`»**.
Every figure in this project is supposed to be recomputable on demand, and today
`scripts/print_figures.py` computes them by **a second implementation** — the one that
produced 18% while the engine produced 26% until ADR-015, and that still counts over the
whole catalogue while the engine counts over the living one.

Two implementations of one number is the defect. This phase deletes one of them.

## Ordering

```
3.0 figures.py = engine --print ── 3.1 content addressing ── 3.2 imported_this_run
                                                                      │
3.3 V1 signal probes ─────────────────────────────────────────────────┴─ 3.4 nightly ── 3.5 Checkpoint 3
```

3.3 is independent of 3.0 – 3.2. 3.4 needs all of them. 3.5 is the gate.

---

### Task 3.0: `figures.py` is the engine's print mode, not a second implementation

**Files:**
- Create: `scripts/figures.py`
- Modify: `package.json` — `"figures": "python3 scripts/figures.py"`
- Delete: `scripts/print_figures.py`
- Test: `tests/engine/test_figures_cli.py`

**Interfaces:**
- `python3 scripts/figures.py [--json]` — **no arguments required** (NFR-062). Exit 0 with
  every figure; **exit 1 naming the missing input** when any registered figure is
  unavailable. It runs `run_engine(mode='print')` and reads `artefact['figures']`. It
  computes nothing of its own.
- Human output stays Arabic and keeps `print_figures.py`'s shape — it is what the 12/9
  meeting reads.

**Why deleting the old one is the point.** `print_figures.py` is a second implementation of
every V1 figure. It disagreed with the engine on F1's ceiling until ADR-015, and it still
counts over the whole catalogue where the engine counts over the living one (D-14 rests on
that difference). Keeping both means every future figure is right in one place and wrong in
the other, with no test that would say which.

- [ ] **Step 1: Write the failing test** — `figures.py` with no arguments exits 0 and its
  JSON equals `run_engine(mode='print')['artefact']['figures']` key for key; a run with a
  registered figure unavailable exits 1 and names the input.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** as a thin wrapper. If a number the old script printed has no
  figure in the artefact, **stop and raise it** — that is a missing figure in the engine,
  not a reason to compute it here.
- [ ] **Step 4:** `npm run figures` and diff its output against the previous script's,
  recording every difference in the commit body. D-14 turns on one of them.
- [ ] **Step 5: Commit.**

---

### Task 3.1: Content addressing — the artefact says what it was built from

**Files:**
- Modify: `src/engine/publish.py` — add `inputs_digest` to the artefact
- Modify: `schemas/dashboard.schema.json`
- Test: `tests/engine/test_publish.py`

**Interfaces:**
- `build_artefact(...)` gains `inputs_digest: str` — a hex digest over the **content** of
  every input the run read: the POS silver tables, the sales tables, the competitor
  snapshot ids, the owner-state pull, and `configs/policy.yaml`.
- Two runs over identical inputs produce an identical digest. A changed policy constant
  changes it, because a figure computed under a different threshold is a different figure.

**Why.** AC-127 asks whether a fresh clone reproduces the committed figures. Without a
digest the only answer is "the numbers look the same", which is how 14,406 became 2,848 in
the documents while nobody noticed. With it, "reproduced" means *the same inputs produced
the same output*, and a mismatch names itself.

- [ ] **Step 1–5:** failing test (identical inputs → identical digest; a changed policy
  constant changes it; the digest is in the schema and the publisher refuses an artefact
  without it) → implement → `pytest tests/engine` → commit.

---

### Task 3.2: `imported_this_run` (ADR-017)

**Files:**
- Modify: `src/engine/run.py` — the sales step's status and the run verdict
- Modify: `src/engine/inputs.py` — the vintage block
- Modify: `schemas/dashboard.schema.json`
- Test: `tests/engine/test_run.py`

**Interfaces:** exactly ADR-017 —
1. `_sales_import` contributing **no rows** reports step status `degraded`, not `ok`
2. the run verdict is at least `degraded` in that case
3. `vintages.sales.imported_this_run: boolean`

Phase 2's data page already renders the field when present and **"unknown"** when absent,
so this task turns that display on rather than requiring a browser change.

- [ ] **Step 1: Write the failing test** — a run over an empty reports directory has
  `imported_this_run: false`, a `degraded` sales step and a `degraded` verdict; a run with
  reports has `true` and `ok`.
- [ ] **Step 2–5:** run → implement → `npm run check:independence` still passes (the probe
  withholds reports on purpose and must not start failing for the new reason) → commit.

---

### Task 3.3: V1 signal probes

**Files:**
- Modify: `scripts/check_signals_live.mjs` — V1 probes over the artefact
- Test: `scripts/__tests__/check_signals_live.test.mjs`

**Interfaces:** the mechanism is kept (§20.1 REFACTOR) and the probes are replaced. Today
it probes the reorder engine, which leaves the build at Phase 4. The V1 probes ask the same
question of each capability: **with this input present, does anything move?**

One probe per capability, each asserting a *published* count changes when its input is
withheld — crossing `inputs.py` and `run.py`, never calling a capability directly. That is
the same rule Task 1.9 enforces for reconciliation, generalised.

- [ ] **Step 1–5:** failing probes → implement → run against real data → commit.

---

### Task 3.4: The nightly workflow runs the engine

**Files:**
- Modify: `.github/workflows/collect-daily.yml`

**Interfaces:** the order is pull → import → engine → publish → probes → commit, replacing
`refresh_pipeline.py` with `scripts/run_engine.py`.

**Two things it must not do.**
- It must **not** stop writing `operational.json` yet. §20.2 keeps it for one release so a
  rolled-back browser still works, and Task 2.7's cut-over has not happened (D-14).
- It must **not** commit `dashboard.json` while the owner's screen reads
  `operational.json` — committing both is fine; serving the wrong one is not.

`FIREBASE_SERVICE_ACCOUNT_JSON` is required here (Task 0.13 step 5, still unset). Without
it every nightly artefact carries `owner_state: unavailable` and asks the owner nothing.

- [ ] **Step 1–4:** update the workflow → run it on a branch → confirm the artefact it
  commits validates and its `inputs_digest` differs from the previous night's only when an
  input changed → commit.

---

### Task 3.5: Checkpoint 3

**Files:** none — a gate.

- [ ] `git clone` into a clean directory, `npm ci`, `pip install -r requirements.txt`
- [ ] `npm run figures` exits **0** in **under two minutes** (NFR-060), timed and recorded
- [ ] its output equals the committed artefact's `figures{}`, **key for key** (AC-127)
- [ ] `inputs_digest` matches the committed artefact's
- [ ] `npm run check:signals` and `npm run check:independence` pass
- [ ] the nightly workflow is green **two nights running**

A fresh clone has no `data/**` (CLAUDE.md rule 6), so Checkpoint 3 measures what a stranger
can actually reproduce. If `npm run figures` needs a POS import first, **that is the
finding** — record it rather than importing and re-running.

---

## Open questions

| id | Question | Owner | Blocks |
|---|---|---|---|
| P3-OQ-1 | `print_figures.py` counts over the whole catalogue; the engine counts over the living one. Deleting it removes the only source of the D-14 figures the owner is to be shown on 12/9. Does `figures.py` need a `--whole-catalogue` mode until GAP-009 closes? | smartshelf-pm | Task 3.0 Step 3 |
| P3-OQ-2 | Checkpoint 3 requires a fresh clone to reproduce the figures, but a fresh clone has no `data/**`. Is the checkpoint "reproduces from the committed snapshots after a POS import", or does the POS export need committing? | smartshelf-architect | Task 3.5 |
| P3-OQ-3 | The CI secret is still unset, so no nightly artefact can carry owner state. Task 3.4 can land without it, but the nightly is then permanently `degraded` | smartshelf-platform | the pilot, not the task |
