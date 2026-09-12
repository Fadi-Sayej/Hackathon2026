---
ID: SPEC-GAPS
Title: Gaps, Open Questions and Assumptions
Status: Living
Version: 0.1 (content unchanged from `specs.md` v1.1)
Parent: [Intent Register (SPEC-000)](../product/intent-register.md)
Related Specs: all F#-S# documents under `docs/features/`
---

> **Migration note.** Moved verbatim from the pre-migration monolithic `specs.md`. It spans
> every feature, so it lives at the feature layer's root rather than under one feature.
> `GAP-…`, `OQ-…` and `ASM-…` identifiers are unchanged.

# SPEC-GAPS — Gaps, Open Questions and Assumptions

**Status:** Living
**Version:** 0.1 (2026-09-08)
**Scope:** All specifications in this directory, against the intents in
[the PRD and feature intents](../product/PRD.md)

This file records where the intent layer is contradictory, under-decided, or in
conflict with behavior the repository already protects. Nothing here has been resolved
by guessing.

---

### Part 1 — Specification Gaps Found

#### GAP-001 — The competitor-comparison intent contradicts protected behavior, and almost nothing survives the conflict

**Source:** `intent.md` §3 (INT-003) against existing store-format behavior enforced in
the repository and by an existing acceptance check.

**Problem:**
The intent derives its thresholds (a statistical break at 90%, a commercial bound at
60%) from a population of 1,970 comparisons drawn from three competitors. Existing
protected behavior classifies those three very differently:

| Competitor | Format | Existing treatment |
|---|---|---|
| The nearby forecourt shop | Same format as our store | May drive a recommendation |
| The supermarket | Below the comparability floor | **Context only — may not drive a recommendation** |
| The hypermarket | Affinity zero | **Dropped before any engine sees it** |

Applying the intent's thresholds under existing behavior:

| Threshold | Items above it | May drive a recommendation | Context-only source | Excluded source only |
|---|---:|---:|---:|---:|
| Commercial (60%) | 165 | **4** | 141 | 20 |
| Statistical (90%) | 24 | **1** | 22 | 1 |

An existing acceptance check fails the build when any recommendation is sourced from an
affinity-zero store, so this is not a matter of preference.

**Why it matters:**
INT-003 is a V1 intent. As specified it produces four actionable items, not 165. Either
the capability is far smaller than the intent implies, or the format policy must change.
The entire content of SPEC-003 turns on this, and so does whether INT-003 belongs in V1
at all.

**Status: RESOLVED (2026-09-08).** Not by choosing between the two positions, but by
changing what a comparison is. A cross-format price never stands alone: it forms one half
of a balanced reference, or is adjusted by a measured format allowance where no
same-format price exists. The judgement is then made against the owner's declared policy
rather than against a competitor's price — so the format rule's purpose survives while
genuine outliers are no longer invisible.

The resolution also brought a constraint nobody had stated: a recommendation must leave a
margin over our own purchase cost. That removes 43 of the 144 breaches — a larger effect
than the format question itself, and it would have shipped as a defect.

**Confidence:** High — every figure is measured from the pilot data.

---

#### GAP-002 — The daily surface cannot be ordered, because the intent forbids the only common unit

**Source:** `intent.md` preamble (INT-NS) against §2 (D-2).

**Problem:**
The surface must present "at most 10 actions, ranked by money". But the intent also
forbids ever combining a recurring per-sale amount with a standing one-time amount, and
separately requires that hygiene signals carry no money at all. So the surface must
produce one ordered list from three incommensurable kinds: recurring values, standing
values, and no value.

There is no rule anywhere for ranking them against one another.

**Why it matters:**
Without it, the ten-item bound cannot be applied. This is the surface the whole product
is organised around, and it cannot be built from the intents as written.

**Recommended resolution:**
Rank within kind, and allocate places across kinds explicitly — for example a fixed
number of places reserved for standing-value work and for unvalued hygiene work, with
the rest going to recurring value. An explicit allocation is defensible to the owner
("two of your ten are counting tasks"), whereas an implicit conversion between kinds
would breach D-2 by the back door.

**Status: RESOLVED (2026-09-08).** Not by choosing an allocation between kinds, but by
removing one kind. SPEC-002 no longer produces a monetary figure (FR-023), so V1 holds a
single monetary kind and FR-104 alone orders it. What survives is the smaller question of
how many places unvalued work receives — OQ-602, now P1.

**Confidence:** High.

---

#### GAP-003 — Automatic withdrawal may make its own reversal unreachable

**Source:** `intent.md` §4 (INT-009).

**Problem:**
Withdrawal is justified by being reversible: a withdrawn product returns "on its first
sale". But a withdrawn product is absent from working surfaces, therefore absent from
ordering, therefore may not be restocked, therefore cannot sell. For seasonal products —
the exact case the zero-stock restriction was designed to protect against — the revival
condition may be unreachable in principle.

**Why it matters:**
It determines whether withdrawal may affect ordering surfaces at all, or only
attention-facing ones. That is a scope question, not an implementation one, and it
governs the shape of INT-009 and later INT-004.

**Status: RESOLVED (2026-09-08).** Not by weakening withdrawal, but by making its
strength follow the evidence. Withdrawal is re-evaluated on every ingestion (FR-060a);
while the window is shorter than a full annual cycle every withdrawal is declared
provisional (FR-063a); when the evidence reaches a full cycle the declaration stops and
earlier withdrawals are re-examined, returning those that prove seasonal (FR-063c).

The two-year sales evidence that closes this has already been requested from the owner,
so the gap has a dated resolution rather than an indefinite one. The residual exposure
in the interim is stated in OQ-401 and accepted.

**Confidence:** High.

---

#### GAP-004 — The reconciliation arithmetic assumes period alignment that has not been established

**Source:** `intent.md` §1 (INT-002) and the arithmetic it describes.

**Problem:**
The inconsistency test computes an implied opening balance from recorded stock,
receipts and sales. It is valid only if all three describe the same period. Recorded
stock is a current snapshot; receipts and sales come from monthly reports covering
January to July. If the snapshot post-dates the reports, every magnitude is wrong by the
activity in between — and the sign of the error is unknown.

**Why it matters:**
It affects both monetary totals in INT-002. The *detection* may survive (a negative
implied opening balance still indicates something is wrong), but the *magnitude* — and
therefore both the confirmed and the estimated figure — may not.

**Recommended resolution:**
Establish the vintage of each input before the flagged list is shown. **Partly overtaken
(2026-09-08):** the magnitude is no longer stated at all, so the exposure is now confined
to ordering and to the risk of flagging a consistent product. Establish the vintages;
where they cannot be aligned, state the window the flags rest on.

**Confidence:** Medium — the misalignment is plausible from the data vintages but has
not been confirmed.

---

#### GAP-005 — A V1 figure rests on data that is not reproducible

**Source:** `intent.md` §3 and §12 (INT-003, INT-PROV).

**Problem:**
The coverage figures for the competitor comparison derive from a matching artefact that
is not carried in the repository and is regenerated locally. Reproduction on a fresh
copy cannot produce them. This directly violates the intent's own rule that every stated
figure be reproducible on demand.

**Why it matters:**
The rule exists so a challenged figure can be recomputed in front of the owner. A figure
that cannot be is the exact failure the rule was written to prevent — and it appears in
a V1 intent.

**Recommended resolution:**
Either bring the derivation within reproduction, or remove the coverage figures from
owner-facing material until it is. Do not state them from the document.

**Status: OPEN — narrowed, and a release condition rather than a design blocker.** The
competitor capability now also states counts derived from the same artefact (SPEC-003
FR-046), so the obligation grew rather than shrank. What it blocks is stating these
figures to the owner, not designing the system.

**Confidence:** High — verified by inspection.

---

#### GAP-006 — "Data hygiene" is in V1 but cannot compete for a place on the only V1 surface

**Source:** `intent.md` §1 (INT-002B) against the preamble (INT-NS).

**Problem:**
INT-002B is deliberately money-free. The surface ranks by money. Strict ranking excludes
hygiene work permanently, so an intent that is in V1 has no route to the owner. The
intent does not say where this work is meant to appear.

**Why it matters:**
Either hygiene work needs reserved places on the surface, or it belongs somewhere else
entirely. Left unresolved, it will be built and then never seen.

**Recommended resolution:**
Resolve with GAP-002 as one allocation decision. Reserving a small number of places is
consistent with the intent treating hygiene as real work rather than as noise.

**Status: RESOLVED (2026-09-08) in principle.** SPEC-006 FR-106 settles that unvalued
entries receive a stated allocation rather than competing on money. Only the size of that
allocation remains open, as OQ-602 (P1). Note that INT-002 has since joined INT-002B in
carrying no money, so the reserved allocation now serves both.

**Confidence:** High.

---

#### GAP-007 — The intent claims a ten-minute daily commitment that nothing verifies

**Source:** `intent.md` §10, and the ten-item bound in the preamble.

**Problem:**
"Ten minutes each morning" appears as an owner commitment, and the ten-item bound is
justified by it. Neither has been observed. Ten items each requiring the owner to walk
to a shelf and count is not a ten-minute task.

**Why it matters:**
The bound is the core product decision of V1, and the acceptance criterion for the
surface (NFR-050) is stated in terms of this claim. If the claim is wrong, the bound is
wrong.

**Recommended resolution:**
Measure it during the pilot rather than asserting it. Until measured, treat ten as a
provisional bound and state it as provisional in owner-facing material.

**Status: OPEN — only measurement closes it.** No decision taken now can settle a claim
about how long the owner actually takes. It does not block design: the bound is a stated
number that can change without restructuring anything.

**Confidence:** Medium.

---

#### GAP-008 — The V2 ordering intent states an order of inputs, not a rule

**Source:** `intent.md` §6 (INT-004).

**Problem:**
The intent establishes that ordering starts from market movement, is then compared with
the store's own movement, and is capped by shelf life. That is a sequence of inputs. It
is not a rule: it does not say how the three combine into a quantity, nor what
geographic extent defines "the market", nor what happens when market movement and the
store's own movement disagree.

**Why it matters:**
INT-004 is described as carrying the largest value in the product. It cannot be
specified, and therefore cannot be designed, from a sequence of inputs.

**Recommended resolution:**
Do not specify INT-004 yet. Resolve the radius, the combination rule and the
disagreement case as explicit product decisions first. Its release is far enough out
that this does not block V1.

**Confidence:** High.

> **Added 2026-09-12 (not part of the migrated content).** The three decisions are now
> posed as answerable questions, with the options the data supports, in
> [F8 — the three decisions](../product/open-decisions/F8-ordering.md). That document
> resolves nothing; it exists so the decisions can be taken in one sitting. It raises
> four new open questions, **GAP-008a … GAP-008d**, one of which is blocking: the
> `WATCH_PRODUCT` population is 527 in F8's intent and 1,857 in `public/data/operational.json`
> (2026-09-10).

---

#### GAP-009 — "Sold nothing" is, for every classified product in the pilot, "has no sales row"

**Source:** `intent.md` §4 (INT-009) and SPEC-004 ASM-030, measured against the pilot data
on 2026-09-08.

**Problem:**
SPEC-004 classifies on sales evidence over the observation window. Measured against
`data/internal/silver_pos/`:

| Class | Count | Present in the sales reports | Absent entirely |
|---|---:|---:|---:|
| Living (sold > 0) | 1,614 | 1,614 | 0 |
| Withdrawable (0 sales, 0 stock) | 3,932 | **0** | 3,932 |
| Idle (0 sales, stock > 0) | 1,674 | **0** | 1,674 |
| Negative stock, 0 sales | 243 | 1 | 242 |

Exactly **one** product in the whole catalogue appears in the sales reports with an
observed zero. Every other "dead" product is dead only in the sense that the seven monthly
reports contain no row for it. Consequently `observed_days`, `last_sale_date`,
`total_receipts_all_months` and `last_purchase_date` are null for 100% of the idle set —
which is why every non-monetary ordering key other than unit cost was found unbuildable,
and why `data/internal/receiving/` (absent) cannot supply one either.

**Why it matters:**
ASM-030 names this as "the strongest assumption in this specification", which understates
it: it is not an assumption at the margin but the entire load-bearing wall under 78% of
the classification, including all 3,932 automatic withdrawals. The project's own rule —
that products with no sales rows are reported as `none`, never as zero — is in direct
tension with labelling them «صفر مبيعات». Note this is *not* a breach of INV-036, which
governs the sales evidence being absent as a whole rather than a product being absent from
it.

**Status: OPEN — a release condition and a measurement, not a design blocker.** The
reading that a monthly POS sales report lists everything that sold, so absence means zero,
is defensible and is what ASM-030 records. Nothing in the design changes if it is right.
What changes if it is wrong is the entire catalogue-cleanup capability, so it must be
established with the owner before 3,932 products are withdrawn in front of him — the
cheapest test being to name twenty absent products and ask whether any of them sold.

**Confidence:** High — measured directly from the pilot artefacts.

---

### Part 2 — Open Questions by Priority

#### P0 — blocks system design

**None.** All five questions that blocked system design have been resolved.

| ID | Resolution |
|---|---|
| ~~OQ-301~~ | A cross-format price forms half a balanced reference, never a standalone benchmark; judgement is against a declared policy, gated by a cost floor |

**Resolved or downgraded since version 0.1**, all by one decision — SPEC-002 no longer
produces a monetary figure:

| ID | Now |
|---|---|
| ~~OQ-601~~ | **Moot.** With no standing amount in V1 there is one monetary kind, and FR-104 alone orders it |
| ~~OQ-602~~ | **P1.** The principle is settled (FR-106: unvalued work gets a stated allocation, not a rank); only the number of places is open |
| ~~OQ-201~~ | **P1.** Period alignment governed the magnitude, which is no longer stated. Detection does not depend on it |
| ~~OQ-401~~ | **Resolved.** Withdrawal is re-evaluated on every ingestion and its strength follows the evidence window; a full annual cycle triggers re-examination of earlier withdrawals. Narrowed to OQ-407 (P1) |
| ~~OQ-406~~ | **Resolved.** The window follows available evidence. Narrowed to OQ-408 (P2) |

The five resolutions came from four decisions, each taken because a rule that read
correctly on paper failed against the pilot data: no money on any stock-derived signal;
withdrawal as a standing rule whose strength follows the evidence window; a declared
pricing policy measured against a balanced reference; and a cost floor beneath every
price recommendation.

#### P1 — important, but design can begin

| ID | Question | Spec |
|---|---|---|
| OQ-101 | Is there a materiality floor for a price difference? | SPEC-001 |
| OQ-102 | Can the owner mark an inverted price as deliberate, suppressing it? | SPEC-001 |
| OQ-202 | What is the materiality floor for an unaccounted quantity? | SPEC-002 |
| OQ-203 | When a product is both flagged for discrepancy and dead, which governs? | SPEC-002 / SPEC-004 |
| OQ-302 | When several stores observe one product, which is the benchmark? | SPEC-003 |
| OQ-303 | How are pack-size mismatches on a shared identifier handled? | SPEC-003 |
| OQ-402 | Is there an introduction grace period for new products? | SPEC-004 |
| OQ-409 | Once evidence spans a full annual cycle, does automatic withdrawal extend to stock-carrying entries? | SPEC-004 |
| OQ-407 | Should a withdrawn entry stay visible on ordering surfaces while the evidence is short? | SPEC-004 |
| OQ-403 | May the owner withdraw a product manually? | SPEC-004 |
| OQ-501 | Is "I don't know" distinct from a deferral? | SPEC-005 |
| OQ-502 | What constitutes a demonstrable change permitting a question to be re-asked? | SPEC-005 |
| OQ-503 | Do questions occupy places on the ten-action surface, or a separate place? | SPEC-005 / SPEC-006 |
| OQ-603 | May staff act on entries, or only the owner? | SPEC-006 |
| OQ-604 | When does a deferral lapse? | SPEC-006 |
| OQ-605 | Does declining suppress an entry permanently? | SPEC-006 |
| OQ-701 | Which figures must be reproducible — owner-facing, or all? | SPEC-007 |
| OQ-801 | What may the 30-day recovered-₪ measurement contain, given that its "stock explained" component cannot be stated in money (D-1)? | INT-MEAS / SPEC-000 §4 |
| OQ-702 | When reproduction and a surface disagree, which is shown? | SPEC-007 |

#### P2 — safely deferred

| ID | Question | Spec |
|---|---|---|
| OQ-103 | Should the markup ceiling be per department or per store? | SPEC-001 |
| OQ-104 | Should the delivery-price signal carry a monetary figure at all? | SPEC-001 |
| OQ-204 | After a physical count, may a monetary figure be reinstated for counted products? | SPEC-002 |
| OQ-304 | Should a competitor promotion be distinguished from a price change? | SPEC-003 |
| OQ-305 | Should a distance bound apply in addition to format affinity? | SPEC-003 |
| OQ-306 | What is the observation freshness bound? | SPEC-003 |
| OQ-404 | What happens to a revived product that still does not sell? | SPEC-004 |
| OQ-405 | What defines an implausible recorded quantity? | SPEC-004 |
| OQ-408 | What exactly constitutes a full annual cycle? | SPEC-004 |
| OQ-504 | Does an owner's answer expire? | SPEC-005 |
| OQ-505 | May staff answer questions, or only the owner? | SPEC-005 |
| OQ-606 | Should the surface guarantee variety across capabilities? | SPEC-006 |
| OQ-607 | Should new entries be distinguished from carried-over ones? | SPEC-006 |
| OQ-703 | How far back must an input vintage be traceable? | SPEC-007 |
| OQ-704 | Should reproduction record its own history? | SPEC-007 |

---

### Part 3 — Assumptions Introduced

None of these is stated by the intents. Each was necessary to make a specification
coherent, and each is a candidate to be confirmed with the owner.

| ID | Assumption | Spec | Risk if wrong |
|---|---|---|---|
| ASM-001 | The delivery-price column is the store's own listing | SPEC-001 | The whole signal compares the wrong two things |
| ASM-002 | A markup within the observed ceiling is deliberate policy, not drift | SPEC-001 | Real pricing drift is suppressed as policy |
| ASM-003 | Platform commission is unavailable, so the ceiling is inferred from behaviour | SPEC-001 | The ceiling encodes habit rather than economics |
| ASM-004 | Both prices in one export are contemporaneous | SPEC-001 | Stale pairs produce phantom differences |
| ASM-010 | Flow quantities are more reliable than stock levels | SPEC-002 | Detection cannot be claimed as certain |
| ASM-011 | Stock, receipts and sales cover the same period | SPEC-002 | See GAP-004 — magnitudes wrong |
| ASM-012 | Cost price is not used by this specification, since no valuation is produced | SPEC-002 | Only matters if a monetary figure is ever reinstated (OQ-204) |
| ASM-013 | Quantity unreliability is catalogue-wide, not departmental | SPEC-002 | Over- or under-flagging by department |
| ASM-020 | A shared identifier denotes the same sellable unit | SPEC-003 | False matches produce spurious extremes |
| ASM-021 | Observed competitor prices were actually charged | SPEC-003 | Comparison against list prices |
| ASM-022 | Format affinity encodes product judgement, not data quality | SPEC-003 | GAP-001's resolution changes |
| ASM-023 | Observations refresh often enough that freshness rarely binds | SPEC-003 | Stale comparisons drive actions |
| ASM-030 | Absence from sales evidence means the product did not sell | SPEC-004 | Withdrawal removes selling products. **Measured 2026-09-08: this is not a marginal assumption — it carries 5,848 of 7,463 classifications. Exactly one product in the catalogue appears in the sales reports with an observed zero. See GAP-009** |
| ASM-031 | Zero stock plus no sales means already absent from the shelf | SPEC-004 | The justification for automatic withdrawal fails |
| ASM-032 | Product identifiers are stable across the window | SPEC-004 | Re-coded products appear dead |
| ASM-033 | The owner needs no notice before automatic withdrawal | SPEC-004 | Withdrawal feels like data loss |
| ASM-034 | Recorded stock is contemporaneous with the window's end | SPEC-004 | Misclassification at the boundary |
| ASM-040 | The owner is the only source for the facts asked | SPEC-005 | Avoidable questions reach him |
| ASM-041 | Three questions fit inside a ten-minute session | SPEC-005 | Questions displace actions |
| ASM-042 | The owner's answer beats any inference | SPEC-005 | Wrong answers become authoritative |
| ASM-043 | A product not worth keeping is not worth asking about | SPEC-005 | Inherits GAP-003 |
| ASM-050 | Ten is the right bound | SPEC-006 | The core V1 decision is wrong |
| ASM-035 | Unit cost price is available for enough idle entries to order them | SPEC-004 | Measured: 1,713 of 1,718 carry a cost above zero. The remaining 5 rank last without a value (D-3) |
| ASM-051 | Money is the right ordering principle | SPEC-006 | Urgent low-value work is never done |
| ASM-052 | The owner reviews roughly daily | SPEC-006 | Entries stale between reviews |
| ASM-053 | Ten entries take about ten minutes | SPEC-006 | See GAP-007 |
| ASM-054 | Recording an outcome is worth the owner's effort | SPEC-006 | Outcomes go unrecorded, measurement fails |
| ASM-060 | Reproducing a figure ends a dispute | SPEC-007 | The trust strategy does not work |
| ASM-061 | Reproduction and the surface read the same data | SPEC-007 | They can disagree without either being wrong |
| ASM-062 | Input vintage is knowable for every input | SPEC-007 | Some figures cannot carry provenance |
| ASM-063 | Reproduction is available at the moment of challenge | SPEC-007 | The defence is unavailable when needed |

---

### Part 4 — Contradictions Between Intents

**CON-001 — "Ranked by money" against "hygiene carries no money."**
INT-NS orders the surface by money; INT-002B forbids money on hygiene signals and places
them in V1. Both cannot hold under strict ranking. Tracked as GAP-006 and OQ-602.

**CON-002 — "Recurring and standing are never summed" against "one ranked list."**
INT-002's D-2 and INT-NS's single ordered surface. Tracked as GAP-002 and OQ-601.

**CON-003 — "Withdrawal is reversible on the first sale" against "withdrawn products are
excluded from other capabilities."**
INT-009 states both. **Resolved (2026-09-08):** revival no longer depends solely on a
sale. Extending the evidence to a full annual cycle re-examines every withdrawal and
returns those that prove seasonal (FR-063c), so the reversal path does not require the
product to be on a shelf. Whether withdrawn entries should also stay visible on ordering
surfaces meanwhile is OQ-407.

**CON-004 — "Every figure is reproducible" against a V1 figure that is not.**
INT-PROV and INT-003. Tracked as GAP-005.

**CON-005 — "No money on a stock-derived signal" against "idle stock, ranked by money."**
`intent.md` §12 rule 1 forbids a shekel figure on any signal derived from a stock
quantity, "including our own derivations, in full and not by half". `intent.md` §4 valued
the idle set at ₪919,170 and ranked it by money. Both were carried into the
specifications — the money into SPEC-004 FR-069, the claim that no such money existed into
SPEC-006 FR-105 — and neither noticed the other.

**Resolved (2026-09-08):** rule 1 governs. The idle set carries no monetary figure and no
aggregate, and is ordered by **unit cost**, which is a property of the product rather than
a quantity and therefore outside rule 1 (D-11, `intent.md` §4ب). The distinction once
offered in defence of the money — that reconciliation claimed a *loss* while the idle set
described *standing inventory* — was rejected as a post-hoc justification: both read the
same unreviewed column, and ₪919,170 is the more fragile of the two at fourteen times the
size and ₪554 per product in a forecourt shop. The figure is not deleted but moved to the
12/9 agenda as a question to the owner: "we computed this from your column — do you trust
it?" His answer governs whether it may ever return (OQ-204's counterpart for SPEC-004).

**Why it survived two reviews:** SPEC-002's removal of money was treated as sufficient to
close GAP-002, and nobody re-derived the premise afterwards. FR-105 now forbids asserting
it.

---

### Part 5 — Repository Behavior That Contradicts an Intent

**REPO-001 — Competitor comparison.**
The intent's §3 analysis treats all three competitors as usable sources. The repository
drops one entirely and forbids another from driving a recommendation, and an existing
acceptance check enforces it. See GAP-001.

**REPO-002 — The unbounded daily list.**
Existing behavior presents every actionable finding on the daily surface. INT-NS bounds
it at ten. This is an intended change, recorded here so the compatibility obligation is
explicit: previously recorded decisions must survive the change (SPEC-006 FR-115, C-50).

**REPO-003 — Negative stock is clamped at the data boundary.**
Existing behavior clamps negative stock to zero for downstream consumers while reporting
the count separately. SPEC-004's withdrawal rule must read the recorded value, not the
clamped one; otherwise a negative-stock product would appear to have zero stock and
become withdrawable, silently violating INV-030. Recorded as SPEC-004 C-32.
