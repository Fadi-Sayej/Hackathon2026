/**
 * reorderFacts.js — the checkable facts behind one reorder quantity.
 *
 * WHY FACTS AND NOT SENTENCES
 *   The owner reads Hebrew and Arabic. A sentence built here could only ever be
 *   built in one language, so the decision layer emits structured values and
 *   src/lib/i18n renders them per language. An English sentence generated next to
 *   the arithmetic would strand the owner in his own store.
 *
 * WHY THE FACTS TRAVEL WITH THE DECISION
 *   Every figure here is the value that actually produced the order quantity,
 *   captured at the moment it was used. Nothing downstream may recompute one for
 *   display: if it did, the sentence and the order could drift apart and the screen
 *   would contradict the number the manager is about to act on.
 *
 * WHAT THE OWNER CAN CHECK
 *   stock on hand → the shelf. sales rate → his POS. lead time → how often the van
 *   comes. Every field below is one of those, or is explicitly labelled as derived
 *   or assumed. A figure he cannot check is worse than no figure.
 */

export const RATE_BASIS_CORRECTED = 'corrected'
export const RATE_BASIS_OBSERVED = 'observed'

/**
 * Which demand rate to size the order from, and what it rests on.
 *
 * Raw sales measure supply, not demand, once a product has run out — so the
 * availability-corrected rate is preferred wherever the pipeline produced one.
 * The basis travels with the number because the two deserve different wording:
 * one is what the POS recorded, the other is what it would have sold given stock.
 */
export function resolveDailyRate(product, fallbackRate) {
  const corrected = product?.demandPerDayCorrected
  if (typeof corrected === 'number' && Number.isFinite(corrected) && corrected > 0) {
    return {
      dailyRate: corrected,
      rateBasis: RATE_BASIS_CORRECTED,
      rateConfidence: product.demandConfidence ?? 'none',
      censoredDays: product.censoredDays ?? null,
    }
  }
  return {
    dailyRate: fallbackRate,
    rateBasis: RATE_BASIS_OBSERVED,
    rateConfidence: product?.velocityConfidence ?? 'none',
    censoredDays: null,
  }
}

/**
 * Shelf life for this product's category, in days, or null for no cap.
 *
 * Read from the pipeline's published table (public/data/market-context.json), so
 * the browser caps against exactly the numbers configs/shelf_life.yaml holds. An
 * unlisted category falls through to the configured default, which is itself null
 * by design: capping an unknown category on a guess would suppress real orders.
 */
export function resolveShelfLifeDays(product, marketContext = {}) {
  const table = marketContext.shelfLife
  if (!table) return null
  const categories = table.categories ?? {}
  const value = Object.prototype.hasOwnProperty.call(categories, product?.category)
    ? categories[product.category]
    : table.defaultDays
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : null
}

/**
 * Build the fact record for one reorder decision.
 *
 * `metrics` must be the object that produced `metrics.recommendedOrder` — this
 * function reads values, it never derives new ones.
 */
export function buildReorderFacts(product, metrics, marketContext = {}) {
  const unitCost = Number.isFinite(product?.cost) && product.cost > 0 ? product.cost : null

  return {
    kind: 'REORDER',
    productName: product?.name ?? null,
    productId: product?.id ?? null,

    // 1 — why this quantity
    currentStock: product?.currentStock ?? null,
    dailyRate: metrics.dailyRate,
    rateBasis: metrics.rateBasis,
    rateConfidence: metrics.rateConfidence,
    censoredDays: metrics.censoredDays ?? null,
    leadTimeDays: product?.leadTimeDays ?? null,
    // 'default' means no supplier has reached three recorded deliveries, so the
    // number is the system's assumption and must be said to be one.
    leadTimeAssumed: product?.leadTimeSource !== 'measured',
    expectedDemandDuringLeadTime: metrics.expectedDemandDuringLeadTime,
    safetyStock: metrics.safetyStock,
    orderQty: metrics.recommendedOrder,
    // What the order would have been without the shelf-life cap, and the cap that
    // reduced it. Both carried so the explanation can show the owner the working.
    uncappedOrderQty: metrics.uncappedOrder ?? metrics.recommendedOrder,
    shelfLifeDays: metrics.shelfLifeDays ?? null,
    shelfLifeCapped: Boolean(metrics.shelfLifeCapped),
    // Shelf life is a category default, never a per-product measurement.
    shelfLifeSource: metrics.shelfLifeDays == null ? null : 'config_default',
    // Units per case is not recorded anywhere in the POS export, so the quantity
    // is in single units and the explanation says so rather than inventing a case.
    caseSize: null,

    // 2 — why now
    coverDays: metrics.daysUntilStockout,
    drivers: Array.isArray(marketContext.activeReasons) ? marketContext.activeReasons : [],
    demandMultiplier: metrics.demandMultiplier ?? 1,

    // 3 — what we are unsure about
    // false = the stock figure fails its own arithmetic, so anything derived from
    // it (cover, order quantity) is not defensible and must not be stated flatly.
    stockReconciles: product?.stockReconciles ?? null,
    availabilityState: product?.availabilityState ?? null,

    // 4 — what it costs to ignore. Omitted entirely without a cost price rather
    // than shown as zero, which would read as "nothing at stake".
    unitCost,
    costToIgnore: unitCost === null ? null : round2(metrics.expectedDemandDuringLeadTime * unitCost),
  }
}

function round2(value) {
  return Number.isFinite(value) ? Math.round(value * 100) / 100 : null
}
