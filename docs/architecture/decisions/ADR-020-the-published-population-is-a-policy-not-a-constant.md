---
ID: ADR-020
Title: The published population is a policy setting, not a constant
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-12
Parent: [System Design](../system-design.md) §19
Related Specs: F1-S1, F4-S1 (FR-074), F6-S1
Inputs: [docs/product/intent-register.md D-14, docs/features/gaps-and-open-questions.md GAP-009, src/engine/run.py]
Updated: 2026-09-12
---

# ADR-020 — The published population is a policy setting, not a constant

**Status:** Accepted (2026-09-13) · **Recorded in:** [System Design](../system-design.md) §19

## Context

FR-074 has the catalogue's withdrawn set reach every other capability's population, so the
engine counts over the **living** catalogue. On the pilot that withdraws 3,903 products and
moves F1 from 68 confirmed losses to 53.

**D-14** forbids putting a figure that depends on automatic withdrawal in front of the
owner until **GAP-009** closes, and GAP-009 is a question only the store owner can answer:
withdrawal rests on "absent from the monthly reports" meaning "sold nothing", true of 3,932
of 3,932 withdrawable products, with exactly one appearing in the reports with an observed
zero.

The consequence, until today, was structural: the browser cut-over (Task 2.7) and the whole
of Phase 4 were blocked — not on engineering, but on a meeting. **That is a dependency we
created, not one the problem has.** The engine already computes both populations: Task 3.0
added `run_engine(population=...)` so `npm run figures:whole` could produce the D-14 figures
from the single implementation. Nothing but a default stops the *published* artefact using
the same switch.

A pilot that cannot proceed because a conversation has not happened is a pilot whose
architecture has made a product decision structural.

## Decision

**The population the engine publishes is declared in `configs/policy.yaml`, and the
artefact states which one it used.**

```yaml
# GAP-009 is open: withdrawal rests on "absent from the reports" = "sold nothing", which
# the owner has not confirmed. Until he does, D-14 forbids showing him a figure that
# depends on it, so the published artefact counts over the WHOLE catalogue.
# When GAP-009 closes, change this to `living` — and nothing else.
published_population: whole
```

The artefact carries `population` at top level beside `schema_version`. A reader can always
tell which catalogue a count was taken over, and the browser can render it.

Two consequences worth stating plainly:

- **The cut-over is no longer blocked.** With `published_population: whole`, no figure in
  `dashboard.json` depends on automatic withdrawal, so serving it to the owner satisfies
  D-14. Task 2.7 becomes an engineering decision again.
- **Closing GAP-009 becomes a one-line change**, made deliberately, with the reason sitting
  next to it — rather than a code change someone has to remember to find.

## Rejected options

### Wait for the meeting
What we were doing. It makes a product conversation a build dependency, and it blocks work
— Phase 4, the cut-over, every e2e test that needs the real spine — that has nothing to do
with the question being asked. The question still matters; it should not be load-bearing
for the schedule.

### Publish both populations in one artefact
Doubles every count and every figure, and creates a reader who must choose. The whole point
of D-1, D-2 and D-3 is that the artefact states one number and says what it rests on. Two
populations side by side invites exactly the comparison D-14 exists to prevent someone
making casually.

### Hard-code `whole` until GAP-009 closes, then hard-code `living`
The same decision, made invisible. Six weeks later nobody remembers why the engine excludes
withdrawn products, or that the exclusion was ever conditional. A policy line with the
reason attached is the difference between a decision and a quirk.

### Let the browser choose
Moves a product decision into a component and makes it per-session. Two people looking at
the same pilot would see different counts and both would be right, which is worse than
either being wrong.

## Consequences

**We accept:** until GAP-009 closes the owner sees figures over a catalogue that includes
products he may genuinely no longer stock — 68 confirmed losses rather than 53. That is
D-14's own choice, now implemented rather than merely stated, and it errs toward showing
him too much rather than hiding something behind an unconfirmed assumption.

The engine's internal behaviour is unchanged: `catalogue_lifecycle` still classifies and
still publishes `withdrawable`, so the question GAP-009 asks stays visible and answerable.

**We gain:** the cut-over, Phase 4 and the remaining e2e work stop waiting on a
conversation. GAP-009 stays open and still matters — it just no longer holds the build.

**We will know it was wrong if:** the owner, shown the whole-catalogue figures, spends his
ten minutes on products he does not stock. That is an argument for closing GAP-009, not for
reversing this.

## Confirmation owed before the population changes

Accepted with one condition, and it is the condition this ADR was written around.
`published_population: whole` is correct **because GAP-009 is open** — withdrawal rests on
"absent from the monthly reports" meaning "sold nothing", true of 3,932 of 3,932
withdrawable products, of which exactly one appears in the reports with an observed zero.
Until the owner confirms that reading, D-14 forbids showing him any figure that depends on
it, and the whole catalogue is the only honest population.

So this acceptance is **not** an acceptance of `whole` as the permanent answer. It accepts
that the population is a declared policy line with its reason attached, and that `whole` is
the right value while the question is open. When
[GAP-009](../../features/gaps-and-open-questions.md) closes, the value changes to `living`
— and nothing else, which is the point.

The cost of being wrong is stated above and has not changed: the owner sees 68 confirmed
losses rather than 53, some over products he may no longer stock. That errs toward showing
him too much, which is the direction D-14 chose deliberately.

## Binds

| F# | How this constrains it |
|---|---|
| F1, F3, F4 | Counts are taken over the population named in `policy.published_population`, and the artefact states it |
| F6 | The surface may render the population; it is in the artefact |
