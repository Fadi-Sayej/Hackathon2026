---
ID: ADR-045
Title: An order suggestion's explanation is asked per department, written with slots the page fills, and sealed as the shelf explanation's is
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-10-10
Parent: [System Design](../system-design.md) §19
Related Specs: F14-S1 (FR-235 … FR-244, INV-098 … INV-101, NFR-082, NFR-083)
Inputs: [docs/features/F14-decision-explanations/specs/F14-S1-decision-explanations.md, D-1, D-3, D-10, D-16, D-29, D-40, ADR-001, ADR-014, ADR-032, ADR-035, ADR-039, src/engine/model_client.py, src/engine/shelf_explanation.py, src/engine/order_evidence.py, src/engine/run.py, scripts/build_order_example.py, scripts/build_shelf_example.py]
Updated: 2026-10-10
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
  figures: the expected sales, the stock left. The card cannot lose them, and each must stay
  right and stay what it is.

## Decision

1. **Where it runs.** A step in the nightly run, after `order_quantity` and before publishing.
   It is never run in the browser, and never at request time. The capability runs
   `order_quantity` first and takes its reason whenever that is unavailable, as
   `shelf_explanation` does with `shelf_plan`.
2. **Which model, and how it is asked.**
   - The model is the one ADR-032 pins, `claude-sonnet-5`, with the same account.
   - The prompt is a versioned file, `configs/prompts/order_explanation.v1.md`. The model id and
     the prompt's version are recorded with every explanation.
   - Its requests go through the shared client of ADR-039 Decision 3. The client gains one
     optional parameter, the request's thinking setting, and a way to return, beside the text,
     the token usage and stop reason the API reports. Left unset and unread, the request is sent
     and answered as today, so the boost and the shelf explanation are unchanged by this ADR.
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
4. **Slots that say what they are.** F14-S1 FR-236 and FR-238 give the details.
   - The model writes no number, in digits or in words, and does not write the product's name.
     Where a figure or the name belongs, it writes a named slot: `{product}`, `{quantity}`,
     `{expected}`, `{weeks}`, `{next_order}`, `{left}`, `{runs_out}` or `{capped}`. Each
     suggestion is offered only the slots its facts support, and each slot may appear once. The
     model is told what each slot means, never its figure or its phrase. It is not sent the
     product's name, the order day's date or weekday, or the shelf life's days; slots carry them.
     The prompt forbids mentioning any other suggestion of the group.
   - The page fills each slot with a phrase that carries the figure and names it, with its
     period: `{left}` becomes "about 3 left on Tuesday 1 Sept", not "3", and `{expected}` "about
     35 expected to sell in the 7 days from Tuesday 1 Sept". Figures take the card's own format,
     and estimates the card's own "about".
   - There is no slot for the stock now. The engine's figure is the stock at the start of the run
     day, and the card never showed it; read later in the day, "now" would be wrong.
   - Where the card has its own sentence for a fact, the text must use it: `{left}` or
     `{runs_out}` when the count was used, and `{capped}`, the card's shelf-life line, when the
     shelf life capped the quantity.
   - The model hears about the market only for a product whose card shows the boost box, and
     hears whether the boost raised the expected sales (a pick above zero), never its figure.
   - Filling is rendering a published field, which ADR-001 allows. The phrases live in the page's
     dictionaries beside the card's own words. The prompt describes how each phrase reads. A
     change to a phrase that changes how it reads in a sentence is a new prompt version, so no text
     written for the old phrase is reused.
   - The capability publishes, per suggestion, the slots offered for it and the prompt version
     its text was written under. The page fills only those slots, and shows only a text whose
     prompt version its phrases serve. It isolates each filled slot for text direction, as it
     already isolates the product name and "40%". Any other slot, a slot whose fact is missing, or
     another prompt version means the text is not shown, and the card shows the engine's
     sentence. Before publishing, the capability runs the check again on every text against
     tonight's offered slots and its group's names.
   - `{weeks}` is offered only when every day of the window has a report with the product's
     units known. F8 sums a week over the days it has reports for (`order_evidence.py`), so a
     week with a missing day would read as a slump, a zero where nothing is known (D-3).
   - The check is ADR-039's no-numeral rule, made stricter. With the slots removed, neither the
     text as written nor its NFKC form may hold a character Unicode classes as a number. Checking
     both catches a numeral that NFKC turns into letters.
   - The intent asks that the figure check be mechanical, «لا بطلبٍ في التعليمات». So the check
     also refuses the number words of F14-S1 Appendix A in the three languages, with their listed
     forms: two upward, fractions, multiples and the duals (יומיים, أسبوعين). Before matching, it
     normalises the text: NFKC; invisible format characters, combining marks and the Arabic
     stretch character removed; `أ`, `إ`, `آ` and `ٱ` folded to `ا` and nothing else; and case
     folded. Words are matched whole, after up to two Hebrew prefix letters, or Arabic's attached
     ones, where `ل` with `ال` is written `لل`. "One", the ordinals, and words that are also
     ordinary words (שני, the bare ست) are left to the prompt.
   - It also refuses any quote-like mark between Hebrew letters, which catches Hebrew numerals
     written in letters (ל״ה, ל”ה) and abbreviations such as ש״ח. And it refuses Appendix A's
     relative days ("tomorrow", "מחר", "غداً"), because a text can be reused on a later night.
   - The lists are a mechanical net for the common forms, not a proof. A withheld text records
     the rule and word that withheld it. A form found missing is added to the lists, and since
     the check runs again before every publish, it applies from the next night.
   - The check also refuses:
     - a slot not offered, or used twice;
     - a text without `{product}` or `{expected}`, or without an offered `{left}`, `{runs_out}`
       or `{capped}`;
     - a product name of the group written out, matched as a whole word;
     - a percentage or ₪ sign, NFKC folding its wide forms, or a percentage or currency word from
       Appendix A, matched like the number words;
     - a text over 200 characters;
     - a language without its own letters.
   - A failing suggestion is withheld in all three languages. The rest of its group stands.
5. **Sealed as ADR-035 and ADR-039 seal.**
   - The snapshot lives under `data/external/snapshots/<run date>/order_explanations/`, the date
     the engine reads it by. It holds `explanations.json`, keyed by suggestion id, and a
     `_manifest.json`. The manifest holds the night's runs, the requests made with the input and
     output tokens and the stop reason the API reported for each, the ceiling, and whether each
     run reached its end.
   - Per suggestion it records
     `{suggestion_id, model, prompt, prompt_sha256, requested_at, inputs_digest, accepted, text | withheld_because, reused_from}`.
     The text is stored with its slots unfilled. A withheld answer's raw text is kept for audit,
     cut to 2,000 characters, and is never shown.
   - The digest is over the suggestion's sent facts with its department's name, and without its
     id. No product name is sent, so a text holds none and may serve another product of the
     department with the same facts; it is never reused in another department. The prompt's
     version is the prompt file's hash, as `shelf_explanation`'s is. The versions the page's
     phrases serve are listed in one place, which the engine, the page and the example's builder
     all read. The engine does not ask under a prompt the list does not serve. A test holds that
     the prompt file's hash is on the list, and the list records a digest of the phrases each
     version serves, so a phrase change fails the test until someone decides whether it needs a
     new prompt version. The id stays the same until the order day (ADR-034), but the facts can
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
   - **Reuse.** Before asking, the step reads earlier nights' snapshots, newest first. It stops at
     the first night whose step reached its end: a run of that night wrote its end manifest,
     whatever stopped its asking. It never reads more than `order_explanation.reuse_nights`
     nights (proposed 7), so the step's time does not grow with the history. With none of them
     ended, it uses what it read. ADR-039 reads only the night before. This step reads back
     further, so that a night that died partway does not make the next night pay again for
     everything. The newest accepted explanation with the same digest, model and prompt version
     is copied into tonight's, with `reused_from`, and no request is made.
6. **Spending, ADR-032's two limits, and a time budget.**
   - The account's monthly spend limit and its alert are the owner's to set where the account is
     managed (D-16, F14-S1 OQ-1404). They are shared with the boost, the shelf explanation and
     the shelf reader.
   - A per-night ceiling in policy, `order_explanation.request_ceiling`, proposed at 60, counted
     across the night's runs as the boost's ceiling is.
   - A time budget, `order_explanation.time_budget_s`, proposed at 600, checked before each send.
     It is cut short by the nightly's deadline: a time the nightly gives the engine, by which
     this step stops sending. It is set so that what follows the engine in the job still fits in
     its 60 minutes: the probes, the commits, and a deploy check of up to 12 minutes. The nightly
     took between 24.6 and 37.2 minutes from 2026-10-03 to 2026-10-09, and its steps' own times
     set the deadline in the implementation plan. The boost, the shelf explanation and the shelf
     reader keep their own budgets, unchanged. The plan states the nightly's combined worst case;
     if it does not fit in 60 minutes, that is F8's and F12's to decide.
   - A request times out at `order_explanation.timeout_s`, proposed 120. Where the shared client
     retries, after a 429, a 5xx or a transport failure, it waits one second and tries once more.
     Any other failure is not retried. One request can therefore take about 241 seconds, and the
     step ends within about 600 + 241 seconds.
   - A request that fails ends the night's asking.

   **What it would cost**, at the prices ADR-032 read on 2026-09-26 ($2 in, $10 out, per million
   tokens). Anthropic's model table gave the same prices on 2026-10-09. The token counts are
   assumptions. The manifest's recorded tokens replace them after the first nights:
   - about 1,500 tokens of prompt per request;
   - about 250 tokens of facts per suggestion;
   - about 200 tokens out per suggestion, three sentences.

   | | Suggestions | Requests | A night | A month (30 nights) |
   |---|---|---|---|---|
   | A small night | about 60 | about 11 | about $0.18 | about $5 |
   | The top of F14-S1 ASM-088's estimate, every suggestion's facts new | about 435 | about 39 | about $1.20 | about $36 |
   | Every group full, up to the ceiling of 60 | 1,200 | 60 | about $3.20 | about $95 |

   The last row is the most the ceiling allows. At the assumed speed below, the time budget stops
   the step at about 720 suggestions, before the ceiling. A ceiling of 40 would cap that row at
   about $64 a month. Reuse brings every row down: a suggestion whose facts did not change costs
   nothing. Nothing is spent until a store's copy has daily sales and a key.

   **How long it would take**, at an assumed 60 tokens a second for each request. That speed is
   not measured and is not documented. At the top of the estimate the answers total about 87,000
   tokens, which four requests at a time write in about 6 minutes. The nightly ran 24.6 of its 60
   minutes on 2026-10-05 (run 37258885696), and between 24.9 and 37.2 minutes on the other nights
   from 2026-10-03 to 2026-10-09.
7. **The example (D-29).**
   - `scripts/build_order_example.py` runs the engine in a temporary folder of its own, with
     stand-in models for the boost and the shelf.
   - One key variable, `SMARTSHELF_ANTHROPIC_API_KEY`, serves every model step today (`run.py`).
     The builder sets it for the boost's stand-in, so the key alone cannot keep this step from
     asking. The engine therefore takes this step's model connection separately from the boost's
     and the shelf explanation's, as it already takes theirs. The builder runs the step with
     asking switched off, so it asks nothing and writes nothing.
   - Before it reproduces the night, the builder seals into that folder's snapshots the committed
     answers, `tests/fixtures/order_example/explanations.json`, or an empty snapshot while there
     are none. It fails when the committed answers' prompt version is not one the page's phrases
     serve. That is how `scripts/build_shelf_example.py` seals the shelf example's. The
     example's artefact carries `order_explanation` beside the three order capabilities it copies
     today.
   - The example's boost today is a stand-in's fixed answer, labelled as the model's. An
     explanation beside it would describe a raise no model chose. So the example's boost becomes a
     real answer too, or none: the same `--explain` run asks for the boost's pick first, then the
     explanations. Until it is run, the example's boost box says the model was not asked tonight,
     and its quantity is not raised. The order probe keeps its stand-in, which it needs. This
     changes F8's example (D-29) and is put to the owner in F14-S1 OQ-1403.
   - Only its `--explain` option calls the real model, once, with the owner's key, and it reads
     the stop reason, so an answer cut off at its limit is refused, not sealed. Nothing of the
     example is written under the store's `data/external/snapshots/`, and no store's run reads
     the fixture (F14-S1 INV-101).
8. **The explanation is never read back.** No engine step, figure or probe reads its text (F14-S1
   INV-098). It is published, and shown in place of the engine's sentence and the shelf-life
   line.

## Rejected options

### Numbers typed by the model, checked against the suggestion's figures
This was the first design, and the owner was shown it: any number in the text had to equal one
the suggestion was sent. Review found that a true number in the wrong place passes. "You'll sell
about 12, and 35 will be left" passes when 12 is the stock and 35 the expected sales. The card has
no other figure to contradict it, because the AI's sentence replaces the engine's. It also could
not make an estimate say "about" (D-10), and it needed rules for rounding, decimal marks and
digit grouping, each a way to pass a wrong figure.

### Bare slots, filled with the figure alone
Review of the second design found the same swap one level up: "You'll sell {left}, and {expected}
will be left" renders the swapped sentence exactly. A phrase that names its figure closes it.

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

### Adaptive thinking at low effort
Anthropic's general advice for Sonnet 5 prefers it to thinking off, for quality. It still spends
output tokens against the 8,000-token limit, in amounts no one has measured on this prompt. With
thinking off, the limit was sized for the sentences alone. Revisit with the first nights' recorded
tokens and stop reasons.

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
- one optional parameter and a usage return on the shared client, a thread pool in one step, and
  a separate model connection for this step in the engine;
- the slots' phrases added to the page's dictionaries in three languages, shown to the owner with
  the mockups;
- the residual of F14-S1 ASM-085: an explanation can still be unfaithful in words. It can give a
  cause the facts lack, use a number word the list leaves out ("one", an ordinal), or turn a slot
  around with a negation or a comparison ("you won't have {left}"). A slot's figure is always the
  engine's, and its phrase always names the figure and its period.

**We gain:**
- the explanation he asked for on every card, under the rules he set for AI-written reasons;
- every figure on the card is still the engine's;
- it is reproducible from committed inputs, and paid for once per distinct set of facts.

**Left open, and not decided here.**
- The three other callers of the shared client also leave thinking at the model's default:
  - the boost, with a 300-token limit;
  - the shelf explanation, with 1,200;
  - the shelf reader, with 4,000 and up to a dozen images.
- By this ADR's own reasoning, that spends output tokens and could cut an answer off. The client
  does not read the stop reason today, so a cut-off answer passes as a bad one. A review on
  2026-10-10 traced what each caller then does: the boost stops the night's asking, and the
  reader asks again, and pays again, every night.
- Whether they should turn thinking off, and how the client should name a cut-off, is F8's and
  F12's to decide. The boost and the explanation wait for daily sales. The reader waits only for
  a photo and the key, so it is likely the first to meet the real model.
- No caller has met it yet: the repository has no model key secret (F14-S1 OQ-1404).

**We will know it was wrong if:**
- the published counts show many suggestions withheld or not written tonight, or the recorded
  words show the lists withholding ordinary text;
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
