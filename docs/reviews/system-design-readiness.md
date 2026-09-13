# System Design → Implementation Readiness Report

**Gate:** SYSTEM DESIGN → IMPLEMENTATION
**Artifacts audited:** the approved intent layer, then at `intent.md` — now [PRD](../product/PRD.md) + [feature intents](../features/) · the specification layer v1.1, then at `specs.md` — now [intent register](../product/intent-register.md), seven [feature specs](../features/), [gaps register](../features/gaps-and-open-questions.md) · [`intent-spec-conformance.md`](intent-spec-conformance.md) (CONDITIONAL PASS, run 2) · the System Design v1.0, then at `design.md` — now [`system-design.md`](../architecture/system-design.md) + [ADRs](../architecture/decisions/) · the repository at `HEAD` of `implementation-plan`
**Date:** 2026-09-08
**Auditor stance:** independent.

> **Run 2 — after correction (2026-09-08). Verdict: CONDITIONAL PASS — IMPLEMENTATION READY WITH NON-BLOCKING ISSUES.**
> Run 1 returned FAIL on one blocker, ARCH-GATE-001. The team put it to a five-advisor
> council with anonymous peer review; the council was unanimous, and the decision was
> applied to `design.md`, now at version 1.1. The blocker is closed and one of the three
> MAJOR findings (ARCH-GATE-003) remains open as a product decision, not an architectural
> one. The original findings are kept below unaltered, each carrying its resolution in
> §19. `intent.md` and `specs.md` were not modified — no upstream artifact needed to
> change, which was the test of whether the correction was real.

> **Path note — the 2026-09-08 documentation migration.** The artifacts this report audited
> were monolithic files at the repository root. They were split and moved without any change
> of content. Citations in the body below use the historical names; they resolve as follows:
>
> | Cited as | Now at |
> |---|---|
> | `intent.md` (project-level §1, §8–§13) | [`docs/product/PRD.md`](../product/PRD.md) |
> | `intent.md` (per-intent sections §2–§7) | [`docs/features/F#-*/intent.md`](../features/) |
> | `specs.md` SPEC-001 … SPEC-007 | [`docs/features/F#-*/specs/F#-S1-*.md`](../features/) |
> | `specs.md` SPEC-000 | [`docs/product/intent-register.md`](../product/intent-register.md) |
> | `specs.md` SPEC-GAPS | [`docs/features/gaps-and-open-questions.md`](../features/gaps-and-open-questions.md) |
> | `design.md` | [`docs/architecture/system-design.md`](../architecture/system-design.md) |
> | `design.md` §19 ADR-001 … ADR-014 | [`docs/architecture/decisions/`](../architecture/decisions/) |
>
> **The verdicts, findings and severities below are unchanged.** Requirement identifiers
> (`FR-…`, `INV-…`, `AC-…`, `OQ-…`, `GAP-…`, `D-…`) were not renumbered by the migration.

---

---

## 1. Verdict

## ~~FAIL~~ → CONDITIONAL PASS — IMPLEMENTATION READY WITH NON-BLOCKING ISSUES *(run 2)*

The contract now says one thing. `design.md` v1.1 defines the term that was doing seven
jobs at once — **a capability is the smallest unit that can independently become
unavailable** (ADR-014) — and every consequence falls out of it rather than being
negotiated: `hygiene` is a registered capability with its own `requires`, computed
`status`, `value_policy: none`, badge, page and precedence slot; `catalogue_lifecycle` and
`owner_questions` move inside `capabilities{}` and gain the `status` they lacked;
`capabilities{}` is exactly the registry id set, and the publisher asserts it. SPEC-002
§11 — detection unavailable, hygiene unaffected — is now expressible, and it is *derived*
from two `requires` lists rather than hand-written, so it cannot be got wrong by
declaration.

The council also caught something run 1 did not: `entry_id` hashed the capability id,
which made a presentation label load-bearing on the owner's durable decisions. Any later
re-carving would have orphaned them silently. ADR-009 now hashes a permanent
`signal_family` instead, which both removes that failure mode and makes the taxonomy
decision reversible — the property that turns this from an irreversible Phase 0 gamble
into an ordinary design choice.

Three things the peer-review round added and the design now carries: the unvalued
precedence order is stated in full and hygiene ranks last with a reason (1,155 records of
finite cleanup would otherwise hold the reserved places for weeks); cross-capability
duplication is named as step (4)'s job rather than left implicit; and the rule-12
independence probe — run with the sales reports withheld, assert `reconciliation`
unavailable *and* `hygiene` still emitting — is now in §14 and §18. That last one matters:
per CLAUDE.md rule 12, four signals in this repository have shipped unit-tested and moved
nothing, because every test supplied the input directly and never crossed the boundary
where it was lost. Without the probe, this fix would have been the fifth.

**What remains, and why it does not block:** ARCH-GATE-002 (the money basis for a cost
question) and ARCH-GATE-004 (the "structurally uncomparable" predicate) are two rule
definitions, each contained in one engine module, each publishable as a provisional
parameter in `configs/policy.yaml` — they must be settled before Phase 1b and Phase 1c
respectively, not before Phase 0. ARCH-GATE-003 (INT-MEAS) is a product decision for the
specification layer, and the honest handling is to say on 12/9 that the 30-day number has
no V1 delivery yet. The eight MINOR findings are precision, not architecture.

### Run 1 verdict *(superseded)*

## FAIL — NOT READY FOR IMPLEMENTATION

One blocker, and it sat inside the first thing Phase 0 builds.

This is a narrow failure of an otherwise exceptionally strong design. Every one of the 90
acceptance criteria in `specs.md` appears in the design's traceability matrix, and the
design invents none. Every FR, INV, NFR and D-decision is answered or covered by an
explicit range. Every surviving component carries a justification, and the removals are
argued from specs rather than from taste. The current-state trace was re-verified against
the repository during this audit and was found accurate on every claim checked — 324
pytest tests collect, `npm run figures` is still `print_figures.py`, no workflow runs on
push or pull request, `scripts/import_owner_answers.py` has never existed, `code/` and
`SmartShelf AI/` are 198 tracked files serving nothing, and Firebase and Basic Auth are
both entirely unconfigured. A design that reports the repository this honestly is rare.

What blocks it is that the artefact contract — `CapabilityOutput` (§11.2) and
`dashboard.json` schema v2 (§11.4) — cannot represent data hygiene, even though the design
elsewhere gives hygiene its own availability, its own badge, its own value policy and its
own allocation slot on the daily surface. Following the contract as written forces a
violation of SPEC-002 §11 and SPEC-006 INV-057; deviating from it requires implementation
to decide whether hygiene is a capability id — a decision that changes the JSON schema,
`registry.py`, `entry_id` (and therefore outcome-id stability under FR-115/C-50), the
navigation, and `compose`'s precedence list. That is Phase 0 item 1, and it is
contradictory in the design as it stands.

Two MAJOR findings sit behind it: SPEC-005 FR-085's ordering key has no defined "money at
stake" for the only question V1 asks, and the existing behaviour the design says it
preserves (C-41) does not transfer; and INT-MEAS — the pilot's own 30-day go/no-go number
— loses the surface `specs.md` SPEC-000 §4 cites as the reason for not specifying it, with
nothing built in its place and no release condition naming it.

The corrections in §18 are small and precisely scoped. None requires re-architecting.

---

## 2. Executive Metrics

| | |
|---|---|
| Intents reviewed | 14 registered (INT-001 … INT-010, INT-NS, INT-PROV, INT-MEAS, INT-002B); 8 in V1 scope |
| Specs reviewed | 8 (SPEC-000 … SPEC-007, SPEC-GAPS) |
| Spec requirements reviewed | 124 FR · 46 INV · 24 NFR · 90 AC · 29 C · 72 SCN · 13 D-decisions |
| Fully design-covered | 118 FR · 44 INV · 23 NFR · 87 AC |
| Partially covered | 4 FR (FR-085, FR-052, FR-106, FR-030-as-status) · 2 INV (INV-003 interaction, INV-057 for hygiene) · 1 NFR (NFR-012, mechanically covered but unnamed) · 3 AC (AC-083, AC-044, AC-107 for hygiene) |
| Missing | 0 |
| Conflicting | 1 — §11.2/§11.4 contract against §13/§14/§21's hygiene requirements |
| Design elements reviewed | 9 architectural drivers · 13 ADRs · 9 engine/publisher components · 8 browser components · 5 ingestion components · 1 owner-state store · 1 artefact · 1 reproduction CLI |
| Justified design elements | 46 of 47 |
| Unjustified design elements | 0 material. 1 flagged by the design itself (`margin_below_cost`, SPEC-GAP-A) and accepted as intent-justified + migration-temporary |
| **Blockers (run 1)** | 1 — **closed in run 2** |
| **Blockers (run 2)** | **0** |
| Major | 3 — 0 closed, 3 open (2 are contained rule definitions, 1 is a product decision) |
| Minor | 8 — 3 closed in run 2 (GATE-005 scope, GATE-010 flow note, GATE-013/014 partly), 5 open |
| Info | 3 |

---

## 3. Intent → Spec → Design Matrix

| Intent | Spec | Design | Verification | Status |
|---|---|---|---|---|
| INT-001 price consistency | SPEC-001 | E `price_consistency`; derived ceiling published in `thresholds`; `Value{per_sale}` | AC-001 … AC-009 | **FULL** |
| INT-002 reconciliation | SPEC-002 (detection half) | E `reconciliation`; `value_policy: none`; `gap_ratio` ordering | AC-020 … AC-024, AC-028, AC-029 | **FULL** |
| INT-002B hygiene | SPEC-002 (hygiene half) | E `reconciliation` (same module); `characterisation: hygiene` | AC-025, AC-107 | **PARTIAL** — no addressable capability status (ARCH-GATE-001) |
| INT-003 competitor position | SPEC-003 | E `competitor_position`; cost floor → balanced reference → policy → attention; `coverage`, `position[]` | AC-040 … AC-054 | **PARTIAL** — FR-052 predicate undefined (ARCH-GATE-004) |
| INT-009 catalogue cleanup | SPEC-004 | E `catalogue_lifecycle`, ADR-004 (recomputed, no stored state), `withdrawn[]` + handover CSV | AC-060 … AC-071b | **FULL** |
| INT-010 knowledge capture | SPEC-005 | E `owner_questions`; O owner-state store; ADR-003 round trip | AC-080 … AC-090 | **PARTIAL** — FR-085 ordering undefined (ARCH-GATE-002) |
| INT-NS the morning screen | SPEC-006 | C `compose` (ADR-006); bound 10; `unvalued_places` | AC-100 … AC-112 | **PARTIAL** — allocation not stated to the owner (ARCH-GATE-008) |
| INT-PROV provenance | SPEC-007 | R `figures.py` = engine `--print` (ADR-002); figure registry; `vintages` | AC-120 … AC-129 | **FULL** |
| INT-MEAS 30-day recovered ₪ | *unspecified* (SPEC-000 §4) | Outcome snapshots captured (§10.3); **telemetry surface removed** (§5.4); no replacement | none | **CONFLICTING** — ARCH-GATE-003 |
| INT-004/005/007/008 (V2/V3) | *deferred* | Off the V1 build; receiving capture retained so the 30-day counter starts | — | FULL (deferral honoured) |
| INT-006 (V4) | *deferred* | Planogram removed to `v1-attic`; D-13 preserved (nothing sensor-shaped in the design) | — | FULL |

---

## 4. Spec → Design Coverage

Grouped by requirement family; every partial or conflicting row is a finding in §16.
Full rows are those where a mechanism, a contract location and a named AC all exist.

| Spec | Requirement group | Design answer | Verification | Status |
|---|---|---|---|---|
| SPEC-001 | FR-001 … FR-003 four-state classification | `price_consistency`, only inverted + above published | AC-001, AC-002 | FULL |
| SPEC-001 | FR-004 … FR-006 derived ceiling, undeterminable case | Ceiling derivation with published `{pct, method, bands}`; `null` → above suppressed, inverted kept | AC-004, AC-005 | FULL |
| SPEC-001 | FR-007 … FR-009 characterisation + evidence | `characterisation` enum; `evidence{shelf, delivery, difference, markup_pct}` | AC-002, AC-003, AC-110c | FULL |
| SPEC-001 | FR-010, FR-011 exclusions | D-4 constants in `policy.yaml`; `counts.excluded_artefact`; absent price ≠ zero | AC-006 | FULL |
| SPEC-001 | FR-012, FR-013 money | `Value{kind: per_sale}`; no totals rendered anywhere | AC-103 | FULL |
| SPEC-001 | INV-003 / NFR-003 density guard | Publish-time guard → `unavailable: ceiling_degenerate` | AC-008 | **PARTIAL** — would also suppress inverted (ARCH-GATE-005) |
| SPEC-001 | INV-002, INV-004, INV-005, C-1 … C-4 | Vintage in `figures`; no velocity field in `Entry`; `entry_id` excludes thresholds | AC-004, AC-007, AC-009 | FULL |
| SPEC-002 | FR-020 … FR-022, FR-024, FR-027 detection | Arithmetic kept verbatim; `gap_ratio` ordering; evidence dict | AC-020, AC-024 | FULL |
| SPEC-002 | FR-023, FR-025, FR-026, FR-029 no money | `value_policy: none` + publisher assertion + no browser arithmetic | AC-021, AC-022, AC-023, AC-025 | FULL |
| SPEC-002 | FR-028, FR-030 hygiene surfaced and distinguishable | `characterisation: hygiene`, "distinct capability badge" | AC-025 | **CONFLICTING** — no capability id, no status (ARCH-GATE-001) |
| SPEC-002 | §11 receipts/sales absent → detection unavailable, hygiene continues | §13 states the behaviour; contract cannot express it | AC-107 | **CONFLICTING** — ARCH-GATE-001 |
| SPEC-002 | FR-031 … FR-033, INV-012, INV-015, NFR-010/011 | No standing kind in V1; raw stock read; `action: count_product`; no cause strings | AC-026, AC-027, AC-028 | FULL |
| SPEC-002 | NFR-012 only aggregate is a count | Covered by `value_policy: none`; not named in §21 | AC-022 | FULL (unnamed — ARCH-GATE-013) |
| SPEC-003 | FR-040 … FR-043 source discipline | `inputs.py` drops affinity-0 before any capability; `evidence.reference` records the driver | AC-040 … AC-042 | FULL |
| SPEC-003 | FR-043a … FR-043d cost floor first | Evaluated before policy; `characterisation: purchase_cost`; missing cost → not evaluated | AC-049 … AC-051 | FULL |
| SPEC-003 | FR-044 … FR-044c balanced reference | Reference builder `{midpoint \| supermarket_plus_allowance \| none}`; allowance measured | AC-052, AC-053, AC-045 | FULL |
| SPEC-003 | FR-045 … FR-046 declared policy + attention | `policy.yaml` 60/100/10; all four values in `thresholds.competitor_position` | AC-043, AC-054 | FULL |
| SPEC-003 | FR-047 … FR-049 characterisation | Two breach characterisations; policy stated; no "error" copy | AC-047, AC-047a | FULL |
| SPEC-003 | FR-050, FR-051 coverage honesty | `coverage{catalogue, comparable_population, matched, …}`; per-product "no comparison" | AC-044, AC-045 | FULL |
| SPEC-003 | FR-052 structurally uncomparable | Named as a published count; **no rule given** | AC-044 | **PARTIAL** — ARCH-GATE-004 |
| SPEC-003 | FR-053, INV-020 … INV-026, NFR-020 … NFR-022 | `position[]`; `role: client` exclusion; freshness bound 14d (provisional) | AC-046, AC-047b, AC-048 | FULL |
| SPEC-004 | FR-060 … FR-062, INV-034 | Pure function per run; `EvidenceWindow.full_annual_cycle`; partition asserted | AC-065, AC-070 | FULL |
| SPEC-004 | FR-063 … FR-063c, INV-030 … INV-032, INV-031a | ADR-004; `provisional` per entry; `withdraw_with_stock=false` asserted; revival by absence | AC-060, AC-062, AC-063a-c | FULL |
| SPEC-004 | FR-065 … FR-068, FR-075, INV-033 | `withdrawn[]` with evidence; manual revival keyed to `window_id`; handover CSV; no external write path | AC-061, AC-063, AC-064 | FULL |
| SPEC-004 | FR-069 … FR-071, D-11 | Ranked by `unit_cost`; no value; stock quantity never shown as justification; three outcomes as `reason` | AC-071, AC-071a, AC-071b | FULL |
| SPEC-004 | FR-072, FR-073, INV-035 | Question entry; `implausible_ratio` provisional (>10 % of 7-month revenue) | AC-069 | FULL |
| SPEC-004 | FR-074, C-31, INV-036 | `withdrawn` in `EngineInputs`; `None` → no exclusion | AC-066, AC-068 | FULL (population of the SPEC-001 ceiling unstated — ARCH-GATE-006) |
| SPEC-004 | FR-061, FR-076, C-32, C-33, NFR-030 … NFR-033 | Window in every count; raw stock; answers survive; idle page paginates | AC-067, AC-070, AC-090 | FULL |
| SPEC-005 | FR-080 … FR-083, INV-041, INV-044 | Suppression over `withdrawn` and `idle` before ranking; `suppressed` counts published | AC-081, AC-082, AC-088 | FULL |
| SPEC-005 | FR-084, INV-040, C-40 | `questions.limit = 3`; panel slices | AC-080 | FULL |
| SPEC-005 | FR-085, C-41, NFR-041 ordering | "expected value = money at stake × yield" — **neither operand defined for a cost question** | AC-083 | **PARTIAL** — ARCH-GATE-002 |
| SPEC-005 | FR-086 … FR-093, INV-042, INV-043, NFR-040, NFR-042 | ADR-003 round trip; `cost_source: owner`; deferral without value; no queue/total | AC-084 … AC-090 | FULL |
| SPEC-006 | FR-100 … FR-102, INV-050 | `compose` bound; remainder text removed; capability pages hold full sets | AC-100, AC-101, AC-110 | FULL |
| SPEC-006 | FR-103 admission | Engine stamps (1)(2)(4); browser applies (3) | AC-110a | FULL |
| SPEC-006 | FR-104 … FR-105, FR-116, INV-051 | `value.amount` desc; `value_kinds_present` derived and asserted; no totals | AC-102, AC-103 | FULL |
| SPEC-006 | FR-106, FR-106a allocation | `unvalued_places` (3 of 10) in `meta.thresholds`; **no component assigned to state it** | AC-100 | **PARTIAL** — ARCH-GATE-008 |
| SPEC-006 | FR-107 … FR-111, INV-052, INV-055 | Badge, `action` enum, `evidence`, `Value.certainty`; no velocity field exists | AC-104, AC-110b, AC-110c, AC-111 | FULL |
| SPEC-006 | FR-112 … FR-115, INV-053, INV-056, C-50, C-52 | O store; `entry_id` threshold-independent (ADR-009); outcome snapshot captured | AC-105, AC-106, AC-109 | FULL |
| SPEC-006 | FR-117, FR-118, INV-057 | Per-capability `status`; publisher refuses on a missing status; empty ≠ unavailable | AC-107, AC-108 | **PARTIAL** for hygiene — ARCH-GATE-001 |
| SPEC-006 | NFR-050 … NFR-053, C-53, C-54 | Bound; `compose` pure; i18n + e2e invariants reused | AC-112, property test | FULL |
| SPEC-007 | FR-120 … FR-123, INV-060 | `vintages` + `thresholds` blocks; schema requires `inputs` on every figure | AC-120, AC-129 | FULL |
| SPEC-007 | FR-124 … FR-127, INV-062, NFR-060 … NFR-062 | ADR-002; content-addressed reuse; exit 1 naming the missing input | AC-121, AC-122, AC-125 | FULL (owner-state source unstated — ARCH-GATE-009) |
| SPEC-007 | FR-128 … FR-134, INV-061, INV-063, INV-064 | `counts: int \| None`; `certainty` required; schema forbids a value without a kind | AC-123, AC-124, AC-126 | FULL |
| SPEC-007 | INV-065, NFR-063, C-60 … C-62, GAP-005 | One code path; committed inputs + rehydrate + recompute | AC-127, AC-128 | FULL |

---

## 5. Design → Spec Reverse Traceability

| Design element | Justification | Classification | Status |
|---|---|---|---|
| Collectors, snapshots, seals, manifests, health checks, `rehydrate_silver` | SPEC-003 inputs; SPEC-007 C-60/C-61 (the server keeps one day) | EXTERNAL-CONSTRAINT | Justified |
| POS importer (+ `--as-of`) | Every V1 input; SPEC-007 FR-120 vintage | DIRECT-SPEC | Justified |
| Sales importer → `sales_monthly` + `sales_summary` + `EvidenceWindow` | SPEC-004 FR-060b, FR-061; CLAUDE.md rule 13 (`none` ≠ zero) | DIRECT-SPEC | Justified |
| `competitor_product_signals`, `product_matching` (per-store rows preserved) | SPEC-003 FR-044 needs cheapest **per format** — the global dedupe destroys it | NECESSARY-DESIGN | Justified |
| `store_types.py` + `store_types.yaml` (+ `role: client`) | SPEC-003 C-20 … C-22, INV-024, D-5 | DIRECT-SPEC | Justified |
| Owner-state store (Firestore) + `pull.py` + committed mirror | SPEC-005 FR-088/NFR-042; SPEC-006 FR-113/NFR-052; mirror for SPEC-007 NFR-062 on a fresh clone | NECESSARY-DESIGN | Justified |
| `src/engine/` as pure functions of `EngineInputs` | SPEC-007 INV-065, NFR-061; every capability's determinism NFR | NECESSARY-DESIGN | Justified |
| `price_consistency`, `reconciliation`, `competitor_position`, `catalogue_lifecycle`, `owner_questions` | SPEC-001 … SPEC-005 | DIRECT-SPEC | Justified |
| `surface_candidates` (producer half of FR-103) | SPEC-006 FR-103 conditions 1, 2, 4 | DIRECT-SPEC | Justified |
| `provenance` figure registry | SPEC-007 FR-121, FR-122, INV-065 | DIRECT-SPEC | Justified |
| `publish.py` + `schemas/dashboard.schema.json` | ARCH-DRIVER-002/003/007; SPEC-006 FR-117/INV-057; the 2026-09-05 empty-export incident | NECESSARY-DESIGN | **Incomplete** — cannot express hygiene (ARCH-GATE-001) |
| `margin_below_cost` (browse only, not admitted) | No spec; `intent.md` §2ب names margins as V1's money-bearing kind; existing `CHECK_MARGIN` | MIGRATION-TEMPORARY | Flagged by the design as SPEC-GAP-A; acceptable |
| `compose.js` in the browser | SPEC-006 FR-103(3) needs outcomes recorded seconds ago; produces no figure, so INV-065 holds | NECESSARY-DESIGN | Justified |
| `DailyPage`, 5 capability pages, `QuestionPanel`, `DataPage` | SPEC-006 FR-100/102/107/117; SPEC-005 FR-084/FR-086; SPEC-007 FR-120/FR-132 | DIRECT-SPEC | Justified |
| Receiving capture retained | `intent.md` §7/§8 — the 30-day counter starts 12/9; explicitly V2 data | DIRECT-SPEC (intent-level) | Justified, and the design says so plainly |
| i18n module + four guard layers | SPEC-006 C-53 | DIRECT-SPEC | Justified |
| `figures.py` = engine `--print` | SPEC-007 FR-124/FR-125, INV-065 | DIRECT-SPEC | Justified |
| Content-addressed intermediate outputs | SPEC-007 NFR-060 (two minutes) with NFR-062 (no preparation) | NECESSARY-DESIGN | Justified |
| `ci.yml` on push/PR | 851 existing tests that nothing runs; ADR-013 | NECESSARY-DESIGN | Justified |
| `market-context.json` still produced nightly | V2 only; **no V1 consumer** | — | ARCH-GATE-014 (INFO) |
| Vercel Basic Auth, Firestore rules pinned to one store | D-12; the data is one business's cost prices | EXTERNAL-CONSTRAINT | Justified; posture flagged (ARCH-GATE-012) |
| Removed: demo spine, browser engines, planogram, LLM layer, telemetry, browser POS connectors, `code/`, `SmartShelf AI/`, 17 dead scripts, MCP server | No spec, no intent, no execution path; D-12 forbids a runtime server and a second import path | — | Removal justified (except INT-MEAS's surface — ARCH-GATE-003) |

**No material ORPHAN-DESIGN found.** Every element traces to a spec, a necessary
consequence, an external constraint, or a declared temporary.

---

## 6. Invariant Enforcement

Forty-six invariants were checked for a *mechanism*, not an assertion. Forty-four have one.

| Invariant | Design enforcement | Verification | Status |
|---|---|---|---|
| INV-010, INV-011, INV-013, INV-054 (D-1) | Type + Assert: `value_policy: none` in `registry.py`; publisher rejects any `value`; the browser has no money arithmetic once `actionPriority.js` is gone | AC-021, AC-025, AC-071a | **ENFORCED** |
| INV-014, INV-051 (D-2) | Type: `Value.kind`; `compose` never adds; `value_kinds_present` derived and asserted `⊆ {per_sale}` | AC-103 | **ENFORCED** |
| INV-057, INV-061 (D-3) | Type: `status`, `counts: int \| None`, `ceiling: null`; publisher refuses a missing status | AC-107, AC-123 | **ENFORCED for 5 of 6 capabilities; UNENFORCEABLE for hygiene** (ARCH-GATE-001) |
| INV-024 (D-5) | Type: `Store.role = client` dropped in `inputs.py` before any capability sees observations | AC-047b | **ENFORCED** |
| INV-033 (D-7) | No write client exists in the engine; outputs are files in this repo + Firestore | AC-064 | **ENFORCED** |
| INV-040 (D-8) | `questions.limit` published; panel slices | AC-080 | **ENFORCED** |
| INV-050 (D-9) | `compose` truncates; property test over random candidate sets | AC-100 | **ENFORCED** |
| INV-001 | `confirmed_loss` assigned only in the inverted branch | AC-003 | **ENFORCED** |
| INV-002 | Ceiling inputs recorded in `figures` with the POS vintage | AC-004 | **ENFORCED** (population unstated — ARCH-GATE-006) |
| INV-003 | Publish-time guard → `unavailable: ceiling_degenerate` | AC-008 | **ENFORCED, over-broad** (ARCH-GATE-005) |
| INV-004 | Identical never becomes an entry | AC-001 | **ENFORCED** |
| INV-005, INV-055 | Type: no units/day field exists in `Entry`; `evidence` keys enumerated per capability in the schema | AC-007, AC-111 | **ENFORCED** |
| INV-012 | Rule reads `inventory.current_stock` raw; no clamp anywhere in the engine | AC-020 | **ENFORCED** |
| INV-015 | Characterisation + i18n only; AC-027 greps the dictionaries for cause words | AC-027 | **ENFORCED** |
| INV-020 | Affinity-0 dropped in `inputs.py` before the capability | AC-040 | **ENFORCED** |
| INV-021, INV-022 | `store {name, format}` on every displayed observation; within-allowance differences are not breaches | AC-042, AC-047a | **ENFORCED** |
| INV-023 | `coverage` expressed against the full catalogue | AC-044 | **ENFORCED** (one input undefined — ARCH-GATE-004) |
| INV-025 (C-24) | Cost floor evaluated first; the module has no branch emitting a price recommendation at all in V1 | AC-049 | **ENFORCED** (structurally, which is stronger than a check) |
| INV-026 | Reference builder returns a typed kind; single prices cannot escape it | AC-052, AC-053 | **ENFORCED** |
| INV-030, INV-031, INV-031a, INV-032, INV-034, INV-036 | Pure function; `Policy.withdraw_with_stock = false` asserted; `provisional` derived from the window; partition asserted per run; `withdrawn = None` on absent evidence | AC-060 … AC-066, AC-070 | **ENFORCED** |
| INV-035 | Implausible quantity is a `question` characterisation; the internal valuation never reaches `evidence` (schema-enumerated keys) | AC-069 | **ENFORCED** |
| INV-041, INV-044 | Suppression over `withdrawn` and `idle` before ranking; yield 0 → suppressed | AC-081, AC-088 | **ENFORCED** |
| INV-042 | No Firestore write client in `src/engine/`; `cost_source: owner` precedence | AC-085 | **ENFORCED** (merge point unassigned — ARCH-GATE-007) |
| INV-043 | Deferral record carries no value field | AC-086 | **ENFORCED** |
| INV-045 | Only `cost_price` is asked in V1 — a fact from his own records | — | **ENFORCED** by scope |
| INV-052, INV-063 | `Value.certainty` is required by the schema; UI renders from it | AC-104, AC-124 | **ENFORCED** |
| INV-053 | Write-through with rollback; Firestore mirror; cache replays on `online` | AC-105 | **ENFORCED** |
| INV-056 | `compose` dedupe with stated precedence | AC-109 | **ENFORCED** |
| INV-060, INV-062, INV-065 | The artefact's `figures{}` *is* the registry `figures.py` prints; one code path | AC-127 | **ENFORCED** (owner-state source unstated — ARCH-GATE-009) |
| INV-064 | Schema forbids a value without a kind; no composites in V1 | AC-126 | **ENFORCED** |

---

## 7. Acceptance Verification Coverage

All 90 acceptance criteria in `specs.md` appear in the design's §21 matrix; the design
invents no criterion of its own. Verified by set difference — spec-only: none;
design-only: none. Three have a compromised path:

| AC | Architectural path | Verification boundary | Status |
|---|---|---|---|
| AC-107 (unavailable ≠ zero findings) | Per-capability `status` rendered by `DailyPage` | Contract test + e2e | **AT RISK** — hygiene has no addressable status (ARCH-GATE-001) |
| AC-083 (broad question outranks a narrow high-value one) | `owner_questions` expected-value ordering | Python unit test | **VACUOUS on real data** — every V1 cost question has yield 1, and "money at stake" is undefined (ARCH-GATE-002) |
| AC-044 (coverage separates structurally uncomparable items) | `coverage.structurally_uncomparable` | Python unit test on the pilot fixture | **UNTESTABLE as specified** — no predicate to test against (ARCH-GATE-004) |
| AC-127 (surface figure == reproduction figure) | `figures.py` = engine `--print`; artefact `figures{}` | Fresh-clone integration run, Phase 3 | **CONDITIONAL** — determinism depends on which owner-state source `figures` reads (ARCH-GATE-009) |
| AC-001 … AC-006, AC-008, AC-009 | `price_consistency` unit tests over the pilot fixture | Python | Viable |
| AC-020 … AC-029 | `reconciliation` unit tests; publisher money assertion | Python + contract | Viable |
| AC-040 … AC-054 | `competitor_position` unit tests; existing affinity acceptance check retargeted | Python | Viable |
| AC-060 … AC-071b | `catalogue_lifecycle` unit tests; partition assert per run | Python | Viable |
| AC-080 … AC-090 | `owner_questions` + owner-state round trip (Firestore live) | Python + e2e | Viable after Checkpoint 0-A |
| AC-100 … AC-112 | `compose` property tests + Playwright over the fixture artefact | JS + e2e | Viable |
| AC-120 … AC-129 | Fresh-clone reproduction, ≤ 2 min | Integration | Viable |

I confirmed the design's claim that the pilot ceiling is derivable: with its stated
parameters (2-point bands, ≥ 75 % density drop, ≥ 20 items in the preceding band) the
elbow lands at **18.0 %** — 81 items in the 16–18 % band collapsing to 8 — so AC-004/AC-005
have a real target. NFR-003 also holds with room: 204 of 6,234 price-paired products
surface, **3.3 %** against a 10 % bound.

---

## 8. Component Responsibility Audit

Every component below has one responsibility, one owner, and a stated "forbidden" list.
This is the strongest part of the design.

| Component | Purpose | Owned behaviour | Owned state | Primary specs | Depends on | Status |
|---|---|---|---|---|---|---|
| POS importer | CSV → typed silver, values preserved raw | Mapping, encoding sniffing, vintage | `silver_pos/{products,inventory,margins}` | all V1 inputs | mapping YAML | Clear |
| Sales importer | Monthly reports → month-grained evidence | Window derivation; `none` ≠ zero | `sales_monthly`, `sales_summary` | SPEC-002, SPEC-004 | inventory vintage | Clear |
| Signal builder / Matcher | Competitor observations; barcode ↔ external key | Incremental load; three-pass matching with confidence | `signals/`, `matching/` | SPEC-003 | rehydrate | Clear |
| Store registry | Format, affinity, client role | Manual classification is final (C-22) | `store_types.yaml` | SPEC-003 | — | Clear |
| Owner-state store + `pull.py` | Durable record of what the owner said and did | Validation, LWW, mirror | answers, outcomes, revivals | SPEC-005, SPEC-006 | Firestore | Clear |
| `price_consistency` | Four-state classification + ceiling | Ceiling derivation, D-4 exclusion | published counts/entries | SPEC-001 | POS only | Clear |
| `reconciliation` | Implied-opening detection **and hygiene** | Two independent signal families | published counts/entries | SPEC-002 | sales_summary | **AMBIGUOUS — two responsibilities, one status (ARCH-GATE-001)** |
| `competitor_position` | Cost floor → balanced reference → policy → attention | Reference construction, coverage | counts, thresholds, position | SPEC-003 | matches, stores | Clear (one predicate missing) |
| `catalogue_lifecycle` | Classify, withdraw, revive, hand over | The only lifecycle state — recomputed, never stored | `withdrawn[]`, `idle[]` | SPEC-004 | sales window, revivals | Clear |
| `owner_questions` | Select ≤3 cost questions | Suppression, ordering | `questions[]`, suppressed counts | SPEC-005 | withdrawn, idle, answers | **Ordering rule incomplete (ARCH-GATE-002)** |
| `surface_candidates` | Stamp `actionable` (1,2,4), attention, `value_kinds_present` | FR-103's producer half | per-entry flags | SPEC-006 | all capabilities | Clear |
| `provenance` | Figure registry, vintages, thresholds | Every published number registers | `meta.*`, `figures{}` | SPEC-007 | all | Clear |
| `publish.py` | Validate, assert money policy, assert status, write atomically | Refusal | `dashboard.json` | ARCH-DRIVER-002/003/007 | schema | **Contract incomplete (ARCH-GATE-001)** |
| `compose.js` | Admission ∧ outcome ∧ allocation ∧ dedupe ∧ bound | Selection only, no figure | none | SPEC-006 | artefact, owner state | Clear |
| `DailyPage` / capability pages / `QuestionPanel` / `DataPage` | Render | UI state only | none | SPEC-006, SPEC-005, SPEC-007 | compose | Clear (allocation statement unassigned) |
| `figures.py` | Reproduction = engine in print mode | Nothing of its own | none | SPEC-007 | engine | Clear (owner-state source unstated) |

No behaviour is owned by nobody. One behaviour — data hygiene's availability — is owned
ambiguously, which is the blocker.

---

## 9. State and Data Ownership Audit

| State | Authoritative owner | Mutated by | Read by | After interruption | Status |
|---|---|---|---|---|---|
| POS inventory CSV, sales reports | External POS; committed by the team | New commit | Ingestion | Last committed file stands | Clear |
| Competitor snapshots | CI collector, append-only, sealed per day | CI | `rehydrate_silver` | Partial day sealed as `partial` | Clear |
| Silver tables, signals, matches | Nobody — derived | Regenerated per run | Engine | Regenerated | Clear |
| **Owner state (answers, outcomes, revivals)** | **The owner, via the browser — the sole writer** | Browser only | Browser, engine (read-only) | Cache replays on `online`; engine uses last successful pull and says so | Clear, and singular |
| Withdrawal | **No stored state** — a pure function of (evidence, stock, revivals) | — | Every capability | Cannot be half-applied by construction | Clear (ADR-004 is the right call) |
| Artefact | Publisher, one atomic write per run | CI | Browser, `figures` (cross-check) | Previous artefact stands | Clear |
| Policy constants | Team, `configs/policy.yaml`, published in `meta.thresholds` | Commit | Engine | — | Clear |
| Surface composition | Browser, ephemeral | Every render | — | Recomputed | Clear |
| Effective cost price (POS value vs owner answer) | **Unassigned** — consumed by ≥3 capabilities | — | price_consistency, competitor_position, owner_questions, margin | — | **ARCH-GATE-007** |

Exactly one mutable store in the whole system, and the engine owns no persistent state.
That is the cleanest possible answer to Phase 8, and it is reached deliberately rather
than by accident.

---

## 10. Flow Audit

| Scenario | Architecture path | Failure path | Status |
|---|---|---|---|
| Nightly ingestion and publish (§9.1) | collect → seal → pull owner state → POS + sales import → rehydrate → signals → matching → capabilities → publish → `check:signals` → commit | Step isolation; dependents see `None` and publish `unavailable`; all-unavailable → publisher refuses, yesterday's artefact stands, CI red | **COMPLETE** |
| Owner state unreachable at run | Run continues; answers absent (D-3); `owner_questions: unavailable`; verdict `degraded`; CI publishes but goes red | Stated | **COMPLETE** |
| No competitor snapshot today | Newest sealed day; per-observation freshness; all stale → `unavailable: observations_stale`, never zero | Stated | **COMPLETE** |
| Owner opens the surface (§9.2) | fetch + schema-validate → owner state (cache → reconcile) → `compose` (6 ordered steps) → render | Fetch/validation failure → "could not be loaded" with the last known vintage, never "nothing to act on" | **COMPLETE** |
| Owner records an outcome (§9.3) | validate → cache write → write-through → re-compose | Cache write fails → rollback, not presented as recorded; Firestore fails → cache holds, browser filter still hides the entry | **COMPLETE** |
| Owner answers a cost question (§9.4) | write → Firestore → next run's pull → four named capabilities change → next morning | Storage unavailable → panel not shown (SPEC-005 §11) | **COMPLETE** |
| Owner challenges a figure (§9.5) | `figures.py` → engine `--print` → registry → figure · unit · vintage · thresholds · printed_at | Missing input → *unavailable — missing: X*, exit 1 | **COMPLETE**, one ambiguity (ARCH-GATE-009) |
| Withdrawal, revival, handover (§9.6) | Recomputed per run; revival by sale = absence of withdrawal; manual revival keyed to `window_id`; CSV download | No sales evidence → `unavailable`, `withdrawn = None`, no exclusion | **COMPLETE** |
| New POS export moves the ceiling (§9.7) | Ceiling derived per run and published with its derivation; `entry_id` excludes thresholds so outcomes survive | — | **COMPLETE** |
| **Receipts or sales absent — hygiene must continue** | §13 requires detection `unavailable` while hygiene continues | **The artefact cannot express it** | **BROKEN — ARCH-GATE-001** |

One note, not a finding: SPEC-006 §11 has two rows that both fit "no fresh data" — *every
capability unavailable* (say the surface cannot be produced) and *input data stale*
(present the age). The design's refusal-to-publish makes the second row govern, since the
browser keeps yesterday's artefact and shows its vintage. That is defensible and the
design states it; it is worth one sentence in §9.2 saying which row governs and why.

---

## 11. Failure Architecture

| Category | Design coverage |
|---|---|
| Malformed / missing input (POS header drift, malformed month) | Yes — import fails, window shrinks, statements updated, run `partial` |
| Unavailable dependency (Firestore, collector, snapshot day) | Yes — `unavailable` with a named reason at every level; watchdog on the collector |
| Timeout / interrupted execution | Yes — atomic `.tmp` + rename; withdrawal stored nowhere so it cannot be half-applied |
| Partial persistence | Yes — publisher refuses a partial artefact; extends the tested `EmptyExportError` |
| Duplicate operation / retry | Yes, narrowly — only the Firestore write-through retries, on `online`; everything else is permanent-for-the-day and visible. Correct for this system |
| Stale state | Yes — vintages on every count; freshness bound on observations; `printed_at` vs input vintage on reproduction |
| Inconsistent state (two devices) | Yes — LWW per record by `at`, existing tested adapter |
| External API change (FTPS, Wolt markup) | Partly — manifest `partial` + watchdog detect a stop; a *silent shape change* is not detected. Acceptable at this scale, and the collectors are the one subsystem with 29 days of proven operation |
| Degenerate threshold | Yes — `ceiling_degenerate` guard, though over-broad (ARCH-GATE-005) |
| Process restart | Yes — no engine state to restore |
| Model failure | N/A — no model in V1, deliberately |
| Browser storage unavailable | Yes — controls disabled with explanation; questions not shown |

The failure design is complete and, unusually, refuses to smooth anything over: the design
states plainly that non-retryable failures must be visible rather than degraded silently.

---

## 12. NFR Coverage

| NFR | Architectural mechanism | Evidence | Status |
|---|---|---|---|
| NFR-001, NFR-010, NFR-020, NFR-033, NFR-051 (explainability) | `evidence` dict per entry, keys enumerated per capability in the schema; verifiable against the owner's own POS | §11.3, AC-110c, AC-024, AC-042 | **CREDIBLE** |
| NFR-002, NFR-011, NFR-021, NFR-032, NFR-041, NFR-053, NFR-061 (determinism) | Pure functions of `EngineInputs`; run time is an input; sorted iteration; content addresses; byte-identical artefact except `generated_at`/`run_id` | §18 | **CREDIBLE** |
| NFR-003 (signal density ≤ 10 %) | Publish-time guard | Measured this audit: **3.3 %** on the pilot | **CREDIBLE**, guard over-broad (ARCH-GATE-005) |
| NFR-012 (only aggregate is a count) | `value_policy: none` + publisher assertion | AC-022 | CREDIBLE (unnamed in §21) |
| NFR-022 (freshness) | `freshness_days` in `policy.yaml`, provisional 14, published in `thresholds` | OQ-306 | **CREDIBLE** |
| NFR-030 (owner effort) | Withdrawal automatic; idle page paginates by rank | — | CREDIBLE |
| NFR-031 (reversibility) | Withdrawal is a recomputation, so reversal is the default, not a feature | ADR-004 | **CREDIBLE — structurally guaranteed** |
| NFR-040 (bounded by suppression, not by the limit) | Suppression over `withdrawn` + `idle` + zero-yield before ranking; 1,270 → 12 on the pilot | AC-082 | **CREDIBLE** |
| NFR-042, NFR-052 (durability) | Firestore + localStorage cache + LWW; write-through with rollback | ADR-003 | **CREDIBLE, unexercised** (ARCH-GATE-011) |
| NFR-050 (ten minutes) | Bound is a constant; measurement in the pilot | GAP-007 | Honest — measurement is the only closure |
| NFR-060 (reproduction ≤ 2 min) | Content-addressed reuse of silver/signals/matches, keyed by input vintages ‖ policy version; measured at Phase 3 | §16 | **CREDIBLE** — reuse is provably identical to recomputation, so FR-125 is not weakened |
| NFR-062 (zero preparation) | `python3 scripts/figures.py`, no arguments; committed inputs; snapshot rehydration | AC-121 | **CREDIBLE** |
| NFR-063, C-61 (coverage of stated figures) | Every figure in the registry; a figure without `inputs` cannot pass the schema | AC-128 | **CREDIBLE** |
| Performance / size | Artefact ≤ 3 MB; main chunk < 400 KB after the demo spine leaves (today 4.36 MB, of which `demoProducts.js` is 193,729 lines) | §16 | **CREDIBLE** |
| Security / privacy | §15 — Basic Auth, pinned Firestore rules, GitHub secrets, no runtime server | — | CREDIBLE for a pilot; posture flagged (ARCH-GATE-012) |

---

## 13. Current → Target Migration

The design's §20.1 maps 40+ current components. Sampled and verified against the
repository; every disposition checked was supported by evidence.

| Current | Target | Action | Evidence | Status |
|---|---|---|---|---|
| Collectors, seals, manifests, `rehydrate_silver` | same | REUSE | 29 consecutive sealed days; tests for seal/manifest/health | Sound |
| `pos_importer.py` | same + `--as-of` | REUSE | Produces 7,674 rows in four tables; no tests today | Sound |
| `import_yomyom_sales.py` | `sales_importer` → monthly + summary + window | REFACTOR | Verified: `refresh_pipeline.py` never calls it (steps at lines 56–105), and `import_pos_file` rewrites the sales table — the destructive ordering bug is real | Sound, and it fixes a live defect |
| `operational_recommendations.py` | `reconciliation.py` + `margin_below_cost.py`; Wolt rule REPLACED | REFACTOR + REPLACE | Verified `WOLT_GAP_MIN_PCT = 5.0` at line 40, applied `abs()` at line 296 — a different product from SPEC-001 | Sound |
| `product_recommendations.py` | `competitor_position.py` | REPLACE | `WATCH_PRODUCT` is INT-005 (V2); `PRICE_CHECK` produced 0 rows | Sound |
| `export_dashboard_data.py` | `publish.py` + schema v2 | REFACTOR | Cannot express unavailability | Sound |
| `print_figures.py` | `figures.py` = engine `--print` | REPLACE | Verified `WOLT_POLICY_CEILING_PCT = 18.0` hard-coded at line 83 — a third rule body; a standing INV-065 breach | Sound |
| `actionPriority.js` | `compose.js` (selection only) | REPLACE | Verified lines 86–93: `missing * cost` on `CHECK_STOCK_DISCREPANCY` — money on a stock quantity, forbidden by D-1 | Sound |
| `openQuestions.js` | engine `owner_questions.py` | REPLACE | Verified: it asks V2 questions (`carried`, `shelf_life`) and its `moneyAtStake` is a reorder value that leaves V1 | Sound — **but see ARCH-GATE-002** |
| Firestore adapters + LWW reconcile | `src/owner/persistence/*` | REUSE | 9 reconcile tests; Firestore path never exercised | Sound, unexercised |
| `completionActions.js` | `src/owner/outcomes.js` | REUSE + id migration | 22 tests; closed enums map cleanly | Sound |
| i18n + guards, e2e suite | same | REUSE | 673 keys × 3 languages, parity tests, e2e invariants | Sound — the right thing kept |
| Demo spine, browser engines, planogram, LLM layer, telemetry, POS connectors, `code/`, `SmartShelf AI/`, 17 dead scripts | removed at Phase 4 under tag `v1-attic` | REMOVE | Verified: `code/` = 176 tracked files, `SmartShelf AI/` = 22, referenced by nothing | Sound |
| **Telemetry (`telemetryModel.js`)** | removed | REMOVE | It is the "built measurement screen" `intent.md` §11.1 names and SPEC-000 §4 relies on | **ARCH-GATE-003** |

**Transitional adapters all have a deletion phase.** `operational.json` for one release,
outcome-id translation and localStorage key migration until Phase 4, old `check:signals`
probes until Phase 4. No permanent compatibility layer survives. This is exactly right.

**No working subsystem is rewritten without reason.** Every REPLACE is argued from a spec
divergence verified in the code, not from taste. No UNJUSTIFIED-REWRITE found.

**No legacy anchoring found.** The two candidates — Firestore and the anonymous-auth
posture — were both tested against "would we introduce this today?". Firestore: yes (a
hosted document store is the right answer to cross-device durability with no server under
D-12, and the alternatives are argued in ADR-003). Anonymous auth: retained by inheritance
rather than by argument, which is ARCH-GATE-012.

---

## 14. Unjustified Architecture

**None found.**

`margin_below_cost` is the only element without a producing specification. The design
identifies it itself (SPEC-GAP-A), justifies it from `intent.md` §2ب, keeps it off the
daily surface precisely because FR-103 requires a producing specification to define
actionability, and names the resolution as a release condition. That is the correct
handling of an orphan, not an orphan.

---

## 15. Remaining Architectural Decisions

### P0 — implementation cannot start

| Decision | Why it is P0 |
|---|---|
| **Is data hygiene a registered capability with its own id, status, badge and value policy — or a characterisation inside `reconciliation`?** | It determines `schemas/dashboard.schema.json`, `src/engine/registry.py`, `entry_id` (and therefore outcome-id stability under FR-115/C-50), the navigation, `compose`'s unvalued precedence list, and whether SPEC-002 §11 can be satisfied at all. All four are Phase 0 item 1. The design answers it both ways in different sections. See ARCH-GATE-001 |

### P1 — must be resolved before the affected area

| Decision | Area |
|---|---|
| What "money at stake" means for a cost-price question (ARCH-GATE-002) | Phase 1b `owner_questions` |
| What makes a product "structurally uncomparable" (ARCH-GATE-004) | Phase 1c `competitor_position` |
| Whether the SPEC-001 ceiling is derived before or after the FR-074 withdrawn exclusion (ARCH-GATE-006) | Phase 1a, and it changes published counts |
| Which component produces the effective cost price from POS ∪ owner answer (ARCH-GATE-007) | Phase 0 `inputs.py` |
| Whether `figures.py` pulls owner state live or reads the committed mirror (ARCH-GATE-009) | Phase 3, AC-127 |
| Whether INT-MEAS gets a V1 delivery, and if not, that this is said on 12/9 (ARCH-GATE-003) | Product decision, before release |

### P2 — legitimate low-level implementation choices

Band arithmetic for the ceiling elbow · parquet layouts · content-address hashing scheme ·
React component decomposition · i18n key naming · the shape of the handover CSV.

**One P0 remains, so the gate fails.**

---

## 16. Findings

### ARCH-GATE-001 — The capability contract cannot express data hygiene, which the design elsewhere treats as a capability

**Type:** CONTRACT-GAP · RESPONSIBILITY-DEFECT · contradictory design
**Severity:** BLOCKER
**Confidence:** HIGH

**Intent evidence:** `intent.md` §1 registers INT-002B ("نظافة البيانات": 625 negative stock, 307 unknown barcodes) as a V1 intent in its own right, distinct from INT-002.

**Spec evidence:**
- `specs.md` SPEC-002 §11 — "Receipts data unavailable for the period | The detection signal is unavailable; report it as unavailable, not as zero findings. **Hygiene signals are unaffected**."
- SPEC-002 FR-030 — "Hygiene signals MUST be distinguishable in the output from money-bearing signals."
- SPEC-006 FR-117 / INV-057 / AC-107 — "Where **a capability** has reported itself unavailable, the surface MUST show it as unavailable rather than as producing no entries"; "An unavailable capability MUST NEVER be rendered as zero findings."
- SPEC-006 FR-107 — every entry must show "which capability produced it".

**Design evidence — the contract says one thing:**
- §7.3 lists `reconciliation` as a single capability owning both families: "Flag negative implied opening balance…; hygiene records (negative stock, no barcode, absent price)".
- §11.2 `CapabilityOutput` has exactly one `status: 'available' | 'unavailable'`.
- §11.4 `capabilities: { [id]: CapabilityOutput }` — six ids, no hygiene.
- §10.2's registry listing enumerates six value policies; hygiene is not among them.

**Design evidence — five other sections say the opposite:**
- §13 — "Receipts or sales absent | reconciliation | detection `unavailable`; **hygiene continues** | User-visible: **Badge**".
- §21 SPEC-002 — "receipts/sales `None` → `unavailable`; hygiene continues | AC-107"; and "hygiene entries … with `characterisation: hygiene`, no value; **distinct capability badge**".
- §14 INV-054 — "**hygiene `value_policy: none`**" — a registry property, which only a registered capability has.
- §9.2 step (3) — unvalued entries "interleaved across unvalued capabilities in the stated order (**reconciliation, hygiene, idle**)".
- §22.2 — "Unvalued precedence … **reconciliation → hygiene → idle**".
- §7.4 — "Capability pages (×5 + margin browse)" with "nav reduced to 9 items", which only adds up if hygiene is one of the five.

**Repository evidence:** `src/recommendations/operational_recommendations.py` emits both families as recommendation *types*, not as capabilities with availability — the shape the design is refactoring away from, which is why the target contract has to settle it.

**Problem:** An implementer who follows §11.2 and §11.4 gets one capability with one
status. When receipts or sales are unavailable — a reachable condition the design's own
§13 designs for — that capability must be marked `unavailable`, which erases the hygiene
entries (SPEC-002 §11 says they are unaffected), or marked `available` with zero flagged
entries, which is exactly the rendering INV-057 forbids. An implementer who instead
follows §13/§14/§21 must invent a capability id, a registry entry, a value policy, a
schema key, a badge, a navigation entry and a slot in `compose`'s precedence list — none
of which the contract sections define.

**Why it matters:** This is Phase 0 item 1 ("`schemas/dashboard.schema.json` v2;
`CapabilityOutput`, `Entry`, `Value` dataclasses; `configs/policy.yaml`;
`src/engine/registry.py` with value policies"). It also decides `entry_id = sha256(capability ‖ barcode ‖ variant)`.
Choosing one way now and the other way later renames every hygiene entry id, which breaks
FR-115 and C-50 — the compatibility obligation the specification layer explicitly recorded
as REPO-002. It is the one place where following the design as written forces a
contradiction with a specification, and under the authority hierarchy the specification
wins, so the design cannot stand as the implementation's contract.

**Required resolution:** Settle whether hygiene is a capability, and make §7.3, §10.2,
§11.2 and §11.4 say the same thing as §9.2, §13, §14, §21 and §22.2. If it is a capability,
give it an id, a registry entry with `value_policy: none`, a place in `capabilities{}`, and
say that `reconciliation.py` publishes two `CapabilityOutput`s. If it is not, then §13's
"hygiene continues" and §21's "distinct capability badge" must be withdrawn and SPEC-002
§11 satisfied some other way that the contract can express. Do not resolve it by adding a
sub-status to `CapabilityOutput` without also settling the badge, the page, the precedence
slot and the entry id.

Two smaller instances of the same contract inconsistency should be fixed with it:
`catalogue` and `questions` appear in §11.4 as **top-level blocks** rather than inside
`capabilities{}`, and the `catalogue` block carries **no `status` field** — yet §13
requires `catalogue_lifecycle` to publish `unavailable: no_sales_evidence`, §7.3 says the
publisher must "refuse on any capability without a status", and AC-066/AC-107 verify it.

---

### ARCH-GATE-002 — The ordering rule for the owner's only questions has no defined "money at stake", and the existing behaviour the design says it preserves does not transfer

**Type:** IMPLEMENTATION-DECISION-LEAK · DESIGN-COVERAGE-GAP
**Severity:** MAJOR
**Confidence:** HIGH

**Intent evidence:** `intent.md` §5 — «مرتّبة بـ«المال × كم صنفاً يصلحه الجواب»» — twelve
questions, three on screen, ordered by money × how many products the answer fixes.

**Spec evidence:** SPEC-005 FR-085 — "Questions MUST be ordered by expected value, defined
as **the money at stake** multiplied by the question yield." C-41 — "Existing behavior
ranks questions by money at stake multiplied by the number of products an answer would
affect. **That ranking is preserved** (FR-085)." Verified by AC-083. Neither "money at
stake" nor its basis is defined anywhere in `specs.md`.

**Design evidence:** §21 SPEC-005 — "FR-085, C-41, NFR-041 | **expected value = money at
stake × yield (deterministic)** | E | AC-083". §7.3 — "order by money × yield". §10.1 —
`Question` carries "why (products affected, money at stake), expected value". The design
restates the formula and locates it in the engine; it defines neither operand.

**Repository evidence:** `src/lib/questions/openQuestions.js:80-113` — the C-41 behaviour
the design says it preserves computes `moneyAtStake` as `valueByProduct.get(product.id)`,
a **reorder value** supplied by the V2 reorder engine, and `productsAffected` from the
**shelf-life category** grouping. Both inputs leave V1 with the reorder engine and the
shelf-life questions (design §5.4, §20.1: `openQuestions.js` → REPLACE). Nothing transfers.

Worse, V1's only question is `cost_price`, keyed per barcode (design §10.1:
`question_id = sha256('cost_price' ‖ barcode)`), so the **yield is 1 for every question**
and FR-085's product collapses to "money at stake" alone. And the products in question are
precisely those with **no cost price** — so the obvious money bases (margin, loss per sale)
are unavailable by construction. An implementer must choose between seven-month revenue,
units sold × shelf price, shelf price alone, or something else. Each produces a different
three questions on the owner's screen out of twelve.

**Why it matters:** SPEC-005 is the whole of INT-010, and its entire visible output is the
three questions the owner sees. The ranking is the capability. It is also a *published
figure* under SPEC-007 FR-122 ("A figure MUST NOT be stated whose provenance cannot be
given") — the design publishes `questions[].why.money_at_stake`. And AC-083 becomes
vacuous on the pilot data: with yield ≡ 1 there is no "broad question" to outrank a narrow
one, so the criterion can only be exercised on a synthetic fixture, which will not catch a
wrong money basis.

**Required resolution:** Define the money basis for a cost-price question at the layer that
owns it — or, if `specs.md` should own it, register it as a spec gap the way SPEC-GAP-A is
registered, with a provisional value in `configs/policy.yaml` so the choice is published in
`meta.thresholds` and reproducible. Also correct the C-41 claim: state what of the existing
ranking is actually preserved (the *shape* money × yield) and what is not (both operands).

---

### ARCH-GATE-003 — The design removes the surface the specification layer relies on to justify not specifying INT-MEAS, and builds nothing in its place

**Type:** INTENT-DRIFT · MIGRATION-GAP
**Severity:** MAJOR
**Confidence:** HIGH

**Intent evidence:** `intent.md` §11 — «معيار القرار — حتى لا يكون 12/9 اجتماع آراء» — the
first of three numbers settled on 12/9 is «**رقم النجاح:** بعد 30 يوماً من V1، كم ₪ مستردّة
(أسعار مصحّحة + مخزون مفسّر + كتالوج منظّف)… **القياس آلي عبر شاشة القياس المبنية**». §11's
closing paragraph makes the entire 30-day go/no-go turn on that number, and §13 lists it
among the decisions to be taken at the meeting. V1 ships ~20/9; the measurement is due ~20/10.

**Spec evidence:** SPEC-000 §4 — "**INT-MEAS** is not specified here for a different reason:
`intent.md` §11.1 states it is **already measured by an existing surface**, so no new
capability is being designed." The whole justification for leaving a V1-registered intent
unspecified is that the surface exists. The prior gate recorded the same concern as
GATE-007 (MAJOR) and left it as OQ-801 (P1).

**Design evidence:** §5.4 — "**S24 telemetry entry** (`telemetry.html`, `src/telemetry/*`) |
Unlinked, single-device; INT-MEAS is *registered, unspecified*; the design captures what it
will need (outcome snapshots, §10) and **builds no surface**". §20.1 removes it. §21
cross-cutting — "INT-MEAS | outcome snapshots captured (§10.3); no surface built; OQ-801
open". §23's release conditions list SPEC-GAP-A, GAP-009 and GAP-005 — **INT-MEAS is not
among them**.

**Repository evidence:** `src/telemetry/telemetryModel.js` is that surface: it accumulates
`potentialImpactIls` and, per recorded decision, "the ₪ recorded on the decision at the
moment it was made" (lines 96–111) — the realised-recovery figure `intent.md` §11.1 names.
It is a second Vite entry (`vite.config.js:17`), unlinked from the app, reading one
browser's localStorage. Its money comes from `actionPriority.js`, so it currently carries
the D-1-forbidden stock-derived figure — removing it as-is is correct.

**Problem:** The design is right to remove it and right that the outcome snapshot in §10.3
is the data INT-MEAS needs. But the removal falsifies the premise on which SPEC-000 §4
declined to specify INT-MEAS, and the design does not record that consequence. The result
is that a V1-registered intent — the one the pilot's continue/stop decision runs on —
has no delivery, no specification, and no release condition. On ~20/10 the team will have
outcome records in Firestore and no stated number.

**Why it matters:** This is precisely the Phase 4 failure mode: every individual
requirement passes, and the product outcome the intent was written to produce does not
arrive. `intent.md` §11 exists so that 12/9 «حتى لا يكون اجتماع آراء» — so the meeting is
not a meeting of opinions. Without the figure, day 30 becomes exactly that.

**Required resolution:** Record at the design layer that removing S24 invalidates SPEC-000
§4's stated reason for not specifying INT-MEAS, and either (a) add INT-MEAS to §23's
release conditions so it is decided before V1 ships, or (b) state explicitly that V1 ships
without a measurement surface and that OQ-801 plus the go/no-go number must therefore be
settled at the specification layer first. Do not design the surface here — that is the
spec layer's decision, and OQ-801 (what the "stock explained" component may contain under
D-1) has to be answered before it can be designed.

---

### ARCH-GATE-004 — "Structurally uncomparable" is published as a count with no defining rule

**Type:** IMPLEMENTATION-DECISION-LEAK · CONTRACT-GAP
**Severity:** MAJOR
**Confidence:** HIGH

**Intent evidence:** `intent.md` §9.4 — the team commits, in person on 12/9, to saying that
price comparison does not cover the catalogue, and gives the structural reason: «**1,628
صنفاً في كتالوجه خدمات ورموز داخلية** (غسيل سيارات، قهوة باريستا، أكواد داخلية بلا باركود
عالمي) — لا تُباع عند أحد فلا يوجد ما يُقارَن بها».

**Spec evidence:** SPEC-003 FR-052 — "The system MUST distinguish products that are
structurally uncomparable — services and internally-coded items that no other retailer
sells — from products merely not yet matched, and MUST NOT count the former as a coverage
failure." INV-023, AC-044 and SCN-045 all depend on it. The spec gives examples, not a test.

**Design evidence:** §21 SPEC-003 — "FR-050, FR-051, FR-052, INV-023 |
`coverage {catalogue, comparable_population, matched, **structurally_uncomparable**}`…". The
field is named in the contract and in §7.3's owned outputs. No rule, no policy constant, no
mention in §22.2's provisional-parameters register.

**Repository evidence:** §3.5 measures 307 catalogue rows with no barcode. The intent's
1,628 is a larger and differently-derived population, and nothing in the repository
computes it — the closest artefact, `public/data/assortment_gap.json`, is dated 2026-08-11
and is on the removal list.

**Problem:** The predicate is the difference between "we cover 35 % of your catalogue" and
"we cover 35 %, and 21 % of the rest is car washes and barista coffee that nobody else
sells". Candidate rules — no barcode at all; a barcode that is not EAN/UPC-shaped; a
department on a services list; an internal code prefix — give materially different counts,
and the count goes into an owner-facing coverage statement. Implementation will invent one.

**Why it matters:** SPEC-007 FR-122 forbids stating a figure whose provenance cannot be
given, and FR-123 requires the threshold in force to be stated with it. An invented
predicate has neither. AC-044 has nothing to assert against.

**Required resolution:** State the predicate, or register it in §22.2 as a provisional
parameter in `configs/policy.yaml` so it is published in `meta.thresholds` and reproducible
— the same treatment the design already gives `implausible_ratio` and `full_annual_cycle`.

---

### ARCH-GATE-005 — The signal-density guard would suppress the confirmed-loss signal that FR-006 exists to protect

**Type:** FLOW-GAP / spec interaction
**Severity:** MINOR
**Confidence:** HIGH

**Spec evidence:** SPEC-001 FR-003/FR-007 — inverted products MUST be surfaced as confirmed
losses. FR-006 — when the ceiling is underivable, "the *inverted* signal is unaffected and
MUST continue to be surfaced". NFR-003/INV-003 bound the *surfaced proportion* at 10 %.

**Design evidence:** §14 — "INV-003 / NFR-003 … Assert at publish: if surfaced ≥ paired or
> 10 %, **the capability publishes `unavailable: ceiling_degenerate`**".

**Problem:** The guard is whole-capability. The surfaced set is inverted + above-ceiling, so
a future export in which inverted alone exceeded 10 % would take the confirmed losses off
the surface — the one signal FR-006 explicitly protects when the ceiling misbehaves. The
design already knows the right shape: for an underivable ceiling it suppresses only the
above-ceiling half and keeps inverted.

**Repository evidence:** Not currently binding — measured this audit, 204 of 6,234
price-paired products surface (**3.3 %**), of which 68 inverted.

**Required resolution:** Say which half the guard suppresses, consistently with FR-006.

---

### ARCH-GATE-006 — Whether the ceiling is derived before or after the withdrawn-set exclusion is unstated, and it moves every published count

**Type:** IMPLEMENTATION-DECISION-LEAK
**Severity:** MINOR
**Confidence:** HIGH

**Spec evidence:** SPEC-004 FR-074 / C-31 / AC-068 — "Withdrawn entries MUST be excluded
from other capabilities' populations, and **every count those capabilities publish MUST
reflect the exclusion**." SPEC-001 FR-004/INV-002 — the ceiling is derived from "the
distribution of the store's own observed markups" for "the period in question".

**Design evidence:** §11.1 passes `withdrawn` to every capability; §21 maps FR-074 to
"counts exclude". Nothing says whether the *ceiling derivation population* is the full
price-paired set or the post-exclusion set.

**Repository evidence — measured this audit on the committed pilot data:**

| Population | Price-paired (after D-4) | Inverted | Above 18 % | Surfaced % | Elbow |
|---|---:|---:|---:|---:|---:|
| All products | 6,234 | 68 | 136 | 3.3 % | 18.0 % |
| Excluding withdrawable (dead + zero stock) | 2,626 | 53 | 111 | 6.2 % | 18.0 % |

The ceiling itself is robust — 18 % either way, which is good news for AC-004/AC-005. The
**counts are not**: the intent's headline 68 and 136 become 53 and 111 once FR-074 is
applied, and the density doubles.

**Why it matters:** These are figures the team will state on 12/9. `intent.md` §12 already
warns that every number must come from `npm run figures` rather than the document, so the
mechanism is right — but the design should say which population the engine uses, or the
first reproduction will disagree with the intent document for a reason nobody can name in
the room.

**Required resolution:** State the derivation population explicitly and record it in the
figure registry's `inputs`.

---

### ARCH-GATE-007 — The effective cost price has no single owner, though four capabilities consume it

**Type:** RESPONSIBILITY-DEFECT
**Severity:** MINOR
**Confidence:** MEDIUM

**Spec evidence:** SPEC-005 FR-087 / INV-042 — an owner's answer is authoritative and must
never be overwritten by inference. FR-093 — capabilities that need the fact MUST use it.

**Design evidence:** §11.1 gives every capability both `products` (carrying the POS cost)
and `owner: OwnerState` (carrying answered costs), and §9.4 lists four consumers of a cost
answer — `price_consistency` (D-4 artefact test), `competitor_position` (policy entry),
`owner_questions` (question closes), and implicitly `margin_below_cost`. §10.1 says
`cost_price` carries `source: pos | owner`, which implies a single merge — but no component
is named as producing it. ARCH-DRIVER-001 is explicitly "one rule, one implementation".

**Problem:** Four modules each merging POS cost with owner cost is four chances to
implement the precedence differently. A capability that reads `products.cost_price` and
forgets `owner.answers` violates INV-042 silently, and AC-085 would only catch it in
whichever capability the test targets.

**Required resolution:** Name the component that produces the effective cost — `inputs.py`
is the natural place, since it already drops affinity-0 stores and builds `EngineInputs` —
and state that capabilities read only the merged field.

---

### ARCH-GATE-008 — FR-106 requires the allocation to be stated; no component is assigned to state it

**Type:** CONTRACT-GAP (UI)
**Severity:** MINOR
**Confidence:** HIGH

**Spec evidence:** SPEC-006 FR-106 — "The surface MUST allocate places to unvalued entries
explicitly rather than ranking them against valued ones, **and the allocation MUST be
stated**." SPEC-GAPS GAP-006's resolution spells out the audience: "An explicit allocation
is defensible to the owner ('two of your ten are counting tasks')."

**Design evidence:** §10.4 puts `surface: {bound, unvalued_places}` in `configs/policy.yaml`;
§11.4 publishes it in `meta.thresholds`. §7.4's `DailyPage` responsibility list — "≤10
entries, capability badge, physical action, evidence, value with kind, estimate label,
outcome controls, per-capability availability, empty state, data age" — does not include
the allocation. §21 maps FR-106 to "`unvalued_places` (provisional 3) with per-capability
keys | AC-100 + unit test", which verifies the mechanism, not the statement.

**Problem:** The value is published but nothing renders it, so FR-106's second clause has no
owner. Note this does not collide with FR-101: stating "three of your ten are counting
tasks" is an allocation, not a remainder count.

**Required resolution:** Add the allocation statement to `DailyPage`'s owned rendering and
give it an acceptance path.

---

### ARCH-GATE-009 — Which owner state `figures.py` reads is unstated, and AC-127 turns on it

**Type:** CONTRACT-GAP
**Severity:** MINOR
**Confidence:** HIGH

**Spec evidence:** SPEC-007 FR-125 — reproduction MUST read current data, not a recorded
value. INV-065 / AC-127 — the figure from the surface equals the figure from reproduction
on the same data. NFR-062 — no setup, no arguments.

**Design evidence:** §9.5 — "`OwnerState.pull` (**or** the committed mirror, flagged as
such)". §12 calls the mirror "a *read replica* for reproduction".

**Problem:** The two branches behave differently in the case that matters. Reading the
mirror makes AC-127 deterministic on a fresh clone (the mirror is committed by the same run
that wrote the artefact) but is a recorded value, which FR-125 disfavours. Pulling live is
current data but requires a service-account credential on the laptop, which NFR-062's "no
preparation" cannot assume, and will disagree with the artefact whenever the owner has
answered since last night — precisely the FR-127 case the design wants visible. Both are
defensible; the design must pick one and say how the other is reported.

**Required resolution:** State the default and the fallback, and how each is labelled in the
printed output.

---

### ARCH-GATE-010 — §22.2 reads as the register of provisional product decisions but omits seven P1 open questions

**Type:** MISSING-ARCH-DECISION (documentation completeness)
**Severity:** MINOR
**Confidence:** HIGH

**Spec evidence:** `specs.md` SPEC-GAPS Part 2 lists 19 questions at P1.

**Design evidence:** The design references 20 OQ ids. Absent: **OQ-102** (may the owner mark
an inverted price deliberate, suppressing it), **OQ-203** (a product both flagged and dead —
which governs), **OQ-402** (introduction grace period for new products), **OQ-407**
(withdrawn entries visible on ordering surfaces), **OQ-603** (may staff act on entries),
**OQ-701** (which figures must be reproducible), **OQ-702** (reproduction vs surface
disagreement). OQ-302 is listed at P1 in SPEC-GAPS Part 2 although SPEC-003 §17 marks it
resolved — a stale row in the specs, worth noting back.

**Assessment:** Several are answered implicitly and well. OQ-102 is served by the generic
decline outcome (§10.5: "a decline stands for the entry id"). OQ-203 is served by FR-074's
exclusion — withdrawal wins. OQ-702 is served by §9.5 printing both vintages. OQ-402 has no
data to implement against (the POS export carries no introduction date), so the spec's
unconditional FR-063 governs. OQ-407 and OQ-603 are V2/pilot-operational. None of these
blocks implementation.

**Why it still matters:** §22.2 presents itself as the complete register of what
implementation may treat as provisional. An implementer reading it will believe the
unlisted questions have no bearing, and will not know that "a declined inverted price stays
declined" is the design's answer to OQ-102 rather than an accident of the outcome model.

**Required resolution:** Either extend §22.2 to cover the P1 set with the design's stance
(including "answered implicitly by X"), or say that it lists only the parameterised subset
and point to SPEC-GAPS for the rest.

---

### ARCH-GATE-011 — The deployment prerequisites the whole design rests on are unconfigured and only partly scheduled

**Type:** UNVERIFIED-FEASIBILITY
**Severity:** MINOR
**Confidence:** HIGH

**Design evidence:** ADR-003 makes Firestore the single mutable store; §22.3 rates the
first-run risk **High**; §23 Phase 0 item 2 schedules Checkpoint 0-A (`check:firebase-live`
plus a CI dry-run pull) before any capability work. §15 keeps Basic Auth as trust boundary 1
but no phase assigns it.

**Repository evidence — verified this audit:** in `.env`, `BASIC_AUTH_USER`,
`BASIC_AUTH_PASSWORD`, `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_APP_ID` and
`FIREBASE_SERVICE_ACCOUNT_JSON` are all **empty**; only `VITE_STORE_ID` is set. `middleware.ts:42-43`
fails closed, so the deployed site returns 503 today. `src/engine/`, `src/owner_state/`,
`schemas/` and `configs/policy.yaml` do not exist — the target is entirely unbuilt, which is
consistent with the design's own account.

**Problem:** The Firestore risk is handled correctly — sequenced first, with honest
degradation designed in §13 if it fails. Two gaps remain: the design carries **no fallback
design** if Checkpoint 0-A cannot be passed (SPEC-005 NFR-042 and SPEC-006 NFR-052 then
have no mechanism, and SPEC-005 §11 removes the question panel entirely), and the Basic
Auth credentials — trust boundary 1 for a page carrying the store's cost prices — are
scheduled in no phase.

**Required resolution:** Add the Basic Auth credentials to Phase 0's prerequisites, and
state in one line what happens to SPEC-005/SPEC-006 durability if Checkpoint 0-A fails —
even if the answer is "stop and redesign", which is a legitimate answer.

---

### ARCH-GATE-012 — Making Firestore load-bearing turns a dormant exposure into a live one, with no trigger for the stated mitigation

**Type:** SECURITY-DESIGN-GAP
**Severity:** MINOR
**Confidence:** HIGH

**Design evidence:** §15 trust boundary 2 — "Firestore rules pinned to
`/stores/yomyom-kafr-qasim/**`, anonymous sign-in. **Accepted pilot posture** … anyone who
loads the app can mint a token and read/write that subtree. Mitigation before wider
exposure (not V1): App Check. The design adds nothing here because D-12 forbids accounts."

**Repository evidence:** `firestore.rules` says the same thing about itself, at length, and
names the conditions for revisiting: "before the pilot is extended, a second store is
added, or the URL is shared more widely". Today the exposure is theoretical — `src/firebase.js`
is inert because the config is empty, and outcomes never leave the device.

**Problem:** The design's own change is what activates it: from Phase 0 the owner's cost
answers, decisions and dismissal reasons live in that subtree, and the engine's CI pull
makes it load-bearing rather than optional. No specification requires more, and D-12 does
forbid accounts — but App Check requires no accounts and would close the hole. The design
defers it to "wider exposure" without naming the trigger, and the rules file's own trigger
list does not include "the data became real", which is exactly what happens here.

**Required resolution:** Either schedule App Check in a phase, or state that the exposure is
accepted for the pilot **with the owner informed**, and record the date or event that
forces the revisit.

---

### ARCH-GATE-013 — NFR-012 is mechanically covered but not named in the traceability matrix

**Type:** DOCUMENTATION
**Severity:** INFO
**Confidence:** HIGH

SPEC-002 NFR-012 ("the only aggregate this specification may publish is a count") is the one
NFR absent from §21. It is enforced by `value_policy: none` plus the publisher assertion and
verified by AC-022, so nothing is at risk — but §21 is described as the test index, and a
missing row reads as a missing test.

---

### ARCH-GATE-014 — `market-context.json` is produced nightly with no V1 consumer

**Type:** ACCIDENTAL-COMPLEXITY (minimal)
**Severity:** INFO
**Confidence:** HIGH

§5.4 and §20.1 keep `src/context/*` and `market-context.json` "produced nightly for V2; not
read by V1", while removing 17 other unreferenced scripts. The inconsistency is deliberate
and harmless — the cost is a step in a nightly job — but it is the one surviving component
with no V1 justification, and the design should say whether it is kept because removing it
would break the collector or because V2 wants the history to accumulate (the latter would
make it a legitimate MIGRATION-TEMPORARY, like the receiving capture).

---

## 17. Gate Checklist

| Check | Result |
|---|---|
| Intent preservation | **FAIL** — INT-MEAS loses its delivery (ARCH-GATE-003); the other seven V1 intents are preserved |
| Spec coverage | **PASS** — 0 missing; 90/90 ACs answered; 4 FRs partial |
| Reverse design justification | **PASS** — no material orphan; the one candidate is self-declared |
| Invariant enforcement | **FAIL** — INV-057 unenforceable for hygiene (ARCH-GATE-001); 44 of 46 fully enforced |
| Acceptance verification | **PASS with reservations** — AC-107 at risk, AC-083 vacuous, AC-044 untestable |
| Component ownership | **FAIL** — `reconciliation` owns two independently-available responsibilities |
| State ownership | **PASS** — one mutable store; the engine owns no persistent state |
| Data ownership | **PASS**, one unassigned derivation (effective cost) |
| Contract completeness | **FAIL** — ARCH-GATE-001; `catalogue` block lacks a status |
| Flow completeness | **PASS** — nine flows with normal, alternate and failure paths |
| Failure design | **PASS** — the strongest section; refusal preferred to smoothing |
| NFR coverage | **PASS** — every material NFR has a credible mechanism, several measured |
| Security / privacy | **PASS for a pilot** — posture recorded; mitigation trigger missing |
| Testability | **PASS** — pure functions, one schema two validators, reproduction as the integration test, rule-12 probes retargeted |
| Migration completeness | **PASS** — every current subsystem dispositioned, every adapter has a deletion phase |
| Legacy anchoring | **PASS** — challenged and argued, not inherited |
| Rewrite bias | **PASS** — every REPLACE traced to a verified spec divergence |
| Simplicity | **PASS** — no service decomposition, no queue, no cache beyond content addressing |
| Architectural decisions | **PASS** — 13 ADRs with context, alternatives, trade-offs, reversibility |
| Repository feasibility | **PASS with reservations** — claims re-verified; Firebase and Basic Auth unconfigured and partly unscheduled |
| No hidden architectural decisions | **FAIL** — one P0 (ARCH-GATE-001) and three P1 rule definitions |
| Bidirectional traceability | **PASS** — forward and reverse matrices both present and both complete |

---

## 18. Minimum Required Actions

To reach PASS. These are corrections to `design.md` only — no specification or intent needs
to change, and no architecture needs rework.

**Blocking (must be resolved before Phase 0 item 1):**

1. **Settle data hygiene's identity in the contract.** Make §7.3, §10.2, §11.2 and §11.4
   agree with §9.2, §13, §14, §21 and §22.2 on whether hygiene is a capability with its own
   id, status, `value_policy`, badge, page and precedence slot. Whatever the answer, ensure
   `entry_id`'s `capability` component is fixed by it before any outcome is recorded, and
   that SPEC-002 §11 ("detection unavailable, hygiene unaffected") is expressible.
   (ARCH-GATE-001)

2. **Give the `catalogue` block a `status`**, or move `catalogue` and `questions` inside
   `capabilities{}` so the publisher's "refuse on any capability without a status" rule can
   actually run over them. (ARCH-GATE-001, second instance)

**Required before the affected phase, and cheap to state now:**

3. Define the money basis for a cost-price question, or register it as a provisional
   parameter in `configs/policy.yaml`; and correct the C-41 "preserved" claim.
   (ARCH-GATE-002 — Phase 1b)
4. Define the "structurally uncomparable" predicate, or register it as a provisional
   parameter. (ARCH-GATE-004 — Phase 1c)
5. State whether the SPEC-001 ceiling is derived before or after the FR-074 exclusion, and
   record the population in the figure registry. (ARCH-GATE-006 — Phase 1a)
6. Name the component that produces the effective cost price. (ARCH-GATE-007 — Phase 0)
7. State whether `figures.py` pulls owner state live or reads the committed mirror, and how
   the other case is labelled. (ARCH-GATE-009 — Phase 3)
8. Narrow the `ceiling_degenerate` guard so it cannot suppress inverted entries.
   (ARCH-GATE-005 — Phase 1a)
9. Assign the FR-106 allocation statement to `DailyPage` and give it an acceptance path.
   (ARCH-GATE-008 — Phase 2)
10. Add the Basic Auth credentials to Phase 0's prerequisites. (ARCH-GATE-011)

**Product decision to surface, not to take here:**

11. Record that removing the telemetry surface invalidates SPEC-000 §4's reason for leaving
    INT-MEAS unspecified, and add INT-MEAS to §23's release conditions alongside SPEC-GAP-A,
    GAP-009 and GAP-005 — so that either it is specified before V1 ships, or the team goes
    into 12/9 knowing the 30-day number will not compute itself. (ARCH-GATE-003)

**Documentation, non-blocking:**

12. Extend §22.2 to state the design's stance on the seven unaddressed P1 questions, or say
    it covers only the parameterised subset. (ARCH-GATE-010)
13. Name NFR-012 in §21. (ARCH-GATE-013)
14. Say why `market-context.json` survives. (ARCH-GATE-014)
15. Schedule App Check or record the trigger that forces it. (ARCH-GATE-012)

---

*Nothing in `intent.md`, `specs.md` or `design.md` was modified by this audit. All
repository figures quoted above were measured from the committed pilot data on 2026-09-08,
not read from any document.*


---

## 19. Resolution Log — Run 2 (2026-09-08)

The blocker was put to a five-advisor council (Contrarian · First Principles · Expansionist
· Outsider · Executor), followed by an anonymous peer-review round in which each advisor
reviewed all five responses without knowing the authorship, then a chairman synthesis. The
council was **unanimous** on the answer and all five reviewers independently ranked the
same argument strongest.

### ARCH-GATE-001 — CLOSED

**Council decision:** split. Data hygiene is its own registered capability.

**The argument that decided it** (First Principles, ranked strongest by 5 of 5 reviewers):
this was never a tie between four contract sections and five behaviour sections. SPEC-002
§11 had already decided it, and the contract sections were stale enumerations, not a
competing position — under the authority hierarchy the specification wins. The underlying
error was defining *capability* extensionally ("these six things"), which makes a
membership question unanswerable. Defined intensionally — **the smallest unit that can
independently become unavailable** — the answer falls out mechanically, and it resolves
`catalogue_lifecycle`'s missing status by the same rule instead of as a second patch.
Availability is the only one of the term's seven roles forced by the world rather than
chosen.

**The precondition the council added** (Contrarian, ranked the best single catch by 4 of 5
reviewers): `entry_id` hashed `capability_id`, making a taxonomy label load-bearing on the
owner's durable decisions in Firestore. Any re-carving would orphan them, and silently —
unmatched keys simply stop suppressing entries he already declined. Fixing this first is
what makes the split safe rather than irreversible.

**Applied to `design.md` (v1.0 → v1.1):**

| # | Change | Sections |
|---|---|---|
| 1 | `entry_id = sha256(**signal_family** ‖ barcode ‖ variant)` — a permanent, enumerated, never-renamed identity string, distinct from the mutable routing `capability` id | §10.1, §11.3, ADR-009 |
| 2 | ADR-014 added: the intensional definition, the decision, both rejected alternatives with their costs, and the trade-offs (SPEC → capability is now many-to-one; a module may return several outputs) | §19 |
| 3 | `hygiene` registered as a capability: own row, own `requires`, `value_policy: none`, own badge, own page, own precedence slot | §7.3, §10.2, §21 |
| 4 | `CapabilityOutput` gains `requires: list[str]`; `status` is **derived** from it against the inputs that landed, never hand-declared — so SPEC-002 §11 is computed, not written | §11.2 |
| 5 | `capabilities{}` holds exactly the registry ids; `catalogue_lifecycle` and `owner_questions` move inside it and gain a `status`; their extra fields become capability-specific extras | §11.4 |
| 6 | Unvalued precedence stated in full — reconciliation → competitor_position → idle → **hygiene last**, with the reason (1,155 finite cleanup records would hold the reserved places for weeks) — and lifted into `configs/policy.yaml` as `surface.unvalued_order` | §9.2, §22.2 |
| 7 | Cross-capability duplication named explicitly as `compose` step (4)'s job, with both entry ids persisting so an outcome on one does not silently satisfy the other | §9.2 |
| 8 | The rule-12 **independence probe** added: run with `sales_monthly` withheld, assert `reconciliation.status == 'unavailable'` **and** `hygiene.status == 'available'` with a non-zero count — stated as something a unit test structurally cannot catch | §14, §18 |
| 9 | Phase 0 item 1 rewritten: the id set and the `signal_family` enumeration must be frozen before anything downstream starts, because they are the keys of every decision the pilot will record | §23 |
| 10 | Phase 1a, Phase 2, the reverse-justification table, the nav item list and the §13 failure rows updated to match | §5.1, §13, §20.1, §21, §23 |

**Verified after the edit:** no occurrence remains of `sha256(capability ‖ …)`, of the old
three-item precedence order, of a top-level `catalogue:`/`questions:` block, or of the
"six capabilities" / "×5 pages" counts. `intent.md` and `specs.md` are byte-identical to
before the audit.

### Findings incidentally closed by the same edit

| Finding | How |
|---|---|
| ARCH-GATE-005 (density guard would suppress inverted entries) | `unavailable_reason: ceiling_degenerate` is now one reason among several on a capability whose `status` is computed from `requires`; the guard is stated as a rule-level reason, not an input failure. *Still requires the explicit statement that only the above-ceiling half is suppressed — remains open as MINOR.* |
| ARCH-GATE-010 (unlisted P1 questions) | Partly: OQ-503 (questions occupy their own panel, not surface places) and OQ-601/OQ-602 (the unvalued order and its home in `policy.yaml`) are now explicit in §9.2 and §22.2. The other P1 stances remain unstated. |
| The SPEC-006 §11 two-row ambiguity noted in §10 of this report | §13 now states which row governs and why. |

### Still open after run 2

| Finding | Severity | Gate |
|---|---|---|
| ARCH-GATE-002 — "money at stake" undefined for the cost question; the C-41 claim does not transfer | MAJOR | Before Phase 1b |
| ARCH-GATE-003 — INT-MEAS has no V1 delivery and no release condition | MAJOR | Product decision, before release |
| ARCH-GATE-004 — "structurally uncomparable" predicate undefined | MAJOR | Before Phase 1c |
| ARCH-GATE-006 … 014 (less GATE-005 partly, GATE-010 partly) | MINOR / INFO | Non-blocking |

### Run 3 — after implementation, 2026-09-13

Runs 1 and 2 audited a design. This one audits **what was built against it**, which is the
only way two of the three MAJOR findings could ever be answered: both were
IMPLEMENTATION-DECISION-LEAKs, and a leak is closed by the decision being made explicitly,
not by the design saying more.

Read from `configs/policy.yaml` and from `public/data/dashboard.json` — never from another
document (rule 11). Findings below are added; **runs 1 and 2 are not edited**, because a
gate report is evidence of what was true when it ran.

| Finding | Run 2 | Run 3 |
|---|---|---|
| ARCH-GATE-002 — "money at stake" undefined | MAJOR, open | **CLOSED** |
| ARCH-GATE-004 — "structurally uncomparable" predicate undefined | MAJOR, open | **CLOSED** |
| ARCH-GATE-003 — INT-MEAS has no V1 delivery | MAJOR, open | **still open, and worse than recorded** |

#### ARCH-GATE-002 — closed

The operand is declared as policy rather than invented in code, and it is **published with
the figure**, which is what FR-122 and FR-123 actually require:

- `configs/policy.yaml:35` — `question_money_basis: window_revenue_at_shelf_price` , with
  the basis spelled out in a comment: *units sold in the window × current shelf price*
- `thresholds.owner_questions` in the artefact — `{limit: 3, money_basis:
  "window_revenue_at_shelf_price", yield_factor: 1.0}`
- every item in `capabilities.owner_questions.items` carries its own `money_basis`,
  `products_affected`, `money_at_stake`, `units_sold` and `window_id`

The `yield_factor: 1.0` is the finding's own observation implemented honestly: V1's only
question is `cost_price`, keyed per barcode, so yield is 1 for every question and FR-085's
product collapses to money at stake alone. The design does not pretend otherwise.

**What is closed is the leak, not the choice.** Whether `window_revenue_at_shelf_price` is
the *right* basis remains a product question — it is a declared, visible, changeable policy
line, which is exactly what this finding asked for. The gate does not adjudicate it.

#### ARCH-GATE-004 — closed, with a divergence to hand to the owner

- `configs/policy.yaml:42` — `uncomparable_min_barcode_digits: 8`
- `thresholds.competitor_position.uncomparable_min_barcode_digits: 8` in the artefact, so
  the rule in force is stated beside the count it produced
- `capabilities.competitor_position.counts` — `catalogue: 7583`,
  `structurally_uncomparable: 782`, `comparable_population: 6801` (and 7583 − 782 = 6801,
  so the arithmetic is internally consistent)

The predicate exists, is declared, and travels with its figure. Closed.

**But the number disagrees with the intent's, and someone should notice.** `intent.md` §9.4
commits to telling the owner that «**1,628 صنفاً في كتالوجه خدمات ورموز داخلية**» — car
washes, barista coffee, internal codes. The implemented predicate finds **782**, less than
half. One of the two is wrong: either a barcode-digit test under-counts services that carry
a plausible-looking code, or the 1,628 was a looser estimate than the sentence implies.

That is not an architecture defect and does not reopen this finding. It is a **figure the
team has committed to saying out loud on 12/9**, and rule 11 says it is quoted from the
artefact that produced it. Recorded for `smartshelf-pm`; belongs with the owner
conversation, not with this gate.

#### ARCH-GATE-003 — still open, and the ground moved under it

Run 2 recorded it as "the design removes the surface and builds nothing in its place". As
of 2026-09-13 that understates it: the surface was not removed, and it **stopped working
anyway**. `src/telemetry/` reads the frozen `operational.json`, joins on the pre-ADR-009 id
namespace, and reads the pre-V1 decision store — so PRD §8's 30-day go/no-go has had no
working instrument since the cut-over on 09-12. Evidence in `deployment.md` §Internal
telemetry page.

This also removes SPEC-000 §4's stated reason for never specifying INT-MEAS — *"already
measured by an existing surface"*. The surface is there and measures nothing, so the
justification does not hold and **F13 owes a spec**. The decision to rebuild rather than
delete was taken on 09-13 (P4-OQ-3).

**Verdict unchanged: CONDITIONAL PASS.** Zero blockers, **one** MAJOR open (ARCH-GATE-003),
down from three.

### Two things the peer review raised that neither run resolved

Recorded here rather than fixed, because both are judgement calls the team should take
deliberately:

1. **The rule does not obviously stop at two.** By ADR-014's own definition, hygiene is
   arguably three families — negative stock, no identifier, absent price — with three
   different actions, and the price column can go missing on its own. The design keeps them
   as three `variant`s inside one capability. That is defensible (they share an input and an
   action verb, *fix this record*) but it is a choice, and ADR-014 should say so rather than
   leave the reader to notice the rule was applied once and then stopped.
2. **`entry_id` has no episode dimension.** A record is fixed, later re-breaks, and the old
   `declined` outcome resurrects and suppresses a live finding. This is the same defect
   class as the four signals CLAUDE.md rule 12 was written about, and it will pass every
   unit test, because a test supplies one run. It affects SPEC-006 FR-114/OQ-605 and is
   worth a spec-layer question before the pilot accumulates outcomes.

*Run 2 changed `design.md` only. No intent, specification or source file was modified.*
