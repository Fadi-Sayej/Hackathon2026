---
ID: ADR-016
Title: The owner-outcome snapshot carries the signal family
Status: Draft
Owner: smartshelf-architect
Date: 2026-09-12
Parent: [System Design](../system-design.md) §19
Related Specs: F6-S1 (FR-115), F13 / INT-MEAS
Inputs: [docs/architecture/system-design.md, docs/implementation/plan.md, docs/architecture/decisions/ADR-009-stable-entry-identity-via-signal-family.md]
Updated: 2026-09-12
---

# ADR-016 — The owner-outcome snapshot carries the signal family

**Status:** Draft · **Recorded in:** [System Design](../system-design.md) §19

## Related Specs

F6-S1 — FR-115 (the snapshot is captured at the moment of the outcome because it cannot be
reconstructed after thresholds move). F13 / INT-MEAS — the pilot's 30-day measurement, which
is the only consumer that reads outcomes back.

## Context

When the owner marks an entry acted, declined or deferred, the browser records
(§9.3, §10.3):

```
{entry_id, status, reason?, deferred_until?, at,
 snapshot: { capability, barcode, value?, kind?, characterisation }}
```

`entry_id` is `entry_id(signal_family, barcode, variant)` — hashed from the **signal
family**, never the capability id, because a capability id is a routing label that moves.
That is [ADR-009](ADR-009-stable-entry-identity-via-signal-family.md), and Phase 1 has
already exercised exactly the move it anticipates: `hygiene` left `reconciliation` and
became its own capability while every `entry_id` stayed identical.

The snapshot records the label that moves and omits the one that does not.

The consequence is not visible today and is not recoverable later. `entry_id` is a hash,
so it cannot be read backwards into a family. When INT-MEAS asks the only question the
pilot exists to answer — *which kinds of finding did the owner act on?* — it must group
outcomes by something durable. Grouping by `capability` answers a different question, and
answers it wrongly for every outcome recorded before a capability moved: the same finding
would appear under `reconciliation` in August and `hygiene` in September.

The design already states why the snapshot exists at all — *"it is captured now because it
cannot be reconstructed after thresholds move"*. The same argument applies with more force
to the family, because a threshold change alters a value while a capability change alters
the grouping itself.

The cost is one field, written once, in a Phase 2 task that is not yet written. After the
pilot has accumulated outcomes it cannot be backfilled at all.

## Decision

**The outcome snapshot carries `signal_family`.**

```
snapshot: { signal_family, capability, barcode, value?, kind?, characterisation }
```

`signal_family` is the durable grouping key and comes from the entry being acted on.
`capability` stays: it records where the finding was routed *on the day the owner saw it*,
which is worth keeping precisely because it may differ later.

The field is mandatory in the outcome record. A snapshot without it is refused by the same
validation that already closes the `status` and `reason` enums (§9.3).

## Rejected options

### Leave the snapshot as it is and recover the family from `entry_id`
Not possible. `entry_id` is a 16-hex hash of `(signal_family, barcode, variant)`; there is
no inverse. Recovering it would mean hashing every family against every barcode in the
catalogue for every outcome, which reconstructs the family only while the *current*
enumeration still contains it — the case where nothing moved, which is the case where the
answer was not needed.

### Record the family only, and drop `capability`
Loses the routing history. Knowing that a finding was shown to the owner under
`reconciliation` in August is how a later reader explains why the August surface looked as
it did. Both fields answer different questions and both are one word.

### Defer until INT-MEAS is specified
INT-MEAS is `Registered — not specified` and blocked on its own decisions, so this would
defer past the pilot. The outcomes accumulate from day one of the pilot; the field is
unrecoverable for every outcome recorded before it is added. Deferring the decision does
not defer the cost, it only guarantees paying it.

## Consequences

**We accept:** one more field in every outcome document, and a Phase 2 validation that
refuses a snapshot without it. Outcomes recorded by the pre-V1 browser (the seven legacy
localStorage keys, §20) have no family and are migrated with `signal_family: null` — a
stated absence rather than a guessed value (D-3).

**We gain:** INT-MEAS can group the pilot's outcomes by a key that survives a capability
moving, which Phase 1 has already demonstrated happens.

**We will know it was wrong if:** no consumer ever groups outcomes by family — in which
case the cost was one unread field, which is the cheap direction for a decision that is
unrecoverable in the other.

## Binds

| F# | How this constrains it |
|---|---|
| F6 | The outcome record written by the daily surface (FR-115) gains a mandatory field, and its validation refuses a snapshot without it |
| F13 | INT-MEAS groups outcomes by `signal_family`; it may not group by `capability` |
