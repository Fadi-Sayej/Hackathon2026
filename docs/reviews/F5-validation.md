---
ID: F5-VALIDATION
Title: F5 — Owner Knowledge Capture · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F5-S1](../features/F5-owner-knowledge-capture/specs/F5-S1-owner-knowledge-capture.md)
Inputs: [docs/features/F5-owner-knowledge-capture/specs/F5-S1-owner-knowledge-capture.md, docs/features/F5-owner-knowledge-capture/intent.md, docs/operations/deployment.md, public/data/dashboard.json (2026-09-28), src/engine/owner_questions.py, src/engine/inputs.py, src/questions/QuestionPanel.jsx, tests/engine/test_owner_questions.py, tests/engine/test_inputs.py, tests/owner_state/, src/questions/__tests__/QuestionPanel.test.jsx, scripts/check_v1_signals.py, GitHub deployment records (Production)]
Updated: 2026-09-28
---

# Validation F5 — Owner Knowledge Capture

- **Deployed URL:** `https://hackathon2026-fadi19.vercel.app` (serves the sign-in page; ADR-029).
- **Commit in production:** `2a716ec`. GitHub deployment `6708764605`, `success`, 2026-09-28 11:29Z.
- **Artefact read:** `public/data/dashboard.json` at `2a716ec`, `generated_at 2026-09-28T03:10:39Z`, run `ok`. The nightly pulled owner state from Firestore (`vintages.owner_state.status: available`).
- **Context:** the pilot with the YomYom store ended on 2026-09-27 (D-23).

## Verdict

**Conformance passes on every criterion, and fidelity is the closest of any feature so far**: the
intent predicted 12 questions led by two named products; the artefact asks 11, led by exactly
those two with exactly the unit counts the intent quoted. **Usefulness is the gap, and it is
not the feature's:** in the whole pilot, **no answer was ever recorded**
(`suppressed_answered: 0` on a live pull), so nothing F5 exists to change was ever changed.

---

## Pass one — conformance

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §15 | AC-080 | no more than three at once, whatever the volume | **met** | `limit: 3` with 11 open; `test_ac_080_the_limit_is_published_and_never_above_three`; the panel: "shows no more than the published limit", "honours a different limit rather than a hard-coded three" |
| spec §15 | AC-081 | none about a withdrawn or idle product | **met** | `suppressed.withdrawn` and `.idle` are counted (0 today, because the published population is `whole`, ADR-020); `test_ac_081_withdrawn_and_idle_are_suppressed` |
| spec §15 | AC-082 | suppressed and remaining counts reportable | **met** | `counts`: open 11 · suppressed no-effect 7,264 · answered 0 · withdrawn 0 · idle 0; `test_ac_082_suppressed_counts_are_reportable` |
| spec §15 | AC-083 | a high-value narrow question before a broad one | **met** | Ordered by `expected_value`: ₪7,440, ₪495.60, ₪376, …; `test_ac_083_ordering_is_by_expected_value`, and ADR-027's `test_adr_027_questions_with_a_figure_come_first_then_the_rest_by_units_sold` |
| spec §15 | AC-084 | an answer changes dependent outputs at the next run | **met in tests; never observed** | The owner's cost replaces the POS cost (`_shape_products`, `cost_source: owner`; `test_products_are_shaped_and_owner_cost_wins`), reaches the engine from Firestore (`test_a_browser_cost_answer_reaches_answered_cost`) and changes the digest (`test_a_changed_owner_answer_does_change_the_digest`). No answer exists in production to watch it happen |
| spec §15 | AC-085 | an answer is never overwritten by inference | **met** | The owner's cost wins over the POS column whenever present (`_shape_products`); nothing writes answers but the browser (ADR-003) |
| spec §15 | AC-086 | a deferral records no content and leaves outputs as they were | **met** | `test_ac_086_a_deferral_leaves_the_question_open_but_unpresented`; `test_answered_cost_ignores_deferrals` |
| spec §15 | AC-087 | an answered question is not asked again, absent revision or change | **met** | `test_ac_087_an_answered_question_is_not_re_presented`; the panel reopens a saved value only when he asks ("reopens the field with his value when he wants to change it") |
| spec §15 | AC-088 | no question whose answer changes nothing | **met** | 7,264 suppressed as `no_effect`; `test_ac_088_only_questions_that_change_an_output` |
| spec §15 | AC-089 | no backlog total or progress indicator beside the questions | **met** | `QuestionPanel.jsx` renders the items and nothing from `counts` (no `open`, no "n of m") |
| spec §15 | AC-090 | an answer survives the product being withdrawn | **met by construction** | Answers live in owner state keyed by barcode (`answers[barcode][fact]`), which classification never touches. No test withdraws an answered product |
| spec §7 | INV-040 … INV-045 | | **met** | INV-040 as AC-080; INV-041 as AC-081; INV-042 as AC-085; INV-043 as AC-086; INV-044 as AC-088. INV-045: every question asks for a cost from his own invoices, or (F8) why something does not sell here; none needs another system |
| boundary probe | rule 12 | depends on exactly what it declares | **met** | `check_v1_signals.py`, 2026-09-28: withholding `products` makes `owner_questions` unavailable, and nothing else it does not declare moves it. The panel then names the reason ("names the reason and does not claim there is nothing to ask") |
| spec §19 | INT-010, INT-NS, protected | traced to an AC | **met** | Every §19 row names an AC |

### Scope drift

| Change | In a plan task's `Files:` list? | In spec §3 scope? | Note |
|---|---|---|---|
| `398a92f` #162: a question whose money is unknown carries no figure | **ADR-027** | yes (FR-085) | — |
| `0e10beb` #168: say a cost answer was saved | issue #168, not a plan task | yes (FR-090) | Traced to an issue, not a spec id (handover rule 6) |
| `2871315`: the team sees the panel read-only | **ADR-029 §5** | not in F5-S1's scope; D-22 | — |
| `cc7a672`, `412c473`: the market disagreement joins the panel; answers stored per fact | **Phase 5 Tasks 5.9, 5.14** | F8-S1 FR-158 (it shares F5's limit, D-8) | Approved by the owner 2026-09-27 |

### Shipped but never requested

Nothing beyond the drift above.

---

## Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F5-owner-knowledge-capture/intent.md`.*

**PROBLEM («أكمل بياناتي الناقصة — بأقل إزعاج»): is the owner measurably less stuck?** The
"least bother" half, yes: 1,270 missing costs became 11 questions, three at a time, each with
the money it unlocks. The "complete my data" half, no: none was ever answered.

**SUCCESS — count it.** The intent: "12 questions, not 1,270", the largest `שטיפה פסח` (186
units) and `תפוצ'יפס ברביקיו` (84 units). The artefact: **11** open, the first
`שטיפה פסח חיצונית / פנימית` with `units_sold: 186`, the second `תפוצ'יפס בטעם ברביקיו ודבש 50
גרם` with `units_sold: 84`. One fewer, and the same two at the top.

**USER: would the owner recognise it?** Yes: his products by name, the money at stake with the
window it rests on (`window_revenue_at_shelf_price`, 2026-01..2026-07), and a field for his
price.

**NOT NOW: anything deferred built?** No general data-entry screen; no question that changes
nothing (7,264 suppressed). The F8 disagreement question arrived through F8-S1, not F5.

**Would you write the same intent again?** Yes. It is the one intent whose numbers the engine
reproduced unaided. What it did not foresee is that "two minutes" of answers would never be
given; the intent assumed the owner would open the screen.

---

## Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| Questions on the daily surface today | **3** (the panel's limit), of 11 open, all cost questions | `capabilities.owner_questions.items`, `limit` |
| `generated_at` | 2026-09-28T03:10:39Z, run `ok` | `public/data/dashboard.json` |
| Matches the intent? | **yes**: 11 against 12, same two first | Pass two |
| Answers ever recorded | **0**: `suppressed_answered 0` on a live Firestore pull; 4 devices had written owner state, the last on 2026-09-24 | `counts`, `vintages.owner_state.devices` |
| Turned off | Withholding `products` makes it unavailable, and the panel says why | `check_v1_signals.py`, 2026-09-28 |
| Rule 8 | **yes**: `money_at_stake` is revenue over a stated window at shelf price, not a stock-derived figure, and ADR-027 publishes no figure where the price is unknown | `.items[].why` |
| Rule 13 | Honoured: `units_sold` and the money are totals over the seven months, labelled with the window, never a daily or weekly rate | `.items[].why.window_id` |

---

## What surprised me

The feature built with the most care for the owner's time is the one he never used: four
devices opened the app, and not one of eleven questions, each two minutes, was answered.

## Not checked, and why

- The panel on the deployed URL: it needs a sign-in; the component tests and the artefact were read.
- AC-084 on real data: it needs an answer, and there is none.
- Why no answer was given: no artefact records the conversation with the owner.

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| Record, for the next store, that F5's value depends on the owner answering, and measure it (F13 now counts decisions, not answers) | smartshelf-pm | Zero answers in the pilot; F13's measurement does not show questions at all |
| ~~A test that withdraws an answered product and keeps its answer (AC-090)~~ **Done 2026-09-28, #234 (`d36c0d4`)**: `tests/engine/test_answer_survives_withdrawal.py` | smartshelf-engineer | Met by construction only |
| #168 and the F8 question entered F5's panel through an issue and F8-S1; F5-S1 does not mention a second fact | smartshelf-architect | F5-S1 §3 describes cost questions only |
