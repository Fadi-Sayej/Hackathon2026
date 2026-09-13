# SmartShelf Deployment

This is the B-1 deployment runbook for the current Vite app.

## Decision

- Provider: Vercel.
- Release source: `main`.
- Build command: `npm run build`.
- Install command: `npm ci`.
- Output directory: `dist`.
- Access protection: Vercel Routing Middleware with HTTP Basic Auth.
- Production deploy command: `npx vercel deploy --prod`.
- **Use `npx`, not a global install.** `npm i -g vercel` fails on macOS with
  `EACCES: permission denied, mkdir '/usr/local/lib/node_modules/vercel'`, and
  `sudo npm i -g` is not the fix — it leaves root-owned files in a system
  directory and causes worse problems later. `npx vercel` needs no install.
- Rollback command: `vercel rollback <deployment-url-or-id>`.

Vercel was chosen because this repository is a static Vite app, the Vercel CLI is already available
on the deployment machine, and Vercel supports Vite builds, SPA rewrites, environment variables,
HTTPS, deployment URLs, and rollbacks.

## Pilot prerequisites — verified status

Task 0.13's checkpoint. First run 2026-09-12 had three of five; re-verified **2026-09-13**,
now **five of five**. The two that were outstanding were console actions, not code, and
both have since been done.

| # | Prerequisite | Verified | Evidence |
|---|---|---|---|
| 1 | Six `VITE_FIREBASE_*` values present; `VITE_STORE_ID` matches `firestore.rules` | **pass** | `npm run check:firebase` exits 0, store id `yomyom-kafr-qasim` |
| 2 | Anonymous sign-in enabled; rules allow a write and read-back | **pass** | `npm run check:firebase-live` — sign-in ✅, write+read ✅, probe cleaned up |
| 3 | The engine pulls owner state with the service account | **pass** | `_pull_owner_state()` → `available`, `data/owner/owner_state.json` written |
| 4 | `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD` set in Vercel for Production **and** Preview | **pass** (2026-09-13) | `npx vercel env ls` lists both, both environments, created 35d ago. Confirmed live, not just present: `curl https://hackathon2026-fadi19.vercel.app` → **401**, which is the gate working. A 503 would mean a variable was missing |
| 5 | GitHub secret `FIREBASE_SERVICE_ACCOUNT_JSON` for a read-only service account | **pass** (2026-09-13) | `gh api repos/Fadi-Sayej/Hackathon2026/actions/secrets` → `total_count: 1`, `FIREBASE_SERVICE_ACCOUNT_JSON` |

### What items 4 and 5 cost while they were unmet

Kept here because both failure modes are silent and will look the same if either is ever
unset again.

**4 — Basic Auth.** `middleware.ts` fails closed: with either variable unset every request
returns HTTP 503 (design §11.7). The failure is safe but **total**, and invisible until
someone opens the URL. An unset pair takes the pilot app down on the day it is shown.
`curl` the URL and read the status code — 401 is healthy, 503 is a missing variable.

**5 — the CI secret.** Without it the nightly workflow cannot pull owner state, so every
CI-produced artefact carries `owner_state: unavailable` and `owner_questions` publishes
`unavailable: answer_storage_unavailable`. The engine is honest about it — it does not
invent an empty answer set — but the owner is never asked a cost question by anything CI
builds.

### Running the engine with credentials

`scripts/run_engine.py` reads `FIREBASE_SERVICE_ACCOUNT_PATH`. Without it the run is
`degraded` and says why; with it the run is `ok`:

```bash
FIREBASE_SERVICE_ACCOUNT_PATH=./secrets/firebase-service-account.json \
  python3 scripts/run_engine.py --skip-market
```

`secrets/` is gitignored and stays that way. The path is never committed, and the CI
equivalent is the `FIREBASE_SERVICE_ACCOUNT_JSON` secret in item 5.

## Required Vercel Environment Variables

Set these in Vercel before any preview or production deployment:

| Name | Environment | Purpose |
|---|---|---|
| `BASIC_AUTH_USER` | Preview and Production | Login username for the pilot URL. |
| `BASIC_AUTH_PASSWORD` | Preview and Production | Login password for the pilot URL. |
| `VITE_LLM_PROXY_URL` | Optional | HTTPS URL for the deployed LLM proxy. Leave unset to use rule-based explanations. |
| `VITE_FIREBASE_*` | Optional (B-2) | Client Firebase web config to activate Firestore persistence + cross-device telemetry. Unset ⇒ localStorage only. Also enable Anonymous sign-in and deploy `firestore.rules` (`firebase deploy --only firestore:rules`). |
| `VITE_STORE_ID` | Optional (B-2) | Firestore store namespace (default `yomyom-kafr-qasim`). |

The middleware fails closed: if either Basic Auth variable is absent, every request returns HTTP 503
instead of serving store data publicly.

Do not commit passwords, API keys, cookies, Vercel project metadata, `.env`, `.env.local`,
service-account files, or `.vercel/`.

## Data Refresh

The committed bundle already contains the real YomYom product catalog in `src/data/demoProducts.js`.
That is enough for the deployed app to show real product names, categories, prices, and inventory.

**Since the Task 2.7 cut-over, the artefact the owner reads is
`public/data/dashboard.json`,** not `operational.json`. `loadDashboard.js` is the only
adapter a V1 page uses; nothing reachable from the nav imports `loadOperationalData`.

**Decision: option 1 — the generated `public/data/*.json` files are committed.** Option 2 is not
available: Vercel's build image has no Python, no pyarrow, and no `data/**` parquet (all gitignored),
so it cannot regenerate the JSON. Option 3 waits on B-2/B-6. Committing the artifact is what makes a
clean Vercel build produce a working site, and `nagham.md` B-1 is explicit that the pilot cannot
depend on someone's laptop.

Read from `public/data/dashboard.json` on 2026-09-13 (schema 2, generated
2026-09-12T13:21:36Z) — **3,533 entries** across seven capabilities:

| Capability | Status | Entries |
|---|---|---|
| `catalogue_lifecycle` | available | 1,632 |
| `hygiene` | available | 1,187 |
| `reconciliation` | available | 439 |
| `price_consistency` | available | 199 |
| `margin_below_cost` | available | 71 |
| `competitor_position` | available | 5 |
| `owner_questions` | available | 0 |

**Refreshing is automatic.** `collect-daily.yml` runs the engine nightly and commits
`public/data/dashboard.json` and `market-context.json`; the push makes Vercel redeploy.
That commit step was added 2026-09-13 — before it, the nightly published the artefact into
the runner's workspace and threw it away, so the owner's screen only ever changed when a
human committed one by hand.

To refresh by hand for a release:

```bash
python3 scripts/import_yomyom_pos.py --input yomyom-inventory.csv   # POS CSV → silver parquet
npm run data:refresh                                                # → public/data/dashboard.json
git add public/data/dashboard.json public/data/market-context.json
git commit -m "data: refresh the engine artefact"
git push                                                            # Vercel redeploys
```

`public/data/operational.json` and `sources.json` are **frozen** and no longer refreshed.
`refresh_pipeline.py` stopped running on 2026-09-13: its `product_recommendations` step
required `silver_pos/yomyom_sales.parquet`, which Task 0.6 deleted on purpose because its
`units_sold_30d` was synthesised from a monthly mean (rule 13). Frozen is the correct state
for a rollback target — see §20.2. Phase 4 deletes the chain.

`vercel.json` serves `/data/*` with `Cache-Control: no-store`, so a redeploy is picked up
immediately rather than serving a manager yesterday's actions.

Do not implement the runtime-fetch split from Issue #24 as part of B-1.

## Verification Checklist

Before promoting a production deployment:

- `npm ci`
- `npm test`
- `npm run test:py`
- `npm run test:pipeline`
- `npm run lint`
- `npm run build`
- `git diff --check`
- `vercel deploy --dry`
- `vercel deploy --prod`

After deployment:

- Unauthenticated request returns `401` when auth is configured.
- Missing auth variables return `503`, never public app data.
- Authenticated request returns the app HTML.
- HTTPS is active.
- Browser refresh and direct routes load the SPA.
- Static assets load behind auth.
- No `localhost` URLs are present in built client assets.
- Real YomYom data is visible.
- Phone QA passes on a real phone.
- Tablet QA passes on a real tablet.
- Rollback is tested with `vercel rollback <deployment-url-or-id>`.

## Internal telemetry page (B-3)

The build emits a second entry, `telemetry.html`, from the same `vite build` (multi-page input in
`vite.config.js`). It is served at **`/telemetry.html`** on the same deployment, behind the same
Basic Auth gate — Vercel serves the built file directly (the filesystem is checked before the SPA
rewrite), so no `vercel.json` rewrite change is needed. It is the internal read-only pilot
dashboard (alerts shown vs acted-on, acceptance by type, ₪ impact). It reads decisions from
Firestore when `VITE_FIREBASE_*` is set, otherwise from that device's localStorage.

> **It has measured nothing since the cut-over (verified 2026-09-13).** Three independent
> breaks, each of which alone is enough:
>
> 1. `TelemetryDashboard.jsx` reads `public/data/operational.json`, **frozen** at `f5406a0`
>    on 2026-09-12 and never rebuilt again by design (CLAUDE.md rule 5 — it is the §20.2
>    rollback target). `dashboard.json` moved on and moves nightly.
> 2. `telemetryModel.js` joins shown-to-decided by `id`, and the two sets no longer share an
>    id namespace: the frozen set holds 4,495 rows keyed the pre-ADR-009 way
>    (`CHECK_WOLT_PRICE_GAP`, `WATCH_PRODUCT`, …), while the owner is shown 3,534 entries
>    keyed `sha256(signal_family ‖ barcode ‖ variant)` (`price.inverted`,
>    `recon.impossible_opening`, …).
> 3. It reads decisions through `src/lib/persistence/persistence.js` — the pre-V1 store.
>    The V1 app writes one key, `smartshelf.ownerState.v2`.
>
> So whatever `/telemetry.html` displays is a still photograph of the pre-cut-over pilot,
> and **PRD §8's 30-day go/no-go has had no working instrument since 2026-09-12.** The
> decision taken on 09-13 is to rebuild it against the artefact rather than delete it; until
> that lands, do not read numbers off this page.

## Custom Domain

Use the default Vercel deployment URL until the DNS owner confirms a custom subdomain. Do not point
customer traffic at an unprotected or unverified domain.
