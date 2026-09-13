---
ID: ADR-021
Title: The artefact states how many devices have written owner state, and when
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-13
Parent: [System Design](../system-design.md) §19
Related Specs: F5-S1, F6-S1
Inputs: [docs/implementation/phase-4-removal.md P4-OQ-1, ADR-003, ADR-005, docs/architecture/system-design.md §10.3]
Updated: 2026-09-13
---

# ADR-021 — The artefact states how many devices have written owner state, and when

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

Phase 4 Task 4.3 removes the one-shot migration that carries the three pre-V1 localStorage
keys into `smartshelf.ownerState.v2`. Its precondition is that **every pilot device has
opened the app at least once since the cut-over**, so that nothing is still sitting
unmigrated on a phone.

Nothing measures that. The outcome store is per-device, and the engine sees only what
Firestore holds — which tells it that *some* devices have written, never that *all* of them
have. The phase file recorded the gap as **P4-OQ-1** and offered two answers: ask the
owner, or publish a device count.

"Ask the owner" was the cheaper answer and is what the phase file recommended. It was not
chosen, for a reason worth writing down: the thing being protected is the owner's own
recorded decisions, deleting them is not reversible, and "I think everyone has opened it"
is a sentence no one should have to stake that on six weeks later.

## Decision

**The browser registers the device it is running on, and the engine publishes what it
finds.**

Browser, on every owner-state write (ADR-003 keeps the browser the sole writer):

- a random opaque `device_id`, minted once per browser and kept in `localStorage`. No
  fingerprinting, no user agent, nothing derived from the person or the hardware — it
  exists to be counted, not to identify anyone.
- written to Firestore beside the owner state as `{ device_id, first_seen_at, last_seen_at }`.

Engine, at run start, with the rest of the owner-state pull:

```json
"owner_state": {
  "status": "available",
  "devices": {
    "count": 3,
    "seen": [
      { "id": "d3f1…", "first_seen_at": "2026-09-12T09:14:02Z", "last_seen_at": "2026-09-13T07:41:55Z" }
    ]
  }
}
```

Sorted by `id`, so the artefact stays deterministic. It is an input like every other part of
owner state, so no capability reads a clock.

## What this does and does not prove

**It gives a floor and a date.** "Three devices have written since the cut-over, the most
recent this morning" is checkable, and it is in the artefact rather than in someone's
memory.

**It cannot prove completeness.** A device that never opens the app again is
indistinguishable from a device that does not exist. So the owner still confirms *"that is
all of them"* — the difference is that he now confirms it **against a number and a set of
dates**, instead of being asked to recall a fleet.

That limit is the honest reading and is stated here so no one later mistakes the count for
a guarantee. It is the same distinction rule 13 draws between "not measurable" and
"measured and not significant": this measures what wrote, not what exists.

## Rejected options

### Ask the owner, record the answer
What the phase file recommended, and it is not wrong — it is just unverifiable afterwards,
and what it guards is irreversible. The two are not symmetric: a wrong "yes" costs the
owner his recorded decisions, and costs us the ability to tell that we lost them.

### Stamp every outcome with its device
More data, same gap. It tells you which devices produced outcomes, not which devices exist
and have been opened. A device whose owner opened the app and did nothing is exactly the
case that matters, and it produces no outcome to stamp.

### Keep the migration forever
Defensible, and cheap — dead code in `ownerState.js` costs almost nothing. Rejected because
Phase 4's purpose is that the repository stops carrying two of everything, and "we could
never tell if it was safe to remove" is how the other half of the attic got there.

## Consequences

**We accept:** a new field in the artefact and its schema, a small Firestore write on the
browser's existing write path, and one more thing the engine reads. It is additive; no
capability's `requires` changes, and a missing `devices` block reads as `status:
unavailable` like every other absent input (ARCH-DRIVER-002).

**We gain:** Task 4.3's precondition becomes checkable, and stays checkable — the same
question will be asked again at every future migration.

**We will know it was wrong if:** the count is right and nobody looks at it, which would
mean "ask the owner" was the proportionate answer after all.

## Binds

| F# | How this constrains it |
|---|---|
| F5 | Owner state gains a device register; the browser remains its sole writer (ADR-003) |
| F6 | The data page may render the device count; it is in the artefact |
