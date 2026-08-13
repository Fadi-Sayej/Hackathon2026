import { normalizeInventory } from './inventoryAdapter.js'
import { normalizeSales } from './salesAdapter.js'
import {
  nonNegativeNumber,
  optionalDate,
  positiveNumber,
  requiredString,
  withProductContext,
} from './validation.js'

export function normalizeProduct(rawProduct, rowIndex = 0) {
  const localIssues = []
  const productId = requiredString(
    rawProduct.id ?? rawProduct.sku ?? rawProduct.productId,
    `demo-product-${rowIndex + 1}`,
    'id',
    localIssues,
  )

  const product = {
    id: productId,
    name: requiredString(
      rawProduct.name ?? rawProduct.productName,
      `Unnamed Product ${rowIndex + 1}`,
      'name',
      localIssues,
    ),
    category: requiredString(
      rawProduct.category ?? rawProduct.department,
      'Uncategorized',
      'category',
      localIssues,
    ),
    ...normalizeInventory(rawProduct, localIssues),
    ...normalizeSales(rawProduct, localIssues),
    price: positiveNumber(rawProduct.price ?? rawProduct.unitPrice, 1, 'price', localIssues),
    cost: nonNegativeNumber(rawProduct.cost ?? rawProduct.unitCost, 0, 'cost', localIssues),
    expiryDate: optionalDate(rawProduct.expiryDate, 'expiryDate', localIssues),
    supplier: requiredString(
      rawProduct.supplier ?? rawProduct.vendor,
      'Preferred supplier',
      'supplier',
      localIssues,
    ),
    leadTimeDays: nonNegativeNumber(
      rawProduct.leadTimeDays ?? rawProduct.leadTime,
      1,
      'leadTimeDays',
      localIssues,
    ),
    // How much sales history the numbers above rest on: 'none' | 'low' | 'medium'
    // | 'high'. inventoryEngine gates every velocity-derived verdict on this, so
    // dropping it here made real measured sales read as "no history" and put the
    // whole catalog back on "Not enough sales history yet". Anything without the
    // field is genuinely unknown, so 'none' is the right default.
    velocityConfidence: rawProduct.velocityConfidence ?? 'none',
    // true = restocked at least once; false = sells but is never delivered
    // (services, made-to-order, staff consumption); null = unknown.
    isStocked: typeof rawProduct.isStocked === 'boolean' ? rawProduct.isStocked : null,
    // false = stock fails the D-7 reconciliation, so any figure computed FROM it
    // (days of cover, order quantity) is not defensible. null = not checkable.
    stockReconciles:
      typeof rawProduct.stockReconciles === 'boolean' ? rawProduct.stockReconciles : null,
  }

  if (product.shelfCapacity === 0) product.shelfCapacity = Math.max(product.shelfQuantity, 1)
  if (product.shelfQuantity > product.shelfCapacity) product.shelfQuantity = product.shelfCapacity
  if (product.cost > product.price) {
    localIssues.push({
      field: 'cost',
      code: 'cost_above_price',
      message: 'cost is greater than price; keeping value for margin visibility.',
      severity: 'info',
      value: product.cost,
    })
  }

  const issues = localIssues.map((issue) => withProductContext(issue, product.id, rowIndex))
  return { product, issues }
}

/**
 * Make a colliding id unique, deterministically.
 *
 * The department is tried first because that is what genuinely differs: the same
 * sandwich is sold from the barista counter and the drive-through at different
 * prices, and both rows are real. Only if the department repeats too does an
 * occurrence counter get appended.
 *
 * Determinism matters more than elegance here. Approved plans, reorder decisions
 * and shelf photos are all keyed by product id; an id that shuffled between
 * loads would silently detach every saved decision from its product.
 */
function disambiguateId(baseId, category, taken) {
  const scoped = category ? `${baseId}--${category}` : baseId
  if (!taken.has(scoped)) return scoped

  let occurrence = 2
  while (taken.has(`${scoped}#${occurrence}`)) occurrence += 1
  return `${scoped}#${occurrence}`
}

/**
 * Normalise a whole catalogue, guaranteeing unique ids.
 *
 * WHY THE UNIQUENESS PASS EXISTS
 *   `scripts/normalize-datasets.mjs` derives the id from a barcode, or from the
 *   product name when there is no barcode. Neither is unique in the real export:
 *   76 ids collide across 7,451 rows, 83 rows deep, and 68 of those collisions
 *   hold genuinely different prices or costs.
 *
 *   Everything downstream indexes by id — `productIndex` in App.jsx, React list
 *   keys, approved plans, shelf photos. A `Map` keyed by a non-unique id keeps
 *   whichever row arrived last and drops the rest without a word. One of the
 *   rows being dropped is what supplies the unit cost on a purchase order.
 *
 *   The generator is fixed too, but this pass is the boundary every product
 *   crosses — bundled catalogue and uploaded CSV alike — so it is the layer that
 *   can promise the invariant regardless of where the data came from.
 */
export function normalizeProducts(rawProducts) {
  const normalized = []
  const issues = []
  const taken = new Set()

  for (const [rowIndex, rawProduct] of rawProducts.entries()) {
    const result = normalizeProduct(rawProduct, rowIndex)
    const product = result.product
    issues.push(...result.issues)

    if (taken.has(product.id)) {
      const uniqueId = disambiguateId(product.id, product.category, taken)
      issues.push({
        row: rowIndex,
        field: 'id',
        severity: 'warning',
        message: `Duplicate product id "${product.id}" — kept as "${uniqueId}". The source export reuses this key across departments.`,
      })
      product.id = uniqueId
    }

    taken.add(product.id)
    normalized.push(product)
  }

  return {
    products: normalized,
    issues,
  }
}
