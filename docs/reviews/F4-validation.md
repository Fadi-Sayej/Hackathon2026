---
ID: F4-VALIDATION
Title: F4 — Catalogue Lifecycle · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F4-S1](../features/F4-catalogue-lifecycle/specs/F4-S1-catalogue-lifecycle.md)
Inputs: [docs/features/F4-catalogue-lifecycle/specs/F4-S1-catalogue-lifecycle.md, docs/features/F4-catalogue-lifecycle/intent.md, docs/operations/deployment.md, public/data/dashboard.json (2026-09-28), src/engine/catalogue_lifecycle.py, src/pages/CapabilityPage.jsx, src/surface/EntryCard.jsx, src/surface/compose.js, src/lib/i18n/dictionaries/, tests/engine/test_catalogue_lifecycle.py, tests/engine/test_run_capabilities.py, scripts/check_v1_signals.py, GitHub deployment records (Production)]
Updated: 2026-09-28
---

# Validation F4 — Catalogue Lifecycle

- **Deployed URL:** `https://hackathon2026-fadi19.vercel.app` (serves the sign-in page; ADR-029).
- **Commit in production:** `2a716ec`. GitHub deployment `6708764605`, `success`, 2026-09-28 11:29Z.
- **Artefact read:** `public/data/dashboard.json` at `2a716ec`, `generated_at 2026-09-28T03:10:39Z`, run `ok`, `population: whole`.
- **Context:** the pilot with the YomYom store ended on 2026-09-27 (D-23).

## Verdict

**The engine conforms; the owner's side of F4 was never built, and part of that is by his own
decision.** The classification is exact and honest: it partitions, ranks idle stock by unit
cost with no money, keeps withdrawal provisional and states why. But **what the intent is for —
a catalogue that cleans itself — does not reach the owner.** D-14 keeps every figure that depends
on automatic withdrawal off his screen until GAP-009 closes (ADR-020 publishes the `whole`
population), and GAP-009 now waits for another store (D-23). Separately, and not by decision:
no screen lists the withdrawn products, offers a revival or the CSV, asks the implausible
quantity as a question, or offers idle stock the three outcomes FR-070 requires.

---

## Pass one — conformance

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §15 | AC-060 | nothing with stock above zero is withdrawn automatically | **met** | `thresholds.withdraw_with_stock: false`; the 1,631 idle entries are `catalogue.idle`, not withdrawn. `test_ac_060_idle_is_never_withdrawn_and_ac_071_ranked_by_unit_cost_without_stock` |
| spec §15 | AC-061 | every withdrawn entry listable with its evidence, and returnable | **partial** | Listable in the artefact: `withdrawn` holds 3,903 entries, `evidence_state: no_row` (`test_withdrawn_evidence_states_no_row_not_zero`). **Returnable only in the engine:** `revival_active` honours a revival in owner state, but no screen lists withdrawn products and the browser has no action that records a revival (`git grep revival` finds none outside the engine and tests) |
| spec §15 | AC-062 | a withdrawn entry with a sale returns without owner action | **met** | Recomputed every run (ADR-004); `test_ac_062_a_sale_revives_without_owner_action` |
| spec §15 | AC-063 | a manual revival is not re-withdrawn in the same window | **met in the engine; not reachable** | `test_ac_063_manual_revival_holds_for_the_window_only`. The owner cannot make a revival (AC-061) |
| spec §15 | AC-063a | a short-window withdrawal carries the insufficiency statement | **met** | `provisional: true`, notes `provisional_window`, `seasonal_misclassification_possible`, and `statement` "Classified on 7 months (2026-01..2026-07)…"; `test_ac_063a_short_window_makes_every_withdrawal_provisional` |
| spec §15 | AC-063b | a full annual cycle re-evaluates every withdrawal | **met by construction; not exercised** | The classification is recomputed from the evidence every run (ADR-004), so a longer window re-evaluates everything. No test extends a window across a seasonal product |
| spec §15 | AC-063c | a full cycle drops the statement | **met** | `test_ac_063c_full_cycle_drops_the_statement` |
| spec §15 | AC-064 | no external system modified | **met** | Nothing in the repository writes to the POS; the engine writes only `public/data/` (D-7) |
| spec §15 | AC-065 | living, withdrawable and idle partition the classified population | **met** | 1,257 + 3,903 + 1,631 = 6,791 = 7,523 − 483 negative stock − 248 no identifier − 1 stock absent; `test_ac_065_partition_and_ac_070_exclusions` |
| spec §15 | AC-066 | no sales evidence → no classification | **met** | `check_v1_signals.py`, 2026-09-28: withholding `sales_summary` or `window` → `catalogue_lifecycle` unavailable; `test_ac_066_no_sales_evidence_means_no_classification` |
| spec §15 | AC-067 | every presentation of a dead count states the window and the seasonal limitation | **partial** | The artefact carries both (`window`, `statement`). **The catalogue page** (`CapabilityPage.jsx`) renders `counts` — "withdrawable 3,903" among them — and neither the window nor the statement; its description is "Which products are still moving, which have gone quiet, and which are finished" |
| spec §15 | AC-068 | other capabilities' counts exclude withdrawn entries | **met in `living`, suspended in what is published** | `test_the_withdrawn_set_reaches_the_other_capabilities` (population pinned to `living`). The published population is `whole` (ADR-020, D-14), so the hand-off is off by decision |
| spec §15 | AC-069 | an implausible quantity is a question wherever it appears | **partial** | The engine: `evidence.question: is_this_quantity_right`, no valuation (`test_ac_069_implausible_quantity_is_a_question_not_a_valuation`). **On screen** it is a statement: "Implausible quantity" / «كمية غير معقولة». On the morning screen `EntryCard` would print the key itself, `is_this_quantity_right`, under the label "question", which is English in `ar.js` and `he.js` |
| spec §15 | AC-070 | a negative-stock dead entry is never withdrawn | **met** | 483 `excluded_negative_stock`, none in `withdrawn`; `test_ac_065_partition_and_ac_070_exclusions` |
| spec §15 | AC-071 | idle ranked by unit cost, descending; no cost ranked last, no zero | **met** | `ordering_key` `unit_cost` from 941.95 down to `null` last |
| spec §15 | AC-071a | no idle entry or aggregate carries money from a stock quantity | **met** | 0 of 1,631 idle entries carry a `value`; no aggregate figure in `catalogue_lifecycle.*` |
| spec §15 | AC-071b | idle entries offer FR-070's outcomes; none is called correct | **missing** | FR-070 needs three: stock present and unsold · quantity wrong · no longer carried. The only buttons an idle entry gets are `EntryCard`'s generic ones: Done · Not worth it · Later |
| spec §7 | INV-030 … INV-036 | | **met in the engine** | As AC-060, AC-061 (reversible in the engine), AC-063a, AC-062, AC-064, AC-065, AC-069, AC-066 |
| boundary probe | rule 12 | depends on exactly what it declares | **met** | `check_v1_signals.py`, 2026-09-28: withholding `inventory`, `products`, `sales_summary` or `window` each makes it unavailable, and "every capability depends on exactly what it declares" |
| spec §19 | INT-009, INT-NS, INT-PROV | traced to an AC | **met** | Every §19 row names an AC |

### Scope drift

`src/engine/catalogue_lifecycle.py` has one commit, `730986c` (SPEC-004, Phase 1). **None.**

### Shipped but never requested

Nothing.

---

## Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F4-catalogue-lifecycle/intent.md`.*

**PROBLEM («نظّف كتالوجي من الأصناف الميتة» — 7,674 products make a stock count frightening):
is the owner measurably less stuck?** **No.** The intent's whole answer is a catalogue that
cleans itself daily "without a button": dead products withdrawn, returned on a sale, and the
count shrinking to his real store so a stock count becomes a day, not a week. The engine does
the classification; nothing is withdrawn for him to see, and no list or CSV reaches him. The
reason is his own decision, D-14, taken because the evidence cannot yet tell "sold nothing"
from "absent from the reports" (GAP-009).

**SUCCESS — count it.** The intent's table against the artefact:

| | Intent | Artefact |
|---|---:|---:|
| sold at least one | 1,535 | 1,257 living |
| zero sales, zero stock → withdrawn | 3,918 | 3,903 withdrawable |
| zero sales, stock on hand → his call | 1,658 | 1,631 idle |
| zero sales, negative stock | 232 | 483 excluded (all negative stock, sold or not) |

The dead and idle counts reproduce to within 1%. "Living" is lower because the engine excludes
every negative-stock product before classifying (C-32), sellers included, and the barcode-less
248 too. The daily benefit the intent counted, 1,535 products to count instead of 7,674, is not
countable: nothing is withdrawn from what he sees.

**USER: would the owner recognise it?** The idle list, yes: his products, most expensive per unit
first, no money figure, which is exactly §4ب. The cup question, no: the intent says to put it
to him as «هذا الرقم منطقي؟»; the screen says «كمية غير معقولة», a verdict.

**NOT NOW: anything deferred built?** No. Nothing is deleted from the POS, no reason is given for
a product going quiet.

**Would you write the same intent again?** Its analysis, yes. Its promise of automatic daily
deletion, not before GAP-009 is answered. The intent itself found that "zero sales" here is
"no row" (rule 13), and D-14 followed from that. The intent never says what the owner gets
while that question is open.

---

## Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| Entries on the daily surface today | **0.** Entries without money share three reserved places, handed out in the order `reconciliation` → `competitor_position` → `catalogue_lifecycle` → `hygiene` (`thresholds.surface`, `compose.js`); reconciliation's 355 fill all three every day until the owner settles them, and F3's 6 come next. F4's 1,632 reach it only after those 361 are settled | `compose()` over `public/data/dashboard.json`, `now` 2026-09-28 08:00Z; re-run with F1's and F2's entries removed admits F3's, not F4's |
| `generated_at` | 2026-09-28T03:10:39Z, run `ok` | `public/data/dashboard.json` |
| On its own page | Counts (living 1,257 · withdrawable 3,903 · idle 1,631 · …) and 1,632 entries, product and characterisation only | `capabilities.catalogue_lifecycle` |
| Matches the intent? | Dead and idle: yes, within 1%. Withdrawal applied for the owner: **no**, by D-14 | Pass two |
| Turned off | Withholding any of its four inputs makes it unavailable, nothing else moves | `check_v1_signals.py`, 2026-09-28 |
| Rule 8 | **yes**: no entry carries a `value`; unit cost is per unit and never multiplied by stock | `.entries[].value` |
| Rule 13 | Honoured and central: every one of the 3,903 withdrawable products has `evidence_state: no_row`, not zero. The seven monthly reports cannot separate a seasonal product from a dead one, and the artefact says so (`statement`) | `.withdrawn[].evidence_state` |

---

## What surprised me

F4's engine is the most careful in the product about what it does not know, and its most
careful sentence, the seasonal warning, is exactly the one the catalogue page drops, right
beside the "withdrawable 3,903" it qualifies.

## Not checked, and why

- AC-063b over real data: there is no 12-month evidence to extend into.
- The catalogue page on the deployed URL: it needs a sign-in; the component and the artefact were read.
- Whether the owner decided on an F4 entry: **no** (2026-09-29: the first `measurement.json` (published 2026-09-29, `generated_at 03:52Z`) records **one** decision in the whole pilot: a deferral ("Later") on one `price.inverted` entry, on 2026-09-17. Nothing acted on, nothing dismissed, no money recovered; four devices had opened the app, the last on 2026-09-24).

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| Say what the owner gets from F4 while D-14 holds: nothing, the idle list only, or the withdrawn list labelled provisional | smartshelf-pm | The intent promises automatic cleaning; D-14 forbids showing it; nothing says what stands in between |
| ~~Show the window and the seasonal statement wherever the dead count is shown~~ **Done 2026-09-28, #235** (approved by the owner; see `docs/reviews/card-wording-2026-09-28.md`) | smartshelf-engineer; screen change, owner approves | AC-067 partial |
| ~~Offer idle stock FR-070's three outcomes instead of the generic three~~ **Done 2026-09-29, #243** (approved by the owner): on the shelf, not selling · the count is wrong · we don't sell it anymore | smartshelf-architect (outcome vocabulary), then smartshelf-engineer; owner approves | AC-071b missing |
| ~~Ask the implausible quantity as a question on screen, and stop the raw `is_this_quantity_right` reaching a card~~ **Done 2026-09-28, #235** (approved by the owner; see `docs/reviews/card-wording-2026-09-28.md`) | smartshelf-engineer; owner approves the wording | AC-069 partial |
| A withdrawn list, a revival action and the CSV (FR-065, FR-067, FR-075) — once D-14 allows | smartshelf-architect, then smartshelf-engineer | AC-061 and AC-063 are engine-only |
| ~~Twelve `evidence.*` labels are English in `ar.js` and `he.js`: `attention_pct`, `cost_floor_pct`, `cost_source`, `evidence_state`, `format_note`, `margin_pct`, `policy_pct`, `premium_pct`, `question`, `reference`, `sources`, `unit_cost` (F3's record names the seven its evidence uses)~~ **Done 2026-09-28, #235** (approved by the owner; see `docs/reviews/card-wording-2026-09-28.md`) | smartshelf-engineer; the owner approves the wording | F4's evidence uses four of them |
