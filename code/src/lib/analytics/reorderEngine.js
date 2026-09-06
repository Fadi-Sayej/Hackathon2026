/**
 * Reorder Recommendation Engine
 *
 * Self-contained module. Takes raw Product[] plus optional marketContext
 * and returns Recommendation[] without depending on inventoryEngine.
 *
 * Recommendation type comes from src/lib/types.js:
 *   type: "REORDER" | "REDUCE_STOCK" | "PROMOTION" | "SHELF_INCREASE" | "SHELF_DECREASE"
 *   urgency: "LOW" | "MEDIUM" | "HIGH"
 *   status: "PENDING" | "APPROVED" | "REJECTED" | "EDITED"
 */

const FAST_MOVER_THRESHOLD = 5
const SLOW_MOVER_SALES_30D = 5
const SLOW_MOVER_DAILY = 0.3
const OVERSTOCK_DAY_COVER = 30
const NEAR_EXPIRY_DAYS = 7

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

export function computeMetrics(product, marketContext = {}) {
  const avgDailySales7 = safeDivide(product.salesLast7Days, 7)
  const avgDailySales30 = safeDivide(product.salesLast30Days, 30)
  const demandMultiplier = marketContext.demandSignals?.[product.category] ?? 1
  const baseWeightedAvg = avgDailySales7 * 0.7 + avgDailySales30 * 0.3
  const weightedAvgDailySales = baseWeightedAvg * demandMultiplier
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
  const recommendedOrder = Math.max(0, rawRecommendedOrder)
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
    demandMultiplier,
    daysUntilStockout: Number.isFinite(daysUntilStockout) ? round(daysUntilStockout) : null,
    isFastMover,
    safetyStock: round(safetyStock),
    expectedDemandDuringLeadTime: round(expectedDemandDuringLeadTime),
    recommendedOrder,
    margin: round(margin),
    marginRate: round(marginRate),
    nearExpiry,
    slowMoving,
    overstocked,
  }
}

function buildRecommendationCandidates(product, metrics, marketContext) {
  const recommendations = []

  if (shouldReorder(metrics)) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: 'REORDER',
        recommendedOrderQuantity: metrics.recommendedOrder,
        urgency: classifyReorderUrgency(metrics, product),
        confidence: scoreReorderConfidence(product, metrics),
        reason: buildReorderReason(product, metrics, marketContext),
      }),
    )
  }

  if (metrics.overstocked) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: 'REDUCE_STOCK',
        urgency: metrics.nearExpiry ? 'HIGH' : 'MEDIUM',
        confidence: scoreOverstockConfidence(metrics),
        reason: buildOverstockReason(product, metrics),
      }),
    )
  }

  if (metrics.nearExpiry && product.currentStock > 0) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: 'PROMOTION',
        urgency: 'HIGH',
        confidence: 0.85,
        reason: buildExpiryReason(product, marketContext),
      }),
    )
  } else if (metrics.slowMoving && product.currentStock > 0 && !metrics.nearExpiry) {
    recommendations.push(
      makeRecommendation(product, metrics, marketContext, {
        type: 'PROMOTION',
        urgency: 'LOW',
        confidence: 0.6,
        reason: buildSlowMovingReason(product, metrics),
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
  return {
    productId: product.id,
    productName: product.name,
    category: product.category,
    type: extras.type,
    recommendedOrderQuantity: extras.recommendedOrderQuantity,
    recommendedShelfQuantity: extras.recommendedShelfQuantity,
    urgency: extras.urgency,
    confidence: extras.confidence,
    reason: extras.reason,
    status: 'PENDING',
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
      `Current stock of ${product.currentStock} covers about ${metrics.daysUntilStockout} days while the supplier lead time is ${product.leadTimeDays} days.`,
    )
  }
  if (metrics.demandMultiplier > 1) {
    const boost = Math.round((metrics.demandMultiplier - 1) * 100)
    parts.push(`Market signals add roughly ${boost}% expected demand for ${product.category}.`)
  }
  if (marketContext.weekend) parts.push('Weekend traffic is expected to be higher.')
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
  return parts.join(' ')
}

function buildExpiryReason(product, marketContext) {
  const reference = marketContext.currentDate ?? 'today'
  return `Expiry date ${product.expiryDate ?? 'unknown'} is within the next ${NEAR_EXPIRY_DAYS} days versus ${reference}. Recommend a promotion or discount to clear stock before write-off.`
}

function buildSlowMovingReason(product, metrics) {
  return `Only ${product.salesLast30Days} units moved in the last 30 days (≈ ${metrics.weightedAvgDailySales} per day). Consider a promotion before tying up more shelf space.`
}

function sortRecommendations(recommendations) {
  const urgencyWeight = { HIGH: 3, MEDIUM: 2, LOW: 1 }
  const typeWeight = { REORDER: 3, PROMOTION: 2, REDUCE_STOCK: 1 }
  return [...recommendations].sort((a, b) => {
    const urgencyDiff = (urgencyWeight[b.urgency] ?? 0) - (urgencyWeight[a.urgency] ?? 0)
    if (urgencyDiff !== 0) return urgencyDiff
    const typeDiff = (typeWeight[b.type] ?? 0) - (typeWeight[a.type] ?? 0)
    if (typeDiff !== 0) return typeDiff
    return (b.confidence ?? 0) - (a.confidence ?? 0)
  })
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
