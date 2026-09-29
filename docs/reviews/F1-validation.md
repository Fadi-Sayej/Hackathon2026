---
ID: F1-VALIDATION
Title: F1 — Delivery-Platform Price Consistency · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F1-S1](../features/F1-delivery-price-consistency/specs/F1-S1-delivery-price-consistency.md)
Inputs: [docs/features/F1-delivery-price-consistency/specs/F1-S1-delivery-price-consistency.md, docs/features/F1-delivery-price-consistency/intent.md, docs/implementation/phase-1-capabilities.md, public/data/dashboard.json and measurement.json (2026-09-29), src/engine/price_consistency.py, src/engine/model.py, src/surface/compose.js, tests/engine/test_price_consistency.py, tests/engine/test_model.py, docs/reviews/F7-validation.md, GitHub deployment records (Production); run 1 also read public/data/operational.json, src/recommendations/operational_recommendations.py and scripts/print_figures.py]
Updated: 2026-09-29 (run 2; run 1 of 2026-09-12 kept below as written)
---

# Validation F1 — Delivery-Platform Price Consistency

## Run 2 — 2026-09-29

Run 1 (below) validated a feature that did not exist yet: Task 1.2 was unbuilt, and the owner's
screen read the pre-spec `operational.json`. Since then:
- Task 1.2 was built (`534122a`, 2026-09-12);
- the browser was cut over to the engine's artefact (Task 2.7, 2026-09-12);
- the old path was deleted (`0a88154`, 2026-09-24).

This run checks the built feature.

- **Deployed URL:** `https://hackathon2026-fadi19.vercel.app` (serves the sign-in page; ADR-029).
- **Commit in production:** `e8f4ea7`. GitHub deployment `6738113055`, `success`, 2026-09-29 15:03Z.
- **Artefact read:** `public/data/dashboard.json` at `b215b0c`, `generated_at 2026-09-29T03:52:33Z`, run `ok`; `measurement.json` from the same run.
- **Context:** the pilot with the YomYom store ended on 2026-09-27 (D-23). The POS export behind every price here is dated 2026-06-06.

### Verdict

**F1 conforms, and its numbers held.** The artefact classifies 5,986
price pairs into the four states. It derives the 18% ceiling from the store's own markups,
and it surfaces 199 products (3.3%), well under the 10% guard. The intent's 68 inverted and
its 18% reproduce exactly. F1 also fills the whole money half of Today: all seven places
for work with a ₪ figure are its inverted prices, every day. The pilot's only recorded
decision was on one of them, a "Later". AC-009 is met by construction rather than by a test.

### Pass one — conformance

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §15 | AC-001 | identical products appear in no surfaced count | **met** | `counts.identical` 4,671 of 5,986; 0 of 199 entries have a 0% markup. `test_ac_001_identical_never_surfaces_and_ac_002_states_are_distinguishable` |
| spec §15 | AC-002 | inverted = confirmed loss, distinguishable from above-ceiling | **met** | 68 `price.inverted` / `confirmed_loss`, 131 `price.above_ceiling` / `question`; two families. Same test |
| spec §15 | AC-003 | no above-ceiling product labelled a loss | **met** | All 131 are `question` with no `value`. `test_ac_003_above_ceiling_is_never_a_loss_and_carries_no_value` |
| spec §15 | AC-004 | the ceiling reported with every dependent count, and reproduced | **met** | `thresholds`: `ceiling_pct 18`, `ceiling_source derived`, `ceiling_method densest_density_collapse`, the bands; every entry's evidence carries `ceiling_pct 18`. `npm run figures` reproduced every `price_consistency.*` figure on 2026-09-28 (F7-validation AC-127). `test_ac_004_ceiling_reported_with_counts`, `test_pilot_ceiling_reproduces_18_percent` |
| spec §15 | AC-005 | no distinguishable ceiling → above "undetermined", not zero; inverted still shown | **met in tests** | `test_ac_005_undetermined_ceiling_suppresses_above_keeps_inverted`, `test_ceiling_undetermined_on_a_flat_distribution`. On real data a ceiling is found |
| spec §15 | AC-006 | artefacts absent and counted | **met** | `counts.excluded_artefact` 23; no entry has a shelf price under ₪0.50. `test_ac_006_artefacts_are_excluded_and_counted` |
| spec §15 | AC-007 | no per-day or days-remaining claim | **met** | Evidence keys are `shelf_price`, `delivery_price`, `difference`, `markup_pct`, `ceiling_pct` and `commission_compounds` only. `test_ac_007_no_velocity_keys_in_evidence` |
| spec §15 | AC-008 | surfaced ≤ 10% of price-paired | **met** | 199 of 5,986 = 3.3%. `test_ac_008_signal_density_guard` |
| spec §15 | AC-009 | a decision stays retrievable after the ceiling moves and reclassifies the product | **met by construction; no end-to-end test** | `entry_id(signal_family, barcode)` has no threshold in it (`model.py:51`; `test_entry_id_is_stable_and_independent_of_thresholds`), and outcomes are never deleted. A product that moves from above-ceiling to inverted changes family, so it gets a new id. The old decision stays retrievable but does not carry over to the new finding. No test moves a ceiling under a recorded outcome |
| spec §7 | INV-001 | loss only when delivery < shelf | **met** | All 68 `confirmed_loss` entries have a negative `difference` |
| spec §7 | INV-002 | ceiling traceable to the store's data | **met** | `ceiling_source: derived`, bands published; `owner_declared_ceiling_pct` unset (GAP-011) |
| spec §7 | INV-003 | surfaced < paired | **met** | 199 < 5,986 |
| spec §7 | INV-004 | identical never counted as surfaced | **met** | As AC-001 |
| spec §7 | INV-005 | no velocity claim | **met** | As AC-007 |
| spec §13 | NFR-001 | enough evidence on the card to check it against the POS | **met** | Every entry carries both prices, the difference and the markup, and the card shows them (`EntryCard.jsx`; `cardsSayWhatToDo.test.jsx`, `DailyPage.test.jsx`). Today states the POS date above the cards since #235 |
| spec §13 | NFR-002 | same data → same classification and ceiling | **met** | As AC-004 |
| spec §13 | NFR-003 | ≤ 10% surfaced | **met** | As AC-008 |
| spec §19 | INT-001, INT-NS, INT-PROV, protected | traced to an AC | **met** | Every §19 row names an AC, and each AC is above |

### Scope drift

| Change | In a plan task's `Files:` list? | In spec §3 scope? | Note |
|---|---|---|---|
| `534122a`: `price_consistency.py` and its tests | **yes** (Task 1.2) | yes | — |
| `99ebcba`: the published population as policy | no | yes | ADR-020 |
| `86b2f20`: the owner's stated ceiling wins, the derived one kept beside it | no | yes (FR-004's derivation survives) | GAP-011; the plan's release conditions name it |

### Shipped but never requested

- `counts.excluded_gap` and `max_credible_gap_pct: 300`: the old `credibility.js` guard,
  kept as a counted exclusion (System Design §22.2) and named in Task 1.2's interface. No
  F1-S1 line asks for it. It excludes 0 today.

### Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F1-delivery-price-consistency/intent.md`.*

**PROBLEM («لا أريد أن أخسر في كل عملية بيع»): is the owner measurably less stuck?** The
losses are found and shown: 68 products whose delivery price is below the shelf price, each
with its ₪ per sale. Whether any was fixed is not known: 0 were marked done, and the pilot's
single decision was a "Later" on one of them (2026-09-17).

**SUCCESS — count it.** The intent's table, against the artefact:

| | Intent | Artefact |
|---|---:|---:|
| Delivery cheaper than the shelf (inverted) | 68 | **68** |
| Ceiling | 18% (81 → 8 across 16–18% / 18–20%) | **18%** (73 → 8) |
| Above the ceiling | 136 | **131** |
| Identical | 4,932 of 6,260 | **4,671 of 5,986** |
| F1's share of the 387 alerts (rows 1 and 4) | 204 | **199** |

The population is 274 smaller than the intent's; this run did not trace why.

**USER: would the owner recognise it?** Yes. The olive oil the intent names (shelf ₪37.90,
Wolt ₪21.90) is the first card on Today, ₪16 per sale.

**NOT NOW: anything deferred built?** No competitor comparison (F3's), no margin against cost
(`margin_below_cost` publishes 34 valued entries but is not admitted to Today), no suggested
price: the action is `verify_price`.

**Would you write the same intent again?** Yes. Its two headline numbers, 68 and 18%,
reproduce exactly. Its figures came from the POS export alone, which the engine reads too,
so nothing in them depended on data that was later replaced.

### Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| Entries on the daily surface today | **7**, the seven places for work with a ₪ figure, the largest ₪ per sale first (₪16, ₪11, ₪7, ₪4, ₪4, ₪3.10, ₪3) | `compose()` over the committed artefact, empty owner state, 2026-09-29 |
| `generated_at` | 2026-09-29T03:52:33Z, run `ok` | `public/data/dashboard.json` |
| Findings published | 199: 68 inverted, 131 above the ceiling | `capabilities.price_consistency` |
| Decisions over the pilot | 1 of 68 inverted (deferred), 0 of 131 above | `measurement.json` → `by_family` |
| Turned off | Withholding `products` makes it unavailable, and nothing it does not declare moves it | `check_v1_signals.py`, all OK on 2026-09-29 |
| Rule 8 | **yes**: 68 `per_sale` `confirmed` values, never summed; the questions carry none | `entries[].value` |
| Rule 13 | Honoured: prices only, no sales claim | evidence keys |

### What surprised me

F1 has no competition for the money half of Today. `margin_below_cost` is the only other
capability that publishes ₪ values, and it is not admitted. So the seven places for work
with a ₪ figure are F1's every day, until the 2026-06-06 export is replaced. That will not
happen under D-23.

### Not checked, and why

- The card on the deployed URL: it needs a sign-in. The artefact, the composed Today and the
  component tests were read instead.
- Why the population is 5,986 and not the intent's 6,260.
- AC-009 end to end: no test moves a ceiling under a recorded outcome.

### Open items

| Item | Owning role | Why it matters |
|---|---|---|
| A test for AC-009: record an outcome, move the ceiling, and show the outcome is still retrievable and applies while the family is unchanged | smartshelf-engineer | Met by construction only |
| Say whether a decision on an above-ceiling question should follow the product when it becomes inverted (a new family, so a new id) | smartshelf-architect | C-4 says "remain valid"; today it stays stored but stops applying |
| ~~Run 1: build Task 1.2~~ **Done** (`534122a`, 2026-09-12) | — | — |
| ~~Run 1: decide what the pilot shows before Task 1.2~~ **Moot**: the cut-over (Task 2.7) came the same day | — | — |
| ~~Run 1: record `operational_recommendations.py` as the incumbent~~ **Moot**: it was deleted on 2026-09-24 (`0a88154`) | — | — |
| ~~Run 1: re-run against the deployed URL~~ **Done** (this run; the page itself needs a sign-in) | — | — |

---

## Run 1 — 2026-09-12, kept as written

Deployed URL: **not verified** — this validation was run against the repository and the
committed artifact only. Every verdict below is therefore repository-level; none of them
has been confirmed on the live pilot URL.
Artifact read: `public/data/operational.json`, `meta.generatedAt` **2026-09-10T02:37:09Z**
Figures recomputed: `npm run figures` (`scripts/print_figures.py`), run **2026-09-12**

## Headline

**F1-S1 is `Approved`. Its product implementation is Phase 1 Task 1.2, and that task has
not been built.** `src/engine/` currently holds `model.py`, `policy.py` and `registry.py`
only; `price_consistency.py` does not exist.

The spec's logic is nonetheless real and reproduces today — in the **reporting** path,
`scripts/print_figures.py`. What the owner's daily screen reads, `public/data/operational.json`,
is still produced by the pre-spec engine. **The two paths disagree, and the owner sees the
older one.**

| | Reporting path (`npm run figures`) | Product path (`operational.json` → the screen) |
|---|---|---|
| Threshold | **18%**, derived from his own data | **flat 5%** (`operational_recommendations.py:40`, `WOLT_GAP_MIN_PCT = 5.0`) |
| Identical (Wolt = shelf) | 4,932 (79%) — not shown | not shown |
| Within his policy (0–18%) | 1,124 — **not shown** | **965 shown** |
| Inverted (Wolt < shelf) | 68 — confirmed loss | 46, not labelled as loss |
| Above his policy (>18%) | 136 — question | 136 (124 in 18–60%, 10 in 60–90%, 2 >90%) |
| Entry artefacts excluded (D-4) | 27, count reported | only `sell <= 0` |
| **Total surfaced** | **204** | **1,147** |

**84% of what the owner is shown today (965 of 1,147) is the band F1-S1 says must never
be surfaced, because it is his own sound policy.**

---

## Pass one — conformance

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| §15 | AC-001 | Identical products appear in no surfaced count | **met** | Both paths exclude 0% gaps; the 5% gate excludes all 4,932 |
| §15 | AC-002 | Inverted surfaced as confirmed loss, distinguishable from above-ceiling | **missing** (product path) | One `recommendation_type` for all 1,147; one reason template (`operational_recommendations.py:310`). Only the sign of `metricValue` separates them, and nothing labels it. Met in the reporting path |
| §15 | AC-003 | No above-ceiling product labelled a loss | **met** | Reason reads *"…align or confirm intentional"* — a question, never a loss assertion |
| §15 | AC-004 | Ceiling reported alongside every dependent count, and recomputable | **partial** | Reproduces via `npm run figures` (18%, from his data). Absent from `operational.json` — every owner-facing count cites no ceiling |
| §15 | AC-005 | No distinguishable ceiling ⇒ reported undetermined, not zero | **not verifiable** | The product path derives no ceiling, so there is no state for it to report |
| §15 | AC-006 | Artefact products absent, count retrievable | **partial** | `print_figures.py` excludes 27 and reports the count; the dashboard path excludes only `sell <= 0` |
| §15 | AC-007 | No per-day or days-remaining claim | **met** | No velocity term in the reason template |
| §15 | AC-008 | Surfaced ≤ 10% of price-paired products | **missing** | 1,147 of 6,260 price-paired = **18.3%** |
| §15 | AC-009 | Owner decision retrievable after the ceiling changes | **not verifiable** | No ceiling in the product path; no owner decision recorded against this signal |
| §7 | INV-001 | No loss claim unless delivery price strictly below shelf | **met** | Nothing is labelled a loss anywhere |
| §7 | INV-002 | Ceiling traceable to his own observed data | **partial** | True in the reporting path; no ceiling in the product path |
| §7 | INV-003 | Surfaced count strictly less than price-paired count | **met** | 1,147 < 6,260 — but see AC-008; the weak form holds while NFR-003 is breached |
| §7 | INV-004 | Identical never surfaced under any threshold | **met** | — |
| §7 | INV-005 | No velocity claim | **met** | — |
| §19 | INT-001 | Traced to AC-001…005 | **partial** | Traced in the document; unsatisfied in the product path |

### Scope drift

| File changed | In Task 1.2's `Files:`? | In spec §3? | Note |
|---|---|---|---|
| — | — | — | **No drift: nothing was built.** `src/engine/price_consistency.py` and `tests/engine/test_price_consistency.py` are both absent |

### Shipped but never requested
- `src/recommendations/operational_recommendations.py` predates F1-S1 and implements a
  different rule (flat 5%). It is not scope drift — it is the incumbent the spec was
  written to replace — but it is what the owner sees, and no document says so.

---

## Pass two — fidelity

*The spec and the plan are closed. Read only `docs/features/F1-delivery-price-consistency/intent.md`.*

**PROBLEM:** «لا أريد أن أخسر في كل عملية بيع» — is he measurably less stuck?
**No.** The intent's central correction is that 79% of his items are priced identically
and most of the rest sit inside his own deliberate 0–18% policy. He is shown 1,147 items
today, 965 of them inside that policy. He is being asked to review his own correct
decisions — which is the exact failure the intent was written to stop.

**SUCCESS — count it. What is the number?**
204 items would be surfaced under the approved rule; 1,147 are surfaced. The gap is
**943 items he should never have been shown.**

**USER — would he recognise this as built for him?**
Partly. The reason text already asks *"align or confirm intentional"* rather than
declaring a loss, which is the intent's tone and honours INV-001. But the volume denies
the message: 1,147 questions is not a daily screen, and D-9 caps the surface at 10 actions.

**NOT NOW — did anything deferred get built anyway?**
No.

**Would you write the same intent again?**
Yes. It is the strongest document in the repository — it corrected its own earlier claim
using the owner's data and derived the 18% ceiling from an observable density collapse
rather than assumption. The failure here is delivery, not intent.

---

## Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| Entries contributed to the daily surface today | 1,147 | `operational.json` `byType.CHECK_WOLT_PRICE_GAP` |
| `meta.generatedAt` of that artifact | 2026-09-10T02:37:09Z | same |
| Does the count match what the approved spec says it should be? | **No — 1,147 vs 204** | `npm run figures`, 2026-09-12 |
| What changes if the signal is turned off | 1,147 entries disappear, of which 943 should never have appeared | distribution computed from `recommendations[].metricValue` |
| Every figure obeys rule 8 (kinds not summed · no shekel on a quantity signal · no number rather than zero) | **yes** | `print_figures.py` prints the per-sale and standing totals separately and warns in Arabic against adding them |
| Anything claimed the monthly data cannot support (rule 13) | **no** | This signal is derived from prices alone and asserts nothing about sales |

---

## What surprised me

The spec's hardest part — deriving the 18% ceiling from the owner's own price
distribution — **is built and reproduces on demand.** It just lives in the script that
prints figures for us, not in the pipeline that feeds his screen. The analysis crossed
into our reporting and never crossed into his product. That is CLAUDE.md rule 12's
failure mode exactly, and it survived because `print_figures.py` makes the correct
numbers easy to demonstrate in a meeting while the screen keeps showing the old ones.

## Not checked, and why

- **The deployed URL.** Everything here is repository-level. A pilot deploy could be
  serving an older artifact still.
- **Arabic and Hebrew rendering** of the surfaced entries.
- **The 6,260 price-paired denominator** was taken from `npm run figures`, which
  recomputes it; it was not independently recomputed from the source parquet.
- **Whether the 46 inverted entries in `operational.json` are a subset of the 68** the
  figures script reports. The counts are consistent with the 5% gate, but the
  product-level identity was not confirmed row by row.

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| Build Task 1.2 (`src/engine/price_consistency.py`) — the four states and ceiling derivation | smartshelf-engineer | Until it exists the owner sees the pre-spec rule |
| Decide what the pilot shows **between now and Task 1.2** — 1,147 entries contradicts the approved spec and D-9 | smartshelf-pm | This is a live pilot surface, not a staging one |
| Record that `operational_recommendations.py` is the incumbent F1-S1 replaces, and that the two paths currently disagree | smartshelf-architect | No document states it; the next reader will assume the screen reflects the spec |
| Re-run this validation against the deployed URL | smartshelf-platform | Every verdict here is repository-level |
