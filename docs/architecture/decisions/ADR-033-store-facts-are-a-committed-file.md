---
ID: ADR-033
Title: The store facts are a committed file the team records from the owner; owner state never holds them
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-25
Parent: [System Design](../system-design.md) §19
Related Specs: F8-S1 (FR-146, FR-151, FR-152, FR-155, FR-157, INV-071, OQ-903, OQ-908)
Inputs: [docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, D-22, ADR-003, ADR-029, F5-S1 C-40, configs/store_policy.yaml, configs/shelf_life.yaml]
Updated: 2026-09-25
---

# ADR-033 — The store facts are a committed file the team records from the owner; owner state never holds them

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

F8-S1 needs two facts per department that only the store owner holds: when he orders it,
and how long its products keep. They are:
- gathered once, by the team;
- recorded as his statements;
- never defaulted or inferred (FR-157, INV-071);
- never asked on screen (FR-157, AC-156).

Where they live is constrained from two sides:
- **ADR-029 makes the team read-only in the owner's app.** Firestore rules allow writes for
  `owner` only (D-22). So the team cannot record them in owner state, which only the browser
  writes (ADR-003).
- **One fact held in two places diverges.** On a degraded day the copies disagree, and
  nothing says which is right. That is the defect ADR-026 fixed, where the reconcile
  boundary was derived at two moments.

## Decision

The store facts live in **`configs/store_facts.yaml`**, committed, with one entry per
department:

- **`order_schedule`** is one of:
  - `weekdays: [sun, wed]`;
  - `every_days: 14` with `from: 2026-10-04`;
  - `no_fixed_days: true`.
- **`shelf_life_days`** is a whole number of days, or `does_not_spoil: true`. `0` records
  "keeps less than a day", which gives no quantity (F8-S1 FR-151, SCN-139).
- **Provenance on every entry:** `stated_by: owner`, `stated_on: <date>`, `recorded_by: team`.
  No name or email is written (D-22).

The file follows these rules:

1. **A department missing from the file has no facts.** Its products get no quantity (F8-S1
   FR-155), and Reorder names what is missing.
2. **Validated at load, never repaired.** A department name that matches no catalogue
   department is rejected, and so is a malformed schedule or a shelf life that is not a
   whole number. Rejected entries are reported in the run's steps.
3. **Published with their dates.** The artefact publishes each department's facts with
   `stated_on` (F8-S1 FR-154), so the owner can see what he told the team, and when.
4. **Changed only by commit.** A schedule change is a reviewed commit. The history is the
   record of when he said what.
5. **Kept apart from the guess table.** `configs/shelf_life.yaml`, the category guesses, is
   not read by F8 (FR-152). The two files stay separate so a guess can never pass as his
   statement.

## Rejected options

### Owner state, entered through a form in the app
The team cannot write owner state (ADR-029). The owner would face a form covering dozens of
departments (the catalogue has 55), twice over, and F5-S1 C-40 records why forms are
abandoned. F8-S1 FR-157 also
forbids on-screen questions for these facts.

### Both a file and owner state, with one of them winning
That is one fact in two places. The copies agree on every normal night, and disagree on the
day one of them is updated and the other is not. There is no degraded day on which that
shape has helped.

### Add the facts to `configs/store_policy.yaml`
That file answers what the store *carries*. Its `verified` values mean an owner-stated
exclusion, or one derived from his sales. Order schedules and shelf lives are different
facts, with different provenance and different readers, and sharing a file would blur what
`verified` means.

### Add his statements to `configs/shelf_life.yaml`
That file is category-level starting guesses, by its own header. His statements would sit
among guesses, and the difference that OQ-908 depends on would be one comment away from
being lost.

## Consequences

**We accept:**
- The owner cannot change a schedule himself in the app. He tells the team, and the team
  commits it.

**We gain:**
- One source, reviewable history, and nothing that conflicts with ADR-029.
- A missing department is visible as missing.

**We will know it was wrong if:** he changes his schedules often enough that the file lags
what he actually does. An owner-writable path would then be needed, through a superseding
ADR and not a second copy.

## Reversibility

Easy. The file is read at run start. Moving the facts elsewhere is a change to one loader
and to this ADR.

## Binds

| F# | How this constrains it |
|---|---|
| F8 | FR-146, FR-151, FR-152, FR-155 and FR-157 read the facts from this file only |
| F10 | When F10 measures shelf life, its spec decides how measurements combine with these statements (F8-S1 FR-151) |
