# CLAUDE.md

Guidance for Claude Code working in this repo.

**Read [docs/README.md](docs/README.md) first.** It is the documentation map. The reasoning
chain is:

```
PRD  →  Feature Intents  →  Feature Specs  →  System Design + ADRs  →  Implementation Plan  →  Code
```

| Layer | Canonical location |
|---|---|
| PRD · settled decisions D-1 … D-20 | [`docs/product/PRD.md`](docs/product/PRD.md) · [`docs/product/intent-register.md`](docs/product/intent-register.md) |
| Feature intents (F1 … F14) | [`docs/features/F#-*/intent.md`](docs/features/) |
| Feature specs (F1-S1 … F7-S1) | [`docs/features/F#-*/specs/`](docs/features/) |
| Gaps, open questions, assumptions | [`docs/features/gaps-and-open-questions.md`](docs/features/gaps-and-open-questions.md) |
| System Design | [`docs/architecture/system-design.md`](docs/architecture/system-design.md) |
| ADR-001 … ADR-028 | [`docs/architecture/decisions/`](docs/architecture/decisions/) |
| Quality gates | [`docs/reviews/`](docs/reviews/) |
| Implementation plan | [`docs/implementation/plan.md`](docs/implementation/plan.md) |
| Deploy / run / data durability | [`docs/operations/`](docs/operations/) |
| What the owner receives | [`docs/pilot/`](docs/pilot/) |

The System Design's §3 is the verified current-state trace; §6 onward is the target. This
file is the rules; those files are the map.

> **Documentation was restructured on 2026-09-08.** The former root files `intent.md`,
> `specs.md` and `design.md` no longer exist — their content was split and moved without
> semantic change into the locations above. See
> [`docs/reviews/documentation-structure-migration.md`](docs/reviews/documentation-structure-migration.md)
> for the full old → new mapping.

Anything in `docs/archive/` is retained for history and is **out of date** — every file
there carries a `LEGACY — NON-AUTHORITATIVE` banner. Do not act on it.

## Roles and workflow

This project is built by the five role skills **in this repository** at `.claude/SKILLS/`.
Each reads files, writes files, and stops. **No role calls another role.** The artifact is
the interface.

> **Why the names carry a `smartshelf-` prefix.** Runtime skill directories define generic
> `product-manager`, `product-architect`, `product-engineer` and `platform-engineer`
> skills, and on a name collision the user-level skill wins — silently loading a role that
> knows nothing about this repository's documents or its thirteen rules. The prefix makes
> the collision impossible. If a role ever loads talking about Jira epics,
> `.claude/project-context.md` or "Ready for Dev", it is the wrong skill: stop and read
> `.claude/SKILLS/<role>/SKILL.md`.

| Role | Owns | Never touches |
|---|---|---|
| `smartshelf-pm` | `docs/product/PRD.md`, `docs/product/intent-register.md`, `docs/features/F#-*/intent.md`, `docs/features/gaps-and-open-questions.md` | architecture, specs, plan, code |
| `smartshelf-architect` | `docs/architecture/system-design.md`, `docs/architecture/decisions/ADR-NNN-*.md`, `docs/features/F#-*/specs/F#-S#-*.md`, `docs/implementation/plan.md` | application code, the PRD, the intents |
| `smartshelf-engineer` | the code and tests for **one** approved spec | the PRD, the intents, any upstream doc |
| `smartshelf-platform` | deployment, CI, observability, cost alerting, `docs/operations/deployment.md` | application code, specs |
| `smartshelf-validator` | `docs/reviews/F#-validation.md` | everything — it reports, never repairs |

The thirteen rules below bind **every** role, not only the engineer. Rule 11 in
particular: no role quotes a figure it has not read from the artifact that produced it.

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

5. **One pipeline. `public/data/dashboard.json` is what the owner reads.**
   The split this rule used to describe is over — it said the front end still read the
   old artefact and that the cut-over was unplanned work. Task 2.7 cut over on
   2026-09-12, and `refresh_pipeline.py` stopped running on 2026-09-13.

   | | writes | read by | run by |
   |---|---|---|---|
   | `npm run data:refresh` → `run_engine.py` | `public/data/dashboard.json` (schema 2), `market-context.json` | **the owner's screen** — `loadDashboard.js` is the only adapter a V1 page uses | `collect-daily.yml` nightly, which **commits** it; and a human |
   | `python3 scripts/refresh_pipeline.py` | `public/data/operational.json` | nothing reachable — only `src/telemetry/` imports `loadOperationalData` | **nobody** |

   So after new POS data or a scrape, `npm run data:refresh` is the whole job.

   `refresh_pipeline.py` is **not** a fallback and must not be restarted. Its
   `product_recommendations` step requires `silver_pos/yomyom_sales.parquet`, which Task
   0.6 deleted deliberately: its `units_sold_30d` was synthesised from a monthly mean,
   which rule 13 forbids. Rebuilding that table re-introduces the invented figure;
   `--allow-no-competitor` to get a green export is rule 10. `operational.json` is frozen
   at its last good value. Phase 4 deletes the chain. The whole story is in
   [`docs/reviews/nightly-2026-09-13-incident.md`](docs/reviews/nightly-2026-09-13-incident.md).

   **This rule used to say `operational.json` survives because "ADR-009's one-shot
   outcome-id translation needs" it. That translation does not exist in code**
   (verified 2026-09-16 — `migrate()` in `src/owner/ownerState.js` is synchronous,
   copies legacy ids verbatim, and nothing under `src/owner/` mentions
   `operational.json`). So that is not a reason to keep the file. What is: the last
   reader is `src/telemetry/TelemetryDashboard.jsx`, which F13 replaces. Do not plan
   Phase 4 Task 4.2 around a translation that was never built.

6. **`data/**` is gitignored; `public/data/*.json` is committed.** A fresh clone has the
   artefacts and nothing to rebuild them from, so regenerating needs the POS import
   first — `scripts/import_yomyom_pos.py --input yomyom-inventory.csv`, then
   `npm run data:refresh`. Checkpoint 3 measured that path end to end.

   `data/external/silver/` is the exception worth knowing about: `rehydrate_silver.py`
   copies committed snapshots into it and never removes anything, so a long-lived working
   tree accumulates files a clean clone does not have and quietly produces different
   figures. It now reports those as `orphans` and warns. Believe the clone, not the
   laptop.

7. **There is no demo data, and nothing generates it.** `normalize:data` used to fall
   back, on a fresh clone, to a ~30-product demo set that overwrote
   `src/data/demoProducts.js` and five other committed files, and it refused only
   without `--allow-demo-fallback`. The demo spine, its generator and that flag were
   removed on 2026-09-24 (ADR-028): no screen had read it since the cut-over. The owner's
   screens read `public/data/*.json`, which the engine writes (rule 5). If a page needs
   data the artefact does not carry, the answer is the engine, never a generated file.

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
    never crossed the boundary where it was lost.

    Run **`npm run check:signals`**. It drives the real engine over a copy of the
    data with one input withheld at source and reads the **published artefact** —
    never a capability's return value. Two failures are caught, both silent
    otherwise: a capability that declares an input it does not need (withholding it
    takes a working signal off the owner's screen for nothing), and a capability
    that needs an input it does not declare (on the day that input is missing it
    publishes a figure computed from nothing and calls it `available`). It also
    proves detection and hygiene fail independently — withhold the sales evidence
    and `reconciliation` must go unavailable while `hygiene` still emits.

    Both probes run in `collect-daily.yml` before `dashboard.json` is committed,
    and both are **blocking** since the cut-over.

    The pre-V1 probe over the reorder ranking, `check:signals:legacy`
    (`check_signals_live.mjs`), was retired on 2026-09-24 (Phase 4 Task 4.2, #77)
    with the reorder engine it exercised (ADR-028). The two probes above are the
    ones this rule means, and the only ones there are.

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
  receiving.
- `src/` (JS) — `pages/` one file per screen · `lib/analytics/` ranking and money
  rules · `lib/dataAdapters/` reads `public/data/*.json` · `lib/i18n/` he/en.
- `scripts/` — 62 entry points (52 `.py`, 7 `.mjs`, 3 `.sh`, counted with `ls` on 2026-09-24, after Phase 4's deletions). Only the
  handful in the System Design §7 are the product.

## Commands

```bash
npm run dev            # Vite dev server
npm run data:refresh   # rebuild every dashboard input (see rule 5)
npm run test           # the JS suite (vitest) — it prints its own count
npm run test:py        # the Python suite (pytest) — likewise
npm run lint
python3 scripts/analyse_sales_movement.py   # T8: measured calendar weights
git mine               # log without the daily snapshot commits
```

Commit style: small, imperative subject, body explains *why*. The daily
`snapshot: market data` commits are machine-authored — `git mine` hides them.

---

Reproduced from `.claude/SKILLS/HANDOVER.md`, which instructs that it be pasted here
unchanged. Paths in it are relative to that file; from here, `../docs/` means `docs/`.

## Artifact chain and handover protocol

SmartShelf is built by a chain of roles. Each role reads files, writes files, and stops.
**No role calls another role.** The artifact is the interface.

### The chain

```
docs/product/PRD.md                                (the root product document)
   └─ smartshelf-pm        → docs/product/PRD.md · docs/product/intent-register.md
                           → docs/features/F#-<slug>/intent.md          (one per feature)
                           → docs/features/gaps-and-open-questions.md
                           → docs/product/open-decisions/F#-<slug>.md   (one per blocked feature)
      └─ smartshelf-architect → docs/architecture/system-design.md
                              → docs/architecture/decisions/ADR-NNN-<slug>.md
                              → docs/features/F#-<slug>/specs/F#-S#-<slug>.md   (on request)
                              → docs/implementation/plan.md
         └─ smartshelf-engineer   → source code and tests
            └─ smartshelf-platform → docs/operations/deployment.md, live URL
               └─ smartshelf-validator → docs/reviews/F#-validation.md
```

### The identifier travels

`docs/product/PRD.md` is the root document. Every feature in its register has an `F#`.
That id travels: feature `F3` becomes intent `F3`, spec `F3-S1`, validation `F3`.

Requirement identifiers **inside** a spec — `FR-…`, `INV-…`, `NFR-…`, `AC-…`, `SCN-…`,
`C-…`, `ASM-…`, `OQ-…` — are globally unique across the whole specification layer and are
**never renumbered**. The System Design §21 traceability matrix, the gate reports and the
implementation plan all cite them. If you need a fully-qualified form, prefix with the
spec id: `F1-S1.FR-001`.

Anything without a traceable id does not belong in this repository.

### Authority hierarchy

When two documents disagree, the one **higher** in this list wins. It is reproduced from
[`docs/README.md`](../docs/README.md), which is the canonical copy.

1. PRD, and the settled decisions `D-1 … D-20` in the intent register §3
2. Feature intents
3. Approved feature specs
4. System Design
5. ADRs
6. Implementation plan
7. Code — evidence of what exists, never product authority

`docs/archive/` is **LEGACY — NON-AUTHORITATIVE**. No role reads it to decide anything.

### Every artifact carries a status header

Every generated document starts with this block, and nothing else may precede it. It
extends the header style already in use across `docs/` with three fields the protocol
needs — `Owner`, `Inputs`, `Updated`:

```yaml
---
ID: F3-S1
Title: Competitor Price Position
Status: Draft
Owner: smartshelf-architect
Parent: [F3 — Competitor Price Position](../intent.md)
Inputs: [docs/product/PRD.md, docs/features/F3-*/intent.md, ADR-001, ADR-011]
Updated: 2026-09-12
---
```

Existing approved documents already carry `ID`, `Title`, `Status`, `Parent` and often
`Version`. **Do not restructure them.** Add the missing fields when you next touch a file
for another reason; never in a commit of its own.

### The status vocabulary

These are the values actually in use in `docs/`. A role reads the **first word** and
ignores any trailing explanation — `Approved — passed the Intent → Spec conformance gate`
is `Approved`.

| Status | Means | May a downstream role start? |
|---|---|---|
| `Approved` | Settled. Intents and specs use this. | Yes |
| `Accepted` | Settled. **ADRs use this instead of `Approved`** — ADR-001 … ADR-022 and ADR-024 … ADR-028 all do. | Yes |
| `Registered — not specified` | The intent is settled, and writing a spec is **deliberately forbidden** until a named decision is taken. F8 … F14 are in this state. | **No** — and not because it is unfinished. Point at the blocking `GAP-` id and stop. |
| `Living` | Continuously updated by design; never "finished". The gaps register is one. | Yes, as a reference — never cite it as settled |
| `Partial — <what is missing>` | Part written, part not. The implementation plan is here. | Only for the parts named as written |
| `Proposal — <what must confirm it>` | Not yet product authority. | No |
| `Draft` | Being written. | No |
| `Ready for review` | A role finished and handed over. Awaiting a human. | No |
| `Blocked` | Stopped on a question that is not the author's to answer. | No |
| `Superseded` | Replaced. Carries `Superseded-by:`. | No — follow the pointer |

**`Accepted` and `Approved` are the same gate.** If you treat an ADR's `Accepted` as
"not approved" you will block the whole chain on all twenty-seven of them.

### The handover rules

1. **A role may only start when every input it needs is `Approved`.**
   If any input is `Draft`, `Ready for review` or `Blocked`, stop and say which file and
   what state it is in. Do not proceed on an unapproved input.

2. **A role may never set its own output to `Approved`.**
   When you finish, set `Status: Ready for review` and stop. Approval is a human act.
   This is the gate. Marking your own work approved removes it.

3. **Hand over only when the task is ready.**
   Before setting `Ready for review`, verify your own skill's "Done when" list and state
   the result item by item. If any item fails, set `Status: Blocked`, write why under a
   `## Blocked on` heading, and stop.

4. **Unanswered questions block the chain.**
   If you cannot complete the artifact without a decision that is not yours to make, set
   `Status: Blocked` and list the questions. Never guess and continue.

5. **Stay in your lane.**
   Write only the artifacts your role owns. If you find a fault in an upstream document,
   report it — do not edit it. Corrections go back to the role that owns that file.

6. **Traceability is mandatory.**
   Every artifact names its `Inputs` and carries the `F#` of the feature it serves. An
   artifact whose id appears nowhere upstream is scope drift, and gets reported.

7. **Superseding, never overwriting.**
   When a decision changes, set the old artifact to `Superseded`, add
   `Superseded-by: <path>`, and write a new one. History is evidence — that is why
   `docs/archive/` still exists and still carries its banner.

8. **A figure is quoted from the artifact that produced it, never from another document.**
   This is CLAUDE.md rule 11, and it binds every role, not just the engineer. Counts in
   this repository have drifted by a factor of five between the markdown and the parquet.
   Read the parquet, the JSON or the test output. Cite where you read it.

### Commits are part of the handover, not a step after it

A role's output is not handed over until it is **committed**. The artifact is the
interface (above), and an uncommitted artifact is not an interface — it exists only in one
working tree.

- **One unit of work, one commit.** A plan task, an ADR, a spec, a validation record.
  Never batch several into one, and never split one across two.
- **Verified first, committed second.** Whatever your skill's "Done when" list requires
  must pass *before* the commit, not after it. A red or unrun suite is not committed.
- **Stage by path.** `data/` and `public/data/` are written as a side effect of running
  the engine; `git add -A` sweeps them in. Name the files your task named.
- **A correction to an upstream defect is its own commit**, with a message saying what was
  wrong and how the fix was verified. Those commits are why the code and the documents
  diverged, and they are the first thing a reviewer looks for.
- **Branch; do not commit to `main`.** Do not push, open a PR or merge unless asked.
- The `NEXT:` line of your four-line report is written **after** the commit exists.

### What to say at the end of every run

Finish every run with exactly these four lines:

```
ARTIFACT:  <path you wrote>
STATUS:    Ready for review | Blocked
DONE-WHEN: <each item, met or not met>
NEXT:      <the role that should run next, and what it needs from the human first>
```
