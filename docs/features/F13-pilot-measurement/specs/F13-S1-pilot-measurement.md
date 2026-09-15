---
ID: F13-S1
Title: Pilot Measurement — the 30-day recovered-₪ surface
Status: Blocked
Owner: smartshelf-architect
Version: 0.1 (2026-09-13)
Parent: [F13 — Pilot Measurement](../intent.md)
Related Intents: INT-MEAS
Inputs: [docs/product/PRD.md §8, docs/features/F13-pilot-measurement/intent.md, F7-S1, F2-S1 (FR-023), F6-S1, ADR-009, ADR-016, ADR-021, docs/reviews/system-design-readiness.md ARCH-GATE-003, OQ-801]
Updated: 2026-09-13
---

# F13-S1 — Pilot Measurement

> **This spec is `Blocked`, deliberately and only in part.** Everything that does not
> depend on a number the owner has not yet given is specified below and is ready to build.
> What is missing is listed under [§14 Blocked on](#14-blocked-on) — it is four items, three
> of them a conversation and one of them OQ-801. Nothing here should be started until those
> close, because the parts that are blocked decide what the parts that are not are counting
> *towards*.

> **Why this spec exists now, when SPEC-000 §4 said it should not.** That section declined
> to specify INT-MEAS because it was *"already measured by an existing surface, so no new
> capability is being designed."* Verified 2026-09-13: the surface exists and measures
> nothing — it reads the frozen `operational.json`, joins on the pre-ADR-009 id namespace,
> and reads the pre-V1 decision store. The justification does not hold, which is
> **ARCH-GATE-003**, open since 2026-09-08 and the last MAJOR finding in the readiness gate.

---

### 1. Purpose

Tell the team, and the owner, **whether the pilot worked** — in his terms, from the
artefact, thirty days after V1 ships.

PRD §8 makes the whole go/no-go turn on one figure. F13's intent states the consequence
plainly: after thirty days the answer is one of three — the number was met, so a
subscription starts; it was not met but use is daily, so intentions are reviewed with him;
or there was no use, and *«نتوقّف بشرف، وقد خسرنا شهراً لا سنة»*.

This spec covers **producing the figure**. It does not choose the threshold, the price, or
the cadence; those are agreed with the owner and recorded, not built.

---

### 2. Intent Traceability

| Intent | This spec |
|---|---|
| INT-MEAS — «رقم النجاح» after 30 days | FR-135 … FR-142, AC-130 … AC-135 |
| INT-PROV — every figure carries provenance | **F7-S1 governs this surface in full.** No requirement here relaxes it |
| INT-STOCK — stock counts are unreliable in both directions | INV-066; D-1 and F2-S1 FR-023 forbid a money figure derived from stock quantities |

---

### 3. Scope

**In scope.** A measurement surface, internal to the team, that joins what the owner was
**shown** to what he **decided**, over a stated window, and states what that is worth in the
one currency it may honestly use.

**Out of scope, and deliberately.**

- The success threshold, the subscription price and the data cadence (§14) — agreed, not computed.
- Any change to what the owner is shown. This measures F6's surface; it does not alter it.
- Attribution of money to stock-derived signals. Forbidden by D-1 and F2-S1 FR-023, and no
  requirement here may be read as creating an exception.

---

### 4. Actors and Triggers

| Actor | Trigger |
|---|---|
| The team | Opens the surface at any time during the pilot; formally at day 30 |
| The owner | Present when the three-way answer is discussed; the figure is shown to him, so F7-S1 applies as if it were his own screen |
| The engine | Publishes outcomes and values in the artefact; this surface reads, never writes |

---

### 5. Domain Terms

| Term | Meaning here |
|---|---|
| **shown** | An entry published in `capabilities.*.entries` for a run inside the window. Identity is `entry_id` = `sha256(signal_family ‖ barcode ‖ variant)` (ADR-009) |
| **decided** | An outcome **the owner** recorded against an entry, carrying `signal_family` (ADR-016). It lives in `smartshelf.ownerState.v2` on the device he used and, since #94, in `stores/{store}/ownerState/outcomes`, which the engine pulls. It is **not** whatever `smartshelf.ownerState.v2` holds on the device reading this surface |
| **acted on** | A decision that resolves the entry rather than dismissing it. The vocabulary is F6-S1's, not a new one |
| **recovered ₪** | The money component of what the owner acted on, **and only the components that may carry money** (INV-066) |
| **window** | The stated measurement period. Every figure names it (F7-S1) |

---

### 6. Functional Requirements

**FR-135** — The surface MUST compute every figure from `public/data/dashboard.json` and
**the owner's** recorded outcomes. It MUST NOT read them from the reading device's own
`smartshelf.ownerState.v2`, which on a team device holds the team's clicks, not the owner's
decisions. It MUST NOT read `public/data/operational.json`, which is frozen and is deleted in
Phase 4 Task 4.2. Where the owner's outcomes are read from is open — §14 item 5.

> **Corrected 2026-09-13.** The first version of this requirement, and of §5 and §9, named
> `smartshelf.ownerState.v2` as the source of outcomes and described it as "Firestore,
> browser-written". Neither half held. The browser wrote nothing to Firestore until #94, and
> the design's own current-state trace (§3) had recorded that outcomes "never leave the device"
> while this spec was describing the §9.3 / §11.5 target as if it were built. And even with
> write-through built, `smartshelf.ownerState.v2` is per device: read on the team's screen it
> measures the team. The requirement is corrected here; the source it needs is item 5.

**FR-136** — Entries MUST be joined to outcomes on `signal_family` and `entry_id`. A surface
that joins on a capability id is wrong by ADR-009, which makes `signal_family` permanent and
the capability id mutable.

**FR-137** — The surface MUST report, per `signal_family` and in total, over the window:
shown, decided, acted on, and dismissed.

**FR-138** — Money MUST be taken from the value the engine published on the entry. The
surface MUST NOT recompute it. (Rule 11; and the prior implementation recomputed money via
`actionPriority.js`, which is how it came to carry a D-1-forbidden stock-derived figure.)

**FR-139** — The surface MUST NOT sum values of different `kind`. `value_kinds_present` is
published in the artefact for exactly this, and rule 8 records the headline that resulted
last time: *"₪106,164 per sale"*.

**FR-140** — For a component that may not carry money (INV-066), the surface MUST state a
**count**, and MUST NOT state a money figure, a zero, or a blank that reads as zero.

**FR-141** — Every figure MUST be rendered with its window, its vintages and the thresholds
in force (F7-S1 FR-122/FR-123).

**FR-142** — Where an input is absent, the surface MUST read **unavailable**, with a reason,
and MUST NOT substitute `0` (ARCH-DRIVER-002).

---

### 7. Behavioral Invariants

**INV-066** — Of the three components the intent names, **only «أسعار مصحّحة» may be stated
in money.** «مخزون مفسّر» is derived from stock quantities the owner himself calls
unreliable in both directions — D-1 and F2-S1 FR-023 forbid a money figure over it — and
«كتالوج منظّف» has no money basis. The composite headline the intent implies therefore
cannot be a single ₪ figure without breaching D-1. What it may be instead is **OQ-801**, and
it is why this spec is `Blocked`.

**INV-067** — The surface is read-only with respect to owner state. The browser writing the
owner's decisions remains the sole writer (ADR-003).

**INV-068** — A device that never opened the app is invisible to this surface, as it is to
ADR-021's device count. "No decisions recorded" MUST NOT be rendered as "the owner rejected
everything".

---

### 8. Behavioral Scenarios

**SCN-128** — *The owner acted on eleven entries, four of which carry money.* The surface
states the money total over those four, the count over all eleven, and does not imply the
other seven were worth nothing.

**SCN-129** — *The window contains a run in which `competitor_position` was unavailable.*
Entries not shown are not counted as un-acted-on. Unavailability is not refusal.

**SCN-130** — *An outcome exists whose `entry_id` is not in any run in the window.* It is
reported separately and not silently dropped — it means the join or the window is wrong, and
that is the failure this whole spec exists to catch.

**SCN-131** — *No outcomes at all have been recorded.* The surface says so explicitly, and
distinguishes "nothing recorded" from "recorded and all dismissed" (INV-068). At the time of
writing this is the live state: the engine's mirror pulls `answers: 0, outcomes: 0`.

---

### 9. Inputs and Observable Outputs

| Input | Source | Absent ⇒ |
|---|---|---|
| shown entries | `dashboard.json` `capabilities.*.entries` | unavailable |
| outcomes | **the owner's** outcomes — written to `stores/{store}/ownerState/outcomes` since #94. Never the reading device's `smartshelf.ownerState.v2`. How the surface reads them is §14 item 5 | unavailable, with reason |
| values, kinds | the entry's own published value | that component carries no money |
| thresholds, vintages, window | `dashboard.json` | unavailable |
| device count | `vintages.owner_state.devices` (ADR-021) | omitted, never `0` |

---

### 13. Non-Functional Requirements

**NFR-064** — Deterministic: the same artefact and the same outcome set produce the same
figures. No clock is read except to render the window.

**NFR-065** — The computation is pure and separately testable, with no React, no DOM and no
storage access — the property the existing `telemetryModel.js` has and which must survive
the rebuild.

---

### 14. Blocked on

Per handover rule 4, these are not the author's to answer. Each changes what is built, not
merely what is written.

| # | Question | Owner | Why it blocks |
|---|---|---|---|
| 1 | **رقم النجاح** — how many ₪ recovered, after 30 days, makes the pilot a success? | the store owner, on the record | Without it the surface has no threshold to render against, and FR-141 has no figure to state the comparison for |
| 2 | **OQ-801** — given INV-066, what may the composite measurement contain? A price-only ₪ figure with the other two as counts, or a different construction? | smartshelf-pm, then architect | It decides the surface's headline. Building a ₪ total first and discovering it breaches D-1 is the exact failure this spec was written to avoid |
| 3 | **سعر الاشتراك** — the subscription price, agreed *today*, starting automatically when the number is met | the store owner | Not a system requirement, and recorded here only because the intent is explicit that a trial without an agreed price measures politeness rather than value. It is a PRD commitment, not a build input |
| 4 | **إيقاع البيانات** — daily or weekly, and who sends it | the store owner and the team | Sets the measurement window's granularity, which FR-141 must state |
| 5 | **Where the surface reads the owner's outcomes from.** The engine could publish them in the artefact from its pull, or the browser could read `stores/{store}/ownerState` directly. The first keeps ADR-001's rule that the browser computes no business rule, and FR-138 already takes money from the artefact. The second adds a browser reader §11.5 names and no module implements | smartshelf-architect | FR-135 and §9 state a requirement with no source. Added 2026-09-13, after #94 showed the source this spec first named never carried the owner's decisions |

Items 1, 3 and 4 are one conversation. Items 2 and 5 are ours; 2 is answerable as soon as
item 1 is known, and 5 is answerable now.

**When these close:** set `Status: Ready for review`, fill the threshold into
`configs/policy.yaml` as a declared policy line beside `owner_declared_ceiling_pct` rather
than into code, and hand to `smartshelf-engineer` with #83.
