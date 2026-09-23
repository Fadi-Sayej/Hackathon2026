---
ID: ADR-027
Title: A question whose money is unknown carries no figure, and ranks after every question that has one
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-23
Parent: [System Design](../system-design.md) §19
Related Specs: F5-S1, F6-S1
Inputs: [docs/features/F5-owner-knowledge-capture/specs/F5-S1-owner-knowledge-capture.md, ADR-001, ADR-012, ADR-019, src/engine/owner_questions.py, src/questions/QuestionPanel.jsx, public/data/dashboard.json (2026-09-23), CLAUDE.md rules 8, 11, #130, #156]
Updated: 2026-09-23
---

# ADR-027 — A question whose money is unknown carries no figure, and ranks after every question that has one

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19 ·
proposed by `smartshelf-architect` for #130. A role may not approve its own output
(HANDOVER rule 2), so this waits for the repository owner.

## Context

`owner_questions` asks one kind of question: the purchase cost of a product that sells and
has none. FR-085 orders the questions by expected value, *"the money at stake multiplied by
the question yield"*, and D-8 caps the panel at three, so the order decides which questions
the owner ever sees. The money is `units_total × shelf_price`, and
`src/engine/owner_questions.py` reads a missing shelf price as zero:

```python
money = units * (p["shelf_price"] or 0.0)
```

That turns an unknown into a fact twice:

1. **It is published.** `why.money_at_stake: 0.0` says nothing is at stake for a product
   whose stake is unknown. The panel renders it as *"Affects ₪0 across 2026-01..2026-07"*.
   D-3, FR-092 and CLAUDE.md rule 8 say a figure that cannot be stated is not stated.
2. **It decides the order.** The question sorts below every question with a real figure,
   exactly like one genuinely worth nothing. Under a cap of three, sorting last means not
   shown.

FR-085 defines expected value and never says what happens when the money is unknown. That
gap is the decision.

## Measured before deciding

Read from the engine's own inputs for the 2026-09-23 run (`load_inputs`, the same path
`run_engine` uses):

| | |
|---|---:|
| products | 7,523 |
| with no shelf price | 223 |
| …and no purchase cost either | 107 |
| …and sold in the seven reports, i.e. a question candidate | **0** |
| open questions today | 11, every one with a shelf price |

**Latent, not live.** It is one POS export away: a single product that loses its shelf
price, has no cost and sells makes it live.

**The reports cannot stand in for the shelf price.** The obvious fallback is the revenue the
sales reports recorded, since each report line carries a selling price. Measured: exactly
one product without a shelf price sold at all, and its report lines carry no selling price
either. #156 explains why. The reports are sales per barcode joined to the same POS item
master, so the selling price on a report line *is* the master's shelf price. When the
master has none, the report has none.

## Decision

**When a question's money cannot be computed, it carries no figure. It is ordered after
every question that has one, among its peers by units sold, and it says what is missing.**

1. **No figure.** With `shelf_price` absent, the item publishes
   `why.money_at_stake: null` and `expected_value: null`, never `0`, and names the missing
   fact in `why.money_missing: "shelf_price"`. `why.units_sold`, `why.money_basis` and
   `why.window_id` are published as today. `money_basis` states the rule that would have
   produced the figure, which is what a reader needs to understand why there is none.
2. **The order.** Questions with a figure come first, by expected value, highest first.
   That is FR-085 unchanged, over exactly the questions it can be computed for. Questions
   without a figure follow, by `units_sold` highest first, then by barcode. Units sold is
   the only published evidence of weight such a question has. It orders the unknowns
   among themselves and is never converted into money.
3. **The cap does not move.** At most three are presented (D-8, INV-040), so a question
   with no figure is shown only when fewer than three questions have one. That is where it
   stands today, but reached honestly rather than through a ₪0.
4. **The panel states no number and says why.** An item with `money_at_stake: null` renders
   no ₪ figure and no `₪` sign. It names the missing shelf price and shows the units sold
   over the window instead. The words are the repository owner's to approve, as every
   change to what he reads is.
5. **Nothing else changes.** `question_id` is `sha256(fact | barcode)` and has no money
   in it, so no id moves, no answer or deferral is orphaned, and the eleven questions
   published today keep their figures and their order.

## Rejected options

### Keep `or 0.0`, and document that zero means unknown
This publishes ₪0 as the money at stake of a product whose stake is unknown. D-3 exists to
forbid that sentence, and the panel would print it without the footnote. A convention that
lives only in documentation is read by nobody who looks at the screen.

### Fall back to the revenue in the sales reports
Measured above, it rescues nothing: the report's selling price comes from the same master,
and the one product that sold without a shelf price has no report price either. It would
also put two money bases into one ranking to cover a case that, on this data, it cannot
cover.

### Rank the questions with no figure first
This gives one of three places to a question on no evidence of value, displacing one whose
value is measured. That overstates the unknown by exactly as much as `or 0.0` understates
it.

### Suppress the question until the shelf price is known
The answer, a purchase cost, would still change outputs: margin, the cost floor and the
questions' own suppression. Hiding the question is silence about a real gap, and it would
count under a suppression bucket whose name says something else.

### Ask the owner for the shelf price first
This is the honest long-term answer, and it is the one to take if the signal below fires.
It is not an architecture decision, though. F5-S1's V1 asks exactly one kind of fact, the
purchase cost (`FACT = "cost_price"`). A second question kind needs its own FR-081 and
FR-093 treatment (what the shelf price feeds, and who stops reporting it missing), which is
a spec round. With zero affected products today, the cost of that round buys nothing yet.

### Put unknowns on the money scale with an estimated price
For example, units × the department's median shelf price. That is an invented figure
presented as money at stake: rule 8's "a plausible number where there is no honest one".

## Consequences

**We accept:** a question without a shelf price is shown only when fewer than three
questions have a figure, as today. The item's `money_at_stake` and `expected_value` become
nullable, which every reader of `owner_questions.items` must handle. Today that is
`QuestionPanel.jsx` alone, which #158 puts back at the top of Today after a week in which the
app rendered it nowhere.

**We gain:** no ₪0 on the owner's screen for an unknown; a stated reason on the item; a
deterministic order among the unknowns; and FR-085 applied exactly where it can be computed.

**We will know it was wrong if:** a question with `money_at_stake: null` stays open while
three questions with figures are presented, run after run, for a product that keeps
selling. Then the owner is being denied a question he could answer, and "Ask the owner for
the shelf price first" becomes worth its spec round.

## Reversibility

Easy. One capability, one sort key, one nullable field and one sentence on the panel. No
entry id, question id or recorded answer depends on the money, so undoing it moves nothing
the owner has done.

## Implementation — for `smartshelf-engineer`, once accepted

**Files:**

- Modify: `src/engine/owner_questions.py`
- Test: `tests/engine/test_owner_questions.py`
- Modify: `src/questions/QuestionPanel.jsx`
- Test: `src/questions/__tests__/QuestionPanel.test.jsx`
- Modify: `src/lib/i18n/dictionaries/ar.js`, `he.js`, `en.js`: one sentence for an item with
  no figure. The wording goes to the repository owner before merge.

**Acceptance, each a failing test first:**

- A candidate with no shelf price publishes `money_at_stake: null`, `expected_value: null`
  and `money_missing: "shelf_price"`, not `0.0`.
- Ordering: every question with a figure precedes every question without one. Among those
  with a figure, by expected value; among those without, by units sold, then barcode.
- Today's eleven questions keep their figures and their order. Assert it over the
  committed inputs, not a fixture.
- One test runs `run_engine` and reads the published artefact. The field has to survive
  the publisher, which is rule 12's boundary.
- The panel renders no `₪` and no number in the money position for such an item, in all
  three languages.

**No schema change.** `capabilities` carries no schema today (ADR-025's finding), so the
nullability is stated here and in §21 rather than enforced by the publisher. When the
capability schema is written, this field is declared nullable in it.

## Binds

| F# | How this constrains it |
|---|---|
| F5 | FR-085's expected value is computed only where the money is known; a question without it carries no figure and ranks after every question that has one |
| F6 | The panel on the daily surface renders no ₪ figure for such a question and says which fact is missing |
