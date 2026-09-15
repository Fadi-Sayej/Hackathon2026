---
ID: CHECKPOINT-3
Title: Checkpoint 3 — can a stranger reproduce the figures?
Status: Ready for review
Owner: smartshelf-engineer
Parent: [Phase 3](../implementation/phase-3-reproduction.md)
Inputs: [scripts/figures.py, public/data/dashboard.json, a fresh git clone of main @ 462d604, GitHub Actions run 34753047653]
Updated: 2026-09-15
---

# Checkpoint 3 — can a stranger reproduce the figures?

Run 2026-09-12 against a **real fresh clone** (`git clone` into an empty directory), not a
cleaned working tree.

## Verdict: reproduction works. The gate as written does not pass, for two stated reasons.

| Gate condition | Result |
|---|---|
| `npm run figures` exits 0 | **no** — exit 1, `owner_questions: answer_storage_unavailable` |
| under two minutes (NFR-060) | **yes** — **74s**, including rehydrating competitor silver from the committed snapshots |
| figures equal the committed artefact's | **not testable** — `dashboard.json` is not committed yet (Task 0.13 step 6 says not to; Task 3.4's workflow starts committing it) |
| figures equal a reference run | **yes** — 40 of 41 shared figures identical |
| `inputs_digest` matches | **not testable** for the same reason; `figures.py` now publishes it so the check is one diff once the artefact is committed |
| nightly green two nights running | **not yet** — Task 3.4 landed today |

## What a fresh clone actually has

1,325 committed files under `data/` — the market snapshots CI commits (rule 9). It does
**not** have `data/internal/silver_pos/`, which is derived and gitignored (rule 6).

So `npm run figures` on a clone exits **1 in 4 seconds** with `no_pos_data`. That is
**P3-OQ-2's answer, and it is not a defect**: the clone carries `yomyom-inventory.csv` and
the seven sales reports, so the import is two documented commands that take under two
seconds together.

```
python3 scripts/import_yomyom_pos.py --input yomyom-inventory.csv   # 0s
python3 scripts/import_yomyom_sales.py                              # 1s
python3 scripts/figures.py                                          # 74s
```

**Checkpoint 3 should say so** rather than implying a clone reproduces from nothing. The
reproduction claim is true; the precondition is two commands, and hiding it would make the
claim false the first time someone tried it.

## The comparison

41 figures on the clone against 46 locally. The five missing are all `owner_questions.*` —
the capability is unavailable without the service account, and the engine says so rather
than publishing an empty answer set.

**Of the 41 shared figures, 40 are identical.** The one difference:

| figure | local (credentialed) | fresh clone |
|---|---|---|
| `provenance.owner_state_available` | 1 | 0 |

Which is correct. It is the figure whose job is to report exactly that difference.

Notably `competitor_position` **does** reproduce: the signal chain rebuilds from the
committed snapshots (558,059 Alonit rows over 34 files, 7,348 Wolt rows over 314) inside
the 74 seconds. Nothing about the market half needs a credential or a network call.

## What blocks a green Checkpoint 3

1. **The service account.** `owner_questions` cannot run without it, so `figures.py` exits
   1 by design (§11.6: exit 1 naming the missing input). Task 0.13 step 5 — the CI secret
   — is still unset. **smartshelf-platform.**
2. **`dashboard.json` is not committed**, so AC-127's literal comparison has nothing to
   compare against. Task 3.4's nightly starts committing it; the check is then one diff.
3. **Two nights of green nightly** — Task 3.4 landed today.

None of these is a reproduction failure. The engine reproduces; the gate is waiting on a
credential, a first committed artefact, and two days.

## The question this raised, and how it was answered

§11.6 says exit 1 when any registered figure is unavailable. On a machine with no
credentials that is *always* true, so `npm run figures` could never exit 0 for anyone
outside the team — including a judge at the 12/9 meeting, who would run it, see `FAIL`, and
reasonably conclude the numbers do not reproduce, when 40 of 41 reproduce exactly.

**Answered 2026-09-12 in code rather than deferred to a decision.** "We could not compute
this from the data you have" and "this needs a credential you were not given" are different
sentences, and only the first is a reproduction failure. `figures.py` now separates them:

```
NOTE  owner_questions: answer_storage_unavailable — needs a credential this machine
      does not have; every other figure is unaffected
exit 0
```

A missing credential is reported and does not fail the command. A figure that genuinely
could not be computed still exits 1 and names itself. Verified by running with the mirror
removed and the environment variables stripped.

## Re-run under ADR-020

The gate's remaining blockers are now two, not three: `dashboard.json` is still not
committed (Task 3.4's nightly starts that), and two green nights have not happened. The
credential is no longer one of them.

---

# Run 2 — 2026-09-13, against commit `462d604`

`dashboard.json` is now committed **by the nightly** rather than by hand, so the two
comparisons that were "not testable" in run 1 are testable. Fresh `git clone` from GitHub
into an empty directory (865 MB), `npm ci`, no service account, every `FIREBASE_*`
variable stripped from the environment.

## Verdict: the engine reproduces exactly. One defect found and fixed; one condition still open, and it is a calendar rather than a bug.

| Gate condition | Run 1 (09-12) | Run 2 (09-13) |
|---|---|---|
| `npm run figures` exits 0 | **no** — exit 1 on a missing credential | **yes** — exit 0, credentials stripped |
| under two minutes (NFR-060) | yes, 74s | **yes — 83.8s** |
| figures equal the committed artefact's | not testable | **yes — 45 of 46 identical** (after the fix below) |
| figures equal a reference run | yes, 40/41 | yes |
| `inputs_digest` matches | not testable | **no** — see finding 2 |
| nightly green two nights running | not yet | **not yet** — see below |

The 46th figure is `provenance.owner_state_available`: same value on both (`1`), differing
only in the `pulled_at` timestamp inside it. That is the figure whose job is to report the
difference between a credentialed run and an uncredentialed one.

## What reproduced byte-for-byte

Read from the clone's own logs and parquet, against the nightly runner's logs for run
[34753047653](https://github.com/Fadi-Sayej/Hackathon2026/actions/runs/34753047653):

| Stage | Runner | Fresh clone |
|---|---|---|
| Silver POS | 7,674 products / 7,674 inventory / 7,674 margins | identical |
| Sales | 1,778 summary / 3,942 monthly rows | identical |
| Alonit load | 37 files, 561,508 rows after dedup | identical |
| Wolt load | 341 files, 7,448 rows after dedup | identical |
| Matching | 190,426 records (bc 182,038, nn 135, fuzzy 8,253), 5,738/7,674 matched, review 420 | identical |

Nothing in the market half needs a credential or a network call. The precondition is still
the two documented import commands (P3-OQ-2); a bare clone exits 1 in seconds with
`no_pos_data` for all seven capabilities, which is correct and should stay documented.

## Finding 1 — the reproduction command reproduced a different population. FIXED

`figures.py` defaulted `--population` to `living`. ADR-020 made the published population a
policy setting and `run_engine` honours it, but an explicit argument meant the policy never
applied — and policy says `whole`, because D-14 forbids putting a figure that depends on
automatic withdrawal in front of the owner while GAP-009 is open.

So the default run disagreed with the committed artefact on **22 of 46 figures**, and
exited 0:

| figure | published | reproduced |
|---|---|---|
| `price_consistency.population` | 5,986 | 2,466 |
| `price_consistency.identical` | 4,671 | 1,504 |
| `competitor_position.matched` | 2,621 | 1,713 |
| `competitor_position.comparable_population` | 6,801 | 3,108 |
| `margin_below_cost.below_cost` | 34 | 17 |
| `owner_questions.suppressed_withdrawn` | 0 | 1,206 |

Running `--population whole` made 45 of 46 match. Fixed in `8d4c2c8`: the default is now
`None` so policy decides, and the payload reports the population the run *used* rather than
the flag it was handed. `test_it_prints_the_engines_figures_and_recomputes_nothing`
asserted `population == "living"` — the test that should have caught this had locked it in,
and now asserts against policy.

## Finding 2 — `inputs_digest` does not match although every figure does. OPEN

The digest is AC-127's mechanism: "reproduced" is meant to mean the same inputs produced
the same output, checkable by one comparison rather than by eye. On run 2 all 46 figures
match and the digest does not:

```
published   9682a62b2c9f6bb7f9d4127377d951dcecf333ee2df5bf0d29dadc188f9eccc4
reproduced  40d30874ee0b91e0d7f5c5190be9d7407c9c3fd2025de8187189329af3b3de14
```

It is not the obvious causes. `_digest` already excludes `owner.pulled_at`, `_imported_at`,
`_source_kind` and `created_at`; `_source_file` holds a bare filename, not a machine path;
`products`, `sales_monthly` and `policy` hash identically between two independent
checkouts; and the digest is stable across repeated runs on one machine. A per-barcode
comparison of `sales_summary` between two checkouts found **no differing column** while the
component hashes differed, so the remaining suspect is how rows are shaped or serialised on
the way into the hash rather than the data itself.

**This matters more than it looks.** A digest that reports a difference when no published
number differs is a false alarm, and a false alarm that fires every time teaches everyone
to ignore it — which is exactly the failure rule 12 describes, one level up. Either the
digest becomes something two honest runs agree on, or AC-127 should stop claiming it as the
comparison. **smartshelf-architect.**

## What still blocks a green Checkpoint 3

> ## ✅ Nothing. Met 2026-09-15.
>
> The calendar condition came in. Two consecutive **scheduled** runs, both green, both
> committing the owner's artefact:
>
> | Run | Started | Result | Artefact |
> |---|---|---|---|
> | [34799925663](https://github.com/Fadi-Sayej/Hackathon2026/actions/runs/34799925663) | 2026-09-14T02:39Z | success | `4645cd5 engine: artefact for 2026-09-14` |
> | [34922204888](https://github.com/Fadi-Sayej/Hackathon2026/actions/runs/34922204888) | 2026-09-15T02:42Z | success | `7361454 engine: artefact for 2026-09-15` |
>
> Every step passed on both nights, including the three blocking probes — `check_v1_signals`,
> `check_independence` and `check_signals_live` — and `check:rules`, which ran for the first
> time on 09-14 and found no drift either night.
>
> The 09-13 re-run is deliberately **not** counted: the condition is two consecutive
> *scheduled* runs, because what it proves is that the nightly works unattended.
>
> **Phase 4 is unblocked.** It was the only thing holding it.

**The condition as it stood (2026-09-13).** Two consecutive green nightlies. The 2026-09-13
scheduled run failed (see [the incident record](nightly-2026-09-13-incident.md)); the
dispatched re-run after the fix was green. The next scheduled run is 2026-09-14 at 00:00
UTC, and a second on 2026-09-15.

Finding 2 is not a blocker as the gate is written — AC-127's digest line was already marked
"not testable", and every figure it is meant to guard now matches — but it should not be
called green either. Recorded, assigned, not hidden.
