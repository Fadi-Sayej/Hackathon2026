---
ID: ADR-001
Title: One rule engine, in Python; the browser computes no business rule
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: F7-S1 (FR-121, FR-125, INV-065, NFR-061/062); every feature spec's determinism NFR
---

# ADR-001 — One rule engine, in Python; the browser computes no business rule

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

Three implementations of the price rule disagree; money is derived in the
browser; reproduction runs a fourth path over the raw CSV (§3.4).

## Related Specs

SPEC-007 FR-121, FR-125, INV-065, NFR-061/062; every capability's determinism NFR.

## Decision

All V1 rules live in `src/engine/` as pure functions; the browser holds one
pure selection function and no arithmetic over money or quantities.

## Rationale

INV-065 cannot hold with two implementations; Python already owns the
data infrastructure, matching and 324 tests; the owner-state round trip must reach the
rules, which are therefore server-side by necessity.

## Alternatives Considered

(1) Engine in JS in the browser over shipped raw data — colocates owner
state with rules, but rewrites matching and the collectors' consumers, ships the whole
silver set to the client, and makes reproduction "open the app". (2) Keep the split and
add a conformance test — a test cannot make two rule bodies one.

## Trade-offs

Answers take effect at the next run, not instantly (AC-084 permits
"next production").

## Consequences

`actionPriority.js`, `reorderEngine.js` and
`print_figures.py` lose their rule content.

## Reversibility

Difficult.
