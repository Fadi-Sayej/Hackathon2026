---
ID: F13-VALIDATION
Title: F13 — Pilot Measurement · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F13-S1](../features/F13-pilot-measurement/specs/F13-S1-pilot-measurement.md)
Inputs: [docs/features/F13-pilot-measurement/specs/F13-S1-pilot-measurement.md, docs/features/F13-pilot-measurement/intent.md, docs/architecture/decisions/ADR-023-the-engine-publishes-the-pilot-measurement.md, docs/architecture/decisions/ADR-029-two-roles-sign-in-and-the-gate-enforces-them.md, src/engine/measurement.py, schemas/measurement.schema.json, src/telemetry/, src/lib/dataAdapters/loadMeasurement.js, tests/engine/test_measurement.py, src/telemetry/__tests__/, src/__tests__/middlewareSignIn.test.js, GitHub deployment records (Production)]
Updated: 2026-09-28
---

# Validation F13 — Pilot Measurement

- **Deployed URL:** `https://hackathon2026-fadi19.vercel.app/telemetry.html` (team accounts only; ADR-029).
- **Commit in production:** `2a716ec` (F13 merged as #231, `9ee163c`). GitHub deployment `6708764605`, `success`, 2026-09-28 11:29Z.
- **Artefact read:** none yet. `public/data/measurement.json` is first written by the nightly of 2026-09-29; until then the page says it is not published. A print-mode run on 2026-09-28 was read instead (see Pass three).
- **Context:** built on 2026-09-28, the day after the pilot with the YomYom store ended (D-23), with no success number (D-24).

## Verdict

**Conformance is met on every criterion, in tests and in the build; nothing has run on real
data yet.** F13 measures what the pilot was for: what the owner was shown and what he decided.
Its first real reading, on 2026-09-29, will be the pilot's own answer to the question its intent
asked after 30 days, and this record cannot contain it. **Pass three must be re-run then.**

---

## Pass one — conformance

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §15 | AC-130 | reads `measurement.json` only; no device owner state, no `operational.json`; the owner cannot fetch it | **met** | `TelemetryDashboard.test.jsx`, "reads the measurement file and no owner state"; `operational.json` deleted (#231); `middlewareSignIn.test.js` lists `/data/measurement.json` among the team-only paths |
| spec §15 | AC-131 | joined on `entry_id`, counted by the snapshot's `signal_family` | **met** | `test_measurement.py`, "counts each status per family and in total" |
| spec §15 | AC-132 | shown, decided, acted, dismissed, deferred, not in this run, per family and in total | **met** | `test_measurement.py`; the page, "lists each family with what it showed and what was decided" |
| spec §15 | AC-133 | money = acted decisions' snapshot values, per kind and certainty, never summed across | **met** | `test_measurement.py`, "money comes only from acted decisions that froze one", "never sums two kinds or two certainties"; the page, "one row per kind and certainty, never a total over them" |
| spec §15 | AC-134 | unavailable owner state → unavailable, no count; nothing decided ≠ all dismissed | **met** | `test_measurement.py`; the page, "says it is unavailable, with the engine's reason", "says nothing is recorded yet"; the schema forbids counts when unavailable |
| spec §15 | AC-135 | a decision whose entry this run does not publish is counted, not dropped | **met** | `test_measurement.py` (`not_in_this_run`); `test_run_capabilities.py`, "the measurement is its own file beside the artefact" |
| spec §15 | AC-162 | no money on a decision that carries none: no ₪, no zero, no blank | **met** | The page, "says nothing is recorded yet … no ₪0"; "no acted-on decision carries money yet" |
| spec §15 | AC-163 | window, the run counted, device count; no target | **met** | The page, "names its window, the run it counted and the devices, and no target" |
| spec §7 | INV-066 … INV-068 | | **met** | INV-066 as AC-133, AC-162; INV-067 as AC-130 (the page imports no owner state and writes nothing); INV-068 as AC-134 |
| spec §19 | INT-MEAS | traced to an AC | **met** | §2 names AC-130 … AC-135, AC-162, AC-163 |

### Scope drift

Built by Phase 4 Task 4.5 (#231) against its `Files:` list. One departure, recorded in the task:
the list first named a block inside `dashboard.json`; it was built as its own file because
ADR-029 Decision 6 requires it. The approved page removed "Recent decisions", "Ignored" and the
10% wrong-data target; the owner approved the screenshots on 2026-09-28.

### Shipped but never requested

Nothing.

---

## Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F13-pilot-measurement/intent.md`.*

**PROBLEM (after 30 days of V1, how many ₪ recovered make the pilot a success, and who measures
it?): is the owner measurably less stuck?** The second half is answered: the engine measures it,
every night, and the team reads it. The first half was dissolved by D-24: there is no success
number, only how much success there is.

**SUCCESS — count it.** The intent's three outcomes after 30 days: the number met, a
subscription; not met but daily use, review the intents together; no use, stop honourably.
With D-24 there is no number to meet, and with D-23 there is no store to continue with. What
remains countable is use, and that is exactly what the first `measurement.json` will state: how
many entries the owner decided, acted on and dismissed over the whole pilot. **Not countable
today.**

**USER: the owner and the team together, in the decision to continue.** The page is team-only
(D-22), in English. The owner will not see it, and after D-23 there is no decision to continue
to take with him.

**NOT NOW / what the intent left open:** nothing deferred was built. The intent's three numbers:
the success number is gone (D-24), the price waits (D-24), the cadence waits for another store
(D-23) and was not needed for the build.

**Would you write the same intent again?** For the next store, yes, without the ₪ total over
three components: OQ-801's answer (money only where a decision carries it) should be in the
intent, not only in the spec. The intent's body still says F13 is "deliberately NOT specified",
and still lists ARCH-GATE-003 as open; both stopped being true on 2026-09-28.

---

## Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| On real data | **not yet published**: the first file is written by the nightly of 2026-09-29 | `public/data/` at `2a716ec` |
| A print-mode run, 2026-09-28 | 3,380 entries shown, 0 decided | `run_engine(mode="print", skip_market=True)["measurement"]`, reading the committed owner-state mirror of 2026-09-12 (no credentials here), so the decisions count is the mirror's, not Firestore's |
| Matches the intent? | Its question (did the pilot help) will be answerable on 2026-09-29, as use, not as ₪ against a target | Pass two |
| Turned off | Without the owner state it is `unavailable` with the reason, and states no count | `test_measurement.py` |
| Rule 8 | **yes**: money one row per kind and certainty; nothing stock-derived | `schemas/measurement.schema.json`, tests |
| Rule 13 | not engaged | — |

---

## Pass three, re-run 2026-09-29

Read from `public/data/measurement.json` at `b215b0c`, `generated_at 2026-09-29T03:52:33Z`, `status: available`,
the owner state pulled from Firestore at 03:52:34Z.

| Question | Answer | Read from |
|---|---|---|
| Shown in this run | 3,523 entries | `totals.shown` |
| Decided over the whole pilot | **1** | `totals.decided` |
| Acted on / dismissed / deferred | **0 / 0 / 1** | `totals` |
| Which | one `price.inverted` entry, deferred on 2026-09-17 09:47Z | `by_family`, `window` |
| Money recovered | none: no acted-on decision carries money | `money: []` |
| Devices that wrote owner state | 4, last seen 2026-09-24 | `devices` |

**This is the pilot's answer to its own question.** The intent's third outcome after 30 days is "no use,
stop honourably, having lost a month and not a year". The owner opened the app on four devices and
recorded one "Later". F13 measured it, as it was built to; the pilot had already ended (D-23).

## What surprised me

F13 is the only feature whose most important output does not exist yet, and the one output the
end of the pilot makes more important, not less: a count of what the owner actually did with
everything F1–F6 put in front of him.

## Not checked, and why

- `measurement.json` on real data, and the page on the deployed URL: neither exists before the
  2026-09-29 nightly, and the page needs a team sign-in.
- The live owner decisions: this machine has no Firestore credentials.

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| ~~Re-run Pass three on the 2026-09-29 nightly's `measurement.json`, and record the pilot's decision counts~~ **Done 2026-09-29** (above) | smartshelf-validator | The feature's first real output, and the pilot's answer |
| ~~F13's intent body still says "deliberately NOT specified" and lists ARCH-GATE-003 as open~~ **Noted 2026-09-29** in the intent | smartshelf-pm | Both stopped being true on 2026-09-28 |
| ~~Put OQ-801's answer (no composite; money only where a decision carries it) into F13's intent for the next store~~ **Noted 2026-09-29** in the intent | smartshelf-pm | The intent still asks for one ₪ figure over three components, which D-1 forbids |
| The implementation-readiness gate (and docs/README) still list ARCH-GATE-003 (no measurement surface) as the one open MAJOR | smartshelf-architect | F13-S1 and ADR-023 answer it; the gate should record that, or say what is still missing |
