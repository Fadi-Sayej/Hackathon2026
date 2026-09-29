---
ID: F3-VALIDATION
Title: F3 — Competitor Price Position · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F3-S1](../features/F3-competitor-price-position/specs/F3-S1-competitor-price-position.md)
Inputs: [docs/features/F3-competitor-price-position/specs/F3-S1-competitor-price-position.md, docs/features/F3-competitor-price-position/intent.md, docs/operations/deployment.md, public/data/dashboard.json (2026-09-28), src/engine/competitor_position.py, src/pages/PriceGapPage.jsx, src/pages/CapabilityPage.jsx, src/surface/EntryCard.jsx, src/lib/i18n/dictionaries/, scripts/check_v1_signals.py, GitHub deployment records (Production)]
Updated: 2026-09-29
---

# Validation F3 — Competitor Price Position

- **Deployed URL:** `https://hackathon2026-fadi19.vercel.app` (serves the sign-in page; ADR-029).
- **Commit in production:** `2a716ec`. GitHub deployment `6708764605`, `success`, 2026-09-28 11:29Z.
- **Artefact read:** `public/data/dashboard.json` at `2a716ec`, `generated_at 2026-09-28T03:10:39Z`, run `ok`.
- **Context:** the pilot with the YomYom store ended on 2026-09-27 (D-23). Every "owner" below is
  the owner the feature was built for; nobody is using it now.

## Verdict

**Conformance passes in the artefact on every criterion that has one, and is partial on the
screen for two** (AC-042, AC-053): the owner never sees which store or format a comparison came
from, nor that a reference is a supermarket price plus the measured allowance. **Fidelity is
where F3 falls short:** the intent measured 144 products over the +60% policy (97 after the cost
gate, about 15 of them for the morning screen); the engine publishes **1** breach and **0** for
the morning screen. **Usefulness today is the Prices page, not a finding:** 873 products positioned
against a reference, 396 of them dearer, and one review-only breach.

---

## Pass one — conformance

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §15 | AC-040 | no surfaced recommendation traceable to an excluded source | **met** | No store in `position` (164) has affinity 0; every source behind the 6 entries has a positive affinity. `_shape_observations` in `src/engine/inputs.py` drops excluded stores, and the store's own, before any capability sees them (C-20, D-5) |
| spec §15 | AC-041 | none traceable solely to a context-only source while OQ-301 is unresolved | **met as amended, with a tension** | OQ-301 is resolved (a cross-format price forms half a balanced reference). But the one policy breach rests on **118 sources, all labelled `context`**: its reference is `supermarket_plus_allowance` (Victory, affinity 0.1, ₪5.20 + 7.0779%). FR-044a permits exactly that; C-21 says a store below the floor "may not drive a recommendation". The artefact labels the driving store `context` while it drives. See *Open items* |
| spec §15 | AC-042 | every displayed observation shows the observing store's format | **partial** | In the artefact: every source carries `format`, and every entry carries `format_note` ("part of any difference is attributable to store format"). **On screen:** no page shows an individual observation. The Prices page shows a count of shops (`prices.col.shops`); the finding page (`CapabilityPage.jsx:66-72`) shows only the product and its characterisation |
| spec §15 | AC-043 | policy, attention, cost floor and allowance reported with every count, and reproducible | **met** | All 13 `competitor_position.*` figures carry `policy_pct 60`, `attention_pct 100`, `cost_floor_pct 10`, `format_allowance_pct 7.0779` (basis 403). Reproduced by `npm run figures` (`test_figures_cli`, 12 passed on 2026-09-27 with the market half built) |
| spec §15 | AC-044 | coverage against the full catalogue, structurally uncomparable separated | **met** | `counts`: catalogue 7,523 · comparable population 6,801 · structurally uncomparable 722 · matched 2,614 · no comparison 5,928 |
| spec §15 | AC-045 | no comparison shows "no comparison", never a zero difference | **met** | 1,805 `comparison` rows have no premium, each with a reason (`no_reference` 1,703 · `stale` 62 · `no_shelf_price` 40); **0** carry a premium without a reference. The Prices page has a "No comparison" tab and a reason per row (`PriceGapPage.test.jsx`, "says why for every product it could not compare") |
| spec §15 | AC-046 | position against each comparable peer, including when favourable | **met** | `position` publishes `cheaper_here`, `dearer_here`, `median_diff_pct` per store; e.g. Wolt Market: 81 cheaper here, 40 dearer, median −5.57% |
| spec §15 | AC-047 | no difference called an error; each breach names the policy | **met** | The breach is `policy_breach_review` ("Outside your policy — review") with `policy_pct 60` in its evidence. No family or characterisation says "error" or "wrong" |
| spec §15 | AC-047a | a format-only difference is never a fault | **met** | `format_note` on all 6 entries; the allowance is applied before the policy |
| spec §15 | AC-047b | no reference is the store's own price | **met** | References are built from competitor observations only (`balanced_reference` over `obs`); none of the 6 references equals its own shelf price |
| spec §15 | AC-049 | no price-reduction signal whose reference fails the cost floor | **met** | The one breach: reference ₪5.57 ≥ cost ₪2.59 × 1.10 |
| spec §15 | AC-050 | a cost-floor failure is a purchase-cost finding | **met** | 5 `competitor.purchase_cost` entries, each failing the floor, `check_purchase_cost`, none a pricing fault |
| spec §15 | AC-051 | no purchase cost → absent from the policy comparison, no assumed cost | **met** | `no_cost_skipped` 36; those rows publish the reference and position with `uncompared_reason: no_cost` and no verdict; the page marks them "not judged" |
| spec §15 | AC-052 | both prices held → midpoint | **met** | 219 references are `midpoint`; e.g. (₪24.90 + ₪21.90) / 2 = ₪23.40 |
| spec §15 | AC-053 | no same-format price → the allowance is visible and reproducible | **met in the artefact, partial on screen** | 510 references are `supermarket_plus_allowance`, each carrying `allowance_pct 7.0779`, measured by `measure_format_allowance` from 403 products. The Prices page's "Reference" column does not say that a reference is a supermarket price plus 7.08% |
| spec §15 | AC-054 | every product over the policy recorded as a breach, whatever surface shows it | **met** | `breaches` 1 = policy-breach entries 1; over-60% rows in `comparison`: 1 |
| spec §15 | AC-048 | an observation past the freshness bound drives nothing | **met** | 0 sources behind a finding are older than 14 days; 62 products seen only in stale prices get a `stale` row and no verdict |
| spec §7 | INV-020 … INV-026 | excluded source, format, format-only fault, coverage, own price, cost floor, balanced reference | **met** | As AC-040, AC-042 (artefact), AC-047a, AC-044, AC-047b, AC-049. INV-026: all 510 allowance-based references have no same-format price to balance with |
| boundary probe | rule 12 | F3 depends on exactly what it declares | **met by hand; not in the probe** | `check_v1_signals.py` withholds only `products`, `inventory`, `sales_summary` and `window`; it never withholds `observations` or `matches`. Run by hand on 2026-09-28 (`run_engine(mode="print", skip_market=True)` with an empty signals directory, then a missing matches file): `competitor_position` goes `unavailable (no_competitor_data)` both times, and `price_consistency` and `market_running_out` stay available |
| spec §19 | INT-003, INT-PROV, protected | traced to an AC | **met** | Every row of §19 names an AC; each is above |

### Scope drift

| Change | In a plan task's `Files:` list? | In spec §3 scope? | Note |
|---|---|---|---|
| `63c3492`: SPEC-003 built | yes, Phase 1 | yes | — |
| `79e352b` #137: publish the comparison behind a finding | **ADR-025** | yes (FR-050, FR-053) | Adds `comparison`, which the Prices page reads |
| `6d41319` #154: count stale prices over the store's own products, a row each | **issue #154**, not a plan task | yes (NFR-022, FR-051) | Handover rule 6 wants a spec id; the issue names FR-051 |

### Shipped but never requested

The Prices page's three tabs and search (`PriceGapPage.jsx`) go beyond FR-053's "able to report
the position". They are the most useful part of F3 today (Pass three).

---

## Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F3-competitor-price-position/intent.md`.*

**PROBLEM («هل أسعاري معقولة مقابل الجيران؟»): is the owner measurably less stuck?** Partly. He can
see, per product, whether he is dearer or cheaper than a balanced reference, and 477 of 873
compared products say "same or cheaper". But the intent's promise was a short list of prices to
review, and that list is one product long.

**SUCCESS — count it.** The intent measured, on the pilot data: 1,970 products with a competitor
price; **144** over the +60% policy; **97** after the cost gate; **~15** over 100% for the
morning screen. The artefact today: 2,614 matched, 873 with a reference, **1** over the policy,
**1** after the gate, **0** over 100%. The gap is not the cost gate (it removed 5, not 47). It is
the reference: the intent's first reference was the Alonit station 1,400 m away, with **755**
comparable products; the only gas-station store in today's `position` is Super Alonit, Kibbutz
Einat, with **5** matched products. Most references (510 of 873) are a supermarket price plus the
measured 7.08%, and the 157 national price-file stores are `unknown` format, context only.

**USER: would the owner recognise it?** The Prices page, yes: his products, his prices, in his
language, the gap first. The finding page, less so: a competitor finding shows only its product
and one line, with none of the prices behind it.

**NOT NOW: did anything deferred get built?** No. No corrected price is suggested; no history is
kept; the store set is the collector's.

**Would you write the same intent again?** Not its numbers. The policy (+60%) and the cost gate
held up. The counts in §3ب came from a reference set the engine does not reproduce, so they
promised a list the feature cannot deliver on this collector's data. The intent should either
name the reference it measured against, or be re-measured on what the collector holds.

---

## Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| Entries on the daily surface today | **0.** Entries without money share three reserved places, handed out in the order `reconciliation` → `competitor_position` → `catalogue_lifecycle` → `hygiene` (`thresholds.surface`, `compose.js`); reconciliation's 355 fill all three every day until the owner settles them. F3's 6 reach it only after those. The surface's 10 are F1 (7) and F2 (3). (`attention` plays no part in admission: with F1's and F2's entries removed, `compose` admits 3 of F3's) | `compose()` over `public/data/dashboard.json`, `now` 2026-09-28 08:00Z |
| `generated_at` | 2026-09-28T03:10:39Z, run `ok` | `public/data/dashboard.json` |
| On its own pages | Prices: 396 dearer · 477 same or cheaper · 1,805 no comparison. Findings: 1 breach, 5 purchase-cost | `capabilities.competitor_position.comparison`, `.entries` |
| Matches the intent? | **no** — 1 breach against 144 (97 after the gate) | as Pass two |
| Turned off | `unavailable (no_competitor_data)`, nothing else moves (by hand; see the probe row) | `run_engine(mode="print")`, 2026-09-28 |
| Rule 8 | **yes** — no entry carries a `value`; premiums are percentages | `.entries[].value` |
| Rule 13 | not engaged: F3 reads daily prices, not the monthly reports | — |

---

## What surprised me

The one price F3 asks the owner to review is driven entirely by stores the artefact itself
calls `context`, and the gas station the intent was built around matches five products. F3 is
honest about everything it computes, and it computes almost nothing to act on.

A latent defect found on the way: `EntryCard.jsx` renders every evidence value with `String()`.
A competitor finding that reached the morning screen (once reconciliation's 355 are settled) would print its
`sources` and `reference` as `[object Object]`, under labels the Arabic and Hebrew dictionaries
leave in English (`evidence.sources` "sources", `evidence.reference` "reference",
`evidence.premium_pct` "premium pct", `evidence.policy_pct` "policy pct", `attention_pct`,
`cost_floor_pct` and `format_note`, the same seven in both). None
reaches it today, so nobody has seen it.

## Not checked, and why

- **Why** Super Alonit, Einat matches 5 products where the intent counted 755: that needs the
  matcher's output and the collector's store list, which is the architect's question, not a
  count.
- The Prices page on the deployed URL: it needs a sign-in; the tests and the artefact were read
  instead.
- Whether the owner acted on an F3 entry: **no** (2026-09-29: the first `measurement.json` (published 2026-09-29, `generated_at 03:52Z`) records **one** decision in the whole pilot: a deferral ("Later") on one `price.inverted` entry, on 2026-09-17. Nothing acted on, nothing dismissed, no money recovered; four devices had opened the app, the last on 2026-09-24).

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| ~~Reconcile the intent's 144/97/~15 with the engine's 1/1/0: which reference did the intent measure against, and is the Alonit station matched?~~ **Partly answered 2026-09-29 (`d0fea13`)**: none of the 157 stores in the national Dor Alon price file had a store type, so none could set a reference. The repository owner decided that the 57 AM-PM shops among them are neighbourhood minimarkets (`configs/store_types.yaml`). On the 2026-09-29 data in print mode, F3 then evaluates 2,036 products (was 835) and finds 13 breaches, 2 at the attention level (was 2 and 0). **Answered 2026-09-29**: the intent measured the same balanced reference against other data, the Kaggle-era files for Alonit Kafr Qasim, Rami Levy Petah Tikva and Shufersal Deal Petah Tikva (`scripts/classify_store_types.py:43-45`), whose importer was deleted on 2026-09-24 (`0a88154`). The Kafr Qasim station is not matched today: no store in the 2026-09-29 national file is named for it (its city column holds codes, so this rests on names), and the one forecourt shop the engine compares against is Super Alonit Kibbutz Einat, on Wolt, with 5 products. The intent now carries a dated note that its table is history | smartshelf-pm, then smartshelf-architect | F3's SUCCESS cannot be counted against numbers the engine does not reproduce |
| C-21 ("a store below the floor may not drive a recommendation") against FR-044a (a supermarket price plus the allowance): which binds? **Narrowed 2026-09-29 (`d0fea13`)**: 11 of the 13 breaches now have a same-format price in their reference; 2 still rest on `context` stores alone (`supermarket_plus_allowance`) | smartshelf-architect | The only breach is driven by `context` stores alone |
| ~~Add `observations` and `matches` to `check_v1_signals.py`'s withholding list~~ **Done 2026-09-28, #234 (`a651353`)**: both withheld, and `tests/test_check_v1_signals.py` refuses a required input no probe withholds | smartshelf-engineer | Rule 12: F3's market inputs are declared but never probed |
| ~~Show the reference's kind (and the allowance) and the sources' formats on screen, or record that FR-042 and FR-044a are met by the artefact alone~~ **Done 2026-09-29, #243**: the Prices page notes "supermarket + 7.1%" or "average of a supermarket and a shop like yours"; the sources' formats stay in the artefact | smartshelf-architect (decision), then smartshelf-engineer; a screen change needs the owner's approval | AC-042 and AC-053 are partial on screen |
| ~~`EntryCard.jsx` prints objects as `[object Object]`; seven `evidence.*` labels are English in `ar.js` and `he.js`~~ **Done 2026-09-28, #235** (approved by the owner; see `docs/reviews/card-wording-2026-09-28.md`) | smartshelf-engineer; the owner approves the wording | Latent until a competitor finding reaches the morning screen |
