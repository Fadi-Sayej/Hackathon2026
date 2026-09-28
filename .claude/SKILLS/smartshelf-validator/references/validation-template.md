---
ID: F<#>-VALIDATION
Title: F<#> — <feature name> · validation
Status: Draft
Owner: smartshelf-validator
Parent: [F<#>-S<#>](../features/F<#>-<slug>/specs/F<#>-S<#>-<slug>.md)
Inputs: [docs/features/F#-*/specs/F#-S#-*.md, docs/product/PRD.md, docs/features/F#-*/intent.md, docs/operations/deployment.md]
Updated: <date>
---

# Validation F<#> — <feature name>

Deployed URL: <url>
Commit: <sha>
Date: <date>

## Pass one — conformance

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §15 | AC-<###> |  | met / partial / missing | <file path · test name · URL and date> |
| spec §7 | INV-<###> |  | met / partial / missing |  |
| spec §20 | boundary probe |  | met / partial / missing | <probe output> |
| spec §21 | claim limit |  | honoured / violated |  |
| spec §19 | INT-<###> | traced to an AC- line? | met / partial / missing |  |
| PRD §7 | owner commitment | only if this feature changes what the owner must do | met / n-a |  |

### Scope drift

| File changed | In the plan task's `Files:` list? | In spec §3 scope? | Note |
|---|---|---|
|  | yes / no | yes / no |  |

### Shipped but never requested
- <anything present that no spec or PRD line asked for>

---

## Pass two — fidelity

Read only `docs/features/F<#>-<slug>/intent.md`. The PRD and the spec are closed.

**PROBLEM:** <quote it> — is the owner measurably less stuck?
<answer>

**SUCCESS:** <quote it> — count it. What is the number?
<answer>

**USER:** would the owner recognise this as built for them, in their language?
<answer>

**NOT NOW:** did anything deferred get built anyway?
<answer>

**Would you write the same intent again?**
<answer>

---

## Pass three — usefulness

Read from the artifacts. Name the artifact for every number.

| Question | Answer | Read from |
|---|---|---|
| Entries this feature contributes to the daily surface today |  | `public/data/dashboard.json` → `capabilities.<id>.entries` / `counts`; or the source `*.parquet` |
| `generated_at` of the artifact you read |  | `public/data/dashboard.json` |
| Does that count match what the approved intent and spec say it should be? | yes / no — <both numbers> |  |
| What changes when the signal is turned off |  | `npm run check:signals` output |
| Every figure obeys rule 8 (kinds not summed · no shekel figure on a quantity signal · no number rather than zero) | yes / no |  |
| Anything claimed that the monthly data cannot support (rule 13) |  |  |

> If turning the signal off changes nothing, the feature is **not delivered**, whatever
> the tests say. Record that as a missing verdict, not a note.

---

## What surprised me
<one or two sentences — usually the most valuable part of this document>

## Not checked, and why
<what this validation did not cover. A clean report with nothing here is a suspicious
report.>

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
|  | smartshelf-pm / -architect / -engineer / -platform |  |
