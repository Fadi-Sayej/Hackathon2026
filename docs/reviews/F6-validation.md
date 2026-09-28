---
ID: F6-VALIDATION
Title: F6 — Daily Action Surface · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F6-S1](../features/F6-daily-action-surface/specs/F6-S1-daily-action-surface.md)
Inputs: [docs/features/F6-daily-action-surface/specs/F6-S1-daily-action-surface.md, docs/features/F6-daily-action-surface/intent.md, docs/operations/deployment.md, public/data/dashboard.json (2026-09-28), src/surface/compose.js, src/surface/DailyPage.jsx, src/surface/EntryCard.jsx, src/lib/i18n/dictionaries/, src/surface/__tests__/, e2e/daily-surface.spec.js, e2e/daily-work.spec.js, GitHub deployment records (Production)]
Updated: 2026-09-28
---

# Validation F6 — Daily Action Surface

- **Deployed URL:** `https://hackathon2026-fadi19.vercel.app` (serves the sign-in page; ADR-029).
- **Commit in production:** `2a716ec`. GitHub deployment `6708764605`, `success`, 2026-09-28 11:29Z.
- **Artefact read:** `public/data/dashboard.json` at `2a716ec`, `generated_at 2026-09-28T03:10:39Z`, run `ok`.
- **Surface read:** `compose()` from `src/surface/compose.js` over that artefact, no outcomes, `now` 2026-09-28 08:00Z.
- **Context:** the pilot with the YomYom store ended on 2026-09-27 (D-23).

## Verdict

**The best-tested feature in the product, and it conforms on everything but one thing the owner
would notice first: no card says what to do.** The surface is bounded, ordered by money, never
sums kinds, labels estimates, keeps decisions, and says "unavailable" rather than "nothing".
But the engine publishes an action for every entry (`verify_price`, `count_product`) and no
card renders it, so the North Star's "sees what to do today" is half met: he sees what is
wrong. And by its own allocation rule, the surface can show only F1 and F2 until 355
reconciliation entries are settled.

---

## Pass one — conformance

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §15 | AC-100 | at most ten entries under any volume | **met** | Today: 10 of 3,309 candidates (3,094 after one per product); `bound: 10` in `thresholds.surface`. `compose.test.js`, `checkpoint2.test.jsx`, `e2e/daily-surface.spec.js` |
| spec §15 | AC-101 | no count of unshown entries, backlog or completion | **met** | `compose` returns exactly `entries`, `unavailable`, `nothingToDo`, and a test locks the key set (`compose.test.js`); deferred entries are reached on the Data page instead (`deferredEntries.test.js`) |
| spec §15 | AC-102 | same kind, descending value | **met** | Today's valued seven: ₪16, 11, 7, 4, 4, 3.1, 3, all `per_sale confirmed`; `compose.test.js` |
| spec §15 | AC-103 | no summary sums a recurring and a standing value | **met** | Kinds are contiguous runs, never interleaved or summed (`compose.js`); `compose.test.js`, `checkpoint2.test.jsx`, e2e |
| spec §15 | AC-104 | every estimate labelled on the surface | **met** | `EntryCard` labels `certainty: estimated` on the card; `DailyPage.test.jsx`. None of today's ten is an estimate |
| spec §15 | AC-105 | an outcome survives reload and session end, and the entry stays gone | **met** | localStorage plus Firestore write-through (`ownerState.js`); `appSpine.test.jsx`, `DailyPage.test.jsx`, e2e |
| spec §15 | AC-106 | an outcome stays retrievable after its entry is no longer produced | **met by construction** | Outcomes are kept by entry id in owner state and never pruned; since 2026-09-28 F13 counts them as `not_in_this_run`. No test named for AC-106 |
| spec §15 | AC-107 | unavailable shown as unavailable, never zero | **met** | `compose` lists unavailable capabilities apart from entries; `DailyPage.test.jsx`, `loadDashboard.test.js`, e2e |
| spec §15 | AC-108 | explicit nothing-to-do state | **met** | `nothingToDo`; `DailyPage.test.jsx` |
| spec §15 | AC-109 | no product twice | **met** | `compose` keeps one entry per barcode (the larger amount), and never merges barcode-less ones; `compose.test.js`, e2e |
| spec §15 | AC-110 | the full set per capability reachable elsewhere | **met** | `CapabilityPage` per capability (`CapabilityPage.test.jsx`); `everyCapabilityReachable.test.jsx` |
| spec §15 | AC-110a | every admitted entry meets FR-103's four conditions | **met** | `tests/engine/test_surface_candidates.py` (`stamp`) |
| spec §15 | AC-110b | every entry names the capability that produced it | **partial** | The card's line is the characterisation ("Confirmed loss", "Numbers that do not add up"), which does separate a loss from a question. The capability itself is only a `data-capability` attribute; no visible text names it |
| spec §15 | AC-110c | every entry states an action the owner can perform, with its required evidence | **partial** | Evidence: yes, every published field is on the card. **Action: no.** Each entry carries `action` (today `verify_price` ×7, `count_product` ×3); `EntryCard.jsx` never renders it, and the dictionaries hold no `action.*` key |
| spec §15 | AC-111 | no velocity claim without sales evidence | **met** | `DailyPage.test.jsx`; no entry on today's surface carries a rate |
| spec §15 | AC-112 | three languages, no untranslated key, no overflow, no split number | **met today; latent gap** | `parity.test.js`, `checkpoint2.test.jsx`, e2e. Today's ten cards use twelve evidence labels, all translated. **Twelve other `evidence.*` labels are English in `ar.js` and `he.js`** (`sources`, `reference`, `question`, …); they appear on a card as soon as an F3 or F4 entry reaches the surface (see F3's and F4's records) |
| spec §7 | INV-050 … INV-057 | | **met** | As AC-100, AC-103, AC-104, AC-105; INV-054: the 3 reconciliation entries and every hygiene entry carry no `value`; INV-055 as AC-111; INV-056 as AC-109; INV-057 as AC-107 |
| spec §19 | INT-NS and inherited | traced to an AC | **met** | Every §19 row names an AC |

### Scope drift

| Change | In a plan task's `Files:` list? | In spec §3 scope? | Note |
|---|---|---|---|
| `e111f82`, `c241c9e`, `74e7d79` #139/#142/#145: "Later" comes back tomorrow, and a way back to hidden entries | issues, not a plan task | yes (FR-113, FR-102) | Traced to issues, not spec ids (handover rule 6) |
| `1f6e600` #116: the surface's stylesheet | issue | yes | Visual; approved under the front-end rule |
| `52b5f85`: the reconciliation card in the owner's words (F2-V4, F2-V7) | F2's validation items | F2-S1 | — |
| `2871315`: team accounts read-only | **ADR-029 §5** | D-22 | — |
| `da7ee02`, `58c0801`: F8 kept off Today | **Phase 5 Tasks 5.0, 5.13** | F8-S1 FR-160 | — |

### Shipped but never requested

Nothing.

---

## Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F6-daily-action-surface/intent.md`.*

**PROBLEM (without a bound the screen becomes a fire hose and nothing gets done): is the owner
measurably less stuck?** The bound holds: 3,309 candidates (3,094 products) become 10. Whether anything got done
is not yet measurable: the owner's decisions are first published by F13's `measurement.json` on
2026-09-29. (The committed owner-state mirror of 2026-09-12 holds none; four devices had
written owner state by 2026-09-24.)

**SUCCESS — the North Star, count it.** "The manager opens one screen each morning and sees what
to do today, ordered by money — no more than 10 actions."

- One screen: yes (Today).
- Ordered by money: yes, ₪16 down to ₪3 per sale, then three without money.
- No more than 10: **10**.
- *Sees what to do:* **no.** He sees what is wrong and the numbers behind it; the action the
  engine chose for him is not on the card.

**USER: would the owner recognise it?** Yes, in Arabic by default, on his phone, with his products
by name. The three reconciliation cards were reworded in his words (F2-V4).

**NOT NOW: anything deferred built?** No reporting over time on this screen (F13 is a separate,
team-only page), no alerts, no staff assignment, capability pages kept, no measure of his
commitment on the owner's side.

**Would you write the same intent again?** Yes, with one line added: "consumes entries from F1–F5"
should say how they share ten places. The allocation that follows from F6-S1 (seven places by
money, three reserved in a fixed order) means F3, F4 and hygiene never appear while
reconciliation has entries left, and it has 355: at three a day, about four months.

---

## Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| Entries on the surface today | **10**: F1 `price.inverted` 7 (valued), F2 `recon.impossible_opening` 3 (the three reserved places) | `compose()` over `public/data/dashboard.json` |
| `generated_at` | 2026-09-28T03:10:39Z, run `ok` | `public/data/dashboard.json` |
| Candidates | 3,309 entries across the admitted capabilities, 3,094 after one per product | `compose` input, recomputed |
| Matches the intent? | Bound and order: yes. What to do: no (AC-110c) | Pass two |
| Turned off | F6 is not a signal; it moves when its inputs do. Withholding the sales evidence takes F2's three off (reconciliation unavailable, `check_independence.py`), and the surface says so | `check:signals`, 2026-09-28 |
| Rule 8 | **yes**: one kind today (`per_sale`), no sum anywhere, no money on the three reconciliation cards | `compose()` output |
| Rule 13 | not engaged directly; each producer carries its own window | — |

---

## What surprised me

The engine names an action for every entry, and nothing between it and the owner says it. The
most-tested screen in the product answers "what is wrong" ten times and "what do I do" never.

## Not checked, and why

- The surface on the deployed URL: it needs a sign-in; the component tests, the e2e suite in CI
  (39 passed on 2026-09-27) and `compose` over the real artefact were read.
- Whether the owner acted on anything: first published on 2026-09-29.

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| ~~Render each entry's action on its card, in the owner's words, with `action.*` keys in three languages~~ **Done 2026-09-28, #235** (approved by the owner; see `docs/reviews/card-wording-2026-09-28.md`) | smartshelf-engineer; screen change, owner approves the wording | AC-110c partial; the North Star's "sees what to do" |
| ~~Decide whether the card must name the producing capability or the characterisation suffices~~ **Decided 2026-09-28 by the repository owner: the characterisation suffices** (dated note under F6-S1 AC-110b) | smartshelf-architect | AC-110b partial |
| Say in F6's intent how F1–F5 share ten places, and whether reconciliation holding all three reserved places for about four months (355 entries, three a day) is intended | smartshelf-pm, then smartshelf-architect | F3, F4 and hygiene cannot reach the surface |
| ~~Translate the twelve English `evidence.*` labels in `ar.js` and `he.js`~~ **Done 2026-09-28, #235** (approved by the owner; see `docs/reviews/card-wording-2026-09-28.md`) | smartshelf-engineer; owner approves | AC-112 latent |
