---
ID: ADR-032
Title: The boost is picked by a pinned Claude model (Sonnet 5) in the nightly run, and checked mechanically before it is used
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-25
Parent: [System Design](../system-design.md) §19
Related Specs: F8-S1 (FR-147, FR-154, FR-164, INV-074, INV-079, NFR-066, C-72, AC-160, AC-161)
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, D-16, D-21, ADR-001, ADR-007, ADR-014, ADR-031, ADR-035, .github/workflows/collect-daily.yml]
Updated: 2026-09-26
---

# ADR-032 — The boost is picked by a pinned Claude model (Sonnet 5) in the nightly run, and checked mechanically before it is used

**Status:** Accepted (2026-09-26, by the repository owner, on PR #200). He chose the model the same day, after seeing the options (Decision 2) · **Recorded in:** [System Design](../system-design.md) §19

## Context

D-21 (2026-09-25) has a language model pick each product's boost once a night, when the
market runs out of it (ADR-031). The pick is accepted only from 0% to 25%, needs a paid
account and a monthly spending cap, and is recorded with its reason.

F8-S1 sets further rules:
- the model sees only published facts (FR-164);
- it moves one number only (INV-079);
- a pick outside the range gives no boost, not a clipped one (FR-147).

ADR-007 excludes a runtime server, and ADR-001 keeps business rules out of the browser.
How a pick is kept, so the run can be reproduced, is a separate decision: ADR-035.

## Decision

1. **Where it runs.** A step inside the nightly run, after the running-out signal (ADR-031)
   and before F8's quantities are computed. Never in the browser, never at request time.
2. **Which model: Anthropic's `claude-sonnet-5`**, chosen by the repository owner on
   2026-09-26 after seeing four options (below). It spends on his account.
   - The model id and the prompt's version are recorded with every pick (ADR-035). Changing
     either is a commit, never a silent drift.
   - No sampling parameter is set. Anthropic's current models reject `temperature` with an
     error, and determinism comes from the record anyway.
   - Requests go through the ordinary Messages API, not the Batch API (see Rejected options).
   - The key is a GitHub Actions secret, `ANTHROPIC_API_KEY`, set by the repository owner as
     he set `VERCEL_DEPLOY_HOOK_URL`.

   **The options he was shown.** Prices are from Anthropic's pricing page
   (platform.claude.com/docs/en/about-claude/pricing), read on 2026-09-26. The monthly
   figures assume 700 input and 80 output tokens a request, at about 30 requests a night (the
   ADR-031 replay's typical night) and at the 200-request ceiling:

   | Model | Per million tokens, in / out | A month, typical | A month, at the ceiling |
   |---|---|---|---|
   | Haiku 4.5 (`claude-haiku-4-5-20251001`) | $1 / $5 | about $1 | about $6.60 |
   | **Sonnet 5 (`claude-sonnet-5`), chosen** | $2 / $10 | **about $2** | about $13 |
   | Opus 5.5 (`claude-opus-5-5`) | $4 / $20 | about $4 | about $26 |
   | Fable 5.1 (`claude-fable-5-1`) | $10 / $50 | about $10 | about $66 |
3. **What it is given.** One request per product that is running out. It contains only facts
   F8 publishes for that product:
   - the window's weekly units and the daily mean;
   - how many market stores are out, and for how many days;
   - the department, the product name and the shelf life.

   Nothing else goes in: no competitor volume, which is not observed, and no ₪ figure. The
   prompt is a versioned file in the repository.
4. **What it may return, and how that is checked.** It must return JSON,
   `{"boost_pct": <number>, "reason": <text ≤ 160 chars>}`, and is checked mechanically in
   this order:
   - It must parse, and `boost_pct` must be a number from 0 to the policy maximum: 25,
     D-21's limit, read from `configs/policy.yaml`. Otherwise the pick is **rejected**: the
     product gets no boost, and the suggestion says the pick was rejected (FR-147).
   - The reason may contain **no digit**: none of 0–9, the Arabic-Indic ٠–٩ or the Extended
     Arabic-Indic ۰–۹. This is D-16's figure check, applied here. A reason that fails is
     withheld, and the suggestion says the model's reason was withheld because it stated a
     figure. An accepted pick stays accepted.
   - A number spelled out in words cannot be caught mechanically. The prompt forbids it, and
     that is a stated residual, not a guarantee.
   - Only `boost_pct` is ever used as a figure (INV-079).
5. **Spending has two limits.**
   - The account's own monthly spend limit, set by the repository owner in the provider's
     console. This is D-21's cap.
   - A per-run ceiling in policy of **200 requests a night**, provisional. That is five times
     the most products ADR-031's replay flags in one night (40).
   - When more products are running out than the ceiling, they are sent in a fixed order: by
     units sold in the window, highest first, then by barcode (F8-S1 NFR-066). The rest get
     no boost, each saying the night's ceiling was reached. The capability stays available:
     the step ran, and each product carries its own reason.
6. **When the step cannot run.** A missing key, an API failure or a timeout make the boost
   capability unavailable (ADR-014). Suggestions publish without a boost and say why (F8-S1
   SCN-151). The run stays `ok`, because the boost is an optional input and its absence takes
   nothing else away.

## Rejected options

### Call the model from the browser when the page opens
It would add a runtime dependency that ADR-007 excludes, and expose the key to every visitor.
Two visitors could also see different boosts for the same suggestion.

### An unpinned "latest" model alias
Picks would change when the provider moves the alias, with nothing in the record to say why.

### Let the model compute the whole quantity
This is the failure F14's intent records: a model turned "order 20" into "25". F8-S1 INV-079
lets the model move one number, inside a mechanical range.

### Show the model's reason unchecked
The reason is shown to the owner beside a quantity. A reason that states a figure would put a
number on his screen that no published fact carries. D-16 forbids exactly that for F14's
sentence, and the same risk applies here.

### Use the Batch API for half the price
It halves every price above: about $1 a month saved at the typical night. But a batch is
guaranteed only within 24 hours. The nightly run would have to submit one night and collect
the next, so every boost would arrive a night late, for a saving smaller than the cost of
the added machinery.

### Run an open model on the CI runner
There is no GPU on the runner. It would add a second stack to maintain, for nothing D-21 asks
for.

## Consequences

**We accept:**
- A paid account and a key, both the repository owner's console acts.
- A cost every night.
- Nothing yet checks whether a pick is *right* (F8-S1 ASM-072).

**We gain:**
- Per-product boosts, as he decided.
- No pick can escape the 0–25% range, and no model text can put a figure in front of him.

**We will know it was wrong if:**
- The picks cluster at one value, so there is no real per-product judgement.
- More than a small share of picks are rejected, or of reasons withheld.
- The month's spend reaches the cap before the month ends.

## Reversibility

Easy. Removing the key switches the step off, and every suggestion then publishes without a
boost. Past picks stay in their snapshots (ADR-035).

## Binds

| F# | How this constrains it |
|---|---|
| F8 | FR-147, FR-154, FR-164 and INV-079 are implemented here; the record is ADR-035's |
| F14 | D-16's reason sentence may cite a pick, because the pick is a published fact (F8-S1 C-72). This ADR does not govern F14's own model call |
