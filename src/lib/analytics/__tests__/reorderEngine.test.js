import { describe, expect, it } from 'vitest'

import {
  aggregateNetValueAtStake,
  generateReorderRecommendations,
} from '../reorderEngine.js'
import { RECOMMENDATION_TYPES } from '../recommendationTypes.js'

const CURRENT_DATE = '2026-08-12'

function product(overrides = {}) {
  return {
    id: 'sku-base',
    name: 'Baseline product',
    category: 'Grocery',
    currentStock: 10,
    shelfQuantity: 5,
    salesLast7Days: 0,
    salesLast30Days: 0,
    leadTimeDays: 3,
    price: 20,
    cost: 10,
    expiryDate: '2026-12-31',
    velocityConfidence: 'none',
    ...overrides,
  }
}

function recommendationOfType(recommendations, type) {
  return recommendations.find((recommendation) => recommendation.type === type)
}

describe('reorderEngine velocity honesty guarantees', () => {
  it('does not fabricate a reorder when velocity confidence is missing or none', () => {
    const recommendations = generateReorderRecommendations([
      product({
        id: 'missing-confidence-fast-sales',
        currentStock: 0,
        salesLast7Days: 35,
        salesLast30Days: 150,
        velocityConfidence: undefined,
      }),
      product({
        id: 'explicit-none-fast-sales',
        currentStock: 0,
        salesLast7Days: 35,
        salesLast30Days: 150,
        velocityConfidence: 'none',
      }),
    ], { currentDate: CURRENT_DATE })

    const reorders = recommendations.filter(
      ({ type }) => type === RECOMMENDATION_TYPES.REORDER,
    )

    expect(
      reorders,
      'A store manager would receive a fabricated reorder based on sales figures that have no supporting velocity evidence.',
    ).toHaveLength(0)
  })

  it('does not promote stock when sales history is unavailable', () => {
    const recommendations = generateReorderRecommendations([
      product({
        id: 'new-near-expiry-sku',
        expiryDate: '2026-08-15',
      }),
      product({
        id: 'new-zero-sales-sku',
        currentStock: 40,
      }),
    ], { currentDate: CURRENT_DATE })

    const promotions = recommendations.filter(
      ({ type }) => type === RECOMMENDATION_TYPES.PROMOTION,
    )

    expect(
      promotions,
      'A store manager would be told to discount stock based on sales history the system does not have.',
    ).toHaveLength(0)
  })

  it('still reorders a proven fast seller on the high-confidence path', () => {
    const recommendations = generateReorderRecommendations([product({
      id: 'proven-fast-seller',
      currentStock: 2,
      salesLast7Days: 35,
      salesLast30Days: 150,
      velocityConfidence: 'high',
    })], { currentDate: CURRENT_DATE })

    expect(
      recommendations.map(({ type }) => type),
      'A store manager would miss a necessary reorder despite high-confidence sales proving an imminent stockout.',
    ).toEqual([RECOMMENDATION_TYPES.REORDER])
  })

  it('emits the four financial and data-quality types from their real signals', () => {
    const scenarios = [
      {
        type: RECOMMENDATION_TYPES.BELOW_COST,
        input: product({ id: 'below-cost', price: 8, cost: 10 }),
      },
      {
        type: RECOMMENDATION_TYPES.NEGATIVE_STOCK,
        input: product({ id: 'negative-stock', currentStock: -3 }),
      },
      {
        type: RECOMMENDATION_TYPES.THIN_MARGIN,
        input: product({ id: 'thin-margin', price: 10, cost: 9 }),
      },
      {
        type: RECOMMENDATION_TYPES.PRICE_GAP,
        input: product({
          id: 'price-gap',
          price: 12,
          competitor: { cheapestCompetitorPrice: 10 },
        }),
      },
    ]

    for (const { type, input } of scenarios) {
      const recommendations = generateReorderRecommendations([input], {
        currentDate: CURRENT_DATE,
      })

      expect(
        recommendationOfType(recommendations, type),
        `A store manager would miss the ${type} alert even though the underlying financial or stock signal is present.`,
      ).toBeDefined()
    }
  })

  it('gives every recommendation a finite numeric shekel value at stake', () => {
    const recommendations = generateReorderRecommendations([
      product({ id: 'below-cost', currentStock: 20, price: 8, cost: 10 }),
      product({ id: 'negative-stock', currentStock: -3 }),
      product({ id: 'thin-margin', price: 10, cost: 9 }),
      product({
        id: 'price-gap',
        price: 12,
        competitor: { cheapestCompetitorPrice: 10 },
      }),
    ], { currentDate: CURRENT_DATE })

    const invalidValues = recommendations.filter(
      ({ valueAtStake }) => typeof valueAtStake !== 'number' || !Number.isFinite(valueAtStake),
    )

    expect(
      invalidValues,
      'Malik’s ranking would silently mis-order customer actions because a recommendation has no numeric ₪-at-stake.',
    ).toHaveLength(0)
  })

  it('sorts the greatest shekel value at stake first', () => {
    const recommendations = generateReorderRecommendations([
      product({ id: 'small-loss', currentStock: 10, price: 9, cost: 10 }),
      product({ id: 'large-loss', currentStock: 100, price: 5, cost: 10 }),
      product({ id: 'stock-discrepancy', currentStock: -3, cost: 10 }),
    ], { currentDate: CURRENT_DATE })
    const values = recommendations.map(({ valueAtStake }) => valueAtStake)

    expect(
      values,
      'A store manager would see a lower-value action ahead of the action with the most ₪ at risk.',
    ).toEqual([...values].sort((a, b) => b - a))
  })

  it('writes product-specific reasons for two recommendations of the same type', () => {
    const recommendations = generateReorderRecommendations([
      product({ id: 'loss-a', name: 'Olive Oil', price: 8, cost: 10 }),
      product({ id: 'loss-b', name: 'Tahini', price: 7, cost: 10 }),
    ], { currentDate: CURRENT_DATE })
    const belowCostReasons = recommendations
      .filter(({ type }) => type === RECOMMENDATION_TYPES.BELOW_COST)
      .map(({ reason }) => reason)

    expect(
      new Set(belowCostReasons).size,
      'A store manager would see duplicated reason text that does not identify which product needs action.',
    ).toBe(2)
  })
})

describe('net value-at-stake aggregation semantics (#30)', () => {
  it('counts each product once by its greatest signal (deduplicated exposure)', () => {
    expect(
      aggregateNetValueAtStake([
        { productId: 'p1', valueAtStake: 200 },
        { productId: 'p1', valueAtStake: 300 }, // same product → keep the larger
        { productId: 'p2', valueAtStake: 150 },
      ]),
      'The headline exposure double-counted a product that trips several signals.',
    ).toBe(450) // max(200,300) + 150, not 200+300+150
  })

  it('treats recommendations without a productId as distinct exposures', () => {
    expect(aggregateNetValueAtStake([{ valueAtStake: 100 }, { valueAtStake: 40 }])).toBe(140)
  })

  it('returns 0 for empty or non-array input', () => {
    expect(aggregateNetValueAtStake([])).toBe(0)
    expect(aggregateNetValueAtStake(null)).toBe(0)
  })

  it('does not double-count a product that triggers both BELOW_COST and PRICE_GAP', () => {
    // price 8 < cost 10 → BELOW_COST value = (10-8)*100 = 200
    // price 8 > competitor 5 → PRICE_GAP value = (8-5)*100 = 300
    // These prescribe opposite fixes on the same 100 units, so the headline must
    // count the product once (its worst single exposure), not 200 + 300 = 500.
    const recommendations = generateReorderRecommendations(
      [
        product({
          id: 'dual-signal',
          currentStock: 100,
          price: 8,
          cost: 10,
          competitor: { cheapestCompetitorPrice: 5 },
        }),
      ],
      { currentDate: CURRENT_DATE },
    )

    const dual = recommendations.filter(({ productId }) => productId === 'dual-signal')
    expect(
      dual.map(({ type }) => type).sort(),
      'The dual-signal product should surface both the below-cost and price-gap actions.',
    ).toEqual([RECOMMENDATION_TYPES.BELOW_COST, RECOMMENDATION_TYPES.PRICE_GAP].sort())

    const grossSum = dual.reduce((sum, { valueAtStake }) => sum + valueAtStake, 0)
    const worstSingle = Math.max(...dual.map(({ valueAtStake }) => valueAtStake))
    const net = aggregateNetValueAtStake(recommendations)

    expect(net, 'Net exposure must equal the single worst signal, not the gross sum.').toBe(worstSingle)
    expect(net).toBeLessThan(grossSum)
  })

  it('sums exposure across distinct products', () => {
    const recommendations = generateReorderRecommendations(
      [
        product({ id: 'loss', currentStock: 100, price: 8, cost: 10 }), // BELOW_COST = 200
        product({
          id: 'overpriced',
          currentStock: 100,
          price: 20,
          cost: 10, // healthy margin → no BELOW_COST / THIN_MARGIN
          competitor: { cheapestCompetitorPrice: 15 }, // PRICE_GAP = (20-15)*100 = 500
        }),
      ],
      { currentDate: CURRENT_DATE },
    )

    const maxFor = (id) =>
      Math.max(
        ...recommendations
          .filter(({ productId }) => productId === id)
          .map(({ valueAtStake }) => valueAtStake),
      )

    expect(aggregateNetValueAtStake(recommendations)).toBe(maxFor('loss') + maxFor('overpriced'))
  })
})

describe('BELOW_COST uses the shared credibility guard (UI_DATA_CONTRACT §9.5)', () => {
  it('flags a genuine below-cost sale', () => {
    const recs = generateReorderRecommendations(
      [product({ id: 'sku-real-loss', price: 24.9, cost: 30 })],
      { currentDate: CURRENT_DATE },
    )
    expect(recs.map((r) => r.type)).toContain(RECOMMENDATION_TYPES.BELOW_COST)
  })

  it('does NOT flag a case price recorded against a unit price', () => {
    // Real rows from the YomYom catalog: a paper bag at ₪0.47 with a ₪200 "cost"
    // is a case price, not a ₪199.53 loss on every bag. A bare price < cost
    // comparison reported 63 below-cost products while the Prices screen showed
    // 37 — two screens contradicting each other about the same shop.
    const artifacts = [
      product({ id: 'sku-case-price', price: 0.47, cost: 200 }),
      product({ id: 'sku-free-promo', price: 0.01, cost: 2.28 }),
      product({ id: 'sku-pack-of-4', price: 1.9, cost: 7.6 }),
    ]
    for (const item of artifacts) {
      const recs = generateReorderRecommendations([item], { currentDate: CURRENT_DATE })
      expect(recs.map((r) => r.type)).not.toContain(RECOMMENDATION_TYPES.BELOW_COST)
    }
  })

  it('agrees with credibleLoss on every product, so screens cannot diverge', async () => {
    const { credibleLoss } = await import('../actionPriority.js')
    const catalog = [
      product({ id: 'a', price: 24.9, cost: 30 }),
      product({ id: 'b', price: 0.47, cost: 200 }),
      product({ id: 'c', price: 10, cost: 8 }),
      product({ id: 'd', price: 10, cost: 20 }),
      product({ id: 'e', price: 10, cost: 20.1 }),
    ]
    const flagged = generateReorderRecommendations(catalog, { currentDate: CURRENT_DATE })
      .filter((r) => r.type === RECOMMENDATION_TYPES.BELOW_COST)
      .map((r) => r.productId)
      .sort()
    const expected = catalog
      .filter((p) => credibleLoss(p.price, p.cost) !== null)
      .map((p) => p.id)
      .sort()

    expect(flagged).toEqual(expected)
  })
})

describe('never suggests reordering something the shop does not stock', () => {
  const seller = (overrides = {}) => product({
    id: 'sku-fast', currentStock: 0, salesLast7Days: 140, salesLast30Days: 600,
    velocityConfidence: 'high', ...overrides,
  })

  it('does suggest reorder for a normal stocked product', () => {
    const recs = generateReorderRecommendations([seller({ isStocked: true })], { currentDate: CURRENT_DATE })
    expect(recs.map((r) => r.type)).toContain(RECOMMENDATION_TYPES.REORDER)
  })

  it('does NOT suggest reorder when the product is never delivered', () => {
    // A car wash sells 20/day and is always "0 in stock". 683 of the 1,778
    // products in YomYom's sales reports had sales but zero receipts across
    // seven months, and they took over the top of the reorder list.
    const recs = generateReorderRecommendations([seller({ isStocked: false })], { currentDate: CURRENT_DATE })
    expect(recs.map((r) => r.type)).not.toContain(RECOMMENDATION_TYPES.REORDER)
  })

  it('does NOT suggest reducing stock on a never-delivered product either', () => {
    const recs = generateReorderRecommendations(
      [seller({ isStocked: false, currentStock: 100000, salesLast7Days: 7, salesLast30Days: 30 })],
      { currentDate: CURRENT_DATE },
    )
    expect(recs.map((r) => r.type)).not.toContain(RECOMMENDATION_TYPES.REDUCE_STOCK)
  })

  it('still suggests reorder when stocking is unknown (null), rather than going silent', () => {
    // null means "no sales report for it", not "not stocked". Suppressing on
    // unknown would hide real replenishment needs for most of the catalog.
    const recs = generateReorderRecommendations([seller({ isStocked: null })], { currentDate: CURRENT_DATE })
    expect(recs.map((r) => r.type)).toContain(RECOMMENDATION_TYPES.REORDER)
  })

  it('keeps margin advice on a never-delivered product', () => {
    // Velocity is still real for a car wash; only replenishment is meaningless.
    const recs = generateReorderRecommendations(
      [seller({ isStocked: false, price: 24.9, cost: 30 })],
      { currentDate: CURRENT_DATE },
    )
    expect(recs.map((r) => r.type)).toContain(RECOMMENDATION_TYPES.BELOW_COST)
  })
})
