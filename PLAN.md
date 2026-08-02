# SmartShelf AI — Pilot Handover Plan

**Goal:** hand YomYom a working product they run in a real store, and measure whether it makes them
money.

This is the master plan. Individual task lists live in `personA.md`–`personD.md`. This file owns the
things that belong to **nobody in particular and therefore get forgotten**: sequencing, integration,
release criteria, QA, and the cut line.

> ⚠️ **Set real dates before starting.** Phases below are relative. Fill in the actual handover date
> at the top of this file and work backwards — everything else depends on it.
>
> **Handover date: 13/08/2026**

---

## 1. The critical path

Only four things genuinely block handing this to a customer. Everything else is improvement.

```
B-1 deploy to a URL ──┐
B-2 real persistence ─┼──► HANDOVER POSSIBLE
C-1 Hebrew/RTL UI ────┤
D-5 handover docs ────┘
```

If these four are not done, there is nothing to hand over — the app runs on one laptop, in English,
losing data on cache clear, with no instructions. **Protect these four above all else.**

Everything else (velocity, LLM explanations, price-gap screen, expiry capture) makes the product
*better*. These four make it *exist*.

## 2. Phases and integration gates

Parallel work that never converges produces four things that don't compose. These gates are
mandatory — everybody stops and integrates.

### 📅 The calendar — 11 days

| Dates | What |
|---|---|
| **Mon 03/08** | **Day 1:** D-0 (ask YomYom), C-0 (data contract). Delete stale branches. |
| Mon 03 – Thu 06/08 | **Phase 1** — foundations, all four in parallel |
| **Thu 06/08** | 🚦 **GATE 1** — deployed URL, real data, opens on a phone |
| Fri 07 – Sun 09/08 | **Phase 2** — persistence, telemetry, price-gap screen |
| Sun 09 – Tue 11/08 | 🚦 **GATE 2** — the four of you run the daily routine for 3 straight days |
| Tue 11 – Wed 12/08 | **Phase 3** — fix what the dry run exposed. **Feature freeze Tue 11/08.** |
| **Wed 12/08** | 🚦 **GATE 3** — go / no-go against §4 |
| **Thu 13/08** | **HANDOVER** |

**11 days for 4 people means you will not build everything.** Read §6 (the cut line) *now*, not on
day 9. The planogram is already cut. Assume the LLM goes too — it is blocked on Gemini billing and
mock explanations are honest and rule-based.

Gate 2 is not padding. It is the only thing standing between you and discovering on 13/08, in front
of the customer, that the daily loop doesn't hold together. **Do not let Phase 3 eat it.**

### 🔔 Day 1 — before any code is written

Two things must happen on day one. Both have a named owner and produce a **written** answer.

| Owner | Task | Deliverable |
|---|---|---|
| **D** | **D-0** — send YomYom the two questions (sales export? daily CSV?) | Answers recorded in §7 below |
| **C** | **C-0** — write `docs/UI_DATA_CONTRACT.md` | Committed + Person D's sign-off (D-0b) |
| A | **A-0** — chase D until the answers land; build A-1 without waiting | — |

Neither blocks the start of coding: A-1 is designed to work without YomYom's answers, and C-0 is an
hour's work. But **C and D must not write code against different assumptions** — that is the one
collision the file split cannot prevent on its own.

### Phase 1 — Foundations (parallel, no dependencies)

| Who | Task |
|---|---|
| A | A-1 velocity engine, A-2 daily snapshot |
| B | B-1 deploy, B-5 env hygiene |
| C | C-1 Hebrew data rendering, C-2 honest analytics |
| D | D-1 daily action list, D-2 expiry capture |

Nobody is blocked. Everybody starts immediately.

### 🚦 GATE 1 — First integration

**Everyone merges to `main`. Deployed URL shows real YomYom data in Hebrew, end to end.**

Do not proceed until a teammate can open the URL on their phone and see real Hebrew product data.
If this slips, the handover slips — say so out loud rather than hoping to catch up.

### Phase 2 — Make it real

| Who | Task |
|---|---|
| A | A-3 sales adapter, A-4 quality gate |
| B | B-2 persistence, B-3 telemetry |
| C | C-3 LLM async fix, C-4 store-floor layout |
| D | D-3 price-gap screen, D-4 daily summary |

### 🚦 GATE 2 — Dry run

**The four of you run the full daily routine yourselves, for three consecutive days, before YomYom
ever sees it.** Export the CSV, run `pilot_daily.sh`, open the app, action the alerts.

This is the single highest-value activity in the plan. It will surface more real problems than any
amount of code review, and it is the only way to know whether the daily loop actually holds together.

### Phase 3 — Handover

| Who | Task |
|---|---|
| A | A-5 refresh competitor data (**stale prices are worse than none**) |
| B | Telemetry dashboard, monitoring |
| C | C-5 performance |
| D | D-5 handover package, training session |

### 🚦 GATE 3 — Go / no-go

Run §4. Every box ticked, or the handover moves.

---

## 3. Ownership of the cross-cutting gaps

### QA — currently owned by nobody, and there are zero tests

There is not one test file in this repo and no test tooling installed. We are asking a business to
run ordering decisions on untested software.

**Minimum bar before handover** — this is not optional:

- **Person A:** pytest over the velocity engine. A stock increase must never register as sales; a
  20% row-count drop must fail the import. These two bugs would silently corrupt every number the
  customer sees.
- **Person C:** vitest over `inventoryEngine` and `reorderEngine`, specifically the
  `velocity_confidence: 'none'` path. Nothing may classify as "Slow moving" without history.
- **Person B:** owns release. Nothing deploys that fails `npm run lint && npm run build`.
- **Person D:** owns the manual pass — every screen at 390px on a real phone, in Hebrew, before
  each gate.

Full coverage is not the goal. Cover the paths where a silent wrong number reaches the customer.

### Git workflow

9 local branches and a history of long-lived person branches. Four parallel tracks on that will
collide.

- Branch from `main`, small and short-lived: `a/velocity-engine`, `c/rtl-layout`.
- **Merge to `main` daily.** A branch alive longer than two days is a merge conflict forming.
- `main` must always build. If you break it, fixing it is your only job.
- Delete the stale branches (`personBandC-latest`, `nagham`, `new`, `kaggle`, …) before Phase 1 so
  nobody branches off a dead one by accident.

### Support during the pilot

It will break in the shop on a weekday morning. Decide now:

- **Who is on call**, and what response time you promise YomYom.
- **How they reach you** — one WhatsApp number, not four.
- **Rollback:** how to revert to the last good deploy in under 5 minutes.
- **A daily glance** at the telemetry to catch a broken import before the customer notices.

---

## 4. Go / no-go checklist

Every line must be true before YomYom uses this unsupervised.

**Works**
- [ ] Deployed URL, HTTPS, access-controlled, loads on a phone in under 5 seconds
- [ ] Real YomYom data, refreshed by a single documented command
- [ ] Decisions survive a cache clear and a browser change
- [ ] `main` builds clean; lint passes

**Honest** *(the credibility bar — a wrong number costs more than a missing feature)*
- [ ] No product shows "Slow moving" without real sales history behind it
- [ ] Recommendation confidence is visible, and low-confidence ones say so
- [ ] Competitor prices are dated and current, or clearly labelled as reference data
- [ ] Anything running on invented constants (planogram) is hidden or labelled a preview
- [ ] No screen displays a number we cannot explain to the customer on the spot

**Usable**
- [ ] Full Hebrew/RTL, correct ₪ and date formatting
- [ ] Works one-handed on a phone
- [ ] Recording an expiry date takes under 15 seconds and no terminal
- [ ] A non-technical person completes the morning routine from the written guide alone

**Measurable**
- [ ] Every recommendation shown, and every accept/dismiss, is recorded
- [ ] We can report acceptance rate and ₪ impact without opening a terminal
- [ ] Baseline captured **before** go-live — otherwise no improvement can be proven

**Supported**
- [ ] On-call named, feedback channel live, rollback tested at least once

---

## 5. What "how good is it" means

Agree these numbers **before** go-live, or the pilot ends in opinions.

| Question | Measure | Target |
|---|---|---|
| Do they use it? | Days opened / pilot days | **> 60%** |
| Do they trust it? | Recommendations accepted / shown | **> 30%** |
| Which alerts are worth keeping? | Acceptance rate **by type** | rank them |
| Did it make money? | ₪ from repriced below-cost items + prevented expiry waste | **> 0, provable** |
| Is it wrong anywhere? | Dismissals tagged "wrong data" | **< 10%** |

The last row matters most. **A tool that is confidently wrong is worse than no tool** — it costs a
customer relationship, not just a feature.

Capture a baseline in week 0: how many below-cost products, current expiry waste, current margin.
Without it, nothing after can be attributed to us.

---

## 6. The cut line

You will not finish everything. Cut in this order, from the top:

1. **Planogram** — runs entirely on invented constants. Hide it.
2. **LLM explanations** — blocked on Gemini billing anyway. Mock explanations are rule-based and
   honest. This is a demo feature, not a pilot feature.
3. **C-5 performance** — a slow first load is survivable.
4. **D-4 printable summary** — nice, not load-bearing.
5. **A-3 sales adapter** — the snapshot proxy covers it if YomYom has no sales export.

**Never cut:** the four critical-path items, the honesty checks in §4, or the telemetry. Shipping
something small and true beats shipping something broad we cannot defend.

### If the deadline is very short

Ship **one screen**: the daily action list, in Hebrew, deployed, with real price-gap and below-cost
alerts and working accept/dismiss. That alone is a real product built on real data — 14,406 matched
barcodes and 60 products provably selling below cost. It is defensible, valuable, and honest.

A narrow tool that works earns the second meeting. A broad one that shows made-up numbers does not.

---

## 7. Decisions

### ✅ Resolved

1. **UI language — English for the pilot.** No RTL flip, no i18n. Person C's C-1 shrinks to
   rendering Hebrew *data* correctly inside an English layout (`dir="auto"`, column alignment,
   Hebrew-aware sorting). **Revisit if floor staff — not just the manager — are expected to use it.**

2. **Planogram — HIDE IT for the pilot.** Measured against real data, it assigns **all 7,451
   products to the BOTTOM shelf with exactly 2 facings each**; zero products reach eye level and
   scores top out at 0.07/1.0. Three compounding causes: 45% of the score is sales velocity (zero),
   the category rules are hardcoded English (`'Snacks'`, `'Water'`) against Hebrew categories so
   **0 of 7,451 match**, and a "Slow moving" early-return sends every product to the bottom.
   It also needs real `shelfCapacity`, which exists in **no** data source we have — currently
   hardcoded to `10` for every product. Fixing it is a shelf-survey project, not a code task.
   → Person D removes it from navigation. Person C leaves the engine in place, unwired.

3. **Customer relationship — owned by the team.** Still name **one person** for outbound messages
   so YomYom hears a single voice; internally decide together.

### 🔴 Open — owner: Person D, due Mon 03/08 (task D-0)

**Person D sends one message containing both. Person A chases until answered (A-0) and is told
directly. Write the answers in below, with the date received.**

4. **Does the POS export sales/transactions, or only inventory?**
   Ask for a sample of *any* sales report the system can produce.
   If yes → the reorder engine works immediately and A-3 outranks A-1.

   > **ANSWER:** ______________________  _(date: ____)_

5. **Can the manager send the CSV daily?** Today it arrives irregularly. **Velocity accuracy is a
   direct function of this cadence** — the highest-leverage ask in the whole pilot. Frame it as 30
   seconds a morning and offer to automate it (scheduled export, shared folder, WhatsApp) rather
   than asking for discipline.

   > **ANSWER:** ______________________  _(date: ____)_

   If the answer is weekly, not daily: Person A widens the `velocity_confidence` bands and we lower
   what we promise the customer. It does not stop the pilot — but it must not be discovered late.

> One message, two asks. Don't spend two separate favours. A-1 is designed to work without either
> answer, so **nothing waits on this** — but the sooner it lands, the less rework.

### 🟡 Agreed on day 1 — owner: Person C, due Mon 03/08 (task C-0)

6. **The `App.jsx` ↔ `src/pages/` prop contract.** Person C drafts `docs/UI_DATA_CONTRACT.md`,
   Person D signs off (D-0b). This is the only real coupling in the four-way split and the one
   collision the file-ownership split cannot prevent by itself. Neither writes code until it's agreed.

   > **SIGNED OFF:** ☐ C drafted  ☐ D agreed  _(date: ____)_
