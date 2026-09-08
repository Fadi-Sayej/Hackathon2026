# Documentation Architecture Migration Report

**Date:** 2026-09-08 · **Scope:** structural reshaping of the product/design documentation only
**Branch:** `implementation-plan`

---

## 1. Result

## MIGRATION COMPLETE

The repository now has exactly one canonical source per artifact type, arranged as
PRD → Feature Intents → Feature Specs → System Design + ADRs → Implementation Plan.
Every approved requirement identifier survived unchanged. No product or architecture
semantics were altered.

Two things were **not** done, deliberately, because they are not structural acts and the
brief forbids them: the stale implementation plan was flagged rather than rewritten, and
the three MAJOR findings still open in the readiness gate were left open.

---

## 2. Old → New Mapping

### Product and specification layer

| Old Path | New Path | Action | Notes |
|---|---|---|---|
| `intent.md` §1, §8–§13 | `docs/product/PRD.md` | **SPLIT** | Project-level half: feature register, releases, not-in-scope, owner commitments, decision criterion, figures, open decisions. Text verbatim |
| `intent.md` §2 | `docs/features/F1-delivery-price-consistency/intent.md` | **SPLIT** | INT-001 |
| `intent.md` §2ب | `docs/features/F2-stock-truth/intent.md` | **SPLIT** | INT-002 + INT-002B |
| `intent.md` §3, §3ب, §3ج | `docs/features/F3-competitor-price-position/intent.md` | **SPLIT** | INT-003 |
| `intent.md` §4, §4ب | `docs/features/F4-catalogue-lifecycle/intent.md` | **SPLIT** | INT-009 |
| `intent.md` §5 | `docs/features/F5-owner-knowledge-capture/intent.md` | **SPLIT** | INT-010 |
| `intent.md` preamble («النجم الثابت») | `docs/features/F6-daily-action-surface/intent.md` | **SPLIT** | INT-NS — thin; see §6 |
| `intent.md` §12 | `docs/features/F7-figure-provenance/intent.md` | **SPLIT** | INT-PROV (also cited in PRD §9) |
| `intent.md` §6 | `docs/features/F8-order-quantity/intent.md`, `F9-assortment-gap/intent.md` | **SPLIT** | INT-004, INT-005 — one source section serves two features; reproduced in both because it is the only intent text either has |
| `intent.md` §7 | `docs/features/F10-expiry-bounded-ordering/intent.md` | **SPLIT** | INT-007 |
| `intent.md` §1 row | `docs/features/F11-supplier-lead-times/intent.md` | **SPLIT** | INT-008 — row only; see §6 |
| `intent.md` §1 row + §9.7 | `docs/features/F12-planogram/intent.md` | **SPLIT** | INT-006 |
| `intent.md` §11 | `docs/features/F13-pilot-measurement/intent.md` | **SPLIT** | INT-MEAS (also PRD §8) |
| `intent.md` (whole file) | — | **REMOVED** | Every section relocated above; history is in git |
| `specs.md` SPEC-000 | `docs/product/intent-register.md` | **MOVE** | Verbatim. Holds D-1 … D-13 |
| `specs.md` SPEC-001 | `docs/features/F1-delivery-price-consistency/specs/F1-S1-delivery-price-consistency.md` | **SPLIT** | Verbatim body |
| `specs.md` SPEC-002 | `docs/features/F2-stock-truth/specs/F2-S1-stock-reconciliation-and-hygiene.md` | **SPLIT** | Verbatim body — **not** split into two, see §6 |
| `specs.md` SPEC-003 | `docs/features/F3-competitor-price-position/specs/F3-S1-competitor-price-position.md` | **SPLIT** | Verbatim body |
| `specs.md` SPEC-004 | `docs/features/F4-catalogue-lifecycle/specs/F4-S1-catalogue-lifecycle.md` | **SPLIT** | Verbatim body |
| `specs.md` SPEC-005 | `docs/features/F5-owner-knowledge-capture/specs/F5-S1-owner-knowledge-capture.md` | **SPLIT** | Verbatim body |
| `specs.md` SPEC-006 | `docs/features/F6-daily-action-surface/specs/F6-S1-daily-action-surface.md` | **SPLIT** | Verbatim body |
| `specs.md` SPEC-007 | `docs/features/F7-figure-provenance/specs/F7-S1-figure-provenance.md` | **SPLIT** | Verbatim body |
| `specs.md` SPEC-GAPS | `docs/features/gaps-and-open-questions.md` | **MOVE** | Cross-feature, so it sits at the feature layer's root |
| `specs.md` (whole file) | — | **REMOVED** | Every section relocated above; history is in git |

### Architecture layer

| Old Path | New Path | Action | Notes |
|---|---|---|---|
| `design.md` | `docs/architecture/system-design.md` | **MOVE** (`git mv`) | v1.1, unchanged except §19 and three link fixes |
| `design.md` §19 ADR-001 … ADR-014 | `docs/architecture/decisions/ADR-0NN-*.md` | **SPLIT** | 14 files. Each already had Context / Decision / Rationale / Alternatives / Trade-offs / Consequences / Reversibility; those inline labels became headings. §19 is now an index table |
| `ARCHITECTURE.md` | `docs/archive/ARCHITECTURE.md` | **ARCHIVE** | Pre-design current-state trace; superseded by System Design §3. `LEGACY` banner added |

### Reviews and plan

| Old Path | New Path | Action | Notes |
|---|---|---|---|
| `reviews/intent-spec-conformance.md` | `docs/reviews/intent-spec-conformance.md` | **MOVE** | Verdict untouched; a path-note table added above §1 |
| `reviews/system-design-readiness.md` | `docs/reviews/system-design-readiness.md` | **MOVE** | Verdict untouched; a path-note table added above §1 |
| `docs/superpowers/plans/2026-09-08-v1-00-index.md` | `docs/implementation/plan.md` | **RENAME** | Canonical plan; metadata header + staleness note added |
| `docs/superpowers/plans/2026-09-08-v1-01-foundations.md` | `docs/implementation/phase-0-foundations.md` | **RENAME** | |
| `docs/superpowers/plans/2026-09-08-v1-02-capabilities.md` | `docs/implementation/phase-1-capabilities.md` | **RENAME** | |
| `docs/superpowers/plans/2026-08-13-t7-receiving-ledger.md` | `docs/archive/plans/2026-08-13-t7-receiving-ledger.md` | **ARCHIVE** | Pre-design plan |

### Superseded product documents

| Old Path | New Path | Action | Superseded by |
|---|---|---|---|
| `docs/archive/PRODUCT_REQUIREMENTS.md` | `docs/archive/pre-pivot/PRODUCT_REQUIREMENTS.md` | **SUPERSEDE** | `docs/product/PRD.md` |
| `docs/BUSINESS_CASE.md` | `docs/archive/pre-pivot/BUSINESS_CASE.md` | **SUPERSEDE** | `docs/product/PRD.md` |
| `docs/PILOT_PLAN.md` | `docs/archive/pre-pivot/PILOT_PLAN.md` | **SUPERSEDE** | `docs/product/PRD.md` §5, §7, §8 |
| `docs/ACCEPTANCE_CRITERIA.md` | `docs/archive/pre-pivot/ACCEPTANCE_CRITERIA.md` | **SUPERSEDE** | the `AC-…` criteria in each feature spec §15 |
| `docs/MOCKS_AND_ASSUMPTIONS.md` | `docs/archive/pre-pivot/MOCKS_AND_ASSUMPTIONS.md` | **SUPERSEDE** | SPEC-GAPS Part 3 |
| `docs/archive/*.md` (27 legacy files) | same paths | **LEAVE** + banner | `LEGACY — NON-AUTHORITATIVE` banner added to each |

### New files

| New Path | Purpose |
|---|---|
| `docs/README.md` | Canonical documentation map and authority hierarchy |
| `docs/product/PRD.md` | Assembled from `intent.md`'s project-level sections |
| `docs/reviews/documentation-structure-migration.md` | This report |

### Left in place (not product authority, not competing with it)

`docs/DEPLOYMENT.md`, `HANDOVER_YOMYOM.md`, `HANDOVER_YOMYOM_AR.md`, `RECEIVING_LEDGER.md`,
`SNAPSHOT_DURABILITY.md`, `YOMYOM_QUESTIONS.md`, `QA_CHECKLIST.md`, `DATASET_SELECTION.md`,
`DEMO_*`, `DO_NOT_SAY.md`, `FINAL_*`, `JUDGE_QA.md`, `SAFE_DEMO_FLOW.md`, `docs/sources/`.
Operational and demo material. **LEAVE** — listed in `docs/README.md` as outside the chain.

---

## 3. Feature Map

| Feature ID | Feature | Intent IDs | Intent | Specs | Release |
|---|---|---|---|---|---|
| **F1** | Delivery-Platform Price Consistency | INT-001 | `features/F1-delivery-price-consistency/intent.md` | `F1-S1` (was SPEC-001) | V1 |
| **F2** | Stock Truth | INT-002, INT-002B | `features/F2-stock-truth/intent.md` | `F2-S1` (was SPEC-002) | V1 |
| **F3** | Competitor Price Position | INT-003 | `features/F3-competitor-price-position/intent.md` | `F3-S1` (was SPEC-003) | V1 |
| **F4** | Catalogue Lifecycle | INT-009 | `features/F4-catalogue-lifecycle/intent.md` | `F4-S1` (was SPEC-004) | V1 |
| **F5** | Owner Knowledge Capture | INT-010 | `features/F5-owner-knowledge-capture/intent.md` | `F5-S1` (was SPEC-005) | V1 |
| **F6** | Daily Action Surface | INT-NS | `features/F6-daily-action-surface/intent.md` | `F6-S1` (was SPEC-006) | V1 |
| **F7** | Figure Provenance and Reproducibility | INT-PROV | `features/F7-figure-provenance/intent.md` | `F7-S1` (was SPEC-007) | V1 |
| **F8** | Order Quantity | INT-004 | `features/F8-order-quantity/intent.md` | — | V2 |
| **F9** | Assortment Gap | INT-005 | `features/F9-assortment-gap/intent.md` | — | V2 |
| **F10** | Expiry-Bounded Ordering | INT-007 | `features/F10-expiry-bounded-ordering/intent.md` | — | V2 |
| **F11** | Supplier Lead Times | INT-008 | `features/F11-supplier-lead-times/intent.md` | — | V3 |
| **F12** | Planogram | INT-006 | `features/F12-planogram/intent.md` | — | V4 |
| **F13** | Pilot Measurement | INT-MEAS | `features/F13-pilot-measurement/intent.md` | — | V1, unspecified |

**Feature ids were assigned to the intents that already existed.** No feature was invented,
merged or dropped: the 13 features are exactly the 14 registered intent ids of SPEC-000 §1,
with INT-002 and INT-002B sharing F2 because a single specification (SPEC-002) already
served both and the intent register lists them as two rows of one question.

**Specs per feature: one each.** The `F#-S#` scheme supports several, but the approved
specification layer contains exactly one specification per feature. Creating `F2-S2` by
cutting SPEC-002 in half would have been a semantic act (its §7 invariants, §16 assumptions
and §19 matrix span both halves) and was not done — see §6.

---

## 4. Canonical Artifacts

**PRD:** `docs/product/PRD.md`
*Supporting:* `docs/product/intent-register.md` (SPEC-000 — the settled decisions D-1 … D-13)

**Feature Intents:** `docs/features/F#-<name>/intent.md` — 13 files

**Feature Specs:** `docs/features/F#-<name>/specs/F#-S#-<name>.md` — 7 files
*Cross-feature:* `docs/features/gaps-and-open-questions.md` (SPEC-GAPS)

**System Design:** `docs/architecture/system-design.md` — v1.1, the only design authority

**ADR directory:** `docs/architecture/decisions/` — ADR-001 … ADR-014

**Review directory:** `docs/reviews/` — `intent-spec-conformance.md`,
`system-design-readiness.md`, `documentation-structure-migration.md`

**Implementation Plan:** `docs/implementation/plan.md` — Phase 0 and Phase 1 written,
Phases 2–4 marked **NOT YET CREATED**

**Documentation map:** `docs/README.md`

---

## 5. Archived / Superseded Artifacts

**Archived with a `LEGACY — NON-AUTHORITATIVE` banner:**

- `docs/archive/ARCHITECTURE.md` — pre-design current-state trace
- `docs/archive/plans/2026-08-13-t7-receiving-ledger.md` — pre-design implementation plan
- `docs/archive/pre-pivot/` — `PRODUCT_REQUIREMENTS.md`, `BUSINESS_CASE.md`, `PILOT_PLAN.md`,
  `ACCEPTANCE_CRITERIA.md`, `MOCKS_AND_ASSUMPTIONS.md`
- `docs/archive/*.md` — the 27 pre-existing legacy files (`TECH_*`, `SPRINT*`, `SAAS_*`,
  `UI_DATA_CONTRACT`, `RECOMMENDATION_FAMILIES`, `PLANOGRAM_ROADMAP`, per-person notes…)

**Removed from the working tree (content fully relocated; history in git):**

- `intent.md` → PRD + 13 feature intents
- `specs.md` → intent register + 7 feature specs + gaps register

There is no file outside `docs/product/`, `docs/features/` or `docs/architecture/` that
could be mistaken for current PRD, spec or design authority.

---

## 6. Unresolved Structural Ambiguities

Recorded, **not** resolved by guessing.

**6.1 — SPEC-002 serves two intents and was left whole.**
INT-002 (reconciliation) and INT-002B (data hygiene) are two rows of the intent register
served by one specification. They are placed under one feature, F2, with one spec `F2-S1`.
Splitting into `F2-S1`/`F2-S2` would require deciding which invariants, assumptions and
acceptance criteria belong to which half — a semantic act. Note the downstream tension:
the System Design's ADR-014 answers this one spec with **two** capabilities, because the
halves fail independently. That is a legitimate design-layer decision and does not oblige
the spec layer to split; it is flagged here so nobody later "fixes" the asymmetry silently.

**6.2 — F6 and F7 have thin intent documents.**
INT-NS lived in `intent.md` as a one-line preamble and INT-PROV as a boxed warning in §12.
Both are cross-cutting rules that SPEC-000 §1 deliberately registered as intents in their
own right. Their intent documents are correspondingly short. **Nothing was invented to
fill them.** Their requirement detail is in `F6-S1` and `F7-S1`.

**6.3 — F11's intent content is a single table row.**
INT-008 (supplier lead times) has no narrative section anywhere in the approved intent
layer. Its intent document reproduces the row and stops.

**6.4 — `intent.md` §6 is the only source for two features.**
It states the input ordering for both INT-004 and INT-005. Rather than pick one owner, the
section is reproduced in F8 and F9, each pointing at the other as a sibling. This is the
one place the migration duplicated text, and it is duplicated because it is the *only*
intent text either feature has.

**6.5 — The `docs/*.md` demo/operational set was left in place.**
`DEMO_*`, `JUDGE_QA`, `DO_NOT_SAY`, `FINAL_*`, `SAFE_DEMO_FLOW`, `QA_CHECKLIST`,
`DATASET_SELECTION` are hackathon-era but are not product, spec or design authority, so
archiving them was outside this migration's remit. They are listed in `docs/README.md`
under "Operational documents (not product authority)". A later cleanup may archive them.

**6.6 — The implementation plan is stale against System Design v1.1.**
`docs/implementation/plan.md` was written against v1.0. ADR-009 and ADR-014 changed the
`entry_id` formula and the capability registry after it was written. A staleness banner was
added; **the plan's content was not rewritten**, because refreshing a plan is a planning
act, not a structural one. It must be refreshed before Phase 0 executes.

**6.7 — Phases 2–4 of the plan do not exist.**
The index references five phases; two files exist. Marked **NOT YET CREATED**. No tasks
were generated, per the brief.

---

## 7. Traceability Check

| Check | Result |
|---|---|
| Intents without a PRD relation | **0** — every feature intent carries `Parent: PRD` and appears in PRD §3 |
| Specs without an Intent | **0** — every `F#-S#` carries `Parent` + `Related Intents` in frontmatter |
| Approved specs lost | **0** — SPEC-000 … SPEC-007 and SPEC-GAPS all relocated; verified by identifier count below |
| Requirement identifiers renumbered | **0** — `FR-…`, `INV-…`, `NFR-…`, `AC-…`, `SCN-…`, `C-…`, `ASM-…`, `OQ-…`, `GAP-…`, `D-…` are unchanged |
| System Design sections without a spec relation | The design's §21 traceability matrix is intact and unmodified; it maps every FR/INV/NFR/AC to a design element |
| ADRs without architectural justification | **0** — all 14 were already established decisions in §19 with context, alternatives and trade-offs. **No ADR was invented** |
| ADRs acting as product requirements | **0** — checked; each records a *how*, not a *what* |
| Broken documentation links | **0** — full relative-link scan across `docs/**`, `CLAUDE.md`, `README.md` |
| Two files claiming the same authority | **0** — one PRD, one System Design, one plan; every legacy file banner-marked |

**Traceability now supported end to end:**

```
docs/product/PRD.md §3
  → docs/features/F1-delivery-price-consistency/intent.md   (INT-001)
    → .../specs/F1-S1-delivery-price-consistency.md  FR-004
      → docs/architecture/system-design.md §21 (E price_consistency, ceiling derivation)
        → docs/architecture/decisions/ADR-001-one-rule-engine-in-python.md
          → docs/implementation/phase-1-capabilities.md (task 1a)
            → src/engine/price_consistency.py + tests/acceptance/  (not yet written)
```

The last hop is honestly empty: no implementation exists yet, and no downstream link was
fabricated.

---

## 8. Semantic Change Check

**No intentional semantic changes were made.**

Every product, specification and architecture statement was moved verbatim. What changed:

| Change | Why it is not semantic |
|---|---|
| Section text redistributed across files | Same words, different files |
| `## SPEC-00N — X` promoted to `# F#-S# — X` | Heading level and id prefix; the spec's own body is untouched |
| YAML frontmatter added to new/moved documents | Metadata (`ID`, `Status`, `Parent`, `Related Intents`); asserts no new requirement |
| Inline `**Context:** …` in ADRs became `## Context` | Formatting of an existing labelled run |
| §19 of the System Design replaced by an index table | The 14 ADRs it contained now live one per file, unchanged |
| Documentation links repointed | Path correction after the move |
| `LEGACY` banners on archive files | Status marking; adds no requirement |
| Staleness note on the implementation plan | Status marking; the plan's own content is untouched |
| `F#` feature ids assigned | Labels over the existing `INT-…` ids. The `INT-…` ids remain primary and are unchanged |
| F6's north-star line rendered as a blockquote | Same words; `**النجم الثابت:** …` was a bold line in the preamble and is now inside `> `. F6's intent also adds one paragraph explaining *why* INT-NS is registered as an intent in its own right — that explanation is quoted from SPEC-000 §1, not written for this migration |
| F8/F9 and F10 intents carry a "direction only" heading | Labels the status of content the intent layer already describes as an ordering of inputs rather than a rule (SPEC-GAPS GAP-008 says so). No requirement added |

**Fidelity verification performed:**

| Check | Result |
|---|---|
| Requirement identifiers in the specification layer before vs after | FR 124→124 · INV 46→46 · NFR 24→24 · AC 90→90 · OQ 40→40 — **0 lost** |
| Requirement identifiers cited by the System Design before vs after | FR 121→121 · INV 46→46 · NFR 23→23 · AC 90→90 — **0 lost** |
| Spec bodies found verbatim inside the pre-migration `specs.md` | 7 / 7 |
| Intent sections found verbatim inside the pre-migration `intent.md` | 9 / 9 with narrative content (F11, F12 are table rows) |
| Words of `design.md` §19 present in the 14 extracted ADR files | all but the section heading "19 Architecture Decisions", which stays in the design as the index heading — **0 content words lost** |
| Broken documentation links across `docs/**`, `CLAUDE.md`, `README.md` | **0** |
| Source files, tests, configs or workflows modified | **0** |

**Pre-existing contradictions preserved, not fixed:**

1. **The implementation plan contradicts System Design v1.1** on `entry_id` and the
   capability registry (§6.6). Flagged, not corrected.
2. **ARCH-GATE-002, ARCH-GATE-003, ARCH-GATE-004** remain open MAJOR findings in the
   readiness gate. The migration did not touch them; ARCH-GATE-003 in particular is
   restated inside `features/F13-pilot-measurement/intent.md` so it is visible where the
   feature lives.
3. **Nineteen P1 open questions** in SPEC-GAPS remain open. None was answered.
4. **The archived pre-pivot documents contradict D-12** (three-store pilot vs single
   store). They were banner-marked, not edited.
