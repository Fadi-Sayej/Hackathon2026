# Intent → Spec Conformance Report

**Gate:** INTENTS → SPECS, judged for readiness to enter SPECS → SYSTEM DESIGN
**Artifacts audited:** [`intent.md`](../intent.md) (Arabic) · [`specs.md`](../specs.md) (English, SPEC-000 … SPEC-GAPS)
**Date:** 2026-09-08

> **Run 2 — after correction. Verdict: CONDITIONAL PASS — READY WITH NON-BLOCKING ISSUES.**
> Run 1 returned FAIL on two blockers. Both were corrected, along with five of the six
> MAJOR findings. The corrections are recorded in §11; the original findings are kept
> below unaltered, each carrying its resolution. `intent.md` is now at §4ب; `specs.md` at
> version 1.1.
>
> One blocking decision was not taken by the auditor. GATE-001 required a product decision
> the intent layer owned, and it was put to a five-advisor council with peer review, then
> checked against the pilot artefacts. That verification changed the answer materially and
> is recorded as GATE-013.

---

## 1. Executive Verdict

## ~~FAIL~~ → CONDITIONAL PASS — READY WITH NON-BLOCKING ISSUES *(run 2)*

Idle stock no longer carries money: it is ordered by unit cost, which is a product
property rather than a quantity, so D-1 holds and V1 genuinely has one monetary kind —
SPEC-006 FR-105 now derives that fact instead of asserting it. SPEC-002's acceptance
criteria were reconciled with the requirements that abolished its monetary tiers. Three
lost intent statements were restored as D-11, D-12 and D-13, and INV-030 was scoped back
to the evidence window the intent attaches to it. What remains is GAP-009: verification
that "sold nothing" means what the classification assumes — a measurement before 12/9, not
a design blocker.

### Run 1 verdict *(superseded)*

## FAIL — NOT READY FOR SYSTEM DESIGN

The specification layer is unusually disciplined: traceability is real, non-goals are
explicit, and four hard product decisions were genuinely settled rather than guessed.
Two blockers remain. First, SPEC-004 attaches a money figure to a stock quantity and
SPEC-006 then declares that no such figure exists in V1 — so the daily surface's ordering
rule rests on a false premise and GAP-002/OQ-601 were closed prematurely. Second, SPEC-002
was revised to remove money, but its invariants, outputs, NFRs and acceptance criteria
still mandate the two monetary tiers the revision deleted — the acceptance criteria
require what the requirements forbid.

---

## 2. Coverage Summary

| | Count | Intents |
|---|---|---|
| **Total registered intents** | 13 | INT-001, 002, 002B, 003, 004, 005, 006, 007, 008, 009, 010, NS, PROV |
| **In scope for this phase** | 8 | INT-001, 002, 002B, 003, 009, 010, NS, PROV |
| **Fully covered** | 4 | INT-001, INT-002B, INT-010, INT-PROV |
| **Partially covered** | 1 | INT-003 |
| **Conflicting** | 3 | INT-002, INT-009, INT-NS |
| **Missing** | 0 of the registered set | — |
| **Deliberately deferred (declared, legitimate)** | 5 | INT-004, 005, 006, 007, 008 — SPEC-000 §4 |

**Unregistered intent content** — three passages of `intent.md` carry binding product
meaning and appear in no spec and in no intent identifier: §9.1 (fixed sensors/cameras,
"killed, not deferred"), §9.2 (no multi-store, no user accounts, no other POS
integrations), §11.1 (the automatic 30-day recovered-₪ measurement that decides the
pilot). See GATE-006 and GATE-007.

---

## 3. Traceability Matrix

| Intent | Specs | Requirements | Acceptance | Coverage |
|---|---|---|---|---|
| **INT-001** — "I do not want to lose money on every sale" | SPEC-001 | FR-001…FR-013, INV-001…INV-005 | AC-001…AC-009 | **FULL** |
| **INT-002** — stock that does not reconcile | SPEC-002 | FR-020…FR-027, FR-033, INV-010…INV-012, INV-015 | AC-020…AC-024, AC-027, AC-028 | **CONFLICTING** — AC-020/AC-028, NFR-011/012, INV-012, §9 outputs still require the two monetary tiers FR-023/FR-025 abolish (GATE-002) |
| **INT-002B** — data hygiene, deliberately money-free | SPEC-002 | FR-028, FR-029, FR-030, INV-013 | AC-025 | **FULL** |
| **INT-003** — "Are my prices reasonable against my neighbours?" | SPEC-003 | FR-040…FR-053, INV-020…INV-026 | AC-040…AC-054 | **PARTIAL** — superseded derived-threshold machinery survives (GATE-003); the intent's 100 % same-day threshold is never stated though FR-045b requires it; D-5/INV-024 has no acceptance criterion |
| **INT-009** — "Clean my catalogue of dead products" | SPEC-004 | FR-060…FR-076, INV-030…INV-036 | AC-060…AC-071 | **CONFLICTING** — FR-069/AC-071 value idle stock in money against D-1 (GATE-001); INV-030 hardens a conditional intent decision into an absolute (GATE-004) |
| **INT-010** — "Complete my missing data, with minimum disturbance" | SPEC-005 | FR-080…FR-093, INV-040…INV-045 | AC-080…AC-090 | **FULL** — the strongest fidelity in the document; FR-082/FR-083 operationalise "12 questions, not 1,270" exactly |
| **INT-NS** — one morning screen, ranked by money, ≤ 10 | SPEC-006 | FR-100…FR-118, INV-050…INV-057 | AC-100…AC-112 | **CONFLICTING** — FR-105's premise "in V1 no capability produces a standing value" is false (GATE-001); FR-103's "actionable today" is defined by no producing spec (GATE-008) |
| **INT-PROV** — every figure recomputable | SPEC-007 | FR-120…FR-134, INV-060…INV-065 | AC-120…AC-129 | **FULL** — GAP-005 remains open but is correctly scoped as a release condition, not a design blocker |
| **INT-004 / 005 / 006 / 007 / 008** | — | — | — | **Deferred by declared decision** (SPEC-000 §4). The reasoning given — that specifying now would mean inventing the open product decisions — is correct and is not a gate failure |
| `intent.md` §9.1, §9.2 | *none* | *none* | *none* | **MISSING** (GATE-006) |
| `intent.md` §11.1 | *none* | *none* | *none* | **MISSING** (GATE-007) |

---

## 4. Findings

### GATE-001 — Idle stock is valued in money, which D-1 forbids and which makes SPEC-006's ordering rule rest on a false premise

**Type:** CONTRADICTION (spec vs. settled decision; spec vs. spec)
**Severity:** BLOCKER
**Confidence:** HIGH

**Intent evidence:**
`intent.md` §12, rule 1 — «لا مبلغ بالشيكل على إشارة مشتقّة من كمية مخزون — **وتنطبق علينا نحن أيضاً، وكاملةً لا نصفها**» ("no shekel figure on a signal derived from a stock quantity — and this applies to us too, in full and not by half").
`intent.md` §2ب — «بسقوطه لم يبقَ في V1 إلا **نوع واحد يحمل مالاً** — الأسعار والهوامش» ("with it gone, only one money-bearing kind remains in V1 — prices and margins").
Against, in the same intent: `intent.md` §4 — «صفر مبيعات + عليه مخزون | 1,658 · **₪919,170** | ⚠️ قراره هو — **مرتّبة بالمال**» and `intent.md` §12 — «1,535 / 3,918 / 1,658 … الراكد بـ₪919,170».

**Spec evidence:**
- `specs.md` SPEC-000 §3, D-1 — recorded as a settled decision binding every specification.
- `specs.md` SPEC-004 FR-069 — "Idle entries MUST be presented … **ranked by the value of the stock recorded against them**"; §9 Outputs — "The idle set, ranked by recorded stock value"; SCN-062; AC-071; and the domain term *Implausible quantity* = "a recorded stock whose **valuation** is inconsistent with the store's scale".
- `specs.md` SPEC-006 FR-105 — "**In V1 no capability produces a standing value**, so a single monetary ordering is well defined"; domain term *Standing value* = "an amount realised once"; §2 — SPEC-006 consumes entries produced under INT-009.
- `specs.md` SPEC-GAPS GAP-002 and OQ-601, both closed on that same premise: "SPEC-002 no longer produces a monetary figure … so V1 holds a single monetary kind and FR-104 alone orders it."
- `specs.md` SPEC-GAPS Part 4 lists CON-001 … CON-004 and does **not** list this one.

**Problem:**
Idle stock value is a monetary figure computed as recorded stock quantity × cost. It is
therefore precisely what D-1 forbids, and it is a *standing* value under SPEC-006's own
definition. Three consequences follow.

1. SPEC-004 AC-071 requires the idle set to be ranked by that figure. SPEC-000 D-1 and
   SPEC-007 C-62 forbid it. A designer cannot satisfy both.
2. SPEC-006 FR-105 asserts as fact that no V1 capability produces a standing value.
   SPEC-004 does. The ordering of the daily surface is therefore undefined again for the
   exact case FR-105 exists to govern — a recurring per-sale price figure competing with
   a one-off stock figure.
3. GAP-002 and OQ-601 were closed by removing money from SPEC-002. They were only ever
   half-closed: SPEC-002 was one of two money-on-stock sources, and the other was left
   standing without being noticed.

The reasoning SPEC-002 FR-023 gives for refusing money — "the underlying file has never
been reviewed by the owner, so no partition of it yields a defensible figure" — applies
without modification to the same file's quantities in SPEC-004. ₪919,170 for the idle set
is the same class of number as the ₪63,572 the intent layer already withdrew.

**Why this matters:**
This is the axis on which this project has already produced its two worst errors (the
"₪106,164 per sale" headline and the ₪43,281/₪20,291 partition). The specification
re-introduces it silently, in the one place nobody re-checked, and then builds the daily
surface's ordering rule on the assumption that it did not. A system designer following
the specs as written will build a surface that ranks a per-sale figure against a one-off
figure — which D-2 forbids — or will silently drop the idle set from the surface, which
removes a V1 intent from the owner's view.

**Required resolution:**
The intent layer must state which side of its own contradiction governs: either idle
stock carries no money figure and needs a non-monetary ordering key of its own (SPEC-002
FR-024's gap ratio is the precedent), or D-1 is narrower than SPEC-000 records and its
real boundary must be written down. Whichever is chosen, SPEC-006 FR-105's factual claim
must be re-derived rather than asserted, and GAP-002 / OQ-601 must be re-opened until it
holds. Record the intent-level conflict in SPEC-GAPS Part 4 alongside CON-001…CON-004.

---

### GATE-002 — SPEC-002's acceptance criteria require the monetary tiers its requirements abolish

**Type:** CONTRADICTION (requirement vs. acceptance; spec vs. intent)
**Severity:** BLOCKER
**Confidence:** HIGH

**Intent evidence:**
`intent.md` §2ب — «**القرار:** الكشف يبقى … **والمبلغ يسقط كاملاً، لا يُقسَّم**» ("the detection stays … and the amount drops entirely, it is not partitioned"), and «**الرقم الموجب ليس رقماً موثوقاً؛ هو فقط رقم غير سالب**».

**Spec evidence:**
Forbidding money — `specs.md` SPEC-002 FR-023, FR-025, FR-031, INV-010, INV-011, AC-021, AC-022.
Still requiring it, in the same specification:
- §4 Precondition — "**For the money signal:** the product has a recorded receipt quantity greater than zero"
- §9 Outputs — "**Tier membership** per flagged product" · "**Two monetary totals, separately labelled: confirmed and estimated**"
- INV-012 — "valid regardless of **which tier** a product falls in"
- NFR-011 — "the same inputs MUST produce the same flags, **tiers and totals**"
- NFR-012 — "no aggregate … may mix **the two tiers** without labelling, nor mix this specification's **total** with a recurring total"
- **AC-020** — "Every flagged product belongs to exactly one tier, and **the two tier totals sum to the combined total**. *(INV-011)*"
- **AC-028** — "Recomputation … reproduces flags, **tiers and both totals**"
- §11 — "The **money signal** is unavailable"; "Cost price missing for the entire flagged set | Report the flagged count and **no total**"
- §2 Intent Traceability and SPEC-000 §1 both still label INT-002 "**the money**"
- SPEC-GAPS Part 3 — ASM-010's risk "the **two-tier split** has no basis"; ASM-012 "One cost price per product is adequate for **valuation**", which flatly contradicts SPEC-002 §16's own ASM-012 ("Cost price is **not** used by this specification, since no valuation is produced")

**Problem:**
AC-020 is the only acceptance criterion covering the detection requirements FR-020,
FR-021 and FR-022, and it is unsatisfiable: it demands two monetary tier totals that
FR-025 forbids, while citing INV-011, which forbids currency aggregates. AC-028 has the
same defect. Removing them would leave INT-002's core detection behaviour with **no**
acceptance coverage at all.

**Why this matters:**
An independent evaluator running the acceptance criteria would either fail a correct
implementation or force a designer to re-introduce the confirmed/estimated partition that
`intent.md` §2ب deleted by name. This is not a stale comment in prose — it is the
verification contract. And the residue is self-reinforcing: §9's output list, the §4
precondition and the §11 failure table all describe a "money signal" that FR-023 states
does not exist, so a designer reading the specification front-to-back meets the deleted
behaviour four times before reaching the requirement that deletes it.

**Required resolution:**
Reconcile SPEC-002 end-to-end with FR-023. Every reference to tiers, to totals, to a
"money signal" and to valuation must be resolved one way or the other, and the detection
requirements FR-020…FR-022 need acceptance coverage that survives the removal. Fix the
duplicate, mutually contradictory statements of ASM-012, and correct INT-002's label in
SPEC-000 §1 and SPEC-002 §2 — it is no longer "the money".

---

### GATE-003 — SPEC-003 still specifies the distribution-derived threshold that FR-045 forbids

**Type:** CONTRADICTION / SPEC-INCOMPLETE
**Severity:** MAJOR
**Confidence:** HIGH

**Intent evidence:**
`intent.md` §3ب — «**السياسة تسبق الإحصاء.** العتبة المشتقّة من التوزيع تصف ما هو قائم؛ نحن نريد أن نصف ما نقبله. فالقاعدة صارت **سياسة معلنة** … أي **+60%**. رقمٌ اختاره، لا رقمٌ استخرجناه.» — §3ب explicitly supersedes §3's pair of derived thresholds (90 % statistical elbow, 60 % commercial).
`intent.md` §3ب — «ما يتجاوز **100%** يدخل شاشة الصباح، والباقي في صفحة الأسعار للمراجعة على مهل.»

**Spec evidence:**
- `specs.md` SPEC-003 FR-045 — the policy threshold "**MUST NOT be derived from the observed distribution**".
- Contradicted by, in the same specification: §5 Domain Terms — "**Statistical outlier threshold** — the point at which the observed distribution of differences breaks (derived, not assumed)"; §11 Failure table — "Threshold **underivable from the distribution** | Suppress the derived-threshold signal and report it as undetermined".
- §9 Outputs — "**Both** thresholds in force" and AC-043 — "**Both** thresholds are reported with any count derived from them", against FR-046, which names **four** values that must be reportable (policy, cost floor, format allowance, attention-separating threshold).
- FR-045b — "the separating threshold **MUST be stated**". It is stated nowhere in `specs.md`; the intent's 100 % is never carried across, though the intent's other two constants (+60 %, 10 %) are recorded in §5 Domain Terms.
- SPEC-000 §2 still lists SPEC-003 as "Draft — **blocked**, see GAP-001", while SPEC-003's own header and GAP-001 both record the resolution.

**Problem:**
Three residues of the pre-resolution design survive: a domain term for a threshold FR-045
forbids, a failure-behaviour row instructing the system to derive that threshold, and an
acceptance criterion that verifies two thresholds where the requirement names four. The
one value the intent settled — 100 % — was dropped in transit.

**Why this matters:**
A designer reading §5 and §11 will build a distribution-derived threshold that FR-045
prohibits. AC-043 under-verifies FR-046 by half, so the cost floor and the format
allowance can go unreported without failing acceptance — and those are the two values
that carry the resolution's whole protective effect.

**Required resolution:**
Remove or re-scope the derived-threshold domain term and failure row; restate AC-043 and
§9 against FR-046's four values; carry the intent's 100 % separating threshold into the
specification where the other constants live; and refresh SPEC-000 §2's status for
SPEC-003.

---

### GATE-004 — SPEC-004 hardens a conditional intent decision into an absolute invariant, and drops the condition

**Type:** SEMANTIC-DRIFT (strengthened requirement) + INTENT-LOSS
**Severity:** MAJOR
**Confidence:** HIGH

**Intent evidence:**
`intent.md` §4 — «**لماذا الحذف التلقائي مقصور على "مخزونه صفر":** لأن الصنف الذي عليه مخزون **قد يكون موسمياً**. بياناتنا تغطي يناير–يوليو فقط…» — the restriction is given a stated cause: a seven-month window.
`intent.md` §4 — «**عند وصول تقارير سنتين** (طُلبت من المالك): تُميَّز الأصناف الموسمية من الميتة فعلاً، **ويتوسّع الحذف التلقائي ليشمل ما عليه مخزون**.» ("automatic deletion expands to include products carrying stock").

**Spec evidence:**
- `specs.md` SPEC-000 §3, D-6 — "Automatic archiving is restricted to products with zero recorded stock", recorded unconditionally as a settled decision.
- SPEC-004 INV-030 — "An entry with recorded stock above zero **MUST NEVER** be withdrawn automatically (D-6)"; FR-064; AC-060; §10's state table marks the transition "**Illegal**".
- SPEC-004 FR-063a/b/c and OQ-401's resolution make the *evidence window* govern the strength of a withdrawal, but only in the direction of **returning** entries; nothing carries the intent's stated expansion.

**Problem:**
The intent states a rule together with the condition that produces it and the condition
under which it lifts. The specification kept the rule, discarded the condition, and
promoted it to an invariant — the strongest form of statement it has. INV-030 makes
permanently illegal something the intent schedules as a change once the two-year reports
arrive, and those reports are already requested (`intent.md` §10).

**Why this matters:**
Invariants are what a system designer treats as immutable and builds structure around.
Encoding a window-dependent policy as "MUST NEVER" is the difference between a
configurable rule and an architectural assumption. SPEC-004 already contains the exact
mechanism this needs — FR-060b's full-annual-cycle test — so the loss is avoidable, not
inherent. It does not block V1, whose window is seven months either way, which is why
this is MAJOR rather than BLOCKER.

**Required resolution:**
Restate D-6 with the condition the intent attaches to it, and re-express INV-030 so that
its scope is the short-evidence window rather than all time. State whether the intent's
stated expansion of automatic withdrawal to stock-carrying entries is accepted, deferred
or rejected — and if deferred, register it as an open question rather than as an
invariant.

---

### GATE-005 — SPEC-006 FR-103 admits entries on a property no producing specification defines

**Type:** AMBIGUOUS-SPEC / SPEC-INCOMPLETE
**Severity:** MAJOR
**Confidence:** HIGH

**Intent evidence:**
`intent.md` preamble — «المدير يفتح شاشة واحدة كل صباح فيرى **ماذا يفعل اليوم**، مرتّباً بالمال — لا أكثر من 10 إجراءات.»

**Spec evidence:**
`specs.md` SPEC-006 FR-103 — "An entry MUST NOT be admitted unless its producing capability **has stated it is actionable today**." The word *actionable* occurs exactly once in the requirement text of `specs.md` (line 2399). SPEC-001, SPEC-002, SPEC-003, SPEC-004 and SPEC-005 define no actionability predicate, expose no such flag in their §9 output lists, and carry no requirement obliging them to produce one.

**Problem:**
Admission to the only surface the product is organised around is gated on a property that
no producing capability is required to supply and that nothing defines. Every V1 signal is
derived fresh per ingestion and none of them distinguishes "true" from "worth doing
today".

**Why this matters:**
This is the selection rule for a ten-slot surface fed by roughly 387 price alerts, 371
reconciliation flags, 1,658 idle entries and 932 hygiene records. Two competent designers
will read "actionable today" differently — newly appearing, above a materiality floor,
not yet outcome-recorded, or simply "produced" — and each reading yields a materially
different daily screen. The related materiality questions (OQ-101, OQ-202) are already
tracked; the admission predicate that would use them is not.

**Required resolution:**
Either define actionability in SPEC-006 as an observable property, or place a requirement
on each producing specification to state one, with what it means for that capability.
Then extend the traceability so FR-103 carries an acceptance criterion; it currently has
none.

---

### GATE-006 — Two explicit intent exclusions survive nowhere in the specification layer

**Type:** INTENT-LOSS / NON-GOAL-INTEGRITY
**Severity:** MAJOR
**Confidence:** HIGH

**Intent evidence:**
`intent.md` §9.1 — «مراقبة رف لحظية بحسّاسات أو كاميرات مثبّتة — مشروع عتاد لا يحمله فريق من اثنين. **مقتولة، لا مؤجّلة.**» ("killed, not deferred").
`intent.md` §9.2 — «**تعدّد متاجر، حسابات مستخدمين، تكاملات POS أخرى** — لا شيء قبل أن يثبت متجر واحد القيمة.»

**Spec evidence:**
Searched across the whole of `specs.md`: no occurrence of multi-store, multiple stores,
user accounts, tenancy, sensors, cameras, or other point-of-sale integrations — not in
any §18 Non-Goals list, not in SPEC-000 §3's decision register, not in SPEC-000 §4's
deferral list. SPEC-000 §4 defers INT-006 as an intent, which is a different statement
from §9.1's permanent exclusion of the sensor approach to it.

**Problem:**
The intent layer's §9 is a list of commitments the team will make to the owner in person
on 12/9. Two of its seven items — one a permanent kill, one a scope ceiling — are absent
from every specification. The five that survive (velocity honesty, coverage honesty,
seasonal honesty, no POS writes, planogram framing) all landed as requirements, which
shows the omission is an oversight rather than a decision.

**Why this matters:**
§9.2 is precisely the kind of boundary the system-design phase acts on: single-store,
single-user, one POS import path. Its absence lets a designer generalise — multi-tenant
data shapes, an account model, a connector abstraction — with no requirement contradicting
them and considerable cost. §9.1's kill is what stops the sensor approach re-entering by
the back door when INT-006 is finally specified for V4.

**Required resolution:**
Carry both exclusions into the specification layer where they bind: §9.2 as a global
scope constraint (SPEC-000 §3 is the natural home, alongside D-7), §9.1 as a recorded
permanent exclusion attached to the INT-006 deferral in SPEC-000 §4.

---

### GATE-007 — The pilot's decision criterion — automatic measurement of recovered money — is specified nowhere and partly collides with D-1

**Type:** COVERAGE-GAP + CONTRADICTION
**Severity:** MAJOR
**Confidence:** MEDIUM

**Intent evidence:**
`intent.md` §11.1 — «**رقم النجاح:** بعد 30 يوماً من V1، كم ₪ مستردّة (أسعار مصحّحة + **مخزون مفسّر** + كتالوج منظّف) تجعلها ناجحة؟ **القياس آلي عبر شاشة القياس المبنية.**»
`intent.md` §11 closing — the whole 30-day go/no-go turns on that number.

**Spec evidence:**
No requirement, invariant, scenario or acceptance criterion anywhere in `specs.md`
concerns measuring recovered money, and the phrase does not appear. SPEC-006 §18 pushes it
out — "Reporting on outcomes over time (**a separate, existing capability**)" — without
registering it as an intent in SPEC-000 §1 or as a deliberate deferral in SPEC-000 §4.
Meanwhile SPEC-002 FR-023, FR-025 and INV-011 forbid any monetary figure derived from
this reconciliation, and SPEC-007 C-62 binds `intent.md` §12's three rules to every figure
the system states.

**Problem:**
The measurement is treated as pre-existing and therefore out of scope. But one of its
three named components — «مخزون مفسّر», stock explained — can only be valued in money the
specifications now prohibit. So either the success number cannot be computed as the intent
describes it, or it will be computed in violation of D-1 on a surface no specification
governs.

**Why this matters:**
This is the number the pilot is decided on. Leaving it unregistered means no specification
constrains it to D-1, D-2 or D-3, and SPEC-007's provenance obligations do not visibly
reach it. If it is genuinely an existing capability, that is a compatibility constraint
that should be written down and checked, not an absence.

**Required resolution:**
Register the success measurement as an intent (or as an explicit deferral with its reason,
matching how INT-004…INT-008 are handled), and state what its money component may consist
of given D-1 — specifically whether the "stock explained" contribution is expressible in
money at all. Its answer is coupled to GATE-001.

---

### GATE-008 — Orphan requirements: several MUST statements carry no acceptance coverage

**Type:** ACCEPTANCE-GAP
**Severity:** MINOR
**Confidence:** HIGH

**Spec evidence:**

| Requirement | What it obliges | Acceptance |
|---|---|---|
| SPEC-003 INV-024 / C-23 (D-5) | "The store's own price MUST NOT serve as its own benchmark" | none; also absent from SPEC-003's §19 matrix |
| SPEC-003 FR-048 | An unhurried-review breach must state the policy it departs from | none (AC-047 covers FR-049 only) |
| SPEC-003 INV-022 | A difference explained by format alone is not a fault | none |
| SPEC-004 FR-070, FR-071 | Three distinguishable idle outcomes; system must not say which is right | none (AC-071 covers ranking only) |
| SPEC-006 FR-103, FR-107, FR-109, FR-110 | Admission; showing the producing capability; a physically doable action; on-surface evidence | none |

**Problem:** D-5 is described in `intent.md` §3 as «القاعدة الحاكمة» — the governing rule of
the whole comparison — and it is the one settled decision with no verification path at all.
SPEC-006 FR-110 (on-surface evidence) is the mechanical basis of NFR-051 and of the
project's trust argument, and is likewise unverified.

**Required resolution:** Add acceptance coverage for these, or state explicitly which
existing criterion is intended to cover each. One criterion legitimately covering several
tightly related requirements is fine; silence is not.

---

### GATE-009 — SPEC-005 has no rule for the intent's five deferred cost questions

**Type:** COVERAGE-GAP
**Severity:** MINOR
**Confidence:** HIGH

**Intent evidence:** `intent.md` §5 — «بلا تكلفة وميتة وعليها مخزون | **5** | ⏸️ **سؤال مؤجَّل**».

**Spec evidence:** SPEC-005 FR-082 suppresses questions about *withdrawn* products. The
five products in question are dead **with** stock — idle, not withdrawn (SPEC-004 FR-064,
INV-030) — so FR-082 does not reach them. No requirement defers them, and the state model
(§10) has no system-initiated deferral, only owner deferral.

**Why this matters:** Minor in volume, but it is the one case in the intent's own
1,270 → 12 arithmetic that the specification's suppression rule does not reproduce.

**Required resolution:** State whether a question about an idle product is suppressed,
deferred, or simply outranked by FR-085.

---

### GATE-010 — SPEC-GAPS Part 3 contradicts the specifications it summarises

**Type:** CONTRADICTION (spec vs. spec)
**Severity:** MINOR
**Confidence:** HIGH

**Spec evidence:**
- SPEC-GAPS Part 3, ASM-012 — "One cost price per product is adequate for **valuation** | SPEC-002 | Valuations drift with cost changes", against SPEC-002 §16 ASM-012 — "Cost price is **not** used by this specification, since no valuation is produced". Same identifier, opposite content.
- SPEC-GAPS Part 3, ASM-010 risk column — "The **two-tier split** has no basis", where the tiers no longer exist.
- SPEC-000 §2 — SPEC-003 "Draft — **blocked**, see GAP-001", where GAP-001 is resolved.

**Required resolution:** Re-derive Part 3 from the specifications rather than maintaining
it in parallel, and refresh the SPEC-000 §2 index.

---

### GATE-011 — Two thresholds required by NFRs have no value and no open question

**Type:** UNTESTABLE-REQUIREMENT
**Severity:** MINOR
**Confidence:** MEDIUM

**Spec evidence:** SPEC-007 NFR-060 — "Reproduction MUST complete **quickly enough to be
performed during a conversation** without the participants waiting on it." No bound, no
open question. SPEC-003 NFR-022's freshness bound is undefined but *is* tracked
(OQ-306) — the contrast shows the omission is inadvertent.

**Note:** SPEC-006 NFR-050's "about ten minutes" is *not* included here: it is tracked as
ASM-053 and GAP-007 with measurement named as the only closure, which is the honest
treatment.

**Required resolution:** Give NFR-060 a bound or an open question.

---

### GATE-012 — Minor design leakage in compatibility constraints

**Type:** DESIGN-LEAKAGE
**Severity:** INFO
**Confidence:** HIGH

**Spec evidence:** SPEC-006 C-53 — "no **untranslated key** reaching the screen … no
horizontal overflow on a **phone**"; SPEC-003 C-20 — "an existing **acceptance check fails
the build**"; SPEC-007 C-61 — inputs "not carried in the **repository** and regenerated
locally".

**Assessment:** All three are stated as existing external constraints or protected
behaviour, which the gate explicitly permits. "Untranslated key" is an implementation
term where "untranslated string" would carry the same obligation without naming the
mechanism. Not a gate failure; recorded for precision only.

---

## 5. Unjustified Specification Requirements

Every material MUST in the specification layer was checked against an intent. The
overwhelming majority are DIRECT or NECESSARY-DERIVATION; only the rows below needed a
judgement.

| Requirement | Classification | Intent justification |
|---|---|---|
| SPEC-001 FR-004, FR-006 (ceiling derived from own data; no default substituted) | DIRECT | `intent.md` §2 — «العتبة من بياناته، لا من افتراض» + §12 rule 3 |
| SPEC-001 NFR-003 (surfaced ≤ 10 % of price-paired products) | NECESSARY-DERIVATION | Operationalises `intent.md` §2's "387 not 1,147" and INV-003; the specific 10 % is a stated, checkable choice rather than a hidden one |
| SPEC-002 FR-024 (order by gap ratio) | DIRECT | `intent.md` §2ب — «الترتيب بحجم الفجوة نسبةً إلى الوارد» |
| SPEC-002 FR-026 (refuse a figure even as an upper bound or illustration) | NECESSARY-DERIVATION | `intent.md` §2ب's «كاملةً لا نصفها» — a bound would be the half-measure the intent names |
| SPEC-003 FR-043a–d (cost floor) | DIRECT | `intent.md` §3ج — the boxed rule and its 43-of-144 evidence |
| SPEC-003 C-24 (the cost floor binds every present and future capability) | NECESSARY-DERIVATION | `intent.md` §3ج states the rule as one «لا تُكسر»; generalising it is faithful, not expansive |
| SPEC-003 FR-044b (format allowance measured, never assumed) | DIRECT | `intent.md` §3ب — «بدل تصنيف مقيس من الـ426 صنفاً … لا رقم مخترع» |
| SPEC-004 FR-060a, FR-063a–c (withdrawal re-evaluated; provisional while short; reversed on a full cycle) | NECESSARY-DERIVATION | `intent.md` §4's seasonality reasoning + §10's requested two-year reports. Sound — but see GATE-004: the same passage's *expansion* clause was not carried |
| SPEC-004 FR-069 / AC-071 (idle set valued and ranked in money) | **ASSUMPTION** | Directly supported by `intent.md` §4 («مرتّبة بالمال», ₪919,170) and directly forbidden by §12 rule 1. The specification chose the money side without recording that it had chosen — **GATE-001** |
| SPEC-005 FR-086 (no queue, total or progress indicator) | NECESSARY-DERIVATION | `intent.md` §5 — «الرابع يحوّلها استمارة، والاستمارة تُهجر». A backlog counter re-creates the form; a defensible reading |
| SPEC-006 FR-101 (no count of unshown entries) | NECESSARY-DERIVATION | Same reasoning applied to `intent.md`'s ten-item bound; the rationale is stated inline, which is the right treatment |
| SPEC-006 FR-106 / FR-106a (unvalued entries get a stated allocation, not a rank) | NECESSARY-DERIVATION | Invented mechanism, but forced: `intent.md` places INT-002/002B in V1 and money-free, and INT-NS ranks by money. The specification surfaced this rather than hiding it (GAP-002/GAP-006), which is correct behaviour — though GATE-001 shows the closure was premature |
| SPEC-006 FR-108 / INV-056 (one product occupies one place) | ASSUMPTION | Not stated in any intent. Reasonable and low-risk, but it is a product decision about the surface taken in the specification layer |
| SPEC-006 FR-112 (outcomes: acted / declined / deferred) | ASSUMPTION | The intent asks the owner to «التصرّف بما فيها» but never asks him to record an outcome. ASM-054 admits the assumption, and OQ-603/604/605 surround it — adequately surfaced |
| SPEC-007 FR-131 (documents must direct the reader to reproduction) | DIRECT | `intent.md` §12's boxed warning |

**No INVENTED requirement was found.** Nothing in the specification layer adds product
capability that no intent supports. The scope-expansion audit returned clean.

---

## 6. Intent Coverage Gaps

1. **`intent.md` §9.2 — no multi-store, no user accounts, no other POS integrations.** Absent from every specification (GATE-006). The scope ceiling most likely to be exceeded by a system designer acting in good faith.
2. **`intent.md` §9.1 — fixed sensors and cameras, "killed, not deferred".** Absent (GATE-006). INT-006's deferral in SPEC-000 §4 does not carry it.
3. **`intent.md` §11.1 — automatic measurement of recovered money over 30 days.** Unregistered as an intent and unspecified; its «مخزون مفسّر» component collides with D-1 (GATE-007).
4. **`intent.md` §3ب — the 100 % separating threshold.** The one settled constant the specification did not carry across, though FR-045b requires it be stated (GATE-003).
5. **`intent.md` §4 — the expansion of automatic withdrawal once two-year evidence arrives.** Dropped, and its absence hardened into INV-030 (GATE-004).
6. **`intent.md` §5 — the five deferred cost questions.** No suppression or deferral rule reaches them (GATE-009).
7. **`intent.md` §13 / §10 — the ingestion cadence (daily or weekly, decided 12/9).** Not tracked as an open question anywhere in SPEC-GAPS. *Assessed as non-blocking:* every specification triggers on "ingestion" rather than on a schedule, which is the correct abstraction and makes the specs cadence-agnostic. Recorded for completeness only.

---

## 7. Open Product Decisions

The specification layer's own register — 32 questions, none at P0 — is well-formed, and
its P1/P2 assignments were checked individually and found defensible. The table below
lists only what this audit changes or adds.

| Question | Priority | Why it matters |
|---|---|---|
| **NEW** — Does an idle product's stock carry a money figure, given D-1? | **P0** | GATE-001. Decides SPEC-004 FR-069/AC-071, whether V1 has one or two monetary kinds, and therefore whether the daily surface can be ordered at all |
| **OQ-601 — re-open** (spec records it as moot) | **P0** | Its closure rests on FR-105's premise, which SPEC-004 falsifies. Moot only if the answer above removes money from the idle set |
| **OQ-602** — how many of the ten places go to unvalued entries | **P1** (as recorded) | Confirmed correctly downgraded: FR-106 settles the mechanism, so design can proceed on the allocation with the number configurable |
| **NEW** — What does "actionable today" mean, and which capability states it? | **P1** | GATE-005. Admission to the ten-slot surface is currently undefined |
| **NEW** — Does automatic withdrawal expand to stock-carrying entries once a full annual cycle is available? | **P1** | GATE-004. The intent says yes; INV-030 says never |
| **NEW** — Is `intent.md` §9.2's single-store / single-user / single-POS ceiling binding on system design? | **P1** | GATE-006. Left unstated, it will be exceeded by default |
| **NEW** — What may the 30-day recovered-₪ measurement contain, given D-1? | **P1** | GATE-007. The pilot's decision criterion |
| **OQ-201** — period alignment of stock, receipts and sales | **P1** (as recorded) | Confirmed correctly downgraded from P0: with FR-023 removing the magnitude, misalignment now affects ordering and false flags rather than a published amount. GAP-004 states this accurately |
| **OQ-306** — competitor observation freshness bound | **P2** (as recorded) | Confirmed. NFR-022 is designable without the constant |
| **NEW** — What bound applies to SPEC-007 NFR-060's reproduction latency? | **P2** | GATE-011 |

---

## 8. Design Leakage

**No material design leakage found.**

The specification layer is notably clean on this axis: no framework, library, algorithm,
module, schema, storage engine, deployment topology or file path is prescribed. Where a
technical fact appears it is framed as an existing external constraint the design must
accommodate — SPEC-003 C-20…C-22, SPEC-004 C-32, SPEC-006 C-50…C-53, SPEC-007 C-60…C-61 —
which the gate permits.

Three items are recorded as INFO only, under GATE-012: "untranslated key" (SPEC-006 C-53),
"fails the build" (SPEC-003 C-20), and "not carried in the repository" (SPEC-007 C-61).
Each is a genuine immutable constraint; only the vocabulary is more implementation-shaped
than it needs to be.

Notably, SPEC-005 correctly abstracted away `intent.md` §5's reference to a concrete code
path, keeping the three-question bound and its rationale while dropping the location. That
is the behaviour the layer separation asks for.

---

## 9. Gate Checklist

| | Check | Run 1 | Run 2 |
|---|---|---|---|
| | Intent coverage | FAIL | **PASS** — D-12, D-13 restored; INT-MEAS registered with OQ-801 |
| | Semantic fidelity | FAIL | **PASS** — INV-030 scoped to the evidence window; OQ-409 registered |
| | Scope integrity | PASS | **PASS** — still no INVENTED requirement |
| | Requirement justification | PASS | **PASS** — FR-069's ASSUMPTION resolved into D-11 |
| | Contradiction check | FAIL | **PASS** — GATE-001 and GATE-002 resolved; CON-005 recorded |
| | Failure behavior | PASS | **PASS** |
| | Edge-case coverage | PASS | **PASS** |
| | Testability | FAIL | **PASS** — AC-020 replaced; NFR-060 bounded at two minutes |
| | Acceptance coverage | FAIL | **PASS** — AC-047a/b, AC-071a/b, AC-110a/b/c close the orphans |
| | Assumptions | PASS | **PASS** — ASM-030 re-weighted against measurement; ASM-035 added |
| | Open questions | FAIL | **PASS** — no P0 remains; OQ-409 and OQ-801 added at P1 |
| | Non-goal integrity | PASS | **PASS** |
| | Design-layer separation | PASS | **PASS** |
| | Traceability | FAIL | **PASS** — matrices extended; SPEC-000 index refreshed |

---

## 10. Required Actions Before System Design (run 1 — now closed)

> Every item below was applied in run 2 except GATE-012. See §11.

**Minimum set to clear the gate.** Blockers first; the two MAJOR items listed are included
because leaving them would let system design proceed on a false or over-strong constraint.

### Blocking

1. **Settle whether idle stock carries money (GATE-001).** This is an intent-layer
   decision, not a specification one: `intent.md` §4 and `intent.md` §12 rule 1 disagree,
   and the specification must not choose between them silently. Once settled: correct
   SPEC-004 FR-069 / §9 / AC-071 to match, re-derive SPEC-006 FR-105 instead of asserting
   it, re-open GAP-002 and OQ-601 until the premise holds, and record the intent-level
   conflict in SPEC-GAPS Part 4.

2. **Reconcile SPEC-002 with its own FR-023 (GATE-002).** Resolve every surviving
   reference to tiers, to monetary totals, to a "money signal" and to valuation — §4
   precondition, §9 outputs, INV-012, NFR-011, NFR-012, AC-020, AC-028, §11 — and supply
   acceptance coverage for FR-020…FR-022 that survives the removal. Correct INT-002's
   label in SPEC-000 §1 and SPEC-002 §2, and the duplicate ASM-012.

### Strongly recommended before design begins

3. **Remove SPEC-003's superseded derived-threshold machinery and state the missing
   constant (GATE-003).** The §5 domain term and the §11 failure row instruct a designer
   to build what FR-045 forbids; AC-043 verifies two of FR-046's four values; the intent's
   100 % separating threshold is not carried across.

4. **Re-scope D-6 and INV-030 to the evidence window the intent attaches to them
   (GATE-004),** and state whether the intent's expansion clause is accepted, deferred or
   rejected.

### Should be cleared, and are cheap

5. Define "actionable today" or oblige each producing specification to supply it (GATE-005).
6. Carry `intent.md` §9.1 and §9.2 into the specification layer (GATE-006).
7. Register the 30-day success measurement, and state what its money component may contain given D-1 (GATE-007).
8. Close the orphan requirements in GATE-008, D-5/INV-024 first.
9. Fix SPEC-GAPS Part 3 and the SPEC-000 §2 index (GATE-010); handle the five deferred cost questions (GATE-009); bound NFR-060 (GATE-011).

---

---

## 11. Resolution Log — Run 2

| Finding | Severity | Status | Correction |
|---|---|---|---|
| GATE-001 | BLOCKER | **RESOLVED** | `intent.md` §4ب drops ₪919,170 and orders idle stock by unit cost. D-11 added. SPEC-004 FR-069 rewritten, FR-069a/FR-069b added, AC-071/071a/071b. SPEC-006 FR-105 now derives the single-kind premise. OQ-601 re-verified. CON-005 recorded |
| GATE-002 | BLOCKER | **RESOLVED** | All tier/total/"money signal" residue removed from SPEC-002 §2, §4, §9, §11, INV-012, NFR-011, NFR-012. AC-020 replaced with a satisfiable criterion covering FR-020…FR-022 and FR-024. AC-028 corrected. ASM-012 reconciled |
| GATE-003 | MAJOR | **RESOLVED** | Derived-threshold domain term and failure row removed; attention threshold stated at +100% in FR-045b and Domain Terms; AC-043 covers all four FR-046 values; SPEC-000 index refreshed; OQ-302 closed against FR-044 |
| GATE-004 | MAJOR | **RESOLVED** | INV-030 scoped to evidence shorter than a full annual cycle, with the intent's expansion clause quoted; state table updated; OQ-409 registered at P1 |
| GATE-005 | MAJOR | **RESOLVED** | FR-103 now defines "actionable today" as four observable conditions; AC-110a verifies it |
| GATE-006 | MAJOR | **RESOLVED** | D-12 (single store, single user, single POS import) and D-13 (fixed sensors and cameras permanently excluded) added; INT-006's deferral note states D-13 is not reopened by it |
| GATE-007 | MAJOR | **RESOLVED** | INT-MEAS registered in SPEC-000 §1; §4 records that SPEC-007 governs its figures and that its "stock explained" component cannot be money under D-1; OQ-801 at P1 |
| GATE-008 | MINOR | **RESOLVED** | AC-047 extended (FR-048), AC-047a (INV-022), AC-047b (INV-024/D-5), AC-071b (FR-070/071), AC-110a/b/c (FR-103/107/109/110); traceability matrices extended |
| GATE-009 | MINOR | **RESOLVED** | SPEC-005 FR-082a defers questions about idle products; AC-081 extended; `intent.md` §5 corrected |
| GATE-010 | MINOR | **RESOLVED** | ASM-010 and ASM-012 corrected in SPEC-GAPS Part 3; SPEC-000 §2 index refreshed |
| GATE-011 | MINOR | **RESOLVED** | NFR-060 bounded at two minutes on the pilot dataset |
| GATE-012 | INFO | Open | Vocabulary only; not a gate condition |
| **GATE-013** | **MAJOR** | **Open — by design** | New; see below |

---

### GATE-013 — "Sold nothing" is, for every classified product in the pilot, "has no sales row"

**Type:** HIDDEN-ASSUMPTION (severity of an acknowledged assumption materially understated)
**Severity:** MAJOR · **Confidence:** HIGH — measured directly from the pilot artefacts

**Found by:** verification of the council's proposed ordering keys against
`data/internal/silver_pos/`. Every key the advisors proposed — months without a sale, age
of last sale, cost of unsold receipts — proved null for 100% of the idle set, which led to
the cause.

**Evidence:**

| Class | Count | Present in the sales reports | Absent entirely |
|---|---:|---:|---:|
| Living (sold > 0) | 1,614 | 1,614 | 0 |
| Withdrawable (0 sales, 0 stock) | 3,932 | **0** | 3,932 |
| Idle (0 sales, stock > 0) | 1,674 | **0** | 1,674 |
| Negative stock, 0 sales | 243 | 1 | 242 |

Exactly one product in the catalogue appears in the sales reports with an observed zero.
`data/internal/receiving/` does not exist, so no receipts-based key is available either.

**Problem:** SPEC-004 ASM-030 calls this "the strongest assumption in this specification",
which understates it — it carries 5,848 of 7,463 classifications, including all 3,932
automatic withdrawals. It is not a breach of INV-036, which governs the evidence set being
absent as a whole rather than a product being absent from it; ASM-030 does record the
right assumption. What was missing is its measured weight.

**Why this matters:** if a monthly POS sales report does not in fact list everything that
sold, the catalogue-cleanup capability withdraws products that sell — and it is V1's
headline. Nothing in the design changes if the assumption holds, which is why this is not
a blocker.

**Required resolution:** establish it with the owner before 3,932 products are withdrawn
in front of him. The cheapest test is to name twenty absent products and ask whether any
sold. Recorded as GAP-009 and as a release condition.

---

## Second-pass note on findings not raised

Each of the following was investigated and deliberately **not** reported, to keep the
gate honest about what actually blocks design.

- **INT-004…INT-008 left unspecified.** SPEC-000 §4 gives a per-intent reason, and each
  reason is a genuine unresolved product decision rather than a scheduling excuse. This is
  correct behaviour, not a coverage gap.
- **GAP-005 (coverage figures not reproducible) left open.** Correctly scoped: it blocks
  stating those figures to the owner, not designing the system. The specification says so
  in exactly those terms.
- **GAP-007 (the ten-minute claim) left open.** No decision can close a claim that only
  measurement settles, and the bound is a constant that can change without restructuring.
- **OQ-602 at P1 rather than P0.** FR-106 settles the mechanism — allocation, not ranking —
  which is the part design needs; the number is genuinely deferrable.
- **SPEC-001 having no stated ceiling constant,** unlike SPEC-003's +60 %. Consistent:
  FR-004 requires the ceiling to be *derived*, so a constant would contradict it. The
  intent's 18 % is an observation about the pilot data, not a policy.
- **SPEC-006 FR-111 / INV-052 (estimate labelling) possibly vestigial** now that SPEC-002
  produces no estimated figure. Harmless and forward-binding; not a defect.
