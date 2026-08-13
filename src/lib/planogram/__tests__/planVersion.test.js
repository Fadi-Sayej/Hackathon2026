import { beforeEach, describe, expect, it } from 'vitest'

import { approvePlan, loadApprovedPlan, planStability, toPlanVersion } from '../planVersion.js'

/**
 * Roadmap §4.5. Without an approved version the plan silently changes under the
 * manager's feet on every render, and no outcome can ever be attributed to it.
 */

const plan = (items = []) => ({
  shelves: [{ code: 'الرف ١', shelfLevel: 'EYE_LEVEL', runCm: 100, usedCm: 40, items }],
  summary: { placedProducts: items.length, totalFacings: items.reduce((n, i) => n + i.facings, 0) },
})

const position = (id, facings = 2) => ({
  productId: id,
  productName: `منتج ${id}`,
  facings,
  widthCm: 10,
  onShelf: 20,
})

beforeEach(() => {
  globalThis.localStorage?.clear?.()
})

describe('version record', () => {
  it('captures the fixture and the placements, not the rendering', () => {
    const version = toPlanVersion({
      unit: { id: 'g1', name: 'ممر ١' },
      category: 'משקאות',
      plan: plan([position('a')]),
    })

    expect(version.fixtureId).toBe('g1')
    expect(version.category).toBe('משקאות')
    expect(version.placements).toEqual([
      { shelfCode: 'الرف ١', shelfLevel: 'EYE_LEVEL', productId: 'a', facings: 2 },
    ])
  })

  it('stamps a creation time so two versions can be ordered', () => {
    const version = toPlanVersion({ unit: { id: 'g1' }, category: 'c', plan: plan() })

    expect(Date.parse(version.createdAt)).not.toBeNaN()
  })

  it('starts as a draft — approving is a separate, deliberate act', () => {
    const version = toPlanVersion({ unit: { id: 'g1' }, category: 'c', plan: plan() })

    expect(version.status).toBe('draft')
  })
})

describe('stability against the approved plan', () => {
  it('reports nothing changed when the placements match', () => {
    const approved = toPlanVersion({ unit: { id: 'g1' }, category: 'c', plan: plan([position('a')]) })

    expect(planStability(plan([position('a')]), approved).changedPositions).toBe(0)
  })

  it('counts a changed facing count as one change', () => {
    const approved = toPlanVersion({ unit: { id: 'g1' }, category: 'c', plan: plan([position('a', 2)]) })

    expect(planStability(plan([position('a', 5)]), approved).changedPositions).toBe(1)
  })

  it('counts an added and a removed product as two changes', () => {
    const approved = toPlanVersion({ unit: { id: 'g1' }, category: 'c', plan: plan([position('a')]) })

    expect(planStability(plan([position('b')]), approved).changedPositions).toBe(2)
  })

  it('lists the moves so the manager sees the work, not just a number', () => {
    const approved = toPlanVersion({ unit: { id: 'g1' }, category: 'c', plan: plan([position('a', 2)]) })

    const { moves } = planStability(plan([position('a', 4)]), approved)

    expect(moves).toEqual([
      { productId: 'a', productName: 'منتج a', kind: 'facings', from: 2, to: 4 },
    ])
  })

  it('has no opinion when no plan has been approved yet', () => {
    expect(planStability(plan([position('a')]), null).changedPositions).toBeNull()
  })
})

describe('approval round trip', () => {
  it('reads back the plan that was approved', () => {
    const version = toPlanVersion({ unit: { id: 'g1' }, category: 'משקאות', plan: plan([position('a')]) })

    approvePlan(version)

    const loaded = loadApprovedPlan('g1', 'משקאות')
    expect(loaded.placements).toEqual(version.placements)
    expect(loaded.status).toBe('approved')
  })

  it('keeps approvals for different categories on the same fixture apart', () => {
    approvePlan(toPlanVersion({ unit: { id: 'g1' }, category: 'a', plan: plan([position('x')]) }))
    approvePlan(toPlanVersion({ unit: { id: 'g1' }, category: 'b', plan: plan([position('y')]) }))

    expect(loadApprovedPlan('g1', 'a').placements[0].productId).toBe('x')
    expect(loadApprovedPlan('g1', 'b').placements[0].productId).toBe('y')
  })

  it('returns null when nothing has been approved for that fixture', () => {
    expect(loadApprovedPlan('never-approved', 'c')).toBeNull()
  })
})
