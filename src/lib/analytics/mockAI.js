/**
 * Mock AI Explanation Layer
 *
 * Produces natural-language explanations for recommendations.
 * This is NOT a real LLM — it composes templates from product
 * metrics and market context. The function signature mirrors
 * what a real LLM call would look like so it can be swapped later.
 */

import { isAssumedLeadTime } from '../receiving/leadTimeResolver.js'
import { hasUsableVelocity, resolveVelocityConfidence } from './velocityConfidence.js'

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

  // UI_DATA_CONTRACT §4.2 is binding on this sentence, not just on the numbers
  // beside it: at velocityConfidence 'none' the text must not claim a sales
  // rate. This used to read "it moves about — units per day on average" for
  // every product without velocity — both a §4.2 breach and a literal em-dash
  // rendered where a number belongs. 5,539 of 7,317 products are at 'none',
  // so that was the common case, not the edge case.
  //
  // Same rule as the assumed-lead-time wording below: say what we know, and
  // stay silent about what we do not.
  const rate = m.weightedAvgDailySales
  const canClaimRate =
    hasUsableVelocity(resolveVelocityConfidence(product)) && Number.isFinite(rate) && rate > 0

  if (canClaimRate) {
    sentences.push(
      `We recommend ordering ${qty} units of ${product.name} because it moves about ${rate} units per day on average.`,
    )
  } else {
    sentences.push(
      `We recommend ordering ${qty} units of ${product.name}. Sales history for this product is too thin to state a daily rate, so this is based on stock level and margin rather than measured demand.`,
    )
  }

  if (m.daysUntilStockout !== null && m.daysUntilStockout !== undefined) {
    const days = m.daysUntilStockout
    // This block is the string a manager actually reads on the Recommendations
    // page, so it carries the same honesty rule as the rule-based reason text:
    // never present the fallback lead time as though a delivery was observed.
    const assumed = isAssumedLeadTime(product)
    const leadTimePhrase = assumed ? 'assumed supplier lead time' : 'supplier lead time'
    const indefinite = assumed ? 'an' : 'a'
    if (days <= product.leadTimeDays) {
      sentences.push(
        `Current stock of ${product.currentStock} units only covers ${days} days, which is shorter than the ${leadTimePhrase} of ${product.leadTimeDays} days, so a stockout is likely before the next delivery.`,
      )
    } else {
      sentences.push(
        `Current stock of ${product.currentStock} units covers ${days} days versus ${indefinite} ${leadTimePhrase} of ${product.leadTimeDays} days.`,
      )
    }
    if (assumed) {
      sentences.push(
        "Not enough deliveries have been recorded to measure this supplier's lead time, so the figure above is the system default rather than something observed.",
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
