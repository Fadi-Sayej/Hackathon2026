# SmartShelf Deployment

This is the B-1 deployment runbook for the current Vite app.

## Decision

- Provider: Vercel.
- Release source: `main`.
- Build command: `npm run build`.
- Install command: `npm ci`.
- Output directory: `dist`.
- Access protection: Vercel Routing Middleware that verifies a Firebase sign-in and its role
  (ADR-029). It replaced HTTP Basic Auth on 2026-09-26.
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

Items 2 and 4 describe the site before ADR-029's sign-in. On 2026-09-26 anonymous sign-in was
disabled and the Basic Auth variables and code were removed; what replaced them is under
[Switching to sign-in](#switching-to-sign-in-adr-029).

### What items 4 and 5 cost while they were unmet

Kept here because both failure modes are silent and will look the same if either is ever
unset again.

**4 — the access gate.** `middleware.ts` fails closed: without its variable every request
returns HTTP 503 (design §11.7). The failure is safe but **total**, and invisible until
someone opens the URL. It takes the pilot app down on the day it is shown. Until 2026-09-26
the variables were `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD`; since then it is
`FIREBASE_PROJECT_ID`. `curl` a data file, `/data/dashboard.json`, and read the status code:
401 is healthy, 503 is a missing variable.

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
| `FIREBASE_PROJECT_ID` | Preview and Production | `hackathon26-a6ebd`. The edge gate checks a sign-in was issued for this project; unset, every request is a 503. |
| `VITE_AUTH_MODE` | Preview and Production | `firebase`. The build shows the sign-in screens; unset, the app skips sign-in and the gate refuses it every data file. |
| `VITE_FIREBASE_*` | Optional (B-2) | Client Firebase web config to activate Firestore persistence + cross-device telemetry. Unset ⇒ localStorage only. Also deploy `firestore.rules` (`firebase deploy --only firestore:rules`), the role rules of ADR-029. |
| `VITE_STORE_ID` | **Production `yomyom-kafr-qasim`; Preview `preview-sandbox`** | Firestore store namespace (code default `yomyom-kafr-qasim`). The two environments differ **on purpose** — see below. |

### Switching to sign-in (ADR-029)

> **Switched over on 2026-09-26**, on the repository owner's decision to go before every
> account had its role:
> - Preview and Production carry the variables below.
> - `firestore.rules` is the role ruleset, and is deployed.
> - Google and email-link sign-in are enabled, and anonymous sign-in is disabled.
> - The same day, on the same decision, step 7 was done without waiting the day: the Basic
>   Auth variables and code are gone, and `middleware.ts` no longer reads `AUTH_MODE`.
> - The steps below are kept as the record.

ADR-029's code shipped **switched off**. Until the switch-over the site kept Basic Auth and
anonymous Firebase. The switch was three environment variables, one rules deploy and a few
console steps, in this order. Only the repository owner can do the console and Vercel steps.

| Variable | Value | Read by |
|---|---|---|
| `AUTH_MODE` | `firebase` | the edge gate, until step 7 removed the switch; no longer read |
| `VITE_AUTH_MODE` | `firebase` | the app build, for the sign-in screens |
| `FIREBASE_PROJECT_ID` | `hackathon26-a6ebd` | the edge gate, to check a token was issued for this project |

1. **Firebase console, once.**
   - Authentication → Sign-in method: enable **Google**, and enable **Email/Password** with
     **Email link (passwordless sign-in)**.
   - Authentication → Settings → Authorised domains: add `hackathon2026-fadi19.vercel.app`
     and the preview domain you rehearse on.
2. **Rehearse on a preview.** Set the three variables for **Preview** only and redeploy a
   preview. Previews use store id `preview-sandbox`, which the rules refuse (below), so
   nothing touches the pilot's data.
3. **Everyone signs in once there**: the two team members, then the owner. Each sees "This
   account has no access".
4. **Give each account its role**, with the service account the nightly uses:
   `python3 scripts/set_user_role.py <email> team` for each team member, and
   `python3 scripts/set_user_role.py <email> owner` for the owner. Check one with `--show`.
   No email is written anywhere by this.
5. **Check on the preview.** Reload the page.
   - A team account lands on `/telemetry.html`, and sees the owner's app read-only.
   - The owner lands on his app, and `/telemetry.html` refuses him.
6. **Switch production, in one sitting.**
   - Deploy the role rules, and commit them so the nightly's drift check (#97) agrees:
     `cp firestore.roles.rules firestore.rules && firebase deploy --only firestore:rules`,
     then commit `firestore.rules`.
   - Set the three variables for **Production** and redeploy.
   - Between the rules deploy and the redeploy, the live app's anonymous saves are refused,
     so keep that gap short.
7. **After a day of normal use**:
   - disable **Anonymous** sign-in in the console;
   - remove `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD` and `AUTH_MODE`;
   - remove the Basic Auth branch of `middleware.ts`.

**Rolling back.** There is no password gate to switch back to: step 7 removed it. If sign-in
breaks, fix it forward. A Vercel deployment keeps the variables it was built with, so
`vercel rollback` to a deployment from before the switch-over still runs the password gate, but
it serves that day's data, and its anonymous Firestore saves are refused by the role rules.

### Preview must not be able to write the pilot's data (2026-09-13)

**Production and Preview carry the same six `VITE_FIREBASE_*` values.** Verified with an
unfiltered `npx vercel env ls`: every one is set for both environments. A filtered
`vercel env ls production` looks like Production-only and is not.

`firestore.rules` pins writes to exactly one store — `match /stores/yomyom-kafr-qasim/{document=**}`
at line 45, with `match /{document=**} allow read, write: if false` at 49–50 catching
everything else. So while both environments shared a store id, **a preview deployment of any
branch could write the pilot's owner state.**

Harmless until #94's write-through lands, because nothing wrote at all. The moment #95
merges it becomes real, and the damage is quiet: a test answer entered on a preview closes a
real owner question, and the engine uses that cost from then on with nothing on the owner's
screen to say why.

**Isolation, applied 2026-09-13 on the owner's decision:** Preview's `VITE_STORE_ID` is
`preview-sandbox`. Writes from a preview no longer match line 45, fall to the catch-all, and
are **refused by the server** rather than by anyone remembering. Production was not touched —
it is still the original Secret, created 35 days ago.

```
VITE_STORE_ID   Config   Preview      preview-sandbox     ← changed
VITE_STORE_ID   Secret   Production   (unchanged, 35d)
```

**The rules that are actually in force were the load-bearing unknown, and they are now
checked — nightly.** The isolation is only as good as the deployed ruleset, and nothing
deployed or verified it: `firebase deploy --only firestore:rules` is run by hand.

Settled 2026-09-13 by reading the deployed ruleset rather than inferring it:

```
project:  hackathon26-a6ebd
release:  cloud.firestore -> 7447070e-16cd-473a-863b-fa5c7f75bd48
deployed: 2026-08-09T11:50:54Z
OK    the deployed ruleset is byte-identical to firestore.rules
```

So the deny branch really is in force, and `preview-sandbox` really is refused. The
isolation above is not decorative.

`npm run check:rules` (`scripts/check_firestore_rules.py`) does this, and
`collect-daily.yml` runs it every night. It is **read-only** — it reads the released
ruleset from `firebaserules.googleapis.com` and diffs the text. No document is touched and
no anonymous user is created, which is why it was preferred to a client `getDoc` probe
against `stores/preview-sandbox/…`: that settles the same question but connects to the
production project as a new anonymous user.

Exit codes are three sentences, not two: `0` identical, `1` drifted with the diff printed,
`2` the credential or API refused — reported as a warning, because *"we could not look"* and
*"a rule changed"* must never look alike. Verified in all three directions, including by
loosening the local catch-all to `if true` and confirming the diff names that line.

**Two limits on what a green `check:rules` means. Neither is obvious from the name.**

*It proves the project the engine reads, not the one the browser writes.* The check
authenticates with the service account and asks `hackathon26-a6ebd` about its own rules. It
never sees Vercel's `VITE_FIREBASE_PROJECT_ID`, so it cannot tell you the bundle in the
owner's browser is built against that same project. Only #96 step 2 settles that — the
document actually appearing under `stores/yomyom-kafr-qasim/ownerState/answers` after a
real answer. Do not read today's green as covering it.

*It is in the wrong place in the nightly, and is moving.* It currently runs **before**
"Commit the owner's artefact", so a rules drift would stop the owner getting correct data
for a reason that has nothing to do with whether that data is correct. That is precisely
the fault this workflow was restructured to remove on 2026-09-13 — the engine used to sit
behind a gate for a chain it did not use. The other three probes belong before the commit
because they establish the artefact is *right*; this one establishes who may write to
Firestore, which is real and unrelated. Tracked as **#97**, deliberately not changed on the
night Checkpoint 3's first gate run happens: the ruleset is byte-identical, so the check
cannot fire for drift, and editing the nightly on gate night buys nothing.

**`npm run check:firebase-live` does not settle this** (it was removed on 2026-10-01: it signed in anonymously, which is disabled since 2026-09-26), and should not be read as though it
does. It writes, reads and deletes a probe document against the **pilot** store, so it
exercises the *allow* branch for `yomyom-kafr-qasim` and says nothing about whether any
other store is denied. The isolation rests on the *deny* branch.

One thing this still does **not** prove, and it belongs to whoever signs #96:

1. **That the deployed browser bundle targets `hackathon26-a6ebd` at all.** Likely — the repo
   names no other project — but unproven, and **not checkable from the CLI**: these are
   Secret-type, and `vercel env pull` returns one identical 11-character placeholder for
   every Secret value. Comparing those placeholders reports a match for any two secrets, and
   comparing a placeholder against a real name reports a spurious mismatch. Never settle this
   from `env pull`. The Vercel dashboard may not settle it either — Secret values are often
   non-readable after creation.

   **There is a route, and it takes half a minute in a browser.** Vite bakes the config into
   the built JavaScript, so the deployed bundle carries the project id *in plain text*. It is
   not a secret: it is already in `.firebaserc` and `collect-daily.yml`. Confirmed against a
   local build — `hackathon26-a6ebd` appears three times in the telemetry chunk:

   | Entry | `projectId` | `initializeApp` |
   |---|---|---|
   | `index.html` — the owner's app | 0 | 0 | 
   | `telemetry.html` | **present** | 2 |

   `index.html` carries no Firebase at all, which is #94 restated from the other end, and it
   stays that way until #95 lands. So today the check must use `/telemetry.html`:

   > Open the pilot URL, sign in, go to **`/telemetry.html`**. DevTools → **Sources** →
   > search all files for `hackathon26`. Whatever project id appears there is the one the
   > browser writes to. If it is not `hackathon26-a6ebd`, the engine and the browser are
   > looking at different databases and **#94's write-through would fail in a third way** —
   > everything green, nothing arriving, for a reason no probe here would catch.

   Neither session can run it: `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD` are not in `.env`,
   so the protected site is unreachable from a terminal here. It needs whoever has the
   sign-in. After #95 merges, #96 step 2 settles the same question more directly, by a real
   answer appearing under `stores/yomyom-kafr-qasim/ownerState/answers`.

The middleware fails closed: if `FIREBASE_PROJECT_ID` is absent, every request returns HTTP 503
instead of serving store data publicly.

Do not commit passwords, API keys, cookies, Vercel project metadata, `.env`, `.env.local`,
service-account files, or `.vercel/`.

## Data Refresh

The deployed app carries no product data of its own. It reads the catalogue from
`public/data/catalogue.json` and its findings from `public/data/dashboard.json`, both written
by the engine and committed by the nightly. The bundled demo catalogue,
`src/data/demoProducts.js`, was removed on 2026-09-24 (ADR-028).

**Since the Task 2.7 cut-over, the artefact the owner reads is
`public/data/dashboard.json`,** not `operational.json`. `loadDashboard.js` is the only
adapter a V1 page uses; nothing reachable from the nav imports `loadOperationalData`.

**Decision: option 1 — the generated `public/data/*.json` files are committed.** Option 2 is not
available: Vercel's build image has no Python, no pyarrow, and no `data/**` parquet (all gitignored),
so it cannot regenerate the JSON. Option 3 waits on B-2/B-6. Committing the artifact is what makes a
clean Vercel build produce a working site, and `nagham.md` B-1 is explicit that the pilot cannot
depend on someone's laptop.

### The nightly's artefact commit is authored by the repository owner (#167, 2026-09-26)

**Committing the artefact is not the same as serving it.** Vercel's Hobby plan builds a
commit only when its **author** is the account owner. `collect-daily.yml` committed as
`smartshelf-collector`. Measured on 2026-09-24 over 100 production deployments (GitHub's
deployment records, whose statuses Vercel writes):

- **0 of 22** collector commits deployed, every one `Deployment was blocked`;
- **78 of 78** human-authored commits deployed.

So a nightly artefact reached the owner only when a human merge happened to deploy `main`,
**6.7 to 88.8 hours** later.

**Tried first, and blocked: a Deploy Hook** (#172, 2026-09-24). A hook builds the head of
`main`, and the block looks at that head's author, so the hook's build of the collector's
commit was blocked as well. Vercel's Deployments page showed it on 2026-09-26: the push and
the hook build of `dbfe30b` were both **Blocked**. The step had been green because it only
checked that the hook queued a job.

**What settled it: a probe on 2026-09-26.** An Actions job pushed two empty commits to
throwaway branches. The one authored by the owner deployed; the one authored by the collector
was blocked. Vercel ignores the committer and the pusher. Every merge commit already showed
the committer part: `GitHub <noreply@github.com>` commits them, and they deploy.

Since then (the repository owner agreed on 2026-09-26):

- **The commit.** *Commit the owner's artefact* commits with
  `--author="Fadi-Sayej <sayejfadi2004@gmail.com>"`. The committer stays
  `smartshelf-collector`, so `git log --format='%an | %cn'` still shows that the nightly made
  it. A rebase onto a newer `main` keeps the author. A rebase that stops on a conflict fails
  the step and pushes nothing. It used to be ignored, and the step then reported a commit it
  had not pushed.
- **The snapshot commit stays the collector's.** Nothing under `data/` is in the built site,
  so its push has nothing to deploy, and its `Deployment was blocked` is expected.
- **The committer address.** Both commit steps use GitHub Actions' own no-reply address.
  Until 2026-09-26 they used `collector@users.noreply.github.com`, which is GitHub's old
  no-reply form for the account `collector` (id 1460107, a stranger's). So every nightly
  commit until then is attributed to that account on GitHub.
- **The check.** *Did Vercel deploy tonight's artefact?* runs after the health check, just
  before *Fail loudly*. It reads GitHub's deployment record for the exact sha pushed. It fails
  the night on `failure` or `error`, and fails it if there is no finished record after
  10 minutes (30 looks, 20 s apart). A failed API call counts as one more look. With no
  record for the sha, it also passes if the newest production deployment succeeded and
  contains the sha. That happens when another commit reaches production first: #201's merge
  (`639dc54`) never got a record, because #209 merged four minutes later. A record of the
  sha's own always wins, so a blocked artefact commit stays red.
- **The test.** `tests/test_nightly_deploy_step.py` runs both steps' own scripts. The commit
  step runs against a local bare repository; the check runs against stand-in `gh` and `sleep`.

**How to verify a night.** Read the *Did Vercel deploy tonight's artefact?* step of the
nightly run. Or read the record directly, as below: the `engine: artefact for …` sha should
be the latest `success`.

**When that step is red.** The artefact is on `main` either way; only the deploy is in doubt.
- *Deployment was blocked*: Vercel's author rule is no longer what this section says. Read
  #167 before changing anything. The next commit authored by the repository owner, such as any
  merge, deploys `main` with the artefact in it.
- *No finished production deployment*: look at Vercel's Deployments page for that sha.
- **Do not re-run the whole job to get a deploy.** A re-run collects again, and it starts from
  the original run's checkout, not from today's `main`.

**Left in place, unused:** the Deploy Hook `nightly` in Vercel and the repository secret
`VERCEL_DEPLOY_HOOK_URL`. Nothing calls either any more. Deleting the hook in Vercel (Settings
→ Git → Deploy Hooks) retires the URL, which can still start a build.

**What production serves, read without signing in.** The latest `success` in
`gh api "repos/Fadi-Sayej/Hackathon2026/deployments?environment=Production"` names the commit.
Read `public/data/dashboard.json` at that sha, not at `main`.

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
python3 scripts/import_pos.py                                       # POS export → silver parquet
npm run data:refresh                                                # → public/data/dashboard.json
git add public/data/dashboard.json public/data/market-context.json
git commit -m "data: refresh the engine artefact"
git push                                                            # Vercel redeploys
```

`public/data/operational.json` is **frozen** and no longer refreshed; `sources.json` was deleted on 2026-09-13 (ADR-005).
`refresh_pipeline.py` stopped running on 2026-09-13: its `product_recommendations` step
required `silver_pos/yomyom_sales.parquet`, which Task 0.6 deleted on purpose because its
`units_sold_30d` was synthesised from a monthly mean (rule 13). Frozen is the correct state
for a rollback target — see §20.2. Phase 4 deleted the chain on 2026-09-24; the file stays,
frozen, until F13 (#83) replaces the telemetry page that reads it.

`vercel.json` serves `/data/*` with **`Cache-Control: no-cache`**, so a redeploy is picked
up immediately rather than serving a manager yesterday's actions.

> **Changed from `no-store` on 2026-09-16.** The requirement above is right and is
> unchanged; `no-store` was simply a stricter header than it needs. The two differ in one
> way only: `no-store` forbids the browser from keeping a copy, so **every page load is a
> full download**; `no-cache` lets it keep one but forbids using it without asking the
> origin first. Both guarantee the owner never sees an artefact older than the last deploy.
>
> What it costs, measured on the committed artefacts at `8317d5e`: the V1 spine fetches
> `dashboard.json` through `loadDashboard.js`, which is **4.34 MB raw / 245 KB gzipped**,
> and under `no-store` he pays it in full every time he opens the app. The artefact changes
> **once a day**, when the nightly commits it. Under `no-cache` the second and later opens
> of the same day are a conditional request answered `304 Not Modified` — a few hundred
> bytes instead of 245 KB, with identical freshness.
>
> **The change is safe in the degenerate case.** If Vercel serves these files without a
> validator (`ETag` / `Last-Modified`), the browser cannot make the conditional request and
> re-downloads — exactly today's behaviour. So this either helps or does nothing; it cannot
> serve anything stale. **Worth confirming once on the deployed site:** a second load of the
> pilot URL should show `304` against `/data/dashboard.json` in the network panel. If it
> shows `200` every time, Vercel is not sending a validator and this is a no-op to revert.

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
sign-in gate, to team accounts only (ADR-029). Vercel serves the built file directly (the filesystem is checked before the SPA
rewrite), so no `vercel.json` rewrite change is needed. It is the internal read-only pilot
measurement (F13-S1): what the engine's latest run shows, and what the owner decided. It reads
`public/data/measurement.json`, which the nightly engine writes beside `dashboard.json`, and
computes nothing (ADR-023). The edge gate answers 403 to the owner for that file (ADR-029 §6).
Until the first nightly after 2026-09-28 writes it, the page says it is not published yet.

> **Rebuilt 2026-09-28 (#231).** The three breaks below are fixed: the page reads the
> engine's measurement, keyed by `signal_family` and entry id, over the owner's decisions as
> the engine pulls them from Firestore. `operational.json` and the pre-V1 store are deleted.
> What follows is the record of why it was rebuilt.

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

> **And the instrument is the smaller half. The input has never flowed at all** — found
> 2026-09-13, filed as **#94 (P0)**.
>
> The owner's answers and outcomes have never left his phone. Verified four ways rather
> than inferred:
>
> | Checked | Result |
> |---|---|
> | `src/owner/ownerState.js` | `localStorage` only — no Firestore call, no `fetch` |
> | the V1 spine (`main`, `App`, `surface/*`, `pages/*`) | imports nothing from `firebase` |
> | the owner's shipped bundle (`main-*.js`, `format-*.js`) | **zero** references to `firestore` / `initializeApp` |
> | `src/owner_state/pull.py` | reads `stores/{store}/ownerState`, which nothing in `src/` writes |
>
> The app cannot write to Firestore: Firebase is not in the bundle he downloads.
>
> **It does not look broken.** `recordOutcome` is `async`, validates `signal_family`
> (ADR-016), checks both enums, and builds a snapshot carrying certainty and
> characterisation — then writes `localStorage` and returns, never awaiting a network call.
> He taps done, the card leaves his list, the record dies in his browser.
>
> Two consequences worth stating plainly:
>
> 1. **Zero outcomes is structural, not disengagement.** With perfect engagement for thirty
>    days the count would still be zero, so PRD §8's number was never going to compute.
> 2. **`vintages.owner_state.reason: null` currently reads as healthy and is not.** That
>    field (859e053) distinguishes a replayed mirror from a live pull; it does not
>    distinguish a live pull that finds something from one that finds an empty collection.
>    Until #94 lands it is the most misleading field in the artefact.
>
> Design §3 — the verified current-state trace — had this right all along at line 229:
> outcomes and answers *"never leave the device"*. The write-through in §9.3, §9.4, §11.5
> and §20 is **target**, not built. Phase 2 Task 2.1 was meant to deliver it and did not;
> its Step 3 said to reuse `src/lib/persistence/*` unchanged, and that layer syncs
> different collections with different shapes, so it could never have satisfied §11.5.

## Prerequisite verification, 2026-09-13

Task 0.13's four non-code prerequisites, all re-checked against the live systems rather
than against this file's previous record of them.

| # | Prerequisite | State | Evidence |
|---|---|---|---|
| 1 | Firebase config, anonymous sign-in, rules deployed | **met** | verified live 2026-09-12 (P2-OQ-2); the nightly's `owner_state_pull` step is `ok` |
| 2 | `FIREBASE_SERVICE_ACCOUNT_JSON` repo secret, read-only role | **met** | present since `2026-09-12T15:09:22Z`. The 09-13 nightly published `vintages.owner_state = {status: "available", pulled_at: …}` with **no `reason`** — a live pull, not the committed replica |
| 3 | Vercel PR previews build | **NOT met — for collaborators** | Re-checked 2026-09-15 across authors: `Deployment was blocked` on #100, #102, #104 (`anasakkari3`); `Deployment has completed` on #95, #106 (`Fadi-Sayej`). The 09-13 "met" cited only owner-authored PRs |
| 4 | Basic Auth set in Vercel | **met, production** | `GET /` returns `401` with `www-authenticate: Basic realm="SmartShelf pilot"`. Also `401` on `/telemetry.html` and `/data/dashboard.json` |

> **On row 3, and how it was got wrong.** Three PRs were checked on 09-13 and all three
> passed, so the prerequisite was recorded as met. All three were opened by the repo owner.
> The prerequisite exists because a *collaborator's* PR was blocked, and that case was not in
> the sample — a filtered sample read as the whole. The same shape as the `vercel env ls
> production` reading recorded above: the filter, mistaken for the answer.

**Why the 401 is the proof and not merely a good sign.** `middleware.ts` fails **closed with
503** when `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD` are unset (design §11.7) — an unset pair
takes the pilot down rather than exposing it. A `401` with the realm is therefore positive
evidence that the pair is set, in a way that no amount of reading the Vercel console would
improve on. This closes ARCH-GATE-011.

**What this does not prove.** Production only. Preview and development environments are not
observable this way; if a preview deployment ever answers `503`, that is this same pair
missing on that environment, and it is a console fix rather than a code one.

> **Note on how this was found.** Both items had been recorded as outstanding since 09-12 —
> Basic Auth "unverified", the secret "confirmed absent". Both were in fact done, the secret
> within hours of that note. Nobody re-checked; the note was simply carried forward, and it
> reached an issue tracker from there. Rule 11 is usually invoked about figures. It applies
> to the state of the world too.

## Custom Domain

Use the default Vercel deployment URL until the DNS owner confirms a custom subdomain. Do not point
customer traffic at an unprotected or unverified domain.
