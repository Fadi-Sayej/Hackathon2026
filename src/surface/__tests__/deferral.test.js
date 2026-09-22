import { describe, expect, it } from 'vitest'
import { nextDayBoundary, settleOutcome } from '../deferral.js'
import { compose } from '../compose.js'

/**
 * #139 — "Later" was a permanent delete.
 *
 * `EntryCard` sent `{ status: 'deferred' }` with no date, `recordOutcome` writes
 * `deferred_until` only when given one, and `compose`'s `isSettled` reads a missing
 * `deferred_until` as *deferred indefinitely*. F6-S1's OQ-604 predicted it in those words:
 * *"Without it, deferral is indistinguishable from permanent dismissal."*
 *
 * Every pre-existing test that touched deferral supplied an explicit `deferred_until`, so
 * the whole suite was green over the button as it actually shipped. These drive the value
 * the surface really produces.
 */

const NOON = new Date(2026, 8, 22, 12, 0, 0).getTime()

describe('nextDayBoundary', () => {
  it('is the next local midnight', () => {
    expect(nextDayBoundary(NOON)).toBe(new Date(2026, 8, 23, 0, 0, 0, 0).getTime())
  })

  it('is strictly after midnight itself, so a deferral made at 00:00 lasts a day', () => {
    const midnight = new Date(2026, 8, 22, 0, 0, 0, 0).getTime()
    expect(nextDayBoundary(midnight)).toBe(new Date(2026, 8, 23, 0, 0, 0, 0).getTime())
  })

  it('crosses a month end', () => {
    const lastDay = new Date(2026, 8, 30, 23, 30, 0).getTime()
    expect(nextDayBoundary(lastDay)).toBe(new Date(2026, 9, 1, 0, 0, 0, 0).getTime())
  })

  it('refuses a time it cannot read rather than returning something plausible', () => {
    expect(() => nextDayBoundary(Number.NaN)).toThrow(/not a time/)
  })
})

describe('settleOutcome', () => {
  it('gives a bare deferral a date', () => {
    expect(settleOutcome({ status: 'deferred' }, { now: NOON }).deferredUntil)
      .toBe(nextDayBoundary(NOON))
  })

  it('leaves an explicit date alone, so a longer deferral stays longer', () => {
    const explicit = { status: 'deferred', deferredUntil: NOON + 7 * 86_400_000 }
    expect(settleOutcome(explicit, { now: NOON })).toEqual(explicit)
  })

  it('does not touch acted or declined', () => {
    for (const status of ['acted', 'declined']) {
      const outcome = { status, reason: null }
      expect(settleOutcome(outcome, { now: NOON })).toBe(outcome)
    }
  })
})

describe('the entry comes back, which is the whole point', () => {
  const entry = {
    id: 'e1', signal_family: 'price.inverted', capability: 'price_consistency',
    barcode: 'b1', product_name: 'p', department: 'd', action: 'verify_price',
    characterisation: 'confirmed_loss', evidence: {}, value: null,
    ordering_key: { name: 'x', value: 1 },
  }
  const artefact = {
    schema_version: 2,
    thresholds: { surface: { bound: 10, unvalued_places: 3, unvalued_order: [] } },
    capabilities: { price_consistency: { status: 'available', unavailable_reason: null, counts: {}, entries: [entry] } },
  }
  const stateWith = (outcome) => ({ outcomes: { e1: outcome }, answers: {} })

  it('is hidden today and present tomorrow', () => {
    const settled = settleOutcome({ status: 'deferred' }, { now: NOON })
    const record = { status: 'deferred', at: NOON, deferred_until: settled.deferredUntil }

    const today = compose(artefact, stateWith(record), { now: NOON })
    expect(today.entries.map((e) => e.id)).toEqual([])

    const tomorrow = compose(artefact, stateWith(record), { now: NOON + 24 * 60 * 60 * 1000 })
    expect(tomorrow.entries.map((e) => e.id)).toEqual(['e1'])
  })

  it('the shape the bug produced is hidden for ever — the regression, stated', () => {
    const dateless = { status: 'deferred', at: NOON }
    for (const now of [NOON, NOON + 24 * 60 * 60 * 1000, NOON + 365 * 24 * 60 * 60 * 1000]) {
      expect(compose(artefact, stateWith(dateless), { now }).entries).toEqual([])
    }
  })
})
