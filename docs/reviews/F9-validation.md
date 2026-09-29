---
ID: F9-VALIDATION
Title: F9 — Assortment Gap · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F9-S1](../features/F9-assortment-gap/specs/F9-S1-assortment-gap.md)
Inputs: [docs/features/F9-assortment-gap/specs/F9-S1-assortment-gap.md, docs/features/F9-assortment-gap/intent.md, docs/implementation/phase-6-v2-assortment-gap.md, docs/reviews/f9-card-2026-09-29.md, docs/operations/deployment.md, public/data/dashboard.json and catalogue.json (2026-09-29), public/data/measurement.json (2026-09-29), src/market/recent.py, src/engine/assortment_gap.py, src/surface/compose.js, src/surface/EntryCard.jsx, tests/test_market_recent.py, tests/engine/test_assortment_gap.py, src/surface/__tests__/compose.test.js, src/surface/__tests__/assortmentGapCard.test.jsx, scripts/check_v1_signals.py, scripts/check_order_signals.py, GitHub deployment records (Production)]
Updated: 2026-09-29
---

# Validation F9 — Assortment Gap

- **Deployed URL:** `https://hackathon2026-fadi19.vercel.app` (serves the sign-in page; ADR-029).
- **Commit in production:** `e8f4ea7`. GitHub deployment `6738113055`, `success`, 2026-09-29 15:03Z. It contains the card (`64eebb1`, #245) and the 2026-09-29 artefact (`b215b0c`).
- **Artefact read:** `public/data/dashboard.json` at `b215b0c`, `generated_at 2026-09-29T03:52:33Z`, run `ok`; `catalogue.json` from the same run (same `inputs_digest`).
- **Replays:** `run_engine(mode="print", skip_market=True)` on current `main`, for 2026-09-28 and 2026-09-29.
- **Context:** the pilot with the YomYom store ended on 2026-09-27 (D-23). F9 was specified, built and put on screen on 2026-09-28/29, after it.

## Verdict

**F9 conforms. Every AC and INV has its evidence, and the live artefact keeps all four
invariants.** One criterion no longer describes Today: AC-167's "two reconciliation entries"
was replaced by D-26's rotation the same day, and the test pinning it still claims to match
the policy file. **Usefulness cannot be judged on use:** there is no store owner, and none of
the 142 findings has an answer. What the artefact does show is that the evidence is thin.
139 of the 142 rest on a single store, and 45 on a single night.

---

## Pass one — conformance

F9-S1 is a compact spec. Its acceptance criteria are in §12 rather than §15, and its intent
traceability is §2 rather than a §19 matrix.

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §12 | AC-164 | a run for 2026-09-28 publishes 138 entries, none catalogued | **met** | Print-mode replay on current `main` for 2026-09-28: `available`, 138 findings, window 2026-09-15…09-28, 13 usable nights. On the live artefact, 0 of 142 entries have a barcode in `catalogue.json` |
| spec §12 | AC-165 | `check:signals` covers it: no snapshots → it and `market_running_out` unavailable; no catalogue → it alone | **met** | `check_order_signals.py` withholds the market snapshots and requires `assortment_gap` unavailable (lines 115-117). `check_v1_signals.py` withholds each declared input and fails a capability that moves on an undeclared one, so withholding `products` must leave `market_running_out` available. `tests/test_check_v1_signals.py` refuses a required input that no probe withholds. Every line of `npm run check:signals` was OK on 2026-09-29 (run for #250) |
| spec §12 | AC-166 | no value; no amount or price in the evidence | **met** | Live artefact: 0 of 142 entries with a `value`; 0 whose evidence mentions price, amount or ₪. `test_an_entry_carries_its_evidence_and_no_value` |
| spec §12 | AC-167 | Today with ≥3 reconciliation and ≥1 F9 shows one F9 entry, first, and two reconciliation entries | **met as written; superseded on screen by D-26** | `compose.test.js`, "shows exactly one F9 entry, first, and reconciliation keeps the other two places", passes. It uses a policy without `rotate`, although its comment says it is "exactly as `configs/policy.yaml` publishes" it. The live policy (D-26, #254) gives the two places to two kinds in turn. Composed from the live artefact with no owner state: F9, then one reconciliation and one competitor entry. See *Open items* |
| spec §12 | AC-168 | "I'll try it" → `acted`, "Not for my store" → `declined`; the entry leaves Today; a team account is read-only | **met** | `assortmentGapCard.test.jsx`: "records … as acted and … as declined with no reason", "is read-only for a team account". `compose.js` drops settled entries (`SETTLED`) |
| spec §12 | AC-169 | tonight's not-stocked `market_running_out` products are exactly the F9 entries with tonight as `last_ran_out` | **met** | Live artefact, `on_day` 2026-09-29: 91 products running out, 66 of them not in the catalogue; 66 F9 entries with `last_ran_out` 2026-09-29; the two sets are equal. `test_tonights_not_stocked_running_out_products_are_all_entries_flagged_tonight` |
| spec §12 | AC-170 | no page shows it while in `NOT_YET_SHOWN` | **met, and now spent** | It was held back until the card's approval (Task 6.3). The repository owner approved the card on 2026-09-29 (`docs/reviews/f9-card-2026-09-29.md`), and `NOT_YET_SHOWN` now holds only `market_running_out` and `market_boost` (`compose.js:28`) |
| spec §12 | AC-171 | FR-172's order, pinned on a fixture that ties on each key | **met** | `test_the_order_is_nights_then_stores_then_latest_night_then_barcode`; `compose.test.js` "shows the first entry the engine published, not the smallest id". Live artefact: the 142 entries are in FR-172 order |
| spec §7 | INV-080 | a catalogued barcode is never an entry | **met** | 0 of 142 on the live artefact; `test_the_findings_are_exactly_the_not_stocked_still_sold_products_that_ran_out` |
| spec §7 | INV-081 | no value, price or quantity | **met** | As AC-166 |
| spec §7 | INV-082 | tonight's `market_running_out` ∖ catalogue = entries flagged tonight | **met** | As AC-169 |
| spec §7 | INV-083 | Today never shows more than one F9 entry | **met** | `unvalued_caps: {assortment_gap: 1}` in `configs/policy.yaml`; `compose.test.js` "gives the capped capability one place"; D-26's tests keep F9 first and single on every day |
| spec §6 | FR-168, FR-170 | evidence fields; family and id | **met** | All 142 carry `stores_ran_out`, `nights_ran_out`, `last_ran_out`, `window`, `listed_at` and `market_name`. The family is `assortment.market_ran_out`, and every id equals `entry_id(family, barcode)` |
| spec §6 | FR-176 | reproducible by print mode | **met** | The replay for 2026-09-29 gives 142 findings, the published count |
| spec §11 | NFR-070 | same inputs, same entries in the same order | **met** | `test_the_result_is_plain_data_and_deterministic`; the replay matched the published count |
| spec §11 | NFR-071 | `npm run figures` within 2 minutes on a fresh clone | **met since #259; not measured by Phase 6** | The plan's progress note measured a local engine run (4.4 s), not a fresh clone. A depth-1 clone on 2026-09-29 took 133 s, mostly `market_context` (Open-Meteo), not F9's replay. After #259 it took 43 s (both measured by that PR, `fda1d08`; not re-measured here) |
| spec §2 | INT-005, D-25, D-23 | traced | **met** | §2 maps each to FRs and INVs, and each FR above reaches an AC or a test |

### Scope drift

| Change | In a plan task's `Files:` list? | In spec §3 scope? | Note |
|---|---|---|---|
| `a378fa1` (Task 6.2) touched `schemas/dashboard.schema.json`, `src/engine/model.py`, `src/engine/publish.py`, `scripts/figures.py` and both probe scripts with their fixtures | no | yes (FR-170, FR-176, AC-165) | The plan records 6.4 as "done inside 6.2". The schema and model carry the new family (FR-170's correction) |
| `64eebb1` (Task 6.5) added the Assortment page: `src/App.jsx`, `src/pages/PageAwaitingData.jsx` | no (6.5 names the card, the dictionaries and `compose.js`) | the card yes; a page is not named in §3 | The page was in the mockups the owner approved (`f9-card-2026-09-29/assortment-page.png`) |
| `64eebb1` also changed `src/engine/assortment_gap.py` | no (a card task) | yes | An engine change inside a screen task |

### Shipped but never requested

- The Assortment page (above). Approved on the mockup, but no FR asks for a page.

---

## Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F9-assortment-gap/intent.md`.*

**PROBLEM («ماذا يبيع السوق ولا أبيعه أنا؟» — an opportunity, not a loss): is the owner
measurably less stuck?** The question is answered on screen: every day one product the store does not
stock, with the stores that ran out of it and on how many nights. Whether that made anyone
less stuck is not measurable. There is no owner (D-23), and `measurement.json` records 0
decisions on the 142 findings.

**SUCCESS — count it.** The intent has no success line. The nearest countable thing is the
finding count: 142 on 2026-09-29.

**USER: would the owner recognise it?** Probably. The card names the product as the market
lists it, names the stores, and asks one question in the owner's three languages. It never says the
product "sells a lot", which the intent's sentence does, and it is right not to. Running out
of a delivery listing is what was seen, and nothing more is claimed.

**NOT NOW: anything deferred built?** No price, no quantity and no reason why it sells. The
intent's "weak here" half went to F8 (D-19), which has no daily data.

**Would you write the same intent again?** Not its solution. The intent orders market
movement, then the store's own movement, then shelf life. F9 uses only the first, and only
one proxy for it: a listing dropping out. The intent's "sells a lot in the market around you"
became "ran out at a store", which is honest but weaker than the promise.

---

## Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| Entries on the daily surface today | **1**, F9's reserved place, first among the unvalued | `compose()` over the committed artefact, empty owner state, 2026-09-29 |
| `generated_at` | 2026-09-29T03:52:33Z, run `ok` | `public/data/dashboard.json` |
| Findings published | **142**; 66 ran out tonight; 78 are listed by a market store tonight | `capabilities.assortment_gap` |
| Matches the spec? | **yes**: 138 for 2026-09-28, as AC-164 says; 142 the next night | print-mode replay |
| Depth of the evidence | **139 of 142 ran out at one store; 45 of 142 on one night of 13** | `evidence.stores_ran_out`, `nights_ran_out` |
| Answers recorded | **0** of 142 | `measurement.json` → `by_family["assortment.market_ran_out"]` |
| Turned off | Without the catalogue: unavailable, `market_running_out` untouched. Without the market snapshots: unavailable | `check_v1_signals.py`, `check_order_signals.py` |
| Rule 8 | **yes**: no value, no ₪, no quantity on any entry | `entries[].value`, `evidence` |
| Rule 13 | Honoured: it reads nightly delivery-catalogue snapshots, never the monthly reports | `src/market/recent.py` |

---

## What surprised me

Nearly every finding is one store's word. 139 of the 142 rest on a single store's listing
dropping out, and a third on a single night. The card says exactly that, but "one store,
one night" is also what a delisting or a scrape gap looks like.

## Not checked, and why

- The card on the deployed URL: it needs a sign-in. The component tests, the approved
  screenshots and the artefact were read instead.
- NFR-071 on a fresh clone: cited from #259's measurement, not repeated.
- Whether a single-night finding is a real sell-out: nothing in the data can tell a sell-out
  from a delisting or a missed scrape.

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| AC-167, SCN-156 and FR-171's "reconciliation keeps two" describe the allocation before D-26. The AC-167 test's policy lacks `rotate` while its comment says it matches `configs/policy.yaml` | smartshelf-architect (a dated note in F9-S1), then smartshelf-engineer (the test's policy or comment) | A criterion and a test describing a Today that no longer exists |
| Decide whether a finding seen at one store on one night is enough to show (45 of 142 today), or whether ADR-031's thresholds should ask for more | smartshelf-pm | Thin evidence is the likeliest false finding, and the owner's time is the cost |
| F9's intent has no success line | smartshelf-pm | Nothing says what a good result would be, once a store owner answers |
| The Phase 6 plan's NFR-071 note measured a local run, not a fresh clone | smartshelf-architect | 133 s on a fresh clone on the same day went unnoticed until #259 |
