---
ID: OPS-NEW-STORE
Title: Setting up a new store's copy
Status: Ready for review
Owner: smartshelf-platform
Parent: [ADR-036](../architecture/decisions/ADR-036-a-store-is-configuration-one-copy-per-store.md)
Inputs: [D-28, ADR-036, ADR-029, ADR-030, ADR-033, docs/pilot/next-store.md, docs/operations/deployment.md, configs/store.yaml, scripts/new_store_copy.py, scripts/find_nearby_venues.py, scripts/check_store.py, scripts/check_firebase_config.mjs, scripts/set_user_role.py, .github/workflows/collect-daily.yml]
Updated: 2026-10-01
---

# Setting up a new store's copy

Each store runs its own copy of SmartShelf, with only its own data (D-28). That means its own:
- repository;
- Vercel project;
- Firebase project;
- nightly.

A copy is set up by configuration; no code changes (ADR-036). This guide goes from nothing
to the first nightly. [`docs/pilot/next-store.md`](../pilot/next-store.md) lists what to ask
the store for, and `npm run check:store` says at every step what is still missing.

## 1. Make the copy

From this repository:

```bash
python3 scripts/new_store_copy.py ../smartshelf-<store>
```

What the copy gets:
- **The code**, with one commit and no history.
- **None of this store's data:** no POS export, sales reports, snapshots, owner state,
  published artefacts or pilot documents.
- **Empty templates** of every store setting.
- **The nightly workflow, but not `ci.yml`.** Code is tested here before an update
  carries it.

The design documents stay and quote the pilot's figures as examples. They are the team's;
a store only ever sees its own site.

Create a private GitHub repository for the copy and push it there.

## 2. Say which store it is: `configs/store.yaml`

Fill every key. None is defaulted, and every tool stops on the first empty one.

| Key | What to put |
|---|---|
| `id` | The store's id: lowercase letters, digits and hyphens. It becomes the Firestore root |
| `name`, `site_title` | The store's name, and the browser tab's title |
| `location` | The store's latitude and longitude |
| `format` | One of `configs/store_types.yaml`'s formats. Ask the owner; never guess |
| `pos.export` | Where the inventory export will be committed, e.g. `<store>-inventory.csv` |
| `sales.monthly_dir`, `sales.daily_dir` | `data/internal/raw_pos/<store>/sales` and `…/sales_daily` |
| `market.radius_km` | How far to look for nearby venues (5 at the pilot) |
| `firebase.project_id` | The copy's Firebase project (step 3) |
| `site.address` | The address the site is opened at, without `https://` (step 4). Sign-in works only there, and the sign-in page links to it from any other address |

## 3. Firebase: the owner's decisions and the sign-in

1. Create a Firebase project. In it:
   - enable Firestore;
   - under Authentication → Sign-in method, enable Google, and Email/Password with its "Email
     link" option (ADR-029; passwords since 2026-10-03).
2. Put the project id in `configs/store.yaml` and in `.firebaserc`. Under Authentication →
   Settings → Authorised domains, add the site's address (`site.address`).
3. In `firestore.rules`, replace `set-to-the-id-in-configs-store-yaml` with the store's `id`.
   Then deploy the rules: `firebase deploy --only firestore:rules`.
4. Create a service account key and save its JSON as the repository's Actions secret
   `FIREBASE_SERVICE_ACCOUNT_JSON`. The nightly pulls the owner's decisions with it.
5. Give each account its role once it has signed in, with
   `python3 scripts/set_user_role.py <email> owner` or `… team`.

## 4. Vercel: the site

Import the repository as a new Vercel project. The variables are those in
[deployment.md](deployment.md#required-vercel-environment-variables):
- `FIREBASE_PROJECT_ID` and `VITE_AUTH_MODE=firebase`, for Preview and Production;
- the `VITE_FIREBASE_*` web config;
- `VITE_STORE_ID`: **Production is the store's `id`; Preview is `preview-sandbox`**. The
  rules refuse the sandbox, so no preview can write the owner's state.

Then check the Production values with `npm run check:firebase -- --env <file with them>`.
It compares the store id, the rules, the project and `.firebaserc` with `configs/store.yaml`.

On a Hobby plan, Vercel deploys only commits authored by the account's owner. The nightly
commits its artefact under the `--author` in `collect-daily.yml`'s commit step. Set it to the
Vercel account owner's GitHub identity.

## 5. The nearby market

```bash
python3 scripts/find_nearby_venues.py
```

It writes a review file under `reports/venues/`: the grocery venues within the radius,
nearest first. For each venue to collect:
1. Add it to `configs/delivery_targets.yaml`. Add the store's own delivery venue too, with
   `role: client`.
2. Record its format in `configs/store_types.yaml`, `verified: manual`. Ask when you do not
   know the format. An unclassified venue only ever counts as context: at the pilot, 57
   shops sat unused until they were classified (#250).
3. Give the store's own entries `role: client`.

## 6. The store's data

1. **Inspect the first export** with `python3 scripts/inspect_pos_file.py --input <file>`.
   If its column names differ from the pilot's, map them in
   `configs/pos_schema_mapping.yaml`.
2. **Commit the export** at `pos.export`, with `<export>.vintage.json` beside it:
   `{"as_of": "YYYY-MM-DD"}`, the day it was taken. The file cannot tell, so it is declared.
3. **Commit the monthly reports** in `sales.monthly_dir` with `git add -f`. The folder is
   ignored, as the pilot's was.
4. **Commit the daily reports** in `sales.daily_dir`. A plain `git add` takes them, one
   file per day (ADR-030).

## 7. What only the owner can say

- For each department: the days it is ordered, and how many days it keeps. Record them in
  `configs/store_facts.yaml`, with the date they were said (ADR-033).
- The shelves: fixtures, shelf lengths, departments and eye-level shelf, and the owner's
  arrangement rules, stated; product widths and today's facings, read from shelf photographs.
  Record them in `configs/store_layout.yaml`, which a new copy starts without (ADR-037).
- The owner's price rule: `price_policy_pct` in `configs/policy.yaml` is the pilot owner's
  +60%. Ask the new owner for theirs.
- GAP-009 and GAP-011 ([next-store.md](../pilot/next-store.md) §3).

## 8. Until nothing blocks

```bash
npm run check:store
```

For each input it says present, missing or stale, and names what a missing one keeps
unavailable. Optional: the market boost needs the Actions secret `ANTHROPIC_API_KEY`
(ADR-032).

The nightly runs on its schedule. After its first night, check that it succeeded. The site
then shows the store's own artefact, and `check:store` reports the collected venues.

## Later: bringing a copy's code up to date

From this repository, after a change has passed CI here:

```bash
python3 scripts/new_store_copy.py --update ../smartshelf-<store>
git -C ../smartshelf-<store> diff        # review, then commit and push there
```

It writes the code and removes code this repository removed. It never touches the store's
data or settings.
