import { describe, expect, it } from 'vitest'

import { generateMockAIExplanation } from '../mockAI.js'

// This is the string a manager actually reads on the Recommendations page.
// It carries the same honesty rule as reorderEngine's rule-based reason text
// (see reorderEngine.test.js: 'never states an assumed lead time as a
// measured one') — never present a fallback lead time as though a delivery
// interval was observed. Mirrors that suite's approach so the two read
// consistently.
function product(overrides = {}) {
  return {
    id: 'sku-lead',
    name: 'Baseline product',
    category: 'Grocery',
    // daysUntilStockout (5) > leadTimeDays (3) below, so the "covers N days
    // versus a/an X-day lead time" branch runs — the one that uses the
    // indefinite article and is distinct from the "shorter than" branch
    // exercised separately below.
    currentStock: 10,
    leadTimeDays: 3,
    ...overrides,
  }
}

function reorderRecommendation(overrides = {}) {
  return {
    productId: 'sku-lead',
    type: 'REORDER',
    urgency: 'MEDIUM',
    recommendedOrderQuantity: 20,
    metrics: {
      weightedAvgDailySales: 2,
      daysUntilStockout: 5,
    },
    ...overrides,
  }
}

describe('generateMockAIExplanation — REORDER lead-time phrasing', () => {
  it('qualifies the lead time as assumed when leadTimeSource is the default fallback', () => {
    const explanation = generateMockAIExplanation(
      product({ leadTimeSource: 'default' }),
      reorderRecommendation(),
    )
    expect(explanation).toMatch(/an assumed supplier lead time/)
    expect(explanation).toMatch(/not enough deliveries have been recorded/i)
  })

  it('treats a product with no leadTimeSource at all as assumed', () => {
    const explanation = generateMockAIExplanation(product(), reorderRecommendation())
    expect(explanation).toMatch(/an assumed supplier lead time/)
  })

  it('states the lead time plainly, with no "assumed" wording, once it is measured', () => {
    const explanation = generateMockAIExplanation(
      product({ leadTimeSource: 'measured' }),
      reorderRecommendation(),
    )
    expect(explanation).toMatch(/a supplier lead time/)
    expect(explanation).not.toMatch(/assumed/i)
    expect(explanation).not.toMatch(/not enough deliveries have been recorded/i)
  })

  it('produces genuinely different text for measured vs. default on otherwise-identical input', () => {
    const assumed = generateMockAIExplanation(
      product({ leadTimeSource: 'default' }),
      reorderRecommendation(),
    )
    const measured = generateMockAIExplanation(
      product({ leadTimeSource: 'measured' }),
      reorderRecommendation(),
    )
    expect(assumed).not.toBe(measured)
  })

  it('does not claim measurement when stock is already short of the assumed lead time', () => {
    // Exercises the other half of the branch (days <= leadTimeDays), which
    // uses `leadTimePhrase` without the indefinite article.
    const explanation = generateMockAIExplanation(
      product({ leadTimeSource: 'default', currentStock: 1 }),
      reorderRecommendation({ metrics: { weightedAvgDailySales: 2, daysUntilStockout: 1 } }),
    )
    expect(explanation).toMatch(/shorter than the assumed supplier lead time/)
  })
})
