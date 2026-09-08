---
ID: ADR-002
Title: Reproduction is the engine in print mode
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: F7-S1 (FR-124 … FR-127, NFR-060, NFR-062, NFR-063, C-61); SPEC-GAPS GAP-005
---

# ADR-002 — Reproduction is the engine in print mode

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

`npm run figures` is a separate script with its own constants.

## Related Specs

SPEC-007 FR-124 … FR-127, NFR-060, NFR-062, NFR-063, C-61; GAP-005.

## Decision

`scripts/figures.py` = `run_engine.py --print`; the figure registry is the
same object the artefact publishes; intermediate outputs are content-addressed so a fresh
clone reproduces everything from committed inputs.

## Alternatives Considered

Keep a lightweight reader over the artefact (fast, but reads a
recorded value — FR-125 forbids).

## Trade-offs

First run on a clone is slower.

## Reversibility

Easy.
