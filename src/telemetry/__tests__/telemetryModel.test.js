import { describe, expect, it } from 'vitest'

import { buildTelemetry } from '../telemetryModel.js'
import { ACTION_STATUS, DISMISS_REASON } from '../../lib/operational/completionActions.js'

// The telemetry numbers are what we present to YomYom at the end of the pilot,
// so the aggregation is pinned here. These use the same recommendation shape the
// pipeline emits and the same decision shape persistence stores.

// A believable below-cost sale: ₪24.90 selling, ₪30.00 cost → ₪5.10 loss/unit
// (estimateImpact treats this as a money action worth ₪5.10).
const marginRec = (id) => ({
  id,
  type: 'CHECK_MARGIN',
  productName: 'חלב 3%',
  sellingPrice: 24.9,
  costPrice: 30,
  confidence: 0.9,
})

// A WOLT gap: shelf ₪8.90 vs WOLT ₪12.90 → ₪4.00/unit at stake.
const woltRec = (id) => ({
  id,
  type: 'CHECK_WOLT_PRICE_GAP',
  productName: 'עדשים',
  sellingPrice: 8.9,
  woltPrice: 12.9,
  confidence: 0.95,
})

// A data-hygiene alert with no money attached.
const barcodeRec = (id) => ({ id, type: 'VERIFY_UNKNOWN_BARCODE', productName: 'לא ידוע' })

describe('buildTelemetry', () => {
  it('counts shown split into money and data', () => {
    const t = buildTelemetry([marginRec('m1'), woltRec('w1'), barcodeRec('b1')], {})
    expect(t.totalShown).toBe(3)
    expect(t.totalMoneyShown).toBe(2)
    expect(t.totalDataShown).toBe(1)
  })

  it('with no decisions, everything shown reads as ignored and nothing captured', () => {
    const t = buildTelemetry([marginRec('m1'), woltRec('w1')], {})
    expect(t.actedOn).toBe(0)
    expect(t.ignored).toBe(2)
    expect(t.capturedImpactIls).toBe(0)
    // Potential is the sum of per-unit money at stake: 5.10 + 4.00.
    expect(t.potentialImpactIls).toBeCloseTo(9.1, 5)
  })

  it('captures ₪ impact from decisions marked done, using the recorded impactIls', () => {
    const decisions = {
      m1: { status: ACTION_STATUS.DONE, type: 'CHECK_MARGIN', impactIls: 5.1, decidedAt: '2026-08-07T09:00:00Z' },
    }
    const t = buildTelemetry([marginRec('m1'), woltRec('w1')], decisions)
    expect(t.totalDone).toBe(1)
    expect(t.actedOn).toBe(1)
    expect(t.capturedImpactIls).toBeCloseTo(5.1, 5)
    // 1 done out of 2 shown.
    expect(t.acceptanceRate).toBeCloseTo(0.5, 5)
  })

  it('tracks dismissals and the wrong-data rate — the key credibility metric', () => {
    const decisions = {
      m1: { status: ACTION_STATUS.DISMISSED, reason: DISMISS_REASON.WRONG_DATA, type: 'CHECK_MARGIN' },
      w1: { status: ACTION_STATUS.DISMISSED, reason: DISMISS_REASON.NOT_WORTH_IT, type: 'CHECK_WOLT_PRICE_GAP' },
    }
    const t = buildTelemetry([marginRec('m1'), woltRec('w1')], decisions)
    expect(t.totalDismissed).toBe(2)
    expect(t.wrongDataDismissals).toBe(1)
    expect(t.wrongDataRate).toBeCloseTo(0.5, 5)
    expect(t.reasonCounts[DISMISS_REASON.NOT_WORTH_IT]).toBe(1)
  })

  it('separates engaged acceptance (done ÷ decided) from backlog coverage', () => {
    // 1 done + 1 dismissed out of 3 shown: engaged acceptance is 50%, but
    // coverage of the backlog is only 2/3, and done ÷ shown is only 1/3.
    const decisions = {
      m1: { status: ACTION_STATUS.DONE, type: 'CHECK_MARGIN', impactIls: 5.1 },
      w1: { status: ACTION_STATUS.DISMISSED, reason: DISMISS_REASON.WRONG_DATA, type: 'CHECK_WOLT_PRICE_GAP' },
    }
    const t = buildTelemetry([marginRec('m1'), woltRec('w1'), woltRec('w2')], decisions)
    expect(t.engagedAcceptanceRate).toBeCloseTo(0.5, 5) // 1 done / (1 done + 1 dismissed)
    expect(t.acceptanceRate).toBeCloseTo(1 / 3, 5) // 1 done / 3 shown
    expect(t.coverageRate).toBeCloseTo(2 / 3, 5) // 2 decided / 3 shown
  })

  it('reports acceptance rate per type', () => {
    const decisions = {
      m1: { status: ACTION_STATUS.DONE, type: 'CHECK_MARGIN', impactIls: 5.1 },
      m2: { status: ACTION_STATUS.DISMISSED, reason: DISMISS_REASON.WRONG_DATA, type: 'CHECK_MARGIN' },
    }
    const t = buildTelemetry([marginRec('m1'), marginRec('m2'), woltRec('w1')], decisions)
    const margin = t.typeRows.find((r) => r.type === 'CHECK_MARGIN')
    expect(margin.shown).toBe(2)
    expect(margin.done).toBe(1)
    expect(margin.dismissed).toBe(1)
    expect(margin.acceptanceRate).toBeCloseTo(0.5, 5)
    expect(margin.isMoney).toBe(true)
  })

  it('does not throw on empty / malformed input', () => {
    expect(() => buildTelemetry(undefined, undefined)).not.toThrow()
    const t = buildTelemetry([], {})
    expect(t.totalShown).toBe(0)
    expect(t.acceptanceRate).toBe(0)
  })
})
