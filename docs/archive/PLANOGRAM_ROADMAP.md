> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# Planogram Roadmap

How SmartShelf gets from a working greedy allocator to a planogram system worth
trusting, derived from the shelf-space-optimization literature (Corstjens &
Doyle; Lim/Rodrigues/Zhang; Hübner & Kuhn's CASRP; the 2025 column-generation
work) and from what the industry platforms — RELEX, Blue Yonder, DotActiv — treat
as part of the same problem.

The research describes a chain-scale system. **We are one store with partial
sales history** — 1,564 of 7,451 products carry usable velocity, the rest do not.
Most of the distance between those two facts is what this document is about:
which recommendations apply now, which are premature, and which are blocked on
data we do not have.

---

## 1. Where we actually are

Measured on the real catalogue (7,451 YomYom products), planning one 6m gondola
of `משקאות` (500 SKUs):

```
carried            100 products      (assortment decision)
not carried        400 products      (the recommendation)
facings            350               (range 3–12, capped)
shelf fill         99–100% per shelf
geometry estimated 0                 (department mapping resolved all 500)
```

| Layer | File | State |
|---|---|---|
| Fixture model | `src/lib/planogram/fixtures.js` | Real. 9 fixture types, double-sided gondolas, shelf levels classified by **height in metres**, not by rank |
| Package geometry | `src/lib/planogram/packageShapes.js` | 53 archetypes with real cm + cube-root size scaling parsed from Hebrew names |
| Allocation | `src/lib/planogram/allocationEngine.js` | Greedy, space-elastic, assortment-capped, hard constraints on clearance / width / heavy goods |
| Layout capture | `src/pages/StoreLayoutPage.jsx` | Manager draws the floor plan; persisted |
| Shelf plan | `src/pages/ShelfPlanPage.jsx` | Renders the allocation, per-position tooltips, derived advice |
| Validation | `src/lib/planogram/planValidation.js` | Re-checks the finished plan independently: shelf width, clearance, heavy goods |
| Baselines | `src/lib/planogram/baselines.js` | B2 margin-proportional + `comparePlans` on margin per linear metre |
| Versioning | `src/lib/planogram/planVersion.js` | draft → approved, and change cost against the approved plan |
| Build sheet | `src/lib/planogram/buildSheet.js` | The printable/CSV list a worker carries to the aisle |
| Compliance | `src/lib/analytics/complianceEngine.js` | Stub — compares two id lists, no vision |

296 Vitest tests and 21 Playwright end-to-end tests pass. `npm run doctor` reports data integrity against the real catalogue.

What this replaced: `shelfCapacity: 10`, a constant stamped onto all 7,451
products, and a scoring engine that *named* its top-ranked products "eye level".

### Gate 3 result, measured

Greedy (B3) against the margin-proportional rule (B2), on the six largest real
departments, same fixture, margin per linear metre:

| Department | SKUs | B3 | B2 | Δ | Hard violations |
|---|---:|---:|---:|---:|---:|
| מוצרי מכולת | 2,472 | 135,465 | 101,806 | **+33%** | 0 |
| חטיפים מתוקים | 848 | 3,133 | 2,389 | **+31%** | 0 |
| משקאות | 500 | 1,620 | 1,116 | **+45%** | 0 |
| מוצרי מקרר | 457 | 4,721 | 2,807 | **+68%** | 0 |
| חטיפים מלוחים | 347 | 717 | 544 | **+32%** | 0 |
| מוצרי בית | 329 | 1,798 | 1,495 | **+20%** | 0 |

Read this as a **structural** result, not a commercial forecast. Both plans use
the same assumed demand, so the gap measures what geometry, shelf-height
constraints and the assortment cut are worth — not what the store will earn.
The commercial claim needs §4.7.

Two defects were found by running this comparison and are fixed:

- The first version had B2 counting only its front row while B3 counted its full
  depth, producing a flattering +3,051%. Both now share `depthCapacity()` and
  `stackLimit()` from the allocator.
- Heavy goods were a *preference* in the allocator and a *hard rule* in the
  validator. With a full bottom shelf the allocator promoted 30 five-kilo rice
  sacks to eye level. Heavy placement is now hard: no bottom-shelf room means the
  product goes unplaced and the shortage is reported.

---

## 2. The research's execution gates, and our position on each

The report is emphatic that these are sequential and that skipping one wastes
the next. Our honest position:

| Gate | Research requirement | Us |
|---|---|---|
| 1. Digital twin | Reproduce an existing planogram from data within tolerance | **Partial.** We can render a drawn fixture faithfully. We have no existing planogram to reproduce — YomYom has never had one. Substitute acceptance in §4.1 |
| 2. Feasibility before optimality | A generator that always returns a physically valid plan | **Done and verified.** `planValidation.js` re-checks independently; zero hard violations across the six largest departments |
| 3. Baselines | Beat B0 current / B1 sales-proportional / B2 margin-proportional / B3 greedy | **Done for B2 vs B3** — see the table above. B1 is only partly available (velocity for 1,564 of 7,451); B0 waits on the §4.1 audit |
| 4. Replenishment | case-pack, delivery frequency, days of supply, labour | **Partial.** DOS exists; case-pack and delivery frequency do not. `leadTimeDays` is the constant 3 |
| 5. Store-specific | generic → cluster → store-specific | **N/A and skipped.** One store. Clustering is months of work with zero value here |
| 6. Compliance | detection → recognition → matching, with human review | **Not started.** Upload UI exists, nothing behind it |

Gate 5 of the report's own list — *stability and versioning* — is also done:
`planVersion.js` freezes an approved plan per fixture and category, and the shelf
plan shows the change cost of moving to the current recommendation as a count
plus the individual moves.

---

## 3. What we deliberately will NOT build

Scope discipline is the main value the research offers a project our size. Each
of these is correct advice for a chain and wrong for us:

- **A monolithic MILP over stores.** We have one store. `N_variables ≈ Σ_s Σ_i |J| |K|` collapses to one bay at a time.
- **Store clustering / category-specific clustering.** Requires multiple stores.
- **Column generation, Benders/LBBD, Lagrangian relaxation.** These earn their complexity above a few thousand binaries. One bay with ~100 carried SKUs and ≤12 facings is roughly 1,200 discrete alternatives — greedy with decreasing marginal value lands within a few percent of optimal on a fractional-knapsack shape. Revisit only if §4.3 shows a real gap.
- **Cross-space elasticity between SKU pairs.** O(n²) coefficients estimated from data we do not have.
- **Generative AI that draws a shelf.** The report is explicit and correct: dimensions, case-pack, facings, adjacency and hard constraints are much harder than producing a picture. The decision engine stays constraint-based and checkable.

---

## 4. Phases

### 4.1 — Trust the twin (blocking everything else)

The research's Gate 1 says: if you cannot reproduce the shelf you already have,
do not start optimising. We have no prior planogram, so the equivalent test is a
**physical audit**: draw YomYom Kafr Qasim in `StoreLayoutPage`, then walk the
store with the drawing.

Deliverables:
- `configs/yomyom_fixtures.yaml` — the audited floor plan, committed, replacing the "medium supermarket" preset as the default.
- Per-fixture record of what it actually holds today (category, rough facing count) — the B0 baseline. Photographs are enough.
- A measured-dimension sample: 30 SKUs across the archetypes, measured with a ruler, compared against `PACKAGE_SHAPES`. Publishes an archetype error rate.

Acceptance: the manager looks at the drawn plan and the rendered bay and says it
is their store. Archetype width error under 20% on the 30-SKU sample.

Why this first: the archetype error rate is the single number that bounds every
facing count the system will ever produce, and nobody has measured it.

### 4.2 — Rules as data, not code

The report's rule DSL, mapped onto the convention this repo already uses for
`configs/store_types.yaml` and `configs/pos_schema_mapping.yaml`.

New file `configs/planogram_rules.yaml`. Every rule carries
`scope + condition + enforcement + priority + dates + owner`:

```yaml
- id: HEAVY_GOODS_LOW
  scope: { fixture_kinds: [gondola, wall] }
  type: shelf_level_restriction
  condition: { volume_litres_gte: 2.5 }
  allow_levels: [BOTTOM]
  enforcement: hard          # safety — never relaxable
  owner: store_ops

- id: BEVERAGE_SIZE_FLOW
  scope: { category: משקאות }
  type: size_flow
  axis: horizontal
  direction: small_to_large
  enforcement: soft
  penalty: 120
  owner: category_manager
```

Also in this phase:

- **Lexicographic priority**, replacing today's single blended score:
  `safety ≻ physical fit ≻ hard merchandising ≻ profit ≻ stability ≻ aesthetics`.
  No amount of margin may buy a safety violation, which is exactly what a
  weighted sum permits by accident.
- **Conflict explanation.** When rules cannot be satisfied together the engine
  names the conflicting set and proposes the lowest-priority relaxation. It must
  never return a bare "infeasible".
- **Per-category space elasticity.** `SPACE_ELASTICITY = 0.2` is currently one
  global constant. Move it to config, per category, with the value and its
  provenance (`assumed` vs `estimated`) recorded — the research is clear there is
  no defensible universal β.
- **Location effect as config.** We classify shelves by height but apply no
  demand multiplier. Add `a[category][shelfLevel]`, defaulting to 1.0 everywhere
  and flagged `estimated: false`, so the day someone estimates it there is a slot
  to put it in and no hardcoded 1.35 to hunt down.

### 4.3 — Baselines and the evaluation harness

Gate 3. Without this we cannot claim the engine is good, only that it runs.

Implement as comparable generators over the same fixture:

| Baseline | Definition | Feasible for us |
|---|---|---|
| B0 | What is on the shelf today | Yes, from the 4.1 audit |
| B1 | Facings ∝ sales share | **No** — no sales |
| B2 | Facings ∝ margin share | Yes |
| B3 | Greedy capacity-aware | Yes — this is today's engine |

Report per plan, per the research's four layers:

```
feasibility   hard violations (must be 0), soft penalty total
space         utilisation %, unused cm, capacity fit
commercial    margin per linear metre, assortment margin retained
operations    positions below replenishment cover, refill actions implied
stability     SKUs moved, facings changed, distance from B0
```

Acceptance: B3 beats B2 on margin-per-metre **and** on stability, with zero hard
violations, on at least four departments. If it does not, the greedy is not
earning its complexity and the fix is the objective, not a solver.

### 4.4 — Replenishment, so the plan survives contact with the store

The report warns that a plan can look excellent commercially and be unworkable
operationally. Add, in this order:

1. **Case-pack** — new field on the product shape, sourced from the supplier file. Optional shelf policy `capacity ≥ case_pack`.
2. **Delivery frequency** per supplier, replacing `leadTimeDays: 3`.
3. **Coverage constraint** — `units_on_shelf ≥ θ × demand × replenishment_interval`. This is the CASRP link and the reason a facing count is an operational decision, not a display one.
4. **Refill labour** as a reported KPI: how many positions this plan requires touching per week.

### 4.5 — Stability and versioning

Currently every render recomputes from scratch, so the plan silently changes
under the manager's feet. The research treats this as one of the most-missed
constraints, and Blue Yonder's draft → approved → historical lifecycle as a
first-class feature rather than a nicety.

- `Δ` penalty against the previous approved plan, plus an optional change budget
  (`no more than X% of positions move`).
- A `PlanogramVersion` record — store, fixture, valid_from/to, the structured
  placement list, KPI estimates, rule validation result. Separate from rendering,
  so the UI can change without touching the model.
- Persisted through the existing adapter interface in `src/lib/persistence/`.

Without versioning we can never attribute a sales change to a plan, which makes
§4.7 impossible.

### 4.6 — A solver, only if §4.3 justifies it

If baselines show greedy leaving real value on the table, then and only then:

- Formulation: `z_ijk ∈ {0,1}` for product *i*, shelf *j*, *k* facings, with
  `D_i(k) = α_i · a_ij · k^β_i` **precomputed per (i,j,k)**. That is the key
  trick from the report — it keeps the non-linear demand out of the model and
  leaves a pure MILP.
- Placement: **Python, not the browser.** OR-Tools CP-SAT or HiGHS behind a
  FastAPI endpoint alongside `src/api/llm_proxy.py`, async with a `job_id` — a
  solver must never block an HTTP request. Behind a solver-adapter seam so the
  licence can change without rewriting the model.
- Warm-start from the current greedy plan, which also serves stability.

### 4.7 — Measuring, and the experiment we can actually run

This is where the "no sales data" constraint bites hardest, and where there is a
way through it that costs nothing.

`data/internal/snapshots/` currently holds two inventory snapshots. Snapshot
differencing gives depletion per SKU — a censored, noisy, but **real** velocity
signal, already modelled by `velocityConfidence.js` (2 snapshots = `low`).

The research's staggered-reset / difference-in-differences design maps onto this
directly, with no POS integration at all:

```
Bay A: apply the optimised plan
Bay B: comparable category, leave unchanged
Snapshot daily for 6 weeks
Compare depletion, differenced against the pre-period
```

That yields the first honest estimate of β for this store, and the first
evidence the engine does anything. Guardrails from the report apply: waste,
stockouts, refill labour, and whether the plan was actually implemented.

**Daily snapshots are the highest-value, lowest-cost action available to this
project.** Everything demand-related unblocks 30 snapshots later.

### 4.8 — Compliance (independent track)

Two separate problems, in the report's framing:

```
GENERATION   data  → optimal layout      (§4.1–4.6)
COMPLIANCE   photo → actual layout → diff
```

Correct one misconception before anyone starts: **SKU-110K is a single-class
detection benchmark.** It finds *where products are*, not *which product*. It
cannot identify a SKU. Identification needs our own catalogue images, and the
model must be allowed to answer `UNKNOWN_PRODUCT` rather than being forced to
guess the nearest match.

Sequence: photo QC → rectification → detection (SKU-110K transfer is fine here)
→ recognition against an internal catalogue → shelf-row assignment → matching
against the plan. Pair with human review of low-confidence cases from day one and
use those reviews as active-learning labels.

`ShelfImageUpload.jsx` is the existing entry point.

---

## 5. The binding constraint

**Correction (verified with `npm run doctor`):** an earlier version of this document, and of `CLAUDE.md`, stated that there is no sales data at all. That is false. **1,564 of 7,451 products carry usable velocity** (504 high, 1,060 medium), and the allocator already plans those on days-of-supply. Seven monthly sales reports covering 410,687 units also sit unimported in `data/internal/raw_pos/yomyom/sales/`.

What follows is therefore about the 5,887 products that still have no history, not about the catalogue as a whole.

| Blocked | Needs | Unblocks when |
|---|---|---|
| β estimation | facing changes observed against outcomes | §4.7, ~30 snapshots |
| Demand forecast `α_ist` | sales or depletion history | §4.7, or a POS sales export |
| OOS-censored demand correction | stock + sales together | POS export |
| Commercial evaluation of any plan | outcome measurement | §4.7 |

Until then the objective degrades honestly to **margin per centimetre**, which
`ShelfPlanPage` states on screen rather than hiding. That is a defensible
ranking. It is not a demand model, and no phase here should pretend otherwise.

---

## 6. Risks, mapped to our data

| Risk | Our specific exposure | Mitigation |
|---|---|---|
| Wrong SKU dimensions | Every dimension is an archetype estimate; zero measured | §4.1 ruler sample publishes the error rate |
| Mis-categorised products | A shampoo sits in `משקאות` in the real export and was drawn as a soda bottle | Keyword override ahead of department; surface suspects for review |
| Negative stock | 625 rows | Clamped in `stockOnHand()` and in the normaliser |
| Services priced as products | Car washes, subscriptions, drive-through combos | `isShelvable()` excludes three departments by name |
| Rules conflict | Not yet possible — no rule engine | §4.2 conflict explainer before rules multiply |
| Plan not implemented | No compliance loop | §4.8; until then treat every result as intent, not fact |
| Over-optimisation | Plan changes on every render | §4.5 stability and versioning |

---

## 7. Order of work

1. **§4.1 audit** — nothing is trustworthy before it, and it needs a store visit
2. **§4.7 daily snapshots** — start immediately and in parallel; the clock is the cost
3. **§4.3 baselines** — cheap, and tells us whether the engine is worth extending
4. **§4.2 rules as data** — before rule count grows past what code can hold
5. **§4.5 stability and versioning** — prerequisite for attributing any outcome
6. **§4.4 replenishment** — once placement is trusted
7. **§4.6 solver** — only if §4.3 justifies it
8. **§4.8 compliance** — independent, start whenever CV capacity exists
