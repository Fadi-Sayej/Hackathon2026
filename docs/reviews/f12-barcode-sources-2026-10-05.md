---
ID: F12-BARCODE-SOURCES
Title: Where a product's pack width could come from, by barcode — the half-day check D-34 asked for
Status: Ready for review — findings for the repository owner
Owner: smartshelf-engineer
Parent: [D-34](../product/intent-register.md#3-decisions-already-made-by-the-intent-layer)
Inputs: [D-3, D-23, D-33, D-34, data/internal/raw_pos/yomyom/sales/*.csv, data/external/snapshots/2026-10-04/, https://www.gs1il.org/, https://world.openfoodfacts.org/]
Updated: 2026-10-05
---

# Where a pack width could come from, by barcode

D-34 (2026-10-05) asked for this check before the shelf reader is designed: does a source we can
reach hold pack sizes for the store's products, at what cost, and on what terms? The answer
decides whether a shelf photo **measures** a width or only **confirms** one.

## The store's products

Read from the seven monthly sales reports the pilot store sent (2026-01 … 2026-07), the only
real sales data held (D-23). 1,778 distinct codes sold at least one unit:

| Kind of code | Codes | Share |
|---|---:|---:|
| EAN-13, Israeli prefix 729 | 1,000 | 56% |
| EAN-13, other prefixes (imports) | 391 | 22% |
| EAN-8 | 102 | 6% |
| UPC-A | 43 | 2% |
| The store's own codes (weighed goods, in-house items) | 242 | 14% |

**No outside database can know the 242 store codes.** For those, the photo is the only source.

## What we already collect

- **The chains' price files** (the price-transparency law; `price_transparency` in the nightly's
  snapshots): barcode, name, brand, unit and contents ("100 מיליליטר"). **No pack dimensions.**
- **Wolt's catalogue** (`delivery_catalog`): name, price, an online photo, and a `barcode_gtin`
  field, empty in the item read. **No pack dimensions**, and D-34 rules out online pictures.

## Open Food Facts (free, open data)

40 of the store's sold barcodes, sampled at random (seed 20261005), were looked up through its
public API. It answered 15 before limiting the rate (25 refused, not retried): 8 found, 7 not.
**None of the 8 carries a width, height or depth.** It records contents (`quantity`, such as
"500 g") and sometimes packaging material, not pack size. It cannot supply widths, whatever its
coverage.

## GS1 Israel's digital item catalogue

The one source built for this. From its public pages:
- "עשרות אלפי מוצרים ממגוון רחב של ספקים" (tens of thousands of products, from a wide range of
  suppliers), maintained by the brand owners themselves;
- images, including 360° product photos, and "נתונים לוגיסטיים" (logistic data). GS1's
  [Package and Product Measurement Standard](https://www.gs1.org/standards/gs1-package-and-product-measurement-standard/current-standard)
  defines how a product's width, height and depth are measured, and logistic data normally
  carries them. **The public pages do not list the fields**, so whether the catalogue gives each
  barcode's dimensions is likely, not confirmed;
- **access, price and terms are not public.** The pages for retailers
  ([catalogue for retailers](https://www.gs1il.org/digital-item-catalog-for-retailers/)) point to
  a contact form and 03-5198714. Whether a figure may be stored in this repository and published
  in the app's data is a question for those terms.

Its images are not usable for D-33 either way: D-34 allows only the store's own photos.

## What it means for the shelf reader

1. **Until GS1 Israel's terms are known, the photo must measure.** No source we can reach today
   holds a single pack width.
2. **If GS1 Israel gives dimensions and lets us use them,** it does more than confirm widths. It
   **replaces the printed card D-34 declined.** A product of known width standing on the shelf is
   a ruler at the depth of the product fronts, where the shelf edge is not (the council's point
   about fronts standing 5–30 cm behind the edge). The photo then picks which side faces out, and
   the two widths must agree within ±5 mm.
3. **The 242 store codes (14%) are photo-only** in every case.
4. **Without GS1,** the scale comes from the shelf edge and the shelf's recorded length, with the
   depth error the council named. The acceptance run on the next store's first photos (D-34)
   would show whether that stays within ±5 mm.

## The next step, and whose it is

Contacting GS1 Israel is outward-facing, and it is the repository owner's to do or to approve:
the four questions are which fields the catalogue holds, what share of these 1,778 barcodes it
covers, what access costs, and whether its figures may be stored and published in the app.
