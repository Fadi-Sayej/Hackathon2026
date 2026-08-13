import { describe, expect, it } from 'vitest'

import { allocateMarginProportional, comparePlans } from '../baselines.js'

/**
 * Gate 3 of the roadmap: the engine has to beat something. B1 (facings
 * proportional to sales) is impossible without sales, so B2 (margin) is the
 * baseline the greedy allocator must justify itself against.
 */

const unit = { id: 'g1', kind: 'gondola', name: 'ممر', x: 0, y: 0, w: 4, d: 1.2, levels: 2, height: 1.8 }

const product = (overrides = {}) => ({
  id: 'p1',
  name: 'פסטה 500 גרם',
  category: 'מוצרי מכולת',
  currentStock: 40,
  price: 10,
  cost: 6,
  ...overrides,
})

describe('margin-proportional baseline', () => {
  it('gives more facings to the higher-margin product', () => {
    const products = [
      product({ id: 'rich', price: 20, cost: 5 }),
      product({ id: 'thin', price: 10, cost: 9 }),
    ]

    const plan = allocateMarginProportional({ unit, products })
    const facings = Object.fromEntries(
      plan.shelves.flatMap((shelf) => shelf.items).map((entry) => [entry.productId, entry.facings]),
    )

    expect(facings.rich).toBeGreaterThan(facings.thin)
  })

  it('gives every carried product at least one facing', () => {
    const products = [product({ id: 'a' }), product({ id: 'b', price: 10.01, cost: 10 })]

    const plan = allocateMarginProportional({ unit, products })
    const items = plan.shelves.flatMap((shelf) => shelf.items)

    expect(items.every((entry) => entry.facings >= 1)).toBe(true)
  })

  it('never exceeds the shelf run', () => {
    const products = Array.from({ length: 30 }, (_, index) =>
      product({ id: `p${index}`, price: 10 + index, cost: 5 }),
    )

    const plan = allocateMarginProportional({ unit, products })

    for (const shelf of plan.shelves) {
      expect(shelf.usedCm).toBeLessThanOrEqual(shelf.runCm)
    }
  })
})

describe('plan comparison', () => {
  const planWith = (items) => ({
    shelves: [{ code: 'الرف ١', runCm: 100, usedCm: 50, items }],
    summary: { placedProducts: items.length, totalFacings: items.reduce((n, i) => n + i.facings, 0) },
  })

  it('scores margin per linear metre, not raw margin', () => {
    // Same margin, half the space -> twice the score.
    const wide = planWith([{ productId: 'a', facings: 1, widthCm: 20, marginPerUnit: 4, onShelf: 10 }])
    const narrow = planWith([{ productId: 'a', facings: 1, widthCm: 10, marginPerUnit: 4, onShelf: 10 }])

    const result = comparePlans({ wide, narrow })

    expect(result.narrow.marginPerMetre).toBeCloseTo(result.wide.marginPerMetre * 2, 5)
  })

  it('measures stability as positions changed against a reference plan', () => {
    const reference = planWith([
      { productId: 'a', facings: 2, widthCm: 10, marginPerUnit: 4, onShelf: 10 },
      { productId: 'b', facings: 2, widthCm: 10, marginPerUnit: 4, onShelf: 10 },
    ])
    const candidate = planWith([
      { productId: 'a', facings: 2, widthCm: 10, marginPerUnit: 4, onShelf: 10 },
      { productId: 'c', facings: 3, widthCm: 10, marginPerUnit: 4, onShelf: 10 },
    ])

    const result = comparePlans({ candidate }, { reference })

    // b removed, c added -> 2 changed positions.
    expect(result.candidate.changedPositions).toBe(2)
  })

  it('reports no stability figure when there is nothing to compare against', () => {
    const result = comparePlans({ only: planWith([]) })

    expect(result.only.changedPositions).toBeNull()
  })
})

describe('like-for-like comparison', () => {
  it('counts units behind each facing, so the baseline is not handicapped', () => {
    // A plan that reports only its front row would look far poorer than one
    // counting its full depth, and the comparison would measure bookkeeping
    // rather than allocation quality.
    const plan = allocateMarginProportional({ unit, products: [product()] })
    const [item] = plan.shelves.flatMap((shelf) => shelf.items)

    expect(item.depthUnits).toBeGreaterThan(1)
    expect(item.onShelf).toBe(item.facings * item.depthUnits * item.stack)
  })
})

describe('the baseline plays by the same rules', () => {
  const grocery = (id, price) =>
    product({ id, name: `מוצר ${id}`, category: 'מוצרי מכולת', price, cost: price * 0.7 })

  it('excludes the same miscategorised outliers the allocator excludes', () => {
    // Otherwise the comparison flatters whichever side keeps the television,
    // and the sign of the result depends on a data error rather than on the
    // allocation. Seen live: SmartShelf reported -66% against its own baseline.
    const products = [
      ...Array.from({ length: 30 }, (_, index) => grocery(`p${index}`, 10 + index * 0.1)),
      grocery('television', 4000),
    ]

    const plan = allocateMarginProportional({ unit, products })
    const ids = plan.shelves.flatMap((shelf) => shelf.items).map((item) => item.productId)

    expect(ids).not.toContain('television')
  })
})
