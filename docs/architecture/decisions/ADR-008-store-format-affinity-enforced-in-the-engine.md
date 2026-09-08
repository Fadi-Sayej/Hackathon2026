---
ID: ADR-008
Title: Store-format affinity is enforced in the engine, under the balanced reference
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: F3-S1 (FR-040 … FR-044c, C-20 … C-22, INV-020 … INV-022, INV-026)
---

# ADR-008 — Store-format affinity is enforced in the engine, under the balanced reference

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

The protected behaviour is enforced only in JS over a stale generated file.

## Related Specs

SPEC-003 FR-040 … FR-044c, C-20 … C-22, INV-020 … INV-022, INV-026.

## Decision

`inputs.py` drops affinity-0 stores before any capability sees them; the
client's own venue is dropped as a reference (D-5); comparable (≥ floor) sources supply
the same-format price, context-only sources supply the supermarket price, and the
reference is their midpoint or supermarket + measured allowance. `storeFormat.js` is
retired; `store_types.py` is the single implementation.

## Reversibility

Easy.
