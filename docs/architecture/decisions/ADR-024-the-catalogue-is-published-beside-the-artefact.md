---
ID: ADR-024
Title: The product catalogue is published beside the artefact, not inside it
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-16
Parent: [System Design](../system-design.md) §7.3, §20.2
Related Specs: F1-S1, F3-S1, F4-S1
Inputs: [ADR-001, ADR-005, ADR-019, ADR-020, ADR-022, docs/architecture/system-design.md §7.3, CLAUDE.md rules 5, 8, 13]
Updated: 2026-09-17
---

# ADR-024 — The product catalogue is published beside the artefact, not inside it

**Status:** Accepted (2026-09-17, by the repository owner) · proposed by `smartshelf-engineer`
and held at `Ready for review` until he decided it, because a role may not approve its own
output (HANDOVER rule 2). Asked and answered directly rather than relayed.

## Context

The owner asked for the pre-V1 nav back. Several of the returning pages need **every
product**, not only the ones with a finding against them: Prices reads price, cost and the
competitor position for a product the owner looks up; Products is a browse list; Overview
counts across the catalogue.

`dashboard.json` cannot answer that. It publishes **findings** — seven capabilities of
per-signal entries, bounded by ADR-020's published-population policy. The 2026-09-16
nightly carries 3,464 entries against a resolved population of 7,523 products. A page
asking "what does the shop sell" is asking a different question from "what needs your
decision today", and the artefact has only ever answered the second.

So the product list has to be published. The decision is **where**.

## Decision

**A second file, `public/data/catalogue.json`, written by the same run, from the same
inputs, validated against its own schema, and fetched only by the pages that need it.**

### Why not inside `dashboard.json`

Measured on the pilot data, not estimated:

| | raw | gzipped |
|---|---|---|
| `dashboard.json` today | 4.34 MB | **245 KB** |
| the catalogue, 7,523 products | 1.73 MB | **182 KB** |

`loadDashboard.js` fetches the artefact on **every page load**, including the daily surface
— the screen the owner opens each morning, which needs no catalogue at all. Folding it in
charges 182 KB to every load of every page to serve three of them.

That argument was sharper still when this was decided: `vercel.json` served `/data/*` with
`Cache-Control: no-store`, so the cost recurred on every single open with no cache to
absorb it. #128 changes that header to `no-cache`, which lets an unchanged file answer
`304`. The conclusion does not depend on which header is in force — it is the right call
either way, and it was the right call under the worse one.

### Why a second file does not re-open the split Phase 2 closed

CLAUDE.md rule 5 says: *"One pipeline. `public/data/dashboard.json` is what the owner
reads."* That rule is about **two pipelines writing two artefacts read by two spines** —
the `refresh_pipeline.py` / `operational.json` chain against the engine. It is not a rule
against a run publishing more than one file, and the engine already publishes
`market-context.json` from the same run.

The provenance property the rule protects is intact, and for a concrete reason: **the
catalogue carries no computed figure at all.** Every number the owner could ask about
still has exactly one place it came from. This file is the product list those numbers were
computed *over*.

### `inputs_digest` travels with it

The two files are fetched separately and a failed catalogue write leaves a stale one beside
a fresh artefact. So the catalogue carries the artefact's own `inputs_digest`, and a reader
can **prove** they came from one run instead of assuming it. This is not decoration: the
first consequence of the rule showed up immediately, in that a catalogue generated on a
developer's laptop had digest `f6e09b34…` where the nightly's artefact had `84081c63…`,
for identical product counts — the orphan-silver divergence CLAUDE.md rule 6 warns about,
made visible by the digest rather than shipped.

### It is sorted, and that is load-bearing

Sorted by `barcode`, then `product_name`. The nightly **commits** this file, so git stores
it once only as long as the bytes repeat night to night; emitted in reader order it would
differ invisibly every night and the repository would grow by ~1.73 MB a day for nothing.

A sort is deterministic only if its key is unique — `sorted` is stable, so equal keys keep
input order, and input order is whatever the parquet reader produced. **ADR-022 makes the
key unique** by identifying a barcode-less row by its name, so there is exactly one row per
`(barcode, product_name)`. Verified on the pilot: 7,523 rows, 7,523 distinct keys, and two
consecutive engine runs produce a byte-identical `products` array.

### What it contains, and what it deliberately does not

Exactly `EngineInputs.products` — the resolved population after ADR-019 and ADR-022 settle
conflicting duplicates. The same population every capability counts over, so the catalogue
page and the finding pages cannot disagree about what exists.

- Prices stay `null` where the export has none. **D-3**: a product with no shelf price has
  no shelf price, and `0` reads as free.
- `recorded_stock` is published raw, negatives included — F2's whole subject — and carries
  **no money figure**. **D-1**, and CLAUDE.md rule 8.
- **Both prices are the store's own.** `shelf_price` is its shelf; `delivery_price` is its
  own Wolt listing (`wolt_price` from the POS export). F1 exists *because* those two
  disagree. There is **no competitor price in this file** — F3 compares against rivals and
  is computed from scraped `observations`, which never reach it. The schema says so on the
  field itself, because the mistake is cheap to make and expensive to see: mapping
  `delivery_price` onto a competitor field lights a price-comparison page instantly and
  tells the owner a rival is undercutting him with his own price. Caught in review of the
  first adapter written against this schema, before it shipped.
- `products: null` when the engine could not load the population, never `[]`. An empty list
  is a claim about the shop; `null` is what happened. `count` is absent with it.
- An empty list **is** allowed when the engine loaded the population and it was empty —
  that is a fact it is entitled to state, which is why `count` has no `minimum: 1` here
  unlike ADR-021's device count.

**No velocity, and this is the honest bottom of it.** The reorder and planogram screens
rank by `salesLast7Days` / `salesLast30Days`. The sales tables are not missing — but they
are **monthly**, one row per product per month with no date column in any of the seven
reports, so a daily rate is **not measurable** (rule 13). The 30-day table that would
supply one existed and was deleted: `yomyom_sales.parquet`, whose `units_sold_30d` was
synthesised from a monthly mean (rule 5, Task 0.6). **Publishing this catalogue does not
change that and must not be read as a step toward it.**

### Failure is isolated

The catalogue is written **after** the artefact, as its own recorded step, and it does not
raise. The artefact is the owner's daily screen; the catalogue serves three secondary
pages. A run that cannot write the second must still have delivered the first, and must say
so in `run.steps` rather than swallow it. A schema breach refuses **before** the write, so
the previous catalogue survives — the pages would rather show yesterday's list than a
broken one, and the digest is what tells them which they are looking at.

## What it serves, and what it does not

**Serves:** Prices (F1, F3 — both `Approved`), Products (F4 — `Approved`), Overview.

**Does not serve, and the boundary should move only deliberately:**

| | why not |
|---|---|
| Assortment gaps | F9 is `Registered — not specified`. The blocking decision is what the owner is expected to *do* with "strong in the market, weak here" — and the gap rule would key on absence from the sales reports, which covers 5,848 of 7,463 products because the reports reach 24.3% of the catalogue (rule 13) |
| The written report | §20.1 REMOVE, and D-12 forbids a runtime server for one store. No document states what it should claim |
| Reorder, Approved orders, Store layout, Shelf plan | demand, not catalogue — see the velocity paragraph above. No catalogue lights them |

## Rejected options

### Fold it into `dashboard.json`
The obvious move. Rejected on the measurement: 182 KB gzipped charged to every load of
every page, including the daily surface, to serve three of them.

### Publish only the products a page asks for
A query API. Rejected by D-12 — no runtime server for one store — and it would make the
catalogue a different population from the one the capabilities counted over, which is the
one disagreement this file exists to prevent.

### Keep the pages on an awaiting state
What they do today, and it is honest. Rejected because the data exists, is already loaded
by every run, and three of the pages sit behind approved specs. An awaiting state for a
product list we are not waiting for is its own kind of lie.

## Consequences

**We accept:** a second published file, a second schema, one more thing the nightly commits,
and 182 KB gzipped for the pages that fetch it. The repository grows once, not nightly, and
only while the sort holds.

**We gain:** three restored pages behind approved specs can render real rows, and the
artefact stays what it is — findings, not data.

**We will know it was wrong if:** the catalogue and the artefact are ever observed with
different `inputs_digest` values on the deployed site, which would mean the two files are
drifting and the pages are showing a product list from a different run than the findings
beside it. That is detectable precisely because the digest is published, which is the point
of publishing it.

## Binds

| F# | How this constrains it |
|---|---|
| F1, F3 | Prices may read the catalogue; every figure it shows still comes from the artefact |
| F4 | Products may render the resolved population, ADR-019 and ADR-022 already applied |
| F8, F12 | Unchanged. Neither is unblocked by this, and neither may be read as unblocked by it |
