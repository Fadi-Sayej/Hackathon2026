---
ID: F<#>-INTENT
Title: F<#> — <feature name>
Status: Draft
Owner: smartshelf-pm
Release: V1 | V2 | V3 | V4
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-<###>
Specs: [F<#>-S<#>](specs/F<#>-S<#>-<slug>.md) | none
Inputs: [docs/product/PRD.md, docs/product/intent-register.md]
Updated: <date>
---

# F<#> — <العنوان بالعربية> · <English name>

> **House structure: Problem · User · Solution · Not In Scope · Related.** F1 … F13 all
> carry these. Keep the owner's words in Arabic, as the existing intents do. Do not
> introduce a different set of headings.

> **If the feature cannot be specified yet**, set `Status: Registered — not specified`,
> title the third section `## Solution (direction only)`, and add a
> `## Blocking product decisions` section naming the `GAP-` id. F8, F9 and F10 are the
> worked examples. That status is a deliberate state, not an unfinished one — it tells
> the architect a spec is **forbidden**, not merely pending.

## Problem

<Who is stuck, on what, and what it costs them today. Quote the owner in their own
language.>

## User

<Who this is for, and where they are when they reach for it. One named person.>

## Solution

<What the product does about it. Where an earlier claim was wrong, say so and show what
the data revealed instead — that correction is the most valuable paragraph in the file.>

**Every figure here is read from an artifact, and says which one.** CLAUDE.md rule 11.
CLAUDE.md rule 8 binds this section: never sum a per-sale figure with a one-off one, no
shekel figure on a quantity-derived signal, and **no number** rather than zero where a
number cannot be stated honestly.

**Success — countable within a week of the owner using it:**
<the observable signal, the number, and the artifact it is read from. Nothing finer than
monthly (CLAUDE.md rule 13).>

## Not In Scope

<At least two related problems deliberately left unsolved, each with its reason. This is
what the architect is forbidden from quietly including.>

## Related

- Depends on <F#> for <what>.
- Sibling of <F#> — <why they share a signal>.

## Settled decisions this depends on

| D-id | What it settles | Why this feature depends on it |
|---|---|---|
| D-<n> |  |  |

## Open questions

| GAP-id | Question | Who can answer it |
|---|---|---|
| GAP-<n> |  | owner / architect / data |
