import { describe, expect, it } from 'vitest'
import { generateMockAIExplanation } from '../mockAI.js'

/**
 * UI_DATA_CONTRACT §4.2, enforced on the explanation text — T9 / #54 Step 5.
 *
 * > At `velocityConfidence: 'none'` the text must not claim a sales rate —
 * > no "يبيع ٣ يومياً", no "سينفد خلال ٤ أيام". Explain from price, stock,
 * > margin, competitor gap, or calendar instead.
 *
 * This was breached. The reorder template said "it moves about ${x ?? '—'}
 * units per day on average" for every product, which at 'none' both asserted a
 * rate we cannot support AND rendered a literal em-dash where a number belongs.
 * 5,539 of 7,317 products sit at 'none', so it was the common path.
 *
 * The rule binds the LLM too (#54 Step 5), but the LLM only ever rephrases this
 * payload — so the guard belongs here, where the claim originates.
 */

const base = {
  id: 'p1',
  name: 'במבה 200 גרם',
  category: 'חטיפים מלוחים',
  currentStock: 4,
  shelfQuantity: 2,
  shelfCapacity: 8,
  price: 10,
  cost: 7,
  leadTimeDays: 2,
  leadTimeSource: 'measured',
}

const recommendation = {
  productId: 'p1',
  type: 'REORDER',
  urgency: 'HIGH',
  confidence: 0.8,
  reason: 'r',
  recommendedOrderQuantity: 24,
  metrics: { weightedAvgDailySales: 3.5, daysUntilStockout: 1 },
}

/** Any phrasing that asserts a rate of sale. */
const RATE_CLAIM = /moves about|units per day|per day on average|يبيع|سينفد/i

describe('§4.2 — no velocity claim without usable velocity', () => {
  it('states no daily rate when velocity confidence is none', () => {
    const text = generateMockAIExplanation(
      { ...base, velocityConfidence: 'none' },
      recommendation,
    )
    expect(text).not.toMatch(RATE_CLAIM)
  })

  it('states no daily rate when the field is absent entirely', () => {
    // resolveVelocityConfidence fails closed to 'none'. Every product today
    // reaches this path, so a regression here is invisible in a spot check.
    const text = generateMockAIExplanation(base, recommendation)
    expect(text).not.toMatch(RATE_CLAIM)
  })

  it('never renders a placeholder where a number belongs', () => {
    for (const confidence of ['none', 'low', 'medium', 'high']) {
      const text = generateMockAIExplanation(
        { ...base, velocityConfidence: confidence },
        { ...recommendation, metrics: { daysUntilStockout: 1 } },   // no rate
      )
      expect(text).not.toMatch(/about\s+—|—\s+units/)
    }
  })

  it('says WHY it is silent rather than just omitting the sentence', () => {
    // A manager who sees no reason assumes the system has nothing. Saying the
    // history is thin is what keeps the recommendation trustworthy.
    const text = generateMockAIExplanation(
      { ...base, velocityConfidence: 'none' },
      recommendation,
    )
    expect(text).toMatch(/too thin|stock level and margin/i)
  })

  it('does state the rate when velocity is genuinely usable', () => {
    // The mirror: the guard must not silence a claim we can support, or the
    // explanation becomes uselessly vague for the 1,778 products that do sell.
    const text = generateMockAIExplanation(
      { ...base, velocityConfidence: 'high' },
      recommendation,
    )
    expect(text).toMatch(/moves about 3\.5 units per day/)
  })

  it('stays silent at a usable confidence when no rate was computed', () => {
    const text = generateMockAIExplanation(
      { ...base, velocityConfidence: 'high' },
      { ...recommendation, metrics: { daysUntilStockout: 1 } },
    )
    expect(text).not.toMatch(RATE_CLAIM)
  })

  it('treats a zero rate as no evidence, not as evidence of zero', () => {
    const text = generateMockAIExplanation(
      { ...base, velocityConfidence: 'high' },
      { ...recommendation, metrics: { weightedAvgDailySales: 0 } },
    )
    expect(text).not.toMatch(/moves about 0 units/)
  })
})
