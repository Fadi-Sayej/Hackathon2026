import { describe, expect, it } from 'vitest'

import { analyzeProduct, analyzeProducts } from '../inventoryEngine.js'

const CURRENT_DATE = '2026-08-12'

function product(overrides = {}) {
  return {
    id: 'sku-base',
    name: 'Baseline product',
    category: 'Grocery',
    currentStock: 24,
    shelfQuantity: 8,
    salesLast7Days: 0,
    salesLast30Days: 0,
    leadTimeDays: 4,
    price: 20,
    cost: 10,
    expiryDate: '2026-12-31',
    velocityConfidence: 'none',
    ...overrides,
  }
}

describe('inventoryEngine velocity honesty guarantees', () => {
  it('never labels products without sales history as slow-moving', () => {
    const analyzed = analyzeProducts([
      product({ id: 'new-sku-zero-sales' }),
      product({
        id: 'new-sku-imported-sales',
        salesLast7Days: 14,
        salesLast30Days: 60,
      }),
    ], { currentDate: CURRENT_DATE })

    const slowMoving = analyzed.filter(({ analytics }) =>
      analytics.statuses.includes('Slow moving'),
    )

    expect(
      slowMoving,
      'A store manager would see an invented “Slow moving” claim for a product with no usable history.',
    ).toHaveLength(0)
  })

  it('shows the honest no-history status and no numeric stockout horizon', () => {
    const { analytics } = analyzeProduct(product(), { currentDate: CURRENT_DATE })

    expect(
      {
        primaryStatus: analytics.primaryStatus,
        statuses: analytics.statuses,
        daysUntilStockout: analytics.daysUntilStockout,
      },
      'A store manager would be shown a confident inventory verdict or a fabricated stockout horizon without sales history.',
    ).toEqual({
      primaryStatus: 'Not enough sales history yet',
      statuses: ['Not enough sales history yet'],
      daysUntilStockout: null,
    })
  })

  it('does not apply slow-moving or non-finite risk penalties without history', () => {
    const { analytics } = analyzeProduct(product(), { currentDate: CURRENT_DATE })

    expect(
      analytics.riskScore,
      'A store manager would see risk inflated by penalties that require sales history.',
    ).toBe(0)
  })

  it('preserves the established high-confidence stockout classifications', () => {
    const { analytics } = analyzeProduct(product({
      id: 'proven-fast-mover',
      currentStock: 10,
      salesLast7Days: 14,
      salesLast30Days: 60,
      leadTimeDays: 5,
      velocityConfidence: 'high',
    }), { currentDate: CURRENT_DATE })

    expect(
      {
        statuses: analytics.statuses,
        primaryStatus: analytics.primaryStatus,
        daysUntilStockout: analytics.daysUntilStockout,
        riskScore: analytics.riskScore,
      },
      'A store manager would lose the established stockout warning for a product backed by real sales history.',
    ).toEqual({
      statuses: ['Stockout risk', 'High priority'],
      primaryStatus: 'High priority',
      daysUntilStockout: 5,
      riskScore: 55,
    })
  })

  it('legitimately labels zero sales as slow-moving when confidence is high', () => {
    const { analytics } = analyzeProduct(product({
      id: 'proven-zero-sales',
      currentStock: 12,
      velocityConfidence: 'high',
    }), { currentDate: CURRENT_DATE })

    expect(
      {
        statuses: analytics.statuses,
        primaryStatus: analytics.primaryStatus,
        daysUntilStockout: analytics.daysUntilStockout,
        riskScore: analytics.riskScore,
      },
      'A store manager would miss a genuine slow-moving warning even though a complete sales history proves zero sales.',
    ).toEqual({
      statuses: ['Slow moving'],
      primaryStatus: 'Slow moving',
      daysUntilStockout: null,
      riskScore: 18,
    })
  })
})
