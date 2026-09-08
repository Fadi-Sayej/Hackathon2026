---
ID: ADR-003
Title: Owner state lives in Firestore, written only by the browser, pulled by the engine
Status: Accepted
Date: 2026-09-08
Parent: [System Design](../system-design.md) §19
Related Specs: F5-S1 (FR-087, FR-088, FR-093, NFR-042); F6-S1 (FR-113 … FR-115, NFR-052); F13 (INT-MEAS)
---

# ADR-003 — Owner state lives in Firestore, written only by the browser, pulled by the engine

**Status:** Accepted · **Recorded in:** [System Design](../system-design.md) §19

## Context

Answers and outcomes are browser-local dead ends; the YAML leg never existed.

## Related Specs

SPEC-005 FR-087, FR-088, FR-093, NFR-042; SPEC-006 FR-113 … FR-115, NFR-052; INT-MEAS.

## Decision

One owner-state document tree under the pinned store path; the browser is
the sole writer (existing adapters, LWW); the engine pulls at run start with a service
account, mirrors to `data/owner/owner_state.json` (committed by CI like snapshots) and
never writes back. Legacy per-feature localStorage keys are migrated once.

## Rationale

No runtime server (D-12); durability across devices; the engine needs the
data in CI where no browser exists; the code exists and its reconcile logic is tested.

## Alternatives Considered

(1) localStorage + manual YAML — fails NFR-042 and puts a team step
between the owner and FR-088. (2) A small API server — adds a runtime component for one
user. (3) Commit outcomes to git from the browser — no.

## Trade-offs

Anonymous-auth exposure (§15); a CI secret to provision; a first-run
risk since Firestore has never been exercised here.

## Reversibility

Moderate.
