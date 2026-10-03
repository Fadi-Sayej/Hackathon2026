---
ID: F12-S1
Title: Planogram — a dated shelf plan from his own sales, waiting for them until they arrive
Status: Ready for review
Owner: smartshelf-architect
Version: 0.7 (2026-10-04: OQ-1206 answered; the arrangement record and the before-and-after measurement; §23; two rounds of the measurement's review)
Parent: [F12 — Planogram](../intent.md)
Related Intents: INT-006
Inputs: [docs/features/F12-planogram/intent.md (Approved for specification, D-30), docs/product/PRD.md (§5 V4, §6 #7), docs/product/intent-register.md (D-1, D-3, D-13, D-14, D-22, D-23, D-28, D-29, D-30, D-31), docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md (§5 "He stocks", FR-143 … FR-146, FR-156), ADR-001, ADR-002, ADR-003, ADR-005, ADR-007, ADR-009, ADR-011, ADR-012, ADR-014, ADR-028, ADR-029, ADR-030, ADR-033, ADR-036, ADR-037, ADR-038, CLAUDE.md]
Answered by: [System Design](../../../architecture/system-design.md) §21 (F12-S1)
Updated: 2026-10-04 (the measurement's review: a before window apart from the plan's, one Poisson regression, a fixture bootstrap, a placebo, `shelf_measurement`; eligibility from the plan's window, one net change, a spaced placebo on both terms, arrangements shown from the artefact)
---

# F12-S1 — Planogram

> **Ready for review.** D-30 unlocked this spec on 2026-10-03: the plan waits for daily sales the
> way F8 does, and D-13 stands. Everything D-30 left open is either decided here, marked
> **(decided here)** for the owner's approval, or asked in §17.

> **Identifier note.** Every `FR-`, `INV-`, `NFR-`, `AC-`, `SCN-`, `C-`, `ASM-` and `OQ-` id
> below is new and globally unique: FR-178 … FR-209, INV-084 … INV-095, NFR-072 … NFR-076,
> AC-172 … AC-198, SCN-159 … SCN-174, C-73 … C-75, ASM-073 … ASM-082, OQ-1201 … OQ-1208.

Implements intent F12. Bound by ADR-001, ADR-002, ADR-003, ADR-005, ADR-007, ADR-009, ADR-011,
ADR-012, ADR-014, ADR-028, ADR-029, ADR-030, ADR-033, ADR-036, ADR-037 and ADR-038, and settled
decisions D-1, D-3, D-13, D-14, D-23, D-29, D-30 and D-31.

## 1. Purpose

Tell the owner, fixture by fixture, which of the products he stocks to put on which shelf and how
many facings each gets. The shelf space goes to what earns the most per centimetre on **his own
sales** (INT-006, PRD §5 V4).

The plan is a **dated plan with its conditions**, not a finished feature (intent, framing
commitment; PRD §6 #7). It names the sales window it rests on, the date of every measurement and
rule, and every product it did not place and why.

Its rules come from shelf-space research (§23), and its numbers start as research averages.
When he arranges a fixture to the plan and records it, the product measures what changed
against fixtures he did not touch. Once enough arrangements are measured, and checked for drift
that was there already, his store's own response replaces the research average (FR-201 …
FR-209). Until then it claims no gain. The intent's "+20–68% margin per linear metre" is a figure
from elsewhere (§21).

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
  - each stocked product's facing width, and its current facings and shelf, all read from his
    shelf photographs;
  - the owner's arrangement rules.
- Three engine capabilities, because they fail on different days (ADR-014):
  - **`layout_facts`** publishes the recorded facts and what is missing, and needs no sales;
  - **`shelf_plan`** publishes the plan, and waits for daily sales;
  - **`shelf_measurement`** publishes what his recorded arrangements changed, and waits for
    them as well as for daily sales.
- Two pages that already exist as waiting shells (ADR-028 §1), filled from the artefact:
  **Store layout** from `layout_facts`, and **Shelf plan** from `shelf_plan` and
  `shelf_measurement`.
- His "I've arranged this shelf" record, and the before-and-after measurement it starts
  (FR-201 … FR-209; OQ-1206, answered).
- A clearly marked example on Shelf plan while it waits, as on Reorder (D-31, FR-200). What the
  example is built from is proposed by its plan for his approval.
- The boundary probe for the new inputs (§20).

### Out of Scope
- **Reading shelves from photographs.** The team records the facts by hand from photographs he
  sends or they take. A vision model reading a shelf is untested, because the PRD's one-day
  trial was never run (OQ-1202) **(decided here)**.
- **Checking a rearranged shelf against the plan** (compliance from a second photograph).
  Possible later, and only by hand-held photographs (D-13).
- **The order of products from left to right within a shelf.** The plan gives each product a
  shelf and a number of facings **(decided here)**.
- **Any money projection, and any money measurement.** The measurement is in units sold (FR-207;
  INV-087, INV-093).
- **Products affecting each other's sales** (cross-space elasticities, which Corstjens and Doyle
  model). The plan treats each product's space on its own (§23).
- **Planning products he does not stock** (F8-S1 §5). Those in his catalogue are listed, not
  planned (FR-198). Products outside his catalogue are F9's.

## 4. Actors and Triggers

| Actor | Trigger | Frequency |
|---|---|---|
| The owner | States his fixtures and rules; sends or allows shelf photographs | At setup, and when a fixture changes |
| The team | Measures shelves, facing widths and current facings; records them and his rules in the layout file (ADR-037); commits | When something is measured or stated |
| The nightly engine | Computes `layout_facts`, `shelf_measurement` and `shelf_plan` | Nightly (ADR-007) |
| The owner | Opens Store layout or Shelf plan | Any time |
| The owner | Presses "I've arranged this shelf" on a fixture's plan, after he rearranges it | When he does |
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
| Space elasticity | How a product's sales respond to its shelf space: sales scale as space to this power. With 0.17, doubling the space multiplies sales by 2^0.17, about 1.125 (§23). |
| Plan's date | The date of the nightly run that published the plan. Each night's plan is a new one (FR-192). |
| Plan's window | The F8 window the plan's demand came from. |
| Arrangement | His record that he rearranged one fixture to one dated plan (FR-201, ADR-038). |
| Before and after windows | The window ending the day before the plan's window begins, and the window starting the day after the arrangement, each held to F8's window rules (FR-202). |
| Comparison products | Products on fixtures with no arrangement from the before window's first day to the after window's last day (FR-203). |
| Placebo | The same estimate between two earlier windows, when nothing was rearranged, to test for drift that was there already (FR-209). |

## 6. Functional Requirements

#### The inputs

**FR-178** — The layout facts come only from the committed layout file (ADR-037). The browser
never writes them, and the engine never repairs them. A fixture, rule or width that fails
validation is rejected by name in the run's steps, as ADR-033 does for store facts. The rest are
used.

**FR-179** — A fixture holds the planned products of the departments it names. A department named
on two fixtures is rejected, unless a "keep on" rule assigns its products between them.

**FR-180** — The plan needs each planned product's facing width. The team reads it from his shelf
photographs and records it with who read it and when (OQ-1201, answered; ADR-037). A product
without a recorded width is not placed, and is named under "no width". A width is never
estimated from the category or the price (D-3).

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
  over-full or stopped by a rule;
- the space elasticity it used, and why (FR-206).

That makes it the "dated plan with its conditions" (PRD §6 #7). A planned product whose demand is
zero (the evidence itemises its department and records no sale) has a known earnings figure of
zero, keeps its first facing, and gets no more.

**FR-192** — All three capabilities are `value_policy: none`, and none is admitted to the daily
surface **(decided here)**. `shelf_plan` publishes each fixture's plan as one entry of the family
`shelf.plan` (ADR-038). The plan's date is the date of the nightly run that published it, so each
night's plan is a new entry. The plan is a page he opens, not one of Today's places. Margin per
sale may appear in a placed product's evidence as a unit price figure, never as a value or a
total (INV-087).

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

**FR-200** — While `shelf_plan` is unavailable, for any reason, Shelf plan offers a clearly marked
example of itself, as Reorder does (D-31, after D-29):
- a banner on every screen of it says it is an example and not the store's data;
- nothing in it can be approved, changed, saved, exported or sent;
- the engine, the published artefacts, the owner state and the pilot measurement never read
  it.

**FR-195** — Neither page has a control that changes anything, except FR-201's record on Shelf
plan and its undo. A team account sees both the same and cannot use that control (ADR-029).

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

#### Measuring what the plan did

**FR-201** — On each fixture's plan, the owner can record "I've arranged this shelf". It records
the existing `acted` outcome on that night's `shelf.plan` entry for the fixture (ADR-003,
ADR-038), carrying:
- the arrangement's date: the day his device's calendar shows when he presses;
- the plan's date and the plan's window;
- each product's shelf, facings and whether that shelf is at eye level, as the plan gave them.

Pressing it again on the same entry changes nothing: the first date stands. Undoing it removes
the arrangement, and its measurement with it **(decided here)**. A team account cannot write it
(ADR-029), and the marked example's control is disabled (D-31).

Each fixture's plan shows his latest arrangement of it and its date from `shelf_measurement`'s
published output, so every device shows the same once the nightly has read it. Until then, the
device he pressed on shows its own record. While a fixture's measurement is still running, the
button says that arranging it again ends that measurement (FR-202).

**FR-202** — An arrangement is measured over two windows of report days, each held to F8's
window rules (F8-S1 FR-144), and read by F8's evidence functions **(decided here)**:
- **before:** the window that ends the day before the plan's window begins;
- **after:** the window of the same length that starts the day after the arrangement.

The plan chose which products get more space and eye level from its own window. A product that
sold above its usual rate there by chance would sell less afterwards anyway, and would look like
a loss. A before window that shares no day with the plan's window removes that (INV-095).

An arrangement is not measurable, and says why, when:
- the daily reports hold no full before window ("history too short");
- the fixture was arranged again between the before window's first day and the after window's
  last day ("rearranged again before its measurement ended").

The window's length and its minimum report days are F8's policy values, and are provisional
(OQ-1207). Until the after window is complete, the measurement says how many report days remain.

**FR-203** — Each arranged product's change is stated net of what happened in the rest of his
store, by difference in differences **(decided here)**:
- its daily mean after ÷ before;
- divided by the comparison products' change: the ratio of the arrangement's after and before
  window terms in FR-205's regression.

It is one figure computed one way, so the products' changes and the store elasticity never
disagree about the yardstick. A product that sold nothing in the before window has no ratio, and
says so; it stays in FR-205.

Store-wide swings, such as holidays, move the comparison products too, which is why they are
the yardstick. They are always in other departments (FR-179), so the yardstick rests on ASM-078,
which FR-209 tests. With no comparison product there is no measurement, and the reason is "no
unchanged fixture to compare with". With comparison products that sold nothing in one of the
windows, the reason is "the comparison products did not sell". Shelf plan explains that the fixtures he leaves as they are
while another is measured are what it is measured against.

A product's net change describes what happened. It carries no verdict of its own: one fixture's
products share whatever else happened on it, so one product's change cannot be told apart from
that (§21).

**FR-204** — A product enters the measurement, arranged or comparison alike, only if it sold in
the plan's window **(decided here)**. That window shares no day with either measured window
(FR-202), so whether a product enters says nothing about its luck in them. Deciding it from the
before window would raise slow sellers' before figures, make them look as if they fell, and,
because the plan gives slow sellers less space, push that onto the elasticity. A product that sold
nothing in one measured window therefore counts as a zero, never as missing. A product left out is
named, with the reason.

**FR-205** — His store's own space elasticity is estimated across every measurable arrangement
together, by one Poisson regression **(decided here)**:
- one observation per product per window: its units, with the window's report days as exposure;
- a term per product and arrangement, and a term per window of each arrangement, which together
  make the difference in differences;
- for arranged products in their after window, three terms:
  - one for having been arranged at all;
  - the logarithm of after ÷ before facings;
  - the change in eye level: +1 moved to eye level, −1 moved off it, 0 otherwise.

The coefficient on the logarithm of facings is the elasticity. Separating it from the other two
terms keeps an eye-level move, and the tidying any rearrangement brings, from being counted as
the effect of space (§23). The eye-level term is dropped when no arranged product changed eye
level, and the estimate says so. That is decided once, on the full sample, so every bootstrap draw
estimates the same model.

The before facings and shelf are the later-dated of two records, provided it is dated no later
than the arrangement:
- the team's count from his shelf photographs (ADR-037);
- his previous arrangement of the fixture.

The after facings and shelf are the ones he recorded following (FR-201). A product whose before
facings are unknown or zero is named, and left out of the estimate, though not out of FR-203.

Its interval comes from a bootstrap that resamples whole fixtures, each with all its products and
arrangements. Products on one fixture share whatever happened there, so an interval that treats
them as independent would be too narrow. In a draw, an arrangement left with no comparison
product drops out of that draw. A draw left with no arrangement, or with no variation in after ÷
before facings, is drawn again. The estimate is published with the number of
arrangements and products behind it, and one verdict (CLAUDE.md rule 13):
- **measured**, when the interval excludes zero;
- **measured and not significant**, when it includes zero;
- **not measurable**, when any of these holds:
  - fewer arrangements or products than the policy minimums;
  - no comparison products;
  - no variation in after ÷ before facings among the arranged products;
  - a failed placebo (FR-209).

The interval's level and the two minimums are policy values, and are provisional (OQ-1207).

**FR-206** — The plan uses the research elasticity, 0.17 (Eisend 2014; §23), until his store's
own value meets all three of these conditions **(decided here)**:
- its verdict is "measured";
- it is above 0 and below 1, the range in which each further facing counts for less (FR-185);
- its placebo ran and found no drift (FR-209).

From then on the plan uses his value. It always names the value it used and why: his own value
is used, or the research value is used because his is not yet measured, is outside the range,
has no placebo, or because `shelf_measurement` is unavailable, giving its reason.

**FR-207** — The measurement is published by `shelf_measurement` (FR-208), per arrangement:
- the fixture, the arrangement's date, the plan's date and the two windows;
- per product, the daily mean before and after and its net change (FR-203), or why it was left
  out.

The store elasticity is published once, with its interval, counts, verdict and the placebo's
result (FR-205, FR-209). Everything is in units sold, never in ₪, and no figure adds a
fixture's products together **(decided here)**.

**FR-208** — `shelf_measurement` requires `products`, `store_layout` and `sales_daily`, with the
registry's reasons (FR-193). It also publishes rule-level reasons of its own:
- `layout_all_rejected`, as `shelf_plan` does;
- `owner_state_unavailable`, when the owner state was not pulled, as F13's measurement does.
  Arrangements are never treated as absent because the store's owner state could not be read
  (CLAUDE.md rule 10);
- `no_arrangement_recorded`, when owner state holds no `acted` outcome of `shelf.plan`.

It runs before `shelf_plan` in the same run, and `shelf_plan` reads the elasticity from it
(FR-206).

**FR-209** — Before his store's elasticity can replace the research value, it is tested for drift
that was there already **(decided here)**. The placebo is the same regression on two earlier
windows, while nothing was rearranged:
- its later window is the arrangement's before window;
- its earlier window sits as far before that as the before window sits before the after window,
  so it tests drift over the same distance the measurement spans;
- each arranged product carries the facing change and eye-level change it would later get.

Both its "arranged at all" term and its facing term should be "measured and not significant". If
either is "measured", the products the plan chose were already moving apart from the others, and
the store elasticity is "not measurable", with that reason. A product the plan gave more space
because it was rising, and that kept rising, shows up here as a facing term.

The placebo is held to the same minimum numbers of arrangements and products as FR-205. With fewer
arrangements that have the history for it, it is "not run", not passed, and FR-206 keeps the
research value. A placebo is weak evidence even when it runs: passing it is necessary for FR-206,
not proof that nothing drifted (ASM-078).

## 7. Behavioral Invariants

**INV-084** — No fixed camera, sensor or continuous image feed is ever an input (D-13).
*Violated if* any input reaches any of the three capabilities other than the committed layout
file, owner state and the existing artefact inputs.

**INV-085** — Demand is computed by F8's own evidence functions over F8's window, never derived a
second time. *Violated if* a product's demand in the plan differs from the `daily_mean`
`order_quantity` publishes for it on the same run, where it publishes one.

**INV-086** — A missing measurement, width, price, cost or demand is never filled in. *Violated if*
a product without a width is placed, or a product with unknown earnings gets more than one
facing.

**INV-087** — No F12 capability publishes a ₪ value, a total, a projected gain or a "margin per
metre" figure. Margin per sale appears only as a unit figure in a product's evidence, never
summed (ADR-012; CLAUDE.md rule 8). The publisher enforces it as it does for F8 and F9: it
refuses a value, or any money-named field other than a placed product's `margin_per_sale`, in
any of the three. *Violated if* any money figure in them adds products, facings or fixtures
together.

**INV-088** — Every catalogue product of a fixture's departments is either placed or named with
its reason. The reasons are "no width", "too wide", "kept off by his rule", "no sale or delivery
in the window", "count zero or below", "stock unknown", or the fixture being over-full or
stopped by a rule. *Violated if* a fixture's published products and its departments' catalogue
products differ.

**INV-089** — Nothing on either page can be changed, approved or sent, except FR-201's record and
its undo, which write that record and nothing else (FR-195). *Violated if* a click on either page
writes any other owner state, or a team account writes an arrangement.

**INV-090** — A product whose earnings per centimetre is unknown never takes a place in the
earnings order (FR-183). *Violated if* such a product is packed before one whose earnings are
known.

**INV-091** — Extra facings are never given on a fixture with a product of unknown size (FR-186).
*Violated if* a fixture with "no width" or "too wide" shows a product with more than one facing.

**INV-092** — A measurement never compares a window that fails F8's window rules, and is never
published without comparison products. *Violated if* a net change is published for an
arrangement with an incomplete window or no comparison.

**INV-093** — A measured change is never extended to the whole store, to other fixtures, to money
or to the future. The one exception is the store elasticity, which FR-206 applies to every
fixture's future plans, and only on FR-206's three conditions. *Violated if* a published figure
scales a measured change beyond its own products and windows, other than through FR-206.

**INV-094** — The plan uses his store's elasticity only on FR-206's three conditions. *Violated
if* the plan uses a store value whose verdict is not "measured", that is not between 0 and 1, or
whose placebo did not run or did not pass.

**INV-095** — A measurement's before window never shares a day with the window of the plan he
followed (FR-202). *Violated if* a published before window and the followed plan's window
overlap.

## 8. Behavioral Scenarios

**SCN-159** — Given no layout file, when the nightly runs, then all three capabilities are
unavailable (`no_store_layout`). Both pages say the measurements have not been recorded.

**SCN-160** — Given a layout file and no daily reports, when the nightly runs:
- `layout_facts` is available, and Store layout shows every recorded fixture with its dates and
  the products without a width;
- Shelf plan says it is waiting for the daily sales reports (`no_daily_sales`), shows no plan
  (D-30), and offers the marked example (D-31).

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

**SCN-169** — Given an owner on a fixture's plan, when he presses "I've arranged this shelf",
then one arrangement is recorded with the fixture, the date, the plan's date and window, and the
shelves and facings he followed. Pressing again changes nothing. A team account pressing it
writes nothing.

**SCN-170** — Given an arrangement 10 report days ago, when the nightly runs, then the fixture's
measurement says how many report days its after window still needs, and publishes no change.

**SCN-171** — Given every fixture arranged inside the windows, when the measurement is due, then
no net change is published, and the reason is "no unchanged fixture to compare with".

**SCN-172** — Given enough arrangements for a store elasticity that is "measured", between 0 and
1, with a placebo that passed, when the nightly runs, then the plan uses the store's value
instead of 0.17 and says so.

**SCN-173** — Given recorded arrangements and an owner state that could not be pulled, when the
nightly runs, then `shelf_measurement` is unavailable (`owner_state_unavailable`), and the plan
uses 0.17 and says it is because the measurement is unavailable.

**SCN-174** — Given an arrangement whose daily reports start inside its plan's window, when the
nightly runs, then that arrangement is not measurable ("history too short"). Given a second
arrangement of the same fixture inside the first one's after window, the first is not measurable
("rearranged again before its measurement ended").

## 9. Inputs and Observable Outputs

| Input | Source | Required? |
|---|---|---|
| Layout facts, with `measured_by` / `measured_on` or `stated_by` / `stated_on` | The committed layout file (ADR-037) | Yes, for all three capabilities |
| His catalogue: products, departments, shelf prices, unit costs, latest counts | The POS export (`products`) and his answered costs | Yes, for all three |
| Daily reports, F8's window and evidence | ADR-030; F8-S1 §5, FR-143 … FR-146 | Yes, for `shelf_plan` and `shelf_measurement` |
| His arrangement records | Owner state, pulled (ADR-003, ADR-038) | For `shelf_measurement`; without it, `owner_state_unavailable` (FR-208) |

| Output | Where it is observable |
|---|---|
| `layout_facts`: the recorded facts with dates, what is missing, rejected entries | `dashboard.json`; the Store layout page |
| `shelf_plan`: per fixture and shelf, products with facings and the reason; the unplaced lists; the conditions, including the elasticity used (FR-189) | `dashboard.json`; the Shelf plan page |
| `shelf_measurement`: per arrangement, its windows and products' changes; the store elasticity with its interval, counts, verdict and placebo (FR-207) | `dashboard.json`; the Shelf plan page |
| Rejected layout entries, by name and reason | The run's steps |

## 10. State / Lifecycle Semantics

Two things persist between runs:
- the committed layout file, whose history of commits records what was measured or stated, and
  when (ADR-037);
- his arrangement records in owner state, which he alone writes (ADR-038).

All three capabilities are recomputed every night from those, the catalogue and the daily
reports. No past artefact is read: each arrangement record carries the plan's date, the plan's
window and the facings he followed, and the windows are recomputed from the daily reports. A new
measurement of the layout, or a new arrangement, changes the next night's plan.

## 11. Failure and Recovery Behavior

- **Layout file absent:** all three capabilities are `no_store_layout`. Not an empty plan
  (CLAUDE.md rule 10).
- **Every fixture rejected:** `layout_all_rejected`, and the rejections are named.
- **Some entries rejected:** named in the run's steps; the rest are used (SCN-167).
- **Reports not yet arrived, too few days, or stopped:** `no_daily_sales`, `no_evidence_window`
  or `stale_daily_sales`, by the same rules F8 uses. Store layout is unaffected.
- **Owner state not pulled:** `shelf_measurement` is `owner_state_unavailable`. The plan uses the
  research elasticity and says why (FR-206, FR-208). His arrangements are never treated as
  absent.
- **Too little history, or rearranged again:** that arrangement is not measurable, with its
  reason (FR-202). The others are measured.
- **An arrangement recorded on two devices:** the browser does not read owner state back, so
  each device knows only its own presses. After the nightly, every device shows the published
  arrangement (FR-201). An undo can still be reversed by the other device (ASM-082).
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
| An arranged product whose before facings are unknown or zero | Named; left out of the elasticity, kept in its net change (FR-205) |
| Every arranged product kept its facings | The store elasticity is not measurable: no variation in facings (FR-205) |
| A product that sold in the plan's window and not in the after window | Kept, with a net change of zero (FR-204) |
| A product that sold in the plan's window and not in the before window | Kept in FR-205; it has no ratio of its own (FR-203) |

## 13. Non-Functional Requirements

**NFR-072** — None of the three capabilities adds a step whose time grows with the collected
market history. They read only the layout file, the catalogue, the daily reports and owner state
(compare the 2026-10-03 nightly, #276).

**NFR-073** — Reproduction: print mode and `npm run figures` compute the same plan and the same
measurement from the same committed inputs and owner-state mirror (ADR-002). The bootstrap's
random draws use a fixed seed.

**NFR-074** — The two pages render on a phone without horizontal scrolling, in Hebrew, Arabic and
English (the existing e2e invariants).

**NFR-075** — A store's layout file is store data. Updating a copy from the product never
overwrites it, and `check:store` reports whether it is present (ADR-036, ADR-037).

**NFR-076** — The measurement reads only the catalogue, the daily reports, the layout file and
owner state, and no past artefact. Its time grows with the arrangements he records and the bootstrap's draws, not
with the collected market history.

## 14. Compatibility and External Constraints

**C-73** — One store per copy (ADR-036, D-28). The layout file belongs to that copy's store.

**C-74** — The team, who measure, cannot write owner state (ADR-029). That is one reason the
layout is a file, not a form (ADR-037).

**C-75** — Front-end work waits for the owner's approval of its mockups. Both pages are built only
after he approves them.

## 15. Acceptance Criteria

**AC-172** — With no layout file, all three capabilities are `unavailable` (`no_store_layout`),
and both pages say the measurements have not been recorded. *(FR-191, FR-193, FR-194, FR-196)*

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

**AC-180** — No F12 capability publishes a ₪ value, total, projected gain or per-metre figure; any
margin is a unit figure in evidence, unsummed. *(FR-192, INV-087)*

**AC-181** — The published plan carries its window dates, every fact's date, the per-fixture
counts of FR-189 and the elasticity it used. *(FR-189)*

**AC-182** — Neither page writes owner state except FR-201's arrangement record and its undo, and
a team account writes nothing. *(FR-195, INV-089)*

**AC-183** — No input other than the layout file, owner state and the existing artefact inputs
reaches any F12 capability. *(INV-084; D-13)*

**AC-184** — A malformed fixture, rule or width is named in the run's steps, and the rest are used.
A department on two fixtures without a "keep on" rule is rejected, and so is a product of a split
department that no rule names. *(FR-178, FR-179, FR-199)*

**AC-185** — When the latest report day is older than `order_freshness_days`, `shelf_plan` is
`stale_daily_sales`. With reports but no window, it is `no_evidence_window`. *(FR-193)*

**AC-186** — In a department the evidence does not itemise, stocked products get one facing each,
with demand published as unknown, never zero. A product whose count is unknown is not planned
and is listed as "stock unknown". *(FR-181, FR-187, FR-197)*

**AC-187** — No F12 capability is admitted to the daily surface. *(FR-192)*

**AC-188** — Updating a store's copy from the product leaves its layout file unchanged, and
`check:store` names the file as missing when it is absent. *(NFR-075)*

**AC-189** — While `shelf_plan` is unavailable, for any reason, Shelf plan offers the marked
example. No engine step, published artefact, owner state or pilot measurement reads it.
*(FR-200; D-31)*

**AC-190** — Pressing "I've arranged this shelf" writes one `acted` outcome on that night's
`shelf.plan` entry, carrying the fixture, the date, the plan's date and window, and each product's
shelf, facings and eye level. Pressing it again leaves the date unchanged, and undoing it removes
the arrangement. After the nightly, the plan shows the arrangement from the published
measurement, and the button on a fixture whose measurement is running warns that pressing ends
it. A team account cannot write it. *(FR-201, INV-089)*

**AC-191** — No net change is published until both windows meet F8's window rules, and none
without comparison products. *(FR-202, FR-203, INV-092)*

**AC-192** — On a fixture-world test with known sales, each net change equals after ÷ before,
divided by the ratio of the arrangement's after and before window terms. On a fixture world built
with a known elasticity, FR-205's interval contains it. *(FR-203, FR-205)*

**AC-193** — A product, arranged or comparison, that did not sell in the plan's window is named
and left out. One that sold in it and not in a measured window is kept, as a zero. Whether a
product enters never depends on either measured window. *(FR-203, FR-204)*

**AC-194** — The store elasticity is published with its interval, counts, verdict and placebo
result. The plan switches to it only on FR-206's three conditions, and names the value it used
and why. *(FR-205, FR-206, INV-093, INV-094)*

**AC-195** — Every published measurement is in units, for its own fixture's products and
windows, never in ₪, never summed over a fixture, and never extended beyond them except through
FR-206. *(FR-207, INV-093)*

**AC-196** — With owner state not pulled, `shelf_measurement` is `owner_state_unavailable`, never
an empty measurement, and the plan names the research value and that reason. With no arrangement
recorded, it is `no_arrangement_recorded`. *(FR-206, FR-208)*

**AC-197** — The plan keeps 0.17 in three fixture worlds:
- where the later-arranged products already drift from the others between the placebo's
  windows, the placebo's arranged term is "measured" and the store elasticity "not measurable";
- where the products later given more space were already rising, the placebo's facing term is
  "measured", with the same result;
- where too few arrangements have the history, the placebo is "not run".

The placebo's windows are as far apart as the measured ones. *(FR-206, FR-209)*

**AC-198** — No published before window shares a day with the window of the plan followed. An
arrangement with too little history, or with another arrangement of its fixture inside its
windows, is not measurable and says which. *(FR-202, INV-095)*

## 16. Assumptions

**ASM-073** — A product's facing width does not change between packs of the same barcode.
*Falsified if* he sells one barcode in two pack sizes.

**ASM-074** — One measured usable length per shelf is enough. A shelf with dividers or uneven
depth is measured as the length that can hold products. *Falsified if* a fixture's products need
depth or height to fit.

**ASM-075** — A day a product sold nothing in either window is a day of no demand, not a day it
was out of stock. *Falsified if* stock-outs are common on measured fixtures: they would make a
plan look worse than it was, and nothing here detects them.

**ASM-076** — Nothing else changed on an arranged fixture between the windows, such as a
promotion or a supplier display. *Falsified if* he ran a promotion there. The comparison
products absorb store-wide changes, not changes on one fixture.

**ASM-077** — When he records an arrangement, the fixture matches the plan he followed, and it
stays so until his next recorded arrangement. Before then, it matched the later of the team's
count and his previous arrangement. *Falsified if* he arranges part of it, or moves products
without recording it. The facings used would then be wrong, and nothing here checks them: the
photograph check is out of scope (§3).

**ASM-078** — Had he not rearranged, the arranged products' sales would have moved by the same
proportion as the comparison products' (parallel trends). The comparison products are always in
other departments, and departments drift differently (CLAUDE.md rule 13). *Falsified if* FR-209's
placebo finds the arranged products already moving apart. Where the placebo was not run, nothing
tests it, and the plan keeps the research value (FR-206).

**ASM-079** — Arranging one fixture does not change what sells on the others. *Falsified if*
customers move purchases from comparison products to arranged ones, as with substitutes on two
fixtures. The yardstick would then fall, and the measurement would overstate the change.

**ASM-080** — He presses "I've arranged this shelf" on the day he rearranges the fixture.
*Falsified if* he presses days later. The days in between would count as after the arrangement,
which understates the change, and nothing here detects the gap.

**ASM-081** — The shelf prices of measured products, arranged and comparison, did not change
between the windows. *Falsified if* he changed one: part of the change in its sales is then the
price's. Nothing here detects it. The daily reports carry no price (ADR-030), and the POS export
is read only as it stands.

**ASM-082** — He records an arrangement from one device, or presses on a second only after the
first press shows on the plan. *Falsified if* he presses on two devices before the nightly, and
then undoes on one. The other device sends its record again when the app next loads, and the
arrangement comes back. Nothing here detects it until the browser reads owner state back (System
Design §11.5).

## 17. Open Questions

**~~OQ-1201~~** — "Who measures product widths: the team, from photos and a tape measure, or the
store owner?" **Answered 2026-10-03: "from photos".** The team reads the widths from his shelf
photographs (FR-180).

**~~OQ-1202~~** — "Should we run the one-day test of an AI reading a real shelf photo, before or
after a first version entered by hand?" **Answered 2026-10-03: "yes why not".** The test is
to be run. He did not choose between before and after, so its plan proposes the order for his
approval.

**~~OQ-1203~~** — "Should the waiting Shelf plan page show a clearly marked example of how it
will look, like Reorder does? That would be a new decision, D-31." **Answered 2026-10-03:
"yes", recorded as D-31 (FR-200).**

**OQ-1204** — What are the provisional space-elasticity factor and facings cap (FR-185)? The
architect proposes 0.17 for the factor, the meta-analysis mean (§23). The cap has no research
figure behind it and is still to be proposed. · owner: the repository owner · blocks: FR-185's
numbers, not its rule.

**~~OQ-1205~~** — "Are my design choices right?" **Answered 2026-10-03: "yes".** The choices
marked **(decided here)** at that time were:
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

**~~OQ-1206~~** — In his words: "the planogram is real science, how our product actually know what
to tell the owner to put where to give him the best sellings". **Answered 2026-10-04, in two
parts:**
- **§23 states the basis** of each rule, with its source.
- **He answered "yes"** to "Should I add the button and the before-and-after measurement to the
  spec?" FR-201 … FR-209 measure the plan in his own store. Once his own elasticity meets
  FR-206's conditions, it replaces the research value.

**OQ-1207** — What are the measurement's provisional values? The architect proposes them, and the
owner approves:
- the window's length and minimum report days (F8's);
- the interval's level;
- the minimum numbers of arrangements and of products for a store elasticity;
- the bootstrap's number of draws.

· owner: the repository owner · blocks: the numbers in FR-202, FR-205 and FR-209, not their
rules.

**OQ-1208** — Are the measurement's design choices right? The choices marked **(decided here)**
in FR-201 … FR-209 are:
- the first date of an arrangement stands, and undoing it removes its measurement (FR-201);
- the before window ends where the plan's window begins (FR-202);
- one product's change carries no verdict, and uses the regression's yardstick (FR-203);
- whether a product is measured is decided from the plan's window alone (FR-204);
- one Poisson regression across all arrangements, with a bootstrap over whole fixtures (FR-205);
- the store value replaces 0.17 only when measured, between 0 and 1, with a passed placebo
  (FR-206);
- no fixture total (FR-207);
- a third capability, not on Today (FR-208);
- the placebo, on both terms and over the same distance (FR-209).

· owner: the repository owner · blocks: building the measurement, not the plan.

## 18. Non-Goals

- A plan built from monthly reports, or from assumed demand, to show something now.
- A floor plan of the store. Store layout lists fixtures; it does not draw the floor.
- Promotions, end caps or seasonal moves.
- A measured gain in money, or one claimed for the whole store (FR-207, INV-093).
- A verdict on one product's or one fixture's change (FR-203, §21).
- How products affect each other's sales (cross-space elasticities).

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
| INT-006 | FR-200 | SCN-160 | AC-189 |
| INT-006 | FR-201 | SCN-169 | AC-190 |
| INT-006 | FR-202, FR-203, FR-204 | SCN-170, SCN-171, SCN-174 | AC-191, AC-192, AC-193, AC-198 |
| INT-006 | FR-205, FR-206, FR-207, FR-209 | SCN-172 | AC-192, AC-194, AC-195, AC-197 |
| INT-006 | FR-208 | SCN-173 | AC-196 |
| Protected behavior | INV-084 | — | AC-183 |
| Protected behavior | INV-085 | — | AC-179 |
| Protected behavior | INV-086, INV-088, INV-090, INV-091 | SCN-162, SCN-163, SCN-165 | AC-175, AC-176, AC-177 |
| Protected behavior | INV-087 | — | AC-180 |
| Protected behavior | INV-089 | SCN-169 | AC-182, AC-190 |
| Protected behavior | INV-092 | SCN-170, SCN-171 | AC-191 |
| Protected behavior | INV-093 | — | AC-194, AC-195 |
| Protected behavior | INV-094 | SCN-172 | AC-194 |
| Protected behavior | INV-095 | SCN-174 | AC-198 |
| Protected behavior | NFR-075 | — | AC-188 |

---

## 20. Boundary Probe

| Probe | What it would catch | Where it runs |
|---|---|---|
| `npm run check:order-signals` (exists), extended over its fixture world, which carries daily reports. The extension withholds the daily reports, the layout file and one product's width. | `shelf_plan` or `shelf_measurement` published without daily sales or a layout; `layout_facts` failing without sales; a product placed without a width | `collect-daily.yml` |
| The same probe, given arrangement records over the fixture world's daily reports. The records are taken from the contract fixture that `ownerStateContract.test.js` writes through the real `recordOutcome`, so they have the browser's shape (ADR-038). The probe withholds the records, then the owner state pull, and separately leaves every fixture arranged. | A measurement made without an arrangement; arrangements treated as absent when owner state was not pulled; a net change published with no comparison products (INV-092) | `collect-daily.yml` |
| `scripts/check_v1_signals.py`'s `PROBED_ELSEWHERE` guard (exists) | Once the `store_layout` input is in any capability's `requires`, `tests/test_check_v1_signals.py` fails until it is listed. Listing it also needs the probe's own word for it in that test | CI |

## 21. Claim Limits

| Claim | Verdict | Why |
|---|---|---|
| "Following the plan raises margin per metre by 20–68%" | not measurable | The figure is from elsewhere (intent), and the measurement is in units (FR-207). |
| "Arranging this fixture raised its sales by X%" | not measurable | One fixture's products share whatever else happened on it, so its own change cannot be told apart from the arrangement's effect. FR-203 states each product's change as what happened, with no verdict. |
| "Space elasticity in this store is E" | measured, measured and not significant, or not measurable (FR-205) | Across all his measurable arrangements, with its interval and placebo. Until it meets FR-206, 0.17 is the research average, not his. |
| "This product sells X a day", from the monthly reports | not measurable | Monthly rows have no days (rule 13). Only F8's daily window is used. |
| "The plan is optimal" | not measurable | The allocation is greedy with a provisional elasticity (OQ-1204). It is a defensible ranking, not a proven optimum. |

## 22. Unmapped PRD Acceptance Lines

None. FR-178 … FR-209 cover the PRD's V4 row: shelf photographs, rules, and generating the plan.
- Photographs enter only as the team's source for the recorded facts (§3).
- Facing widths are an input the PRD row does not name. They come from his shelf photographs
  (FR-180, OQ-1201).

---

## 23. Scientific Basis

OQ-1206, in his words: "the planogram is real science". For each rule the plan applies: where it
comes from, and whether it is measured in his store or assumed. The figures were checked against
the papers' published abstracts and the literature that cites them, on 2026-10-04.

| Rule | Source | What the source found | How F12 uses it | In his store |
|---|---|---|---|---|
| Space goes by profit per unit of space, not by sales share (FR-185) | Corstjens and Doyle, "A Model for Optimizing Retail Space Allocations", *Management Science* 27(7), 1981, 822–833 | Allocating by profit, with each product's response to space, beats rules of thumb such as sales share. Their model also includes cross-space elasticities and inventory costs | Margin per sale × demand ÷ facing width, per centimetre. Cross-elasticities and inventory costs are left out (§3) | Margin and demand are his own (F8; his prices and costs) |
| More space sells more, with diminishing returns (FR-185) | Curhan, "The Relationship between Shelf Space and Unit Sales in Supermarkets", *Journal of Marketing Research* 9(4), 1972, 406–412 | About 500 items had their shelf space changed, with sales watched 5 weeks before and 12 weeks after. The average space elasticity was 0.212 | Each further facing counts for less, by a space elasticity | Assumed until FR-205 measures it and FR-206 accepts it |
| The elasticity to start from (FR-206, OQ-1204) | Eisend, "Shelf space elasticity: A meta-analysis", *Journal of Retailing* 90(2), 2014, 168–181 | Across 1,268 estimates, the average was 0.17. It varied by category: lowest for commodities, then staples, highest for impulse buys | 0.17 until his own meets FR-206. At 0.17, doubling a product's space multiplies its sales by about 1.125. Being an average across categories, it may be high or low for a given fixture | Replaced by his own on FR-206's conditions |
| Shelf position matters more than extra facings (FR-183) | Drèze, Hoch and Purk, "Shelf management and space elasticity", *Journal of Retailing* 70(4), 1994, 301–326 | In field experiments in stores, location moved sales a lot. Facings moved them much less, as long as a product kept the minimum it needed not to run out. Fitting shelf sets to each store's own sales gained about 4% | The eye-level shelf goes first to the highest earners. Every planned product gets one facing first. F12 does not know each product's minimum to avoid running out, so one facing may be below it | Eye level is its own term in FR-205, so it is not counted as the effect of space. Its size is not published |
| Measure the change against products that did not change (FR-202, FR-203) | Difference in differences, a standard method for a change made to some units and not others | Compare the change in the changed units with the change in unchanged ones over the same days | His arrangement starts the clock. Fixtures he did not touch are the yardstick. A placebo on earlier windows tests that they were moving together before (FR-209) | When FR-205 says measured |
| Products chosen for a high window sell less afterwards anyway (FR-202) | Regression to the mean, a general statistical effect | A unit picked because its figure was high is likely to show a lower figure next time, with no change at all | Neither measured window shares a day with the plan's window, which chose the products and decides which are measured (INV-095, FR-204) | Removes the effect of the plan window's luck. A trend that continues past that window is not removed: the placebo tests for it (FR-209) |
| Products on one shelf share its luck (FR-205) | Clustered data, a general statistical effect | Treating units that share a shock as independent makes an interval too narrow | The bootstrap resamples whole fixtures | With few fixtures, the interval is still rough; the minimum numbers (OQ-1207) bound how rough |

**What this does not make the plan.** It is not optimal (§21): the packing is greedy, and the
elasticity starts as an average from other stores. It is not a forecast either: the measurement
says what happened on his arranged fixtures, in units. Nothing goes beyond them except his
store's elasticity, under FR-206's conditions (INV-093).
