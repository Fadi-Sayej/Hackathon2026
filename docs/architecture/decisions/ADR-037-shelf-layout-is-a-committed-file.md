---
ID: ADR-037
Title: The shelf layout, facing widths and arrangement rules are a committed file the team records; owner state never holds them
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-10-03
Parent: [System Design](../system-design.md) §19
Related Specs: F12-S1 (FR-178 … FR-180, FR-190, FR-199, NFR-075, C-74, OQ-1201, OQ-1202)
Inputs: [docs/features/F12-planogram/specs/F12-S1-planogram.md, D-13, D-22, D-30, ADR-029, ADR-033, ADR-036]
Updated: 2026-10-03 (OQ-1201 answered: widths from photographs)
---

# ADR-037 — The shelf layout is a committed file the team records; owner state never holds them

**Status:** Ready for review · **Recorded in:** [System Design](../system-design.md) §19

## Context

F12-S1 needs three kinds of fact that only the store can give, and needs them before its daily
sales arrive (D-30):
- each fixture's shelves, usable lengths, departments, chilled or not, and eye-level shelf;
- each stocked product's facing width;
- the owner's arrangement rules.

ADR-033 settled where the store's other stated facts live (order schedules and shelf lives): a
committed file, recorded by the team, validated at load, and changed only by commit. Some of these
facts are stated by the owner (rules, which shelf is at eye level). Others are measured by the
team (lengths; widths read from his shelf photographs, F12-S1 OQ-1201).

## Decision

The layout facts live in **one committed file per store copy**, beside `configs/store_facts.yaml`,
and follow ADR-033's rules:
1. **What is missing stays missing.** A product without a width is not placed (F12-S1 FR-180),
   and a department on no fixture is listed by `layout_facts`.
2. **Validated at load, never repaired.** A fixture, rule or width that does not validate is
   rejected by name in the run's steps. An empty file is still a file. An absent file is a
   missing input (`no_store_layout`).
3. **Provenance on every entry, by kind:**
   - a measurement carries `measured_by` (`owner` or `team`) and `measured_on`;
   - a statement (a rule, the eye-level shelf, a fixture's departments) carries `stated_by:
     owner`, `stated_on` and `recorded_by: team`.

   No name or email is written (D-22). The artefact publishes the dates (F12-S1 FR-189).
4. **Changed only by commit.** The history records what was measured or stated, and when.
5. **Store data under ADR-036.** The file is in a new copy's manifest of files that start empty,
   so updating a copy from the product never overwrites a store's layout. `check:store` reports
   whether it is present (F12-S1 NFR-075).

Shelf photographs are the team's source for these facts. They are never an input to the engine,
so D-13 holds by construction.

## Rejected options

### A form in the app
The owner could write owner state, but the measurements are the team's (F12-S1 OQ-1201),
and the team cannot write owner state (ADR-029). It would also mean a form with one width per
stocked product, the kind ADR-033 rejected for 55 departments, citing F5-S1 C-40 on abandoned
forms.

### A vision model reading shelf photographs
Nobody knows whether a model can read facing widths to the millimetre from a hand-held
photograph: the PRD's one-day trial was never run (F12-S1 OQ-1202). If the trial succeeds, a
later ADR can supersede this one, for widths alone.

### Add the layout to `configs/store_facts.yaml`
That file is keyed and validated per department, against the catalogue, and F8 depends on that
validation (ADR-033). Fixtures and per-product widths are different keys. Mixing them would change
a file F8 reads, for a feature F8 does not need.

## Consequences

**We accept:** reading widths from his shelf photographs is work for the team (OQ-1201, answered
2026-10-03: "from photos"), and a plan waits until it is done.

**We gain:** F12 can be set up the day a store states its fixtures, before any sales arrive, with
no new storage, no image handling and no model cost.

**We will know it was wrong if:** widths are never recorded for most stocked products, so plans
keep saying "no width". Then the vision trial (OQ-1202) becomes the next decision.

## Reversibility

Easy. The file only feeds two capabilities. Moving widths to another source changes how one input
is filled, not what the plan does with it.

## Binds

| F# | How this constrains it |
|---|---|
| F12 | Its inputs come from this file only (F12-S1 FR-178, INV-084) |
| F8 | Unaffected: `configs/store_facts.yaml` is not changed |
