---
ID: ADR-014
Title: A capability is the smallest independently-unavailable unit; data hygiene is one
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: F2-S1 (§11, FR-028 … FR-030); F6-S1 (FR-107, FR-117, INV-057); SPEC-000 (INT-002 vs INT-002B)
---

# ADR-014 — A capability is the smallest independently-unavailable unit; data hygiene is one

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

Version 1.0 of this document used "capability" to mean seven things at once —
a specification, a Python module, an availability status, a registry entry with a value
policy, a badge, a page, and a slot in the surface's precedence order — and enumerated the
set extensionally. It could then give no answer to a membership question, and it gave two:
§7.3/§10.2/§11.2/§11.4 treated data hygiene as a characterisation inside `reconciliation`,
while §9.2/§13/§14/§21/§22.2/§7.4 gave it a badge, a value policy, a precedence slot and a
page. The implementation-readiness gate raised this as its only blocker
(`reviews/system-design-readiness.md`, ARCH-GATE-001).

## Related Specs

SPEC-002 §11 ("the detection signal is unavailable … hygiene signals are
unaffected"), FR-028 … FR-030; SPEC-006 FR-107, FR-117, INV-057; SPEC-000 INT-002 vs
INT-002B.

## Decision

define the term intensionally — **a capability is the smallest unit that can
independently become unavailable** — and register data hygiene as its own capability
(`hygiene`), with its own id, `requires`, computed `status`, `value_policy: none`, badge,
page and precedence slot. `status` is derived from `requires` against the inputs that
landed, never hand-declared. `capabilities{}` holds exactly the registry ids, so
`catalogue_lifecycle` and `owner_questions` move inside it and gain a `status` they lacked.

## Rationale

availability is the only one of the seven roles forced by the world rather
than chosen — the inventory CSV arrives, the seven monthly sales reports may not. Reasoning
from badges and nav counts upward produced the contradiction; reasoning from input
dependency downward resolves it mechanically, and resolves `catalogue_lifecycle`'s missing
status by the same rule rather than as a second patch.

## Alternatives Considered

(1) A per-signal-family sub-status inside one `CapabilityOutput` —
duplicates the availability machinery at every consumer (`compose`, the INV-057 gate, the
badge, the full-list page), invents a "half unavailable" rendering the surface has no
vocabulary for, and has to be written again for every V2 capability whose inputs land
separately. (2) `counts: None` for the detection half — renders `reconciliation` as
available-with-nothing, which is exactly what INV-057 forbids.

## Trade-offs

SPEC → capability is no longer 1:1; `CapabilityOutput.spec` is explicitly
many-to-one. A Python module may return several outputs. The surface gains one more
unvalued capability competing for three reserved places, which is why §9.2 states the
order and `configs/policy.yaml` holds it.

## Consequences

the contract sections and the behaviour sections now say the same thing;
the rule-12 independence probe (§14, §18) is what proves it.

## Reversibility

easy, and
now cheap — ADR-009 removed the capability id from `entry_id`, so a later re-carving no
longer orphans recorded outcomes.
*Decided 2026-09-08 by a five-advisor council with anonymous peer review; the council was
unanimous for the split and all five reviewers ranked the input-dependency argument
strongest. The `signal_family` precondition in ADR-009 came from the same session.*
