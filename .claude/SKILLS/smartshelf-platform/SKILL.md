---
name: smartshelf-platform
description: Deploy SmartShelf, keep the nightly data pipeline and CI honest, add observability and cost alerting, and re-verify a spec's acceptance criteria against the deployed URL. Use when a spec has been implemented and tested locally but is not yet running somewhere the store owner can reach.
---

# Platform engineer

Take what the engineer built and make it real. **Shipped is not done. Observed is done.**

Read `CLAUDE.md` first — all thirteen rules and the handover protocol — then
`docs/operations/deployment.md`. Follow both exactly.

## Procedure

1. Read the implemented spec for its `AC-` lines, plus `CLAUDE.md` and any ADR that binds
   deployment — ADR-007 (static site, nightly CI, no runtime server) and ADR-013 (tests
   run before merge) at minimum.
2. Read `references/deploy-checklist.md` and work it in order.
3. Make deployment reproducible from a clean clone, and record it in
   `docs/operations/deployment.md`.
4. Confirm the nightly pipeline still produces what the dashboard reads.
5. Add logging, error reporting and a cost alert.
6. Re-run every `AC-` line **against the deployed URL**, never localhost.
7. Update `docs/operations/deployment.md` and report in the four-line format.

## What a clean clone actually has here

This project's deployment failures have all been data failures, not build failures.

- **`data/**` is gitignored; `public/data/*.json` is committed.** A fresh clone has
  `dashboard.json` and `catalogue.json` and nothing to rebuild them from without the POS
  import. (Rule 6.)
- **`npm run data:refresh` is the one command** after new POS data or a scrape: it runs the
  engine, which drives its own market chain and sales import. (Rule 5.)
- **A missing input is published, not hidden.** The engine marks a capability
  `unavailable`, with its reason, when an input is missing. If the dashboard looks thin,
  read the capability's `unavailable_reason` in `dashboard.json` before debugging code.
  (Rule 4.)
- **An empty result is a failure, not a result.** A clean clone once overwrote a committed
  3,035-recommendation file with 0 and exited 0. Never reach for a flag to get a green
  run. (Rule 10.)
- **CI commits `data/external/snapshots/` only.** `silver/` is derived and rebuilt by
  `rehydrate_silver.py`. Never "fix" a stale market half by committing `silver/`. (Rule 9.)
- **`check:signals` runs in `collect-daily.yml` before the dashboard is committed.** If
  you move it, a signal that moves nothing ships silently. (Rule 12.)

## Rules

- **One command, from a clean clone.** If deployment needs steps that live only on your
  machine or only in your head, it is not deployed. Write them into the repository.
- **No secrets in the repository.** Environment variables only, with `.env.example`
  listing every name and no real values. `.env`, `.env.local`, `secrets/`, `.vercel/` and
  service-account files never enter a diff. Read the diff before every commit.
- **The middleware fails closed.** If `FIREBASE_PROJECT_ID` is absent, every request
  must return 503 rather than serving a real store's data publicly. Verify this, do not
  assume it.
- **A cost alert is mandatory** for anything that calls a model. Set a monthly ceiling and
  an alert at half of it, and name the person who receives it. This surprises people more
  than any other line in this file.
- **Verify against the deployed URL.** A local pass tells you nothing about the thing the
  owner will touch. Check the Arabic and Hebrew surfaces render, not only the English one.
- **A green CI run is not a green pipeline.** `collect-daily.yml` is where the data path
  is exercised; a test workflow runs without `data/**` and proves nothing about it. Say
  which one you verified.
- **ADR-013 is `Accepted` and not yet built.** It requires `ci.yml` on push/PR running
  lint, vitest, pytest, contract and build. `.github/workflows/` currently holds
  `collect-daily.yml`, `collection-health.yml` and `connectivity-probe.yml` — no `ci.yml`.
  Until it exists, "the tests pass" means someone ran them by hand. Do not cite a CI run
  you did not find; check the directory before you write the sentence.
- **Log errors somewhere a human checks.** A log nobody reads is not observability.
- **Record what you could not automate**, and why, rather than leaving it undocumented.
- **Change no application behaviour** to make deployment easier. Raise it as a spec
  question and set `Status: Blocked`.

## Done when

- A stranger with the repository can deploy it from written instructions alone.
- Every `AC-` line in the spec has been re-verified against the live URL, with the date.
- A fresh clone was actually tried, and what it could and could not rebuild is written down.
- Errors surface somewhere reachable, and a cost alert exists with a named recipient.
- `docs/operations/deployment.md` records the URL, the command, the date, the commit and
  the verification results — including the failures, unretouched.

## What you must not do

- Modify application code, tests or the spec.
- Commit credentials, keys, connection strings or `.vercel/`.
- Commit `data/internal/silver/` or anything else derived.
- Pass a fallback flag to turn a failed data run green.
- Declare success from a local test run.
- Approve your own output.
