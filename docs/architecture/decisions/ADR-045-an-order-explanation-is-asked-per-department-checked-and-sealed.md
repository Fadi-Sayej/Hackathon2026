---
ID: ADR-045
Title: An order suggestion's explanation is asked per department, written with slots the page fills, and sealed as the shelf explanation's is
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-10-09
Parent: [System Design](../system-design.md) §19
Related Specs: F14-S1 (FR-235 … FR-244, INV-098 … INV-101, NFR-082, NFR-083)
Inputs: [docs/features/F14-decision-explanations/specs/F14-S1-decision-explanations.md, D-10, D-16, D-29, D-40, ADR-001, ADR-014, ADR-032, ADR-035, ADR-039, src/engine/model_client.py, src/engine/shelf_explanation.py, scripts/build_order_example.py, scripts/build_shelf_example.py]
Updated: 2026-10-09
---

# ADR-045 — An order suggestion's explanation is asked per department, written with slots the page fills, and sealed as the shelf explanation's is

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

D-40 asks that every order suggestion carry the AI's explanation. D-16 fixed how an AI-written
reason is made in this product: once a night, from published facts, with a paid account, a
monthly spending ceiling with an alert, and a mechanical check that it states no figure its facts
do not carry. ADR-039 built that method for the shelf explanation, and said F14 could reuse it.

Two things make the order explanation different from the shelf's:
- **Volume.** A shelf plan has a few fixtures. A night's order suggestions could number about 60
  to about 435 at a store like YomYom (F14-S1 ASM-088), so one request each would not fit the
  nightly. The owner chose one request per department (F14-S1 OQ-1402).
- **Figures.** The shelf explanation may hold no digit outside its product names. The order
  explanation replaces the engine's sentence on the card (OQ-1401), and that sentence states
  figures: the expected sales, the stock left. The card cannot lose them, and they must stay
  right.

## Decision

1. **Where it runs.** A step in the nightly run, after `order_quantity` and before publishing.
   It is never run in the browser, and never at request time. The capability runs
   `order_quantity` first and takes its reason whenever that is unavailable, as
   `shelf_explanation` does with `shelf_plan`.
2. **Which model, and how it is asked.**
   - The model is the one ADR-032 pins, `claude-sonnet-5`, with the same key.
   - The prompt is a versioned file, `configs/prompts/order_explanation.v1.md`. The model id and
     the prompt's version are recorded with every explanation.
   - Its requests go through the shared client of ADR-039 Decision 3. The client gains one
     optional parameter, the request's thinking setting. Left unset, the request is sent as
     today, so the boost and the shelf explanation are unchanged by this ADR.
   - The explanation sets thinking off. Anthropic's model documentation (read 2026-10-09) says
     Sonnet 5 thinks by default when a request does not say otherwise, and that thinking is billed
     as output and counts against the answer's token limit. Writing sentences from given facts
     needs no reasoning. With thinking off, an answer's length and cost depend only on the
     sentences, and a long answer is not cut off before its JSON closes.
3. **Groups.**
   - The suggestions are grouped by department, in the order `order_quantity` publishes them, at
     most 20 to a request. That is the figure the owner chose (OQ-1402). Policy may set a smaller
     group; a larger one is his decision.
   - The answer is JSON keyed by suggestion id, each with `he`, `ar` and `en`, within 8,000
     tokens.
   - Up to `order_explanation.concurrency` (proposed 4) requests are in flight at once, through a
     small pool of threads in the step.
   - The ceiling is counted when a request is sent, not when it returns. The time budget and the
     stop after a failure are checked before each send.
   - Requests already in flight when the step stops are allowed to finish, and their answers are
     checked and kept.
4. **Slots, not numbers.** F14-S1 FR-236 and FR-238 give the details.
   - The model writes no numeral. Where a figure belongs, it writes a named slot, such as
     `{expected}`, `{left}`, `{cycle_days}` or `{order_day}`. Each suggestion is offered only the
     slots its facts support.
   - The page fills each slot from that suggestion's published facts, in the words and format
     the card already uses: "about 34.6", "7 days", "Tuesday 1 Sep". This is rendering a published
     field, which ADR-001 allows, and the wording stays in the page's dictionaries, the only place
     it lives today.
   - The check is ADR-039's no-numeral rule, made stricter. The suggestion's own product name and
     the slots are replaced by a space, the text is normalised (NFKC), and no character Unicode
     classes as a number may remain.
   - The check also refuses a slot not offered, a text without `{expected}`, and a capped text
     without `{shelf_life_days}`. It refuses a percentage or ₪ sign or word from a fixed list, a
     text over 200 characters, and a language without its own letters.
   - A failing suggestion is withheld in all three languages. The rest of its group stands.
5. **Sealed as ADR-035 and ADR-039 seal.**
   - The snapshot lives under `data/external/snapshots/<run date>/order_explanations/`, the date
     the engine reads it by. It holds `explanations.json`, keyed by suggestion id, and a
     `_manifest.json` with the night's runs, the requests made, the ceiling and whether the step
     completed.
   - Per suggestion it records
     `{suggestion_id, model, prompt, prompt_sha256, requested_at, inputs_digest, accepted, text | withheld_because, reused_from}`.
     The text is stored with its slots unfilled. A withheld answer's raw text is kept for audit,
     cut to 2,000 characters, and is never shown.
   - The digest is over the suggestion's sent facts without its id. An explanation therefore
     follows its facts. The id stays the same until the order day (ADR-034), but the facts can
     change in between.
   - It is committed in the nightly's existing step for sealed answers, which commits the boost's
     picks and the shelf explanations today, and grows to take it.
   - **Nothing sealed is replaced**, as ADR-035 and ADR-039 require. A second run the same night
     asks only for suggestions with no record that night. A suggestion whose facts changed since
     its record shows as out of date until the next night.
   - **The manifest is written when the step starts**, and again when it ends. A job that dies
     partway is never mistaken for a night with no key.
   - **Print mode never calls the model.** It reads the night's snapshot. Without one, the
     capability is unavailable with `no_model_key`, and every quantity is unchanged.
   - **Reuse.** Before asking, the step reads the most recent earlier night's snapshot, and only
     that one. An accepted explanation with the same digest, model and prompt version is copied
     into tonight's, with `reused_from`, and no request is made.
6. **Spending, ADR-032's two limits, and a time budget.**
   - The account's monthly spend limit and its alert are the owner's to set where the account is
     managed (D-16, F14-S1 OQ-1404). They are shared with the boost, the shelf explanation and
     the shelf reader.
   - A per-night ceiling in policy, `order_explanation.request_ceiling`, proposed at 60, counted
     across the night's runs as the boost's ceiling is.
   - A time budget, `order_explanation.time_budget_s`, proposed at 600, checked before each send.
   - A request times out at `order_explanation.timeout_s`, proposed 120. Where the shared client
     retries, after a 429, a 5xx or a transport failure, it waits one second and tries once more.
     One request can therefore take about 241 seconds, and the step ends within about
     600 + 241 seconds.
   - A request that fails ends the night's asking.

   **What it would cost**, at the prices ADR-032 read on 2026-09-26 ($2 in, $10 out, per million
   tokens). Anthropic's model table gave the same prices on 2026-10-09. The token counts are
   assumptions, to be replaced by the first nights' measured usage:
   - about 1,500 tokens of prompt per request;
   - about 250 tokens of facts per suggestion;
   - about 200 tokens out per suggestion, three sentences.

   | | Suggestions | Requests | A night | A month (30 nights) |
   |---|---|---|---|---|
   | A small night | about 60 | about 8 | about $0.17 | about $5 |
   | The top of F14-S1 ASM-088's estimate, every suggestion's facts new | about 435 | about 40 | about $1.21 | about $36 |
   | Every group full, up to the ceiling of 60 | 1,200 | 60 | about $3.20 | about $95 |

   The last row is the most the ceiling allows. At the assumed speed below, the time budget stops
   the step at about 720 suggestions, before the ceiling. A ceiling of 40 would cap that row at
   about $64 a month. Reuse brings every row down: a suggestion whose facts did not change costs
   nothing. Nothing is spent until a store's copy has daily sales and a key.

   **How long it would take**, at an assumed 60 tokens a second for each request. That speed is
   not measured and is not documented. At the top of the estimate the answers total about 87,000
   tokens, which four requests at a time write in about 6 minutes. The nightly ran 24.6 of its 60
   minutes on 2026-10-05 (run 37258885696), and 24.9 on 2026-10-09.
7. **The example (D-29).**
   - `scripts/build_order_example.py` runs the engine in a temporary folder of its own, with
     stand-in models for the boost and the shelf. It gives the explanation step no key, so the
     step asks nothing.
   - Before it reproduces the night, it seals into that folder's snapshots the committed answers,
     `tests/fixtures/order_example/explanations.json`, or an empty snapshot while there are none.
     That is how `scripts/build_shelf_example.py` seals the shelf example's.
   - Only its `--explain` option calls the real model, once, with the owner's key. Nothing of the
     example is written under the store's `data/external/snapshots/`, and no store's run reads
     the fixture (F14-S1 INV-101).
8. **The explanation is never read back.** No engine step, figure or probe reads its text (F14-S1
   INV-098). It is published, and shown in place of the engine's sentence.

## Rejected options

### Numbers typed by the model, checked against the suggestion's figures
This was the first design, and the owner was shown it: any number in the text had to equal one
the suggestion was sent. Review found that a true number in the wrong place passes. "You'll sell
about 12, and 35 will be left" passes when 12 is the stock and 35 the expected sales. The card has
no other figure to contradict it, because the AI's sentence replaces the engine's. It also could
not make an estimate say "about" (D-10), and it needed rules for rounding, decimal marks and
digit grouping, each a way to pass a wrong figure. With slots, every figure is the engine's, in
its own place, with the card's own "about".

### The shelf explanation's check alone, no numerals and no slots
It is simpler, and already written. But the card would lose the figures the engine's sentence
gives today, which the owner did not choose.

### One request per suggestion
It is the boost's shape, and a failure would touch one card only. But at the top of the estimate
it is about 435 requests a night, paying for the prompt on every one. That is about $72 a month,
against about $36 per department. One at a time it would take half an hour or more. Many at once
risks the account's rate limits. The owner chose per department (OQ-1402).

### The Message Batches API
It costs half as much per token. But a batch may take up to 24 hours to finish, and the nightly
publishes the same night. It would also need state across runs to collect a batch the next night,
which no other step has. Re-evaluate if the nightly's cost, not its time, becomes the constraint.

### Thinking left at the model's default
It needs no client change. But thinking is billed as output and counts against the token limit,
so a 20-suggestion answer would cost more. It could also be cut off before its JSON closes, which
withholds the whole group. No reasoning is needed to put given facts into words.

### Sentences built from templates
They would be deterministic, cheap and keyless. They already exist: they are the engine's
sentence, which the card falls back to. But the owner asked for the AI's (D-40).

## Consequences

**We accept:**
- one more snapshot directory, and a bigger commit step in the nightly;
- one optional parameter on the shared client, and a thread pool in one step;
- slot words added to the page's dictionaries in three languages, worded as the card's own;
- the residual of F14-S1 ASM-085: an explanation can still be unfaithful in words, or put a slot
  where it means another fact. A slot's figure is always right; its place in the sentence is the
  model's.

**We gain:**
- the explanation he asked for on every card, under the rules he set for AI-written reasons;
- every figure on the card is still the engine's;
- it is reproducible from committed inputs, and paid for once per distinct set of facts.

**Left open, and not decided here.** The boost's requests (300 tokens) and the shelf
explanation's (1,200) also leave thinking at the model's default. By this ADR's own reasoning,
that spends output tokens and could cut an answer off. Whether they should turn it off is their
own question, F8's and F12's. Neither has run against the real model yet, since no store sends
daily sales.

**We will know it was wrong if:**
- the published counts show many suggestions withheld or not written tonight;
- the manifests show answers cut off, timeouts, or 429s (F14-S1 ASM-086, ASM-087);
- he reports an explanation that does not match its card.

Each of these is a policy value or a new prompt version, not a new design.

## Reversibility

Easy. The explanation is text in place of a sentence the engine still computes, and removing it
changes no figure (INV-098). The sealed snapshots stay as history. The client's new parameter is
optional, and nothing else depends on it.

## Binds

| F# | How this constrains it |
|---|---|
| F14 | `order_explanation` (F14-S1 FR-235 … FR-244) |
| F8 | Nothing in the quantities or the boost changes. The shared client gains an optional thinking setting, unused by the boost. The card's sentence becomes the fallback when an explanation exists (F14-S1 FR-242) |
| F12 | The shelf explanation keeps its own check and its thinking setting. This ADR changes nothing in it |
