---
ID: F14-S1
Title: Decision Explanations — the AI's reason beside every order suggestion
Status: Ready for review
Owner: smartshelf-architect
Version: 0.1 (2026-10-10)
Parent: [F14 — Decision Explanations](../intent.md)
Related Intents: INT-EXPL
Inputs: [docs/features/F14-decision-explanations/intent.md, docs/product/PRD.md, docs/product/intent-register.md (D-1, D-3, D-10, D-15, D-16, D-17, D-28, D-29, D-40), docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md (FR-144, FR-147, FR-148, FR-149, FR-154, FR-155, FR-160 … FR-164), docs/reviews/F8-screens-mockups.md, docs/features/F12-planogram/specs/F12-S1-planogram.md (FR-210 … FR-215), ADR-001, ADR-007, ADR-014, ADR-028, ADR-032, ADR-034, ADR-035, ADR-039, ADR-045, CLAUDE.md]
Answered by: [System Design](../../../architecture/system-design.md) §21
Updated: 2026-10-10 (C-79 met: the mockups approved, and the card and note merged as #313)
---

# F14-S1 — Decision Explanations

> **Why this spec exists now.** The repository owner asked for it on 2026-10-09: "yes every
> suggestion should have a ai explanation" (D-40). How the explanation is made was settled on
> 2026-09-24 (D-15 … D-17). While the design was put to him the same day, he chose:
> - **the AI's sentence replaces the engine's sentence on the card** (OQ-1401);
> - **one request per department** (OQ-1402).
>
> He approved the four parts of the design in conversation: what the sentence says, how the
> nightly makes it, what the card shows, and the example and tests. This spec writes them down,
> except what OQ-1403 lists as changed or new since. The largest change is in how numbers reach
> the card. The model writes no number, in digits or in words. It writes named slots, and the page
> fills each one with a phrase that carries the engine's figure and says what it is and when
> ("about 3 left on the order day"). Each choice this spec makes for him is marked
> **(decided here)** and put to him as OQ-1403.
>
> **What he will see, and when.** No store sends daily sales today (D-23), so `order_quantity`
> publishes nothing and neither does this. Until a store does, he sees the explanation only in
> Reorder's marked example (D-29, FR-244).

> **Identifier note.** Every id below is new and globally unique: FR-235 … FR-244, INV-098 …
> INV-101, SCN-178 … SCN-188, NFR-082, NFR-083, C-76 … C-80, AC-221 … AC-237, ASM-085 … ASM-088,
> OQ-1401 … OQ-1404. No existing id is renumbered.

Implements intent F14. Bound by ADR-001, ADR-007, ADR-014, ADR-028, ADR-032, ADR-034, ADR-035,
ADR-039 and ADR-045, and by settled decisions D-1, D-3, D-10, D-15, D-16, D-17, D-28, D-29 and
D-40. It amends what F8-S1 FR-149 and the F8 card mockups put on the card, by OQ-1401 (FR-242).

## 1. Purpose

Every order suggestion F8 publishes carries an explanation, written by the AI in his language,
of why that quantity (D-40). The explanation puts the suggestion's own published facts into
words. On the Reorder card it replaces the engine's sentence, which comes back on any night the
explanation is missing. Every figure in it is the engine's, in a phrase that says what the figure
is and when: the model writes none (FR-238). It never changes a quantity, and it adds no cause the
facts do not carry (D-16).

## 2. Intent Traceability

- **INT-EXPL** — «مع مساعد ذكاء اصطناعي يشرح القرار» (#54). D-15 makes "the decision" the order.
- **D-40** — "yes every suggestion should have a ai explanation" (2026-10-09).
- **D-16** — how an AI-written reason is made: once a night, from published facts, under a paid
  account, a monthly ceiling with an alert, and a mechanical figure check. The intent adds that
  the check is mechanical, «لا بطلبٍ في التعليمات».
- **D-10** — an estimated figure says it is an estimate. The slots' phrases carry "about" and
  "expected" (FR-238).
- **D-3** — no figure where none can be stated. A week with missing reports offers no weekly
  figures (FR-238).
- Serves the PRD's F14 row (V2, with F8, no due date: D-17).

## 3. Scope

Behavioural scope, not a file list. Which files change is declared by the implementation plan.

### In Scope
- **`order_explanation`**, a capability of its own, published nightly beside `order_quantity`.
- **The nightly step that writes it.** It asks the model once per department group, checks each
  suggestion's text, and seals the night's answers.
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
- **The thinking setting of the boost's and the shelf explanation's requests.** They are left as
  they are; ADR-045 names the question.
- **F8's weekly figures over missing report days.** F8 publishes a week's units summed over the
  days it has reports for. That is F8's to word. Here, the weekly figures are offered only over a
  window with every day reported (FR-238).
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
| The owner, who holds the key | Runs the example's builder once with its `--explain` option, so the example's explanations are real answers (FR-244) | Once, and again when the example's inputs or the prompt change |
| A team account | Opens Reorder | Any time; read-only (ADR-029) |

## 5. Domain Terms

| Term | Definition |
|---|---|
| Suggestion | One `order_quantity` entry: a product's quantity for its department's next order day (F8-S1 FR-163). |
| Explanation | The AI's account, in Hebrew, Arabic and English, of why one suggestion's quantity is what it is, written from that suggestion's facts (FR-235). |
| The engine's sentence | The card's text today: "You'll sell about {expected} before your next order…", with its stock clause, and the shelf-life line "Only what sells in {days}, before it spoils." |
| Slot | A named place in the model's text, such as `{left}`, that the page fills with a phrase carrying one published fact and saying what it is and when (FR-238). |
| Group | The suggestions one request asks about: one department's, at most 20 (FR-237). |
| Facts digest | A hash of one suggestion's FR-236 facts with its department's name, and without its id or product name. It says what an explanation was written from (FR-239). |

## 6. Functional Requirements

**FR-235** — Every suggestion carries an explanation, written by a language model, of why its
quantity is what it is (D-40). Where its facts support them, the explanation says:
- how steadily it has sold over the window's weeks;
- when the order is placed, and how many days it covers;
- what stock will be left on the order day, or that it will be gone by then, when the count was
  used;
- where they apply: that the shelf life capped the quantity; that the count could not be used,
  so the quantity does not subtract stock; that the nearby stores ran out of it, and whether the
  market boost raised the expected sales.

It is written once a night, from the suggestion's published facts, and published with it. It is
never written at request time (D-16). Every figure in it is a slot's (FR-238), so an estimate
always reads as one (D-10).

**FR-236** — The model is given only what each suggestion publishes (F8-S1 FR-154)
**(decided here)**:
- its id, which keys the answer, its quantity, and whether it is net or gross. Its product name
  is not sent: it reaches the text only as the `{product}` slot;
- the expected sales for the days the order covers, and, when `{weeks}` is offered, the units
  sold in each of the window's weeks, oldest first;
- how many days the order covers. The order day itself is not sent: its date reaches the text
  only through `{next_order}`;
- whether the count was used. When it was, the stock at the order day when it is above 0.05,
  the card's own threshold, and otherwise that nothing will be left. When it was not, F8's
  reason (F8-S1 FR-149);
- whether the shelf life capped the quantity, and whether the department's products do not
  spoil. The shelf life's days reach the text only through `{capped}`;
- **the market, only when the card shows a boost box:** that is, when the product is in
  `market_running_out`'s published products, as Reorder's boost box requires today. Then, that
  the nearby stores ran out of it, and whether the boost raised the expected sales (applied,
  with a pick above zero), or F8's `not_applied_because` when it did not (F8-S1 FR-147, FR-148).
  Never the boost's `reason`, `pct` or `model_pick_pct`. Without a boost box, nothing about the
  market is sent, and the prompt forbids any statement about it;
- the slots offered for this suggestion, each by its name and what it means, without its figure
  or its phrase (FR-238).

Figures are sent as the card shows them: to one decimal place, halves rounded up, as the page's
own rounding does, not to the nearest even. Each request also carries the department's name.
Nothing else goes in: no barcode, no product name, no date or weekday, no price, cost, margin or ₪
figure (D-1), no stock now, no shelf-life days, and no daily mean. The prompt forbids mentioning
any other suggestion of the group.

**FR-237** — The model is asked once per group **(decided here, within OQ-1402)**:
- one department's suggestions, in the order `order_quantity` publishes them, at most 20 to a
  request, the figure he chose (OQ-1402). A larger department is asked in several groups. The
  policy may set a smaller group; a larger one needs his decision;
- the answer is JSON keyed by suggestion id, each with its Hebrew, Arabic and English text;
- up to 4 requests are in flight at once (policy). The night's request ceiling is counted when a
  request is sent;
- the request turns the model's thinking off, and allows an answer of up to 8,000 tokens. The
  task is wording, not reasoning. The pinned model thinks by default when a request does not say
  otherwise, and thinking is billed as output and counts against the answer's token limit
  (ADR-045).

**FR-238** — The model writes no number. It writes slots, and the page fills each with a phrase
that carries one published fact and says what it is and when **(decided here)**:

| Slot | Filled with (English shown; Hebrew and Arabic say the same) | Offered when |
|---|---|---|
| `{product}` | the product's name | always |
| `{quantity}` | "an order of 35" | always |
| `{expected}` | "about 35 expected to sell in the 7 days from the order day" | always |
| `{weeks}` | "35, 35, 35 and 35 sold in the 4 weeks to 26 Aug", oldest first, with the window's weeks and last day | every day of the window has a report with this product's units known, and every week of the window is 7 days |
| `{next_order}` | "your order on Tuesday 1 Sept, for the 7 days until the next one" | always, and used in every text |
| `{left}` | "about 3 left on the order day" | the count was used, and the stock at the order day is above 0.05 |
| `{runs_out}` | "what you have will be gone by the order day" | the count was used, and the stock at the order day is 0.05 or below |
| `{capped}` | "only what sells in 2 days, before it spoils" | the shelf life capped the quantity |

Figures in the phrases take the card's format: one decimal, halves rounded up, a whole number
without ".0". Days counts and dates take the card's words for them ("7 days", "Tuesday 1 Sept").
`{capped}` is the card's own shelf-life line. Only `{next_order}` names the date, and every text
uses it, so "the order day" in the other phrases always has its date in the same text, once. In
Hebrew and Arabic the phrases say "the order day" in the construct form, יום ההזמנה and يوم
الطلب, never היום or اليوم, which also mean "today". Each phrase names its own period, so a
reader can tell which order and which days each figure belongs to. The phrases' words are
new, in the three languages, and are shown to the owner with the mockups (C-79). Because the
model is sent no product name, and a text may serve another product of the department, the
prompt asks for Hebrew and Arabic wording that does not depend on the product's gender or number
("המכירות של {product}", "مبيعات {product}"). It also asks for "יום ההזמנה" and "يوم الطلب", not
היום and اليوم, when the text itself speaks of the order day. The prompt tells
the model what each slot means and how its phrase reads. A change to a phrase that changes how it
reads in a sentence is a new prompt version, and the page shows a text only under the phrases its
prompt version was written for (FR-242).

Each suggestion's text is checked mechanically, on its own, before anything is published:
- the answer parses. It holds that suggestion's id with all three languages, each non-empty and
  at most 200 characters before the slots are filled;
- every slot in it is one offered for that suggestion, and each appears at most once. Every text
  uses `{product}`, `{expected}` and `{next_order}`. Every offered `{left}`, `{runs_out}` or `{capped}` is used,
  so the card keeps what the engine's sentence and shelf-life line said;
- no product name of the group appears in the text as written, matched as the word lists are.
  The model is not sent the names; this catches one it guesses;
- **the figure check (D-16).** With the slots removed, neither the text as written nor its
  Unicode NFKC form holds a character Unicode classes as a number. That covers every script's
  digits, fractions and numerals;
- **Hebrew letter-numerals.** Before any other normalising, with only the slots replaced by a
  space and invisible format characters and Hebrew vowel points and dagesh removed (U+05B0 to
  U+05BD, U+05BF, U+05C1, U+05C2, U+05C4, U+05C5, U+05C7), a mark directly after a Hebrew letter
  is refused. A mark is any character in the Unicode categories Pi, Pf, Po, Sk or Lm, the Hebrew
  cantillation marks (U+0591 to U+05AF, some of which look like a geresh), and `׳`, `״`, `'`,
  `"`, `′`, `″`, `ʼ`, `ʺ`, `´`, `¨`, `˝` and the backtick. That catches numerals
  written in letters, of one letter (ז׳ is 7) or more (ל״ה and ל”ה are 35), and abbreviations
  and loanwords alike (ש״ח, סה״כ, צ׳יפס). Ordinary punctuation after a word is not a mark here:
  `.`, `,`, `:`, `;`, `!`, `?` and `…` are exempt. The prompt forbids abbreviations and quote
  marks in Hebrew, so the model writes the words out;
- **numbers in words (D-16).** The text is normalised for matching: slots replaced by a space, Unicode NFKC,
  invisible format characters and combining marks removed (Hebrew points, Arabic vowel marks),
  the Arabic stretch character removed, `أ`, `إ`, `آ` and `ٱ` folded to `ا` and nothing else, and
  case folded. It then holds none of the number words in Appendix A. They are matched as whole
  words, after up to two of Hebrew's prefix letters (ו, ה, ב, ל, מ, ש, כ), or after Arabic's
  prefixes: `و` or `ف`, then `ب`, `ك` or `ل`, then `ال`, where `ل` with `ال` is written `لل`. A
  word that starts with `لل` is also tested with `ال` put back (لليوم as اليوم, لليلة as الليلة),
  for the listed words that carry their own article. A closed set of pronoun endings is also
  taken off the end before matching: Hebrew ו, ה, ם, ן, הם, הן, נו, ך, כם, כן; Arabic ه, ها, هم,
  هما, هن, كم, كما, كن, نا, ي, so "חציו" and "نصفها" are caught.
  The lists are loaded through the same normalisation, and a test holds that every listed word
  comes out unchanged. "One" and the ordinals are left to the prompt, because they serve as
  ordinary words too (ASM-085);
- **no relative days.** In the same normalised text, none of Appendix A's relative-day words:
  today, tonight, tomorrow, yesterday and their Hebrew and Arabic forms. A text can be reused on
  a later night (FR-239), and the model is not told the date;
- **no percentage or money (D-1).** In the same normalised text, none of the signs `%` or `٪`,
  no character in the Unicode currency-symbol category (₪, $, €, …), NFKC folding their wide and
  small forms, and none of Appendix A's percentage and currency words;
- with the slots removed, the Hebrew text holds a Hebrew letter, the Arabic text an Arabic
  letter, and the English text a Latin letter.

A failing suggestion's three languages are withheld together, so the languages never disagree.
The rest of its group is unaffected. A suggestion missing from the answer is withheld as
missing. An answer that does not parse withholds its whole group. A withheld text records the
rule and the word that withheld it.

The word lists are a mechanical net for the common ways a number, a relative day, a percentage or
a currency is written in the three languages. They are not a proof that none is written: a form
the lists miss is ASM-085's residual. A form found missing is added to the lists, and the check
runs again on every text before publishing (FR-240), so the addition applies from the next night.
What no check catches is named in ASM-085.

**FR-239** — Each night's explanations are sealed and reproduced as the shelf explanation's are
(ADR-035, ADR-039, ADR-045) **(decided here)**:
- the snapshot records, per suggestion, the model, the prompt's version, the facts digest, and
  the text with its slots unfilled, or why it was withheld;
- the facts digest is over FR-236's facts for that suggestion with its department's name, and
  without its id. No product name is sent, so a text holds none, and may serve another product
  of the same department with the same facts. A text written for one department is never reused
  in another;
- each request's input and output tokens and its stop reason, as the API reports them, are
  recorded in the night's manifest;
- print mode never calls the model. It reads the night's snapshot;
- an explanation whose digest no longer matches its suggestion's facts is not shown. The
  suggestion counts as out of date;
- the prompt's version is the prompt file's hash, as the shelf explanation's is. The engine
  reads the same list of served versions as the page and the example's builder (FR-242,
  FR-244). It does not ask under a prompt the list does not serve: the night's manifest says
  `prompt_not_served`, and the suggestions are not written tonight. The list records, for each
  version, a digest of the phrases it serves. A test holds that the prompt file's hash is on the
  list, and that every listed version's digest equals the current phrases'. So a change to the
  phrases fails the test until someone either confirms each listed version still reads right, or
  takes it off the list. A version taken off the list means its texts are not shown and are
  asked again; for the example, the committed answers are asked again with `--explain`;
- **reuse.** Before asking, the step reads earlier nights' snapshots, newest first. It stops at
  the first night whose step reached its end, meaning a run of that night wrote its end manifest,
  whatever stopped its asking, and never reads more than `order_explanation.reuse_nights` nights
  (proposed 7). With none of them ended, it uses what it read. It reuses the newest accepted
  explanation with the same facts digest, model and prompt version, and copies it into tonight's,
  so each night's snapshot is complete on its own. Unchanged facts are paid for once. A withheld
  explanation is never reused, and a new prompt or model asks again;
- nothing sealed is replaced. A second run the same night asks only for suggestions with no
  record that night. One whose facts changed since its record shows as out of date until the
  next night;
- the night's manifest is written when the step starts and again when it ends. A night that
  started asking is never mistaken for a night with no key.

**FR-240** — `order_explanation` is a capability of its own, `value_policy: none` and not
admitted, because it fails on different days from the quantities (ADR-014) **(decided here)**:
- it runs `order_quantity` first. When that is unavailable, for any reason, including its own
  rule-level ones, so is this, with the same reason;
- it requires `order_quantity`'s inputs and `order_explanations`, the night's sealed snapshot.
  Without a model key the live run asks nothing and seals nothing, so the reason is
  `no_model_key`;
- it publishes, per suggestion, its text in the three languages with the slots unfilled, the
  slots offered for it and the prompt version it was written under, or why it has none: withheld
  (with the check's reason), out of date, or not written tonight. With a text, it also publishes
  the model and the night it was reused from, if any;
- before publishing, it runs FR-238's check again on every text against tonight's offered slots
  and its department group's names. A text that fails it is published as withheld;
- it counts suggestions, explained, withheld, out of date, not written tonight, reused and
  requests made. Explained, withheld, out of date and not written tonight add up to the
  suggestions: the intent's "N of N".

**FR-241** — The step is bounded **(decided here)**:
- spending has ADR-032's two limits. The account's monthly limit and its alert are the owner's,
  set in the provider's console (D-16, OQ-1404). They are shared with the boost, the shelf
  explanation and the shelf reader. A per-night ceiling of requests sits in policy, proposed 60,
  and is counted across the night's runs;
- a time budget, proposed 600 seconds, is checked before each request is sent. It is cut short
  by a deadline the nightly gives the engine, by which this step stops sending, so that the steps
  after the engine still fit in the job's 60 minutes. Those are the probes, the commits and the
  deploy check. The implementation plan sets the deadline from the nightly's measured step times.
  The boost, the shelf explanation and the shelf reader keep their own budgets; this spec does
  not change them;
- a request times out at 120 seconds. A request that fails, after the shared client's one retry
  where it retries, ends the night's asking, as the boost's does. Requests already in flight
  finish, and their answers are checked and kept.

A suggestion past any of these is not written tonight, and says so (FR-240).

**FR-242** — On Reorder, a suggestion with an explanation shows it in place of the engine's
sentence and the shelf-life line, in the page's language, after a tag saying it is the AI's
**(OQ-1401)**:
- the page fills each slot from that suggestion's published facts, as FR-238's table says, and
  isolates each filled slot for direction, as it already isolates the product name and "40%";
- the page fills only the slots published as offered for that suggestion, and shows only a text
  whose prompt version is one its phrases were written for. The versions the phrases serve are
  listed in one place, which the engine, the page and the example's builder all read (FR-239). When the text holds any other slot,
  a slot whose fact is missing, or another prompt version, the page does not show the text. The
  card shows the engine's sentence instead;
- the quantity, the "Your stock count wasn't used" notice, the market boost box and the three
  buttons stay as they are.

A suggestion without an explanation shows the card exactly as F8 shows it today, with no tag and
no per-card reason. This amends, for a suggestion with an explanation, the wording F8-S1 FR-149
records for a gross suggestion (OQ-902) and the card the owner approved in the F8 mockups. Both
stay as the card's sentence whenever there is no explanation.

**FR-243** — Above the suggestions, once, Reorder shows a note:
- what the AI does: it writes each card's explanation from that suggestion's facts, and it
  explains the quantity without changing it;
- when only some of tonight's suggestions have one, how many do, from `order_explanation`'s
  published counts, which include the suggestions he has already approved or dismissed ("Tonight
  the AI explained 28 of 30 suggestions. A card it did not explain shows the engine's
  sentence.");
- when none do, that the AI has not explained tonight's suggestions;
- the counts are the engine's. Between a change to the phrases and the next night, the page may
  hide a text the counts call explained (FR-242); the card then shows the engine's sentence, as
  the note says;
- when `order_explanation` is unavailable, its reason in his words. Without a key, that the AI's
  explanations are off because no key for the model has been set up.

There is no note when there are no suggestions, and none when `order_quantity` is unavailable:
Reorder then shows F8's waiting text (F8-S1 FR-160).

**FR-244** — In Reorder's marked example (D-29), the explanations are real answers for the
example's test shop:
- the engine takes this step's model connection separately from the boost's and the shelf
  explanation's, because one key serves them all today (ADR-045). In the example's publish pass,
  the builder gives neither this step nor the boost a model connection, so neither asks nor
  writes anything; it seals what they read instead (below);
- **the example's boost is a real answer too, or none (decided here).** Today the example's
  boost is a stand-in's fixed answer, labelled as the model's ("the model's estimate"), and an
  explanation would describe a raise no model chose. The same `--explain` run asks the model for
  the example's boost pick first, and then for the explanations, which so see the real pick. The
  pick is committed beside the explanations as `tests/fixtures/order_example/boost_picks.json`.
  Before it reproduces the night, the builder seals into its temporary folder the committed
  pick, or a finished boost manifest with no pick while there is none. The boost box then says
  the model was not asked about it tonight, in its existing words (`reorder.boostNot.no_pick`),
  and the quantity is not raised. The order probe's fixture world keeps its stand-in, which its
  probe needs. This changes F8's example (D-29), and is put to the owner in OQ-1403;
- before it reproduces the night, the builder seals into its own temporary snapshot folder the
  committed answers, or an empty snapshot while there are none. The example carries
  `order_explanation` with the order capabilities it already copies. The builder fails when the
  committed answers' prompt version is not one the page's phrases serve, or when a committed
  answer's or pick's facts digest no longer matches the example's facts, so an edit to the shared
  fixture world never leaves the example quietly out of date. Removing the stale committed file
  is the remedy: the example then shows its cards unexplained, or its boost not asked, until
  `--explain` is run again;
- only its `--explain` option asks, once, with the real key: `python3
  scripts/build_order_example.py --explain`. Its requests use the shared client's stop reason, so
  an answer cut off at its token limit is refused, not sealed. The owner runs it, because he holds the key, and the
  answers are committed as `tests/fixtures/order_example/explanations.json`. This follows the
  Shelf plan example's precedent (`scripts/build_shelf_example.py`);
- until they are committed, the example's cards show the engine's sentence, and the note says the
  AI has not explained them.

The example stays read-only: nothing in it can be approved, changed, saved or sent.

## 7. Behavioral Invariants

**INV-098** — No figure of `order_quantity`, `market_boost` or any other capability comes from the
explanation, and nothing reads its text back. *Violated if* any quantity, expected sales, stock,
entry, id, outcome key or count other than `order_explanation`'s own differs between a run with
the sealed explanations and one without them.

**INV-099** — An explanation is shown only beside the facts it was written from. *Violated if*
one is published for a suggestion whose facts digest differs from the one it recorded.

**INV-100** — Every figure in a shown explanation is a slot's phrase, filled from its own
suggestion's published facts. No published explanation holds a numeral or a listed number word
outside its slots, a slot not offered for its suggestion, a percentage or a ₪ amount (D-1, D-16).
No shown one has a slot without a published fact behind it (D-3), or a prompt version its phrases
do not serve. *Violated if* re-running FR-238's check on any published text fails it, or the page
shows a slot it could not fill.

**INV-101** — The example's explanations never reach a store's data. *Violated if* any is found
under the store's `data/external/snapshots/`, or a store's run reads one (D-29).

## 8. Behavioral Scenarios

**SCN-178** — Given a suggestion for במבה with an accepted explanation sealed for its current
facts, when he opens Reorder in Hebrew, then its card shows the AI tag and the Hebrew text where
the engine's sentence was. Each slot shows its phrase, such as the Hebrew for "about 35 expected
to sell in the 7 days from the order day". The quantity, the buttons and any boost box are
unchanged.

**SCN-179** — Given a group of six suggestions, where the model's text for one holds the digits
"40" or the word "forty", when the step checks the answer, then that one is withheld as stating a
figure, and its card shows the engine's sentence. The other five are shown, and the note says the
AI explained 5 of tonight's 6 suggestions.

**SCN-180** — Given no model key, when the nightly runs, then no request is made,
`order_explanation` is unavailable with `no_model_key`, every card shows the engine's sentence,
and the note says the AI's explanations are off. Every quantity equals a run without the step.

**SCN-181** — Given a suggestion whose facts are unchanged since last night's accepted
explanation, when the step runs, then no request is made for it, and tonight's snapshot copies
the explanation, naming last night as where it came from.

**SCN-182** — Given more groups than the night's request ceiling allows, or a time budget or the
nightly's deadline spent, when the step stops sending, then the remaining suggestions are not
written tonight. Their cards show the engine's sentence, and the counts say how many.

**SCN-183** — Given a request that fails, when the step continues, then it sends nothing more
that night. Answers already in flight are checked and kept, and every suggestion not asked is not
written tonight.

**SCN-184** — Given the example before its explanations and boost pick are committed, when he
opens "See how this page looks", then every card shows the engine's sentence, the note says the
AI has not explained them, and the מים card's boost box says the model was not asked about it
tonight, with its quantity not raised. Nothing can be approved.

**SCN-188** — Given a prompt edited without its hash added to the served-versions list, when the
nightly runs, then the step asks nothing, the manifest says `prompt_not_served`, and every card
shows the engine's sentence.

**SCN-185** — Given an explanation sealed before a late report changed its suggestion's facts,
when print mode reproduces the night, then that explanation is not shown, the suggestion counts
as out of date, and its card shows the engine's sentence.

**SCN-186** — Given a capped suggestion whose texts never use `{capped}`, when the step checks
the answer, then it is withheld, and its card shows the engine's sentence with its shelf-life
line.

**SCN-187** — Given a window in which three days have no report, when the step asks, then no
suggestion is sent weekly figures or offered `{weeks}`, and a text using `{weeks}` is withheld.

## 9. Inputs and Observable Outputs

| Input | Source | Required? |
|---|---|---|
| `order_quantity`'s published suggestions and their facts | The night's run (F8-S1 FR-154) | Yes. Without them, so is this unavailable, with their reason |
| `market_running_out`'s published products | The night's run | No. Without it, nothing about the market is sent (FR-236) |
| The night's explanations | The model's answers, checked and sealed under `data/external/snapshots/` (ADR-045) | Yes. Without them, `no_model_key` |
| The prompt | A versioned file under `configs/prompts/` (ADR-045) | Yes |
| The policy's values | `order_explanation` in `configs/policy.yaml` (FR-237, FR-238, FR-241) | Yes |
| The nightly's deadline | Given to the engine by the nightly (FR-241) | No. Without it, the step's own budget applies |

| Output | Where it is observable |
|---|---|
| `order_explanation`: per suggestion, its text in three languages with the slots unfilled, its offered slots and prompt version, or why it has none; the counts (FR-240) | `dashboard.json`; the Reorder page, slots filled |
| The night's sealed snapshot, with the requests made, their tokens and stop reasons, and whether the step reached its end | `data/external/snapshots/<night>/order_explanations/` |
| The example's explanations (FR-244) | `tests/fixtures/order_example/explanations.json`; the example's preview |

## 10. State / Lifecycle Semantics

- **The explanation is written once a night and kept.** The snapshot is committed by the
  nightly's existing step for sealed answers (CLAUDE.md rule 9). Nothing in it is replaced; a
  second run that night only adds (FR-239).
- **Recomputed each run:** which sealed explanation matches which suggestion, by digest, and the
  check, again, before publishing (FR-240).
- **Filled at render:** the slots, from the suggestion's published facts. Nothing new is
  computed; the page formats published fields in phrases (ADR-001).
- **Never stored:** anything at request time. Nothing is written to owner state, and the
  explanation does not touch a suggestion's id or outcome key (ADR-034, INV-098).
- **A suggestion's explanation follows its facts, not its id.** The id is the same every night
  until the order day (ADR-034). When its facts change, a new explanation is asked for the next
  night. When they do not, the old one is reused (FR-239).

## 11. Failure and Recovery Behavior

| Condition | Behaviour |
|---|---|
| No model key | Nothing is asked or sealed. `order_explanation` is unavailable (`no_model_key`). Every card shows the engine's sentence |
| `order_quantity` unavailable | So is `order_explanation`, with the same reason. Reorder waits as F8 does |
| An answer does not parse, or misses a suggestion | That group, or that suggestion, is withheld. Its cards show the engine's sentence. It is asked again the next night |
| A text fails the check | That suggestion is withheld, with the check's reason. The rest of its group is shown |
| Ceiling reached, time budget or the nightly's deadline spent, or a request failed | The suggestions not asked are not written tonight (FR-241) |
| The job stops partway | The manifest written at the start says the step began. What was sealed stands; the rest is not written tonight. The next night reuses from what was sealed (FR-239) |
| A sealed explanation's digest no longer matches | Not shown; out of date (INV-099) |
| A shown text has a slot the page cannot fill, or a prompt version its phrases do not serve | The card shows the engine's sentence (FR-242) |
| `order_quantity` is available with no suggestions | `order_explanation` is available with every count at zero. That is a result, not a failure: there is nothing to explain. No note is shown |

Nothing here is an empty result standing in for a failure (CLAUDE.md rule 10): every suggestion
is counted in exactly one of FR-240's four states.

## 12. Edge Cases

| Case | Behaviour |
|---|---|
| A product name holds digits or "%" ("קוקה קולה 1.5", "חלב 3%") | The name reaches the text only through `{product}`, which is removed before the checks and isolated for direction when filled |
| A text writes a product's name instead of `{product}`, or names another product of its group | Withheld. Names are matched as whole words, so "מים" is not found inside "ימים" |
| The model writes a number anyway ("35", "３５", "½", "٣٥", "Ⅻ") | Withheld. The raw text and its NFKC form are both checked against the Unicode number classes |
| The model writes a number in words ("four weeks", "חצי", "أسبوعين", "ובשלושת", "ثلاثةَ", "ثلاثـة") | Withheld, for every word and form in Appendix A, with its prefixes, vowel marks or stretching removed. "One" and the ordinals are not on it (ASM-085) |
| A Hebrew numeral in letters ("ז׳", "ל״ה", "ל”ה", "ל´´ה") or an abbreviation ("ת״א", "סה״כ") | Withheld: a mark straight after a Hebrew letter is refused, before NFKC can turn it into something else. The prompt asks for words written out |
| "لليوم", "لليلة" | Withheld: a word starting with `لل` is also tested with `ال` put back |
| "חציו", "نصفها", "שלושתם" | Withheld: pronoun endings are taken off before matching |
| "משקל", "במשקל" (weight) | Withheld, a safe false positive: it holds שקל. The prompt asks for other words |
| "لليومين", "للثلاثة" | Withheld: `لل` is matched as `ل` with `ال` |
| "מצד שני", "השני", "لست بحاجة" | Allowed: שני and the bare ست are not on the list, because they serve as ordinary words |
| A weekday the model was not sent ("Thursday", "الخميس") | Not caught: an invented fact is ASM-085's residual. The prompt forbids naming days; `{next_order}` names the order day |
| "Tomorrow", "מחר", "غداً" | Withheld: the model is not told the date, and the text may be reused on a later night |
| "לפי", "כפי", "על פי" | Allowed: פי is not on the list, because a multiple needs a number word that is |
| A slot not offered (`{left}` on a gross suggestion), or used twice | Withheld |
| "ש״ח", "ש''ח" or "％" after a slot | Withheld: the gershayim is refused, and the text is NFKC-normalised before the signs are matched |
| A window with a day unreported, or a week shorter than 7 days | `{weeks}` is not offered, and no weekly figures are sent (SCN-187) |
| Stock at the order day of 0.05 or less | `{left}` is not offered; `{runs_out}` is, and must be used, as the card says it today |
| A department whose products do not spoil | `{capped}` is never offered; the model is told they do not spoil |
| A capped suggestion | Its texts must use `{capped}`, the card's own line, or it is withheld (SCN-186) |
| A product that no nearby store has run out of | No boost box on the card, and nothing about the market is sent; the prompt forbids market statements |
| A boost applied with a pick of 0% | The model is told the boost did not raise the expected sales, so the text does not say it did |
| A department with 45 suggestions | Three groups: 20, 20 and 5 |
| The boost applied | The explanation may say the nearby stores ran out. It has no slot for the boost's percentage, which stays in the boost box with its "the model's estimate" label (D-10) |
| A suggestion approved or dismissed earlier | It is not on the page (F8-S1 FR-163). The note's counts are tonight's published suggestions |

## 13. Non-Functional Requirements

**NFR-082** — The step never holds the night's artefact up **(decided here)**. Its requests are
bounded by the policy's ceiling, its time by its own budget and by the nightly's deadline,
checked before each request is sent, and each request by its timeout (FR-241). It ends
within about 600 + 241 seconds: the budget, plus a request sent just before it ran out that timed
out and was retried, and never later than about 241 seconds after the nightly's deadline. The
other model steps keep their own budgets. The implementation plan states the nightly's combined
worst case against its 60 minutes; if it does not fit, that is a decision for F8 and F12, not
taken here. Each night it
publishes the requests made and how many explanations were reused.

**NFR-083** — Its cost is estimated before it is switched on, and counts under ADR-032's monthly
limit. ADR-045 gives the estimate: about $5 a month at about 60 suggestions a night, and about $36
a month at about 435, if every suggestion's facts change nightly. The tokens recorded in each
night's manifest (FR-239) replace the estimate's assumptions.

## 14. Compatibility and External Constraints

**C-76** — There is no service running at request time (ADR-007), so the explanation is written
by the nightly or not at all.

**C-77** — The page renders published fields and computes nothing (ADR-001). The note's counts
are `order_explanation`'s published counts. The slots are published fields formatted in phrases,
with the card's own number and date formats.

**C-78** — CI commits only `data/external/snapshots/` (CLAUDE.md rule 9). The nightly's sealed
explanations live there. The example's are committed by hand (FR-244).

**C-79** — Front-end work waits for the owner's approval of its mockups (2026-09-16). The card,
the slots' phrases and the note are built only after he approves screenshots of the example in
Hebrew, Arabic and English, on desktop and phone. *(Met 2026-10-10: he approved the mockups drawn on this spec's phrases, "it
is good merge and push" ([docs/reviews/F14-screens-mockups.md](../../../reviews/F14-screens-mockups.md)),
and the card and the note were merged as #313, before this spec's own approval (OQ-1403). They
show nothing until the engine publishes `order_explanation`. The merged page keeps the list of
served prompt versions as a constant holding only the mockups' sample version; the one shared
list of FR-239 and FR-242 replaces it when the engine's side is built. A change he makes to this
spec through OQ-1403 changes the merged card with it.)*

**C-80** — One store per copy (D-28). The prompt is product text: it names no store, and nothing
in it is a store's setting.

## 15. Acceptance Criteria

**AC-221** — Withholding the sealed explanations leaves every quantity, figure, entry, id and
outcome key of `order_quantity` and `market_boost` unchanged. Each suggestion then says it has no
explanation, and why. *(FR-240, INV-098)*

**AC-222** — The check, run on fixed answers:
- passes a text whose only figures are offered slots, each used once, with `{product}`,
  `{expected}`, `{next_order}` and every offered `{left}`, `{runs_out}` or `{capped}`, where the product's name
  holds digits or "%";
- withholds a text with a numeral of any script outside its slots, Roman numerals included;
- withholds one with a number word from Appendix A in any of the three languages, in each of its
  listed forms, including a dual, with stacked prefixes ("ובשלושה", "وبالثلاثة"), with Arabic
  vowel marks or stretching, or split by an invisible character;
- withholds one with a mark straight after a Hebrew letter ("ז׳ ימים", "ל״ה", "ל”ה", "ל’",
  "ל´´ה", "לʺה"), and one with a relative day ("tomorrow", "מחר", "غداً", "لليوم", "لليلة");
- withholds a number word with a pronoun ending ("חציו", "نصفها");
- withholds "لليومين" and "للأسبوعين", and passes "מצד שני", "لست" and a Hebrew word followed by
  a full stop or comma;
- withholds one without `{next_order}`;
- passes one with "לפי", "כפי" or "על פי";
- withholds one with a slot not offered, a slot used twice, or a required slot missing;
- withholds one with a product's name written out, but not one whose word only contains a name
  ("ימים" against "מים");
- withholds one with `%`, `٪`, `％`, `₪`, a percentage word, or a currency name, including "ש״ח",
  "ש''ח" and "שקלים";
- withholds one over 200 characters, one missing a language, and a text without its own
  language's letters once its slots are removed.

Only the failing suggestion is withheld, in all three languages. *(FR-238, INV-100)*

**AC-223** — The request built for a group carries only FR-236's facts and the department's
name, figures to one decimal with halves rounded up. It carries no barcode, product name, date,
weekday, price, cost, margin, ₪ figure, stock now, shelf-life days, boost reason, boost
percentage, model pick, daily mean or slot phrase. It carries no weekly figures when `{weeks}` is not offered, and nothing about the market
for a product without a boost box. A boost applied at 0% is sent as not raising the expected
sales. It turns thinking off. *(FR-236, FR-237)*

**AC-224** — Groups are one department's suggestions in published order, at most 20. An answer
missing a suggestion withholds that one. An answer that does not parse withholds its group only.
*(FR-237, FR-238)*

**AC-225** — Print mode never calls the model, and reproduces the published explanations from the
snapshot. An explanation whose facts digest no longer matches is not shown. *(FR-239, INV-099)*

**AC-226** — A suggestion whose facts, department, model and prompt match an accepted explanation
from the nights read back is not asked, and tonight's snapshot copies it with where it came from.
The step reads back to the first night that reached its end, and never more than `reuse_nights`.
A text written for one department is not reused in another. A withheld one is asked again. A
second run the same night replaces no sealed record. *(FR-239)*

**AC-227** — Past the request ceiling, the time budget or the nightly's deadline, or after a
request fails, no further request is sent that night. Answers already in flight are kept. The
remaining suggestions are not written tonight, and the counts add up to the suggestions.
*(FR-240, FR-241, NFR-082)*

**AC-228** — On Reorder, in each of the three languages, a suggestion with an explanation shows
the AI tag and its text in place of the engine's sentence and the shelf-life line, each slot
filled with its phrase as FR-238's table says. The card keeps its quantity, its "stock count
wasn't used" notice, its boost box and its buttons. A suggestion without an explanation, or whose
text has a slot not published as offered, a slot without its fact, or a prompt version the
page's phrases do not serve, shows the card exactly as before this spec.
*(FR-238, FR-240, FR-242, INV-100)*

**AC-229** — The note says what the AI does. With some suggestions unexplained it gives the
published "N of M"; with none explained, that the AI has not explained them; with the capability
unavailable, its reason. There is no note with no suggestions, or with `order_quantity`
unavailable. *(FR-243)*

**AC-230** — The example is built with the step's asking switched off and no model called. With
committed explanations it shows them. Without them its cards show the engine's sentence and the
note says so. Its buttons stay disabled. The build fails on committed explanations whose prompt
version the page's phrases do not serve. *(FR-244)*

**AC-231** — Without a key, nothing is asked or sealed, and `order_explanation` is unavailable
with `no_model_key`. *(FR-240)*

**AC-232** — Building the example writes nothing under the store's `data/external/snapshots/`,
and a store's run reads nothing from `tests/fixtures/order_example/`. *(FR-244, INV-101)*

**AC-233** — A run that stops after its first request still leaves a manifest saying the step
began, so print mode does not say `no_model_key`. *(FR-239)*

**AC-234** — Each night's manifest records every request's input and output tokens and its stop
reason as the API reported them. *(FR-239, NFR-083)*

**AC-235** — In the English text on a right-to-left page, and in the Hebrew and Arabic texts, a
filled slot holding a product name with digits ("קוקה קולה 1.5") or a figure keeps its figure in
its own place, and `{weeks}` lists the weeks oldest first, read in each language's own
direction. *(FR-242)*

**AC-236** — A text using `{expected}`, `{next_order}` and `{left}` together, filled for the
example's קולה, reads in each language with the expected sales as expected over the days from the
order day, the order as the one on that day, and the stock left as on that day. The date appears
once, in `{next_order}`. *(FR-238)*

**AC-237** — The example's builder seals the committed boost pick, or a finished boost manifest
with no pick, into its own temporary folder. With no committed pick, the מים card's boost box
says the model was not asked about it tonight and its quantity is not raised. The builder fails
when a committed answer's or pick's facts digest no longer matches the example's facts, or the
committed answers' prompt version is not served; removing the stale file lets it build.
*(FR-244, SCN-184)*

## 16. Assumptions

**ASM-085** — The model's explanation is faithful to the facts it was given. *Falsified if* it
gives a cause the facts do not carry ("it's hot this week"), states a number with a word the list
leaves out ("one", "the second week", a misspelling), uses a relative time the list leaves out
("this week", "next week"), names a weekday it was not sent, gets a Hebrew or Arabic agreement wrong around `{product}`, or
turns a slot around with a negation or a comparison ("you won't
have {left}"). No check catches these. A slot put in an odd place does not change
what its phrase says, because each phrase names its figure and its period, but the sentence can
read oddly. The prompt forbids all of them, and the page labels the text as the AI's. The figures
in the slots are always the engine's, and the quantity, not the text, is what the product stands
behind (INV-098).

**ASM-086** — A group of 20 suggestions fits one answer of 8,000 tokens within 120 seconds, with
thinking off. *Falsified if* the first nights' manifests show answers cut off (a `max_tokens`
stop reason) or timed out. The remedy is a smaller group, which is policy.

**ASM-087** — The account's rate limits allow four requests at once. *Falsified if* the
manifests show 429s. The remedy is fewer at once, which is policy.

**ASM-088** — The size of a night is estimated from the monthly reports (CLAUDE.md rule 13).
- In July 2026, 565 products sold at least 4 units (`sales_monthly.parquet`). Only 59 sold in all
  seven months.
- 435 of the 565 have a department in `public/data/catalogue.json`, matching barcodes with leading
  zeros removed as the engine does, across 25 departments. That is 39 groups of at most 20. The
  other 130 are not in the catalogue, so F8 cannot suggest them.
- F8's own test, sold in each of four weeks, needs daily reports, so the true count is not known
  until a store sends them.

*Falsified by* the first nights' counts, which replace it.

## 17. Open Questions

**~~OQ-1401~~** — Where does the AI's explanation sit on each card? **Answered 2026-10-09:
"Replace the engine's line"**, choosing between:
- "Under the engine's line (Recommended)": "Keep today's "You'll sell about 35…" line, which is
  always there and always exact. Add the AI's "why" beneath it, marked as AI-written. A night
  without an answer loses nothing."
- "Replace the engine's line": "The AI's sentence becomes the card's only explanation. The
  engine's line comes back only on a night with no AI answer. Less text, but the exact figures
  are then in the AI's words."
- "Behind a "Why?" button": "The card stays as it is today. A "Why this quantity?" button opens
  the AI's sentence. Cleanest card, but you have to press to read it."

FR-242 and FR-238 follow from it.

**~~OQ-1402~~** — How does the nightly ask? **Answered 2026-10-09: "One request per department
(Recommended)"**. The options were, verbatim:
- "One request per department (Recommended)": "One request covers up to ~20 suggestions in a
  department, and each sentence is checked on its own. An explanation is reused while its facts
  don't change, and a few requests run at once. At the top of the range: about 30 requests,
  ~$1.50 a night, ~$47 a month, around 5 minutes. At about 60 suggestions it's ~$5 a month. One
  bad answer can cost a whole group its sentences that night (they fall back to the engine's
  line)."
- "One request per suggestion": "Each suggestion gets its own request, the way the market boost
  works today. A failure only affects that one card. At the top of the range: about 565
  requests, ~$3 a night, ~$95 a month, around 45 minutes unless many run at once, which risks
  the model's rate limits. It would need a much higher nightly request limit."

FR-237 follows from it. The top of the range has since been re-estimated (ASM-088), and OQ-1403
shows what that changes.

**OQ-1403** — Do you approve F14-S1 as written? It asks for the choices marked
**(decided here)**, and for the changes since the conversation below.

**What changed from what you were shown:**

| | Shown in conversation | Proposed here | Why |
|---|---|---|---|
| How numbers reach the card | The AI writes them, and a check keeps only numbers from the suggestion's facts | The AI writes slots, and the page fills each with a phrase that carries the card's own figure and says what it is and when ("about 3 left on the order day") | A check on values passes a true number in the wrong place: "you'll sell about 12, and 35 will be left", with the stock and the sales swapped. A slot's phrase names its figure and its period, so a slot in an odd place reads oddly, not wrongly. Every figure is the engine's, and an estimate always says "about" and "expected" (D-10) |
| Numbers written in words | caught only by the prompt | the number words of Appendix A, in all their listed forms, and Hebrew letter-numerals, refused mechanically | the intent wants the figure check mechanical, «لا بطلبٍ في التعليمات». "One" and the ordinals stay with the prompt |
| Stock now | allowed, as one of the numbers the sentence may state | not sent, and no slot | the engine's figure is the stock at the start of the run day, and the card never showed it. Read later in the day, "now" would be wrong |
| Weekly figures | always, as "the weekly sales" | only when every day of the window has a report | F8 sums a week over the days it has reports for, so a week with missing reports would read as a slump (D-3) |
| The market | "nearby stores have run out" where it applies | only for a card that shows the boost box | for any other product, the engine knows nothing about the market worth saying |
| What is withheld when a text fails | "only that sentence" | that suggestion's text in all three languages | the languages never disagree. The rest of the group is unaffected |
| Top of the range | about 565 suggestions, about 30 requests | about 435 suggestions, about 39 requests | 130 of the 565 are not in the catalogue (ASM-088) |
| Cost at the top of the range | about $47 a month | about $36 a month | the same 130 |
| Requests a night, the ceiling | 40 | 60 | about 39 groups at the top of the range, plus margin. If every group were full up to the ceiling, the most it could cost is about $95 a month at 60, against about $64 at 40. At the assumed speed the time budget stops the step before the ceiling is reached |
| Time budget | 360 s | 600 s, cut short by the nightly's deadline | the answers at the top of the range total about 87,000 tokens. At an assumed 60 tokens a second for each of four requests, that is about 6 minutes. The deadline keeps the nightly's later steps inside its 60 minutes |
| Step time at the top of the range | around 5 minutes | about 6 minutes | as above |
| Request timeout | 90 s | 120 s | a 20-suggestion answer is about 4,000 tokens, about 67 seconds at the same assumed speed |
| Worst-case step time | about 9 minutes | about 14 minutes, or less by the deadline | follows from the two above (NFR-082) |

**What is new, not covered in conversation:**
- thinking turned off, and an answer limit of 8,000 tokens (FR-237);
- the slots' phrases, which you will see in the mockups; the product's name as a slot; each slot
  at most once; `{product}`, `{expected}` and `{next_order}` in every text, and the card's own stock and
  shelf-life sentences whenever they apply (`{left}` or `{runs_out}`, `{capped}`);
- a boost applied at 0% is not described as raising anything;
- the checks for percentage and currency words, relative days ("tomorrow"), Hebrew
  abbreviations with gershayim, and each language's own letters (FR-238);
- the model is not sent the product's name, the order day's date or weekday, or the shelf life's
  days; slots carry them;
- the daily rate is not sent: it was in the list of facts F8 publishes, not in the numbers the
  sentence may state;
- reuse from earlier nights back to the first that reached its end, at most 7, matched by a
  digest of the facts and the department, without the suggestion's id, so a new order day with
  the same facts reuses the old text (FR-239);
- a text is shown only under the phrases its prompt was written for (FR-242);
- the nightly's deadline applies to this step only; the boost and the shelf keep their budgets
  (FR-241);
- the example's boost: the same `--explain` run asks the model for one real pick. Until then the
  example's boost box says the model was not asked about it tonight, and its quantity is not
  raised: the מים order goes from 23 to 21. This replaces the stand-in's fixed answer the example
  shows today as "the model's estimate" (FR-244), and changes F8's example (D-29):
  - the approved example (2026-10-03) showed "a suggestion the market boost raised". It will show
    none until a key is set (OQ-1404) and `--explain` is run, and none at all if the real pick is
    0% or rejected. `tests/test_order_example.py`'s check for a raised suggestion changes with it;
  - the other choice is to keep the stand-in, labelled in the example as a test answer, not the
    model's. That needs new wording on the card;
- only `{next_order}` names the date, once per text; the other phrases say "the order day"
  (FR-238), as the mockups showed the date three times in one text otherwise;
- the word lists are a net for the common forms, not a proof; a missed form is added when found
  (FR-238). Review rounds 4 to 7 kept finding new forms the net missed, in three languages.
  Each was added, and more will be found. The guarantee that holds is the one for numerals in
  any script. Numbers in words rest on the prompt, with the net behind it, as they do for the
  Shelf plan's explanation, which you approved with the same residual (F12-S1 FR-212, OQ-1209);
- the note's wording: "Tonight the AI explained 28 of 30 suggestions. A card it did not explain
  shows the engine's sentence." The counts include suggestions already approved or dismissed,
  which the page hides (FR-243);
- the engine gives this step its own model connection, so the example can build without asking
  (FR-244).

· owner: the repository owner · blocks: ADR-045's acceptance, the mockups and the implementation
plan.

**OQ-1404** — The model key is not set, and the monthly spending limit is not known. On
2026-10-10:
- the repository has no `ANTHROPIC_API_KEY` secret (`gh secret list`), which the nightly reads
  (`collect-daily.yml`);
- tonight's artefact says `no_boost_key` and `no_model_key`.

No AI step has run in the nightly. D-16 makes a paid account, with a monthly spending limit and
its alert, a condition of any AI-written reason, and ADR-032 leaves them with the owner, in the
provider's console. They are shared with the boost, the shelf explanation and the shelf reader.
Is the key to be set, and with what monthly limit? · owner: the repository owner · blocks: the
first night a store's daily sales arrive, and the example's `--explain` run, not the build.

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
| INT-EXPL · D-40 | FR-235, FR-236, FR-237, FR-238 | SCN-178, SCN-179, SCN-186, SCN-187 | AC-222, AC-223, AC-224, AC-236 |
| INT-EXPL · D-16 | FR-239, FR-240, FR-241 | SCN-180, SCN-181, SCN-182, SCN-183, SCN-185, SCN-188 | AC-221, AC-225, AC-226, AC-227, AC-231, AC-233, AC-234 |
| INT-EXPL · D-40 | FR-242, FR-243 | SCN-178, SCN-179, SCN-180 | AC-228, AC-229, AC-235 |
| INT-EXPL · D-29 | FR-244 | SCN-184 | AC-230, AC-232, AC-237 |
| Protected behavior | INV-098 | SCN-180 | AC-221 |
| Protected behavior | INV-099 | SCN-185 | AC-225 |
| Protected behavior | INV-100 | SCN-179, SCN-186, SCN-187 | AC-222, AC-228 |
| Protected behavior | INV-101 | SCN-184 | AC-232 |
| Protected behavior | NFR-082 | SCN-182, SCN-183 | AC-227 |
| Protected behavior | NFR-083 | — | AC-234 |

---

## 20. Boundary Probe

CLAUDE.md rule 12. The explanation adds no signal to any quantity, so the probe proves the
opposite: that withholding it moves nothing else, that it reaches the published artefact only
from a sealed answer that passes the check, and that it goes out of date when any of its facts
change.

| Probe | What it would catch | Where it runs |
|---|---|---|
| `npm run check:order-signals` (exists), extended over its fixture world with sealed explanations, then with them withheld | An explanation published from nothing; a quantity or figure that changes without the model's answer (INV-098) | `collect-daily.yml` |
| The same probe, sealing stand-in answers that hold a typed number, a Roman numeral, a number word, a stray "%", "ש״ח", a slot not offered, a product name written out, and a capped text without `{capped}`. It reads the artefact, and scans every published text with a check written apart from FR-238's: any character classed as a number outside a `{…}` slot fails | A failing answer published, or a hole in the check itself (INV-100) | `collect-daily.yml` |
| The same probe, changing one source at a time for each FR-236 fact: a daily report, a day's report removed, the count, the shelf life, the schedule, the boost's pick, the market snapshots, the product's department | A stale explanation shown beside new facts, or a fact left out of the digest (INV-099) | `collect-daily.yml` |
| `scripts/check_v1_signals.py`'s `PROBED_ELSEWHERE` guard (exists) | Once `order_explanations` is in any capability's `requires`, `tests/test_check_v1_signals.py` fails until it is listed. Listing it also needs the probe's own word for it in that test | CI |

## 21. Claim Limits

| Claim | Verdict | Why |
|---|---|---|
| "The AI's explanation shows the quantity is right" | not measurable | The explanation puts F8's facts into words (FR-235). The quantity's grounds are F8-S1's rules |
| "Explanations make him approve more suggestions" | not measurable | No store sends daily sales (D-23), and no comparison without explanations is planned |
| "Every suggestion is explained" | measured each night | FR-240's counts: N of N, and the states of the rest |
| "No explanation holds a numeral of any script outside its slots" | measured each night | INV-100, re-checked at publish (FR-240) |
| "No explanation holds a Hebrew letter-numeral, or a number word from Appendix A in its listed forms" | measured each night, as a net | The net catches the listed forms; forms it misses are ASM-085's residual, added when found |
| "Every figure in an explanation is the engine's, and says what it is" | not measurable as a whole | Each slot's phrase names its figure and period, but "one", an ordinal, a negation or a comparison around a slot is not read by any check (ASM-085) |
| "No explanation gives a cause its facts lack" | not measurable | ASM-085. The prompt forbids it; no check reads causes |

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
- **Success item 2's mechanical check reads digits, numerals and listed number words.** "One",
  the ordinals, and a negation or comparison around a slot are left to the prompt (ASM-085).
- **"Within a week of the owner using F8's suggestions"** cannot start until a store sends daily
  sales (D-23).

## 23. Appendix A — The check's word lists

FR-238 matches these after normalising: slots removed, NFKC, invisible format characters and
combining marks removed, the Arabic stretch character removed, Arabic alef and hamza forms
folded to plain alef, and case folded. Each is matched as a whole word, after up to two Hebrew
prefix letters (ו, ה, ב, ל, מ, ש, כ), or Arabic's و or ف, then ب, ل or ك, then ال, where ل with
ال is written لل, and a word starting with لل is also tested with ال put back. The pronoun endings
of FR-238 are taken off the end. The Arabic words are listed folded. **(decided here)**

**Number words.** Two upward, fractions and multiples, with the forms listed.

| | English | Hebrew | Arabic |
|---|---|---|---|
| 2 to 10 | two, three, four, five, six, seven, eight, nine, ten | שניים, שתיים, שתים, שתי, שלש, ששה, חמשה, שלושה, שלוש, שלושת, ארבעה, ארבע, ארבעת, חמישה, חמש, חמשת, שישה, שש, ששת, שבעה, שבע, שבעת, שמונה, שמונת, תשעה, תשע, תשעת, עשרה, עשר, עשרת | اثنان, اثنين, اثنتان, اثنتين, ثلاثه, ثلاثة, ثلاث, اربعه, اربعة, اربع, خمسه, خمسة, خمس, سته, ستة, سبعه, سبعة, سبع, ثمانيه, ثمانية, ثماني, ثمان, تسعه, تسعة, تسع, عشره, عشرة, عشر |
| 11 to 19 | eleven, twelve, thirteen, fourteen, fifteen, sixteen, seventeen, eighteen, nineteen | caught by עשר, עשרה | caught by عشر, عشرة |
| Tens | twenty, thirty, forty, fifty, sixty, seventy, eighty, ninety | עשרים, שלושים, שלשים, ארבעים, חמישים, חמשים, שישים, ששים, שבעים, שמונים, תשעים | عشرون, عشرين, ثلاثون, ثلاثين, اربعون, اربعين, خمسون, خمسين, ستون, ستين, سبعون, سبعين, ثمانون, ثمانين, تسعون, تسعين |
| Zero, tens, hundreds, thousands, millions | zero, tens, hundred, hundreds, thousand, thousands, million, millions | אפס, עשרות, מאה, מאות, מאתיים, אלף, אלפים, אלפיים, מיליון, מליון | صفر, عشرات, مئه, مئة, مائه, مائة, مئات, مئتين, مئتان, مائتين, مائتان, مئتا, مئتي, ثلاثمئة, اربعمئة, خمسمئة, ستمئة, سبعمئة, ثمانمئة, تسعمئة, ثلاثمائة, اربعمائة, خمسمائة, ستمائة, سبعمائة, ثمانمائة, تسعمائة, الف, الاف, الفين, مليون |
| Fractions | half, halves, halved, halving, quarter, quarters, third, thirds | חצי, מחצית, רבע, שליש | نصف, ربع, ثلث |
| Multiples | double, doubled, doubles, doubling, twice, triple, tripled, triples, thrice, dozen, dozens, couple, pair, both, fortnight | שניהם, שתיהן, כפול, כפולה, כפליים, פעמיים, הוכפל, הוכפלה, הוכפלו, יוכפל, הכפיל, הכפילו, תריסר, תריסרים, זוג | كلا, كلاهما, كلتا, كلتاهما, ضعفين, ضعفان, ضعفي, ضعفا, مضاعف, تضاعف, تضاعفت, يتضاعف, تتضاعف, سيتضاعف, مرتين, مرتان, زوج, دزينه, دزينة, دسته, دستة |
| Duals | — | יומיים, שבועיים, חודשיים, שנתיים | يومين, يومان, اسبوعين, اسبوعان, شهرين, شهران |

Not listed, because they serve as ordinary words: "one", אחד, אחת, واحد, واحدة, احد (also
"anyone", and Sunday as الاحد); the ordinals; Hebrew's שני (also "second" and "other", as in
מצד שני); Arabic's bare ست (as in لست). שתיה and שתייה (drink) are never matched as שתי with an
ending;
Hebrew's פי (as in לפי, כפי, על פי); Arabic's bare ضعف, which also means weakness.

**Relative days.** today, tonight, tomorrow, yesterday; היום, הלילה, הערב, מחר, מחרתיים, אתמול,
שלשום; اليوم, الليله, الليلة, غدا, غد, بكره, بكرة, امس, البارحه, البارحة. היום and اليوم also mean "the
day"; the prompt asks for other words ("each day", "כל יום", "كل يوم").

**Percentages.** percent, per cent, percentage, percentages; אחוז, אחוזים; بالمئه, بالمئة,
بالمائه, بالمائة, المئه, المئة.

**Currency.** shekel, shekels, nis, ils, agora, agorot; שקל, שקלים, שח, אגורה, אגורות; شيكل,
شيقل, شواكل, اغورة, اغورات.

