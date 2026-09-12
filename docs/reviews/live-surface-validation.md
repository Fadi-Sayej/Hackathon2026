---
ID: LIVE-SURFACE-VALIDATION
Title: What the owner's screen actually shows, against the settled decisions
Status: Ready for review
Owner: smartshelf-validator
Parent: [F6-S1](../features/F6-daily-action-surface/specs/F6-S1-daily-action-surface.md)
Inputs: [public/data/operational.json, src/pages/OperationalPage.jsx, src/lib/analytics/actionPriority.js, src/lib/questions/openQuestions.js, src/App.jsx, docs/product/intent-register.md]
Updated: 2026-09-12
---

# What the owner's screen actually shows

The engine has been validated. The **live surface** — what the pilot serves today, and what
the owner opens on 12/9 — has not. It still runs the pre-V1 spine over
`public/data/operational.json`, and the cut-over is deliberately deferred.

Measured 2026-09-12 against the deployed build and the committed artefact.

## Verdict

Two settled decisions are honoured. Two are broken, and one finding is worse than either.

| Decision | Verdict | Evidence |
|---|---|---|
| **D-2** — a recurring and a one-off amount are never summed | **met** | `OperationalPage.jsx:174-177` keeps `perUnitTotal` and `oneOffTotal` apart, with the reason written beside them |
| **D-8** — at most three questions on screen | **met** | `openQuestions.js:19` — `MAX_QUESTIONS_ON_SCREEN = 3` |
| **D-9** — the daily surface shows at most ten actions | **BROKEN** | `OperationalPage.jsx:55` — `TOP_N = 20` |
| **AC-101** — no count of unshown entries appears | **BROKEN** | the button reads *"Show all 1,639 actions"* (`op.showAll`) |

## Finding 1 — the surface shows twenty, and offers 1,639

`TOP_N = 20` against D-9's ten, and a button that expands to the full 1,639.

AC-101 exists because a backlog number turns a daily surface into a queue the owner is
failing. *"Show all 1,639 actions"* is that number, in a button, on the first screen.

## Finding 2 — one capability fills the entire surface

Computed by running `rankActions` over the committed artefact: **the top 20 entries are all
`CHECK_STOCK_DISCREPANCY`.** Not most — all of them.

This is the same defect [`compose` was fixed for](phase-0-1-execution-report.md) during
Phase 2: entries ranked against each other with no allocation, so one family crowds out
every other. FR-106 and F6-S1 §12 name the consequence — *"hygiene work would otherwise
never surface"* — and on the live surface it doesn't. The owner sees twenty stock
discrepancies and no price gap, no catalogue finding, nothing else.

The engine's `compose` already allocates places and produces 7 valued + 3 unvalued. The
live spine does not.

## Finding 3 — the questions are computed from demo data, under a "REAL POS DATA" badge

The most serious of the three, and the only one that is a claim rather than a ranking.

The page header shows **REAL POS DATA · REAL COMPETITOR PRICES · PROOF OF CONCEPT**.
Directly beneath it, "Questions for the manager" carries figures like *"At stake: 283 ILS ·
Affects 126 products"*.

Traced:

```
App.jsx:75    loadDemoStoreData()          → src/data/demoProducts.js  (7,451 compiled entries)
App.jsx:250   analyzeProducts(...)
App.jsx:289   generateReorderRecommendations(...)   → type REORDER
App.jsx:351   buildOpenQuestions(...)
openQuestions.js:66  `if (rec.type !== 'REORDER') continue`   → moneyAtStake
```

`operational.json` contains **no `REORDER` recommendations** — its types are
`CHECK_STOCK_DISCREPANCY`, `CHECK_WOLT_PRICE_GAP`, `CHECK_NEGATIVE_STOCK`, `CHECK_MARGIN`,
`VERIFY_UNKNOWN_BARCODE` and `WATCH_PRODUCT`. The money beside each question therefore comes
from the **demo spine and the reorder engine**, not from the owner's POS export.

`src/data/demoProducts.js` is the file §20.1 marks REMOVE as *"a second copy of the truth"*;
its first entry is named «מוצر בדיקة -1» — *test product* — in category «בדיקة», *test*.

**If he asks where 283 comes from, there is no answer that survives the question.** That is
the failure F1's intent describes in its own words: state a number as fact, have him reply
*"I do it deliberately"*, and every figure on the page falls with it.

## What is not wrong

`rankActions` keeps the two money kinds apart and says why. `MAX_QUESTIONS_ON_SCREEN` is
three. The Wolt price-gap count of 1,147 is wrong against F1's approved spec, but that is
the known cut-over gap already recorded in [F1-validation](F1-validation.md) — not a new
finding.

## Not checked

- The Arabic and Hebrew renderings. The screenshot audited was English; the owner reads
  Arabic, and AC-112 has no cover on this spine.
- What the V2/V4 nav items (Reorder, Approved orders, Assortment gaps, Store layout, Shelf
  plan) show when clicked. They are all demo-fed and he will click them.
- Whether any surfaced figure is a zero standing in for an absent one (D-3).

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| Decide what the owner is shown on 12/9: this spine, or the cut-over | smartshelf-pm | Finding 3 is not fixable inside the old spine — the demo data *is* its input |
| If this spine ships: remove the money figures from the questions, or the "REAL POS DATA" badge | smartshelf-pm | A number with no provenance beside a badge claiming provenance is worse than no number (D-3) |
| If this spine ships: `TOP_N` 20 → 10, and drop the count from the show-all button | smartshelf-engineer | Two one-line changes; D-9 and AC-101 |
| Check the Arabic rendering before 12/9 | smartshelf-platform | Nobody has opened the pilot in the language the owner reads |
