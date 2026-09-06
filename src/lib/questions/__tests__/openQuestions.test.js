import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  MAX_QUESTIONS_ON_SCREEN,
  QUESTION_CARRIED,
  QUESTION_SHELF_LIFE,
  buildOpenQuestions,
  topQuestions,
} from '../openQuestions.js'
import { applyGroupDecision, proposeSimilarProducts } from '../proposeGroup.js'
import { clearAnswers, loadAnswers, saveAnswer, summariseChange, toYaml } from '../answerStore.js'

const shelfLife = {
  categories: { 'מחלקת -barista': 2, 'משקאות': 180, 'כל הסיגריות': null },
  defaultDays: null,
}

const products = [
  { id: 'a', barcode: '1', name: 'קרואסון', category: 'מחלקת -barista', availabilityState: 'STOCKOUT_SUSPECTED' },
  { id: 'b', barcode: '2', name: 'בורקס', category: 'מחלקת -barista', availabilityState: 'AVAILABLE' },
  { id: 'c', barcode: '3', name: 'קולה', category: 'משקאות', availabilityState: 'AVAILABLE' },
  { id: 'd', barcode: '4', name: 'מרלבורו', category: 'כל הסיגריות', availabilityState: 'STOCKOUT_SUSPECTED' },
]
const recs = [
  { type: 'REORDER', productId: 'a', valueAtStake: 300 },
  { type: 'REORDER', productId: 'd', valueAtStake: 50 },
]

describe('what the system asks', () => {
  it('asks whether a STOCKOUT_SUSPECTED product is still carried', () => {
    const qs = buildOpenQuestions(products, recs, { shelfLife, ownerAnswers: {} })
    const carried = qs.filter((q) => q.type === QUESTION_CARRIED)
    expect(carried.map((q) => q.productId).sort()).toEqual(['a', 'd'])
  })

  it('never asks shelf life for a category marked non-perishable', () => {
    const qs = buildOpenQuestions(products, recs, { shelfLife, ownerAnswers: {} })
    const asked = qs.filter((q) => q.type === QUESTION_SHELF_LIFE).map((q) => q.category)
    expect(asked).not.toContain('כל הסיגריות')
  })

  it('asks once per category, not once per product', () => {
    const qs = buildOpenQuestions(products, recs, { shelfLife, ownerAnswers: {} })
    const bakery = qs.filter((q) => q.type === QUESTION_SHELF_LIFE && q.category === 'מחלקת -barista')
    expect(bakery).toHaveLength(1)
  })

  it('never asks something already answered', () => {
    const answered = { carried: { 1: { answer: 'no' } }, shelfLifeCategories: { 'מחלקת -barista': { days: 3 } } }
    const qs = buildOpenQuestions(products, recs, { shelfLife, ownerAnswers: answered })
    expect(qs.find((q) => q.id === 'carried:1')).toBeUndefined()
    expect(qs.find((q) => q.id === 'shelf_life:מחלקת -barista')).toBeUndefined()
  })
})

describe('ranking and the three-question limit', () => {
  it('shows at most three questions', () => {
    const many = Array.from({ length: 20 }, (_, i) => ({
      id: `p${i}`, barcode: `b${i}`, name: `product ${i}`,
      category: `cat${i}`, availabilityState: 'STOCKOUT_SUSPECTED',
    }))
    const qs = buildOpenQuestions(many, [], { shelfLife, ownerAnswers: {} })
    expect(topQuestions(qs).length).toBeLessThanOrEqual(MAX_QUESTIONS_ON_SCREEN)
  })

  it('ranks a high-value question above a low-value one', () => {
    const qs = buildOpenQuestions(products, recs, { shelfLife, ownerAnswers: {} })
    const carried = qs.filter((q) => q.type === QUESTION_CARRIED)
    expect(carried[0].productId).toBe('a') // 300 at stake beats 50
  })

  it('lets a category answer outrank a single-product answer of the same value', () => {
    const qs = buildOpenQuestions(products, recs, { shelfLife, ownerAnswers: {} })
    const shelf = qs.find((q) => q.type === QUESTION_SHELF_LIFE)
    const carried = qs.find((q) => q.type === QUESTION_CARRIED && q.productId === 'a')
    // Same seed product and value, but the shelf-life answer settles the whole category.
    expect(shelf.score).toBeGreaterThan(carried.score)
  })
})

describe('grouping proposes, the owner decides', () => {
  it('falls back to the category field when the model is off', () => {
    const proposal = proposeSimilarProducts(products[0], products, { modelEnabled: false })
    expect(proposal.source).toBe('category')
    expect(proposal.products.map((p) => p.id)).toEqual(['b'])
  })

  it('always exposes the full list so the group can be rejected', () => {
    const proposal = proposeSimilarProducts(products[0], products, { modelEnabled: false })
    expect(proposal.products.length).toBe(proposal.totalCandidates)
  })

  it('applies to the whole category only on confirmation', () => {
    const proposal = proposeSimilarProducts(products[0], products, { modelEnabled: false })
    const answer = { type: 'shelf_life', productId: 'a', value: 3 }
    expect(applyGroupDecision(answer, proposal, true).scope).toBe('category')
    expect(applyGroupDecision(answer, proposal, false).scope).toBe('product')
    expect(applyGroupDecision(answer, proposal, false).productIds).toEqual(['a'])
  })
})

// Minimal in-memory localStorage: the suite runs in the node environment, matching
// the existing persistence tests (src/lib/persistence/__tests__/reconcile.test.js).
function installFakeLocalStorage() {
  const store = new Map()
  globalThis.localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
    clear: () => store.clear(),
  }
}

describe('answers persist beyond the browser', () => {
  beforeEach(() => {
    installFakeLocalStorage()
    clearAnswers()
  })
  afterEach(() => {
    delete globalThis.localStorage
  })

  it('records a carried answer and reads it back', () => {
    saveAnswer({ type: 'carried', barcode: '1', value: 'no' })
    expect(loadAnswers().carried['1'].answer).toBe('no')
  })

  it('records a category shelf life when a group was confirmed', () => {
    saveAnswer({ type: 'shelf_life', scope: 'category', category: 'מחלקת -barista', value: 3, confirmedProducts: 47 })
    expect(loadAnswers().shelfLifeCategories['מחלקת -barista'].days).toBe(3)
  })

  it('exports YAML the Python pipeline can load', () => {
    saveAnswer({ type: 'carried', barcode: '1', value: 'seasonal' })
    saveAnswer({ type: 'shelf_life', barcode: '2', value: 5 })
    const yaml = toYaml(loadAnswers())
    expect(yaml).toContain("carried:")
    expect(yaml).toContain("'1': { answer: 'seasonal'")
    expect(yaml).toContain("shelf_life_days:")
    expect(yaml).toContain("'2': { days: 5")
  })

  it('merges what the pipeline already published under local answers', () => {
    saveAnswer({ type: 'carried', barcode: '1', value: 'yes' })
    const merged = loadAnswers({ carried: { 9: { answer: 'no' } } })
    expect(merged.carried['9'].answer).toBe('no')
    expect(merged.carried['1'].answer).toBe('yes')
  })
})

describe('showing what changed', () => {
  it('counts orders removed, added and changed', () => {
    const before = [
      { productId: 'a', recommendedOrderQuantity: 50 },
      { productId: 'b', recommendedOrderQuantity: 10 },
    ]
    const after = [
      { productId: 'b', recommendedOrderQuantity: 16 },
      { productId: 'c', recommendedOrderQuantity: 4 },
    ]
    expect(summariseChange(before, after)).toMatchObject({
      ordersRemoved: 1, ordersAdded: 1, quantitiesChanged: 1,
    })
  })

  it('reports no change honestly rather than inventing one', () => {
    const same = [{ productId: 'a', recommendedOrderQuantity: 5 }]
    expect(summariseChange(same, same)).toMatchObject({
      ordersRemoved: 0, ordersAdded: 0, quantitiesChanged: 0,
    })
  })
})
