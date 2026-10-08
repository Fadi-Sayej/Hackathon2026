---
ID: ADR-041
Title: A shelf reader reads widths, facings and pictures from the store's own photos; people never measure them
Status: Accepted
Owner: smartshelf-architect
Date: 2026-10-05
Parent: [System Design](../system-design.md) §19
Related Specs: F12-S1 (FR-180, FR-205, FR-216, FR-218 … FR-223, AC-207 … AC-210, NFR-079, OQ-1211)
Inputs: [D-3, D-13, D-23, D-33, D-34, D-35, docs/reviews/f12-barcode-sources-2026-10-05.md, ADR-032, ADR-035, ADR-036, ADR-037, ADR-039, ADR-040]
Updated: 2026-10-06 (D-36: the package's printed name where there is no tag; ADR-042: the photos come from the app, and the nightly reads them)
---

# ADR-041 — A shelf reader reads the store's own photos

**Status:** Accepted (2026-10-05, by the repository owner: "approve", with F12-S1 v0.9). It amends ADR-037
(who writes widths, current facings and pictures) and ADR-040 (who crops the pictures).

## Context

D-34 (2026-10-05): no one measures widths or cuts pictures. A shelf reader does it from the
store's own photos:
- the AI reads each shelf tag and counts the facings, and is matched only against products the
  store has recently sold. One clear match names the product, and anything else leaves it
  unknown;
- the AI marks rough areas, and image processing finds the exact edges on the full photo;
- pictures are cut automatically from the store's own photos;
- every AI answer is sealed, and its cost is estimated before it is switched on;
- the tolerance is ±5 mm per product. About 20 hand readings grade the reader once, on the next
  store's first photos, and never feed a plan;
- no printed card is stood on the shelves.

D-35: there is no barcode database, so the photo measures every width.

A photo has no scale of its own. With no card and no database, the one real length available is
the shelf's. ADR-037 already records each shelf's length in the layout file, as a fact of the
unit stated once, like its departments.

## Decision

1. **The photos.** The store photographs each shelving unit from the front, straight on, with the
   whole unit in frame. They are hand-held photos: D-13 holds. They are store data, kept in the
   store's copy at `data/internal/shelf_photos/<YYYY-MM-DD>/<fixture>/`, in a private
   repository. They are never published, and nothing but the reader opens them. Only a
   product's crop leaves a photo (Decision 7). Until the app has an upload, a store's photos are
   committed to that folder by whoever receives them. That is moving files, not measuring.

   *Amended 2026-10-06 by ADR-042.* The app has its upload: the nightly collects the photos sent
   from it into this folder. A photo committed by hand is still read the same way.
2. **When it runs.** On demand, when photos arrive: `npm run read:shelves`, or a manually started
   workflow. It never runs in the nightly. Its output is committed, and the nightly reads it like
   any other store file.

   *Amended 2026-10-06 by ADR-042.* The nightly runs it when it has photos not read yet and the
   model key is set, before the engine, within the same ceiling and time budget.
3. **The AI step**, sealed as the explanation is (ADR-039):
   - each photo is sent whole, and each shelf again as a full-resolution strip, so the tags'
     small print can be read;
   - the answer is JSON. Per shelf, it gives the shelf's two ends at the line of the product fronts.
     Per run of identical facings, left to right, it gives a rough box, the facing count and the
     tag text below the run;
   - the model and prompt are pinned. The answer is sealed in
     `data/external/snapshots/<date>/shelf_readings/`, with the photo's digest, and reused while the
     photo, model and prompt are unchanged. Print mode never asks;
   - a request ceiling and a time budget sit in policy, as the boost's and the explanation's do.
4. **Identity** (D-34). The candidates are the catalogue products the store has sold in the
   policy's recent window. A run is a product when:
   - its tag shows a code that is exactly one candidate's barcode or store code; or
   - its tag's name matches exactly one candidate, after normalising spaces and punctuation, and
     the tag's price equals that product's shelf price.

   Anything else leaves the run unknown, and the model's own confidence is never used. A 1 L and a
   1.5 L bottle of one brand differ in name or price on the tag, and a tie between them is
   unknown.

   *Amended 2026-10-06 by D-36.* Where a run has no tag, the AI transcribes the brand, name and
   size printed on the package's front, and the run is the single candidate in the unit's
   departments whose POS words, apart from its size, are all printed there, with no printed size
   contradicting its POS name (F12-S1 FR-220 v0.10). The tag, where there is one, is still the
   only thing read.
5. **Edges and width.** Within the AI's rough box, image processing finds the run's left and
   right edges, and the boundaries between its facings, on the full-resolution photo. It finds the
   shelf's ends at the line of the product fronts the same way. Then:
   `width_mm = run width ÷ facings ÷ shelf span × the shelf's recorded length`.
   The shelf's length is the one real length the reader needs: one figure per shelf, stated once
   in the layout file. Nobody measures a product.

   *Amended 2026-10-08 by ADR-044 (D-38).* The reader also measures each product's height on the
   same photo, in the same scale, down to the shelf's line. Heights pass the same checks, go to
   the readings file's `heights`, and are used only after their own acceptance run.
6. **The checks.** A width is recorded only when every check passes, and otherwise stays unknown,
   with its reason (D-3):
   - the facings found by image processing equal the AI's count;
   - the facings within the run agree with each other within ±5 mm;
   - a product read in two runs, or two photos, agrees within ±5 mm;
   - the runs fit within the shelf's span.
7. **Pictures and current facings.** For each named run, the reader cuts one facing as the
   product's picture (ADR-040, `cropped_by: reader`). It records the run as the product's current
   fixture, shelf and facings: the "before" F12-S1 FR-205 measures from.
8. **Where the readings go.** The reader writes `configs/shelf_readings.yaml`, a machine file in
   the layout file's own format. Its sections are `widths`, `current` and `pictures`, each entry
   with `measured_by: reader` (or `cropped_by: reader`) and the photo's date. The layout file keeps
   what is stated: fixtures, shelf lengths and rules. The loader reads both, and the same checks
   apply. The readings file is store data under ADR-036.

   *Amended 2026-10-06 by ADR-042 (built in Task 8.13).* A fourth section, `photos`, lists each
   photo the AI answered for, with the day it was read. Each reading adds to the earlier ones,
   because photos arrive a unit at a time.
9. **The acceptance run** (D-34). `configs/shelf_reader_acceptance.yaml` holds about 20 products
   measured by hand on the same store's first photos, with who measured them and when. The engine
   compares them with the reader's widths at every run. The reader's widths are used only when
   at least 20 products are listed and every one is within ±5 mm. Until then, its widths are
   recorded but not used: those products plan as "no width", and the page says the reader's widths
   are waiting for their acceptance run. Pictures and current facings are used from the first
   reading. The hand readings never enter a plan.
10. **Cost, estimated before it is switched on** (D-34). This uses ADR-032's prices ($2 in and $10
    out per million tokens), and assumes about 1,600 tokens per image at the model's largest
    size, a whole photo plus about five shelf strips, and about 3,000 tokens out per photo:
    - about 12,000 tokens in and 3,000 out per photo, which is about **$0.05 a photo**;
    - for a store of 15 units, one photo each, a full reading costs about **$0.80**;
    - it runs only when photos arrive.

    The first reading's measured usage replaces these assumptions, and the owner's monthly limit
    covers it (ADR-032).
11. **One new dependency: Pillow**, the standard Python imaging library, for reading the photos
    and cutting the pictures. The edge-finding uses it with numpy, which is already present.

## Rejected options

### People measuring (D-34)
The owner rejected it.

### A printed card on each shelf (D-34)
The owner rejected it. It would have given the scale at the depth of the product fronts. Without
it, the scale comes from the shelf's span at that depth and its stated length (Decision 5).

### A barcode database (D-35)
None we can reach holds a pack width, and GS1 Israel is not contacted.

### The AI's boxes as the measurement
The model sees a reduced copy of the photo, about 1.3 mm a pixel across a 2 m unit before any error
in its boxes. Its boxes locate. Image processing on the full photo measures.

### A dedicated shelf-detection model (such as one trained on SKU-110K)
It would be a second model to install, tune for a CPU and validate, for boxes the AI already gives
roughly and image processing then refines.

### Image processing alone
It cannot read a tag, so it cannot say which product a run is.

## Consequences

**We accept:** the reader has never seen a real shelf. There is no store and no photo (D-23). Its
widths stay unused until the acceptance run passes on the next store's first photos. Each shelf's
length is still stated once.

**We gain:** the plan, its pictures and the measurement's "before" come from the store's own
photos, with no one measuring a product. A wrong reading stays unknown instead of becoming a plan.

**We will know it was wrong if:** the acceptance run fails, or most runs end unknown because their
tags cannot be read. Then the next decision is the app's own capture screen, which takes the photo
with guidance (straight on, whole unit, no glare), or a different scale.

## Reversibility

Moderate. The readings file has the layout file's format, so the plan reads a width the same way
wherever it came from. Removing the reader leaves products without a width, which the plan
already handles.

## Binds

| F# | How this constrains it |
|---|---|
| F12 | Widths, current facings and pictures come from the reader's readings file (F12-S1 FR-180, FR-218 … FR-223). ADR-037 keeps the stated facts; ADR-040 keeps where pictures sit |
| Every other feature | Unaffected |
