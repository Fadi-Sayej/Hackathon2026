<!-- Paste this section into CLAUDE.md, unchanged. -->

## Artifact chain and handover protocol

SmartShelf is built by a chain of roles. Each role reads files, writes files, and stops.
**No role calls another role.** The artifact is the interface.

### The chain

```
docs/product/PRD.md                                (the root product document)
   └─ smartshelf-pm        → docs/product/PRD.md · docs/product/intent-register.md
                           → docs/features/F#-<slug>/intent.md          (one per feature)
                           → docs/features/gaps-and-open-questions.md
                           → docs/product/open-decisions/F#-<slug>.md   (one per blocked feature)
      └─ smartshelf-architect → docs/architecture/system-design.md
                              → docs/architecture/decisions/ADR-NNN-<slug>.md
                              → docs/features/F#-<slug>/specs/F#-S#-<slug>.md   (on request)
                              → docs/implementation/plan.md
         └─ smartshelf-engineer   → source code and tests
            └─ smartshelf-platform → docs/operations/deployment.md, live URL
               └─ smartshelf-validator → docs/reviews/F#-validation.md
```

### The identifier travels

`docs/product/PRD.md` is the root document. Every feature in its register has an `F#`.
That id travels: feature `F3` becomes intent `F3`, spec `F3-S1`, validation `F3`.

Requirement identifiers **inside** a spec — `FR-…`, `INV-…`, `NFR-…`, `AC-…`, `SCN-…`,
`C-…`, `ASM-…`, `OQ-…` — are globally unique across the whole specification layer and are
**never renumbered**. The System Design §21 traceability matrix, the gate reports and the
implementation plan all cite them. If you need a fully-qualified form, prefix with the
spec id: `F1-S1.FR-001`.

Anything without a traceable id does not belong in this repository.

### Authority hierarchy

When two documents disagree, the one **higher** in this list wins. It is reproduced from
[`docs/README.md`](../docs/README.md), which is the canonical copy.

1. PRD, and the settled decisions `D-1 … D-34` in the intent register §3
2. Feature intents
3. Approved feature specs
4. System Design
5. ADRs
6. Implementation plan
7. Code — evidence of what exists, never product authority

`docs/archive/` is **LEGACY — NON-AUTHORITATIVE**. No role reads it to decide anything.

### Every artifact carries a status header

Every generated document starts with this block, and nothing else may precede it. It
extends the header style already in use across `docs/` with three fields the protocol
needs — `Owner`, `Inputs`, `Updated`:

```yaml
---
ID: F3-S1
Title: Competitor Price Position
Status: Draft
Owner: smartshelf-architect
Parent: [F3 — Competitor Price Position](../intent.md)
Inputs: [docs/product/PRD.md, docs/features/F3-*/intent.md, ADR-001, ADR-011]
Updated: 2026-09-12
---
```

Existing approved documents already carry `ID`, `Title`, `Status`, `Parent` and often
`Version`. **Do not restructure them.** Add the missing fields when you next touch a file
for another reason; never in a commit of its own.

### The status vocabulary

These are the values actually in use in `docs/`. A role reads the **first word** and
ignores any trailing explanation — `Approved — passed the Intent → Spec conformance gate`
is `Approved`.

| Status | Means | May a downstream role start? |
|---|---|---|
| `Approved` | Settled. Intents and specs use this. | Yes |
| `Accepted` | Settled. **ADRs use this instead of `Approved`** — ADR-001 … ADR-039 all do. | Yes |
| `Registered — not specified` | The intent is settled, and writing a spec is **deliberately forbidden** until a named decision is taken. F10, F11 and F14 are in this state. | **No** — and not because it is unfinished. Point at the blocking `GAP-` id and stop. |
| `Living` | Continuously updated by design; never "finished". The gaps register is one. | Yes, as a reference — never cite it as settled |
| `Partial — <what is missing>` | Part written, part not. The implementation plan is here. | Only for the parts named as written |
| `Proposal — <what must confirm it>` | Not yet product authority. | No |
| `Draft` | Being written. | No |
| `Ready for review` | A role finished and handed over. Awaiting a human. | No |
| `Blocked` | Stopped on a question that is not the author's to answer. | No |
| `Superseded` | Replaced. Carries `Superseded-by:`. | No — follow the pointer |

**`Accepted` and `Approved` are the same gate.** If you treat an ADR's `Accepted` as
"not approved" you will block the whole chain on all thirty-nine of them.

### The handover rules

1. **A role may only start when every input it needs is `Approved`.**
   If any input is `Draft`, `Ready for review` or `Blocked`, stop and say which file and
   what state it is in. Do not proceed on an unapproved input.

2. **A role may never set its own output to `Approved`.**
   When you finish, set `Status: Ready for review` and stop. Approval is a human act.
   This is the gate. Marking your own work approved removes it.

3. **Hand over only when the task is ready.**
   Before setting `Ready for review`, verify your own skill's "Done when" list and state
   the result item by item. If any item fails, set `Status: Blocked`, write why under a
   `## Blocked on` heading, and stop.

4. **Unanswered questions block the chain.**
   If you cannot complete the artifact without a decision that is not yours to make, set
   `Status: Blocked` and list the questions. Never guess and continue.

5. **Stay in your lane.**
   Write only the artifacts your role owns. If you find a fault in an upstream document,
   report it — do not edit it. Corrections go back to the role that owns that file.

6. **Traceability is mandatory.**
   Every artifact names its `Inputs` and carries the `F#` of the feature it serves. An
   artifact whose id appears nowhere upstream is scope drift, and gets reported.

7. **Superseding, never overwriting.**
   When a decision changes, set the old artifact to `Superseded`, add
   `Superseded-by: <path>`, and write a new one. History is evidence — that is why
   `docs/archive/` still exists and still carries its banner.

8. **A figure is quoted from the artifact that produced it, never from another document.**
   This is CLAUDE.md rule 11, and it binds every role, not just the engineer. Counts in
   this repository have drifted by a factor of five between the markdown and the parquet.
   Read the parquet, the JSON or the test output. Cite where you read it.

### Commits are part of the handover, not a step after it

A role's output is not handed over until it is **committed**. The artifact is the
interface (above), and an uncommitted artifact is not an interface — it exists only in one
working tree.

- **One unit of work, one commit.** A plan task, an ADR, a spec, a validation record.
  Never batch several into one, and never split one across two.
- **Verified first, committed second.** Whatever your skill's "Done when" list requires
  must pass *before* the commit, not after it. A red or unrun suite is not committed.
- **Stage by path.** `data/` and `public/data/` are written as a side effect of running
  the engine; `git add -A` sweeps them in. Name the files your task named.
- **A correction to an upstream defect is its own commit**, with a message saying what was
  wrong and how the fix was verified. Those commits are why the code and the documents
  diverged, and they are the first thing a reviewer looks for.
- **Branch; do not commit to `main`.** Do not push, open a PR or merge unless asked.
- The `NEXT:` line of your four-line report is written **after** the commit exists.

### What to say at the end of every run

Finish every run with exactly these four lines:

```
ARTIFACT:  <path you wrote>
STATUS:    Ready for review | Blocked
DONE-WHEN: <each item, met or not met>
NEXT:      <the role that should run next, and what it needs from the human first>
```
