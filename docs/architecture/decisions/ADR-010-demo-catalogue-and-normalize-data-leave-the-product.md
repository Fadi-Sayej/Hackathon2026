---
ID: ADR-010
Title: The generated demo catalogue and `normalize:data` leave the product
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: ARCH-DRIVER-001; F7-S1 (FR-125); D-12
---

# ADR-010 — The generated demo catalogue and `normalize:data` leave the product

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

Rule 7's overwrite hazard; a second copy of the truth in the bundle.

## Related Specs

ARCH-DRIVER-001; SPEC-007 FR-125; D-12.

## Decision

The artefact is the only bridge from pipeline to browser. **Consequence:**
V2's reorder capability, when designed, is an engine module publishing entries — not a
browser engine over a generated module.

## Reversibility

Easy.
