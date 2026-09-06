import { affinityRules } from './affinityRules.js'

/**
 * Cross-Merchandising Intelligence Engine.
 *
 * Combines a curated affinity knowledge base with the live product catalog
 * and current planogram to generate "place these together" suggestions
 * designed to lift Average Basket Value (ABV).
 *
 * @typedef {Object} AffinitySuggestion
 * @property {string} id
 * @property {{ id, name, category, shelfLevel }} anchor
 * @property {{ id, name, category, shelfLevel }} partner
 * @property {number} strength
 * @property {string} reason
 * @property {string} placement
 * @property {number} liftEstimate
 * @property {number} combinedDailySales
 * @property {boolean} isCoLocated
 * @property {'HIGH'|'MEDIUM'|'LOW'} priority
 */

export function generateCrossMerchandisingSuggestions(
  products = [],
  planogramItems = [],
  rules = affinityRules,
) {
  const byCategory = groupByCategory(products)
  const placementByProductId = new Map(
    planogramItems.map((item) => [item.productId, item]),
  )

  const suggestions = []

  for (const rule of rules) {
    const [anchorCategory, partnerCategory] = rule.pair
    const anchorPool = byCategory.get(anchorCategory) ?? []
    const partnerPool = byCategory.get(partnerCategory) ?? []
    if (anchorPool.length === 0 || partnerPool.length === 0) continue

    const anchor = pickTopMover(anchorPool)
    const partner = pickTopMover(partnerPool)
    if (!anchor || !partner) continue

    const anchorPlacement = placementByProductId.get(anchor.id)
    const partnerPlacement = placementByProductId.get(partner.id)
    const isCoLocated =
      Boolean(anchorPlacement) &&
      Boolean(partnerPlacement) &&
      anchorPlacement.shelfLevel === partnerPlacement.shelfLevel

    const combinedDailySales = round(
      (anchor.analytics?.weightedAvgDailySales ?? 0) +
        (partner.analytics?.weightedAvgDailySales ?? 0),
    )

    suggestions.push({
      id: `${anchor.id}:${partner.id}`,
      anchor: {
        id: anchor.id,
        name: anchor.name,
        category: anchor.category,
        shelfLevel: anchorPlacement?.shelfLevel ?? null,
        shelfLabel: anchorPlacement?.shelfLabel ?? null,
      },
      partner: {
        id: partner.id,
        name: partner.name,
        category: partner.category,
        shelfLevel: partnerPlacement?.shelfLevel ?? null,
        shelfLabel: partnerPlacement?.shelfLabel ?? null,
      },
      strength: rule.strength,
      reason: rule.reason,
      placement: rule.placement,
      liftEstimate: rule.liftEstimate,
      combinedDailySales,
      isCoLocated,
      priority: classifyPriority(rule.strength),
    })
  }

  return suggestions.sort((left, right) => {
    const leftScore = left.strength * (1 + left.combinedDailySales / 20)
    const rightScore = right.strength * (1 + right.combinedDailySales / 20)
    return rightScore - leftScore
  })
}

export function summarizeAffinity(suggestions = []) {
  return {
    total: suggestions.length,
    highImpact: suggestions.filter((suggestion) => suggestion.priority === 'HIGH').length,
    coLocated: suggestions.filter((suggestion) => suggestion.isCoLocated).length,
    estimatedAvgLift: suggestions.length
      ? round(
          suggestions.reduce((sum, suggestion) => sum + suggestion.liftEstimate, 0) /
            suggestions.length,
        )
      : 0,
  }
}

function groupByCategory(products) {
  const map = new Map()
  for (const product of products) {
    if (!product?.category) continue
    if (!map.has(product.category)) map.set(product.category, [])
    map.get(product.category).push(product)
  }
  return map
}

function pickTopMover(pool) {
  if (!pool.length) return null
  return pool
    .slice()
    .sort(
      (a, b) =>
        (b.analytics?.weightedAvgDailySales ?? 0) -
        (a.analytics?.weightedAvgDailySales ?? 0),
    )[0]
}

function classifyPriority(strength) {
  if (strength >= 0.75) return 'HIGH'
  if (strength >= 0.6) return 'MEDIUM'
  return 'LOW'
}

function round(value) {
  return Math.round(value * 100) / 100
}
