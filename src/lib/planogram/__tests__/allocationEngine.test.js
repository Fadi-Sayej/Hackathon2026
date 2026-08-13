import { describe, expect, it } from 'vitest'

import { allocateUnit } from '../allocationEngine.js'
import { FIXTURE_KINDS } from '../fixtures.js'

const spec = FIXTURE_KINDS.gondola
const gondola = {
  id: 'g1',
  kind: 'gondola',
  name: 'ممر ١',
  x: 0,
  y: 0,
  w: spec.w,
  d: spec.d,
  levels: spec.levels,
  height: spec.height,
}

const product = (overrides = {}) => ({
  id: 'p1',
  name: 'פסטה 500 גרם',
  category: 'מוצרי מכולת',
  currentStock: 100,
  price: 10,
  cost: 6,
  ...overrides,
})

const allItems = (result) => result.shelves.flatMap((shelf) => shelf.items)

describe('placement output', () => {
  it('exposes the geometry the validator needs to check clearance and weight', () => {
    const result = allocateUnit({ unit: gondola, products: [product()] })

    const [item] = allItems(result)
    expect(item.heightCm).toBeGreaterThan(0)
    expect(item.litres).toBeGreaterThan(0)
  })
})

describe('hard constraints', () => {
  it('never allocates more width than a shelf has', () => {
    const products = Array.from({ length: 120 }, (_, index) =>
      product({ id: `p${index}`, price: 10 + index * 0.1 }),
    )

    const result = allocateUnit({ unit: gondola, products })

    for (const shelf of result.shelves) {
      const width = shelf.items.reduce((sum, item) => sum + item.facings * item.widthCm, 0)
      expect(width).toBeLessThanOrEqual(shelf.runCm)
    }
  })

  it('keeps heavy packages off the eye-level shelf', () => {
    // A 5kg rice sack is 22 x 32 x 12cm — well past the heavy threshold.
    const products = [product({ id: 'rice', name: 'אורז בסמטי 5 קג', price: 40, cost: 10 })]

    const result = allocateUnit({ unit: gondola, products })
    const placed = result.shelves.find((shelf) => shelf.items.length > 0)

    expect(placed.shelfLevel).toBe('BOTTOM')
  })
})

describe('assortment', () => {
  it('carries fewer products than fit at one facing, so facings can vary', () => {
    const products = Array.from({ length: 400 }, (_, index) =>
      product({ id: `p${index}`, price: 10 + index * 0.01 }),
    )

    const result = allocateUnit({ unit: gondola, products })
    const facings = allItems(result).map((item) => item.facings)

    expect(result.summary.notCarriedProducts).toBeGreaterThan(0)
    expect(Math.max(...facings)).toBeGreaterThan(1)
  })

  it('reports the products it declined to carry', () => {
    const products = Array.from({ length: 400 }, (_, index) => product({ id: `p${index}` }))

    const result = allocateUnit({ unit: gondola, products })

    expect(result.notCarried.length).toBe(400 - result.summary.placedProducts)
  })
})

describe('non-merchandise', () => {
  it('places nothing from a services department', () => {
    const products = [
      product({ id: 'wash', name: 'שטיפה רכב פרטי', category: 'קופה שטיפה (הכל )', price: 80, cost: 30 }),
    ]

    const result = allocateUnit({ unit: gondola, products })

    expect(allItems(result)).toHaveLength(0)
  })
})

describe('stock reporting', () => {
  it('reports negative POS stock as zero, not as a negative quantity', () => {
    const result = allocateUnit({ unit: gondola, products: [product({ currentStock: -1763 })] })

    const [item] = allItems(result)
    expect(item.currentStock).toBe(0)
    expect(item.status).toBe('out')
  })
})

describe('heavy goods are a safety constraint, not a preference', () => {
  it('refuses to place a heavy package above the bottom shelf when the bottom is full', () => {
    // A 5kg rice sack scales to ~14cm wide, so a 6m bottom shelf holds about 41
    // of them at one facing. 80 forces a genuine overflow, and the overflow must
    // be reported as unplaced rather than promoted to a higher shelf.
    const products = Array.from({ length: 80 }, (_, index) => ({
      id: `rice${index}`,
      name: 'אורז בסמטי 5 קג',
      category: 'מוצרי מכולת',
      currentStock: 100,
      price: 40 + index,
      cost: 10,
    }))

    const result = allocateUnit({ unit: gondola, products })

    const misplaced = result.shelves
      .filter((shelf) => shelf.shelfLevel !== 'BOTTOM')
      .flatMap((shelf) => shelf.items)

    expect(misplaced).toHaveLength(0)
    expect(result.unplaced.length).toBeGreaterThan(0)
  })
})

describe('miscategorised products', () => {
  const grocery = (id, price) =>
    product({ id, name: `מוצר ${id}`, category: 'מוצרי מכולת', price, cost: price * 0.7 })

  it('keeps a product whose margin is absurd for its department off the shelf', () => {
    // A 65-inch television really is filed under groceries in the YomYom export.
    // Its margin dwarfs every actual grocery item, so profit-per-centimetre puts
    // it at eye level — on a shelf it could not physically sit on.
    const products = [
      ...Array.from({ length: 30 }, (_, index) => grocery(`p${index}`, 10 + index * 0.1)),
      grocery('television', 4000),
    ]

    const result = allocateUnit({ unit: gondola, products })

    expect(allItems(result).map((item) => item.productId)).not.toContain('television')
  })

  it('reports it as a suspected data error rather than dropping it silently', () => {
    const products = [
      ...Array.from({ length: 30 }, (_, index) => grocery(`p${index}`, 10 + index * 0.1)),
      grocery('television', 4000),
    ]

    const result = allocateUnit({ unit: gondola, products })

    expect(result.suspect.map((entry) => entry.product.id)).toContain('television')
    expect(result.suspect[0].reason).toBe('MARGIN_OUTLIER')
  })

  it('leaves an ordinary premium product alone', () => {
    // Twice the category median is a nice bottle of oil, not a data error.
    const products = [
      ...Array.from({ length: 30 }, (_, index) => grocery(`p${index}`, 10 + index * 0.1)),
      grocery('premium', 24),
    ]

    const result = allocateUnit({ unit: gondola, products })

    expect(allItems(result).map((item) => item.productId)).toContain('premium')
  })
})

describe('demand confidence is reported, not assumed', () => {
  const withVelocity = (id, perDay) => ({
    ...product({ id, name: `מוצר ${id}`, category: 'משקאות' }),
    velocityConfidence: 'high',
    analytics: { weightedAvgDailySales: perDay, margin: 4, statuses: [], daysUntilStockout: null },
  })

  it('summarises how much of the plan rests on measured velocity', () => {
    // The screen used to state flatly that there is no sales history. That is
    // false for this store: 1,564 of 7,451 products carry medium or high
    // confidence. A blanket claim in either direction is wrong; the mix is the
    // only honest thing to show.
    const products = [
      withVelocity('a', 12),
      withVelocity('b', 8),
      product({ id: 'c', name: 'פסטה', category: 'משקאות' }),
    ]

    const result = allocateUnit({ unit: gondola, products })

    expect(result.summary.demandConfidence).toEqual({ none: 1, low: 0, medium: 0, high: 2 })
  })

  it('reports all-none when nothing has history', () => {
    const result = allocateUnit({ unit: gondola, products: [product()] })

    expect(result.summary.demandConfidence.none).toBe(1)
    expect(result.summary.demandConfidence.high).toBe(0)
  })

  it('counts only the products actually placed', () => {
    const products = Array.from({ length: 400 }, (_, index) => product({ id: `p${index}` }))

    const result = allocateUnit({ unit: gondola, products })
    const counted = Object.values(result.summary.demandConfidence).reduce((a, b) => a + b, 0)

    expect(counted).toBe(result.summary.placedProducts)
  })
})
