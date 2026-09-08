---
ID: ADR-007
Title: Static site, nightly CI, no runtime server; V2/V4 and AI code leave the V1 build
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: D-12, D-13; PRD §5 (a two-person team)
---

# ADR-007 — Static site, nightly CI, no runtime server; V2/V4 and AI code leave the V1 build

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Related Specs

D-12, D-13; PRD §5 (a two-person team)

## Context

D-12, D-13, a two-person team, a 4.36 MB bundle of demo data and unspecified engines.

## Decision

The V1 app routes only to the daily page, five capability pages, questions,
receiving capture and the data page; the demo spine, browser engines, planogram, LLM
layer, telemetry entry, browser POS connectors, dead scripts and the `code/` and
`SmartShelf AI/` copies are removed from the tree at the end of Phase 4 under a git tag.

## Rationale

Every component must be justified by a spec, an immutable constraint or a
necessary property; none of these is.

## Alternatives Considered

Keep them routed but hidden —
they would keep being linted, tested, bundled and mistaken for product. **Trade-offs:**
V2/V4 revival is a conscious act (tag + design), not a flag flip. **Reversibility:**
Easy (git).
