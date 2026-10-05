---
ID: ADR-040
Title: A product's shelf picture is a file cut from the store's own photos, listed with its provenance and served as it is
Status: Proposal — awaiting the repository owner's acceptance with F12-S1 v0.9
Owner: smartshelf-architect
Date: 2026-10-05
Parent: [System Design](../system-design.md) §19
Related Specs: F12-S1 (FR-216, FR-217, AC-206, NFR-078)
Inputs: [D-13, D-22, D-23, D-33, D-34, docs/features/F12-planogram/specs/F12-S1-planogram.md, ADR-001, ADR-036, ADR-037, ADR-041]
Updated: 2026-10-05
---

# ADR-040 — A product's shelf picture is a file cut from the store's own photos

**Status:** Proposal, for the repository owner's acceptance with F12-S1 v0.9.

## Context

D-33 (2026-10-05): Shelf plan shows each product's picture on its shelf, from the store's own
shelf photos. A product without a picture yet shows its numbered tile. D-34, the same day: the
shelf reader cuts them, not people ([ADR-041](ADR-041-a-shelf-reader-reads-the-stores-photos.md)).
Neither says where the pictures are kept and how they reach the page.

ADR-037 already makes the store's shelves a committed file the team records from his photos, with
who measured each fact and when. It also says the photos are never an input to the engine, and
counts "no image handling" among its gains. A picture is a different kind of fact from a width:
the page shows it, and nothing computes from it.

D-13 excludes real-time shelf monitoring by fixed sensors or cameras. D-23 forbids making up what
a store would send.

## Decision

1. **One file per product, in the store's copy, at `public/store/shelf-pictures/`.** The shelf
   reader cuts the product's front from the photo it reads the product's width from, and writes
   the file there; the reading is committed with it. `public/` is what the site serves, so the page reads the file as it is, and no step
   copies or converts it.
2. **Listed with its provenance**, in a `pictures` section in the layout file's format. The
   reader writes it to its readings file, `configs/shelf_readings.yaml` (ADR-041):

   ```yaml
   pictures:
     "<barcode>": {file: <barcode>.jpg, cropped_by: reader, cropped_on: 2026-10-10}
   ```

   `cropped_by` is `reader`, as D-34 says. No name or email is written (D-22). A file in the folder
   that the layout file does not list is not shown.
3. **Validated at load, never repaired** (ADR-037 rule 2). A picture entry is rejected by name, and
   the product keeps its numbered tile, when:
   - no catalogue product has its barcode;
   - its file name is not a plain name ending `.jpg`, `.jpeg`, `.png` or `.webp`. A path is never
     accepted, so an entry cannot reach outside the folder;
   - the file is missing, larger than 150 KB, or does not begin as the type its name says.

   That check reads a file's size and its first bytes. Nothing reads what a picture shows: no
   step looks at the image, so D-13 holds, and ADR-037's "photos are never an input to the
   engine" holds for every figure.
4. **Published as an address, not as data.** `layout_facts` publishes each listed product's
   picture address and `cropped_on`, and the planned products without one, per fixture, as it
   does for widths (F12-S1 FR-217). `shelf_plan` gives each placed product its address. The
   address carries `cropped_on` (`?v=2026-10-10`), so a new crop is never hidden by the browser's
   copy of the old one. No figure depends on a picture.
5. **Store data under ADR-036.** `public/store/**` joins the files a new copy starts without, so
   one store's pictures never appear in another's copy, and updating a copy never overwrites
   them. `check:store` reports how many pictures are listed, and how many of those are present.

## Rejected options

### Pictures from the market data or the web
The nightly collects nearby stores' listings, and product photos exist elsewhere. D-33 asks for
the store's own photos, which show the products as they stand on his shelves. A picture from
somewhere else would be a picture of another shop's product, and its use is not ours to grant.

### A generated or drawn picture
D-23: nothing stands in for what a store would send. A product without a picture keeps its
numbered tile, which says that the picture has not been taken.

### Cropping by hand
D-34: no one cuts pictures.

### Keeping the files in `configs/`, copied into `public/` each night
It would add a copy step and a commit of image files to the nightly, for files that do not
change between nights. Kept where the site serves them, they are committed once, with the layout
file that lists them.

## Consequences

**We accept:** pictures add to the repository's size: at 150 KB at most, a store of 300 products adds
at most 45 MB, and a typical crop is far smaller.

**We gain:** the plan looks like his own shelf, drawn from his own photos, with no new kind of
storage.

**We will know it was wrong if:** most products have no picture after a reading. Then the reader's
identity step (ADR-041 Decision 4) is the bottleneck, not where pictures are kept.

## Reversibility

Easy. Pictures feed no figure. Removing the section leaves every plan as it is, with numbered
tiles.

## Binds

| F# | How this constrains it |
|---|---|
| F12 | Pictures come only from this folder and section (F12-S1 FR-216). ADR-037 is amended in part: its "no image handling" no longer holds, and the rest stands |
| Every other feature | Unaffected: no capability other than `layout_facts` and `shelf_plan` reads the section |
