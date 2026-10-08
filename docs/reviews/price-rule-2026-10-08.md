---
ID: D39-PRICE-RULE-REVIEW
Title: The price rule is the owner's (D-39, ADR-043) — what was built, and the proof that nothing moved
Status: Ready for review
Owner: smartshelf-engineer
Parent: [ADR-043](../architecture/decisions/ADR-043-the-price-rule-is-the-owners-and-its-findings-wait-for-it.md)
Inputs: [D-39, ADR-043, docs/implementation/phase-7-store-onboarding.md (Tasks 7.7–7.10), configs/store_facts.yaml, src/engine/competitor_position.py, src/lib/dataAdapters/foldPolicyBreach.js, src/pages/CapabilityPage.jsx]
Updated: 2026-10-08
---

# The price rule is the owner's — the proof

The repository owner approved ADR-043 and its sentence on 2026-10-08 ("approve"). This records
what Tasks 7.7–7.10 built and how each claim was checked, the same day.

## What a store without a rule sees

F3's findings page, as the engine publishes it for YomYom's data with the rule withheld. The
approved sentence stands where the breaches were. The purchase-cost findings are still listed
below it, the counts no longer include breaches, and the two thresholds that belong to the
rule are gone.

| English | עברית | العربية |
|---|---|---|
| [f3-without-a-rule-en.png](price-rule-2026-10-08/f3-without-a-rule-en.png) | [f3-without-a-rule-he.png](price-rule-2026-10-08/f3-without-a-rule-he.png) | [f3-without-a-rule-ar.png](price-rule-2026-10-08/f3-without-a-rule-ar.png) |

## What YomYom sees: nothing changed

| Check | How | Result |
|---|---|---|
| Every screen | 126 screens: every page in he, ar and en, on a phone (390×844) and a desktop (1280×900), with the Prices tabs. Shot twice from main and twice from this branch, each build on its own port and its bundle confirmed. Each side served the artefact its own engine prints for YomYom's data at 2026-10-08T08:00Z; run id and fingerprint were set equal on both sides, as they are random or expected to differ. | **126 of 126** screens have an after-render byte-identical to a before-render. Repeated after rebasing onto #309 (which changed `App.jsx`, the dictionaries and `pages.css`), with fresh artefacts from both engines: **124 of 126**. The other two, the phone Prices page in en and he, differ by 11 and 5 pixels, at most 3 levels of 255, at the search field's antialiased edge, the spots this proof has always flickered at; enlarged eight times they are the same |
| The fold, on real data | The branch's artefact folded by `foldPolicyBreach`, compared with main's artefact capability by capability, as JSON with the publisher's key order | `competitor_position` byte-identical (20 entries, in order); 14 of 15 capabilities byte-identical. The 15th, `market_running_out`, is equal as data; its `products` keys come in hash order, which changes between any two runs (see below) |
| The engine | A print-mode run on main and on this branch, over the same data | `competitor_position` lost exactly its 13 breach entries, 3 breach counts and 2 thresholds, and `policy_breach` publishes them, with the same ids. Nothing else moved but the fingerprint, the two surface order lists and the figure names |
| Rule 12 | `check_v1_signals.py` on real data | withholding `price_rule` takes `policy_breach` down and nothing else; `check_order_signals.py` and `check_independence.py` pass |
| A new store | A clean copy (`new_store_copy.py`) and `check:store` | "✗ The owner's price rule … no price_rule in configs/store_facts.yaml: ask the owner (D-39) — until then unavailable: policy_breach" |
| Suites | Python, JS, lint | Python 1,318 pass; JS 711 pass; lint clean |

## Found on the way, not part of this change

`market_running_out.products` is filled by iterating a set of barcodes
(`src/market/running_out.py`, `_running_out_at`), so its key order follows Python's string
hashing and differs between runs over the same data. The fingerprint is unaffected, because
it sorts, but the committed `dashboard.json` changes bytes on nights when nothing changed. It
is fixed separately.
