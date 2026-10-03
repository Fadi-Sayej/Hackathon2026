---
ID: F12-S1
Title: Planogram — a dated shelf plan from his own sales, waiting for them until they arrive
Status: Ready for review
Owner: smartshelf-architect
Version: 0.3 (2026-10-03, after two independent review rounds)
Parent: [F12 — Planogram](../intent.md)
Related Intents: INT-006
Inputs: [docs/features/F12-planogram/intent.md (Approved for specification, D-30), docs/product/PRD.md (§5 V4, §6 #7), docs/product/intent-register.md (D-1, D-3, D-13, D-14, D-22, D-23, D-28, D-29, D-30), docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md (§5 "He stocks", FR-143 … FR-146, FR-156), ADR-001, ADR-002, ADR-005, ADR-007, ADR-011, ADR-012, ADR-014, ADR-028, ADR-029, ADR-030, ADR-033, ADR-036, ADR-037, CLAUDE.md]
Answered by: [System Design](../../../architecture/system-design.md) §21 (F12-S1)
Updated: 2026-10-03
---

# F12-S1 — Planogram

> **Ready for review.** D-30 unlocked this spec on 2026-10-03: the plan waits for daily sales the
> way F8 does, and D-13 stands. Everything D-30 left open is either decided here, marked
> **(decided here)** for the owner's approval, or asked in §17.

> **Identifier note.** Every `FR-`, `INV-`, `NFR-`, `AC-`, `SCN-`, `C-`, `ASM-` and `OQ-` id
> below is new and globally unique: FR-178 … FR-199, INV-084 … INV-091, NFR-072 … NFR-075,
> AC-172 … AC-188, SCN-159 … SCN-168, C-73 … C-75, ASM-073 … ASM-074, OQ-1201 … OQ-1205.

Implements intent F12. Bound by ADR-001, ADR-002, ADR-005, ADR-007, ADR-011, ADR-012, ADR-014,
ADR-028, ADR-029, ADR-030, ADR-033, ADR-036 and ADR-037, and settled decisions D-1, D-3, D-13,
D-14, D-23 and D-30.

## 1. Purpose

Tell the owner, fixture by fixture, which of the products he stocks to put on which shelf and how
many facings each gets. The shelf space goes to what earns the most per centimetre on **his own
sales** (INT-006, PRD §5 V4).

The plan is a **dated plan with its conditions**, not a finished feature (intent, framing
commitment; PRD §6 #7). It names the sales window it rests on, the date of every measurement and
rule, and every product it did not place and why.

It never claims a gain. The intent's "+20–68% margin per linear metre" is a figure from
elsewhere, and this store has no before-and-after to measure one (§21).

## 2. Intent Traceability

- **INT-006** — «رتّب رفوفي لأربح أكثر» ("arrange my shelves so I earn more").
- **D-30** — unlocked for specification, the plan waiting for daily sales the way F8 does.
- **D-13** — no fixed cameras or sensors, ever.
- Serves PRD §6 #7 (the planogram is shown as a dated plan with its conditions).

## 3. Scope

Behavioural scope, not a file list. The implementation plan declares the files.

### In Scope
- The store's **layout facts**, recorded by the team from the owner in a committed file
  (ADR-037):
  - each fixture's shelves and their usable lengths;
  - the departments it holds, whether it is chilled, and which shelf is at eye level;
  - each stocked product's facing width;
  - the owner's arrangement rules.
- Two engine capabilities, because they fail on different days (ADR-014):
  - **`layout_facts`** publishes the recorded facts and what is missing, and needs no sales;
  - **`shelf_plan`** publishes the plan, and waits for daily sales.
- Two pages that already exist as waiting shells (ADR-028 §1), filled from the artefact:
  **Store layout** from `layout_facts`, and **Shelf plan** from `shelf_plan`.
- The boundary probe for the new inputs (§20).

### Out of Scope
- **Reading shelves from photographs.** The team records the facts by hand from photographs he
  sends or they take. A vision model reading a shelf is untested, because the PRD's one-day
  trial was never run (OQ-1202) **(decided here)**.
- **Checking a rearranged shelf against the plan** (compliance from a second photograph).
  Possible later, and only by hand-held photographs (D-13).
- **The order of products from left to right within a shelf.** The plan gives each product a
  shelf and a number of facings **(decided here)**.
- **A marked example while the plan waits.** D-29 confines examples to the order pages; this
  needs its own decision (OQ-1203).
- **Any money projection.** See INV-087 and §21.
- **Planning products he does not stock** (F8-S1 §5). Those in his catalogue are listed, not
  planned (FR-198). Products outside his catalogue are F9's.

## 4. Actors and Triggers

| Actor | Trigger | Frequency |
|---|---|---|
| The owner | States his fixtures and rules; sends or allows shelf photographs | At setup, and when a fixture changes |
| The team | Measures shelves and facing widths; records them and his rules in the layout file (ADR-037); commits | When something is measured or stated |
| The nightly engine | Computes `layout_facts` and `shelf_plan` | Nightly (ADR-007) |
| The owner | Opens Store layout or Shelf plan | Any time |
| A team account | Opens either page | Any time; read-only (ADR-029) |

## 5. Domain Terms

| Term | Definition |
|---|---|
| Fixture | One shelving unit, fridge or freezer, named by the owner. It has one or more shelves. |
| Shelf | One level of a fixture, with its usable length in whole centimetres, as measured. |
| Eye-level shelf | The shelf the owner names as the one customers see first. At most one per fixture. |
| Facing | One unit of a product standing at the front of a shelf, beside the others. |
| Facing width | One product's width at the front of the shelf, in whole millimetres, as measured. |
| Arrangement rule | One of a closed set of his statements (FR-188). |
| He stocks | F8-S1 §5, the same test: the window records a sale or a delivery of it. In a department the evidence does not itemise (FR-156), his latest count shows it above zero. |
| Planned product | A product he stocks, in a department a fixture holds. |
| Demand | The daily mean that F8's evidence functions give for the product over F8's window. The same functions compute it, so it is never a second derivation (INV-085). It is unknown where the evidence does not itemise the department (ADR-011). |
| Earnings per centimetre | Margin per sale × demand ÷ facing width. Defined only where all three are known. |
| Margin per sale | Shelf price less unit cost, for one unit. A unit figure, not a quantity (D-1). |

## 6. Functional Requirements

#### The inputs

**FR-178** — The layout facts come only from the committed layout file (ADR-037). The browser
never writes them, and the engine never repairs them. A fixture, rule or width that fails
validation is rejected by name in the run's steps, as ADR-033 does for store facts. The rest are
used.

**FR-179** — A fixture holds the planned products of the departments it names. A department named
on two fixtures is rejected, unless a "keep on" rule assigns its products between them.

**FR-180** — The plan needs each planned product's facing width **(decided here; beyond D-30's
list, so OQ-1201 asks who measures)**. A product without one is not placed, and is named under
"no width". A width is never estimated from the category, the price or a photograph (D-3).

**FR-181** — Demand is computed by F8's evidence functions over F8's window, never by a second
derivation. Monthly reports supply no demand (F8-S1 FR-143; CLAUDE.md rule 13). In a department
the evidence does not itemise, demand is unknown, never zero (ADR-011; F8-S1 FR-156).

#### The layout, which does not wait for sales

**FR-190** — `layout_facts` requires `products` and `store_layout`, and is `available` as soon as
both exist, whatever the sales evidence (D-30). It publishes:
- each fixture: its shelves and lengths, departments, chilled, eye level and rules;
- the dates each fact was measured or stated (ADR-037);
- what is missing: no layout file, departments on no fixture, products without a width per
  fixture, and entries rejected.

While F8's window does not exist (no reports, too few, or stale), "products without a width"
counts the departments' catalogue products. While it exists, it counts only the planned
products.

**FR-191** — Store layout shows `layout_facts`, the same before and after sales arrive.

#### The plan

**FR-182** — Every planned product with a width gets one facing first (FR-183). The plan withdraws
nothing: which products he keeps is his and F4's question, and D-14 forbids a figure that depends
on automatic withdrawal.

**FR-183** — First facings are packed shelf by shelf, each product on the first shelf in this
order with room for it **(decided here)**:
1. products whose earnings per centimetre is known, highest first, on the eye-level shelf first
   and then the other shelves in the order recorded;
2. then products whose earnings per centimetre is unknown, by barcode.

Eye level goes to what his own sales show earns most. A product whose earnings are unknown is
never ranked for it (D-3).

**FR-184** — A fixture whose planned products' first facings cannot all be packed in FR-183's
order is **over-full**, and gets no plan **(decided here)**. It is over-full even when some other
packing would fit them, because the order is what puts earnings at eye level:
- Its plan states the total facing width that did not fit, and lists its planned products.
- Which product leaves a shelf is his decision, not a ranking's, because taking one off would
  be a withdrawal (D-14). He resolves it with a "keep off" rule or a longer shelf, and the next
  night plans it.
- A product wider than every shelf of its fixture is not placed, under "too wide" with its
  width, and does not make the fixture over-full.

**FR-185** — Each shelf's length left after the first facings goes, one facing at a time, to the
product on that shelf whose next facing earns the most per centimetre. An extra facing stands on
the shelf that holds the product's first facing. Each further facing of a product counts for
less than the one before. A space-elasticity factor and a facings cap set by how much; both are
policy values, and provisional (OQ-1204).

**FR-186** — Extra facings (FR-185) are given only on a fixture with no product under "no width"
or "too wide" **(decided here)**. Those products stand somewhere on the real shelf, taking space
of unknown size, so any spare length is not known to be free. Such a fixture gets first facings
only, and its plan says why.

**FR-187** — A product whose earnings per centimetre is unknown keeps its first facing and gets
no more. The plan says which part is unknown: the margin (no shelf price, or no unit cost from the
POS or his answer) or the demand. Its earnings are never computed as if the unknown were zero
(D-3).

**FR-188** — His arrangement rules are a closed set **(decided here)**:
- keep these products, or this department, together on one shelf;
- keep this product on fixture F;
- keep this product off fixture F;
- at least N facings;
- at most N facings.

Every rule is obeyed. A rule that cannot be obeyed stops that fixture's plan, which names the
rule. Two examples: at least N facings that do not fit, or a "together" set longer than any
shelf. A product kept off a fixture is listed there under "kept off by his rule".

**FR-189** — The published plan states its conditions:
- the window's first and last report day;
- every fact's measured or stated date;
- per fixture: placed, "no width", "too wide" and "kept off by his rule", and whether it was
  over-full or stopped by a rule.

That makes it the "dated plan with its conditions" (PRD §6 #7). A planned product whose demand is
zero (the evidence itemises its department and records no sale) has a known earnings figure of
zero, keeps its first facing, and gets no more.

**FR-192** — Both capabilities are `value_policy: none`, and neither is admitted to the daily
surface **(decided here)**. The plan is a page he opens, not one of Today's places. Margin per sale
may appear in a placed product's evidence as a unit price figure, never as a value or a total
(INV-087).

#### Waiting

**FR-193** — `shelf_plan` requires `products`, `store_layout` and `sales_daily`, in that order.
Its reason is the first missing input, through the registry (ADR-014):
- `no_pos_data`;
- `no_store_layout`, when the layout file is absent (an empty file is still a file, as with
  ADR-033's);
- `no_daily_sales`, when no daily report has arrived (D-30: it waits the way F8 does).

It also publishes rule-level reasons of its own:
- `layout_all_rejected`, when every fixture in the file was rejected;
- `no_evidence_window`, when reports exist but F8's window does not (fewer than 21 report days,
  F8-S1 FR-144);
- `stale_daily_sales`, when the latest report day is older than F8's freshness limit, the policy
  value `order_freshness_days` (ADR-030 §4). The plan stops by the same rule that stops F8.

**FR-194** — Shelf plan shows the plan per fixture. When `shelf_plan` is unavailable, it shows the
reason in the owner's words and language, and no plan, the way Reorder waits for its daily
reports. It never shows an empty plan as if there were nothing to arrange.

**FR-195** — Neither page has a control that changes anything. A team account sees them the same
(ADR-029).

**FR-196** — `layout_facts` is unavailable (`no_store_layout`) when the layout file is absent, and
(`layout_all_rejected`) when every fixture in it was rejected. Store layout then says the
measurements have not been recorded, or names what was rejected.

**FR-198** — A catalogue product in a fixture's departments that he does not stock is listed on
that fixture under "no sale or delivery in the window". In a department the evidence does not
itemise, the listing is "count zero or below". The plan assumes such products are off the
shelf, because his catalogue keeps products long after they leave it. A "keep this product on
fixture F" rule plans it all the same, with one facing **(decided here)**.

**FR-199** — In a department split across two fixtures, a product no "keep on" rule names is
rejected by name and listed by `layout_facts` **(decided here)**.

**FR-197** — When the latest stock count is unknown in a department the evidence does not itemise,
its products are not "stocked" (F8-S1 §5) and are not planned. `layout_facts` lists them as
"stock unknown".

## 7. Behavioral Invariants

**INV-084** — No fixed camera, sensor or continuous image feed is ever an input (D-13).
*Violated if* any input reaches either capability other than the committed layout file and the
existing artefact inputs.

**INV-085** — Demand is computed by F8's own evidence functions over F8's window, never derived a
second time. *Violated if* a product's demand in the plan differs from the `daily_mean`
`order_quantity` publishes for it on the same run, where it publishes one.

**INV-086** — A missing measurement, width, price, cost or demand is never filled in. *Violated if*
a product without a width is placed, or a product with unknown earnings gets more than one
facing.

**INV-087** — Neither capability publishes a ₪ value, a total, a projected gain or a "margin per
metre" figure. Margin per sale appears only as a unit figure in a product's evidence, never
summed (ADR-012; CLAUDE.md rule 8). The publisher enforces it as it does for F8 and F9: it
refuses a value, or any money-named field other than a placed product's `margin_per_sale`, in
either capability. *Violated if* any money figure in either adds products, facings or fixtures
together.

**INV-088** — Every catalogue product of a fixture's departments is either placed or named with
its reason. The reasons are "no width", "too wide", "kept off by his rule", "no sale or delivery
in the window", "count zero or below", "stock unknown", or the fixture being over-full or
stopped by a rule. *Violated if* a fixture's published products and its departments' catalogue
products differ.

**INV-089** — Nothing on either page can be changed, approved or sent (FR-195). *Violated if* a
click on either page writes owner state.

**INV-090** — A product whose earnings per centimetre is unknown never takes a place in the
earnings order (FR-183). *Violated if* such a product is packed before one whose earnings are
known.

**INV-091** — Extra facings are never given on a fixture with a product of unknown size (FR-186).
*Violated if* a fixture with "no width" or "too wide" shows a product with more than one facing.

## 8. Behavioral Scenarios

**SCN-159** — Given no layout file, when the nightly runs, then both capabilities are unavailable
(`no_store_layout`). Both pages say the measurements have not been recorded.

**SCN-160** — Given a layout file and no daily reports, when the nightly runs:
- `layout_facts` is available, and Store layout shows every recorded fixture with its dates and
  the products without a width;
- Shelf plan says it is waiting for the daily sales reports (`no_daily_sales`) and shows no plan
  (D-30).

**SCN-161** — Given a window, a fixture of two shelves at 100 cm and 90 cm, and planned products
with widths and known earnings, when the nightly runs, then:
- every product gets one facing, with the eye-level shelf filled first by earnings per centimetre;
- the remaining length goes by FR-185;
- the plan states its window and dates.

**SCN-162** — Given a planned product with no recorded width, when the plan is made, then it is not
placed, it is named under "no width", and its fixture gets first facings only (FR-186).

**SCN-163** — Given a fixture whose first facings cannot all be packed, when the plan is made, then
that fixture gets no plan. It shows the width that did not fit and lists its planned products.
No product is dropped by ranking.

**SCN-164** — Given his rule "at least 4 facings of X" and too little room for it, when the plan is
made, then that fixture's plan names the rule it could not meet, and nothing is broken.

**SCN-165** — Given a planned product with no unit cost, when the plan is made, then it has exactly
one facing and is packed after every product with known earnings. The plan says its margin is
not known.

**SCN-166** — Given reports that have stopped arriving, when the latest report day is older than
`order_freshness_days`, then `shelf_plan` is unavailable (`stale_daily_sales`).

**SCN-167** — Given a layout file with one malformed fixture, when the nightly runs, then that
fixture is named in the run's steps and the others are planned.

**SCN-168** — Given a department the evidence does not itemise, when the plan is made, then its
stocked products (latest count above zero) each get one facing, and the plan says their demand is
unknown.

## 9. Inputs and Observable Outputs

| Input | Source | Required? |
|---|---|---|
| Layout facts, with `measured_by` / `measured_on` or `stated_by` / `stated_on` | The committed layout file (ADR-037) | Yes, for both capabilities |
| His catalogue: products, departments, shelf prices, unit costs, latest counts | The POS export (`products`) and his answered costs | Yes, for both |
| Daily reports, F8's window and evidence | ADR-030; F8-S1 §5, FR-143 … FR-146 | Yes, for `shelf_plan` only |

| Output | Where it is observable |
|---|---|
| `layout_facts`: the recorded facts with dates, what is missing, rejected entries | `dashboard.json`; the Store layout page |
| `shelf_plan`: per fixture and shelf, products with facings and the reason; the unplaced lists; the conditions (FR-189) | `dashboard.json`; the Shelf plan page |
| Rejected layout entries, by name and reason | The run's steps |

## 10. State / Lifecycle Semantics

Nothing persists between runs except the committed layout file. The history of its commits
records what was measured or stated, and when (ADR-037). Both capabilities are recomputed every
night from the current facts and F8's current window. A new measurement changes the next plan,
and the file's history shows when it changed.

## 11. Failure and Recovery Behavior

- **Layout file absent:** both capabilities are `no_store_layout`. Not an empty plan (CLAUDE.md
  rule 10).
- **Every fixture rejected:** `layout_all_rejected`, and the rejections are named.
- **Some entries rejected:** named in the run's steps; the rest are used (SCN-167).
- **Reports not yet arrived, too few days, or stopped:** `no_daily_sales`, `no_evidence_window`
  or `stale_daily_sales`, by the same rules F8 uses. Store layout is
  unaffected.
- **A department on no fixture:** listed by `layout_facts`. Not an error.

## 12. Edge Cases

| Case | Behaviour |
|---|---|
| A product wider than every shelf of its fixture | "Too wide", with its width; the fixture gets first facings only (FR-184, FR-186) |
| A fixture whose departments have no planned products | Shown by `layout_facts`; no plan for it |
| A rule naming a product not in his catalogue | Rejected by name (FR-178) |
| Two eye-level shelves on one fixture | The fixture is rejected by name (FR-178) |
| A chilled department named on an unchilled fixture | Recorded as stated. The plan does not second-guess his fixtures **(decided here)** |
| Exactly one facing of everything fills the fixture | No extra facings, and the fixture is not over-full |

## 13. Non-Functional Requirements

**NFR-072** — Neither capability adds a step whose time grows with the collected market history.
They read only the layout file, the catalogue and F8's window (compare the 2026-10-03 nightly,
#276).

**NFR-073** — Reproduction: print mode and `npm run figures` compute the same plan from the same
committed inputs (ADR-002).

**NFR-074** — The two pages render on a phone without horizontal scrolling, in Hebrew, Arabic and
English (the existing e2e invariants).

**NFR-075** — A store's layout file is store data. Updating a copy from the product never
overwrites it, and `check:store` reports whether it is present (ADR-036, ADR-037).

## 14. Compatibility and External Constraints

**C-73** — One store per copy (ADR-036, D-28). The layout file belongs to that copy's store.

**C-74** — The team, who measure, cannot write owner state (ADR-029). That is one reason the
layout is a file, not a form (ADR-037).

**C-75** — Front-end work waits for the owner's approval of its mockups. Both pages are built only
after he approves them.

## 15. Acceptance Criteria

**AC-172** — With no layout file, both capabilities are `unavailable` (`no_store_layout`), and
both pages say the measurements have not been recorded. *(FR-191, FR-193, FR-194, FR-196)*

**AC-173** — With a layout file and no daily reports, `layout_facts` is available and Store layout
shows every recorded fixture with its dates. `shelf_plan` is `unavailable` (`no_daily_sales`), and
Shelf plan shows no plan. *(FR-190, FR-193, FR-194; D-30)*

**AC-174** — With a window, every planned product with a width gets one facing, packed shelf by
shelf, eye level first by earnings per centimetre, and the remaining length goes by FR-185.
*(FR-182, FR-183, FR-185)*

**AC-175** — A product without a width is never placed, is named under "no width", and its fixture
gets first facings only. *(FR-180, FR-186, INV-086, INV-091)*

**AC-176** — Every catalogue product of every fixture's departments is placed or named with its
reason, including "no sale or delivery in the window". An over-full fixture gets no plan, only the
width that did not fit. *(FR-184, FR-198, INV-088)*

**AC-177** — A product with unknown earnings has exactly one facing, is packed after every product
with known earnings, and the plan says which part is unknown. *(FR-183, FR-187, INV-086, INV-090)*

**AC-178** — A rule that cannot be met stops that fixture's plan and is named; no rule is broken.
*(FR-188)*

**AC-179** — On the same run, wherever `order_quantity` publishes a `daily_mean` for a product, the
plan's demand for it equals that value. *(FR-181, INV-085)*

**AC-180** — Neither capability publishes a ₪ value, total, projected gain or per-metre figure; any
margin is a unit figure in evidence, unsummed. *(FR-192, INV-087)*

**AC-181** — The published plan carries its window dates, every fact's date, and the per-fixture
counts of FR-189. *(FR-189)*

**AC-182** — Neither page writes owner state, and a team account sees both read-only.
*(FR-195, INV-089)*

**AC-183** — No input other than the layout file and the existing artefact inputs reaches either
capability. *(INV-084; D-13)*

**AC-184** — A malformed fixture, rule or width is named in the run's steps, and the rest are used.
A department on two fixtures without a "keep on" rule is rejected, and so is a product of a split
department that no rule names. *(FR-178, FR-179, FR-199)*

**AC-185** — When the latest report day is older than `order_freshness_days`, `shelf_plan` is
`stale_daily_sales`. With reports but no window, it is `no_evidence_window`. *(FR-193)*

**AC-186** — In a department the evidence does not itemise, stocked products get one facing each,
with demand published as unknown, never zero. A product whose count is unknown is not planned
and is listed as "stock unknown". *(FR-181, FR-187, FR-197)*

**AC-187** — Neither capability is admitted to the daily surface. *(FR-192)*

**AC-188** — Updating a store's copy from the product leaves its layout file unchanged, and
`check:store` names the file as missing when it is absent. *(NFR-075)*

## 16. Assumptions

**ASM-073** — A product's facing width does not change between packs of the same barcode.
*Falsified if* he sells one barcode in two pack sizes.

**ASM-074** — One measured usable length per shelf is enough. A shelf with dividers or uneven
depth is measured as the length that can hold products. *Falsified if* a fixture's products need
depth or height to fit.

## 17. Open Questions

**OQ-1201** — FR-180 needs a facing width for every planned product, which goes beyond the inputs
D-30 listed. Who measures them: the team, from his shelf photographs and a tape, or the owner?
The catalogue holds 7,523 products (`figures["competitor_position.catalogue"]`, artefact of
2026-10-03), and only the stocked products on recorded fixtures need one. · owner: the
repository owner · blocks: the first plan.

**OQ-1202** — Should the one-day trial of a vision model reading a real shelf photograph be run,
before or after a first version that records by hand? · owner: the repository owner · blocks:
nothing in this spec.

**OQ-1203** — May Shelf plan show a marked example while it waits, as D-29 allows the order pages?
That needs its own D-n. · owner: the repository owner · blocks: nothing; without it, the page
waits.

**OQ-1204** — What are the provisional space-elasticity factor and facings cap (FR-185)? · owner:
the repository owner, on the architect's proposal · blocks: FR-185's numbers, not its rule.

**OQ-1205** — Are the choices marked **(decided here)** right? They are:
- the packing order and eye level (FR-183);
- the over-full rule (FR-184);
- first facings only where some sizes are unknown (FR-186);
- the rule set (FR-188);
- not on Today (FR-192);
- shelf, not position (§3);
- recording by hand (§3);
- trusting a chilled department as recorded (§12);
- assuming unstocked catalogue products are off the shelf, with a "keep on" rule to override it
  (FR-198);
- rejecting a split department's unassigned products (FR-199).

· owner: the repository owner · blocks: approval of this spec.

## 18. Non-Goals

- A plan built from monthly reports, or from assumed demand, to show something now.
- A floor plan of the store. Store layout lists fixtures; it does not draw the floor.
- Promotions, end caps or seasonal moves.
- Any measured gain from following the plan.

## 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-006 | FR-178, FR-179, FR-199 | SCN-167 | AC-184 |
| INT-006 | FR-190, FR-191, FR-193, FR-194, FR-196 | SCN-159, SCN-160, SCN-166 | AC-172, AC-173, AC-185 |
| INT-006 | FR-182, FR-183, FR-185 | SCN-161 | AC-174 |
| INT-006 | FR-180, FR-184, FR-186, FR-198 | SCN-162, SCN-163 | AC-175, AC-176 |
| INT-006 | FR-181, FR-187, FR-197 | SCN-165, SCN-168 | AC-177, AC-179, AC-186 |
| INT-006 | FR-188 | SCN-164 | AC-178 |
| INT-006 | FR-189 | SCN-161 | AC-181 |
| INT-006 | FR-192, FR-195 | SCN-160 | AC-182, AC-187 |
| Protected behavior | INV-084 | — | AC-183 |
| Protected behavior | INV-085 | — | AC-179 |
| Protected behavior | INV-086, INV-088, INV-090, INV-091 | SCN-162, SCN-163, SCN-165 | AC-175, AC-176, AC-177 |
| Protected behavior | INV-087 | — | AC-180 |
| Protected behavior | INV-089 | — | AC-182 |
| Protected behavior | NFR-075 | — | AC-188 |

---

## 20. Boundary Probe

| Probe | What it would catch | Where it runs |
|---|---|---|
| `npm run check:order-signals` (exists), extended over its fixture world, which carries daily reports. The extension withholds the daily reports, the layout file and one product's width. | `shelf_plan` published without daily sales or a layout; `layout_facts` failing without sales; a product placed without a width | `collect-daily.yml` |
| `scripts/check_v1_signals.py`'s `PROBED_ELSEWHERE` guard (exists) | Once the `store_layout` input is in either capability's `requires`, `tests/test_check_v1_signals.py` fails until it is listed. Listing it also needs the probe's own word for it in that test | CI |

## 21. Claim Limits

| Claim | Verdict | Why |
|---|---|---|
| "Following the plan raises margin per metre by 20–68%" | not measurable | No before-and-after for this store, and the figure is from elsewhere (intent). |
| "This product sells X a day", from the monthly reports | not measurable | Monthly rows have no days (rule 13). Only F8's daily window is used. |
| "The plan is optimal" | not measurable | The allocation is greedy with a provisional elasticity (OQ-1204). It is a defensible ranking, not a proven optimum. |

## 22. Unmapped PRD Acceptance Lines

None. FR-178 … FR-199 cover the PRD's V4 row: shelf photographs, rules, and generating the plan.
- Photographs enter only as the team's source for the recorded facts (§3).
- Facing widths are an input the PRD row does not name (FR-180, OQ-1201).
