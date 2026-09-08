---
ID: ADR-006
Title: Surface composition is a pure browser function over engine candidates
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: F6-S1 (FR-100 … FR-108, NFR-053); F7-S1 (INV-065)
---

# ADR-006 — Surface composition is a pure browser function over engine candidates

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

Admission depends on outcomes the browser owns; the bound and allocation are
selection, not computation.

## Related Specs

SPEC-006 FR-100 … FR-108, NFR-053; SPEC-007 INV-065.

## Decision

Engine stamps `actionable` for FR-103 conditions 1, 2 and 4 and publishes
ordered full sets; `compose.js` applies condition 3, the stated allocation
(`unvalued_places`, provisional 3 of 10), one-place-per-product precedence and the bound.

## Rationale

Composition produces no figure, so INV-065 is untouched; putting it in the
engine would require a browser-side re-composition anyway to honour an outcome recorded
minutes ago (SCN-104).

## Alternatives Considered

Engine composes and the browser only filters — the filter reopens
places, which is composition again.

## Reversibility

Easy.
