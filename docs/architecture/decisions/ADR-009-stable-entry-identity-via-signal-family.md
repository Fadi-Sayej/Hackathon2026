---
ID: ADR-009
Title: Entry identity is stable and legacy outcome ids are translated once
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: F6-S1 (FR-115, C-50); F1-S1 (C-4); F2-S1 (C-13)
---

# ADR-009 — Entry identity is stable and legacy outcome ids are translated once

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

Outcomes are keyed to `recommendation_id = sha256(barcode|type…)`.

## Related Specs

SPEC-006 FR-115, C-50; SPEC-001 C-4; SPEC-002 C-13.

## Decision

`entry_id = sha256(signal_family ‖ barcode ‖ variant)[:16]`, independent of
thresholds, of the run, **and of the capability taxonomy**. `signal_family` is a permanent
string enumerated in §10.1, fixed once and never renamed or reused; the routing
`capability` id travels beside it as a mutable field. Hashing the capability id instead
would make a presentation label load-bearing on durable owner decisions: any later
re-carving — hygiene splitting out, idle merging in, a module renamed — would orphan every
recorded outcome in Firestore, and it would fail *silently*, because unmatched keys simply
stop suppressing entries the owner already declined. On first load after cut-over,
`ownerState.js` maps legacy ids by
`(legacy type → capability, barcode)` from the last `operational.json` it can still fetch
and rewrites them; the mapping runs once and is then deleted (no permanent adapter).

## Reversibility

Easy.
