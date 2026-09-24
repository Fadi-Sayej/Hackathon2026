---
ID: F14-DECISIONS
Title: F14 Decision Explanations — the three decisions that must be taken before a spec exists
Status: Ready for review
Owner: smartshelf-pm
Parent: [SPEC-GAPS · GAP-012](../../features/gaps-and-open-questions.md)
Supersedes: —
Superseded-by: — (on resolution, becomes the next free D-n in the intent register §3)
Related Intents: INT-EXPL
Inputs: [docs/features/F14-decision-explanations/intent.md, docs/features/gaps-and-open-questions.md, docs/product/intent-register.md, docs/product/PRD.md §5, issue #54, PR #178, tag v1-attic-2026-09-24 (src/lib/ai/factsGuard.js), ADR-007, public/data/dashboard.json (generated 2026-09-24T02:46:37Z)]
Updated: 2026-09-24
---

# F14 — the three decisions

[GAP-012](../../features/gaps-and-open-questions.md) records that the promise to YomYom, *an
assistant that explains the decision* (#54), still stands. The repository owner confirmed
it on 2026-09-24. Nothing yet decides how it is kept. This brief turns that into three
questions, each with the options the evidence supports.

**It answers nothing.** F14 stays `Registered — not specified` until a human takes these.

> **This document is not product authority.** It is a question, not a decision. When the
> three are taken they are recorded as the next free `D-n` in the
> [intent register §3](../intent-register.md), which *is* authority. This file is then set
> `Superseded` and kept as the record of how the decision was reached.

---

## The constraint that bounds every option

**An explanation may not add a figure or a cause.**
- Every number in a reason sentence must already be in the published evidence of the item
  it explains.
- Where a figure is withheld, the sentence withholds it too (D-3). A quantity-derived item
  never gains an amount (D-1).
- Stock that does not add up is never attributed to theft, breakage or entry error (F2-S1
  INV-015).

This is not hypothetical. `src/lib/ai/factsGuard.js`, preserved at tag
`v1-attic-2026-09-24`, records the one real trial against a model: on 2026-09-08, *"given
'order 20 units', gemini-3.5-flash-lite and gemini-flash-lite-latest both wrote '25 units'.
Unprompted, on trivial input."* That file existed to reject such output mechanically, before
display. **Any option below in which a model writes the sentence needs that check or its
successor. A request in a prompt is not a control.**

---

## Decision 1 — What is explained first?

**The question for the owner:** «ماذا تريد أن تفهمه أولاً: لماذا ظهر البند على شاشتك، أم
لماذا هذه الكمية في الطلبية؟»

| Option | What it means | What it costs |
|---|---|---|
| **A. V1's findings, now** | A reason beside each item the owner already sees. The material exists: every capability publishes its evidence per item (see the table in the F14 intent) | Nothing waits on another feature |
| **B. V2's order recommendations** | The promise as first written: "order 24 units — because…" | Waits on F8, which is `Registered — not specified` (GAP-008). There is no order to explain until F8 exists |
| **C. A now, B when F8 lands** | Findings explained first, orders with F8 | Two surfaces to keep honest instead of one |

---

## Decision 2 — Who writes the sentence?

**The question for the owner:** «هل يكفي أن تكون الجملة واضحة وصحيحة، أم يجب أن يكتبها
مساعد ذكي؟»

| Option | What it means | What it costs |
|---|---|---|
| **A. Written by rules from the published evidence** | Fixed sentence patterns per kind of item, filled with that item's own figures | Cannot invent a figure, and costs nothing to run. But it reads as a template, and whether it counts as "an AI assistant" is the client's judgement, not ours |
| **B. Written by a model once a night, from the same evidence, and published with the item** | The nightly writes one sentence per item; the owner's screen shows it | Fits ADR-007 (no service runs at request time). Needs a funded model account (#54 recorded the earlier one had no credits), a monthly cost ceiling with an alert (the platform rule for anything that calls a model), and the mechanical figure check above before anything is published |
| **C. An assistant the owner can ask, on screen** | He taps an item and asks "why?", and gets an answer | Closest to "assistant". Needs a service running at request time, which ADR-007 excludes, so the architect would have to supersede it. Also needs hosting, a funded account, a cost alert and the same figure check, on every answer |

---

## Decision 3 — When is the promise due?

**The question for the owner:** «متى وعدنا العميل أن يراه — خلال هذه التجربة، أم مع V2؟»

| Option | What it means | What it costs |
|---|---|---|
| **During the V1 pilot** | The client sees explanations on the screen he already uses | Competes with the pilot's own work. Only Decision 1 **A** is possible without F8 |
| **With V2** | Explanations arrive with ordering. PRD §5 dates V2 at ~15/10 | The pilot runs on unexplained findings. The client was promised otherwise, and should hear the date |

The register row for F14 says **V2, proposed** until this is answered.

---

## What is not in question

- **The promise itself.** Confirmed standing, 2026-09-24.
- **The constraint above.** It follows from D-1, D-3 and D-10, which are settled.
