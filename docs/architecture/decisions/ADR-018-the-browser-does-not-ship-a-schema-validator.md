---
ID: ADR-018
Title: The browser does not ship a schema validator
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-12
Parent: [System Design](../system-design.md) §19
Related Specs: F6-S1 (AC-107), F7-S1
Inputs: [docs/implementation/phase-2-browser.md, docs/architecture/system-design.md §16, schemas/dashboard.schema.json, .github/workflows/ci.yml]
Updated: 2026-09-12
---

# ADR-018 — The browser does not ship a schema validator

**Status:** Accepted (2026-09-12) · **Recorded in:** [System Design](../system-design.md) §19

## Context

Phase 2 Task 2.0 tells `loadDashboard` to validate the artefact against
`schemas/dashboard.schema.json` — *the same schema the publisher uses*, on the reasoning
that a hand-written JS check would drift from the Python one. It then raises its own
question (P2-OQ-1): is a validator already in the bundle?

Measured: **no.** `npm ls ajv zod` returns empty — both are present in `node_modules` only
as transitive dependencies of build tooling, which means neither is a dependency this app
may rely on; an unrelated `npm install` can remove either. Shipping one means adding a
direct dependency to a browser bundle with a stated budget — design §16 expects a main
chunk under 400 KB, and Checkpoint 4 sets a hard limit of 500 KB.

The premise is also weaker than it looks. The schema is **already enforced twice**:

| Where | What | When |
|---|---|---|
| `src/engine/publish.py` `validate_artefact` | the full schema, and the registry-completeness and money-policy assertions | every publish — a failing artefact is never written |
| `.github/workflows/ci.yml` | the same `validate_artefact` over the committed artefact | every push and pull request |

An artefact that reaches the browser has passed both. A third enforcement adds a dependency
to catch a case the first two already refuse to produce.

## Decision

**`loadDashboard` performs no schema validation. It checks only what it cannot render
without, and every check traces to an acceptance criterion rather than to the schema:**

| Check | Fails as | Why the browser needs it |
|---|---|---|
| the response is reachable and parses as JSON | `unreachable` | a network state, which no schema describes |
| `schema_version === 2` | `invalid` | a different version has an unknown shape; rendering it would guess |
| `capabilities` is an object | `invalid` | there is nothing to render otherwise |
| every capability has a `status` | `invalid` | **AC-107** — an unavailable capability must read as unavailable, never as zero findings, and that is impossible to honour without the field |

Roughly five lines, no dependency, and each one has a rendering reason. The behaviour Task
2.0 specifies is unchanged: never throw, never fall back, report the state.

## Rejected options

### Add `ajv` as a direct dependency and validate the full schema in the browser
Spends the §16 budget on a third enforcement of a contract already enforced where it is
produced and again where it is committed. It would catch only an artefact hand-edited
between CI and the browser — and that artefact fails the four checks above anyway if it is
malformed in any way the UI can observe.

### Hand-write a full structural check in JS
The drift risk Task 2.0 correctly names. Two descriptions of one contract diverge, and the
divergence is invisible until an artefact passes one and fails the other. Avoided by not
writing a second description at all — the four checks above are not a description of the
schema, they are the UI's own preconditions.

### Validate in a build step and inline the result
Moves the dependency out of the bundle but pins validity to build time, while the artefact
is refreshed nightly and independently. It would certify a file that is replaced after
certification.

## Consequences

**We accept:** the browser trusts an artefact that passed the publisher and CI. An artefact
corrupted after CI — a partial deploy, a truncated transfer — is caught only if it breaks
JSON parsing or one of the four checks. A subtly wrong value (a count that should be null)
renders as published.

That risk is the same one the artefact already carries for every figure, and it is
addressed where figures are addressed: provenance (F7-S1) and reproduction (`npm run
figures`, Phase 3), not a schema check in a phone browser.

**We gain:** no new dependency, the §16 budget intact, and one description of the contract
instead of two.

**We will know it was wrong if:** an artefact reaches the browser that passes the four
checks and renders something false. The first such case is a Phase 3 reproduction concern,
not an argument for a validator.

## The budget is now enforced

Accepted with one addition: this decision rests on a §16 budget that nothing checked.
`npm run check:bundle` runs in CI after the build and fails when the bundle grows past a
ceiling.

The ceiling is set at **5,200 KB**, just above the 5,012 KB measured on 2026-09-12 — not at
the 500 KB Checkpoint 4 target, which the 4.36 MB demo spine (§20.1 REMOVE) makes
unreachable until Phase 4. It is a ratchet: lowering it is the point, and raising it needs a
reason in the commit message.

Without it the argument for declining a validator would have been a sentence in a document
rather than a constraint.

## Binds

| F# | How this constrains it |
|---|---|
| F6 | `loadDashboard` returns `ok` / `unreachable` / `invalid`; the `status` check is what makes AC-107 achievable |
| F7 | Trust in artefact content is carried by provenance and reproduction, not by browser-side validation |
