---
ID: ADR-045
Title: An order suggestion's explanation is asked per department, checked against its own figures, and sealed as the shelf explanation's is
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-10-09
Parent: [System Design](../system-design.md) §19
Related Specs: F14-S1 (FR-235 … FR-244, INV-098 … INV-100, NFR-082, NFR-083)
Inputs: [docs/features/F14-decision-explanations/specs/F14-S1-decision-explanations.md, D-16, D-40, ADR-014, ADR-032, ADR-035, ADR-039, src/engine/model_client.py, src/engine/shelf_explanation.py]
Updated: 2026-10-09
---

# ADR-045 — An order suggestion's explanation is asked per department, checked against its own figures, and sealed as the shelf explanation's is

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

D-40 asks that every order suggestion carry the AI's explanation. D-16 fixed how an AI-written
reason is made in this product: once a night, from published facts, with a paid account, a
monthly spending ceiling with an alert, and a mechanical check that it states no figure its facts
do not carry. ADR-039 built that method for the shelf explanation, and said F14 could reuse it.

Two things make the order explanation different from the shelf's:
- **Volume.** A shelf plan has a few fixtures. A night's order suggestions could number about 60
  to about 565 at a store like YomYom (F14-S1 ASM-088), so one request each would not fit the
  nightly. The owner chose one request per department (F14-S1 OQ-1402).
- **Figures.** The shelf explanation may state no digit. The order explanation replaces the
  engine's sentence on the card (OQ-1401), and that sentence states figures: the expected sales,
  the stock left. A sentence that may state none would have to explain a quantity without its
  numbers.

## Decision

1. **Where it runs.** A step in the nightly run, after `order_quantity` and before publishing. It
   is never run in the browser, and never at request time.
2. **Which model, and how it is asked.**
   - The model is the one ADR-032 pins, `claude-sonnet-5`, with the same key.
   - The prompt is a versioned file, `configs/prompts/order_explanation.v1.md`. The model id and
     the prompt's version are recorded with every explanation.
   - Its requests go through the shared client of ADR-039 Decision 3. The client gains one
     optional parameter, the request's thinking setting. Left unset, the request is sent as
     today, so the boost and the shelf explanation are unchanged by this ADR.
   - The explanation sets thinking off. Anthropic's model documentation (read 2026-10-09) says
     Sonnet 5 thinks by default when a request does not say otherwise, and that thinking is billed
     as output and counts against the answer's token limit. Writing a sentence from given facts
     needs no reasoning, and with thinking off an answer's length and cost depend only on the
     sentences.
3. **Groups.** The suggestions are grouped by department, in the order `order_quantity` publishes
   them, at most `order_explanation.group_size` (proposed 20) to a request. The answer is JSON
   keyed by suggestion id, each with `he`, `ar` and `en`. Up to `order_explanation.concurrency`
   (proposed 4) requests are in flight at once, through a small pool of threads in the step. The
   ceiling, the time budget and the stop after a double failure are checked before each request
   is sent.
4. **What it is given and how it is checked:** F14-S1 FR-236 and FR-238.
   - Each suggestion is sent only its own published facts, and the department's name goes once
     per request.
   - **The figure check compares numbers, not digits.** After the suggestion's own product name
     is removed, every number in digits must equal one of the numbers sent for that suggestion,
     as sent or rounded to a whole number. This is D-16's rule taken literally: "states no figure
     its suggestion's facts do not carry". The shelf explanation's check is stricter, allowing no
     digit at all (ADR-039 Decision 4), because its sentence replaces nothing that states a figure.
   - The check also refuses `%`, `٪`, `₪` and the currency's name, and needs each language's
     own letters. A failing suggestion is withheld in all three languages. The rest of its group
     stands.
5. **Sealed as ADR-035 and ADR-039 seal.**
   - The snapshot lives under `data/external/snapshots/<run date>/order_explanations/`, the same
     date the engine reads it by. It holds `explanations.json`, keyed by suggestion id, and a
     `_manifest.json` with the night's runs, the requests made, the ceiling and whether the step
     completed.
   - Per suggestion it records
     `{suggestion_id, model, prompt, prompt_sha256, requested_at, inputs_digest, accepted, text | withheld_because, reused_from}`.
     A withheld answer's raw text is kept for audit, cut to 2,000 characters, and is never shown.
   - The digest is over the suggestion's sent facts without its id. An explanation therefore
     follows its facts. The id stays the same until the order day (ADR-034), but the facts can
     change in between.
   - It is committed in the nightly's existing step for sealed answers, which grows to take it.
   - **Merge, never replace.** A second run the same night asks only for suggestions with no
     record for their current digest.
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
   - A time budget, `order_explanation.time_budget_s`, proposed at 600, checked before each
     request. A request times out at `order_explanation.timeout_s`, proposed 120, and is retried
     once after the client's one-second pause, so one request can take about 241 seconds. The
     step therefore ends within about 600 + 241 seconds.
   - A request that fails twice ends the night's asking.
   - The answer's token limit is `order_explanation.max_tokens`, proposed 6,000: 20 suggestions,
     each three texts of at most 200 characters, with room for the JSON.

   **What it would cost**, at the prices ADR-032 read on 2026-09-26 ($2 in, $10 out, per million
   tokens). Anthropic's model table gave the same prices on 2026-10-09. The token counts are
   assumptions, to be replaced by the first nights' measured usage:
   - about 1,500 tokens of prompt per request;
   - about 250 tokens of facts per suggestion;
   - about 200 tokens out per suggestion, three sentences.

   | | Suggestions | Requests | A night | A month (30 nights) |
   |---|---|---|---|---|
   | A small night | about 60 | about 8 | about $0.17 | about $5 |
   | The top of F14-S1 ASM-088's range, every suggestion new | about 565 | about 46 | about $1.55 | about $47 |
   | At the ceiling, 60 full groups | 1,200 | 60 | about $3.20 | about $95 |

   Reuse brings each down: a suggestion whose facts did not change costs nothing. Nothing is spent
   until a store's copy has daily sales and a key.

   **How long it would take**, at an assumed 60 tokens a second for each request. That speed is
   not measured and is not documented. At the top of the range the answers total about 113,000
   tokens. Four requests at a time write that in about 8 minutes, within the budget. The nightly
   ran 24.6 minutes of its 60 on 2026-10-05.
7. **The explanation is never read back.** No engine step, figure or probe reads its text (F14-S1
   INV-098). It is published, and shown in place of the engine's sentence.

## Rejected options

### One request per suggestion
It is the boost's shape, and a failure would touch one card only. But at the top of the range it
is about 565 requests a night. That would cost about $95 a month, since the prompt is paid for on
every request. It would take about 45 minutes one at a time, or many requests at once, which
risks the account's rate limits. The owner chose per department (OQ-1402).

### The shelf explanation's check, no digit at all
It is simpler, and already written. But the AI's sentence replaces the engine's (OQ-1401), which
says "You'll sell about 35… about 12 will still be on the shelf". A sentence forbidden every digit
would have to explain the quantity without its numbers, or the card would lose them. D-16 allows
a figure the facts carry, so the check enforces exactly that.

### The Message Batches API
It costs half as much per token. But a batch may take up to 24 hours to finish, and the nightly
publishes the same night. It would also need state across runs to collect a batch the next night,
which no other step has. Re-evaluate if the nightly's cost, not its time, becomes the constraint.

### Thinking left at the model's default
It needs no client change. But thinking is billed as output and counts against the token limit. A
20-suggestion answer would then cost more, and could be cut off before its JSON closes. That
withholds the whole group, and no reasoning is needed to put given facts into words.

### Sentences built from templates
They would be deterministic, cheap and keyless. They already exist: they are the engine's
sentence, which the card falls back to. But the owner asked for the AI's (D-40).

## Consequences

**We accept:**
- one more snapshot directory, and a bigger commit step in the nightly;
- one optional parameter on the shared client, and a thread pool in one step;
- a check that allows figures, so an explanation can state a true number. The cost is a more
  complex check than the shelf's: a number must be parsed and compared;
- the residual of F14-S1 ASM-085: an explanation can still be unfaithful in words.

**We gain:** the explanation he asked for on every card, under the rules he set for AI-written
reasons, reproducible from committed inputs, and paid for once per distinct set of facts.

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
| F8 | Nothing in the quantities or the boost changes. The shared client gains an optional thinking setting, unused by the boost |
| F12 | The shelf explanation keeps its own check and its default thinking. This ADR changes nothing in it |
