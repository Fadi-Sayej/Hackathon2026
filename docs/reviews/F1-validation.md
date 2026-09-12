---
ID: F1-VALIDATION
Title: F1 — Delivery-Platform Price Consistency · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F1-S1](../features/F1-delivery-price-consistency/specs/F1-S1-delivery-price-consistency.md)
Inputs: [docs/features/F1-delivery-price-consistency/specs/F1-S1-delivery-price-consistency.md, docs/features/F1-delivery-price-consistency/intent.md, docs/implementation/phase-1-capabilities.md, public/data/operational.json, src/recommendations/operational_recommendations.py, scripts/print_figures.py]
Updated: 2026-09-12
---

# Validation F1 — Delivery-Platform Price Consistency

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
