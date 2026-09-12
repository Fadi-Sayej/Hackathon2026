---
ID: F8-DECISIONS
Title: F8 Order Quantity — the three decisions that must be taken before a spec exists
Status: Ready for review
Owner: smartshelf-pm
Parent: [SPEC-GAPS · GAP-008](../../features/gaps-and-open-questions.md)
Supersedes: —
Superseded-by: — (on resolution, becomes D-14 … D-16 in the intent register §3)
Related Intents: INT-004, INT-005
Inputs: [docs/features/F8-order-quantity/intent.md, docs/features/gaps-and-open-questions.md, docs/product/intent-register.md, configs/delivery_targets.yaml, configs/store_types.yaml, public/data/operational.json, data/external/snapshots/2026-09-05/]
Updated: 2026-09-12
---

# F8 — the three decisions

[GAP-008](../../features/gaps-and-open-questions.md) says INT-004 states an order of inputs,
not a rule, and names three decisions that must be taken first. It does not say what the
choices are. This document turns each into a question the owner can answer in one
sitting, with the options the data actually supports.

**It answers nothing.** Every figure below is cited to the file it was read from
(CLAUDE.md rule 11). F8 stays `Registered — not specified` until a human takes these.

> **This document is not product authority.** It is a question, not a decision. When the
> three are taken they are recorded as **D-14 … D-16** in the
> [intent register §3](../intent-register.md), which *is* authority; this file is then set
> `Superseded` and kept as the record of how the decision was reached. Never cite it as
> though it settled anything.

---

## Decision 1 — What geography is "the market"?

**The question for the owner:** «المتاجر التي تنافسك فعلاً — أيّها؟»

The collector already made a provisional choice that nobody ratified.
`configs/delivery_targets.yaml` filters to venues within **~5 km** of YomYom by haversine
distance, and lists nine: one `reference` and eight `competitor`, from **0.21 km** to
**2.76 km**.

| Option | What counts as the market | What it costs |
|---|---|---|
| **A — Keep ~5 km** | All nine venues as configured | Nothing to build; ratifies a radius chosen for collection convenience, not because it describes who the owner loses a sale to |
| **B — Nearest few** | The three inside ~1 km (0.21, 0.60, 0.86 km) | Smallest, most defensible catchment; two of the three are a supermarket and a delivery-brand grocery, neither of them YomYom's format |
| **C — By format, not distance** | Comparable formats at any distance in the set | Matches what the engine already enforces; may leave very few comparable venues, and the count of those is not yet established |
| **D — Ask the owner to name them** | The stores he believes he competes with | The only option grounded in his knowledge rather than ours; may not match who is on the delivery platform, and unnamed stores then have no data |

**What makes this hard, and it is not distance.** `configs/store_types.yaml` records
YomYom as `gas_convenience` — a forecourt convenience store, typical range 300–1,500
SKUs — and the file's own note says *"This is YomYom. Every affinity lookup starts from
here."* The nearest venue at 0.21 km is a supermarket; at 2.28 km is a major discount
chain. **The closest store by distance is not the most comparable by format**, and
[ADR-008](../../architecture/decisions/ADR-008-store-format-affinity-enforced-in-the-engine.md)
already enforces format affinity in the engine. A radius decision that ignores format
will be overridden by the engine anyway.

**A constraint on all four options.** In the 2026-09-05 snapshot, the nine venues carried
between **129 and 953 products** each — a sevenfold spread (read from
`data/external/snapshots/2026-09-05/delivery_catalog/`). A radius that includes a venue
publishing 129 products contributes almost nothing to most of the catalogue. Whichever
option is chosen, the coverage it actually yields must be counted before a spec is
written, not after.

---

## Decision 2 — How do market movement and the store's own movement become one quantity?

**The question for the owner:** «إذا كان السوق يبيعه بقوة وأنت لا — نطلب أكثر أم أقل؟»

The intent sets the order — market first, own movement second, shelf life as a cap — but
not the arithmetic.

| Option | Rule | What it assumes |
|---|---|---|
| **A — Market proposes, own movement caps** | Market movement sets a candidate quantity; the store's own history caps it | Past sales are a fair ceiling — which is the assumption the intent explicitly rejects ("مبيعاته وحدها تقول ما باعه **مما كان على الرف**") |
| **B — Own movement proposes, market flags** | The store's own history sets the quantity; market movement only raises a question | Conservative, closest to today's behaviour, and it makes F8 an alerting feature rather than an ordering one |
| **C — Weighted combination** | An explicit weight between the two | Requires a number nobody can currently justify, and it would have to be defended to the owner |
| **D — No quantity at all in V2** | Surface the disagreement; let the owner set the number | Honest about what the data supports; does not deliver "كم أطلب", which the intent calls the largest value in the product |

**What bounds every option.** The sales reports are **monthly**, one row per product per
month, and cover **24.3% of the catalogue** (CLAUDE.md rule 13). For the other 75.7%
there is no sales row at all — reported as `none`, never as zero. Any rule that needs
the store's own movement is undefined for three products in four. **That is the real
constraint on this decision**, and it is a fact about the data, not a modelling choice.

---

## Decision 3 — What happens when the two disagree?

**The question for the owner:** «صنف قوي في السوق وضعيف عندك — مكانه على الرف؟ سعره؟ أم سوقه هنا ضعيف فعلاً؟»

That sentence is already written in the intent, as the F8/F9 shared framing. What is not
decided is what the system does with the owner's answer.

| Option | Behaviour | Consequence |
|---|---|---|
| **A — Conversation only** | Ask; record nothing | What ships today. The intent register §4 says this "is not yet a decision the system can record" |
| **B — Record the answer, suppress the entry** | The owner's reason is stored; the product stops being raised | Needs a place to put it — F5 owner knowledge capture is the obvious home, and D-8 caps on-screen questions at three at once |
| **C — Record and act** | The answer changes future ordering | The largest version, and unreachable until Decisions 1 and 2 are taken |

**A count in the intent no longer matches the artifact.** F8's intent is built on *"الـ527
صنفاً الموسومة `WATCH_PRODUCT` اليوم بلا قرار"* — 527 products. `public/data/operational.json`
(`meta.generatedAt` 2026-09-10) reports `byType.WATCH_PRODUCT` = **1,857**. Whatever the
owner is asked to decide here applies to more than three times the population the intent
describes. **Which number is right is not a pm decision** — it needs whoever owns the
signal to say whether the definition widened or the count drifted. It is recorded as an
open question below, and it should be settled before this decision is put to the owner,
because "there are 527 of these" and "there are 1,857 of these" are different meetings.

---

## What is not in scope for these decisions

- **Ordering that writes anything anywhere.** D-7 settles it: the system never writes to
  the owner's point-of-sale system. No option above changes that.
- **A monetary figure on a quantity.** D-1 and D-11 settle it. Whatever F8 produces, it
  carries no shekel amount derived from a stock quantity, and where a figure cannot be
  stated honestly the surface shows no figure, not zero (D-3).
- **Shelf-life as anything but a cap.** F8 depends on F10, whose own intent records that
  it needs 30 days of recorded receipts that do not exist yet.

## Acceptance — how we will know these were answered

| # | Countable criterion |
|---|---|
| 1 | The market is defined by a written rule that names either a distance, a format set, or a list of stores — and the number of venues it yields is counted from `configs/delivery_targets.yaml`, not estimated |
| 2 | For a stated sample of products, the combination rule produces either a quantity or an explicit "no quantity", with no third outcome |
| 3 | The rule states what it does for the 75.7% of the catalogue with no sales row, in one sentence |
| 4 | The disagreement case names where the owner's answer is stored, or states that it is not stored |

## Open questions

| GAP/OQ | Question | Who can answer it |
|---|---|---|
| GAP-008a | Is `WATCH_PRODUCT` = 527 (F8 intent) or 1,857 (`operational.json`, 2026-09-10)? Did the definition widen, or did the count drift? | whoever owns the signal — architect or engineer |
| GAP-008b | How many of the nine venues are format-comparable to `gas_convenience` under ADR-008, and what catalogue coverage do they give? | architect |
| GAP-008c | Does the owner accept a V2 that surfaces the disagreement without proposing a quantity (Decision 2, option D)? | owner |
| GAP-008d | Do the Wolt venue ids in the snapshots map to the keys in `configs/delivery_targets.yaml`? No mapping was found while writing this. | engineer |
