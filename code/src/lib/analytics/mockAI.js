/**
 * Mock AI Explanation Layer
 *
 * Produces natural-language explanations for recommendations.
 * This is NOT a real LLM — it composes templates from product
 * metrics and market context. The function signature mirrors
 * what a real LLM call would look like so it can be swapped later.
 */

export function generateMockAIExplanation(product, recommendation, context = {}) {
  if (!product || !recommendation) return ''

  switch (recommendation.type) {
    case 'REORDER':
      return buildReorderExplanation(product, recommendation, context)
    case 'REDUCE_STOCK':
      return buildOverstockExplanation(product, recommendation, context)
    case 'PROMOTION':
      return buildPromotionExplanation(product, recommendation, context)
    case 'SHELF_INCREASE':
      return buildShelfIncreaseExplanation(product, recommendation, context)
    case 'SHELF_DECREASE':
      return buildShelfDecreaseExplanation(product, recommendation, context)
    default:
      return recommendation.reason ?? ''
  }
}

export function annotateRecommendations(products, recommendations, context = {}) {
  const productIndex = new Map(products.map((product) => [product.id, product]))
  return recommendations.map((recommendation) => {
    const product = productIndex.get(recommendation.productId)
    const explanation = product
      ? generateMockAIExplanation(product, recommendation, context)
      : recommendation.reason
    return { ...recommendation, explanation }
  })
}

function buildReorderExplanation(product, recommendation, context) {
  const m = recommendation.metrics ?? {}
  const qty = recommendation.recommendedOrderQuantity ?? 0
  const sentences = []

  sentences.push(
    `We recommend ordering ${qty} units of ${product.name} because it moves about ${m.weightedAvgDailySales ?? '—'} units per day on average.`,
  )

  if (m.daysUntilStockout !== null && m.daysUntilStockout !== undefined) {
    const days = m.daysUntilStockout
    if (days <= product.leadTimeDays) {
      sentences.push(
        `Current stock of ${product.currentStock} units only covers ${days} days, which is shorter than the ${product.leadTimeDays}-day supplier lead time, so a stockout is likely before the next delivery.`,
      )
    } else {
      sentences.push(
        `Current stock of ${product.currentStock} units covers ${days} days versus a ${product.leadTimeDays}-day lead time.`,
      )
    }
  }

  const marketLine = describeMarketBoost(product, m, context)
  if (marketLine) sentences.push(marketLine)

  if (recommendation.urgency === 'HIGH') {
    sentences.push('Urgency is high — place this order in the next purchase cycle.')
  }

  return sentences.join(' ')
}

function buildOverstockExplanation(product, recommendation, context) {
  const m = recommendation.metrics ?? {}
  const sentences = []

  sentences.push(
    `${product.name} is overstocked: ${product.currentStock} units on hand against an average pace of about ${m.weightedAvgDailySales ?? 0} per day.`,
  )

  if (m.daysUntilStockout && Number.isFinite(m.daysUntilStockout)) {
    sentences.push(
      `That is roughly ${Math.round(m.daysUntilStockout)} days of cover, well above the 30-day threshold for this category.`,
    )
  }

  if (context.currentDate && product.expiryDate) {
    sentences.push(
      `With expiry on ${product.expiryDate}, holding extra inventory ties up cash and increases write-off risk.`,
    )
  }

  sentences.push(
    'Recommend pausing further orders and considering a small promotion or bundle to recover capital.',
  )

  return sentences.join(' ')
}

function buildPromotionExplanation(product, recommendation, context) {
  const m = recommendation.metrics ?? {}
  const sentences = []

  if (product.expiryDate) {
    sentences.push(
      `${product.name} is approaching its expiry date (${product.expiryDate}).`,
    )
    sentences.push(
      `At the current pace of ${m.weightedAvgDailySales ?? 0} units per day, the remaining ${product.currentStock} units will likely not sell through in time.`,
    )
    sentences.push(
      'A short-term promotion or discount is the cheapest way to avoid writing the stock off.',
    )
  } else {
    sentences.push(
      `${product.name} is slow moving — only ${product.salesLast30Days} units in the last 30 days.`,
    )
    sentences.push(
      'Consider a small price drop, a bundle with a faster mover, or reduced shelf space.',
    )
  }

  const marketLine = describeMarketBoost(product, m, context)
  if (marketLine && product.expiryDate) sentences.push(marketLine)

  return sentences.join(' ')
}

function buildShelfIncreaseExplanation(product, recommendation, context) {
  const m = recommendation.metrics ?? {}
  const facings = recommendation.recommendedShelfQuantity
  const sentences = []
  sentences.push(
    `Increase shelf facings for ${product.name}${facings ? ` to ${facings} units` : ''} because it is among the top movers in ${product.category} with about ${m.weightedAvgDailySales ?? 0} units sold per day.`,
  )
  const marketLine = describeMarketBoost(product, m, context)
  if (marketLine) sentences.push(marketLine)
  return sentences.join(' ')
}

function buildShelfDecreaseExplanation(product, recommendation) {
  const facings = recommendation.recommendedShelfQuantity
  return `Reduce shelf facings for ${product.name}${facings ? ` to ${facings} units` : ''}. Sales velocity does not justify the current shelf footprint and the space is better used by faster movers.`
}

function describeMarketBoost(product, metrics, context) {
  const signals = []
  const multiplier = metrics?.demandMultiplier ?? context.demandSignals?.[product.category] ?? 1

  if (multiplier > 1) {
    const boostPct = Math.round((multiplier - 1) * 100)
    signals.push(`category demand is up ~${boostPct}% based on current signals`)
  }

  if (context.weather === 'hot' && isHotWeatherCategory(product.category)) {
    signals.push('hot weather is lifting cold drinks and ice cream demand')
  }

  if (context.weekend && isWeekendCategory(product.category)) {
    signals.push('weekend traffic typically increases this category')
  }

  if (context.holiday) {
    signals.push('a public holiday is in the window, which boosts impulse purchases')
  }

  if (context.localEvent) {
    signals.push(`a nearby event (${context.localEvent}) is expected to add foot traffic`)
  }

  if (signals.length === 0) return null
  return `Market context: ${signals.join('; ')}.`
}

function isHotWeatherCategory(category) {
  return ['Cold Drinks', 'Water', 'Ice Cream', 'Energy Drinks'].includes(category)
}

function isWeekendCategory(category) {
  return ['Snacks', 'Energy Drinks', 'Cigarettes', 'Cold Drinks', 'Chocolate'].includes(category)
}
