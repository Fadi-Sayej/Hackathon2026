---
ID: ADR-036
Title: A store is configuration, and each store runs its own copy with only its own data
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-30
Parent: [System Design](../system-design.md) §19
Related Specs: every F#-S# (each reads the store through its inputs); F13-S1; F8-S1 (D-18's market)
Inputs: [D-12, D-22, D-23, D-28, ADR-003, ADR-029, ADR-030, ADR-033, docs/pilot/next-store.md, src/engine/inputs.py, src/engine/run.py, src/common/paths.py, src/context/weather.py, scripts/import_yomyom_pos.py, scripts/import_yomyom_sales.py, configs/delivery_targets.yaml, configs/store_types.yaml, firestore.rules, scripts/check_firebase_config.mjs, .github/workflows/collect-daily.yml]
Updated: 2026-09-30
---

# ADR-036 — A store is configuration, and each store runs its own copy with only its own data

**Status:** Accepted (2026-09-30, by the repository owner: "approved") · **Recorded in:** [System Design](../system-design.md) §19

## Context

**D-28:** each store gets its own copy of SmartShelf with its own data, for privacy, and a
new store is set up by configuration, never by changing code.

On 2026-09-30 the product could not do that. It was built for one store, and that store's
identity was written into the code in about forty places:
- **Paths and file names.** `run.py`'s `SALES_DIR` is `raw_pos/yomyom/sales`. The engine
  reads `silver_pos/yomyom_products.parquet` and `yomyom_inventory.parquet`. The nightly
  imports `yomyom-inventory.csv`.
- **The store's format.** `inputs.py` hard-codes `OUR_FORMAT = "gas_convenience"`, which
  decides D-18's market and every competitor's affinity.
- **The store's identity.** `yomyom-kafr-qasim` is the default in `run.py`, the value the
  nightly sets, and the Firestore root `firestore.rules` pins. The client's catalogue id and
  delivery venue are YomYom's entries in `store_types.yaml` and `delivery_targets.yaml`.
- **The location.** YomYom's coordinates sit in `weather.py`'s defaults and in the comment
  that explains how `delivery_targets.yaml` was built by hand.

Privacy adds a second problem. YomYom's own data is committed in this repository: its POS
export, seven monthly sales reports, POS snapshots, the owner-state mirror and the published
artefacts. A copy made by cloning would hand all of it to the next store.

## Decision

### 1. One copy per store

A copy is a store's own:
- private repository;
- Vercel project;
- Firebase project (owner state and accounts, ADR-003 and ADR-029);
- secrets and nightly.

Copies share code and nothing else. This repository stays YomYom's copy and the place code
is written.

### 2. One settings file: `configs/store.yaml`

It states what makes a copy one store's:

| Key | Meaning |
|---|---|
| `id` | The Firestore root and the store's id everywhere (today `yomyom-kafr-qasim`) |
| `name` | The store's name, as the team and the setup guide use it |
| `site_title` | The browser tab's title, set into `index.html` at build (today "SmartShelf AI — YomYom pilot", the only place the app names a store) |
| `location` | `lat` and `lon`; used for the weather context and for finding nearby venues |
| `format` | One of `store_types.yaml`'s formats. Replaces `OUR_FORMAT` |
| `pos.export` | Path of the committed inventory export (today `yomyom-inventory.csv`) |
| `sales.monthly_dir`, `sales.daily_dir` | Where its monthly and daily reports are committed (ADR-030) |
| `market.radius_km` | How far the nearby-venue finder looks (§4) |
| `firebase.project_id` | The copy's own Firebase project (§1), added 2026-09-30 |

One loader, `src/common/store.py`, reads and validates it. Every store-specific reader goes
through it: the engine, the importers, the weather context, the build (the tab title), the
nightly (which sets `VITE_STORE_ID` from it), and `check_firebase_config` (which compares
`firestore.rules`' pinned root with it). A missing or invalid key stops the run with the
key's name; nothing is defaulted to YomYom's value.

> **Clarified 2026-09-30, in Task 7.1–7.2, before any code merged.** Three details changed
> while building:
> - **`client_store_ids` is not a key.** The store's own entries are already marked
>   `role: client` in `configs/store_types.yaml`, and the engine reads them there
>   (`client_store_ids()`). Listing them in the settings too would decide one fact twice.
> - **`firebase.project_id` is a key.** Each copy has its own Firebase project (§1), and the
>   nightly, the engine's owner-state pull and `set_user_role.py` all named this copy's
>   project in code. An environment naming a different project stops the run, as a
>   different `VITE_STORE_ID` does.
> - **The web build keeps its deployment's `VITE_STORE_ID`, and takes only the tab title
>   from the settings.** Preview's `VITE_STORE_ID` is `preview-sandbox` on purpose
>   (deployment.md), so that a preview of any branch cannot write the owner's state. Setting
>   the id from the settings at build would have undone that. `check:firebase` checks that
>   Production's id, `firestore.rules`' pinned root, `VITE_FIREBASE_PROJECT_ID` and
>   `.firebaserc` all match the settings. Unset, the browser writes nothing remotely; it no
>   longer falls back to YomYom's id.

The derived tables stop carrying a store's name. They become `silver_pos/products.parquet`
and `silver_pos/inventory.parquet`, because one copy holds one store.

### 3. Store data is listed, and a copy starts without it

`src/common/store.py` also holds the **store-data manifest**: every path that holds a store's
data or its owner's statements. For each path it says whether a new copy starts without it,
or with an empty template:

| Starts without | Starts with an empty template |
|---|---|
| the POS export and its vintage, `data/internal/**`, `data/owner/**`, `data/external/snapshots/**` (the market around another location), `public/data/*.json`, `docs/pilot/**` except `next-store.md` | `configs/store.yaml`, `configs/store_facts.yaml`, `configs/owner_answers.yaml`, `configs/store_policy.yaml`, `configs/measured_weights.yaml`, `configs/delivery_targets.yaml`, and `configs/store_types.yaml` (its scale and affinity kept, its stores emptied) |

`scripts/new_store_copy.py <dir>` writes the code into a new directory with a fresh history,
applying the manifest. `--update <dir>` later brings a copy's code up to date and never
touches a manifest path. Both refuse to run if the result would contain the source store's
`id` or `name` under a manifest path.

> **Clarified 2026-10-01, in Task 7.5.** The manifest as built, in `src/common/store.py`,
> differs from the table in three ways:
> - `configs/measured_weights.yaml` is left out rather than emptied. It is generated from the
>   store's sales by `analyse_sales_movement.py`, and nothing in the engine reads it.
> - `firestore.rules`, `.firebaserc` and `.env.example` start as templates, because they
>   pin this copy's store id and Firebase project.
> - `samples/**` is left out.
>
> A copy also leaves out `.github/workflows/ci.yml`. Many tests read committed store data a
> clean copy does not have, and a copy changes no code: code is tested here before `--update`
> carries it. The ignore rules follow any store's folder, not YomYom's.

### 4. Nearby venues are found, then confirmed by a person

`scripts/find_nearby_venues.py` takes the store's location and radius. It asks the delivery
platform's public venue listing for grocery venues, measures each venue's distance, and
writes the candidates to a review file. It never writes `delivery_targets.yaml`. The team
confirms the venues, and each venue's format is asked and recorded as `verified: manual`,
never guessed (D-23; #250 showed what an unclassified store costs). Tests run on a response
captured once from the live listing, never an invented one.

### 5. `npm run check:store` says whether a copy is ready

`scripts/check_store.py` validates the settings file and reports each input the store is
expected to supply, as present, missing or stale:
- the POS export, the monthly reports and the daily reports;
- the department facts;
- the client venue, and a format for each nearby venue;
- the Firebase and Vercel settings the nightly needs, by name only, never by value.

For each missing input it names the capabilities that stay unavailable, read from the
registry's `requires`. It is `docs/pilot/next-store.md` made executable.

### 6. The fake data goes

`scripts/generate_fake_yomyom_pos.py`, its mention in `README.md`, and `product_matching.py`'s
fallback to a sample CSV are removed (CLAUDE.md rule 7, D-23).

## Rejected options

- **Several stores in one app.** It would need store switching, per-store accounts and a
  per-store database layout, and it would put two stores' data one rule away from each other.
  The repository owner chose one copy per store (D-28).
- **Clone the repository and delete the old store's files by hand.** Every copy would depend
  on someone remembering about forty paths. The history would still carry the data.
- **Move every store file under one `store/` directory.** It is cleaner, but it moves files
  that half the documents and every script cite, in a phase that exists to change nothing
  visible. The manifest draws the same boundary without the move.
- **Default the settings to YomYom's values.** A copy that forgot a key would then run
  quietly on another store's identity. That is the failure this ADR exists to prevent.

## Consequences

- YomYom is the first store in `configs/store.yaml`. The proof that nothing changed for it:
  the engine run over the same data before and after publishes the same artefact, every
  capability's status, counts, entry ids and evidence, `assortment_gap`'s market prices
  included. Only the run's own time and id differ.
- A second store is set up by the guide in `docs/operations/new-store.md`: make a copy,
  fill the settings, find and confirm venues, commit the store's exports, set the accounts,
  and run `check:store` until nothing blocks.
- The design documents stay in every copy, and they quote YomYom's figures and product names
  as design evidence. They belong to the team, and a store only ever sees its own site.

## Reversibility

Easy for the settings file: it only moves constants. The manifest and the copy script are
additive. Renaming the silver tables is derived data, rebuilt every run.

## Binds

Every new store-specific value goes into `configs/store.yaml` or a manifest path, never into
code. A reviewer rejects a hard-coded store id, name, path, format or coordinate.
