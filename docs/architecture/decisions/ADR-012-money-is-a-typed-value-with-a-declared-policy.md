---
ID: ADR-012
Title: Money is a typed value with a declared per-capability policy
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: D-1, D-2, D-11; F6-S1 (FR-104 … FR-106, FR-111, FR-116)
---

# ADR-012 — Money is a typed value with a declared per-capability policy

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

§3.4-2.

## Related Specs

D-1, D-2, D-11; SPEC-006 FR-104 … FR-106, FR-111, FR-116.

## Decision

`Value{amount, kind, certainty}`; registry declares `value_policy`; the
publisher asserts; `value_kinds_present` is derived and published; no total is rendered
anywhere in V1 (the existing "per sale at stake" sum is dropped — OQ-104 notes it is not
a realisable amount, and FR-116 permits summaries only with separation, which a single
kind makes trivially true but which nothing requires).

## Reversibility

Easy.
