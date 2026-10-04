---
ID: ADR-039
Title: A shelf plan's explanation is a pinned model's answer, checked and sealed as the boost's is
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-10-04
Parent: [System Design](../system-design.md) §19
Related Specs: F12-S1 (FR-210 … FR-215, INV-096, INV-097, NFR-077)
Inputs: [docs/features/F12-planogram/specs/F12-S1-planogram.md, D-16, D-32, ADR-014, ADR-032, ADR-035, src/engine/market_boost.py, .github/workflows/collect-daily.yml]
Updated: 2026-10-04
---

# ADR-039 — A shelf plan's explanation is a pinned model's answer, checked and sealed as the boost's is

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

D-32 asks that the AI explain why each shelf is arranged as the plan says. D-16 already fixed how
an AI-written reason is made in this product: once a night, from published facts, with a paid
account, a spending ceiling, and a mechanical check that it states no figure its facts do not
carry. ADR-032 and ADR-035 built that for the market boost:
- a pinned model;
- a JSON answer checked for digits;
- two spending limits;
- each night's answers sealed as a committed snapshot that print mode reads instead of calling
  the model.

The explanation needs the same, with two differences:
- it is written after the plan, from the plan's facts, where the boost feeds the quantity;
- it is text beside a figure, never a figure.

## Decision

1. **Where it runs.** A step in the nightly run, after `shelf_plan` and before publishing. It is
   never run in the browser, and never at request time.
2. **Which model.** The one ADR-032 pins, `claude-sonnet-5`, which the owner chose on
   2026-09-26, with the same key (`ANTHROPIC_API_KEY`, read as `SMARTSHELF_ANTHROPIC_API_KEY`).
   The prompt is a versioned file, `configs/prompts/shelf_explanation.v1.md`, and it holds §23's
   findings in plain words. The model id and prompt version are recorded with every
   explanation.
3. **One client, not two.** The request, the transport, the digit pattern and the facts digest
   move out of `market_boost.py` into one module that both steps use. The check is one rule,
   applied in one place.
4. **What it is given and what it may return:** F12-S1 FR-211 and FR-212.
   - The answer is JSON: `{"he": …, "ar": …, "en": …}`, each at most the policy's length.
   - The digit check runs after removing the product names it was given.
   - A failing answer is withheld whole.
5. **Sealed as ADR-035 seals the boost.**
   - The snapshot lives under `data/external/snapshots/<plan date>/shelf_explanations/`. It
     holds `explanations.json`, and a `_manifest.json` with the requests made, the ceiling and
     whether the step completed.
   - Per fixture, `explanations.json` holds:
     `{fixture, plan_entry_id, model, prompt_version, requested_at, inputs_digest, text | withheld_because, reused_from?}`.
   - It is committed in the nightly's existing step for the boost's picks, which grows to take
     both. Merge-never-replace: a same-day re-run asks only for fixtures with nothing sealed.
   - **Print mode never calls the model.** It reads the night's snapshot. With none, the
     explanations are withheld input: every plan is unchanged, and each fixture says it has no
     explanation.
   - **Reuse.** Before asking, the step looks for the same facts digest in earlier nights'
     snapshots. If it finds one, it copies that explanation into tonight's snapshot with
     `reused_from`, and makes no request. Each night's snapshot stays complete on its own, and
     an unchanged plan is paid for once.
6. **Spending, ADR-032's two limits.**
   - The account's monthly spend limit is the one the owner sets in the provider's console. It
     is shared with the boost.
   - A per-run ceiling in policy: `shelf.explanation_request_ceiling`, proposed at 40.
   - A time budget in policy: `shelf.explanation_time_budget_s`, proposed at 300 (F12-S1
     NFR-077). The nightly ran 29.5 minutes of its 60 on 2026-10-04 (run 37174519014). At
     ADR-032's 30-second timeout, 40 slow requests would take 20 minutes, so the budget is what
     keeps the step from threatening the timeout.

   **What it would cost**, at the prices ADR-032 read from Anthropic's pricing page on
   2026-09-26 ($2 in, $10 out, per million tokens). The estimate assumes about 1,500 tokens in
   (the prompt and one fixture's facts) and 900 out (three languages) per request. Those token
   counts are assumptions, to be replaced by the first nights' measured usage:

   | | Requests a night | A night | A month (30 nights) |
   |---|---|---|---|
   | A 15-fixture store, every plan new each night | 15 | about $0.18 | about $5.40 |
   | At the ceiling | 40 | about $0.48 | about $14.40 |

   Reuse brings both down: a plan whose facts did not change costs nothing. Nothing is spent
   until a store's copy has a layout, daily sales and a key.
7. **The explanation is never read back.** No engine step, figure or probe reads its text
   (F12-S1 INV-096). It is published, and shown beside the plan.

## Rejected options

### Sentences built from templates
They would be deterministic, cheap and need no key: the plan's reasons are already codes. But the
owner asked for the AI's explanation (D-32). Templates stay possible as a fallback, if a night
without a key should still say something. That would be a decision of its own.

### Writing the explanation when he opens the page
D-16 forbids it: it could not be checked before he reads it, and every opening would spend.

### One explanation per product
It would cost a request for every placed product, and it answers the wrong question. He asked
why the shelf is arranged this way, and the answer is about the shelf.

### Letting the model choose or adjust the arrangement
The plan's rules and their research basis are what F12-S1 approved. A model that moved products
could not be reproduced from committed inputs and would not be checked. The model explains the
plan; it never makes it.

## Consequences

**We accept:**
- one more snapshot directory, and a bigger commit step in the nightly;
- the boost's client code moves into a shared module;
- an explanation can still be unfaithful in words, which is F12-S1 ASM-083's residual.

**We gain:** the explanation he asked for, under the rules he already set for AI-written reasons,
reproducible from committed inputs, and paid for once per distinct plan.

**We will know it was wrong if:** answers are withheld often, which the published counts show,
or he reports an explanation that does not match its plan. Either is a prompt change, and so a
new prompt version.

## Reversibility

Easy. The explanation is text beside the plan, and removing it changes no figure (INV-096). The
sealed snapshots stay as history.

## Binds

| F# | How this constrains it |
|---|---|
| F12 | `shelf_explanation` (F12-S1 FR-210 … FR-215) |
| F8 | The boost's model client moves to the shared module, with no change in behaviour (ADR-032) |
| F14 | When F14 is specified, its sentence (D-16) can use the same client, check and sealing |
