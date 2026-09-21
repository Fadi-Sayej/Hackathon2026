---
ID: NAV-REACHABILITY-2026-09-21
Title: 1,638 published findings are reachable from no screen, and the spec's own answer is unrouted
Status: Ready for review
Owner: smartshelf-engineer
Parent: [F6-S1](../features/F6-daily-action-surface/specs/F6-S1-daily-action-surface.md)
Inputs: [public/data/dashboard.json (2026-09-21, inputs_digest 376fa424c441), src/App.jsx, src/components/layout/navGroups.js, src/pages/CapabilityPage.jsx, src/surface/V1Spine.jsx, src/surface/compose.js, src/lib/dataAdapters/artefactToOperational.js, docs/features/F6-daily-action-surface/specs/F6-S1-daily-action-surface.md, docs/product/intent-register.md]
Updated: 2026-09-21
---

# 1,638 published findings are reachable from no screen

The repository owner asked a narrow question: two nav items are both called "Today" in
English — fix it. Four independent reads of the code and the approved documents were run
against that question. **None of them answered it**, because all four found the same larger
thing first, and it makes the narrow question premature.

This records what was verified, what was wrong, and what is left to decide. It reports; it
repairs nothing.

## The finding

**`CapabilityPage` is not in the shipped application.**

| | |
|---|---|
| `src/App.jsx` | never imports `CapabilityPage`. Its route branches are `daily`, `operational`, `data-source`, `products`, an `AWAITING` fallback, then `return null` |
| `src/pages/CapabilityPage.jsx` | imported by exactly one non-test file: `src/surface/V1Spine.jsx` |
| `src/surface/V1Spine.jsx` | imported by **nothing but its own tests**. `src/main.jsx` mounts `App.jsx`. The file says so itself: *"It is NOT the app's default."* |
| `src/components/layout/navGroups.js` | thirteen ids, **none of them a capability id** |

So **FR-102**, **C-51**, **AC-110** and **SCN-109** — *"the owner MUST be able to reach the
full set of entries for a capability deliberately, on a surface other than this one"* — are
discharged by nothing. `CapabilityPage.jsx`'s own header claims *"This is where AC-110 is
discharged"*, and it is unreachable.

`src/pages/__tests__/CapabilityPage.test.jsx` contains a test named *"AC-110 — the full set
stays reachable away from the daily surface"*. It renders the component directly and passes.
**No test in any suite asserts that the full set is reachable from the running app**, which
is why this survived the restore.

## What the owner can actually reach

Measured against `public/data/dashboard.json`, 2026-09-21, `inputs_digest 376fa424c441`.

`artefactToOperational.js` is a **filter, not a translation**: `TYPE_BY_FAMILY` has eight
keys, `toRecommendation` returns `null` for anything absent from it, and the nulls are
dropped by `.filter(Boolean)`.

| signal family | entries | reaches `operational`? |
|---|---|---|
| `catalogue.idle` | 1,631 | **no** |
| `hygiene.negative_stock` | 578 | yes |
| `recon.impossible_opening` | 355 | yes |
| `hygiene.no_identifier` | 248 | yes |
| `hygiene.absent_price` | 223 | yes |
| `price.above_ceiling` | 131 | yes |
| `margin.below_cost` | 71 | yes |
| `price.inverted` | 68 | yes |
| `hygiene.conflicting_duplicate` | 68 | yes |
| `competitor.purchase_cost` | 4 | **no** |
| `competitor.policy_breach` | 2 | **no** |
| `catalogue.implausible_quantity` | 1 | **no** |

```
published            3,380
reachable            1,742
reachable from nowhere 1,638
```

The daily surface shows **ten**, by design and correctly (FR-100). The engine computes and
commits 3,380 findings nightly; 1,638 of them can be reached from no screen in the product.

**`margin_below_cost` is reachable only through `operational`.** `compose.js:14` excludes it
from the daily surface (SPEC-GAP-A: no specification produces it), and `CapabilityPage` is
unrouted. Its 71 entries — 34 below cost, 37 thin margin — leave the product entirely if that
page is removed as things stand. This is the strongest single argument against the narrow fix
the question proposed.

## What the question asked, and why it is premature

The two nav items collide **in English only**:

| | `page.daily.name` | `page.operational.name` |
|---|---|---|
| ar | `شغل اليوم` | `اليوم` |
| he | `עבודת היום` | `היום` |
| en | `Today` | `Today` |

`DEFAULT_LANGUAGE` is `ar`, and `en.js` describes itself as *"English — for demos, judges and
anyone outside the store."* The owner does not see the collision. A judge does.

Deleting `operational` would take reachability from 1,742 to 10 and remove `margin_below_cost`
from the product, to fix a label in a language the owner does not read. **Route the full-set
surface first; the naming question is then a one-string English rename.**

## Two things this review had to correct in its own inputs

Recorded because a review that only reports other people's errors is not being read
adversarially enough.

- One read claimed `artefactToOperational` *"flat-maps every entry of every capability"*. It
  does not — it saw the `flatMap` at `:215-217` and missed both `if (!type) return null` and
  the `.filter(Boolean)` on the following line. The 1,638 figure above is the correction.
- Two reads quoted the entry total as 3,464. That was the 2026-09-17 artefact. Today's is
  **3,380**. Rule 11: the figure comes from the artefact that produced it, and the artefact
  changes nightly.

## Consequential defects found on the way

| | |
|---|---|
| **#139** | `EntryCard.jsx:55` sends `{status: 'deferred'}` with no date; `recordOutcome` omits `deferred_until`; `compose.js:26` reads its absence as *deferred indefinitely*. **"Later" is a permanent delete.** OQ-604 (`F6-S1:447`) predicted it verbatim: *"Without it, deferral is indistinguishable from permanent dismissal."* Every test supplies an explicit date, so none exercises the button as it ships |
| **#140** (fixed) | `App.jsx` passed `actions=` where `OperationalPage` destructures `decisions=`. Decisions taken on one surface suppressed nothing on the other |
| open | `e2e/ui-invariants.spec.js` navigates by positional index and its `PAGES` list omits `daily`, so every label in those tests is off by one and `data-source` is never visited. It passes |

## What is decided, and what is not

**Settled by this review, because it is a measurement and not an opinion:** the full-set
surface is unrouted, 1,638 entries are unreachable, and `margin_below_cost` has exactly one
route.

**Not settled here, and deliberately:**

1. **Whether the nav is ten or thirteen.** §20.1 marks the restored pages `REMOVE`; the owner
   asked for them back on 2026-09-16. The two disagree on the record. Issue #74 reserves that
   reconciliation for `smartshelf-architect` and says *"neither this issue nor #124 should be
   the place that quietly settles it."* **Nor is this review.** It wants an ADR.
2. **How long a deferral lasts.** OQ-604, `smartshelf-pm`. An Undo control decides nothing and
   stops the loss; the duration still needs an answer.
3. **Reopening D-9** was considered and rejected by all four reads. `intent-register.md:80` —
   *"These are settled. A specification may operationalize them; it may not reopen them."* The
   bound is on the *daily* surface and FR-102 already grants the escape hatch; the escape hatch
   is what is missing, not the bound.

## The sequence, if the nav question is answered "route them"

`CapabilityPage` renders a bare `<ol>` with no cap. `catalogue_lifecycle`'s full set is 1,632
rows of which **1,631 carry the identical characterisation `idle`**. PR #135 measured this
exact shape — 7,523 rows produced 98,044 DOM nodes and 4,879 ms to first row at 390 px with
CPU throttled 4× — and fixed it by capping at 250 and saying what is held back.

**Bound the capability page first, then route it.** Route-then-discover is how #135's own
loading bug shipped, and that PR's note is the standard: *"Unit tests passed throughout. The
page was broken. Found by opening it."*
