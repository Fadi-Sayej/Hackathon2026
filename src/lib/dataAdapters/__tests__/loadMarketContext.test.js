import { describe, expect, it } from 'vitest'
import { toEngineContext } from '../loadMarketContext.js'
import { computeMetrics } from '../../analytics/reorderEngine.js'

/**
 * The adapter is the boundary between the committed artifact and the engine.
 * Every other test hands computeMetrics a context it built itself, so a field
 * dropped HERE is invisible to all of them — which is exactly what happened: the
 * shelf-life cap worked in tests and was silently off in the running app, ordering
 * 51 croissants instead of 16.
 */
const artifact = {
  date: '2026-09-07',
  status: 'ok',
  weather: { label: 'warm', temperatureC: 28 },
  hebrew: { holidays: [], chametz: null },
  islamic: { phase: null },
  demandSignals: { 'משקאות': 1.2 },
  shelfLife: { categories: { 'מחלקת -barista': 2 }, defaultDays: null },
  ownerAnswers: { carried: { 123: { answer: 'no' } }, shelfLifeDays: {}, shelfLifeCategories: {} },
}

const fallback = { weather: 'hot', demandSignals: {} }

describe('artifact fields survive the crossing into engine context', () => {
  it.each([
    ['demandSignals', (c) => c.demandSignals?.['משקאות']],
    ['shelfLife', (c) => c.shelfLife?.categories?.['מחלקת -barista']],
    ['ownerAnswers', (c) => c.ownerAnswers?.carried?.['123']?.answer],
  ])('carries %s through', (_name, read) => {
    expect(read(toEngineContext(artifact, fallback))).toBeTruthy()
  })

  it('applies the shelf-life cap through the real adapter, not just a hand-built context', () => {
    const croissant = {
      id: 'x', name: 'קרואסון', category: 'מחלקת -barista', price: 11, cost: 5.5,
      currentStock: 0, salesLast7Days: 0, salesLast30Days: 0,
      demandPerDayCorrected: 8.38, demandConfidence: 'medium',
      leadTimeDays: 3, leadTimeSource: 'default', isStocked: true,
    }
    const metrics = computeMetrics(croissant, toEngineContext(artifact, fallback))
    expect(metrics.shelfLifeCapped).toBe(true)
    expect(metrics.recommendedOrder).toBe(16)   // not the uncapped 51
  })

  it('falls back cleanly when the artifact is absent', () => {
    expect(toEngineContext(null, fallback)).toBe(fallback)
  })
})
