---
ID: PLAN-PHASE-9
Title: Phase 9 — V2, F14 Decision Explanations (F14-S1)
Status: Ready for review
Owner: smartshelf-architect
Parent: [Implementation plan](plan.md)
Inputs: [docs/features/F14-decision-explanations/specs/F14-S1-decision-explanations.md (Approved 2026-10-12), ADR-045 (Accepted 2026-10-12), ADR-001, ADR-014, ADR-032, ADR-034, ADR-035, ADR-039, docs/reviews/F14-screens-mockups.md (Approved 2026-10-10), src/engine/model_client.py, src/engine/shelf_explanation.py, src/engine/market_boost.py, src/engine/run.py, scripts/build_order_example.py, src/pages/ReorderPage.jsx (the card and note, merged as #313)]
Updated: 2026-10-12
---

# Phase 9 — V2, F14 Decision Explanations

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal.** Build the engine's half of F14-S1: the `order_explanation` capability, the nightly step
that asks the model per department group, checks each text and seals the night's answers, the
probe, and the example's real answers (FR-235 … FR-244). The card and the note are already on
main (#313, approved with the mockups on 2026-10-10); this phase feeds them.

**Architecture.** One pure check module and one pure facts module, unit-tested on their own; one
capability module holding the live step (publish mode only) and the reader (both modes), as
`shelf_explanation.py` does; the shared model client gains a thinking setting and returns the
API's usage and stop reason. One list of served prompt versions, in `configs/prompts/`, is read by
the engine, the page and the example's builder.

**Tech stack.** Python 3 (stdlib `unicodedata`, `concurrent.futures`, `decimal`, `hashlib`),
pytest; React and Vitest for the one page change; GitHub Actions for the nightly.

**Spec.** [F14-S1](../features/F14-decision-explanations/specs/F14-S1-decision-explanations.md)
(approved 2026-10-12) and [ADR-045](../architecture/decisions/ADR-045-an-order-explanation-is-asked-per-department-checked-and-sealed.md).
Executors read both.

**On real data, `order_explanation` is unavailable when this phase ends.** No store sends daily
sales (D-23), so `order_quantity` is unavailable, and so is this, with the same reason. There is
also no model key (F14-S1 OQ-1404). Everything is proven on the order probe's fixture world, with
a stand-in transport, as Phases 5 and 8 were. No test makes a network call.

## Phase constraints

- **The model writes no number.** Every figure on the card is a slot the page fills (FR-238). No
  task lets the model's text carry a figure through any path, reuse included.
- **One check, run twice.** The live step checks each text before sealing it, and the capability
  checks it again before publishing (FR-240), with the same function. There is no second copy.
- **The quantities never move.** No task changes `order_quantity`, `market_boost` or any other
  capability's figures; withholding the sealed explanations changes nothing else (INV-098).
- **No ₪ anywhere.** `order_explanation` has `value_policy: none`, and the check refuses money
  signs and words (D-1).
- **Nothing asks at request time, and print mode never asks** (D-16, ADR-007).
- **The deadline is this step's only** (FR-241). The boost, the shelf explanation and the shelf
  reader keep their own budgets; Phase 9 does not touch them.
- **The example is fenced** (D-29, INV-101): built in a temporary folder, nothing under the
  store's `data/external/snapshots/`, and its committed answers are read by nothing else.
- **No new dependency.** Everything here is in Python's standard library.
- **Actions minutes.** Two pull requests, each tested locally first (pytest, vitest, lint, build
  and bundle, e2e, `check:signals`) and pushed once.

## Values

Approved with F14-S1 OQ-1403 on 2026-10-12. They go into `configs/policy.yaml` under
`order_explanation:`, and the artefact publishes every one.

| Value | Policy key | Approved |
|---|---|---|
| Suggestions per request | `group_size` | 20, the owner's figure; the loader refuses more (OQ-1402) |
| Requests in flight at once | `concurrency` | 4 |
| Requests per night | `request_ceiling` | 60 |
| Time budget | `time_budget_s` | 600 |
| Request timeout | `timeout_s` | 120 |
| Characters per language, before the slots are filled | `max_chars` | 200 |
| Answer token limit | `max_tokens` | 8000 |
| Nights read back for reuse | `reuse_nights` | 7 |

**Decided here, from measurement: the nightly's deadline.** F14-S1 FR-241 leaves it to this plan.
Seven nightly runs, 2026-10-06 to 2026-10-12, measured with `gh run view`:
- the engine step started 16 to 22 minutes into the job and took 1.0 to 1.7 minutes;
- everything after it took 4.4 to 8.6 minutes. The deploy check alone may take up to 12.

The nightly sets the deadline at **36 minutes after the job starts**. This step stops sending then,
and finishes within about 4 more minutes (one request timed out and retried). That leaves about
20 minutes for what follows, against the 15 it can take at worst, inside the job's 60.

## Tasks, in dependency order

| Task | What | Depends on |
|---|---|---|
| 9.0 | The shared client: a thinking setting, usage and stop reason | — |
| 9.1 | Policy, the prompt, and the served-versions list | — |
| 9.2 | The check | — |
| 9.3 | Facts, slots, digest and groups | 9.2's slot names |
| 9.4 | The live step and the capability | 9.0, 9.1, 9.2, 9.3 |
| 9.5 | The nightly: deadline and commit | 9.4 |
| 9.6 | The probe | 9.4 |
| 9.7 | The example | 9.4 |
| 9.8 | The page reads the served list; the screen lists | 9.1 |
| 9.9 | Checkpoint 9 and the record | all |

### Task 9.0: The shared client returns usage and stop reason, and takes a thinking setting (ADR-045 Decision 2)

**Files:**
- Modify: `src/engine/model_client.py`
- Test: `tests/engine/test_model_client.py`

**Interfaces:**
- Produces:
  - `Answer`, a frozen dataclass: `text: str`, `stop_reason: Optional[str]`,
    `input_tokens: Optional[int]`, `output_tokens: Optional[int]`;
  - `ask_full(payload: dict, *, model: str, key: str, transport: Transport, max_tokens: int,
    timeout: float = TIMEOUT_S, thinking: Optional[dict] = None) -> Answer`;
  - `ask(...)`, unchanged in signature and behaviour, now `return ask_full(...).text`.
- Consumes: nothing new.

- [ ] **Step 1: Write the failing tests.** Using the existing stand-in transport pattern:
  - `ask_full` with `thinking={"type": "disabled"}` sends `"thinking": {"type": "disabled"}` in the
    body; without it, the body has no `thinking` key, byte for byte as today;
  - a 200 answer `{"content": [{"type": "text", "text": "x"}], "stop_reason": "end_turn",
    "usage": {"input_tokens": 10, "output_tokens": 3}}` gives `Answer("x", "end_turn", 10, 3)`;
  - an answer whose first block is `{"type": "thinking", "thinking": ""}` still returns the text
    block's text;
  - `stop_reason: "max_tokens"` is returned, not raised: the caller decides (Task 9.4 withholds);
  - `ask` returns the same text as before for every existing case in the file.
- [ ] **Step 2: Run** `python3 -m pytest tests/engine/test_model_client.py -v`. Expected: the new
  tests fail on `ImportError: cannot import name 'ask_full'`.
- [ ] **Step 3: Implement.** Move the body of `ask` into `ask_full`; add `thinking` to the body only
  when it is not `None`; read `stop_reason` and `usage` with `.get` so a missing field is `None`.
- [ ] **Step 4: Run** the client's tests, then `python3 -m pytest tests/engine/test_market_boost.py
  tests/engine/test_shelf_explanation.py -q`. Expected: all pass; the boost and the shelf
  explanation are unchanged.
- [ ] **Step 5: Commit** `src/engine/model_client.py tests/engine/test_model_client.py`:
  "The model client returns usage and stop reason, and takes a thinking setting (ADR-045)".

**Done when:** the boost's and the shelf explanation's suites pass unchanged, and no request they
send has changed.

### Task 9.1: Policy, the prompt, and the served-versions list (FR-237, FR-238, FR-239, FR-241)

**Files:**
- Modify: `configs/policy.yaml`, `src/engine/policy.py`
- Create: `configs/prompts/order_explanation.v1.md`, `configs/prompts/order_explanation.served.json`
- Test: `tests/engine/test_policy.py`, `tests/engine/test_order_explanation_served.py`

**Interfaces:**
- Produces: `Policy` fields `order_explanation_prompt: str`, `order_explanation_served: str`,
  `order_explanation_group_size: int`, `order_explanation_concurrency: int`,
  `order_explanation_request_ceiling: int`, `order_explanation_time_budget_s: int`,
  `order_explanation_timeout_s: int`, `order_explanation_max_chars: int`,
  `order_explanation_max_tokens: int`, `order_explanation_reuse_nights: int`;
  `Policy.as_dict()["order_explanation"]` with the model (`boost_model`) and every value;
  the served list's shape:
  ```json
  {"versions": [{"prompt_sha256": "<sha256 of order_explanation.v1.md>",
                 "phrases_sha256": "<digest of the page's slot phrases>"}]}
  ```
- Consumes: nothing.

- [ ] **Step 1: Write the failing tests.**
  - `test_policy.py`: the loader reads the ten values of the Values table; `group_size: 21` is
    refused with an error naming OQ-1402; a missing key is refused, as every `_required` is.
  - `test_order_explanation_served.py`: the sha256 of `configs/prompts/order_explanation.v1.md`'s
    bytes is a `prompt_sha256` on the served list.
- [ ] **Step 2: Run** both files with `python3 -m pytest -v`. Expected: FAIL (no keys, no files).
- [ ] **Step 3: Write the policy block** under `order_explanation:` with the Values table's numbers,
  `prompt: configs/prompts/order_explanation.v1.md` and
  `served: configs/prompts/order_explanation.served.json`, each with a one-line comment citing
  F14-S1 OQ-1403. Load them in `policy.py` beside `shelf_explanation_*`, and add them to `as_dict`.
- [ ] **Step 4: Write the prompt.** It is product text and names no store (C-80). It says, in this
  order:
  1. the task: for each suggestion in the request, write why its quantity is what it is, in
     Hebrew, Arabic and English, from its facts only (FR-235);
  2. the answer's form: one JSON object keyed by suggestion id, each value
     `{"he": …, "ar": …, "en": …}`, nothing else;
  3. each slot by name, what it means, and how its phrase reads, from the FR-238 table, with the
     rule that only offered slots may be used, each once; `{product}`, `{expected}` and
     `{next_order}` in every text, and every offered `{left}`, `{runs_out}` or `{capped}`;
  4. never a number, in digits or words; never a product's name, a date, a weekday, "today" or
     "tomorrow"; never a percentage or money; never another suggestion of the group; nothing
     about the market unless the facts carry it;
  5. Hebrew without abbreviations or quote marks; "יום ההזמנה" and "يوم الطلب" for the order day,
     never היום or اليوم; wording that does not depend on the product's gender or number
     ("המכירות של {product}", "مبيعات {product}");
  6. at most 200 characters per language, plain sentences, no persuasion.

  Its examples must not open with "For {next_order}", which reads "for … for" in English.
- [ ] **Step 5: Write the served list** with the prompt's sha256 and, for now, the phrases digest
  that Task 9.8's test computes (run Task 9.8 Step 2 to get it, or leave a value the test then
  names as wrong and replace it with the one it prints).
- [ ] **Step 6: Run** the tests again. Expected: PASS.
- [ ] **Step 7: Commit** the five files: "Policy, the prompt and the served versions for
  order_explanation (F14-S1, OQ-1403)".

**Done when:** `npm run figures` reproduces the artefact with `thresholds.order_explanation` present
once Task 9.4 registers the capability, and the served test pins the prompt.

### Task 9.2: The check (FR-238, Appendix A; AC-222)

**Files:**
- Create: `src/engine/order_explanation_check.py`
- Test: `tests/engine/test_order_explanation_check.py`

**Interfaces:**
- Produces:
  - `SLOTS = ("product", "quantity", "expected", "weeks", "next_order", "left", "runs_out",
    "capped")`;
  - `check(answer: dict, *, offered: frozenset, required: frozenset, group_names: list,
    max_chars: int) -> dict`, where `answer` is one suggestion's `{"he", "ar", "en"}` and the
    result is `{"accepted": bool, "withheld_because": Optional[str], "word": Optional[str]}`;
  - `withheld_because` is one of `missing_language`, `too_long`, `wrong_letters`,
    `slot_not_offered`, `slot_repeated`, `slot_required`, `product_named`, `numeral`,
    `letter_numeral`, `number_word`, `relative_day`, `percentage`, `currency`;
  - `normalise(text: str) -> str` and `letter_numeral(text: str) -> Optional[str]`, exported for
    the probe's own scan to stay independent of them (Task 9.6 does not import them).
- Consumes: nothing.

The rules, in the order the check applies them, each from FR-238:
1. three non-empty languages, each at most `max_chars` before filling;
2. slots: every `{name}` is in `offered`, none twice, every name in `required` present;
3. letter-numerals, before NFKC: slots replaced by a space, `Cf` characters and Hebrew vowel
   points and dagesh (U+05B0–U+05BD, U+05BF, U+05C1, U+05C2, U+05C4, U+05C5, U+05C7) removed; then
   any mark straight after a Hebrew letter is refused, a mark being a character in Pi, Pf, Po,
   Sk or Lm, a cantillation mark (U+0591–U+05AF), or one of `׳ ״ ' " ′ ″ ʼ ʺ ´ ¨ ˝` and the
   backtick, except `. , : ; ! ? …`;
4. numerals: with slots replaced by a space, no character whose Unicode category starts with
   `N`, in the raw text or its NFKC form;
5. the normalised text (slots to a space, NFKC, `Cf` and `Mn` removed, U+0640 removed,
   `أ إ آ ٱ` to `ا` and nothing else, case-folded) tokenised on non-letters; each token is
   tested as is, after taking off up to two Hebrew prefix letters, after Arabic's
   `و|ف`, `ب|ك|ل`, `ال` and `لل` (also tested with `ال` put back), and after the pronoun endings,
   against Appendix A's lists: number words, relative days, percentage words, currency words,
   with the ordinary-word exceptions (שתיה, שתייה never as שתי). Signs: `%`, `٪` and every `Sc`
   character after NFKC;
6. product names of the group, matched as tokens the same way, refused;
7. each language holds a letter of its own script once the slots are removed.

- [ ] **Step 1: Write the failing tests**, one per AC-222 case and per §12 row, each asserting
  `withheld_because` and, for word rules, `word`:
  - passes: a text with `{product}`, `{expected}`, `{next_order}` and an offered `{left}`; a
    product name holding digits or "%" passed through `{product}`; "לפי", "כפי", "על פי",
    "מצד שני", "لست", "שתיה", "الاحد"; a Hebrew word followed by `.` or `,`;
  - withheld `numeral`: "35", "３５", "½", "٣٥", "Ⅻ";
  - withheld `letter_numeral`: "ז׳ ימים", "ל״ה", "ל”ה", "ל’", "ל´´ה", "לʺה", "ש״ח", "סה״כ";
  - withheld `number_word`: "four", "שלושה", "ובשלושה", "ثلاثةَ", "ثلاثـة", "ثلا‍ثة" (a ZWJ inside),
    "وبالثلاثة", "لليومين", "للأسبوعين", "חציו", "نصفها", "שבועיים", "أسبوعين", "مرتين", "both",
    "שלשים", "מליון", "ثلاثمائة";
  - withheld `relative_day`: "tomorrow", "מחר", "غداً", "لليوم", "لليلة";
  - withheld `percentage`: "%", "٪", "％", "percent", "אחוזים";
  - withheld `currency`: "₪", "$", "€", "שקלים", "شيكل", and "משקל" (the accepted false
    positive, asserted so a change to it is seen);
  - withheld `slot_not_offered`, `slot_repeated`, `slot_required` (no `{next_order}`; no offered
    `{runs_out}`; a capped text without `{capped}`), `product_named` ("במבה" in a group holding
    it, not "ימים" against "מים"), `too_long` (201 characters), `missing_language`,
    `wrong_letters` (an English "he" text).
- [ ] **Step 2: Run** `python3 -m pytest tests/engine/test_order_explanation_check.py -v`.
  Expected: FAIL on the missing module.
- [ ] **Step 3: Implement** the module: Appendix A's lists as `frozenset` constants, each loaded
  through `normalise` once at import, and an assertion that every listed word comes out unchanged
  (the test in Step 1 also asserts it).
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit**: "The check for order explanations (F14-S1 FR-238, Appendix A)".

**Done when:** every AC-222 case passes, and the module imports nothing from the engine.

### Task 9.3: Facts, slots, digest and groups (FR-236, FR-237, FR-238, FR-239)

**Files:**
- Create: `src/engine/order_explanation_facts.py`
- Test: `tests/engine/test_order_explanation_facts.py`

**Interfaces:**
- Produces:
  - `round_half_up(x: float) -> float`: one decimal, halves up (`decimal.ROUND_HALF_UP`), as the
    page's `Math.round(x * 10) / 10` for figures of 0 and above;
  - `offered_slots(entry: dict, window: dict) -> frozenset` and
    `required_slots(entry: dict, offered: frozenset) -> frozenset`;
  - `facts(entry: dict, *, department: str, market_products: dict, window: dict) -> dict`, the
    FR-236 facts without the id or the product name;
  - `digest(entry, *, department, market_products, window) -> str`, `facts_digest` of `facts`;
  - `groups(entries: list, size: int) -> list[list[dict]]`: by department, in published order,
    at most `size` each.
- Consumes: Task 9.2's `SLOTS`; `model_client.facts_digest`; `order_quantity`'s entry shape
  (`evidence.quantity`, `kind`, `weekly_units`, `expected_sales`, `cycle.days`, `order_day`,
  `count.used`, `count.not_used_because`, `stock_at_order_day`, `capped`, `shelf_life.days`,
  `boost.applied`, `boost.pct`, `boost.not_applied_because`, `report_days`) and the window
  (`report_days`, `weeks`, `last_day`).

Rules:
- `{weeks}` is offered only when `evidence.report_days == window.report_days`, the window's
  report days equal its calendar days, and every week is 7 days;
- `{left}` when `count.used` and `stock_at_order_day > 0.05`; `{runs_out}` when `count.used` and
  `stock_at_order_day <= 0.05`; `{capped}` when `capped` and `shelf_life.days`;
- the market facts only when `entry.barcode in market_products`; "raised" is
  `boost.applied and boost.pct > 0`;
- figures in the facts are `round_half_up`; no date, weekday, shelf-life days, stock now, daily
  mean, name, barcode, price or boost figure.

- [ ] **Step 1: Write the failing tests** over the example world's six suggestions (built with
  the order probe's fixture world): קולה offers `{left}`; במבה, לחם, פיתות and מים offer
  `{runs_out}`; ביסלי offers neither (gross); לחם and פיתות offer `{capped}`; a window with one
  day unreported offers no `{weeks}` and sends no weekly figures (AC-223, SCN-187); only מים
  carries market facts; a 0% pick is "not raised"; `round_half_up(0.25) == 0.3` and
  `round_half_up(34.65) == 34.7`; the facts hold none of the forbidden fields; the digest is the
  same for two suggestions with equal facts and different ids, and differs across departments;
  `groups` splits 45 suggestions of one department into 20, 20 and 5.
- [ ] **Step 2: Run** them. Expected: FAIL on the missing module.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit**: "Facts, slots and groups for order explanations (F14-S1 FR-236)".

### Task 9.4: The live step and the capability (FR-235 … FR-241; INV-098 … INV-100)

**Files:**
- Create: `src/engine/order_explanation.py`
- Modify: `src/engine/inputs.py`, `src/engine/registry.py`, `src/engine/run.py`,
  `src/engine/publish.py` (only if it lists capabilities that may not carry a value)
- Test: `tests/engine/test_order_explanation.py`, `tests/engine/test_unavailable_reasons.py`

**Interfaces:**
- Produces:
  - `CAP, SPEC, FOLDER = "order_explanation", "F14-S1", "order_explanations"`;
  - `read(snapshots_root: Path, day: str) -> Optional[dict]`, as `shelf_explanation.read`;
  - `live_step(inputs, *, snapshots_root: Path, key: Optional[str], transport, now: datetime,
    asking: bool = True, deadline: Optional[datetime] = None, clock=time.monotonic) -> dict`;
  - `run(inputs) -> CapabilityOutput`, with `extras["explanations"]`, a list of
    `{suggestion_id, slots, text, prompt, model, why_none, withheld_because, word, reused_from}`
    in suggestion order, and `counts` `{suggestions, explained, withheld, out_of_date,
    not_written_tonight, reused, requests_made}`. These are the names the merged page reads
    (`ReorderPage.jsx`: `suggestion_id`, `slots`, `text`, `prompt`; `counts.suggestions`,
    `counts.explained`);
  - `EngineInputs.order_explanations: Optional[dict]`, read by run date;
  - registry: `"order_explanation": CapabilitySpec("order_explanation", "F14-S1", "none", False,
    "suggestion_order", ("products", "sales_daily", "store_facts", "order_explanations"),
    published_from=<date>)`, `<date>` being the first nightly after pull request 1 merges;
    `INPUT_REASONS["order_explanations"]
    = "no_model_key"`;
  - `run_engine(..., order_explanation_transport=None, order_explanation_ask: bool = True)`.
- Consumes: Tasks 9.0 to 9.3; `order_quantity.run`; `market_running_out`'s published products.

What `live_step` does, in order:
1. no key, or `asking=False`: return `{"skipped": "no_model_key" | "not_asked"}`, write nothing;
2. run `order_quantity`; unavailable: return its reason, write nothing;
3. read the served list; the prompt file's sha256 not on it: write the manifest with
   `skipped: "prompt_not_served"` and return (SCN-188);
4. write the night's manifest with a run marked started (`completed: false`, AC-233);
5. for each suggestion: if tonight's snapshot holds a record for its id, skip it (nothing sealed
   is replaced); else look back newest first through earlier snapshots, stopping at the first
   whose manifest has a run with `ended: true`, and at most `reuse_nights`; copy the newest
   accepted record with the same digest, model and prompt sha256, with `reused_from`;
6. group the rest (`groups`), and send up to `concurrency` at once through a thread pool.
   Before each send: stop on a failed request, on the ceiling (counted at send), on the time
   budget, or on the deadline (`deadline` is the earlier of `now + time_budget_s` and the
   nightly's `SMARTSHELF_MODEL_DEADLINE`). In-flight requests finish and are kept;
7. each answer: `stop_reason == "max_tokens"` withholds its group as `cut_off`; a non-parsing
   answer withholds its group as `did_not_parse`; else each id is checked with Task 9.2's
   `check` and sealed accepted or withheld, with the raw answer cut to 2,000 characters for an
   audit when withheld;
8. seal records as they arrive (`explanations.json`), then the manifest's run with
   `ended: true`, `completed`, `requests_made`, `reused`, `not_asked` with reasons, and each
   request's `input_tokens`, `output_tokens` and `stop_reason` (AC-234).

What `run` does: run `order_quantity` first and take its reason when unavailable (FR-240); no
sealed snapshot: unavailable `no_model_key`; else, per suggestion, `out_of_date` when the digest
differs (INV-099), `withheld` as sealed, `not_written_tonight` when absent, and otherwise **check
the text again** against tonight's offered and required slots and the group's names (FR-240),
publishing it as withheld if it now fails.

- [ ] **Step 1: Write the failing tests** with a stand-in transport that records each request and
  answers from a table keyed by suggestion id:
  - AC-221: a publish run with the stand-in, then print mode with the sealed snapshot and print
    mode without it, give identical `order_quantity` and `market_boost` capabilities; without it,
    `order_explanation` is unavailable `no_model_key` (AC-231);
  - AC-223: the request body holds `"thinking": {"type": "disabled"}`, `max_tokens: 8000`, and
    none of the forbidden fields, read from the recorded body;
  - AC-224: 45 suggestions in one department make 3 requests; an answer missing an id withholds
    that id as `missing`; an unparseable answer withholds its group only; `stop_reason:
    max_tokens` withholds its group as `cut_off`;
  - AC-225: print mode never calls the transport; a sealed record whose digest no longer matches
    is published `out_of_date`;
  - AC-226: an unchanged suggestion is copied from last night with `reused_from` and no request;
    the look-back stops at the first ended night and never reads more than `reuse_nights`; a
    record from another department is not reused; a second run the same night adds and replaces
    nothing;
  - AC-227: past the ceiling, the budget or the deadline, or after a failure, no request is sent;
    in-flight answers are kept; counts add up to the suggestions;
  - AC-233: a transport that raises after the first request leaves a manifest marked started;
  - AC-234: each request's tokens and stop reason are in the manifest;
  - SCN-188: an unlisted prompt asks nothing and records `prompt_not_served`;
  - FR-240: a sealed text that passed the night's check but holds a word added to the lists
    since is published withheld.
- [ ] **Step 2: Run** `python3 -m pytest tests/engine/test_order_explanation.py -v`. Expected:
  FAIL on the missing module.
- [ ] **Step 3: Implement** `order_explanation.py`, the input in `inputs.py`, the registry entry,
  and `run.py`'s step: after the boost (and its inputs' re-read), before the shelf explanation,
  with `transport=order_explanation_transport or urllib_transport`, `asking=order_explanation_ask`,
  the deadline from the environment, and inputs read again when it wrote. Add the runner.
- [ ] **Step 4: Run** `python3 -m pytest -q` (the whole suite) and
  `python3 -m pytest tests/engine/test_unavailable_reasons.py -v` after adding
  `order_explanation`'s reasons. Expected: PASS.
- [ ] **Step 5: Commit**: "order_explanation: the live step and the capability (F14-S1 FR-235 …
  FR-241, ADR-045)".

**Done when:** AC-221, AC-223 … AC-227, AC-231, AC-233, AC-234 and SCN-188 pass with no network,
and a print-mode run on real data publishes `order_explanation` unavailable with
`order_quantity`'s reason.

### Task 9.5: The nightly's deadline and commit step (FR-239, FR-241; ADR-045 Decisions 5 and 6)

**Files:**
- Modify: `.github/workflows/collect-daily.yml`
- Test: `tests/test_collection_health.py` (only if it reads the commit step's paths)

**Interfaces:**
- Produces: `SMARTSHELF_MODEL_DEADLINE`, an ISO-8601 UTC time, in the job's environment from its
  first step; the commit step's message "snapshot: boost picks and AI explanations for ${DAY}".
- Consumes: Task 9.4 (`run.py` reads the variable).

- [ ] **Step 1: Add a first step** that writes the deadline, 36 minutes after the job starts:
  ```yaml
  - name: Set tonight's deadline for the AI explanations (F14-S1 FR-241, Phase 9)
    run: echo "SMARTSHELF_MODEL_DEADLINE=$(date -u -d '+36 minutes' +%Y-%m-%dT%H:%M:%SZ)" >> "$GITHUB_ENV"
  ```
  with a comment giving the measurement above.
- [ ] **Step 2: Extend the commit step** with
  `git add -f -- ':(glob)data/external/snapshots/*/order_explanations/*.json' 2>/dev/null || true`
  and its message, and its comment naming ADR-045 Decision 5.
- [ ] **Step 3: Check** the workflow with `python3 -c "import yaml,sys;
  yaml.safe_load(open('.github/workflows/collect-daily.yml'))"` and run the collection-health
  tests. Expected: PASS.
- [ ] **Step 4: Commit**: "The nightly sets the explanations' deadline and commits them".

**Done when:** the first nightly after the merge shows the deadline in its environment, and a run
with no key commits nothing new.

### Task 9.6: The probe (F14-S1 §20; INV-098 … INV-100)

**Files:**
- Modify: `scripts/check_order_signals.py`, `scripts/check_v1_signals.py`,
  `tests/test_check_v1_signals.py`, `tests/fixtures/order_signals/build.py`
- Test: `tests/test_check_order_signals.py` (if present; else the probe's own exit code in CI)

**Interfaces:**
- Produces: `FakeOrderExplainer` in the fixture world, answering each requested id with a text
  that passes the check (`{product}`, `{expected}`, `{next_order}` and the required offered slot);
  `BadOrderExplainer`, answering with the planted failures below; probe cases
  `withheld_order_explanations_problems`, `bad_order_answers_problems`,
  `order_fact_change_problems`; `PROBED_ELSEWHERE["order_explanations"]`;
  `_F8_WORDING["order_explanations"] = "the sealed order explanations"`.
- Consumes: Task 9.4's `run_engine` parameters.

- [ ] **Step 1: Write the cases**, each reading the published artefact, never a return value:
  - **withheld:** the world built with `FakeOrderExplainer`, then the snapshot removed: every
    `order_quantity` and `market_boost` figure equal, and every suggestion saying why it has no
    explanation (INV-098, AC-221);
  - **bad answers:** `BadOrderExplainer` plants a digit, a Roman numeral, a number word, "%",
    "ש״ח", an unoffered slot, a written product name, and a capped text without `{capped}`. Each
    is published withheld. Then an **independent scan** over every published text: remove
    `\{[a-z_]+\}`, and fail on any character whose `unicodedata.category` starts with `N`. It is
    written in the probe and imports nothing from `order_explanation_check` (INV-100);
  - **facts changed:** for each FR-236 source in turn (a daily report, a report day removed, the
    count, the shelf life, the schedule, the boost's pick, the market snapshots, the product's
    department), seal, change the source, rebuild in print mode: the explanation is
    `out_of_date` (INV-099).
- [ ] **Step 2: Add** `"order_explanations": "scripts/check_order_signals.py"` to
  `PROBED_ELSEWHERE`, and the wording to `_F8_WORDING`.
- [ ] **Step 3: Run** `npm run check:order-signals` and `python3 -m pytest
  tests/test_check_v1_signals.py -v`. Expected: PASS, and the probe prints each new case.
- [ ] **Step 4: Commit**: "The probe withholds, plants and changes order explanations
  (F14-S1 §20)".

### Task 9.7: The example's real answers, or none (FR-244; AC-230, AC-232, AC-237)

**Files:**
- Modify: `scripts/build_order_example.py`, `public/examples/order-example.json` (rebuilt),
  `tests/test_order_example.py`
- Create (by the owner's `--explain` run only): `tests/fixtures/order_example/explanations.json`,
  `tests/fixtures/order_example/boost_picks.json`

**Interfaces:**
- Produces: `build() -> dict` that includes `order_explanation` in the example's capabilities;
  `explain() -> int`, run by `--explain`; the two committed files' shapes are the sealed
  snapshot's own (`explanations.json`, `picks.json`), so the builder seals them unchanged.
- Consumes: Task 9.4's `order_explanation_ask=False`; `market_boost`'s snapshot format
  (`picks_dir`, `picks.json`, `_manifest.json`).

- [ ] **Step 1: Write the failing tests** in `test_order_example.py`:
  - the build passes no key and asks no model: a transport that raises if called is given, and
    the key variable is unset during the build (AC-230);
  - with no committed pick, no suggestion's boost is applied, מים's quantity is 21, and its boost
    says `no_pick` (AC-237, SCN-184). This replaces the test's old "boosted" assertion;
  - with no committed explanations, `order_explanation` is available, explains none, and counts
    six not written tonight (SCN-184);
  - building writes nothing under the repository's `data/external/snapshots/` (compare its
    listing before and after), and no store run reads `tests/fixtures/order_example/` (grep the
    engine's sources for the path: only the builder names it) (AC-232);
  - a committed record whose digest no longer matches, or whose prompt is not served, fails the
    build with a message naming the file to remove (AC-237).
- [ ] **Step 2: Run** `python3 -m pytest tests/test_order_example.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** In `build()`: unset the key variable for the publish pass; pass
  `order_explanation_ask=False`; seal into the temporary snapshots the committed pick, or a boost
  manifest with one finished run and no picks, and the committed explanations, or a manifest with
  one ended run and none. Check each committed record's digest and prompt first. Add
  `order_explanation` to the copied capabilities. Correct the module docstring's claim that every
  figure on the preview is the engine's own: the boost was a stand-in's until this task.
  In `explain()`: require the key; run the publish pass with the real transports for the boost
  and this step only; refuse if any answer's stop reason is `max_tokens`; write the two files
  sorted, and print how many were explained and withheld.
- [ ] **Step 4: Rebuild** with `python3 scripts/build_order_example.py` and run the tests and
  `npx vitest run src/pages/__tests__/orderExamplePreview.test.jsx`. Expected: PASS.
- [ ] **Step 5: Commit** the script, the rebuilt example and the test: "The example's boost and
  explanations are real answers, or none (F14-S1 FR-244)".

**Done when:** the example shows six cards with the engine's sentence, the note "the AI has not
explained", and מים not raised at 21, until the owner runs `--explain` with the key (OQ-1404).

### Task 9.8: The page reads the served list, and the screen lists (FR-242; C-77)

**Files:**
- Modify: `src/pages/ReorderPage.jsx`, `src/surface/compose.js`,
  `src/pages/__tests__/ReorderPage.explanation.test.jsx`
- Create: `src/pages/__tests__/orderExplanationServed.test.js`

**Interfaces:**
- Produces: `PHRASES_SERVE`, built from `configs/prompts/order_explanation.served.json`'s
  `prompt_sha256` values; `phrasesDigest(dictionaries) -> string`, the sha256 over the
  `reorder.ai.slot.*` strings of en, he and ar, sorted by key then language and joined with a
  newline.
- Consumes: Task 9.1's served list.

- [ ] **Step 1: Write the failing test** `orderExplanationServed.test.js`: every listed version's
  `phrases_sha256` equals `phrasesDigest` of the current dictionaries. It prints the current
  digest on failure, so a phrase change shows the value to confirm or the version to drop
  (FR-239).
- [ ] **Step 2: Run** `npx vitest run src/pages/__tests__/orderExplanationServed.test.js`.
  Expected: FAIL until Task 9.1's list holds the printed digest.
- [ ] **Step 3: Implement.** Import the JSON in `ReorderPage.jsx` in place of the constant set,
  and change the explanation tests from `'mockup-sample'` to the list's first version. Add
  `'order_explanation'` to `NOT_ON_TODAY` and `NOT_YET_SHOWN` in `compose.js`, with a comment:
  it is approved as part of each Reorder card, not as a capability of its own.
- [ ] **Step 4: Run** `npm run test`, `npm run lint`, `npm run build && npm run check:bundle`.
  Expected: PASS, within the ceiling #313 set (1029 KB).
- [ ] **Step 5: Commit**: "The page reads the served prompt versions from one list (F14-S1
  FR-242)".

### Task 9.9: Checkpoint 9 and the record

**Files:** `docs/implementation/plan.md` (this phase's row), `docs/architecture/system-design.md`
§21 (F14-S1: built), this file's status.

- [ ] Run the whole local gate: `python3 -m pytest -q`, `npm run test`, `npm run lint`,
  `npm run build && npm run check:bundle`, `npm run check:signals`, and the e2e suite on a free
  port (not 5173).
- [ ] Record the checkpoint's results in this file, with the test counts as printed.

## Pull requests

1. **Engine:** Tasks 9.0 to 9.4. The capability is published, and unavailable on real data.
2. **Nightly, probe, example and page:** Tasks 9.5 to 9.9.

Each is tested locally first and pushed once (Phase constraints).

## Checkpoint 9

- AC-221 … AC-237 pass: the engine's in pytest, the page's in vitest (AC-228, AC-229, AC-235 and
  AC-236 are #313's and stay green).
- `npm run check:signals` passes with the three new probe cases, and `order_explanations` is in
  `PROBED_ELSEWHERE`.
- On real data, `order_explanation` is unavailable with `order_quantity`'s reason, and the
  nightly commits no explanation (no store, no key).
- The example builds without a key and shows the engine's sentence on every card, and מים at 21,
  not raised.
- **After the owner sets the key (OQ-1404) and runs `--explain`:** read the example's answers in
  the three languages with him, and the manifest's tokens and stop reasons against ASM-086 and
  ASM-087. Neither is a condition of this checkpoint; both are its first use.

## Review focus

The inputs no task's tests can exercise, most likely to bite first:
1. **Real answers, not stand-ins.** The first real `--explain` run may show cut-offs, 429s, or
   texts the check withholds often. Read the manifest and the counts on that run, before any store
   night (ASM-086, ASM-087).
2. **How the Hebrew and Arabic read.** No check reads agreement or tone (ASM-085). The owner reads
   the example's answers once, in his languages, before a store's first night.
3. **Mixed-direction text on a real phone.** Task 9.8 keeps #313's isolation tests; an e2e
   screenshot of the rebuilt example in he and ar at 390×844 confirms it on screen.
4. **A long night.** A stand-in transport with a delay tests the deadline (Task 9.4), but not the
   nightly's other steps' times on the same night. The first store nights' job times are read
   against the 36-minute deadline.
5. **The lists' false positives.** The check records the word that withheld each text. After the
   first nights, the recorded words show whether an ordinary word is withheld often.
