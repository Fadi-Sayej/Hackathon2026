import { describe, expect, it } from 'vitest'

import { credibleGap, credibleLoss } from '../credibility.js'

// Shared credibility guards (#39): the single source of "is this ₪ figure
// defensible?" for the operational action list (actionPriority). The reorder /
// dashboard exposure sort (reorderEngine) shared it until its removal on 2026-09-24.

describe('credibleLoss', () => {
  it('reports a genuine below-cost loss (₪24.90 sold vs ₪30.00 cost)', () => {
    expect(credibleLoss(24.9, 30)).toBeCloseTo(5.1, 5)
  })

  it('withholds a per-case-vs-per-unit data error (בראוניז ₪3.90 vs "cost" ₪238)', () => {
    // 238 / 3.90 ≈ 61x — a cost-price data problem, not a ₪234 loss per brownie.
    expect(credibleLoss(3.9, 238)).toBeNull()
  })

  it('withholds a sub-credible selling price', () => {
    expect(credibleLoss(0.01, 2.28)).toBeNull()
  })

  it('returns null when the product is not selling below cost', () => {
    expect(credibleLoss(10, 8)).toBeNull()
  })

  it('returns null for a zero or missing cost', () => {
    expect(credibleLoss(10, 0)).toBeNull()
    expect(credibleLoss(10, null)).toBeNull()
  })
})

describe('credibleGap', () => {
  it('reports a believable shelf-vs-Wolt gap', () => {
    expect(credibleGap(24.9, 19.9)).toBeCloseTo(5.0, 5)
  })

  it('is order-independent', () => {
    expect(credibleGap(19.9, 24.9)).toBe(credibleGap(24.9, 19.9))
  })

  it('withholds a gap beyond 300% (a unit/pack mismatch)', () => {
    expect(credibleGap(1, 10)).toBeNull() // 900% of the smaller price
  })

  it('withholds when either price is sub-credible', () => {
    expect(credibleGap(0.3, 5)).toBeNull()
  })
})
