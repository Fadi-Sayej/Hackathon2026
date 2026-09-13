---
ID: ADR-023
Title: The engine publishes the pilot measurement; the browser renders it
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-13
Parent: [System Design](../system-design.md) §19
Related Specs: F13-S1 (§14 item 5), F6-S1, F7-S1
Inputs: [ADR-001, ADR-004, ADR-005, ADR-016, docs/features/F13-pilot-measurement/specs/F13-S1-pilot-measurement.md, issue #94, issue #96]
Updated: 2026-09-13
---

# ADR-023 — The engine publishes the pilot measurement; the browser renders it

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

F13-S1 §14 item 5 asks where the measurement surface reads the owner's outcomes from. Two
candidates: the **engine** publishes the measurement in the artefact, or the **browser** reads
`stores/{store}/ownerState` from Firestore and computes it.

The question exists because F13-S1's first draft named `smartshelf.ownerState.v2` — the
reading device's own localStorage, which on a team screen holds the team's clicks, not the
owner's decisions (#94).

## What the data allows, read before deciding

| Fact | Source |
|---|---|
| The artefact carries **nothing** about outcomes — no `outcome`, `acted`, `declined`, `deferred` or `recovered` anywhere | `public/data/dashboard.json` |
| The engine reads **no past artefact**; `publish.py` only writes the current one | `src/engine/` |
| Committed artefact history is **one day** — the nightly began committing `dashboard.json` on 2026-09-13, as the 09-13 incident fix | `git log -- public/data/dashboard.json` |
| **Every outcome carries its own money**: ADR-016 captures `value`, `kind` and `certainty` into the snapshot at the moment of the decision | `tests/fixtures/owner_state_firestore_contract.json` |
| The engine already pulls the whole outcome set every run | `src/owner_state/pull.py` |

## Decision

**The engine computes and publishes the pilot measurement. The browser renders it and computes
nothing.**

This is ADR-001 applied without an exception: recovered ₪ is a business rule over money, and
the browser holds no business rule. It is also the only answer consistent with **FR-138**,
which already requires the surface to take money from the value the engine published rather
than recompute it — a browser that recomputed the total from Firestore would be doing exactly
what FR-138 forbids, one layer up.

A browser reader would additionally need the reader §11.5 names and nothing implements, a
second anonymous-auth path, and a duplicate of the join in JavaScript. The duplicate is the
part that matters: two implementations of one figure is what ADR-002 exists to prevent.

## The split this exposes, and it is the useful part

Not everything F13-S1 asks for needs the same inputs.

**The success number needs no history at all.** «رقم النجاح» is money recovered from what the
owner acted on. Because ADR-016 froze `value`, `kind` and `certainty` into each outcome's
snapshot, that total is a function of **owner state alone** — which the engine pulls in full,
every run. It survives thresholds moving, entries being re-carved, and the artefact changing
shape, which is precisely why ADR-016 captured it. So PRD §8's number is computable tonight,
from data already in hand, and it does not depend on the artefact history existing.

**Rates over what was shown do need history.** `shown` — F13-S1 FR-137 — is "an entry
published in a run inside the window". That is only knowable from the artefacts of those runs,
and:

- the committed history is **one day** (2026-09-13 onward);
- it grows only while the nightly keeps committing, so **a missed night is a permanent hole**
  in the shown-set, the same irreplaceable loss the market snapshot has;
- reading past artefacts is reading **inputs**, not owning state, so it does not breach
  ADR-004 — but it does make the measurement depend on git history, which is new.

**Consequence to state plainly:** a 30-day acceptance *rate* cannot be computed for any window
starting before 2026-09-13. A 30-day *recovered ₪* can. If the pilot's 30 days start at the V1
ship, the rate is available; if anyone asks for a rate reaching back to the cut-over, the
honest answer is "not measurable", not a smaller number (rule 13's distinction).

## Rejected options

### The browser reads Firestore and computes the measurement
Breaks ADR-001, duplicates a money rule the engine already owns, and needs a browser reader
that does not exist. It is also the option that looks cheapest and is not: the join it
duplicates is the one #94 showed nobody was testing across.

### Publish raw outcomes in the artefact and let the browser aggregate
Puts the owner's full decision history — including what he declined and why — into a file
committed to the repository on every run, to save an aggregation the engine is already placed
to do. The artefact states figures, not a personal record.

### Keep it out of the engine until the owner's numbers arrive
F13-S1 is `Blocked` on those numbers, so this is tempting. But the transport question is
independent of the threshold: what is measured may move with OQ-801; *where it is computed*
does not. Deciding it now is what lets the build start the day the numbers land.

## Consequences

**We accept:** the artefact gains a measurement block, and its schema with it — so this lands
**after Checkpoint 3 closes**, like every other artefact change queued tonight. The engine
gains a reason to read its own past output, which is a new dependency and should be narrow:
the shown-set only, never re-deriving figures from old artefacts.

**We gain:** one implementation of recovered ₪, in the language that owns every other figure,
provenanced by F7-S1 like the rest, and available to any surface that reads the artefact
rather than only to a browser holding the owner's session.

**We will know it was wrong if:** the measurement needs to answer questions per viewer or per
moment — "what did *this* device see" — which an engine-published aggregate cannot express.
Nothing in F13's intent asks for that; PRD §8 asks one number of the whole pilot.

## Binds

| F# | How this constrains it |
|---|---|
| F13 | The surface renders; it computes no figure. FR-135's source is the artefact |
| F7 | The measurement is a figure: provenance, window and thresholds travel with it |
| F6 | Unchanged — the daily surface is not a measurement surface |
