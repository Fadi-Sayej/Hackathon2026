---
ID: ADR-023
Title: The engine publishes the pilot measurement; the browser renders it
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-13
Parent: [System Design](../system-design.md) §19
Related Specs: F13-S1 (§14 item 5), F6-S1, F7-S1
Inputs: [ADR-001, ADR-004, ADR-005, ADR-016, ADR-021, ADR-024, ADR-029, D-23, D-24, docs/features/F13-pilot-measurement/specs/F13-S1-pilot-measurement.md, issue #94, issue #96, issue #83]
Updated: 2026-09-28 (accepted by the repository owner on PR #230, as revised on 2026-09-27)
---

# ADR-023 — The engine publishes the pilot measurement; the browser renders it

**Status:** Accepted (2026-09-28, by the repository owner, on PR #230) · **Recorded in:** [System Design](../system-design.md) §19

> **Revised 2026-09-27.** Written on 2026-09-13 and never accepted. Two decisions since then
> change what it has to carry. D-24: the measurement shows how much success there is and
> renders no target. D-23: the pilot with the YomYom store has ended, and no store sends new
> data. The decision below stands; [Revision](#revision-2026-09-27) says what it now publishes
> and what it no longer needs.

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

## Revision (2026-09-27)

**No history is read.** The 2026-09-13 text planned to count what was shown from past
artefacts, read from git. It is dropped. "Shown" is what **this run** publishes: the entries
in `capabilities.*.entries`, counted per `signal_family`. The engine still owns no state and
reads no past output (ADR-004), and nothing depends on git history. With no store sending
data (D-23), the runs differ only in their competitor half, so the history would add nothing
the current run does not show.

**No rate crosses two sets.** Decisions come from the whole outcome set, and "shown" from
one run. So no figure divides one by the other. The only share published is within the
decisions: acted on out of decided.

**No target (D-24).** Nothing is compared with a success figure, and `configs/policy.yaml`
gains no threshold.

**The file.** It is published as `public/data/measurement.json`, beside `dashboard.json` and
never inside it. ADR-029 Decision 6 (Accepted) put it there: the edge gate can keep a file from
the owner, and already answers 403 to him for that path, but no gate can keep a field inside
the file his app downloads. It is written like the catalogue (ADR-024): validated against
`schemas/measurement.schema.json`, atomically, as its own step after the artefact, so a
failure leaves the previous file and never the artefact. It names the run it was computed
with (`generated_at`, `run_id`, `inputs_digest`) and carries ADR-021's device register, so
the page needs no second file. Its fields:

| Field | Meaning |
|---|---|
| `status`, `unavailable_reason` | `unavailable` when the owner state is, with its reason (FR-142). Never zeros in its place |
| `window` | `first` and `last`: the earliest and latest decision recorded, `null` when there is none; `pulled_at`: when the engine read them |
| `totals` | `shown` (this run), `decided`, `acted`, `declined`, `deferred`, and `not_in_this_run`: decisions whose entry this run does not publish (SCN-130), counted, never dropped |
| `by_family` | the same counts per `signal_family` (FR-136, FR-137) |
| `money` | one row per `kind` and `certainty`: the sum of `snapshot.value` over **acted** decisions that carry one, with how many. Kinds are never summed together (FR-139), and confirmed and estimated are never summed together (D-10) |
| `declined_reasons` | how many declined decisions gave each reason, and how many gave none |

Money comes only from each decision's snapshot, which froze the value the engine published
on the entry when he decided (ADR-016). Nothing is recomputed (FR-138). A decision with no
money is a count and nothing else (FR-140, INV-066). Order suggestions carry none (D-1).

**The digest reads the decisions.** `inputs_digest` feeds the owner's answers, and not his
decisions or his revivals. Both are already read by what the engine publishes:
`order_quantity` reads his approvals to detect a schedule change (ADR-034), and
`catalogue_lifecycle` reads his revivals. So two runs over different owner state could
publish different artefacts under one digest. The measurement adds a third reader, and the
fix is the same for all three: the decisions and the revivals join the digest. The pull time
and the device register still do not (ADR-021).

**Not a registered figure.** The file carries its own window and pull time, and the run that
`npm run figures` reproduces computes it too. It is not added to `figures{}`: its input
needs a credential, and `figures.py` already separates "needs a credential" from "does not
reproduce". Registering it would make every machine without the service account report a
missing figure.

## Rejected options

### The browser reads Firestore and computes the measurement
Breaks ADR-001, duplicates a money rule the engine already owns, and needs a browser reader
that does not exist. It is also the option that looks cheapest and is not: the join it
duplicates is the one #94 showed nobody was testing across.

### Publish raw outcomes in the artefact and let the browser aggregate
Puts the owner's full decision history — including what he declined and why — into a file
committed to the repository on every run, to save an aggregation the engine is already placed
to do. The artefact states figures, not a personal record.

### Count "shown" from past artefacts in git (this ADR's 2026-09-13 text)
It makes the engine depend on its own history, and a missed night becomes a permanent hole in
the count. After D-23 it buys nothing: no store sends data, so the entries do not change from
run to run except in their competitor half.

### Keep it out of the engine until the owner's numbers arrive
F13-S1 is `Blocked` on those numbers, so this is tempting. But the transport question is
independent of the threshold: what is measured may move with OQ-801; *where it is computed*
does not. Deciding it now is what lets the build start the day the numbers land.

## Consequences

**We accept:** a fourth published file beside the artefact, with its own schema, which the
nightly commits with the artefact. (The 2026-09-13 text also accepted reading past artefacts;
the revision drops that.)

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
