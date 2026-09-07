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

describe('competitor data adjusts the rate, never gates the decision', () => {
  const artifactWithStockout = {
    ...artifact,
    competitorStockouts: { status: 'ok', days: 27, lift: 1.15, barcodes: ['777'] },
  }
  const base = {
    id: 'p', name: 'חלב', category: 'מוצרי מקרר', price: 7, cost: 4,
    currentStock: 2, salesLast7Days: 0, salesLast30Days: 0,
    demandPerDayCorrected: 4, demandConfidence: 'high',
    leadTimeDays: 3, leadTimeSource: 'default', isStocked: true,
  }

  it('lifts the rate when the surrounding branches are out of it', () => {
    const ctx = toEngineContext(artifactWithStockout, fallback)
    const withLift = computeMetrics({ ...base, barcode: '777' }, ctx)
    const without = computeMetrics({ ...base, barcode: '999' }, ctx)
    expect(withLift.competitorLift).toBe(1.15)
    expect(without.competitorLift).toBe(1)
    expect(withLift.dailyRate).toBeGreaterThan(without.dailyRate)
  })

  it('still recommends a product no competitor sells at all', () => {
    // The regression this whole change exists to prevent: no competitor match
    // must never mean no reorder.
    const ctx = toEngineContext({ ...artifact, competitorStockouts: null }, fallback)
    const metrics = computeMetrics({ ...base, barcode: 'unmatched', currentStock: 0 }, ctx)
    expect(metrics.competitorLift).toBe(1)
    expect(metrics.recommendedOrder).toBeGreaterThan(0)
  })

  it('ignores a lift when history is too short to classify', () => {
    const ctx = toEngineContext(
      { ...artifact, competitorStockouts: { status: 'insufficient_history', days: 1, barcodes: [], lift: 1.15 } },
      fallback,
    )
    expect(computeMetrics({ ...base, barcode: '777' }, ctx).competitorLift).toBe(1)
  })
})
