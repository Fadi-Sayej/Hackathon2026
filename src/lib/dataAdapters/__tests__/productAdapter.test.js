import { describe, expect, it } from 'vitest'

import { normalizeProducts } from '../productAdapter.js'

describe('duplicate product ids', () => {
  // The YomYom export carries the same sandwich in two departments at two
  // prices. Both rows are real. `id` was derived from barcode-or-name alone, so
  // they collided, and every consumer that indexes by id — `productIndex`, React
  // keys, approved plans — silently kept whichever row came last. Measured on
  // the real catalogue: 83 rows lost, 68 of the collisions holding genuinely
  // different prices or costs. One of those wrong rows is what builds a purchase
  // order's unit cost.
  const row = (overrides = {}) => ({
    id: 'ym-כריך רוסטביף',
    name: 'כריך רוסטביף',
    category: 'מחלקת -barista',
    currentStock: 5,
    price: 24.9,
    cost: 10,
    salesLast7Days: 0,
    salesLast30Days: 0,
    ...overrides,
  })

  it('never emits the same id twice', () => {
    const { products } = normalizeProducts([
      row(),
      row({ category: 'מחלקת drive', price: 28.9 }),
    ])

    const ids = products.map((product) => product.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('keeps every row rather than dropping the collision', () => {
    const { products } = normalizeProducts([
      row(),
      row({ category: 'מחלקת drive', price: 28.9 }),
      row({ category: 'מחלקת drive', price: 30 }),
    ])

    expect(products).toHaveLength(3)
    expect(products.map((product) => product.price).sort((a, b) => a - b)).toEqual([24.9, 28.9, 30])
  })

  it('disambiguates with the department, because that is what actually differs', () => {
    const { products } = normalizeProducts([row(), row({ category: 'מחלקת drive' })])

    expect(products[0].id).toBe('ym-כריך רוסטביף')
    expect(products[1].id).toContain('מחלקת drive')
  })

  it('is stable: the same input always yields the same ids', () => {
    const input = [row(), row({ category: 'מחלקת drive' })]
    const first = normalizeProducts(input).products.map((product) => product.id)
    const second = normalizeProducts(input).products.map((product) => product.id)

    // Approved plans and reorder decisions are keyed by product id. An id that
    // shuffles between loads silently detaches every saved decision.
    expect(second).toEqual(first)
  })

  it('reports the collision instead of hiding it', () => {
    const { issues } = normalizeProducts([row(), row({ category: 'מחלקת drive' })])

    expect(issues.some((issue) => issue.field === 'id')).toBe(true)
  })

  it('leaves a catalogue with unique ids completely untouched', () => {
    const { products, issues } = normalizeProducts([
      row(),
      row({ id: 'ym-2', name: 'מים', category: 'משקאות' }),
    ])

    expect(products.map((product) => product.id)).toEqual(['ym-כריך רוסטביף', 'ym-2'])
    expect(issues.filter((issue) => issue.field === 'id')).toEqual([])
  })
})
