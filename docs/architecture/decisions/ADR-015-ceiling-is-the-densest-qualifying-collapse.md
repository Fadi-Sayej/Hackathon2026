---
ID: ADR-015
Title: The markup ceiling is the densest qualifying collapse, not the last
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-12
Parent: [System Design](../system-design.md) §19
Related Specs: F1-S1 (FR-004, FR-005, AC-004, AC-005)
Inputs: [docs/features/F1-delivery-price-consistency/intent.md, docs/features/F1-delivery-price-consistency/specs/F1-S1-delivery-price-consistency.md, docs/implementation/phase-1-capabilities.md, yomyom-inventory.csv]
Updated: 2026-09-12
---

# ADR-015 — The markup ceiling is the densest qualifying collapse, not the last

**Status:** Accepted (2026-09-12) · **Recorded in:** [System Design](../system-design.md) §19

## Related Specs

F1-S1 — FR-004 and FR-005 (ceiling derivation), AC-004 and AC-005 (the ceiling is
reported and recomputable; undetermined is reported as undetermined).

## Context

F1-S1 derives the delivery-platform markup ceiling from the store's **own** markup
distribution rather than from an assumed figure. `derive_ceiling` bands the positive
markups and looks for a density collapse: a band holding at least `min_band_count`
whose successor holds at most `1 − drop_ratio` of its count.

The pilot export produces **more than one** qualifying collapse, and the implementation
rule written into Task 1.2 — *"the LAST candidate is the ceiling"* — selects the wrong
one. Read from `yomyom-inventory.csv`, 1,260 positive markups, `band_pct=2`,
`drop_ratio=0.75`, `min_band_count=20`:

| band | count | drop to next | qualifies |
|---|---|---|---|
| 16–18 → 18–20 | **81** | 0.90 | ✓ |
| 24–26 → 26–28 | 24 | 1.00 | ✓ |

"Last" yields **26%**. F1's approved intent, F1-S1 and `scripts/print_figures.py` all
state **18%**, and the intent derives it from exactly the 81 → 8 collapse above. The
intent's own text anticipates the later bands — *«انهيار 90%، ثم ترتفع ثانية»*, a 90%
collapse, then it rises again — so the author saw the tail and still took 18. The rule,
not the intent, is what is wrong.

The rule was not careless: it is correct on the synthetic fixture in Task 1.2, whose
comment reads *"the pilot's shape"*. But that fixture's tail band holds 5 items, below
`min_band_count`, where the real tail band holds 24. The fixture did not reproduce the
one feature that distinguishes the rules.

The difference is visible to the owner. At 18% he sees the 136 "above your policy"
items the intent publishes; at 26% he sees roughly a quarter of them.

## Decision

**The ceiling is the upper edge of the qualifying band with the greatest count.** Where
two qualifying bands tie, the **higher** edge wins.

The store's pricing policy is a mass, not a boundary: the band where that mass ends is
the policy's edge. A tail band that happens to empty out afterwards is not a second
policy.

Tie-breaking high follows from what the ceiling means. Everything at or below it is the
owner's deliberate pricing and must not be surfaced — that is F1's central correction,
that 79% of his catalogue is priced identically and most of the rest sits inside a
policy he chose. A distribution with two equal masses has both inside that policy, so
the ceiling is the top of the upper one. Taking the lower edge would surface an entire
mass of his normal pricing as questions, which is the exact failure this feature exists
to prevent. Task 1.2's fixture is such a distribution — two qualifying bands of 81 — and
it expects 18, the higher.

## Rejected options

### The LAST qualifying collapse (the implemented rule)
Yields 26% on the pilot export, contradicting an `Approved` intent and spec and the
figures script that reproduces them. A 24-item tail band outvotes the 81-item mass that
*is* the owner's policy. It passes the synthetic fixture only because that fixture's
tail is too small to qualify.

### The FIRST qualifying collapse
Yields 18% on the pilot export — the right answer, for the wrong reason. It returns
**2%** on Task 1.2's own fixture, because any early band that happens to be followed by
an empty one wins. Correct on one dataset by luck is not a rule.

### Raise `min_band_count` until the tail band stops qualifying
Fits the parameter to one store's export. It would need re-tuning for the next store,
and D-12's single-store scope is a sequencing decision, not a licence to hard-code this
one's shape into the engine.

## Consequences

**We accept:** ties need a stated rule, and one is given above. A store whose policy
mass genuinely is not its densest band would be read wrongly — no such distribution has
been observed, and AC-005's undetermined path still covers a distribution with no
qualifying collapse at all.

**We gain:** one rule that reproduces **18%** on both Task 1.2's fixture and the real
pilot export — the only one of the three that does. Robustness to tail noise, which is
where a price file is noisiest.

**We will know it was wrong if:** a pilot store's derived ceiling sits visibly above the
band where the bulk of its markups stop, or the owner says the surfaced "above policy"
set contains prices he set deliberately.

## Confirmation owed before the pilot

Accepted with one condition. The rule derives 18% from the owner's distribution; it does
not establish that 18% is the policy **he believes he has**. The derivation is evidence of
his behaviour, not a statement of his intent, and F1's whole correction rests on the
difference between the two.

Before the figures are put in front of him, he confirms the ceiling — tracked as
[GAP-011](../../features/gaps-and-open-questions.md). If he names a different number, that
is not a defect in this rule: it means his behaviour and his policy have diverged, which is
itself the most useful thing F1 could tell him.

## Binds

| F# | How this constrains it |
|---|---|
| F1 | The ceiling reported by AC-004, and the population AC-008's density guard measures, are both computed under this rule |
