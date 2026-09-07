/**
 * Reorder Recommendation Engine
 *
 * Self-contained module. Takes raw Product[] plus optional marketContext
 * and returns Recommendation[] without depending on inventoryEngine.
 *
 * Recommendation type comes from recommendationTypes.js.
 *   urgency: "LOW" | "MEDIUM" | "HIGH"
 *   status: "PENDING" | "APPROVED" | "REJECTED" | "EDITED"
 */

import {
  RECOMMENDATION_TYPES,
  RECOMMENDATION_TYPE_METADATA,
} from './recommendationTypes.js'
import { credibleLoss } from './actionPriority.js'
import { isAssumedLeadTime } from '../receiving/leadTimeResolver.js'
import {
  buildReorderFacts,
  resolveCompetitorLift,
  resolveDailyRate,
  resolveShelfLifeDays,
} from './reorderFacts.js'

const FAST_MOVER_THRESHOLD = 5
const SLOW_MOVER_SALES_30D = 5
const SLOW_MOVER_DAILY = 0.3
const OVERSTOCK_DAY_COVER = 30
const NEAR_EXPIRY_DAYS = 7
const THIN_MARGIN_THRESHOLD = 0.2
const VELOCITY_CONFIDENCE_LEVELS = new Set(['none', 'low', 'medium', 'high'])

export function generateReorderRecommendations(products, marketContext = {}) {
  if (!Array.isArray(products)) return []

  const recommendations = []

  for (const product of products) {
    const metrics = computeMetrics(product, marketContext)
    const candidates = buildRecommendationCandidates(product, metrics, marketContext)
    for (const recommendation of candidates) {
      recommendations.push(recommendation)
    }
  }

  return sortRecommendations(recommendations)
}

/**
 * Net ₪-value-at-stake across a set of recommendations (Issue #30).
 *
 * DEFINITION — *deduplicated product exposure*, not a gross action-item sum.
 *
 * Each recommendation carries its own per-action `valueAtStake`, and a single
 * product can trip several signals at once — e.g. BELOW_COST *and* PRICE_GAP on
 * the same stock. Those two often prescribe contradictory fixes (raise the price
 * to cost vs. drop it to the competitor), so summing their values would count one
 * product's capital more than once and inflate the headline the pilot is graded
 * on (PLAN.md §5).
 *
 * The roll-up therefore counts each product ONCE, by its single greatest
 * at-stake value — the worst-case capital exposed on that product's stock — and
 * sums those per-product maxima. Per-recommendation `valueAtStake` is unchanged
 * and still drives action-item ranking; this is only the aggregate definition.
 *
 * Recommendations without a `productId` are treated as distinct (each counts on
 * its own). Values are already clamped to >= 0 by calculateValueAtStake.
 */
export function aggregateNetValueAtStake(recommendations) {
  if (!Array.isArray(recommendations)) return 0
  const worstPerProduct = new Map()
  for (const recommendation of recommendations) {
    const key = recommendation.productId ?? recommendation
    const value = recommendation.valueAtStake ?? 0
    if (value > (worstPerProduct.get(key) ?? 0)) worstPerProduct.set(key, value)
  }
  let total = 0
  for (const value of worstPerProduct.values()) total += value
  return round(total)
}

/**
 * NOTE ON WHO DECIDES
 * `marketContext.demandSignals` is computed by the pipeline
 * (src/context/demand_signals.py) and read from public/data/market-context.json.
 * This module applies it; it does not choose it. Do not reintroduce a signal table
 * here — the previous one was keyed in English against a Hebrew catalog and
 * silently multiplied everything by 1.
 */
export function computeMetrics(product, marketContext = {}) {
  const avgDailySales7 = safeDivide(product.salesLast7Days, 7)
  const avgDailySales30 = safeDivide(product.salesLast30Days, 30)
  const demandMultiplier = marketContext.demandSignals?.[product.category] ?? 1
  const observedWeightedAvg = avgDailySales7 * 0.7 + avgDailySales30 * 0.3
  // Prefer the availability-corrected rate: raw sales measure supply, not demand,
  // once the shelf has emptied. The basis travels on the metrics so the
  // explanation can state which of the two it sized the order from.
  const { dailyRate: baseRate, rateBasis, rateConfidence, censoredDays } =
    resolveDailyRate(product, observedWeightedAvg)
  const baseWeightedAvg = baseRate
  // Competitor stockouts adjust the RATE; they never decide whether to order.
  const competitorLift = resolveCompetitorLift(product, marketContext)
  const weightedAvgDailySales = baseWeightedAvg * demandMultiplier * competitorLift
  const daysUntilStockout =
    weightedAvgDailySales > 0
      ? product.currentStock / weightedAvgDailySales
      : Number.POSITIVE_INFINITY
  const isFastMover = weightedAvgDailySales >= FAST_MOVER_THRESHOLD
  const safetyStock = weightedAvgDailySales * (isFastMover ? 3 : 2)
  const expectedDemandDuringLeadTime = weightedAvgDailySales * product.leadTimeDays
  const rawRecommendedOrder = Math.ceil(
    expectedDemandDuringLeadTime + safetyStock - product.currentStock,
  )
  const uncappedOrder = Math.max(0, rawRecommendedOrder)

  // Ordering more than can be sold within the product's own shelf life is not a
  // stockout fix, it is waste with extra steps: the engine used to put 51 chocolate
  // croissants (about six days' worth) on the list. Nothing in the POS export
  // records shelf life, so this caps against crude per-category defaults the owner
  // can correct — see configs/shelf_life.yaml. An unknown category is left uncapped,
  // because suppressing a real order on a guess is the worse error.
  const shelfLifeDays = resolveShelfLifeDays(product, marketContext)
  const sellableWithinShelfLife =
    shelfLifeDays === null ? null : Math.floor(weightedAvgDailySales * shelfLifeDays)
  const shelfLifeCap =
    sellableWithinShelfLife === null
      ? null
      : Math.max(0, sellableWithinShelfLife - Math.max(0, product.currentStock))
  const recommendedOrder =
    shelfLifeCap === null ? uncappedOrder : Math.min(uncappedOrder, shelfLifeCap)
  const margin = product.price - product.cost
  const marginRate = product.price > 0 ? margin / product.price : 0
  const nearExpiry = isNearExpiry(product.expiryDate, marketContext.currentDate)
  const slowMoving =
    product.salesLast30Days < SLOW_MOVER_SALES_30D || weightedAvgDailySales < SLOW_MOVER_DAILY
  const overstocked = !slowMoving && product.currentStock > weightedAvgDailySales * OVERSTOCK_DAY_COVER

  return {
    avgDailySales7: round(avgDailySales7),
    avgDailySales30: round(avgDailySales30),
    weightedAvgDailySales: round(weightedAvgDailySales),
    // The exact rate the order quantity was sized from, and what it rests on.
    dailyRate: round(weightedAvgDailySales),
    rateBasis,
    rateConfidence,
    censoredDays,
    demandMultiplier,
    competitorLift,
    daysUntilStockout: Number.isFinite(daysUntilStockout) ? round(daysUntilStockout) : null,
    isFastMover,
    safetyStock: round(safetyStock),
    expectedDemandDuringLeadTime: round(expectedDemandDuringLeadTime),
    recommendedOrder,
    uncappedOrder,
    shelfLifeDays,
    // True only when the cap actually reduced the order, so the explanation can
    // stay silent about shelf life when it made no difference.
    shelfLifeCapped: shelfLifeCap !== null && recommendedOrder < uncappedOrder,
    margin: round(margin),
    marginRate: round(marginRate),
    nearExpiry,
    slowMoving,
    overstocked,
  }
}

function buildRecommendationCandidates(product, metrics, marketContext) {
  const recommendations = []
  const velocityConfidence = readVelocityConfidence(product)
  const hasVelocityConfidence = velocityConfidence !== 'none'

  // Some products sell fast and are never delivered: car washes, espresso pulled
  // to order, staff consumption. 683 of the 1,778 products in YomYom's sales
  // reports had sales but ZERO stock receipts across seven months. They always
  // read as "0 in stock, selling 20/day, reorder now", which put car washes at
  // the top of the reorder list. Velocity is still real and useful for margin
  // work — only replenishment is meaningless. isStocked === false says so
  // explicitly; null means we have no sales report and therefore cannot tell.
  const isReplenishable = product.isStocked !== false

  if (hasVelocityConfidence && isReplenishable && shouldReorder(metrics)) {
    // The order quantity is (daily sales x lead time) + safety - CURRENT STOCK.
    // When D-7 has proven that stock figure cannot be right, the arithmetic is
    // sound but its input is not, so we keep the signal ("this is selling and
    // may be low") and drop the false precision ("order exactly 108"). 59% of
    // reorder suggestions were in exactly this position. Telling a manager to
    // order a specific number from a count we disproved on the next screen is
    // the fastest way to lose him.
    const stockIsTrustworthy = product.stockReconciles !== false
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: RECOMMENDATION_TYPES.REORDER,
        recommendedOrderQuantity: stockIsTrustworthy ? metrics.recommendedOrder : null,
        urgency: classifyReorderUrgency(metrics, product),
        confidence: stockIsTrustworthy
          ? scoreReorderConfidence(product, metrics)
          : Math.min(scoreReorderConfidence(product, metrics), 0.4),
        reason: stockIsTrustworthy
          ? buildReorderReason(product, metrics, marketContext)
          : `Selling ${metrics.weightedAvgDailySales}/day, but the stock figure for this `
            + `product does not reconcile with deliveries and sales. Count it, then decide `
            + `how much to order.`,
      }),
    )
  }

  if (hasVelocityConfidence && isReplenishable && metrics.overstocked) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: RECOMMENDATION_TYPES.REDUCE_STOCK,
        urgency: metrics.nearExpiry ? 'HIGH' : 'MEDIUM',
        confidence: scoreOverstockConfidence(metrics),
        reason: buildOverstockReason(product, metrics),
      }),
    )
  }

  if (hasVelocityConfidence && metrics.nearExpiry && product.currentStock > 0) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: RECOMMENDATION_TYPES.PROMOTION,
        urgency: 'HIGH',
        confidence: 0.85,
        reason: buildExpiryReason(product, marketContext),
      }),
    )
  } else if (
    hasVelocityConfidence &&
    metrics.slowMoving &&
    product.currentStock > 0 &&
    !metrics.nearExpiry
  ) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: RECOMMENDATION_TYPES.PROMOTION,
        urgency: 'LOW',
        confidence: 0.6,
        reason: buildSlowMovingReason(product, metrics),
      }),
    )
  }

  // Uses the SHARED credibility guard, not a bare price < cost. A cost recorded
  // per case against a price recorded per unit is indistinguishable from a
  // catastrophic loss: this catalog has a paper bag selling at ₪0.47 with a
  // "cost" of ₪200 (425x), and a deliberately free ₪0.01 coffee. A bare
  // comparison flagged 63 products, 26 of them artifacts, while the Prices screen
  // — which does guard — showed 37. Two screens contradicting each other about
  // the same shop on the same day costs more trust than either number is worth.
  // See UI_DATA_CONTRACT §9.5.
  if (credibleLoss(product.price, product.cost) !== null) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: RECOMMENDATION_TYPES.BELOW_COST,
        confidence: 0.95,
        reason: buildBelowCostReason(product, metrics),
      }),
    )
  } else if (calculateMarginRate(product) < THIN_MARGIN_THRESHOLD) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: RECOMMENDATION_TYPES.THIN_MARGIN,
        confidence: 0.8,
        reason: buildThinMarginReason(product, metrics),
      }),
    )
  }

  const competitorPrice = readCompetitorPrice(product, marketContext)
  if (competitorPrice !== null && product.price > competitorPrice) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: RECOMMENDATION_TYPES.PRICE_GAP,
        confidence: 0.9,
        competitorPrice,
        reason: buildPriceGapReason(product, competitorPrice),
      }),
    )
  }

  if (product.currentStock < 0) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: RECOMMENDATION_TYPES.NEGATIVE_STOCK,
        confidence: 0.95,
        reason: buildNegativeStockReason(product),
      }),
    )
  }

  return recommendations
}

function shouldReorder(metrics) {
  if (metrics.recommendedOrder <= 0) return false
  if (metrics.slowMoving) return false
  if (metrics.weightedAvgDailySales <= 0) return false
  return true
}

function classifyReorderUrgency(metrics, product) {
  if (metrics.daysUntilStockout === null) return 'LOW'
  if (metrics.daysUntilStockout <= product.leadTimeDays) return 'HIGH'
  if (metrics.daysUntilStockout <= product.leadTimeDays + 2) return 'MEDIUM'
  return 'LOW'
}

function scoreReorderConfidence(product, metrics) {
  let confidence = 0.5
  if (product.salesLast30Days >= 30) confidence += 0.2
  if (product.salesLast7Days >= 7) confidence += 0.15
  if (metrics.isFastMover) confidence += 0.1
  if (metrics.demandMultiplier > 1) confidence += 0.05
  return clamp(round(confidence), 0, 0.98)
}

function scoreOverstockConfidence(metrics) {
  let confidence = 0.55
  if (metrics.daysUntilStockout && metrics.daysUntilStockout > 45) confidence += 0.15
  if (metrics.nearExpiry) confidence += 0.2
  if (metrics.marginRate < 0.15) confidence += 0.05
  return clamp(round(confidence), 0, 0.95)
}

function makeRecommendation(product, metrics, marketContext, extras) {
  const metadata = RECOMMENDATION_TYPE_METADATA[extras.type]
  const velocityConfidence = readVelocityConfidence(product)
  return {
    productId: product.id,
    productName: product.name,
    category: product.category,
    type: extras.type,
    recommendedOrderQuantity: extras.recommendedOrderQuantity,
    recommendedShelfQuantity: extras.recommendedShelfQuantity,
    urgency: extras.urgency ?? metadata.defaultUrgency,
    confidence: extras.confidence,
    velocityConfidence,
    valueAtStake: calculateValueAtStake(product, metrics, extras),
    reason: extras.reason,
    status: 'PENDING',
    // Which competitor price this was built on, and how comparable that store's
    // format is to ours. Carried so an auditor can check that no recommendation
    // was ever sourced from a store we are not supposed to compare against.
    competitorPrice: extras.competitorPrice ?? null,
    competitorStoreType: product.competitor?.priceStoreType ?? null,
    competitorFormatAffinity: product.competitor?.priceAffinity ?? null,
    // The checkable facts behind this number, captured from the values that
    // produced it. src/lib/i18n/explainReorder.js renders these per language;
    // nothing downstream recomputes any of them.
    facts: extras.type === 'REORDER' ? buildReorderFacts(product, metrics, marketContext) : null,
    metrics: {
      currentStock: product.currentStock,
      weightedAvgDailySales: metrics.weightedAvgDailySales,
      daysUntilStockout: metrics.daysUntilStockout,
      safetyStock: metrics.safetyStock,
      leadTimeDays: product.leadTimeDays,
      margin: metrics.margin,
      marginRate: metrics.marginRate,
      demandMultiplier: metrics.demandMultiplier,
    },
    context: {
      weather: marketContext.weather ?? null,
      weekend: marketContext.weekend ?? null,
      holiday: marketContext.holiday ?? null,
      localEvent: marketContext.localEvent ?? null,
      season: marketContext.season ?? null,
    },
  }
}

function buildReorderReason(product, metrics, marketContext) {
  const parts = []
  parts.push(
    `Average daily sales ${metrics.weightedAvgDailySales} units (last 7 days weighted).`,
  )
  if (metrics.daysUntilStockout !== null) {
    parts.push(
      isAssumedLeadTime(product)
        ? `Current stock of ${product.currentStock} covers about ${metrics.daysUntilStockout} days against an assumed ${product.leadTimeDays}-day supplier lead time — not enough deliveries have been recorded to measure the real one, so that figure is the system default and not a measurement.`
        : `Current stock of ${product.currentStock} covers about ${metrics.daysUntilStockout} days while the supplier lead time is ${product.leadTimeDays} days.`,
    )
  }
  if (metrics.demandMultiplier > 1) {
    const boost = Math.round((metrics.demandMultiplier - 1) * 100)
    parts.push(`Market signals add roughly ${boost}% expected demand for ${product.category}.`)
  }
  if (marketContext.weekend) parts.push('Weekend traffic is expected to be higher.')
  parts.push(`Product: ${buildProductReference(product)}.`)
  return parts.join(' ')
}

function buildOverstockReason(product, metrics) {
  const parts = []
  if (metrics.daysUntilStockout !== null) {
    parts.push(
      `Stock on hand covers about ${metrics.daysUntilStockout} days at the current pace.`,
    )
  } else {
    parts.push('Sales velocity is effectively zero against current stock.')
  }
  parts.push(`Holding ${product.currentStock} units is well above the ${OVERSTOCK_DAY_COVER}-day cover threshold.`)
  if (metrics.nearExpiry) parts.push('Expiry is approaching, so capital is at risk.')
  parts.push(`Product: ${buildProductReference(product)}.`)
  return parts.join(' ')
}

function buildExpiryReason(product, marketContext) {
  const reference = marketContext.currentDate ?? 'today'
  return `Expiry date ${product.expiryDate ?? 'unknown'} is within the next ${NEAR_EXPIRY_DAYS} days versus ${reference}. Recommend a promotion or discount to clear ${buildProductReference(product)} before write-off.`
}

function buildSlowMovingReason(product, metrics) {
  return `Only ${product.salesLast30Days} units of ${buildProductReference(product)} moved in the last 30 days (≈ ${metrics.weightedAvgDailySales} per day). Consider a promotion before tying up more shelf space.`
}

function buildBelowCostReason(product, metrics) {
  const lossPerUnit = Math.abs(metrics.margin)
  return `${buildProductReference(product)} sells at ${formatCurrency(product.price)}, below its ${formatCurrency(product.cost)} unit cost by ${formatCurrency(lossPerUnit)}. ${formatStock(product.currentStock)} is recorded on hand.`
}

function buildPriceGapReason(product, competitorPrice) {
  const gap = product.price - competitorPrice
  return `${buildProductReference(product)} sells at ${formatCurrency(product.price)}, while the cheapest nearby competitor sells it at ${formatCurrency(competitorPrice)}. The gap is ${formatCurrency(gap)} across ${formatStock(product.currentStock)} on hand.`
}

function buildNegativeStockReason(product) {
  return `${buildProductReference(product)} has ${formatStock(product.currentStock)} in the POS. Count the item and correct the stock record before ordering; the discrepancy is worth ${formatCurrency(Math.abs(product.currentStock) * product.cost)} at cost.`
}

function buildThinMarginReason(product, metrics) {
  const marginPercent = round(metrics.marginRate * 100)
  return `${buildProductReference(product)} sells at ${formatCurrency(product.price)} with a ${formatCurrency(product.cost)} unit cost, leaving a ${marginPercent}% margin across ${formatStock(product.currentStock)} on hand.`
}

function sortRecommendations(recommendations) {
  const urgencyWeight = { HIGH: 3, MEDIUM: 2, LOW: 1 }
  const typeWeight = {
    [RECOMMENDATION_TYPES.NEGATIVE_STOCK]: 7,
    [RECOMMENDATION_TYPES.BELOW_COST]: 6,
    [RECOMMENDATION_TYPES.PRICE_GAP]: 5,
    [RECOMMENDATION_TYPES.THIN_MARGIN]: 4,
    [RECOMMENDATION_TYPES.REORDER]: 3,
    [RECOMMENDATION_TYPES.PROMOTION]: 2,
    [RECOMMENDATION_TYPES.REDUCE_STOCK]: 1,
  }
  return [...recommendations].sort((a, b) => {
    const valueDiff = (b.valueAtStake ?? 0) - (a.valueAtStake ?? 0)
    if (valueDiff !== 0) return valueDiff
    const urgencyDiff = (urgencyWeight[b.urgency] ?? 0) - (urgencyWeight[a.urgency] ?? 0)
    if (urgencyDiff !== 0) return urgencyDiff
    const typeDiff = (typeWeight[b.type] ?? 0) - (typeWeight[a.type] ?? 0)
    if (typeDiff !== 0) return typeDiff
    return (b.confidence ?? 0) - (a.confidence ?? 0)
  })
}

function readVelocityConfidence(product) {
  const confidence = product.velocityConfidence ?? product.analytics?.velocityConfidence ?? 'none'
  return VELOCITY_CONFIDENCE_LEVELS.has(confidence) ? confidence : 'none'
}

function calculateMarginRate(product) {
  return product.price > 0 ? (product.price - product.cost) / product.price : 0
}

function readCompetitorPrice(product, marketContext) {
  const productPrice = product.competitor?.cheapestCompetitorPrice
  if (Number.isFinite(productPrice)) return productPrice

  const source = marketContext.competitorPriceAdvantage
  const entry = source instanceof Map ? source.get(product.id) : source?.[product.id]
  if (Number.isFinite(entry)) return entry
  if (!entry || typeof entry !== 'object') return null

  const contextualPrice =
    entry.competitorPrice ?? entry.cheapestCompetitorPrice ?? entry.price ?? null
  return Number.isFinite(contextualPrice) ? contextualPrice : null
}

function calculateValueAtStake(product, metrics, extras) {
  const stock = Math.max(0, product.currentStock)
  let value = 0

  switch (extras.type) {
    case RECOMMENDATION_TYPES.REORDER:
      value = (extras.recommendedOrderQuantity ?? 0) * product.cost
      break
    case RECOMMENDATION_TYPES.REDUCE_STOCK:
      value = Math.max(0, stock - metrics.weightedAvgDailySales * OVERSTOCK_DAY_COVER) * product.cost
      break
    case RECOMMENDATION_TYPES.PROMOTION:
      value = stock * product.cost
      break
    case RECOMMENDATION_TYPES.BELOW_COST:
      value = Math.max(0, product.cost - product.price) * stock
      break
    case RECOMMENDATION_TYPES.PRICE_GAP:
      value = Math.max(0, product.price - extras.competitorPrice) * stock
      break
    case RECOMMENDATION_TYPES.NEGATIVE_STOCK:
      value = Math.abs(product.currentStock) * product.cost
      break
    case RECOMMENDATION_TYPES.THIN_MARGIN:
      value = Math.max(0, product.price * THIN_MARGIN_THRESHOLD - metrics.margin) * stock
      break
  }

  return round(Number.isFinite(value) ? value : 0)
}

function buildProductReference(product) {
  return `“${product.name}” (${product.id})`
}

function formatCurrency(value) {
  return `₪${Number(value).toFixed(2)}`
}

function formatStock(value) {
  return `${value} ${Math.abs(value) === 1 ? 'unit' : 'units'}`
}

function isNearExpiry(expiryDate, currentDate) {
  if (!expiryDate) return false
  const reference = currentDate ? new Date(`${currentDate}T00:00:00Z`) : new Date()
  const expiry = new Date(`${expiryDate}T00:00:00Z`)
  if (Number.isNaN(expiry.getTime()) || Number.isNaN(reference.getTime())) return false
  const daysUntilExpiry = (expiry.getTime() - reference.getTime()) / 86_400_000
  return daysUntilExpiry >= 0 && daysUntilExpiry <= NEAR_EXPIRY_DAYS
}

function safeDivide(value, divisor) {
  return divisor === 0 ? 0 : value / divisor
}

function round(value) {
  return Math.round(value * 100) / 100
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}
