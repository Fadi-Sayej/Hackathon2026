import { normalizeInventory } from './inventoryAdapter.js'
import { normalizeSales } from './salesAdapter.js'
import {
  nonNegativeNumber,
  optionalDate,
  positiveNumber,
  requiredString,
  withProductContext,
} from './validation.js'

const LEAD_TIME_CONFIDENCES = new Set(['low', 'medium', 'high'])

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
    // Where leadTimeDays came from: 'measured' = a median over at least three
    // recorded deliveries from this supplier (T7 receiving ledger); 'default' =
    // no delivery interval has ever been observed for it, so the number is an
    // assumption. Anything that puts leadTimeDays into a sentence has to know
    // which of the two it is holding, so this must survive normalization —
    // dropping it here is what let the reason text state an assumed 3 as fact.
    leadTimeSource: rawProduct.leadTimeSource === 'measured' ? 'measured' : 'default',
    // What the measured median rests on: 'high' (>= 6 delivery dates), 'medium'
    // (3-5), 'low' (below the threshold, i.e. not measured at all).
    leadTimeConfidence: LEAD_TIME_CONFIDENCES.has(rawProduct.leadTimeConfidence)
      ? rawProduct.leadTimeConfidence
      : 'low',
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

export function normalizeProducts(rawProducts) {
  const normalized = []
  const issues = []

  for (const [rowIndex, rawProduct] of rawProducts.entries()) {
    const result = normalizeProduct(rawProduct, rowIndex)
    normalized.push(result.product)
    issues.push(...result.issues)
  }

  return {
    products: normalized,
    issues,
  }
}
