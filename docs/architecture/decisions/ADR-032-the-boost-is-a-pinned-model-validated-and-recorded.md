---
ID: ADR-032
Title: The boost is picked by a pinned Claude model in the nightly run, checked mechanically, and recorded in the artefact
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-25
Parent: [System Design](../system-design.md) §19
Related Specs: F8-S1 (FR-147, FR-154, FR-164, INV-074, INV-079, NFR-066, NFR-067, C-71, C-72, AC-160, AC-161)
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, D-16, D-21, ADR-001, ADR-002, ADR-005, ADR-007, ADR-014, .github/workflows/collect-daily.yml]
Updated: 2026-09-25
---

# ADR-032 — The boost is picked by a pinned Claude model in the nightly run, checked mechanically, and recorded in the artefact

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

D-21 (2026-09-25) has a language model pick each product's boost once a night, when the
market runs out of it (ADR-031). The pick is accepted only from 0% to 25%, needs a paid
account and a monthly spending cap, and is recorded with its reason so the quantity replays
from it.

F8-S1 sets further rules:
- the model sees only published facts (FR-164);
- it moves one number only (INV-079);
- a pick outside the range gives no boost, not a clipped one (FR-147).

Three existing rules bind where the model can run:
- ADR-007: there is no runtime server; figures are made in the nightly CI run.
- ADR-001: the browser computes no business rule.
- ADR-002: reproduction is the engine in print mode, and print mode cannot depend on a
  model answering the same way twice.

## Decision

1. **Where it runs.** A step inside the nightly engine run, after the running-out signal
   and before publishing. Never in the browser, never at request time.
2. **Which model.** Anthropic's Claude, through its API, pinned to one model id:
   `claude-sonnet-5`.
   - The id and the prompt's version are published with every pick.
   - Changing either is a commit, never a silent drift.
   - The key is a GitHub Actions secret, `ANTHROPIC_API_KEY`, set by the repository owner,
     as he set `VERCEL_DEPLOY_HOOK_URL`. Without it the run warns, and no product is boosted.
3. **What it is given.** One request per product that is running out. It contains only facts
   F8 publishes for that product:
   - the window's weekly units and the daily mean;
   - the market facts: how many stores are out, and for how many days;
   - the department, the product name and the shelf life.

   Nothing else goes in: no competitor volume, which is not observed, and no ₪ figure. The
   prompt is a versioned file in the repository, and temperature is 0.
4. **What it may return.** JSON, `{"boost_pct": <number>, "reason": <text ≤ 160 chars>}`.
   - The run checks it mechanically. It must parse, `boost_pct` must be a number, and it must
     lie from 0 to the policy maximum: 25, D-21's limit, read from `configs/policy.yaml`.
   - Anything else is **rejected**. It is recorded as rejected, with what came back, and the
     product gets no boost.
   - Only `boost_pct` is ever used as a figure. The reason is shown as the model's words
     (INV-079).
5. **The record is the artefact.** Each pick is published beside its suggestion:
   `{model, prompt_version, requested_at, inputs_digest, boost_pct, reason, accepted}`.
   - The committed artefact of the night is the record.
   - Print-mode reproduction (ADR-002) reads the picks from the artefact of the run it
     reproduces. It never calls the model (F8-S1 NFR-067, C-71).
6. **Spending has two limits.**
   - The account's own monthly spend limit, set by the repository owner in the provider's
     console. This is D-21's cap.
   - A per-run ceiling in policy of 200 requests a night, provisional. Products beyond it are
     not sent, and get no boost ("the night's request ceiling was reached").
   - The run publishes the requests made, and warns when the ceiling was hit.
7. **The boost is a capability of its own (ADR-014).** It needs the running-out signal and
   the key. When it is unavailable (no key, the API failing or timing out, the ceiling hit),
   suggestions publish without a boost and say why (F8-S1 SCN-151). That leaves the run
   `ok`. The model is an optional input, and its absence takes nothing else away.

## Rejected options

### Call the model from the browser when the page opens
It would add a runtime dependency that ADR-007 excludes, and expose the key to every
visitor. Two visitors could also see different boosts for the same suggestion, with no
record of either.

### An unpinned "latest" model alias
Picks would change when the provider moves the alias, with nothing in the record to say
why. Pinning makes a model change a reviewable commit.

### Let the model compute the whole quantity
This is the failure F14's intent records: a model turned "order 20" into "25". F8-S1 INV-079
allows the model to move one number, inside a mechanical range.

### Clip an out-of-range pick to 25%
D-21 is explicit: a pick outside the range gives no boost. Clipping would turn a malformed
answer into the maximum boost.

### Run an open model on the CI runner
There is no GPU on the runner. It would add a second stack to maintain, and nothing is
gained against D-21's requirement of a paid account.

## Consequences

**We accept:**
- A paid account and a key, both the repository owner's console acts.
- A cost every night.
- A figure that is not deterministic. It is recorded and replayed, never recomputed.
- Nothing yet checks whether a pick is *right* (F8-S1 ASM-072).

**We gain:**
- Per-product boosts, as he decided.
- Every pick is auditable, with its model, prompt and inputs, and none can escape the 0–25%
  range.

**We will know it was wrong if:**
- The picks cluster at one value, so there is no real per-product judgement.
- More than a small share of picks are rejected.
- The month's spend reaches the cap before the month ends.

## Reversibility

Easy. Removing the key switches the step off, and every suggestion then publishes without a
boost. Past picks stay in past artefacts.

## Binds

| F# | How this constrains it |
|---|---|
| F8 | FR-147, FR-154, FR-164 and INV-079 are implemented here |
| F14 | D-16's reason sentence may cite a pick, because the pick is a published fact (F8-S1 C-72). This ADR does not govern F14's own model call |
