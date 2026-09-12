# PRD sections the pm owns

The PRD already exists at `docs/product/PRD.md`. **Do not restructure it.** These are the
shapes to match when adding to it.

## Feature register row

| F# | Rank | Feature | Serves | Release | Intent |
|---|---|---|---|---|---|
| F<#> | <n> | <name, no technology> | <journey or owner commitment> | V1 | `docs/features/F<#>-<slug>/intent.md` |

## Acceptance row

Every criterion is countable by a person, on the deployed URL, without reading code.

| F# | Countable criterion | How it is counted |
|---|---|---|
| F<#> |  | <artifact or screen the count is read from> |

## Not in scope

| What | Why it was deferred | Revisit when |
|---|---|---|
|  |  |  |

## Constraints

Technology named by the user goes **here**, as a note for the architect — never into a
feature row or an intent.

| Constraint | Source | Note for the architect |
|---|---|---|
|  | owner / regulation / budget / data |  |

## Risks

| Risk | Likelihood | What would tell us early |
|---|---|---|
|  |  |  |

## Open decisions

A decision that is settled moves to the intent register §3 and gets a `D-` id. One that is
not stays here, named, with who must take it.

| Question | Owner | Blocking which F# |
|---|---|---|
|  |  |  |
