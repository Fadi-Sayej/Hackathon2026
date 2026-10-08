---
ID: ADR-044
Title: The owner enters each shelving unit in the app, with each shelf's length and height; the reader measures product heights, and the plan checks they fit
Status: Proposed
Owner: smartshelf-architect
Date: 2026-10-08
Parent: [System Design](../system-design.md) §19
Related Specs: F12-S1 (FR-228 … FR-234, AC-215 … AC-220, NFR-081, ASM-084, OQ-1213)
Inputs: [D-3, D-13, D-23, D-34, D-38, ADR-029, ADR-036, ADR-037, ADR-041, ADR-042, docs/reviews/F12-unit-form-mockups.md]
---

# ADR-044 — The owner enters each unit, and heights are checked

**Status:** Proposed, for the repository owner's approval with the screens
([mockups](../../reviews/F12-unit-form-mockups.md)) and F12-S1 v0.12. If accepted, it amends
ADR-037 (who records a unit) and ADR-041 Decisions 5, 6, 8 and 9 (the reader measures heights too).

## Context

D-38 (2026-10-08): the owner enters each shelving unit in the app, on Store layout, each shelf's
length and height included, so no one edits the layout file. Height is used: the reader measures
each product's height from the photo, and the plan checks that a product fits under the shelf
above.

Today:
- the units live in `configs/store_layout.yaml`, which the team writes from what the owner says,
  and which changes only by commit (ADR-037);
- each shelf has a length and no height. The shelf's length is the one real length the reader
  measures from (ADR-041 Decision 5);
- the plan fits products side by side only. F12-S1 ASM-074 assumes height never stops a product
  fitting.

The reader's AI already gives each group of products a rough box, top and bottom included, and
image processing already finds the shelf's edge. So a product's height needs no new request.

## Decision

1. **The form** (D-38). On Store layout, above the photos. Per unit:
   - its name, which its photos use too;
   - its departments, from the catalogue's own list;
   - whether it is chilled;
   - its shelves from the top, each with its length and its height in whole centimetres. Height
     is measured from the shelf up to the shelf above it. The top shelf's height may be left
     empty when nothing is above it;
   - which shelf is at eye level.

   The form starts from the units the artefact publishes, and saves the whole list. A team account
   sees it disabled (ADR-029). It is shown where the upload is: where Firebase is configured and
   sign-in is on.
2. **The carrier is the owner's state.** The list is one document,
   `stores/<store>/ownerState/layout`, with the day it was saved, written whole on each save. The
   deployed rules already let the owner write it and the team only read it.
3. **The nightly writes it into the layout file** (amends ADR-037). It runs in the step that
   collects the photos, before the engine, with the same service account:
   - the app's list replaces the file's `fixtures` section. Everything else is kept: the rules,
     and what the reader read;
   - a unit the owner changed carries the day of the change. An unchanged unit keeps its dates;
   - the file records which save it took (`entered_in_app`), so a save is written once, and a
     later correction by the team is not undone the next night. The form opens on a save the file
     has not taken yet, so a second save never undoes the first;
   - the file is committed, so ADR-037's "changed only by commit" and its history hold;
   - a unit entered in the app says `recorded_by: app`, and each shelf says `measured_by: owner`.
     Store layout then says "As you entered it on …", not "recorded by the team".

   The loader checks a unit from the app exactly as it checks one the team wrote. A unit it
   rejects is named on Store layout, as today.
4. **Shelf heights in the file.** Each shelf may carry `height_cm`. The top shelf may carry
   `null`: open above. Store layout shows each shelf's height.
5. **The reader measures heights** (amends ADR-041 Decisions 5 and 6). Image processing finds
   the shelf's line once, across the whole shelf: the top of its front edge, which a single
   product's bottom can barely differ from. Each facing's top is the topmost sharp edge near the
   AI's box, never above the tallest product's top, where the shelf above hangs its edge and
   tags. Then:
   `height_mm = (shelf edge − top edge) in pixels × the width's own millimetres per pixel`,
   the shelf's length over its span. A height is recorded only when:
   - the facings' heights agree within ±5 mm;
   - a product read in two runs or two photos agrees within ±5 mm;
   - it is no taller than its shelf's height, where the shelf has one.

   Otherwise it stays unknown, with its reason (D-3). Heights go to the readings file's `heights`
   section, beside `widths` (amends Decision 8).
6. **The acceptance run covers heights** (amends ADR-041 Decision 9). The hand readings on the
   store's first photos also give each product's height. The reader's heights are used only when
   at least 20 are listed and every one is within ±5 mm, as its widths are.
7. **The plan checks heights** (F12-S1 FR-233):
   - on a unit whose shelves carry heights, a product is placed only when its width and its height
     are known. A product with no height is listed under "height not measured", as one with no
     width is today;
   - a product goes only on a shelf whose height is at least its own plus a clearance, so it can be
     taken out. The clearance is a policy value, **2 cm, provisional** (OQ-1213). An open shelf has
     no limit;
   - the packing order is unchanged: eye level first, then spread by length. A shelf a product
     does not fit under is passed over for the next one in the order that it fits and has room;
   - a product taller than every shelf of its unit is not placed, and is listed as "taller than
     every shelf", as one wider than every shelf is today;
   - a "together" set goes on a shelf every one of its products fits under. The tallest shelf fits
     any product that fits anywhere, so there always is one;
   - a unit recorded without heights, by the team before D-38, is planned as today, with no
     height check.
8. **The drawing to scale** (F12-S1 FR-234). Shelf plan draws a unit to scale when every shelf has
   a height (or is open above) and every placed product has one. Each shelf's row is drawn in
   proportion to its height, and each tile to its product's height. An open shelf is drawn a
   little taller than its tallest product. Otherwise the drawing is as today.
9. **No new cost.** A height comes from the same photo and the same answer as the width, so no
   request is added and NFR-079's estimate stands.

## Rejected options

### The team keeps recording the units
ADR-037 as it stands. D-38 asks that no one edits the layout file.

### The engine reads the units straight from the owner's state
That would mean one fewer step, but the layout's history would live in Firestore, not in commits
(ADR-037 Decision 4). There would also be two places a unit comes from, with two loaders.

### Heights recorded but not used
That was "A" in the question put to the owner. D-38 chose B: height is used.

### The AI's box as the height
The model sees a reduced photo, about 1.3 mm a pixel across a 2 m unit, before any error in its
box (ADR-041). Its box locates, and image processing measures, as for widths.

## Consequences

**We accept:**
- the reader's heights, like its widths, have never met a real shelf (D-23). They stay unused
  until the acceptance run passes on the next store's first photos. Until then, on a unit with
  heights, no product is placed, which is already true of widths;
- the owner measures each shelf once, with a tape: two numbers a shelf.

**We gain:**
- no one edits the layout file;
- a tall bottle is never planned under a low shelf;
- the drawing shows the unit as it stands.

**We will know it was wrong if:** the acceptance run passes for widths but fails for heights. That
would mean a hand-held photo is not straight enough for one scale to serve both directions
(ASM-084). The next step would be the app's own capture screen, which guides the photo.

## Reversibility

High for the form: the file keeps its format, and the team can write it again. Moderate for the
plan: a unit without heights is planned as today.

## Binds

| F# | How this constrains it |
|---|---|
| F12 | Units come from the owner's form (FR-228, FR-229); shelves carry heights (FR-230); the reader measures heights (FR-231, FR-232); the plan checks them (FR-233) and draws to scale (FR-234) |
| Every other feature | Unaffected |
