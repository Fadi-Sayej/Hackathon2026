---
ID: ADR-035
Title: A model's answer is collected data: it is sealed as a daily snapshot, and reproduction reads it like any other
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-25
Parent: [System Design](../system-design.md) §19
Related Specs: F8-S1 (NFR-066, NFR-067, C-71, AC-160); F7-S1 (FR-125, FR-126)
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, D-21, ADR-002, ADR-004, ADR-032, CLAUDE.md rules 6 and 9, scripts/check_v1_signals.py, scripts/check_independence.py]
Updated: 2026-09-26
---

# ADR-035 — A model's answer is collected data: it is sealed as a daily snapshot, and reproduction reads it like any other

**Status:** Accepted (2026-09-26, by the repository owner, on PR #200) · **Recorded in:** [System Design](../system-design.md) §19

## Context

A boost pick (ADR-032) cannot be recomputed. The same request can return a different answer,
and F8-S1 requires the quantity to replay from the recorded pick (NFR-067, C-71). The
existing rules pull three ways:
- **ADR-002 and F7-S1 FR-125.** Reproduction is the engine in print mode, and it "MUST read
  current data rather than any recorded value of a previous computation". ADR-002 rejects
  reading back from the artefact for exactly that reason.
- **ADR-004.** The engine owns no persistent state.
- **CLAUDE.md rule 9.** CI commits only `data/external/snapshots/`.

The rule-12 probes also run the engine in print mode (`check_v1_signals.py`,
`check_independence.py`). They need a defined answer to "where do the picks come from here?".

## Decision

1. **A pick is an external source's answer, captured on the night it was given, like the
   delivery catalogues.** It is not a computation of this engine.
2. **Each night's picks are sealed as a snapshot**, under
   `data/external/snapshots/<day>/boost_picks/`. `<day>` is the day of the market evidence
   the picks answered, meaning the latest usable day of ADR-031's signal, which the artefact
   publishes. It is not the date on which a run or a reproduction happens.
   - The file is `picks.json`. For each product it holds `{barcode, model, prompt_version,
     requested_at, inputs_digest, boost_pct, reason, accepted, rejected_because?}`.
   - A `_manifest.json` records the requests made, the ceiling (ADR-032) and whether the step
     completed.
   - It is committed in **its own step, right after the engine and before the blocking
     probes**. So picks already paid for are kept whatever the probes decide. Neither
     existing commit covers it: `collect-daily.yml` commits snapshots before the engine runs,
     and commits only `public/data/` after it. It is still a snapshot, so rule 9 needs no new
     exception.
   - **Merge-never-replace**, the snapshot convention (§12). A same-day re-run asks only for
     products that have no pick yet, and never replaces a pick already sealed.
3. **The live run and reproduction differ in one step only.**
   - **The live run** asks the model (ADR-032), writes the day's snapshot, then reads it back
     as an input.
   - **Print mode** never calls the model. It reads the day's snapshot if one exists. If none
     exists, that is the model input withheld: no boost, and each suggestion says why.
4. **A pick whose inputs no longer match is not used.** Every pick records the digest of the
   facts it was given (ADR-032, Decision 3). If reproduction computes different facts for a
   product, its recorded pick is not applied. The suggestion says so, rather than silently
   pairing an old answer with new facts.
5. **The probes follow from Decision 3.** `check:signals` withholds the model by withholding
   the `boost_picks` snapshot (F8-S1 §20). Suggestions must then publish unboosted, and no
   boost may appear from nothing. F8's probes have to run **with** the market inputs. Today's
   probes run with `skip_market=True` (`check_v1_signals.py`), and withholding the picks
   there would exercise nothing. The implementation plan names that probe task.
6. **Where the authority comes from.** FR-125 is read together with F8-S1 C-71, which
   carries D-21: a pick is replayed from its record. This ADR's part is to make that record
   collected data, so reproduction still reads only committed inputs.

## Rejected options

### Read the picks back from the previous artefact
This is the lightweight reader ADR-002 rejects. It reads "a recorded value of a previous
computation" (FR-125), and it ties reproduction to the artefact of one night.

### Call the model again in print mode
The answer can differ, so reproduction would not reproduce. It would also spend money on
every reproduction and probe, and fail whenever the key or the API is absent.

### Keep the picks in a store the engine owns
ADR-004 forbids engine-owned state. A private store would also need its own durability and
history, both of which the snapshot mechanism already provides.

## Consequences

**We accept:**
- The snapshots grow by one small file a night.
- A pick is reproducible only for the facts it was given (Decision 4).

**We gain:**
- Reproduction stays "committed inputs → the same artefact" (ADR-002).
- The engine still owns no state (ADR-004), and CI still commits only snapshots (rule 9).
- The probes get a clean way to withhold the model.

**We will know it was wrong if:** reproductions routinely hit Decision 4, the digest
mismatch. That would mean the facts drift between the live run and reproduction, which is a
defect in its own right, outside this ADR.

## Reversibility

Easy. The snapshot is additive. Dropping the boost leaves past snapshots as history.

## Binds

| F# | How this constrains it |
|---|---|
| F8 | NFR-066, NFR-067, C-71 and AC-160: the pick is replayed from this snapshot |
| F7 | FR-125 is read with F8-S1 C-71 (D-21): the pick is replayed from a committed snapshot, the only kind of record reproduction reads |
