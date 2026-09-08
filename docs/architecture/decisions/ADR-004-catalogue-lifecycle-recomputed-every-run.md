---
ID: ADR-004
Title: Catalogue lifecycle is recomputed every run; the engine owns no persistent state
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: F4-S1 (FR-060a, FR-063c, FR-065 … FR-067, INV-031, INV-032, §10)
---

# ADR-004 — Catalogue lifecycle is recomputed every run; the engine owns no persistent state

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

SPEC-004 §10 calls withdrawal a lifecycle state.

## Related Specs

SPEC-004 FR-060a, FR-063c, FR-065 … FR-067, INV-031, INV-032, §10 (interruption).

## Decision

`withdrawn` = f(evidence window, recorded stock, owner revivals). No stored
withdrawal set. Manual revivals are owner state with a `window_id`.

## Rationale

FR-060a already demands re-evaluation per ingestion; storing the set only
creates a second truth and an interruption problem.

## Alternatives Considered

A committed
`catalogue_state.json` with transitions — more code, same result, plus drift.

## Trade-offs

"The withdrawal is not repeated" (SCN-064b) is expressed as "the entry is
simply not withdrawn", with the previous run's artefact as the only history; OQ-704
(reproduction history) stays open.

## Reversibility

Easy.
