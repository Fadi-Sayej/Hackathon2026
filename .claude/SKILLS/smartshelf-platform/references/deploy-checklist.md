# SmartShelf deployment checklist

Work it in order. A box is ticked only after you ran the thing, not after you read it.

## Reproducibility
- [ ] Clean clone builds using the documented commands only (`npm ci`, `npm run build`)
- [ ] Python runs from the repo root, with `python3` — there is no virtualenv (rules 1, 2)
- [ ] All configuration comes from environment variables
- [ ] `.env.example` lists every variable name, with no real values
- [ ] The deploy and rollback commands are written in `docs/operations/deployment.md`

## Data path — where this project's deploys actually fail
- [ ] A clean clone was actually tried, and what it can and cannot rebuild is written down
- [ ] `public/data/operational.json` is present and committed; `data/**` is gitignored (rule 6)
- [ ] Every directory the exporter globs exists — a missing one yields a silent
      `competitorSignals: 0`, not an error (rule 4)
- [ ] `npm run data:refresh` was run in full after new POS data or a scrape, not
      `data:dashboard` alone (rule 5)
- [ ] The export was non-empty; no fallback flag was used to make it pass (rules 7, 10)
- [ ] `silver/` was rebuilt by `rehydrate_silver.py`, not committed (rule 9)
- [ ] `npm run check:signals` runs in `collect-daily.yml` **before** the dashboard is
      committed (rule 12)

## Access and secrets
- [ ] Basic Auth credentials set for Preview and Production
- [ ] Middleware verified to fail closed — missing credentials return 503, not store data
- [ ] No `.env`, `.env.local`, `secrets/`, `.vercel/`, key or service-account file in the diff
- [ ] The diff was read before the commit, not after

## Observability
- [ ] Application errors reach a place a human actually checks
- [ ] Request logs carry a timestamp and an identifier
- [ ] Model calls log token usage
- [ ] The nightly workflow reports failure somewhere visible, not only in the Actions tab

## Cost
- [ ] Monthly ceiling set on the model account
- [ ] Alert configured at 50% of the ceiling
- [ ] A named person receives that alert

## Verification
- [ ] Every spec `AC-` line re-run against the deployed URL, never localhost
- [ ] The Arabic and Hebrew surfaces checked, not only the English one
- [ ] `.github/workflows/` was listed, and which workflow was verified is stated —
      `collect-daily.yml` is where the data path is exercised; a test workflow that runs
      without `data/**` proves nothing about it
- [ ] ADR-013 (`ci.yml` on push/PR: lint, vitest, pytest, contract, build) is confirmed
      present — or its absence is recorded as a finding, not passed over. It was
      `Accepted` and had not been built as of 2026-09-12
- [ ] Results recorded in `docs/operations/deployment.md` with the date and the commit
- [ ] Failures written down rather than retried until green
