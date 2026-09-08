---
ID: ADR-011
Title: Evidence semantics: `no_row` is recorded, and classification states it
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: F4-S1 (ASM-030, INV-036, FR-063a, FR-076); CLAUDE.md rule 13; SPEC-GAPS GAP-009
---

# ADR-011 — Evidence semantics: `no_row` is recorded, and classification states it

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

GAP-009 — 5,848 classifications rest on absence of a row.

## Related Specs

SPEC-004 ASM-030, INV-036, FR-063a, FR-076; CLAUDE.md rule 13.

## Decision

`EvidenceState ∈ {observed_units, observed_zero, no_row}` is computed per
product; classification follows ASM-030 (`no_row` within the window counts as dead) but
every withdrawn entry and every dead count carries the evidence state and the window, so
the surface says "no sales row in 7 monthly reports (Jan–Jul 2026)", never "zero sales".
The owner check that GAP-009 names is a release condition, not a code path.

## Reversibility

Easy.
