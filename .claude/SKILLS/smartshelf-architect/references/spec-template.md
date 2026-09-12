---
ID: F<#>-S<#>
Title: <feature name>
Status: Draft
Owner: smartshelf-architect
Version: 0.1 (<date>)
Parent: [F<#> — <feature name>](../intent.md)
Related Intents: INT-<###>
Inputs: [docs/features/F<#>-*/intent.md, docs/product/PRD.md, ADR-<NNN>, CLAUDE.md]
Answered by: [System Design](../../../architecture/system-design.md) §<n>
Updated: <date>
---

# F<#>-S<#> — <feature name>

> **This is the house structure. Sections 1–19 are fixed** — F1-S1 through F7-S1 all
> carry exactly these nineteen, in this order, with these names. The gate report, the
> System Design §21 and the implementation plan all navigate by them. Do not rename,
> reorder or drop one; write "None." under a section that does not apply. Sections 20
> and 21 are additions this project's CLAUDE.md rules require, and go at the end so the
> existing numbering is untouched.

> **Identifier note.** Every `FR-`, `INV-`, `NFR-`, `AC-`, `SCN-`, `C-`, `ASM-` and `OQ-`
> id below is globally unique across the whole specification layer. Check the layer before
> assigning a number. **Never renumber an existing id.**

Implements intent F<#>. Bound by ADR <numbers> and settled decisions D-<n>.

## 1. Purpose

<What this feature decides, surfaces or forbids, and what it must never claim. Three
sentences.>

## 2. Intent Traceability

- **INT-<###>** — "<the owner's sentence>"

## 3. Scope

Behavioural scope, not a file list. Which files change is declared by the implementation
plan task, never here.

### In Scope
- <…>

### Out of Scope
- <…, naming the spec that owns it instead, if any>

## 4. Actors and Triggers

| Actor | Trigger | Frequency |
|---|---|---|

## 5. Domain Terms

| Term | Definition |
|---|---|

## 6. Functional Requirements

**FR-<###>** — <requirement, in the present tense>

## 7. Behavioral Invariants

Honesty constraints live here, as `INV-` lines, never as prose. CLAUDE.md rule 8:
per-sale and one-off figures are never summed; a quantity-derived signal carries no
shekel figure; where a number cannot be stated honestly the surface shows **no number**,
not zero.

**INV-<###>** — <what must never happen, and what violating it would look like>

## 8. Behavioral Scenarios

**SCN-<###>** — Given <state>, when <event>, then <observable outcome>.

## 9. Inputs and Observable Outputs

| Input | Source | Required? |
|---|---|---|

| Output | Where it is observable |
|---|---|

## 10. State / Lifecycle Semantics

<What persists between runs, what is recomputed, what is never stored.>

## 11. Failure and Recovery Behavior

<What happens when an input is absent, stale or malformed. An empty result is a failure,
not a result (CLAUDE.md rule 10) — say which.>

## 12. Edge Cases

| Case | Behaviour |
|---|---|

## 13. Non-Functional Requirements

**NFR-<###>** — <requirement, countable>

## 14. Compatibility and External Constraints

**C-<###>** — <constraint from outside: data shape, platform, language, ADR>

## 15. Acceptance Criteria

House format — bold id, em dash, criterion, then the requirements it discharges in
italic parentheses:

**AC-<###>** — <testable criterion>. *(FR-<###>, INV-<###>)*

## 16. Assumptions

**ASM-<###>** — <what is assumed true, and what would falsify it>

## 17. Open Questions

**OQ-<###>** — <question> · owner: <who can answer> · blocks: <what>

## 18. Non-Goals

- <something a reader would reasonably expect and will not get>

## 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-<###> | FR-<###> | SCN-<###> | AC-<###> |
| Protected behavior | INV-<###> | — | AC-<###> |

---

## 20. Boundary Probe

CLAUDE.md rule 12. Name the test that proves this feature moves a real recommendation
when its input is present — the one that crosses the real path (`src/engine/inputs.py` →
`run.py` → the publisher, as the implementation plan defines it) rather than handing a
function its argument. A unit test cannot discharge this.

`src/engine/` holds Phase 0 only today — `model.py`, `policy.py`, `registry.py`.
`inputs.py` and `run.py` arrive with Phase 1, so a spec landing before then must name the
probe it *will* use and say the path does not exist yet, rather than implying it does.

| Probe | What it would catch | Where it runs |
|---|---|---|
| `npm run check:signals` (exists) / `scripts/check_independence.py` (planned — plan Task 1.9) / <named probe> |  | `collect-daily.yml` |

## 21. Claim Limits

CLAUDE.md rule 13. What this feature must **not** claim, given that the sales reports are
monthly and cover 24.3% of the catalogue. Distinguish the two verdicts explicitly —
they are not the same finding.

| Claim | Verdict | Why |
|---|---|---|
|  | not measurable / measured and not significant |  |

## 22. Unmapped PRD Acceptance Lines

<Any PRD acceptance line with this F# that this spec does not satisfy. Empty is fine.
Silence is not.>
