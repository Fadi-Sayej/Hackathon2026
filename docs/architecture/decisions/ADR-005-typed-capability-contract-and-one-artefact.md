---
ID: ADR-005
Title: A typed capability contract and one schema-validated artefact
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: F6-S1 (FR-117, FR-118, INV-057); F7-S1 (FR-120, FR-123, FR-128, FR-129); D-3
---

# ADR-005 — A typed capability contract and one schema-validated artefact

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

A missing directory is indistinguishable from "found nothing".

## Related Specs

SPEC-006 FR-117, FR-118, INV-057; SPEC-007 FR-120, FR-123, FR-128, FR-129; D-3.

## Decision

`CapabilityOutput` with explicit `status`; `dashboard.json` schema v2 with
`vintages`, `thresholds`, `value_kinds_present`, `figures`; publisher refuses on any
missing status or money-policy breach; atomic write. `operational.json` and
`sources.json` retire after the browser cut-over.

## Alternatives Considered

Extend `operational.json` in place — keeps `posHealth`/`byType` shapes
that encode zero-for-missing.

## Reversibility

Moderate (schema is a contract).
