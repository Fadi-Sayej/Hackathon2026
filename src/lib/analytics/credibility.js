/**
 * credibility.js — shared "is this ₪ figure defensible?" guards (Issue #39).
 *
 * The pilot commits to one definition of a credible money figure, and BOTH
 * ranking surfaces must honour it: the operational action list
 * (`actionPriority.js`, ₪ per sale) and the reorder / dashboard exposure sort
 * (`reorderEngine.js`, total ₪ at stake). Before #39 these lived only in
 * actionPriority, so `valueAtStake` could report a loss actionPriority would
 * have refused to state — two screens one nav click apart disagreeing about the
 * same product. This module is the single source of those thresholds so they
 * can never drift apart again.
 *
 * The rules come from the YomYom manager (05/08) and from the real export:
 *   - Prices are reliable; stock counts are not.
 *   - Cost recorded per CASE against a price per UNIT looks like a catastrophic
 *     loss but is a data-entry problem, e.g. בראוניז (4*4) sells ₪3.90 with a
 *     "cost" of ₪238.00 (a whole case). Telling a manager he loses ₪234 on every
 *     brownie would discredit every other number on the screen.
 */

// A shelf price of ₪0.01 against a ₪2.28 cost is a data-entry error, not a
// -22,700% margin, so anything below this is not a credible price at all.
export const MIN_CREDIBLE_PRICE = 0.5

// Shelf-vs-Wolt gaps beyond this are almost always a unit/pack mismatch.
export const MAX_CREDIBLE_GAP_PCT = 300

// Genuine below-cost selling looks like ₪24.90 against a ₪30.00 cost — close,
// not 60x. Beyond this ratio it is treated as a cost-price data problem.
export const MAX_CREDIBLE_COST_RATIO = 2

export function toNumber(value) {
  const parsed = typeof value === 'string' ? Number(value) : value
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * Is this a believable below-cost sale, or a cost-price data problem?
 *
 * @returns {number|null} loss per unit in shekels, or null if not credible.
 */
export function credibleLoss(sellingPrice, costPrice) {
  const selling = toNumber(sellingPrice)
  const cost = toNumber(costPrice)
  if (selling == null || cost == null) return null
  if (selling < MIN_CREDIBLE_PRICE || cost <= 0) return null
  if (cost / selling > MAX_CREDIBLE_COST_RATIO) return null
  const loss = cost - selling
  return loss > 0 ? loss : null
}

/**
 * Is the gap between two prices for the same product believable, or a unit/pack
 * mismatch? Order-independent.
 *
 * @returns {number|null} absolute gap in shekels, or null if not credible.
 */
export function credibleGap(priceA, priceB) {
  const a = toNumber(priceA)
  const b = toNumber(priceB)
  if (a == null || b == null) return null
  if (a < MIN_CREDIBLE_PRICE || b < MIN_CREDIBLE_PRICE) return null
  const gap = Math.abs(a - b)
  const gapPct = (gap / Math.min(a, b)) * 100
  if (gapPct > MAX_CREDIBLE_GAP_PCT) return null
  return gap
}
