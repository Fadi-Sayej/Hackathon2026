---
ID: PLAN-PHASE-2
Title: Phase 2 — Browser
Status: Ready for review
Owner: smartshelf-architect
Version: 1.0 (2026-09-12)
Parent: [Implementation Plan](plan.md)
Related Specs: F6-S1 (AC-100 … AC-112), F7-S1, F5-S1, F2-S1, F1-S1, F3-S1, F4-S1
Inputs: [docs/architecture/system-design.md §9, §10, §11.3–11.5, §12, §13, §20, docs/features/F6-daily-action-surface/specs/F6-S1-daily-action-surface.md, docs/implementation/phase-1-capabilities.md]
Updated: 2026-09-12
---

# Phase 2 — Browser

**Depends on:** Phase 1's artefact. `public/data/dashboard.json` exists, validates against
`schemas/dashboard.schema.json`, and carries seven capabilities (Checkpoint 1, recorded in
[the execution report](../reviews/phase-0-1-execution-report.md)).

**Delivers:** one spine — the artefact plus owner state — replacing the two the app has
today. `loadDashboard`, the browser's owner-state model with its migrations, `compose`,
the daily surface, five capability pages, the question panel, the data page, and the
cut-over away from `operational.json`.

**Checkpoint 2:** AC-100 … AC-112 pass, and the e2e invariants in Task 2.9 hold against a
real artefact.

---

## What this phase must not do

- **No selection logic in a component.** `compose` decides what appears; a component
  renders what it is given. A page that filters entries itself cannot be tested against
  AC-100 and will drift from the engine's ordering.
- **No recomputation of anything the engine computed.** The browser never re-derives a
  ceiling, a count, a value or a status. If a number is needed and absent from the
  artefact, that is a capability change, not a browser change.
- **No number where the engine published none.** D-3. An absent value renders as absent;
  it never becomes 0, "—" with a currency symbol, or a blank that reads as zero.
- **No new dependency.** The app has i18n, RTL, formatting and persistence already
  (§20.1 REUSE rows). Anything else needs an ADR.

## Ordering

```
2.0 loadDashboard ─┬─ 2.1 owner state + migrations ─┬─ 2.2 compose ── 2.3 DailyPage
                   │                                 │
                   ├─ 2.4 capability pages ──────────┤
                   ├─ 2.5 questions ─────────────────┤
                   └─ 2.6 data page ─────────────────┴─ 2.7 spine + cut-over ── 2.8 i18n ── 2.9 e2e
```

2.4, 2.5 and 2.6 are independent of each other once 2.0 and 2.1 are merged. 2.7 needs
every page. 2.9 needs 2.7.

## File structure (this phase)

| File | Responsibility |
|---|---|
| `src/lib/dataAdapters/loadDashboard.js` | fetch + schema-validate the artefact; honest status; no fallback |
| `src/owner/ownerState.js` | the browser's owner-state model, cache, write-through, migrations |
| `src/owner/outcomes.js` | record/read outcomes; the closed enums; the ADR-016 snapshot |
| `src/owner/answers.js` | record/read cost answers |
| `src/surface/compose.js` | selection and ordering for the daily surface — the only selector |
| `src/surface/DailyPage.jsx`, `src/surface/EntryCard.jsx` | render what `compose` returns |
| `src/pages/CapabilityPage.jsx` | one component, five routes: the full set per capability |
| `src/questions/QuestionPanel.jsx` | the engine's questions, at most three (D-8) |
| `src/pages/DataPage.jsx` | vintages, capability statuses, run verdict |
| `src/App.jsx` | one spine; nav reduced to ten items |

## Conventions every task in this phase follows

- **Tests are vitest**, beside the unit under test, named for the `AC-` they discharge.
- **A fixture artefact** lives at `src/__fixtures__/dashboard.fixture.json` and is built by
  Task 2.0. Every later task reads it rather than inventing a shape.
- **Three languages or it is not done.** Any user-visible string added in a task ships with
  `ar`, `he` and `en` keys in the same commit. Task 2.8 is the parity check, not the place
  translations are written.
- **One task, one commit**, green before committed — see the engineer skill.

---

### Task 2.0: `loadDashboard` — read the artefact, or say why not

**Files:**
- Create: `src/lib/dataAdapters/loadDashboard.js`
- Create: `src/__fixtures__/dashboard.fixture.json`
- Test: `src/lib/dataAdapters/__tests__/loadDashboard.test.js`

**Interfaces:**
- Produces: `loadDashboard({ fetchImpl = fetch, url = '/data/dashboard.json' }) -> Promise<{ status: 'ok' | 'unreachable' | 'invalid', artefact: object | null, reason: string | null }>`.
- **Never throws and never falls back.** An unreachable or invalid artefact is a *state the
  UI renders*, not an exception and not a reason to show older data. `loadOperationalData.js`
  is not modified and not deleted here — Task 2.7 removes its last caller.
- **No schema validation, and no validator dependency**
  ([ADR-018](../architecture/decisions/ADR-018-the-browser-does-not-ship-a-schema-validator.md)).
  The schema is enforced where the artefact is produced (`publish.py`) and again in CI, so
  a third copy in the browser would spend the §16 bundle budget on a case the first two
  refuse to produce. `loadDashboard` checks four preconditions it cannot render without:
  the response parses, `schema_version === 2`, `capabilities` is an object, and every
  capability carries a `status` — the last because AC-107 is unachievable without it.

- [ ] **Step 1: Build the fixture from a real artefact**

Run the engine and copy its output, so the fixture cannot describe a shape the engine does
not produce:

```bash
python3 scripts/run_engine.py --skip-market
mkdir -p src/__fixtures__ && cp public/data/dashboard.json src/__fixtures__/dashboard.fixture.json
```

Then trim it by hand to at most three entries per capability, keeping **one** of each
`characterisation` present and **both** an `available` and an `unavailable` capability.
Keep `vintages`, `thresholds`, `figures` and `run` whole — they are what the data page and
the provenance strip read.

- [ ] **Step 2: Write the failing test**

```javascript
// src/lib/dataAdapters/__tests__/loadDashboard.test.js
import { describe, expect, it } from 'vitest'
import fixture from '../../../__fixtures__/dashboard.fixture.json'
import { loadDashboard } from '../loadDashboard'

const ok = (body) => async () => ({ ok: true, status: 200, json: async () => body })

describe('loadDashboard', () => {
  it('returns the artefact when it validates', async () => {
    const r = await loadDashboard({ fetchImpl: ok(fixture) })
    expect(r.status).toBe('ok')
    expect(r.artefact.schema_version).toBe(2)
  })

  it('reports an unreachable artefact without throwing', async () => {
    const r = await loadDashboard({ fetchImpl: async () => { throw new Error('offline') } })
    expect(r.status).toBe('unreachable')
    expect(r.artefact).toBeNull()
  })

  it('reports a 404 as unreachable, not as an empty dashboard', async () => {
    const r = await loadDashboard({ fetchImpl: async () => ({ ok: false, status: 404 }) })
    expect(r.status).toBe('unreachable')
  })

  it('refuses an artefact that does not validate', async () => {
    const broken = { ...fixture, schema_version: 1 }
    const r = await loadDashboard({ fetchImpl: ok(broken) })
    expect(r.status).toBe('invalid')
    expect(r.artefact).toBeNull()
    expect(r.reason).toMatch(/schema_version/)
  })

  it('refuses a capability with no status rather than rendering it as empty', async () => {
    const broken = structuredClone(fixture)
    const first = Object.keys(broken.capabilities)[0]
    delete broken.capabilities[first].status
    const r = await loadDashboard({ fetchImpl: ok(broken) })
    expect(r.status).toBe('invalid')
  })
})
```

- [ ] **Step 3: Run the test** → FAIL, module not found.
- [ ] **Step 4: Implement** the four checks of ADR-018. Add no dependency: `ajv` and `zod`
  appear in `node_modules` only as transitive build-tool dependencies and may vanish on any
  unrelated install.
- [ ] **Step 5:** `npx vitest run src/lib/dataAdapters` → 5 passed. Commit.

---

### Task 2.1: Owner state in the browser, and the one-shot migrations

**Files:**
- Create: `src/owner/ownerState.js`, `src/owner/outcomes.js`, `src/owner/answers.js`
- Test: `src/owner/__tests__/ownerState.test.js`, `src/owner/__tests__/outcomes.test.js`

**Interfaces:**
- `loadOwnerState() -> OwnerState` — reads `smartshelf.ownerState.v2`, running the
  migrations below **once** if it is absent.
- `recordOutcome(entry, { status, reason?, deferredUntil? }) -> Promise<void>` — writes the
  cache first; the UI commits only after the cache write succeeds (§9.3). A failed
  Firestore write is retried by the existing reconcile on `online`.
- `recordAnswer(barcode, { value, status }) -> Promise<void>`.
- Closed enums, validated on write: `status ∈ {acted, declined, deferred}`,
  `reason ∈ {wrong_data, not_worth_it, already_handled}`.

**The snapshot is mandatory and carries the family (ADR-016).**

```
snapshot: { signal_family, capability, barcode, value?, kind?, characterisation }
```

`entry_id` is a hash with no inverse, so a snapshot written without `signal_family` loses
the only durable grouping key INT-MEAS has. `recordOutcome` **refuses** an entry lacking
`signal_family` — the same refusal that closes the status and reason enums.

**Migrations (§20.2), one shot, additive, never destructive.** The three legacy keys are
read once into `smartshelf.ownerState.v2` and then left in place, unread:

| Legacy key | Becomes | Enum mapping |
|---|---|---|
| `smartshelf.operationalActions.v1` | `outcomes` | `DONE→acted`, `DISMISSED→declined`, `SNOOZED→deferred` |
| `smartshelf.ownerAnswers.v1` | `answers` | — |
| `smartshelf.demoState.v1.recommendationDecisions` | `outcomes` | as above |

A migrated outcome has **no** `signal_family`: it is written as `null`, a stated absence,
never guessed (D-3). A migrated outcome keeps its legacy id; the id translation against the
last `operational.json` is a separate concern that survives to Phase 4 (§20.2), and this
task does not attempt it.

- [ ] **Step 1: Write the failing tests** — at minimum:
  - a migrated `DONE` becomes `acted` and survives a second `loadOwnerState()` without
    doubling
  - a migrated outcome has `signal_family: null`, not a guess and not an omitted key
  - `recordOutcome` refuses an entry with no `signal_family`
  - `recordOutcome` refuses a status or reason outside the enum
  - a failed cache write leaves the outcome **unrecorded** and reports it (AC-105's
    failure half)
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**, reusing `src/lib/persistence/*` unchanged (§20.1 REUSE).
- [ ] **Step 4:** `npx vitest run src/owner` → all pass. Commit.

---

### Task 2.2: `compose` — the only thing that decides what the owner sees

**Files:**
- Create: `src/surface/compose.js`
- Test: `src/surface/__tests__/compose.test.js`

**Interfaces:**
- `compose(artefact, ownerState, { now }) -> { entries: Entry[], unavailable: {id, reason}[], nothingToDo: boolean }`
- At most `thresholds.surface.bound` entries (10). Ordering: valued entries first, in
  descending value **within a kind**, then unvalued in `thresholds.surface.unvalued_order`,
  at most `unvalued_places` (3) of them.

**The rules this function exists to enforce**, each with its acceptance line:

| Rule | Why | AC |
|---|---|---|
| At most ten entries | D-9 | AC-100 |
| No count of what is not shown | a backlog number turns a daily surface into a queue the owner is failing | AC-101 |
| Descending value **within a kind**, never across kinds | D-2 — a per-sale and a one-off amount are different quantities | AC-102, AC-103 |
| An entry whose outcome is recorded does not appear | AC-105 | AC-105 |
| A deferred entry does not appear until `deferred_until` | | AC-105 |
| One product appears once | INV-056 | AC-109 |
| An unavailable capability is reported as unavailable | never as zero findings | AC-107 |
| No entries **and** no unavailability → explicit nothing-to-do | absence is a state, not a blank | AC-108 |

- [ ] **Step 1: Write the failing tests**, one per row above, against the fixture. The
  ordering tests must include **two kinds present at once**: a suite that only ever sees
  `per_sale` cannot fail AC-103, which is the rule most likely to be broken later.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Pure function: no fetch, no clock read (`now` is a parameter),
  no persistence. Sorted iteration throughout, so the same artefact and the same owner state
  produce the same surface (§ determinism).
- [ ] **Step 4:** `npx vitest run src/surface` → all pass. Commit.

---

### Task 2.3: `DailyPage` and `EntryCard`

**Files:**
- Create: `src/surface/DailyPage.jsx`, `src/surface/EntryCard.jsx`
- Test: `src/surface/__tests__/DailyPage.test.jsx`

**Interfaces:** `DailyPage` renders what `compose` returns and owns no selection. Keeps
four behaviours from `OperationalPage.jsx` (§20.1): search, print, handled/undo, and the
source strip.

**What a card must and must not show:**
- Every estimated value is **labelled estimated on the card itself** (AC-104) — not in a
  legend, not in a tooltip, not only in a colour.
- A card whose entry has no value shows **no value area at all** (D-3) — not a dash, not a
  zero, not an empty currency symbol.
- No velocity claim where there is no sales evidence (AC-111). The entry carries no such
  field; the card must not synthesise one from a quantity.
- The window / vintage / thresholds strip is rendered for every count (ARCH-DRIVER-007).

- [ ] **Step 1: Write the failing tests** — an estimated value is labelled; a valueless
  entry renders no value element; recording an outcome removes the card and survives a
  remount (AC-105); an unavailable capability renders its reason (AC-107); the empty state
  is explicit (AC-108).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4:** vitest → pass. Commit.

---

### Task 2.4: The five capability pages, and the margin browse

**Files:**
- Create: `src/pages/CapabilityPage.jsx`
- Test: `src/pages/__tests__/CapabilityPage.test.jsx`

**Interfaces:** one component, six routes — price, reconciliation, hygiene, competitor,
catalogue, and margin (browse-only). Renders `artefact.capabilities[id]` whole: entries,
counts, thresholds, and the unavailable reason when there is one.

This is where AC-110 is discharged: **the full set per capability stays reachable** away
from the daily surface. The ten-entry bound is a property of the surface, not of the data.

`margin_below_cost` is browse-only and **is not admitted to the daily surface** until
SPEC-008 exists (plan.md release conditions, SPEC-GAP-A). The page renders it; `compose`
does not select it.

- [ ] **Step 1–4:** failing test (an unavailable capability renders its reason and no zero;
  the entry count on the page is the capability's own, not the surface bound) → implement →
  vitest → commit.

---

### Task 2.5: The question panel

**Files:**
- Modify: `src/questions/QuestionPanel.jsx` (refactored from `src/lib/questions/answerStore.js` + the existing panel, §20.1)
- Test: `src/questions/__tests__/QuestionPanel.test.jsx`

**Interfaces:** renders `artefact.capabilities.owner_questions.items` — **the engine's
questions**, never the browser's. `src/lib/questions/openQuestions.js` and `proposeGroup.js`
are replaced, not adapted: they ask the wrong questions for V1 (§20.1 REPLACE).

- At most three on screen at once (D-8) — and the limit is read from
  `capabilities.owner_questions.limit`, not hard-coded.
- `owner_questions` publishing `unavailable: answer_storage_unavailable` renders as
  unavailable, not as "no questions today" (AC-107's rule, applied here).
- An answer is written through `recordAnswer` from Task 2.1.

- [ ] **Step 1–4:** failing test (unavailable ≠ no questions; the limit comes from the
  artefact; an answer round-trips) → implement → vitest → commit.

---

### Task 2.6: The data page

**Files:**
- Create: `src/pages/DataPage.jsx`
- Test: `src/pages/__tests__/DataPage.test.jsx`

**Interfaces:** renders `vintages`, every capability's status, and `run` — the verdict and
its steps. This is the page an operator opens when a number looks wrong.

It must show, plainly:
- the POS vintage (`vintages.pos.as_of`) and the sales window (`first`, `last`, `months`)
- **whether this run's sales reports arrived** — `vintages.sales.imported_this_run`
  ([ADR-017](../architecture/decisions/ADR-017-a-run-states-whether-its-sales-evidence-arrived.md)).
  The field does not exist yet; ADR-017 lands in Phase 3. Render it when present and render
  **"unknown"** when absent — never `true`, which would assert something this artefact
  cannot support.
- the owner-state status and pull time
- the run verdict, and for a `degraded` or `partial` run, which step caused it

- [ ] **Step 1–4:** failing test (a degraded run names its cause; a missing
  `imported_this_run` renders unknown, not true) → implement → vitest → commit.

---

### Task 2.7: One spine, ten nav items, and the cut-over

**Files:**
- Modify: `src/App.jsx` — one spine: artefact + owner state
- Modify: `src/components/layout/AppShell.jsx` — nav reduced to ten items
- Test: `src/__tests__/App.spine.test.jsx`

**Interfaces:** the app reads **`dashboard.json` only**. `loadOperationalData.js` loses its
last caller in this task and is deleted in Phase 4, not here — a rolled-back browser must
still work for one release (§20.2).

Nav, exactly ten: daily · price · reconciliation · hygiene · competitor · catalogue ·
margin · questions · receiving · data.

`operational.json` **keeps being written for one release** (§20.2) and `sources.json` stops
immediately. Removing either is Phase 4.

- [ ] **Step 1–4:** failing test (the app makes no request for `operational.json`; an
  `invalid` artefact renders the invalid state rather than an empty dashboard) → implement →
  vitest → commit.

---

### Task 2.8: Three languages, no untranslated key

**Files:**
- Modify: `src/lib/i18n/dictionaries/{ar,he,en}.js`
- Test: `src/lib/i18n/__tests__/parity.test.js`

**Interfaces:** AC-112. A test that asserts **key-set equality across the three
dictionaries** and fails on a key present in one and absent in another — so a later task
adding an English string without Arabic breaks the suite rather than the pilot.

Arabic is the owner's language and is not a translation of the English: where F1 … F7's
intents phrase something in the owner's own words, that phrasing is the source and the
English follows it.

- [ ] **Step 1–4:** parity test (failing, if any key is already missing) → fill the gaps →
  vitest → commit.

---

### Task 2.9: Checkpoint 2 — the e2e invariants

**Files:**
- Create: `e2e/daily-surface.spec.js`
- Modify: `package.json` — `"check:surface": "playwright test e2e/daily-surface.spec.js"`

**Why e2e and not unit.** Every test above hands its unit a fixture. None of them crosses
`loadDashboard` → `compose` → `DailyPage` → `ownerState` with a real artefact, and that is
the boundary CLAUDE.md rule 12 is about. Task 1.9 proved the engine's half; this proves the
browser's.

Against a **real** artefact produced by `python3 scripts/run_engine.py --skip-market`:

- [ ] at most ten entries on the daily surface (AC-100)
- [ ] no count of unshown entries anywhere in the DOM (AC-101)
- [ ] no summary sums two value kinds (AC-103)
- [ ] recording an outcome removes the entry, and it is still absent after reload (AC-105)
- [ ] an unavailable capability reads as unavailable, and the string "0" does not stand in
      for it (AC-107)
- [ ] no product appears twice (AC-109)
- [ ] the page renders in `ar`, `he` and `en` with no untranslated key and no horizontal
      overflow at 390 px (AC-112, C-53)

**Checkpoint 2 is met when** these pass and Tasks 2.0 – 2.8 are green.

---

## What Phase 2 deliberately leaves to Phase 3 and 4

| Left | To | Why |
|---|---|---|
| `vintages.sales.imported_this_run` | Phase 3 | ADR-017; the data page renders it when present |
| `figures.py` as engine `--print`, content addressing, V1 signal probes | Phase 3 | reproduction, not rendering |
| Deleting `loadOperationalData.js`, `operational.json`, the legacy keys, the id translation | Phase 4 | §20.2 — one release of overlap, then removal |
| `v1-attic` tag and the §20.1 REMOVE list | Phase 4 | nothing is deleted while a rollback target still needs it |

## Open questions

| id | Question | Owner | Blocks |
|---|---|---|---|
| ~~P2-OQ-1~~ | **Answered 2026-09-12.** Neither `ajv` nor `zod` is a direct dependency — both are transitive build-tool deps. [ADR-018](../architecture/decisions/ADR-018-the-browser-does-not-ship-a-schema-validator.md): the browser ships no validator and checks four preconditions instead | smartshelf-architect | — |
| P2-OQ-2 | `owner_questions` is `unavailable: answer_storage_unavailable` without Firebase credentials (Task 0.13 steps 2–5 are unmet). Task 2.5 renders that honestly, but the pilot needs the credentials | smartshelf-platform | the pilot, not the task |
| P2-OQ-3 | The daily surface shows entries over the **living** catalogue, so F1's published 68/136 become 53/108. Which figures does the owner see on 12/9? | smartshelf-pm | what the meeting is told, not the build |
