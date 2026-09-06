import { describe, expect, it } from 'vitest'
import { createTranslator } from '../index.js'
import { renderReorderExplanation, renderReorderExplanationText } from '../explainReorder.js'
import { buildReorderFacts } from '../../analytics/reorderFacts.js'
import { computeMetrics, generateReorderRecommendations } from '../../analytics/reorderEngine.js'

const LANGUAGES = ['he', 'ar', 'en']

const product = {
  id: 'p1',
  name: 'קוקה קולה 1.5 ליטר',
  category: 'משקאות',
  price: 8,
  cost: 5,
  currentStock: 12,
  salesLast7Days: 40,
  salesLast30Days: 160,
  leadTimeDays: 3,
  leadTimeSource: 'default',
  velocityConfidence: 'medium',
  demandPerDayCorrected: 18.4,
  demandConfidence: 'medium',
  availabilityState: 'STOCKOUT_SUSPECTED',
  censoredDays: 30,
  stockReconciles: true,
  isStocked: true,
}

/** Every number the sentence prints must be one the decision actually used. */
function numbersIn(text) {
  return (text.match(/\d+(?:\.\d+)?/g) ?? []).map(Number)
}

describe('reorder explanation — figures must match the decision', () => {
  it.each(LANGUAGES)('prints only decision values in %s', (language) => {
    const metrics = computeMetrics(product, { demandSignals: {} })
    const facts = buildReorderFacts(product, metrics, {})
    const t = createTranslator(language)
    const text = renderReorderExplanationText(facts, t)

    // The decision's own values, plus the derived percentages the facts carry.
    const allowed = new Set([
      facts.currentStock, facts.dailyRate, facts.leadTimeDays,
      facts.expectedDemandDuringLeadTime, facts.safetyStock, facts.orderQty,
      facts.coverDays, facts.censoredDays, facts.costToIgnore,
      Math.round((facts.demandMultiplier - 1) * 100),
    ].filter((value) => typeof value === 'number'))

    for (const printed of numbersIn(text)) {
      expect(allowed.has(printed), `${printed} in ${language} is not a decision value`).toBe(true)
    }
  })

  it('prints the order quantity the engine decided, not a recomputed one', () => {
    const metrics = computeMetrics(product, { demandSignals: {} })
    const facts = buildReorderFacts(product, metrics, {})
    const rendered = renderReorderExplanation(facts, createTranslator('en'))
    expect(rendered.quantity).toContain(String(metrics.recommendedOrder))
    expect(facts.orderQty).toBe(metrics.recommendedOrder)
  })

  it('sizes the order from corrected demand when the pipeline produced one', () => {
    const metrics = computeMetrics(product, { demandSignals: {} })
    expect(metrics.rateBasis).toBe('corrected')
    // 18.4 corrected, not the 5.71/day the raw weekly+monthly blend would give.
    expect(metrics.dailyRate).toBeCloseTo(18.4, 1)
  })

  it('falls back to observed sales when no corrected rate exists', () => {
    const noCorrection = { ...product, demandPerDayCorrected: null }
    const metrics = computeMetrics(noCorrection, { demandSignals: {} })
    expect(metrics.rateBasis).toBe('observed')
  })
})

describe('assumed values stay labelled assumed', () => {
  it.each(LANGUAGES)('labels an assumed lead time in %s', (language) => {
    const metrics = computeMetrics(product, { demandSignals: {} })
    const facts = buildReorderFacts(product, metrics, {})
    const t = createTranslator(language)
    const rendered = renderReorderExplanation(facts, t)

    expect(facts.leadTimeAssumed).toBe(true)
    // The assumption must be visible in the quantity section, where the number is
    // used, and again in the uncertainty section — not smoothed away in either.
    expect(rendered.quantity).toContain(t('explain.qty.leadAssumed', { lead: facts.leadTimeDays }))
    expect(rendered.uncertainty).toContain(t('explain.unsure.leadAssumed'))
  })

  it.each(LANGUAGES)('does not claim measurement in %s when none exists', (language) => {
    const metrics = computeMetrics(product, { demandSignals: {} })
    const facts = buildReorderFacts(product, metrics, {})
    const t = createTranslator(language)
    const rendered = renderReorderExplanation(facts, t)
    expect(rendered.quantity).not.toContain(t('explain.qty.leadMeasured', { lead: facts.leadTimeDays }))
  })

  it('says the daily rate is derived, not observed, in every language', () => {
    const metrics = computeMetrics(product, { demandSignals: {} })
    const facts = buildReorderFacts(product, metrics, {})
    for (const language of LANGUAGES) {
      const t = createTranslator(language)
      expect(renderReorderExplanation(facts, t).uncertainty)
        .toContain(t('explain.unsure.monthlyBasis'))
    }
  })
})

describe('honest degradation', () => {
  it('omits the cost section entirely when no cost price exists', () => {
    const noCost = { ...product, cost: 0 }
    const facts = buildReorderFacts(noCost, computeMetrics(noCost, {}), {})
    expect(facts.costToIgnore).toBeNull()
    expect(renderReorderExplanation(facts, createTranslator('he')).cost).toBeNull()
  })

  it('states that case size is unknown rather than inventing one', () => {
    const facts = buildReorderFacts(product, computeMetrics(product, {}), {})
    const t = createTranslator('he')
    expect(facts.caseSize).toBeNull()
    expect(renderReorderExplanation(facts, t).quantity).toContain(t('explain.qty.noCaseSize'))
  })

  it('flags a stock figure that fails its own arithmetic', () => {
    const broken = { ...product, stockReconciles: false }
    const facts = buildReorderFacts(broken, computeMetrics(broken, {}), {})
    const t = createTranslator('he')
    expect(renderReorderExplanation(facts, t).uncertainty).toContain(t('explain.unsure.stockBroken'))
  })

  it('renders in all three languages without leaking a raw key', () => {
    const facts = buildReorderFacts(product, computeMetrics(product, {}), {
      activeReasons: ['hot_weather', 'ramadan'],
    })
    for (const language of LANGUAGES) {
      const text = renderReorderExplanationText(facts, createTranslator(language))
      expect(text).not.toMatch(/explain\./)
      expect(text.length).toBeGreaterThan(80)
    }
  })
})

describe('facts travel with every REORDER the engine emits', () => {
  it('attaches facts whose order quantity matches the recommendation', () => {
    const recs = generateReorderRecommendations([product], { demandSignals: {} })
    const reorder = recs.find((r) => r.type === 'REORDER')
    expect(reorder.facts).toBeTruthy()
    expect(reorder.facts.orderQty).toBe(reorder.recommendedOrderQuantity)
  })
})
