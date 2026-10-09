---
ID: F14-S1
Title: Decision Explanations — the AI's reason beside every order suggestion
Status: Ready for review
Owner: smartshelf-architect
Version: 0.1 (2026-10-09)
Parent: [F14 — Decision Explanations](../intent.md)
Related Intents: INT-EXPL
Inputs: [docs/features/F14-decision-explanations/intent.md, docs/product/PRD.md, docs/product/intent-register.md (D-1, D-3, D-10, D-15, D-16, D-17, D-28, D-29, D-40), docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md (FR-147, FR-154, FR-160 … FR-164), docs/features/F12-planogram/specs/F12-S1-planogram.md (FR-210 … FR-215), ADR-001, ADR-007, ADR-014, ADR-028, ADR-032, ADR-034, ADR-035, ADR-039, ADR-045, CLAUDE.md]
Answered by: [System Design](../../../architecture/system-design.md) §21
Updated: 2026-10-09
---

# F14-S1 — Decision Explanations

> **Why this spec exists now.** The repository owner asked for it on 2026-10-09: "yes every
> suggestion should have a ai explanation" (D-40). How the explanation is made was settled on
> 2026-09-24 (D-15 … D-17). While the design was put to him the same day, he chose:
> - **the AI's sentence replaces the engine's sentence on the card** (OQ-1401);
> - **one request per department** (OQ-1402).
>
> He approved the four parts of the design in conversation: what the sentence says, how the
> nightly makes it, what the card shows, and the example and tests. This spec writes them down.
> Each choice it makes for him is marked **(decided here)** and put to him as OQ-1403.
>
> **What he will see, and when.** No store sends daily sales today (D-23), so `order_quantity`
> publishes nothing and neither does this. Until a store does, he sees the explanation only in
> Reorder's marked example (D-29, FR-244).

> **Identifier note.** Every id below is new and globally unique: FR-235 … FR-244, INV-098 …
> INV-100, SCN-178 … SCN-185, NFR-082, NFR-083, C-76 … C-80, AC-221 … AC-231, ASM-085 … ASM-088,
> OQ-1401 … OQ-1404. No existing id is renumbered.

Implements intent F14. Bound by ADR-001, ADR-007, ADR-014, ADR-028, ADR-032, ADR-034, ADR-035,
ADR-039 and ADR-045, and by settled decisions D-1, D-3, D-10, D-15, D-16, D-17, D-28, D-29 and
D-40.

## 1. Purpose

Every order suggestion F8 publishes carries an explanation, written by the AI in his language,
of why that quantity (D-40). The explanation puts the suggestion's own published facts into
words. On the Reorder card it replaces the engine's sentence, which comes back on any night the
explanation is missing. It never changes a quantity. It adds no cause the facts do not carry,
and it states no figure they do not carry (D-16).

## 2. Intent Traceability

- **INT-EXPL** — «مع مساعد ذكاء اصطناعي يشرح القرار» (#54). D-15 makes "the decision" the order.
- **D-40** — "yes every suggestion should have a ai explanation" (2026-10-09).
- **D-16** — how an AI-written reason is made: once a night, from published facts, under a paid
  account, a monthly ceiling with an alert, and a mechanical figure check.
- Serves the PRD's F14 row (V2, with F8, no due date: D-17).

## 3. Scope

Behavioural scope, not a file list. Which files change is declared by the implementation plan.

### In Scope
- **`order_explanation`**, a capability of its own, published nightly beside `order_quantity`.
- **The nightly step that writes it.** It asks the model once per department group, checks each
  sentence, and seals the night's answers.
- **The Reorder card and one note above the suggestions** (FR-242, FR-243).
- **The explanations in Reorder's marked example** (D-29, FR-244).
- **The boundary probe's extension** (§20).

### Out of Scope
- **Explaining V1's findings** (prices, stock, catalogue). D-15 keeps them showing their
  evidence.
- **Approved orders.** An approved line shows the product, the quantity and the order day
  (F8-S1 FR-162), and no explanation.
- **The market boost's own reason.** It stays in the boost box, Arabic only, as F8-S1 FR-164
  publishes it. Changing its language is the boost's prompt, and F8's.
- **Causes F8 does not publish:** weather, busy weekdays, promotions, holidays. Adding one would
  be a new input and a new decision. The intent's own example (#54) needs two of them (§22).
- **An assistant he can ask on screen.** D-16 rejected writing at request time.
- **The Shelf plan's explanation.** That is F12-S1 FR-210 … FR-215.

## 4. Actors and Triggers

| Actor | Trigger | Frequency |
|---|---|---|
| The nightly engine | Computes `order_quantity`, then asks for, checks and seals the explanations, then publishes `order_explanation` | Nightly (ADR-007) |
| The language model | Writes one group's explanations from their published facts | Nightly, only for suggestions it has not explained before (FR-239) |
| The owner | Opens Reorder | Any time |
| The team | Asks once, by hand with the key, for the example's explanations, and commits them (FR-244) | When the example's inputs or the prompt change |
| A team account | Opens Reorder | Any time; read-only (ADR-029) |

## 5. Domain Terms

| Term | Definition |
|---|---|
| Suggestion | One `order_quantity` entry: a product's quantity for its department's next order day (F8-S1 FR-163). |
| Explanation | The AI's account, in Hebrew, Arabic and English, of why one suggestion's quantity is what it is, written from that suggestion's facts (FR-235). |
| The engine's sentence | The card's text today: "You'll sell about {expected} before your next order…", with its stock clause, and the shelf-life line "Only what sells in {days}, before it spoils." |
| Group | The suggestions one request asks about: one department's, at most the policy's group size (FR-237). |
| Sent figures | The numbers FR-236 sends the model for one suggestion. They are the only numbers its explanation may state (FR-238). |
| Facts digest | A hash of one suggestion's FR-236 facts, without its id. It says what an explanation was written from (FR-239). |

## 6. Functional Requirements

**FR-235** — Every suggestion carries an explanation, written by a language model, of why its
quantity is what it is (D-40). Where its facts support them, the explanation says:
- how steadily it has sold over the window's four weeks;
- when the next delivery comes, by weekday, and how many days the order covers;
- what stock will be left by then, when the count was used;
- where they apply: that the shelf life capped the quantity; that the count could not be used,
  so the quantity is gross; that the nearby stores have run out of it.

It is written once a night, from the suggestion's published facts, and published with it. It is
never written at request time (D-16).

**FR-236** — The model is given only what each suggestion publishes (F8-S1 FR-154)
**(decided here)**:
- its id, which keys the answer, its product name, its quantity, and whether it is net or gross;
- the units sold in each of the window's four weeks, oldest first, and the expected sales;
- the order day, as a weekday, and how many days the cycle covers;
- whether the count was used. When it was, the stock now and the stock at the order day. When
  it was not, F8's reason (F8-S1 FR-149);
- the shelf life in days when it is stated, and whether it capped the quantity;
- whether the nearby stores are running out of it, and whether the market boost applied.

Each request also carries the department's name. Nothing else goes in: no barcode, no date, no
price, cost, margin or ₪ figure (D-1), no boost percentage, no boost reason and no daily mean.
The numbers sent are the only numbers the answer may state (FR-238).

**FR-237** — The model is asked once per group **(decided here; OQ-1402)**:
- one department's suggestions, in the order `order_quantity` publishes them, at most
  `order_explanation.group_size` to a request (proposed 20). A larger department is asked in
  several groups;
- the answer is JSON keyed by suggestion id, each with its Hebrew, Arabic and English text;
- up to `order_explanation.concurrency` requests run at once (proposed 4);
- the request turns the model's thinking off. The task is wording, not reasoning. The pinned
  model thinks by default when a request does not say otherwise, and thinking is billed as
  output and counts against the answer's token limit (ADR-045).

**FR-238** — Each suggestion's text is checked mechanically, on its own, before anything is
published **(decided here)**:
- the answer parses. It holds that suggestion's id with all three languages, each non-empty and
  within `order_explanation.max_chars` (proposed 200). The Hebrew text holds a Hebrew letter,
  and the Arabic text an Arabic letter;
- **the figure check (D-16).** First the suggestion's own product name is removed, exactly as
  given. Then every number written in digits (0–9, ٠–٩ or ۰–۹, read as one number when joined by
  `.` or `٫`) must equal one of that suggestion's sent figures, as sent or rounded to a whole
  number. This is looser than the shelf explanation's check, which allows no digit (F12-S1
  FR-212), because this sentence replaces the engine's, and the engine's states figures
  (OQ-1401);
- no text holds a percent sign (`%`, `٪`), the sign `₪`, or the currency's name from a fixed list
  in the three languages (D-1).

A failing suggestion's three languages are withheld together, so they never disagree. The
others in the same answer are unaffected. A suggestion missing from the answer is withheld as
missing. An answer that does not parse withholds its whole group. Two things cannot be caught
mechanically: a number written in words, and a cause the facts do not carry. The prompt forbids
both, and ASM-085 states what is left.

**FR-239** — Each night's explanations are sealed and reproduced as the shelf explanation's are
(ADR-035, ADR-039, ADR-045) **(decided here)**:
- the snapshot records, per suggestion, the model, the prompt's version, the facts digest, and
  the text or why it was withheld;
- print mode never calls the model. It reads the night's snapshot;
- an explanation whose digest no longer matches its suggestion's facts is not shown. The
  suggestion counts as out of date;
- a suggestion is not asked when the most recent earlier snapshot holds an accepted explanation
  with the same facts digest, model and prompt version. Tonight's snapshot copies it, so each
  night's snapshot is complete on its own, and unchanged facts are paid for once. A withheld
  explanation is never reused, and a new prompt or model asks again;
- a second run the same night asks only for suggestions with no record for their current digest.

**FR-240** — `order_explanation` is a capability of its own, `value_policy: none` and not
admitted, because it fails on different days from the quantities (ADR-014) **(decided here)**:
- it requires `order_quantity`'s inputs and `order_explanations`, the night's sealed snapshot.
  Without a model key the live run asks nothing and seals nothing, so the reason is
  `no_model_key`;
- whenever `order_quantity` is unavailable, so is it, with `order_quantity`'s reason;
- it publishes, per suggestion, its text in the three languages, or why it has none: withheld
  (with the check's reason), out of date, or not written tonight. With a text, it also publishes
  the model, the prompt and the night it was reused from, if any;
- it counts suggestions, explained, withheld, out of date, not written tonight, reused and
  requests made. Explained, withheld, out of date and not written tonight add up to the
  suggestions: the intent's "N of N".

**FR-241** — The step is bounded **(decided here)**:
- spending has ADR-032's two limits. The account's monthly limit and its alert are the owner's,
  set in the provider's console (D-16). They are shared with the boost, the shelf explanation
  and the shelf reader. A per-night ceiling of requests sits in policy, proposed 60, and is
  counted across the night's runs;
- a time budget, proposed 600 seconds, is checked before each request;
- a request times out at 120 seconds and is retried once. A request that fails twice ends the
  night's asking, as the boost's does.

A suggestion past any of these is not written tonight, and says so (FR-240).

**FR-242** — On Reorder, a suggestion with an explanation shows it in place of the engine's
sentence and the shelf-life line, in the page's language, after a tag saying it is the AI's
**(OQ-1401)**. The quantity, the "Your stock count wasn't used" notice, the market boost box and
the three buttons stay as they are. A suggestion without an explanation shows the card exactly
as F8 shows it today, with no tag and no per-card reason.

**FR-243** — Above the suggestions, once, Reorder shows a note:
- what the AI does: it writes each card's explanation from that suggestion's facts, and it
  explains the quantity without changing it;
- when only some of tonight's suggestions have one, how many do, from `order_explanation`'s
  published counts ("The AI explained 28 of tonight's 30 suggestions. The others show the
  engine's sentence.");
- when none do, that the AI has not explained tonight's suggestions;
- when `order_explanation` is unavailable, its reason in his words. Without a key, that the AI's
  explanations are off because no key for the model has been set up.

When `order_quantity` is unavailable, Reorder shows F8's waiting text and no note (F8-S1 FR-160).

**FR-244** — In Reorder's marked example (D-29), the explanations are the real step's answers for
the example's test shop. The team asks for them once, by hand with the key, and commits them with
the example's inputs, because the example is built in print mode, which never calls the model.
Until then, the example's builder gives the engine an empty snapshot, so the example's cards show
the engine's sentence and the note says the AI has not explained them. The example stays
read-only: nothing in it can be approved, changed, saved or sent.

## 7. Behavioral Invariants

**INV-098** — No figure of `order_quantity`, `market_boost` or any other capability comes from the
explanation, and nothing reads its text back. *Violated if* any quantity, expected sales, stock,
entry, id, outcome key or count other than `order_explanation`'s own differs between a run with
the sealed explanations and one without them.

**INV-099** — An explanation is shown only beside the facts it was written from. *Violated if*
one is published for a suggestion whose facts digest differs from the one it recorded.

**INV-100** — No published explanation states, in digits, a number its suggestion was not sent,
a percentage or a ₪ amount (D-1, D-16). *Violated if* re-running FR-238's check on any published
text fails it.

## 8. Behavioral Scenarios

**SCN-178** — Given a suggestion for במבה with an accepted explanation sealed for its current
facts, when he opens Reorder in Hebrew, then its card shows the AI tag and the Hebrew text where
the engine's sentence was. The quantity, the buttons and any boost box are unchanged.

**SCN-179** — Given a group of six suggestions, where the model's sentence for one says "40" and
none of its sent figures is 40, when the step checks the answer, then that one is withheld as
stating a figure and its card shows the engine's sentence. The other five are shown, and the
note says the AI explained 5 of tonight's 6 suggestions.

**SCN-180** — Given no model key, when the nightly runs, then no request is made,
`order_explanation` is unavailable with `no_model_key`, every card shows the engine's sentence,
and the note says the AI's explanations are off. Every quantity equals a run without the step.

**SCN-181** — Given a suggestion whose facts are unchanged since last night's accepted
explanation, when the step runs, then no request is made for it, and tonight's snapshot copies
the explanation, naming last night as where it came from.

**SCN-182** — Given more groups than the night's request ceiling allows, or a time budget spent,
when the step stops asking, then the remaining suggestions are not written tonight. Their cards
show the engine's sentence, and the counts say how many.

**SCN-183** — Given a request that fails twice, when the step continues, then it asks nothing more
that night, and every suggestion not yet asked is not written tonight.

**SCN-184** — Given the example before its explanations are committed, when he opens "See how
this page looks", then every card shows the engine's sentence and the note says the AI has not
explained them. Nothing can be approved.

**SCN-185** — Given an explanation sealed before a late report changed its suggestion's facts,
when print mode reproduces the night, then that explanation is not shown, the suggestion counts
as out of date, and its card shows the engine's sentence.

## 9. Inputs and Observable Outputs

| Input | Source | Required? |
|---|---|---|
| `order_quantity`'s published suggestions and their facts | The night's run (F8-S1 FR-154) | Yes. Without them, so is this unavailable, with their reason |
| The night's explanations | The model's answers, checked and sealed under `data/external/snapshots/` (ADR-045) | Yes. Without them, `no_model_key` |
| The prompt | A versioned file under `configs/prompts/` (ADR-045) | Yes |
| The policy's values | `order_explanation` in `configs/policy.yaml` (FR-237, FR-238, FR-241) | Yes |

| Output | Where it is observable |
|---|---|
| `order_explanation`: per suggestion, its text in three languages or why it has none; the counts (FR-240) | `dashboard.json`; the Reorder page |
| The night's sealed snapshot, with the requests made and whether the step completed | `data/external/snapshots/<night>/order_explanations/` |
| The example's explanations (FR-244) | Committed with the example's inputs; the example's preview |

## 10. State / Lifecycle Semantics

- **The explanation is written once a night and kept.** The snapshot is committed by the
  nightly's existing step for sealed answers (CLAUDE.md rule 9). It is never rewritten, only
  added to the same night (FR-239).
- **Recomputed each run:** which sealed explanation matches which suggestion, by digest.
- **Never stored:** anything at request time. Nothing is written to owner state, and the
  explanation does not touch a suggestion's id or outcome key (ADR-034, INV-098).
- **A suggestion's explanation follows its facts, not its id.** The id is the same every night
  until the order day (ADR-034). When its facts change, a new explanation is asked for. When
  they do not, the old one is reused (FR-239).

## 11. Failure and Recovery Behavior

| Condition | Behaviour |
|---|---|
| No model key | Nothing is asked or sealed. `order_explanation` is unavailable (`no_model_key`). Every card shows the engine's sentence |
| `order_quantity` unavailable | So is `order_explanation`, with the same reason. Reorder waits as F8 does |
| An answer does not parse, or misses a suggestion | That group, or that suggestion, is withheld. Its cards show the engine's sentence. It is asked again the next night |
| A sentence fails the check | That suggestion is withheld, with the check's reason. The rest of its group is shown |
| Ceiling reached, time budget spent, or a request failed twice | The suggestions not asked are not written tonight (FR-241) |
| A sealed explanation's digest no longer matches | Not shown; out of date (INV-099) |
| `order_quantity` is available with no suggestions | `order_explanation` is available with every count at zero. That is a result, not a failure: there is nothing to explain. No note is shown |

Nothing here is an empty result standing in for a failure (CLAUDE.md rule 10): every suggestion
is counted in exactly one of FR-240's four states.

## 12. Edge Cases

| Case | Behaviour |
|---|---|
| A product name holds digits ("קוקה קולה 1.5") | The name is removed before the figure check, exactly as given. A name changed in the copying keeps its digits, and is checked like any number |
| A sentence names another product of its group | That name is not removed, so any digits in it are checked against this suggestion's figures |
| A number written with a thousands comma ("1,000") | Read as two numbers, 1 and 000. Unless both are sent figures, it is withheld. Withheld is safer than misread |
| Arabic-Indic digits in the Arabic text | Read as the same numbers (FR-238) |
| Expected sales of 34.6 | "34.6" and "35" both pass. "34" does not |
| A gross suggestion | No stock figure is sent, so none can be stated. The "Your stock count wasn't used" notice stays on the card (FR-242) |
| A department with 45 suggestions | Three groups: 20, 20 and 5 |
| The boost applied | The explanation may say the nearby stores ran out. It cannot state the boost's percentage, which stays in the boost box with its "the model's estimate" label (D-10) |
| A suggestion approved or dismissed earlier | It is not on the page (F8-S1 FR-163). The note's counts are tonight's published suggestions |

## 13. Non-Functional Requirements

**NFR-082** — The step never holds the quantities up. Its requests are bounded by the policy's
ceiling, its time by the budget checked before each request, and each request by its timeout
(FR-241). It ends within about 600 + 241 seconds, the budget plus one request timed out twice.
Each night it publishes the requests made and how many explanations were reused.

**NFR-083** — Its cost is estimated before it is switched on, and counts under ADR-032's monthly
limit. ADR-045 gives the estimate: about $5 a month at about 60 suggestions a night, and about $47
a month at about 565 if every suggestion changes nightly. These are replaced by the first nights'
measured usage.

## 14. Compatibility and External Constraints

**C-76** — There is no service running at request time (ADR-007), so the explanation is written
by the nightly or not at all.

**C-77** — The page renders published fields and computes nothing (ADR-001). The note's counts
are `order_explanation`'s published counts, not a count the page makes.

**C-78** — CI commits only `data/external/snapshots/` (CLAUDE.md rule 9). The nightly's sealed
explanations live there. The example's are committed by a person (FR-244).

**C-79** — Front-end work waits for the owner's approval of its mockups (2026-09-16). The card
and the note are built only after he approves screenshots of the example in Hebrew, Arabic and
English, on desktop and phone.

**C-80** — One store per copy (D-28). The prompt is product text: it names no store, and nothing
in it is a store's setting.

## 15. Acceptance Criteria

**AC-221** — Withholding the sealed explanations leaves every quantity, figure, entry, id and
outcome key of `order_quantity` and `market_boost` unchanged. Each suggestion then says it has no
explanation, and why. *(FR-240, INV-098)*

**AC-222** — The check, run on fixed answers:
- a sentence whose numbers are all sent figures passes, including expected sales rounded to a
  whole number, Arabic-Indic digits, and digits inside the product's own name;
- a sentence with a number not sent is withheld as stating a figure;
- so is one with `%`, `٪`, `₪` or the currency's name;
- so is one over the length limit, one missing a language, and a Hebrew text with no Hebrew
  letter.

Only the failing suggestion is withheld, in all three languages. *(FR-238, INV-100)*

**AC-223** — The request built for a group carries only FR-236's facts and the department's
name. It carries no barcode, date, price, cost, margin, ₪ figure, boost percentage, boost reason
or daily mean. It turns thinking off. *(FR-236, FR-237)*

**AC-224** — Groups are one department's suggestions in published order, at most the group
size. An answer missing a suggestion withholds that one. An answer that does not parse withholds
its group only. *(FR-237, FR-238)*

**AC-225** — Print mode never calls the model, and reproduces the published explanations from the
snapshot. An explanation whose facts digest no longer matches is not shown. *(FR-239, INV-099)*

**AC-226** — A suggestion whose facts, model and prompt match an accepted explanation in the most
recent earlier snapshot is not asked, and tonight's snapshot copies it with where it came from.
A withheld one is asked again. *(FR-239)*

**AC-227** — Past the request ceiling or the time budget, or after a request fails twice, no
further request is made that night. The remaining suggestions are not written tonight, and the
counts add up to the suggestions. *(FR-240, FR-241, NFR-082)*

**AC-228** — On Reorder, in each of the three languages, a suggestion with an explanation shows
the AI tag and its text in place of the engine's sentence and the shelf-life line. It keeps its
quantity, its "stock count wasn't used" notice, its boost box and its buttons. A suggestion
without one shows the card exactly as before this spec. *(FR-242)*

**AC-229** — The note says what the AI does. With some suggestions unexplained it gives the
published "N of M"; with none explained, that the AI has not explained them; with the capability
unavailable, its reason. With `order_quantity` unavailable there is no note. *(FR-243)*

**AC-230** — The example is built without calling the model. With committed explanations it shows
them. Without them its cards show the engine's sentence and the note says so. Its buttons stay
disabled. *(FR-244)*

**AC-231** — Without a key, nothing is asked or sealed, and `order_explanation` is unavailable
with `no_model_key`. *(FR-240)*

## 16. Assumptions

**ASM-085** — The model's explanation is faithful to the facts it was given. *Falsified if* it
gives a cause the facts do not carry ("it's hot this week"), or states a number in words that
they do not carry. The check catches neither. The prompt forbids both, and the page labels the
text as the AI's. The quantity, not the text, is what the product stands behind (INV-098).

**ASM-086** — A group of 20 suggestions fits one answer of 6,000 tokens within 120 seconds, with
thinking off. *Falsified if* the first nights' manifests show answers cut off (withheld as not
parsing) or timed out. The remedy is a smaller group size, which is policy.

**ASM-087** — The account's rate limits allow four requests at once. *Falsified if* the
manifests show 429s. The remedy is lower concurrency, which is policy.

**ASM-088** — The size of a night is estimated from the monthly reports (CLAUDE.md rule 13). In
July 2026, 565 products sold at least 4 units. Only 59 sold in all seven months. 433 of the 565
have a category, across 25 categories, so about 39 to 46 groups. F8's own test (sold in each of
four weeks) needs daily reports, so the true count is not known until a store sends them.
*Falsified by* the first nights' counts, which replace it.

## 17. Open Questions

**~~OQ-1401~~** — Where does the AI's explanation sit on each card? **Answered 2026-10-09:
"Replace the engine's line"**, choosing between:
- "Under the engine's line (Recommended)";
- "Replace the engine's line": "The AI's sentence becomes the card's only explanation. The
  engine's line comes back only on a night with no AI answer. Less text, but the exact figures
  are then in the AI's words";
- "Behind a 'Why?' button".

FR-242 and FR-238's looser figure check follow from it.

**~~OQ-1402~~** — How does the nightly ask? **Answered 2026-10-09: "One request per department
(Recommended)"**, against "One request per suggestion". He was shown, at ADR-032's prices:
- per department: about 30 requests, about $1.50 a night and $47 a month at the top of the
  range, and about $5 a month at about 60 suggestions;
- per suggestion: about 565 requests, about $3 a night and $95 a month.

The request count was then measured as about 39 to 46 (ASM-088). The cost stands, because it is
mostly the answers' length, not the number of requests. FR-237 follows from it.

**OQ-1403** — Do you approve F14-S1 as written? The choices marked **(decided here)** are:
- the model sees only FR-236's facts (FR-236);
- one request per group of up to 20, four at once, with thinking off (FR-237);
- the checks: the figure check, no percentage or ₪, length, and each language's letters (FR-238);
- sealing and reuse as the shelf explanation's (FR-239);
- a capability of its own (FR-240);
- the limits (FR-241).

**Four values differ from what was said while designing it**, after measuring:

| Value | Said in conversation | Proposed here | Why it changed |
|---|---|---|---|
| Requests a night | 40 | 60 | about 39 to 46 groups at the top of the range, not 30 (ASM-088) |
| Time budget | 360 s | 600 s | at the top of the range the answers total about 113,000 tokens. At an assumed 60 tokens a second for each of four requests, that is about 8 minutes (ADR-045) |
| Request timeout | 90 s | 120 s | a 20-suggestion answer is about 4,000 tokens, about 67 seconds at the same assumed speed |
| Worst-case step time | about 9 minutes | about 14 minutes | follows from the two above (NFR-082) |

Two checks are new: no ₪ or currency name, and each language's own letters. Thinking off is
also new: the conversation did not cover it. · owner: the repository owner · blocks: ADR-045's
acceptance, the mockups and the implementation plan.

**OQ-1404** — Is the account's monthly spending limit set, with its alert, and at what? D-16
makes it a condition of any AI-written reason, and ADR-032 leaves it with the owner, in the
provider's console. It is shared with the boost, the shelf explanation and the shelf reader. ·
owner: the repository owner · blocks: the first night a store's daily sales arrive, not the
build.

## 18. Non-Goals

- An explanation that argues for the quantity beyond its facts. It explains; it does not
  persuade.
- Weather, holidays or busy days as causes (§3, §22).
- Choosing or changing a quantity by AI. F8's rules set it; the AI explains it (INV-098).
- An explanation on Approved orders, in the CSV export or on Today.
- Explanations for products with no quantity. Those keep F8's per-department reasons
  (F8-S1 FR-155).

## 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-EXPL · D-40 | FR-235, FR-236, FR-237, FR-238 | SCN-178, SCN-179 | AC-222, AC-223, AC-224 |
| INT-EXPL · D-16 | FR-239, FR-240, FR-241 | SCN-180, SCN-181, SCN-182, SCN-183, SCN-185 | AC-221, AC-225, AC-226, AC-227, AC-231 |
| INT-EXPL · D-40 | FR-242, FR-243 | SCN-178, SCN-179, SCN-180 | AC-228, AC-229 |
| INT-EXPL · D-29 | FR-244 | SCN-184 | AC-230 |
| Protected behavior | INV-098 | SCN-180 | AC-221 |
| Protected behavior | INV-099 | SCN-185 | AC-225 |
| Protected behavior | INV-100 | SCN-179 | AC-222 |
| Protected behavior | NFR-082 | SCN-182, SCN-183 | AC-227 |

---

## 20. Boundary Probe

CLAUDE.md rule 12. The explanation adds no signal to any quantity, so the probe proves the
opposite: that withholding it moves nothing else, and that it reaches the published artefact only
from a sealed answer.

| Probe | What it would catch | Where it runs |
|---|---|---|
| `npm run check:order-signals` (exists), extended over its fixture world with sealed explanations, then with them withheld | An explanation published from nothing; a quantity or figure that changes without the model's answer (INV-098) | `collect-daily.yml` |
| The same probe, with one sealed explanation's facts changed after sealing | A stale explanation shown beside new facts (INV-099) | `collect-daily.yml` |
| `scripts/check_v1_signals.py`'s `PROBED_ELSEWHERE` guard (exists) | Once `order_explanations` is in any capability's `requires`, `tests/test_check_v1_signals.py` fails until it is listed | CI |

## 21. Claim Limits

| Claim | Verdict | Why |
|---|---|---|
| "The AI's explanation shows the quantity is right" | not measurable | The explanation puts F8's facts into words (FR-235). The quantity's grounds are F8-S1's rules |
| "Explanations make him approve more suggestions" | not measurable | No store sends daily sales (D-23), and no comparison without explanations is planned |
| "Every suggestion is explained" | measured each night | FR-240's counts: N of N, and the states of the rest |
| "No explanation states a figure its facts lack" | measured each night, in digits only | INV-100 and the check. Numbers in words are ASM-085's residual |

## 22. Unmapped PRD Acceptance Lines

None. The PRD's F14 row carries no acceptance line of its own.

#### Intent obligations this spec does not satisfy

- **The intent's example sentence is not said.** «اطلب 24 وحدة — غداً 36 درجة، والخميس ذروة،
  وبقي 12 فقط» needs the weather and the busy weekday, and F8 publishes neither. The intent's
  own constraint, "the explanation adds no figure and no reason", forbids the model from
  supplying them. The owner was told this before he chose (D-40).
- **Success item 1, "N of N on screen", counts the AI's sentences.** On a night with a withheld
  or unasked suggestion, its card still carries a reason, the engine's sentence, but the count
  says it is not the AI's (FR-240, FR-243).
- **"Within a week of the owner using F8's suggestions"** cannot start until a store sends daily
  sales (D-23).
