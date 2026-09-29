---
ID: F8-VALIDATION
Title: F8 — Order Quantity · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F8-S1](../features/F8-order-quantity/specs/F8-S1-order-quantity.md)
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, docs/features/F8-order-quantity/intent.md, docs/implementation/phase-5-v2-order-quantity.md, docs/reviews/F8-screens-mockups.md, public/data/dashboard.json (2026-09-28), src/engine/order_*.py, src/engine/market_*.py, src/market/running_out.py, src/engine/owner_questions.py, src/pages/ReorderPage.jsx, src/pages/ApprovedOrdersPage.jsx, src/questions/QuestionPanel.jsx, tests/engine/, src/**/__tests__/, scripts/check_order_signals.py, GitHub deployment records (Production)]
Updated: 2026-09-28
---

# Validation F8 — Order Quantity

- **Deployed URL:** `https://hackathon2026-fadi19.vercel.app` (serves the sign-in page; ADR-029).
- **Commit in production:** `2a716ec`. GitHub deployment `6708764605`, `success`, 2026-09-28 11:29Z.
- **Artefact read:** `public/data/dashboard.json` at `2a716ec`, `generated_at 2026-09-28T03:10:39Z`, run `ok`.
- **Fixture world:** `tests/fixtures/order_signals/build.py`, driven by `npm run check:order-signals` on 2026-09-28.
- **Context:** the pilot with the YomYom store ended on 2026-09-27 (D-23). F8 was built on 2026-09-26/27 (Phase 5, #207–#225) and has never had the input it needs.

## Verdict

**Conformance is met on fixtures for every criterion, and on real data for the ones real data
can exercise: F8 publishes nothing it cannot support.** With no daily report ever received,
`order_quantity` is `unavailable (no_daily_sales)`, and the Reorder page says so in the owner's
words; the boost is `unavailable (no_boost_key)`; the one live part, the market's running-out
signal, finds 79 products today and has nowhere to show them. **Fidelity cannot be judged on use:
F8 answered "what do I order, and how much?" for no product, on no day, and after D-23 it will
not until another store sends daily reports.**

---

## Pass one — conformance

Every AC below is tested in the files named, and the input-withholding ones are also run by
`check_order_signals.py` over the fixture world (all OK on 2026-09-28: 2 suggestions, 1 boosted,
1 disagreement; each input withheld moves exactly what it should).

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §15 | AC-136 | monthly reports only → no quantity, Reorder names the missing input | **met on real data** | `order_quantity: unavailable, no_daily_sales`; Reorder renders «بانتظار تقارير المبيعات اليومية…» (screenshotted from the build on 2026-09-27, #225); `ReorderPage.test.jsx`, "names no_daily_sales as the capability publishes it" |
| spec §15 | AC-137 | no quantity from a report longer than a day, nor a month divided | **met** | `test_order_evidence.py`, `test_sales_daily_importer.py`; the probe: withholding the report days → unavailable, "monthly unused" |
| spec §15 | AC-138 | a missing day is left out, never zero; 21 report days, one a week, ending within 7 days | **met** | `test_order_evidence.py`, `test_inputs.py` |
| spec §15 | AC-139 | not sold in each of four weeks → no quantity, not zero | **met** | `test_order_evidence.py`, `test_order_quantity.py`, `ReorderPage.test.jsx` ("2 don't sell every week, so no quantity") |
| spec §15 | AC-140 | daily mean, expected sales and rounding recompute from the published facts | **met** | `test_order_arithmetic.py`, `test_order_evidence.py` |
| spec §15 | AC-141 | an accepted pick applied once; a store below the floor never adjusts | **met** | `test_order_arithmetic.py`, `test_publish.py`; the market is the D-18 stores (`market_store_ids`, `test_running_out.py`) |
| spec §15 | AC-142 | market withheld → suggestions unadjusted, each saying why, no disagreement | **met** | Probe: "withholding the market → suggestions unadjusted, no disagreement"; `test_order_quantity.py` |
| spec §15 | AC-143 | an unusable count is never used, and the gross suggestion says why | **met** | `test_order_arithmetic.py`, `test_order_quantity.py`, `ReorderPage.test.jsx` ("why the count was not used") |
| spec §15 | AC-144 | stock now = count + deliveries − sales; net never below zero | **met** | `test_order_arithmetic.py`; probe: "withholding the deliveries → no net suggestion" |
| spec §15 | AC-145 | shelf life caps at whole days; under a day, or rounding to zero, gives none | **met** | `test_order_arithmetic.py`, `test_store_facts.py` |
| spec §15 | AC-146 | nothing defaulted; a missing fact means no quantity, named on Reorder | **met** | `configs/store_facts.yaml` holds `departments: {}`, and no code defaults one (`test_store_facts.py`); probe: "withholding the store facts → no quantity" |
| spec §15 | AC-147 | a department with no row in the evidence → no quantity, and Reorder says so | **met** | `test_order_quantity.py`, `ReorderPage.jsx` (`not_itemised`) |
| spec §15 | AC-148 | no ₪ on a suggestion, an approved line or the export | **met** | `publish.py` refuses a money-named field (`test_publish.py`); `ApprovedOrdersPage.test.jsx`, "shows no shekel figure, no price and no total"; `ReorderPage.test.jsx` |
| spec §15 | AC-149 | every suggestion publishes FR-154's facts, each recomputable | **met** | `test_order_quantity.py`, `test_order_arithmetic.py` |
| spec §15 | AC-150 | disagreements count toward three on screen, after every ₪ question | **met** | `test_owner_questions.py`, `QuestionPanel.test.jsx` ("counts toward the same limit of three") |
| spec §15 | AC-151 | states only what was observed; once per product; answered → never again, no quantity change | **met** | `test_owner_questions.py` ("answered it is retired for good"); probe: "an answered disagreement → not raised again"; `QuestionPanel.test.jsx` |
| spec §15 | AC-152 | his own quantity listed on Approved orders, the suggested one kept | **met** | `ReorderPage.test.jsx`, `ApprovedOrdersPage.test.jsx`, `ownerState.test.js` |
| spec §15 | AC-153 | export: product, barcode, quantity, order day; nothing written to the POS | **met** | `ApprovedOrdersPage.test.jsx`, "has exactly the columns ADR-034 names"; nothing in the repository writes to the POS |
| spec §15 | AC-154 | one entry id per department and order day, every night | **met** | `test_order_quantity.py`, `ReorderPage.test.jsx` ("an approval holds the next night") |
| spec §15 | AC-155 | a department the reports do not itemise → the FR-158 question, saying there is no row | **met** | `test_owner_questions.py` ("no window raises none except where no evidence itemises the department"), `QuestionPanel.test.jsx` |
| spec §15 | AC-156 | no on-screen question about schedules or shelf life | **met** | Store facts are a committed file the team records (ADR-033); `owner_questions` raises only `cost_price` and `market_disagreement` |
| spec §15 | AC-157 | a stock now below zero is never used; gross, saying the evidence is inconsistent | **met** | `test_order_arithmetic.py` (`stock_inconsistent`) |
| spec §15 | AC-158 | no evidence window → no disagreement, except the no-row department | **met** | `test_owner_questions.py` |
| spec §15 | AC-159 | expected to sell under one unit in its cycle → no quantity | **met** | `test_order_arithmetic.py` |
| spec §15 | AC-160 | every boost with its pick, reason and model, labelled the model's estimate; the quantity replays | **met** | `test_market_boost.py`, `ReorderPage.test.jsx` ("the model's estimate", the reason in «») |
| spec §15 | AC-161 | a pick outside 0–25% gives no boost, not a clipped one, and says so; nothing else taken from the model | **met** | `test_market_boost.py`, `test_publish.py` (an applied boost outside 0…max is refused) |
| spec §7 | INV-069 … INV-079 | | **met** | INV-069 as AC-148; INV-070 as AC-137; INV-071 as AC-146; INV-072 as AC-138, AC-147; INV-073 as AC-143, AC-157; INV-074 as AC-141, AC-161; INV-075 as AC-151, AC-158; INV-076 as AC-139, AC-159; INV-077 as AC-153; INV-078 as AC-154; INV-079 as AC-161 |
| boundary probe | rule 12, F8-S1 §20 | F8's inputs each move exactly what they should | **met on fixtures; warns on real data** | `check_order_signals.py` all OK; it warns rather than blocks until `order_quantity` is first available on real data, which after D-23 will not happen with this store |
| spec §19 | INT-004 | traced to an AC | **met** | Every §19 row names an AC |

### Scope drift

Phase 5 ran against the plan's `Files:` lists (#207 … #223). Changes outside them:

| Change | In a plan task's `Files:` list? | Note |
|---|---|---|
| #221: `checkpoint2.test.jsx` exempts `NOT_YET_SHOWN` | no | Fixed `main` after the first nightly published F8's ids; recorded in the plan's corrections |
| #224: `figures.py` treats F8's capabilities as registering no figure | no | Found while validating 5.14; System Design §11.6 |
| #225: Reorder's waiting reason drawn as the approved heading | no | Brings the screen to the approved mockup |

### Shipped but never requested

Nothing. The screens are exactly the approved mockups (compared from the build on 2026-09-27;
only Approved orders' row order within a department differs, alphabetical, and was reported).

---

## Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F8-order-quantity/intent.md`.*

**PROBLEM («ماذا أطلب اليوم وبأي كمية؟» — the largest value in the product): is the owner
measurably less stuck?** No. No quantity has ever been suggested for any product. The reason is
the input: the seven reports are monthly (rule 13), the daily ones were asked for (owner
conversation #7) and never came, and the pilot has ended (D-23).

**SUCCESS — count it.** The intent names no count. What can be counted: suggestions published on
real data, **0**; days with a daily report, **0**; departments with stated facts, **0**. On the
fixture world, 2 suggestions, 1 boosted, 1 disagreement, each recomputable.

**USER: would the owner recognise it?** The screens were approved by the repository owner as
mockups on 2026-09-27 and built to them. The store owner never saw them.

**NOT NOW / direction:** the intent gave an ordering (market first, then his movement, then shelf
life) and left the rule open. D-19 reversed the first two (his sales set the quantity, the market
only adjusts it), which is his decision, not drift. The intent's second half, the sentence for a
product strong in the market and weak here, is built as the disagreement question, in the
intent's own three answers plus one.

**Would you write the same intent again?** Yes, with its input named as a condition. Everything
F8 needs from the store (daily sales and deliveries, each department's order days and shelf life)
was known when the intent was approved, and none of it was in hand.

---

## Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| Suggestions on real data | **0**: `unavailable (no_daily_sales)` | `capabilities.order_quantity` |
| On the daily surface | none by design: F8 never reaches Today (`NOT_ON_TODAY`, FR-160) | `src/surface/compose.js` |
| The market signal | 79 products running out across 3 stores on 2026-09-28; shown only as facts on Reorder cards, and there are no cards | `capabilities.market_running_out` |
| The boost | `unavailable (no_boost_key)`: no key, and no candidates without daily reports | `capabilities.market_boost` |
| Disagreement questions | 0 raised on real data (`open_disagreement: 0`) | `capabilities.owner_questions.counts` |
| `generated_at` | 2026-09-28T03:10:39Z, run `ok` | `public/data/dashboard.json` |
| Turned off | On fixtures, each input withheld moves exactly its dependants (the probe) | `check_order_signals.py` |
| Rule 8 | **yes**: no ₪ anywhere in F8's output; `publish.py` refuses one | `test_publish.py` |
| Rule 13 | Central and honoured: no quantity from the monthly reports; the monthly data is "unused" by the probe's own check | `check_order_signals.py` |

---

## What surprised me

The most carefully specified feature in the product, three review rounds and 26 acceptance
criteria, is the only one whose input never existed for a single day. Nothing in it is wrong;
there was never anything for it to be right about.

## Not checked, and why

- Any behaviour on real daily reports: there are none.
- The live model call: there is no `ANTHROPIC_API_KEY`, and no candidate.
- The screens on the deployed URL: they need a sign-in. The build was compared with the approved
  mockups on 2026-09-27 instead.

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| For the next store, make the daily reports and department facts a precondition before anyone builds on them, and ask ASM-065 with them | smartshelf-pm | F8 waited for inputs that were never in hand |
| Decide whether the market's running-out signal (79 products today) should be visible anywhere while F8 is dormant, or stay a Reorder fact only | smartshelf-pm; a screen change needs the owner's approval | A live signal with no screen |
| ~~`check_order_signals.py` warns forever with this store (it blocks only after `order_quantity` is first available on real data)~~ **Done 2026-09-29 (`05f3698`)**: it blocks once any of `order_quantity`, `market_boost` or `assortment_gap` is available in the committed artefact. F9's assortment gap has been available since the 2026-09-29 nightly, so it blocks now. The market snapshot is committed before the probes run, so a block holds back only the owner's artefact | smartshelf-architect | The warning will never turn into a block |
