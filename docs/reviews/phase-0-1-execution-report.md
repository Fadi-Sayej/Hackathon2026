---
ID: PHASE-0-1-EXECUTION
Title: What executing the Phase 0 and Phase 1 plan found
Status: Ready for review
Owner: smartshelf-engineer
Parent: [Implementation Plan](../implementation/plan.md)
Inputs: [docs/implementation/phase-0-foundations.md, docs/implementation/phase-1-capabilities.md, public/data/dashboard.json]
Updated: 2026-09-12
---

# What executing the Phase 0 and Phase 1 plan found

Phases 0 and 1 are built: tasks 0.4 – 0.13 and 1.0 – 1.9, on branch
`engine/phase-0-and-1`, 25 commits. Python tests 317 → 442; JS 498; lint, build and the
rule-12 independence probe pass.

**Thirteen defects in the plan surfaced only under execution.** Every one was caught by
the plan's own tests — none by reading. That is the finding worth keeping: the documents
could not have revealed any of them, and a plan validated by review alone would have
shipped all thirteen.

Two further items are **not** plan defects and need a decision from a role that is not the
engineer. They are listed separately at the end.

---

## Plan defects, and how each was settled

| # | Task | What was wrong | Settled by |
|---|---|---|---|
| 1 | 0.5 | `tests/owner_state/test_model.py` collides with the existing `tests/engine/test_model.py`; under pytest's default import mode collection fails outright, so the plan's declared filename could not stand | `pytest.ini` with `--import-mode=importlib` |
| 2 | 0.6 | Its `import_yomyom_sales.py` rewrite imports `read_pos_vintage`, which **Task 0.7** creates. `collect-daily.yml:108` calls that script nightly, so applying 0.6 in order breaks the live pipeline | 0.7 executed first, then 0.6's script |
| 3 | 0.7 | The test calls `import_pos_file`, which calls `update_source()`, which writes the **committed** `public/data/sources.json` — rewriting `yomyom_pos.row_count` from **7,674 to 1** on every suite run | source-status path isolated in the fixture |
| 4 | 0.10 | The fixture omits `product_name` from its inventory rows while the loader joins on `(barcode, product_name)` — necessarily, since one fixture row has a null barcode and no other key | fixture corrected; the real table carries the column |
| 5 | 0.11 | `silver_dir` / `sales_dir` bound as signature defaults, which the task's own test then monkeypatches. An import-time default cannot be redirected that way, so the isolation silently did nothing and the test read real data | resolved at call time; they stay parameters, as Task 1.9 requires |
| 6 | 0.11 | The `_sales_import` stub takes zero arguments where the orchestrator passes two | stub widened, signature kept |
| 7 | 1.2 | The density guard runs only when a ceiling exists, so AC-008's case — no discernible collapse — could never reach it and reported `ceiling_undetermined` where the test demands `ceiling_degenerate`. INV-003 calls only the second a broken threshold | missing branch added |
| 8 | 1.2 | **The ceiling rule returns 26% on the pilot export where the approved intent says 18%.** Two collapses qualify; "the LAST candidate" takes the 24-item tail band over the 81-item policy mass | [ADR-015](../architecture/decisions/ADR-015-ceiling-is-the-densest-qualifying-collapse.md) |
| 9 | 1.1 | Three fixtures written as though the implied opening balance were `stock + receipts − units`. F2-S1 defines it as `stock − receipts + units`, so "consistent" rows came out flagged and vice versa. Every row using **real pilot numbers** was already correct; only the invented ones were inverted | fixtures aligned to the spec |
| 10 | 1.5 | Fixture identifiers (`"cheese"`, `"a"`, `"b"`) are shorter than `policy.uncomparable_min_barcode_digits`, so FR-052 classified every one structurally uncomparable — including the two that had to be comparable for the deliberate `"svc"` service code to mean anything | identifiers lengthened; `"svc"` left short |
| 11 | 1.5 | An empty `observations` list short-circuited to `unavailable`. An empty list is data; FR-051 requires each product to be counted "no comparison". `registry.py` states the convention: *"a missing input is None — never an empty frame"* | short-circuit removed; `None` still refused by `derive_status` |
| 12 | 1.8 | The withdrawn fixture product carries a cost price, so it can never become a cost question and the suppression the test asserts is unobservable | fixture given no cost |
| 13 | 1.9 | The probe withholds the raw monthly reports but copies silver wholesale. `import_sales` reports `monthly_rows: 0` and **writes nothing**, leaving a previous run's `sales_summary` in place — so evidence never disappeared and detection stayed available. The probe passed nothing | derived tables removed in the withheld copy |

One regression was **ours, not the plan's**: the `pytest.ini` fix for defect 1 broke Task
1.0's bare `from helpers import …`, because importlib mode does not put a test's own
directory on `sys.path`. Closed with `pythonpath = tests/engine` rather than by editing the
plan's test files.

---

## Not defects — decisions owed by another role

### A. A missing report day leaves detection running on stale evidence

Uncovered by defect 13 and **left untouched**. On the real pipeline, when the seven monthly
reports do not arrive, `import_sales` writes nothing and the previous run's
`sales_summary.parquet` survives. `load_inputs` reads it, and `reconciliation` publishes
findings as though the reports had arrived. Nothing in the artefact says the evidence is
stale beyond `vintages.sales`.

SPEC-002 §11's independence claim is not affected — that is now proven across the real
boundary. The question is whether detection should refuse evidence older than the current
window, and it belongs to **smartshelf-architect**.

### B. F1's published figures do not survive catalogue withdrawal

Read from `public/data/dashboard.json` at Checkpoint 1 (never from a document — CLAUDE.md
rule 11):

| | intent publishes | engine produces |
|---|---|---|
| ceiling | 18% | **18.0%** ✓ |
| inverted (confirmed loss) | 68 | **53** |
| above policy (question) | 136 | **108** |
| surfaced total | 204 | **161** |

The ceiling agrees exactly. The counts do not, and the reason is designed behaviour:
`catalogue_lifecycle` runs first and withdraws 3,916 products, so price consistency sees a
population of 2,544 rather than the 6,260 price-paired products `scripts/print_figures.py`
counts. FR-074 requires the withdrawn set to reach every other capability's population.

So the intent's 68/136 were computed over the whole catalogue including withdrawn products.
Whether the owner should be shown figures over the living catalogue or the whole one is a
product question for **smartshelf-pm**, and it changes what the 12/9 meeting is told.

### Also open, from before this work

- **ADR-015 is `Draft`.** It was decided under delegated authority and cannot be
  self-approved. Until a human accepts it the ceiling rule is provisional.
- **The live dashboard still shows 1,147 F1 entries** where the engine produces 161.
  Nothing reads `dashboard.json` yet; Phases 2–4 are not written. Recorded in
  [F1-validation](F1-validation.md).
- **Task 0.13 steps 2–5** need Firebase, Vercel and GitHub credentials — **smartshelf-platform**.
  `owner_questions` publishes `unavailable: answer_storage_unavailable` without them.

---

## Checkpoint 1 — the figures, from the artefact

| capability | status | counts |
|---|---|---|
| `price_consistency` | available | ceiling 18.0% · 53 inverted · 108 questions · population 2,544 |
| `reconciliation` | available | 460 flagged |
| `hygiene` | available | 622 negative stock · 308 no identifier · 61 absent price |
| `catalogue_lifecycle` | available | 1,300 living · 3,916 withdrawable · 1,658 idle |
| `competitor_position` | available | 3,186 comparable · 1,768 matched |
| `margin_below_cost` | available | 17 below cost · 15 thin |
| `owner_questions` | unavailable | `answer_storage_unavailable` |

`value_kinds_present: ['per_sale']`. Run status `degraded`, correctly — the owner state is
unreachable without credentials and the artefact says so rather than publishing an empty
answer set.

Two counts sit outside the plan's §3.5 expectations and are **not explained**:
`absent_price` 61 against ~223, and `living` 1,300 against ~1,565. Both are plausibly POS
vintage differences — the silver tables were re-imported from `yomyom-inventory.csv` during
this work — but that was not verified, and it should be before any of these numbers is
quoted to the owner.
