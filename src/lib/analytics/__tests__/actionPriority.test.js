import { describe, expect, it } from 'vitest'
import {
  IMPACT_KIND,
  estimateImpact,
  impactKind,
  rankActions,
  totalImpact,
} from '../actionPriority.js'

const discrepancy = (overrides = {}) => ({
  id: 'd1', type: 'CHECK_STOCK_DISCREPANCY', metricValue: 100, costPrice: 5,
  confidence: 0.9, ...overrides,
})
const margin = (overrides = {}) => ({
  id: 'm1', type: 'CHECK_MARGIN', sellingPrice: 24.9, costPrice: 30,
  confidence: 0.9, ...overrides,
})

describe('stock discrepancy (D-7)', () => {
  it('values the shortfall at what the stock cost', () => {
    expect(estimateImpact(discrepancy())).toBe(500) // 100 units x ₪5
  })

  it('states no figure when the cost price is unknown', () => {
    // Better to rank it low than to invent a shekel amount.
    expect(estimateImpact(discrepancy({ costPrice: null }))).toBeNull()
  })

  it('is a money action, not data hygiene', () => {
    const { money } = rankActions([discrepancy()])
    expect(money.map((r) => r.id)).toContain('d1')
  })
})

describe('per-sale and one-off figures are never added together', () => {
  it('tags each action with its impact kind', () => {
    expect(impactKind(discrepancy())).toBe(IMPACT_KIND.ONE_OFF)
    expect(impactKind(margin())).toBe(IMPACT_KIND.PER_SALE)
  })

  it('totals them separately', () => {
    // Summing produced a "₪106,164 per sale" headline: ₪8,719 of unaccounted
    // water bottles is not something that happens on every sale.
    const { money } = rankActions([discrepancy(), margin()])
    expect(totalImpact(money, IMPACT_KIND.ONE_OFF)).toBe(500)
    expect(totalImpact(money, IMPACT_KIND.PER_SALE)).toBeCloseTo(5.1, 2)
  })

  it('defaults to per-sale so an untagged action cannot leak into the one-off total', () => {
    expect(totalImpact([{ impactIls: 9 }], IMPACT_KIND.ONE_OFF)).toBe(0)
    expect(totalImpact([{ impactIls: 9 }], IMPACT_KIND.PER_SALE)).toBe(9)
  })
})
