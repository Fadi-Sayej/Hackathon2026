---
ID: F2-VALIDATION
Title: F2 — Stock Reconciliation and Data Hygiene · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F2-S1](../features/F2-stock-truth/specs/F2-S1-stock-reconciliation-and-hygiene.md)
Inputs: [docs/features/F2-stock-truth/specs/F2-S1-stock-reconciliation-and-hygiene.md, docs/features/F2-stock-truth/intent.md, docs/operations/deployment.md, public/data/dashboard.json (2026-09-24), src/engine/reconciliation.py, src/engine/inputs.py, src/surface/compose.js, src/surface/EntryCard.jsx, src/lib/i18n/dictionaries/, GitHub deployment records (Production)]
Updated: 2026-09-24
---

# Validation F2 — Stock Reconciliation and Data Hygiene

- **Deployed URL:** `https://hackathon2026-fadi19.vercel.app`. It returns 401 without credentials (verified 2026-09-24).
- **Commit in production:** `3bb38ce`. GitHub deployment `6635446258`, `success`, 2026-09-24 10:21Z.
- **Artefact read:** `public/data/dashboard.json` at `3bb38ce`, `generated_at 2026-09-24T02:46:37Z`, run `ok`.
- **Replaces** the 2026-09-16 record (last changed in `50abc45`; git holds it). What became of each of its findings is under *Since 2026-09-16*.

## Verdict

**Conformance passes on nine of ten acceptance criteria. AC-023 is partial**, and the 09-16
record marked it met on half its evidence. Fidelity passes, with one sentence missing, and
it is the intent's own. **Usefulness improved and is still where F2 is weakest:**
- The count is now honest: 355, where the 09-16 record found a vintage bug publishing 439.
- ADR-026 made each finding's period the months actually summed.
- But the owner's screen does not follow the nightly: every nightly deploy is blocked
  (#167). And every finding rests on one stock count from 2026-06-06, which is 110 days old
  today.

---

## Pass one — conformance

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §15 | AC-020 | negative implied opening flagged, others not; no receipts, never flagged; gap ratio descending | **met** | 355 entries, `ordering_key.name` `gap_ratio` for all, descending 6.3855 → 0.0036. **0** flagged with receipts ≤ 0. For **355 of 355**, `recorded_stock − receipts + units_sold < 0` recomputes from the entry's own published evidence |
| spec §15 | AC-021 | no flagged product carries money | **met** | **0 of 355** entries carry a `value` |
| spec §15 | AC-022 | no aggregate in currency | **met** | `counts` = `{flagged: 355}`. The only units in F2's figures are `products` and `records` |
| spec §15 | AC-023 | asked the size of the loss, the system states it is not determinable before a count, and offers no figure | **partial** | *No figure* is met: every entry is `value=None`, and `EntryCard.jsx` renders no value area for one ("not a dash, not a zero"). *States it is not determinable* has **no surface**: nothing in V1 lets the owner ask, and the copy System Design §21 names for FR-026 ("i18n copy for 'not determinable before a count'") exists in **no** dictionary. The page's description says only that received and sold do not balance |
| spec §15 | AC-024 | every flagged product shows the three quantities and the unaccounted | **met** | All of `recorded_stock`, `receipts`, `units_sold`, `unaccounted` are present and non-null on **355 of 355**. Since ADR-026 the period beside them is the span they were summed over: `window_id` `2026-01..2026-05` on every entry, `reconcile_before` `2026-06` |
| spec §15 | AC-025 | no hygiene record carries money | **met** | **0 of 1,117** hygiene entries carry a `value` (578 negative stock · 248 no identifier · 223 absent price · 68 conflicting duplicate) |
| spec §15 | AC-026 | no surface sums a recurring and a standing figure | **met** | `src/surface/compose.js:70-75` orders kinds as contiguous runs, never interleaved |
| spec §15 | AC-027 | no output states or implies a cause | **met** | One family (`recon.impossible_opening`), one characterisation (`inconsistent` → *"Numbers that do not add up"*), one action (`count_product`). No wording names theft, breakage or entry error |
| spec §15 | AC-028 | recomputation reproduces the flagged set and its ordering | **met** | Two local `run_engine(mode="print")` runs over a copy of the silver tables are identical. More than the criterion asks: that local run equals **CI's published 2026-09-24 artefact** entry for entry (ids, evidence, ordering, actionability), for both `reconciliation` and `hygiene` |
| spec §15 | AC-029 | a decision survives the product ceasing to be flagged | **met, as mechanism** | Outcomes are keyed on `entry.id` (`src/owner/ownerState.js`), and ADR-009 keeps that id stable. **Not exercised:** see *Not checked* |
| spec §7 | INV-010, INV-011, INV-013 | no money on a flagged product, an aggregate or a hygiene record | **met** | As AC-021, AC-022 and AC-025 |
| spec §7 | INV-012 | detection valid whatever the sign of an input | **met** | **81** of the 355 flagged products have negative recorded stock. The rule reads raw stock and clamps nothing |
| spec §7 | INV-014 | per-sale and standing never summed | **met** | As AC-026 |
| spec §7 | INV-015 | never asserts where the stock went | **met** | As AC-027 |
| boundary probe | rule 12 | detection and hygiene fail independently; each capability depends on exactly what it declares | **met** | On `3bb38ce` over copied data, `check_independence` exits 0: *"detection 355 flagged with the reports, unavailable (no_sales_evidence) without them"*, hygiene 1,117 → 1,117. `check_v1_signals` exits 0: *"every capability depends on exactly what it declares"* |
| spec §19 | INT-002, INT-002B, INT-PROV, protected | traced to an AC | **met** | INT-002 → AC-020–024, 026, 027. INT-002B → AC-025. INT-PROV → AC-028. Protected behaviour → AC-029. No row is without an AC |

### Scope drift

This covers the changes that reached F2 since 2026-09-16.

| Change | In a plan task's `Files:` list? | In spec §3 scope? | Note |
|---|---|---|---|
| #160: the reconcile cut moved to `load_inputs` (ADR-026) | **yes**, ADR-026's Implementation list as corrected in `630667c` | yes | The correction was an engineer's edit to an accepted ADR; the owner ratified it 2026-09-24 (#164) |
| #163: the importer collapses a report's reprinted lines | **no plan task.** Traced to issue #156, not to a spec id | yes (the inputs of FR-020) | Its own verification (#163) reports the published artefact unchanged; not re-measured here. Recorded because handover rule 6 asks for a traceable id and an issue is not one |
| #165: a comment in `reconciliation.py` | n/a (comment only) | n/a | — |

### Shipped but never requested

Nothing new.

---

## Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F2-stock-truth/intent.md`.*

**PROBLEM (INT-002, «أين يختفي مخزوني؟»): is the owner measurably less stuck?** On the
list, yes:
- 355 products whose arithmetic cannot close, worst first.
- Each has the three quantities and, since this week, the true period they cover. An owner
  can now check a card against his own January–May records and get the same totals, which
  was not true before ADR-026.

Whether he *has* acted on it is **not measurable from any artifact here**. The artefact
publishes that 4 devices have written owner state (the last on 2026-09-23), but no outcome
counts. The pilot measurement that would count them is ADR-023, still `Ready for review`.

**SUCCESS: is it countable?** The intent sets no numeric line. Its claim is negative (*no
amount, by deliberate decision*), and that counts **zero**: no entry, aggregate or figure in
either half carries currency.

**USER: would the owner or the stocktaker recognise it as built for them?** Mostly.
- Product names are his Hebrew listings. The action is *count this product*, which is the
  stocktaker's job.
- Five of the six evidence labels on the Hebrew card are Hebrew. **The sixth is English:
  `evidence.reconcile_months` → "reconcile months" in `he.js`.**
- The period prints as the raw id `2026-01..2026-05`. `EntryCard.jsx` renders evidence with
  `String(raw)`, so the period is now true but still not in his language.

**NOT NOW: did anything deferred get built?** No. No correct quantity is proposed, no cause
is apportioned, and nothing writes to the POS.

**Would you write the same intent again?** Yes. But its governing sentence has no
owner-facing sentence in the product. *«والرقم الحقيقي يُعرف بعد العدّ، لا قبله»*, "the real
number is known after the count, not before", is exactly what FR-026 and AC-023 owe him, and
it is the half of AC-023 that is missing. The product withholds the figure correctly and
never tells him why.

---

## Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| Entries F2 contributes to the daily surface today | **3 of 10**: the surface is `{price_consistency: 7, reconciliation: 3}`. **Hygiene: 0 of 1,117** | the real `compose()` from `src/surface/compose.js`, run over the 2026-09-24 artefact with no outcomes |
| `generated_at` of the artefact read | 2026-09-24T02:46:37Z | `public/data/dashboard.json` at `3bb38ce` |
| Does the count match what it should be? | **yes**: 355 on the true stock date (`as_of 2026-06-06`, `declared_sidecar`). The 09-16 record measured 355 as the honest count against a published 439 | artefact `vintages.pos`, `counts` |
| Turn the signal off | withholding the reports takes `reconciliation` to `unavailable (no_sales_evidence)`, while hygiene still emits 1,117 | `check_independence`, exit 0, 2026-09-24 |
| Rule 8 (kinds not summed · no shekel figure on a quantity signal · no number rather than zero) | **yes**. Where the stock date is unusable, the cut leaves all three reconcile figures `None`, never a full-history sum (pinned by `test_adr_026_an_unusable_stock_date_cuts_nothing`) | artefact; `tests/engine/test_unknown_reconcile_window.py` |
| Anything claimed beyond what monthly data supports (rule 13) | **no**. The window is month-grained and now names the months summed. The count's own month (June) is excluded whole, because its flows straddle the count: *not measurable* at monthly grain, and stated as such (OQ-201) | artefact `window`, `reconcile_before` |

---

## Since 2026-09-16

| Finding | Now | Evidence |
|---|---|---|
| **F2-V1:** the published count was inflated by 24% (439 against 355), caused by a vintage bug | **resolved** | The 2026-09-24 artefact publishes 355 on `as_of 2026-06-06` from `declared_sidecar`. The fix was #109's sidecar, and ADR-026 then made the window match the cut |
| **F2-V2:** INT-002B reaches the daily surface never, by construction | **still open, unchanged** | `compose()` over today's artefact gives hygiene **0 of 10**. Reconciliation takes all three unvalued places |
| **F2-V3:** not checked (rendered page, AC-029 end to end, the owner's view) | **still not checked** | below |

## New findings

### F2-V4: AC-023's statement has no surface. **smartshelf-architect**, then the owner for the wording.

FR-026 owes the owner a sentence: the amount is not determinable before a physical count. V1
has no place for it. Nothing lets him ask, and the copy System Design §21 names is in no
dictionary. The 09-16 record marked AC-023 met on the absence of a figure alone. The
architect decides where the sentence lives. The words are the owner's to approve
(front-end rule).

### F2-V5: the owner's screen does not follow the nightly. **The repository owner** (Vercel console), then **smartshelf-platform**. Filed as #167.

- **Every** production deploy of a commit authored by `smartshelf-collector` is blocked:
  22 of 22 since 2026-09-13, against 78 of 78 human-authored.
- A nightly artefact reaches the owner only when a later human merge deploys `main`.
  Measured lags run from 6.7 h to **88.8 h**, and from 09-18 to 09-21 the screen showed
  09-17's data.
- Today's artefact, carrying ADR-026's corrected period, went live 7.5 h late, and only
  because an unrelated tidy PR (#165) merged.

### F2-V6: every finding rests on one stock count, 110 days old. **The repository owner** (a fresh POS export from the store).

`vintages.pos.as_of` is 2026-06-06, and every nightly since has re-published the same count.
ADR-026 made that visible, with the period stopping at May. So the 355 describe June's
shelf, not today's. Nothing in the product asks for a newer export, and the list will not
change until one arrives.

### F2-V7: on the Hebrew card, one label is English and the period is a raw id. **smartshelf-engineer**, after the owner approves the wording.

`evidence.reconcile_months` is "reconcile months" in `he.js`. `window_id` renders as
`2026-01..2026-05` through `String(raw)`. Neither is wrong; both fall short of *"in his
language, on his screen"*.

## Not checked, and why

- **The rendered page.** The gate returns 401 and this session has no Basic Auth
  credentials. Every figure above was read from the artefact at the commit production
  serves, which GitHub's deployment record ties to `3bb38ce`.
- **AC-029 end to end.** Whether any owner outcome exists on a reconciliation entry is not
  published. The committed mirror (pulled 2026-09-12) holds none, and no product has yet
  left the list while carrying a decision.
- **Whether the 355 are worth the owner's time.** No artifact answers that, and given
  F2-V6, the more useful question may be when the next stock count is coming.

## What surprised me

The week's most owner-visible correction, ADR-026's period, was right, merged, published by
the nightly and reproduced to the byte on a laptop, and it still reached the owner only by
accident. An unrelated PR happened to merge. Every check this project runs is green on a
morning when the owner's screen is a day old, because nothing looks at the last step.

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| F2-V4: a surface for FR-026's statement | smartshelf-architect; wording by the owner | The intent's governing sentence never reaches the owner |
| F2-V5 / #167: nightly deploys are blocked | the repository owner (Vercel), then smartshelf-platform | The owner sees data only as fresh as the last human merge |
| F2-V6: a fresh POS export | the repository owner, with the store | All 355 findings describe June |
| F2-V7: one English label, and a raw period id | smartshelf-engineer, after the owner approves the wording | Language on the owner's screen |
| F2-V2: hygiene has no daily place | smartshelf-architect and smartshelf-pm | Still undecided out loud |
