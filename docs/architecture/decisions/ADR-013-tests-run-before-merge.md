---
ID: ADR-013
Title: Tests run before merge
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: —  (engineering practice; no spec prescribes it)
---

# ADR-013 — Tests run before merge

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Related Specs

—  (engineering practice; no spec prescribes it)

## Context

851 tests, none run by CI.

## Decision

`ci.yml` on push/PR (lint, vitest,
pytest, contract, build).

## Reversibility

Easy.
