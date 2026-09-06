import { analyzeProducts } from './inventoryEngine.js'

const shelfLevels = ['EYE_LEVEL', 'MIDDLE', 'TOP', 'BOTTOM']

const shelfLabels = {
  EYE_LEVEL: 'Eye level',
  MIDDLE: 'Middle shelf',
  TOP: 'Top shelf',
  BOTTOM: 'Bottom shelf',
}

const heavyOrLowPriorityCategories = new Set(['Water', 'Car Accessories'])
const impulseCategories = new Set(['Energy Drinks', 'Cold Drinks', 'Snacks', 'Chocolate', 'Gum & Candy'])

export function generatePlanogram(products, marketContext = {}) {
  if (!Array.isArray(products) || products.length === 0) {
    return []
  }

  const analyzedProducts = products[0]?.analytics ? products : analyzeProducts(products, marketContext)
  const stats = buildStats(analyzedProducts)

  // Optional plugin hook: marketContext.competitorPriceAdvantage may be a
  // Set, array, or plain object of product ids that earn a shelf-priority
  // bump because we are the local price leader on those items. When the
  // field is missing the engine behaves exactly as before.
  const priceAdvantageSet = toIdSet(marketContext.competitorPriceAdvantage)

  return analyzedProducts
    .map((product) => {
      const scoring = scoreProduct(product, stats, {
        competitorPriceAdvantage: priceAdvantageSet.has(product.id),
      })
      const shelfLevel = chooseShelfLevel(product, scoring.score)
      const facings = calculateFacings(product, shelfLevel)

      return {
        productId: product.id,
        productName: product.name,
        category: product.category,
        shelfLevel,
        shelfLabel: shelfLabels[shelfLevel],
        facings,
        score: scoring.score,
        scoreBreakdown: scoring.breakdown,
        reason: buildPlanogramReason(product, shelfLevel, facings, scoring.breakdown),
      }
    })
    .sort((left, right) => {
      const shelfDiff = shelfLevels.indexOf(left.shelfLevel) - shelfLevels.indexOf(right.shelfLevel)
      if (shelfDiff !== 0) return shelfDiff
      return right.score - left.score
    })
}

export function groupPlanogramByShelf(planogramItems) {
  return shelfLevels.map((shelfLevel) => ({
    shelfLevel,
    shelfLabel: shelfLabels[shelfLevel],
    items: planogramItems.filter((item) => item.shelfLevel === shelfLevel),
  }))
}

export function summarizePlanogram(planogramItems) {
  return {
    totalItems: planogramItems.length,
    eyeLevelItems: planogramItems.filter((item) => item.shelfLevel === 'EYE_LEVEL').length,
    totalFacings: planogramItems.reduce((sum, item) => sum + item.facings, 0),
    topScore: planogramItems[0]?.score ?? 0,
  }
}

function buildStats(products) {
  return {
    maxDailySales: Math.max(...products.map((product) => product.analytics.weightedAvgDailySales), 1),
    maxMargin: Math.max(...products.map((product) => product.analytics.margin), 1),
  }
}

function scoreProduct(product, stats, options = {}) {
  const salesScore = normalize(product.analytics.weightedAvgDailySales, stats.maxDailySales)
  const marginScore = normalize(product.analytics.margin, stats.maxMargin)
  const expiryRiskScore = product.analytics.statuses.includes('Near expiry') ? 1 : 0
  const stockRiskScore = product.analytics.daysUntilStockout !== null && product.analytics.daysUntilStockout < 3 ? 1 : 0
  const impulseScore = impulseCategories.has(product.category) ? 0.2 : 0
  const penaltyScore = product.analytics.statuses.includes('Slow moving') ? 0.18 : 0
  // Hyper-local pricing edge: if we're the cheapest within 1km, give this
  // product a shelf-priority bump so customers notice the value first.
  const competitorPriceBonus = options.competitorPriceAdvantage ? 0.15 : 0

  const score = clamp(
    salesScore * 0.45 +
      marginScore * 0.25 +
      stockRiskScore * 0.2 +
      expiryRiskScore * 0.1 +
      impulseScore +
      competitorPriceBonus -
      penaltyScore,
    0,
    1,
  )

  return {
    score: round(score),
    breakdown: {
      salesScore: round(salesScore),
      marginScore: round(marginScore),
      stockRiskScore,
      expiryRiskScore,
      impulseScore,
      penaltyScore,
      competitorPriceBonus,
    },
  }
}

function toIdSet(input) {
  if (!input) return new Set()
  if (input instanceof Set) return input
  if (Array.isArray(input)) return new Set(input)
  if (typeof input === 'object') return new Set(Object.keys(input))
  return new Set()
}

function chooseShelfLevel(product, score) {
  if (heavyOrLowPriorityCategories.has(product.category) && score < 0.82) return 'BOTTOM'
  if (product.analytics.statuses.includes('Slow moving')) return 'BOTTOM'
  if (score >= 0.53) return 'EYE_LEVEL'
  if (score >= 0.42) return 'MIDDLE'
  if (score >= 0.25) return 'TOP'
  return 'BOTTOM'
}

function calculateFacings(product, shelfLevel) {
  const dailySales = product.analytics.weightedAvgDailySales
  const isFastMover = dailySales >= 5
  const isSlowMover = product.analytics.statuses.includes('Slow moving')
  const levelBoost = shelfLevel === 'EYE_LEVEL' ? 1.25 : shelfLevel === 'MIDDLE' ? 1 : 0.75
  const rawFacings = Math.ceil(dailySales * 1.5 * levelBoost)
  const minimum = isFastMover ? 6 : 2
  const maximum = isSlowMover ? Math.min(3, product.shelfCapacity) : product.shelfCapacity

  return clamp(Math.max(minimum, rawFacings), 1, maximum)
}

function buildPlanogramReason(product, shelfLevel, facings, breakdown) {
  const reasons = []

  if (shelfLevel === 'EYE_LEVEL') {
    reasons.push('High visibility because sales velocity and margin justify premium shelf space.')
  } else if (shelfLevel === 'BOTTOM') {
    reasons.push('Lower shelf placement protects eye-level space for faster or more profitable products.')
  } else if (shelfLevel === 'TOP') {
    reasons.push('Top shelf placement is enough for moderate demand without crowding priority items.')
  } else {
    reasons.push('Middle shelf placement balances demand, margin, and available facings.')
  }

  if (product.analytics.statuses.includes('Near expiry')) {
    reasons.push('Near-expiry status keeps it visible enough to sell through.')
  }

  if (breakdown.stockRiskScore > 0) {
    reasons.push('Stockout risk raises the display priority until replenishment arrives.')
  }

  reasons.push(`Recommend ${facings} facings based on weighted daily sales of ${product.analytics.weightedAvgDailySales}.`)
  return reasons.join(' ')
}

function normalize(value, max) {
  if (max <= 0) return 0
  return clamp(value / max, 0, 1)
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function round(value) {
  return Math.round(value * 100) / 100
}
