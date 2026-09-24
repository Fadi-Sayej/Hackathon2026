/**
 * catalogueToProducts — catalogue rows in the shape the restored product pages read.
 *
 * A pure mapping. It computes nothing, defaults nothing to zero, and invents no field the
 * catalogue does not carry. Four of its decisions are load-bearing.
 *
 * 1. `delivery_price` IS NOT COMPETITOR DATA, AND IS NOT MAPPED TO IT
 *    `competitor` stays null here. The obvious move is to feed `delivery_price` into
 *    `product.competitor.cheapestCompetitorPrice`, because both are "another price for the
 *    same product" and PriceGapPage would light up immediately. It would also be false:
 *    `delivery_price` is `wolt_price` (src/engine/inputs.py:107) — the store's OWN delivery
 *    listing, not a rival's shelf. Mapping it across would tell the owner a competitor was
 *    undercutting him with his own price. Real competitor prices live in the artefact's
 *    `competitor_position` capability and reach the page from there.
 *
 * 2. NO SALES FIELDS AT ALL, NOT ZEROED ONES
 *    `salesLast7Days`/`salesLast30Days` are absent, so `resolveVelocityConfidence` returns
 *    'none', `hasUsableVelocity` is false, and `inventoryEngine` gates every velocity-derived
 *    verdict off and reports `noVelocityData`. Writing 0 instead would make 7,523 products
 *    read as "Slow moving" — the exact conflation velocityConfidence.js was written to stop.
 *
 * 3. IDENTITY IS NOT BARCODE ALONE
 *    248 of the 7,523 rows carry `barcode: null`, and ADR-019/ADR-022 identify those by name.
 *    Keying the index on barcode would collapse all 248 onto one id, which is the defect
 *    those ADRs exist for — reappearing in the UI layer where nobody would look for it.
 *
 * 4. PRICES STAY NULL (D-3)
 *    A product with no shelf price has no shelf price. `formatShekel` already renders null as
 *    '—' and 0 as ₪0.00, so passing the null through is what keeps those two apart on screen.
 */

const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null)

/**
 * A stable id for a catalogue row.
 *
 * Prefixed by kind so a barcode and a name-derived id can never collide, and so an id read
 * off a rendered page says which of the two identity paths produced it (ADR-022).
 */
export function productId(row) {
  const barcode = row?.barcode
  if (typeof barcode === 'string' && barcode.length > 0) return `b:${barcode}`
  const name = row?.product_name
  return typeof name === 'string' && name.length > 0 ? `n:${name}` : null
}

/** One catalogue row in the pages' product shape. */
export function toProduct(row) {
  const id = productId(row)
  if (!id) return null              // no barcode and no name: nothing to identify it by
  return {
    id,
    name: row.product_name ?? null,
    category: row.department ?? null,
    price: num(row.shelf_price),
    cost: num(row.cost_price),
    costSource: row.cost_source ?? null,
    // Raw, negatives included — F2's whole point — and carrying no money (D-1).
    currentStock: num(row.recorded_stock),
    hasIdentifier: row.has_identifier === true,
    // The store's own delivery listing. Named for what it is so no caller mistakes it for a
    // rival's price. See note 1.
    deliveryPrice: num(row.delivery_price),
    // Not in the catalogue, so null, and ProductsPage shows '—'. ApprovedOrdersPage grouped by
    // it until the page was removed on 2026-09-24 (ADR-028).
    supplier: null,
    // Not competitor data. See note 1.
    competitor: null,
  }
}

/**
 * @param {object|null} catalogue a payload from `loadCatalogue`
 * @returns {Array|null} products, or null when the population could not be loaded —
 *   never [] for that case, which would read as an empty shop.
 */
export function catalogueToProducts(catalogue) {
  const rows = catalogue?.products
  if (rows === null || rows === undefined) return null
  if (!Array.isArray(rows)) return null
  return rows.map(toProduct).filter(Boolean)
}
