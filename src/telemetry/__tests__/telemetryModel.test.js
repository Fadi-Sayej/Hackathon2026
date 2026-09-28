import { describe, expect, it } from 'vitest'

import { viewMeasurement } from '../telemetryModel.js'

/**
 * F13-S1 (Phase 4 Task 4.5). The engine computes the measurement (ADR-023); this model only
 * shapes the published file for display. Every number below is one the file carries, or a
 * share of two counts from the same set of decisions.
 */

const counts = (over = {}) => ({ shown: 0, decided: 0, acted: 0, declined: 0, deferred: 0, not_in_this_run: 0, ...over })

// public/data/measurement.json, as the engine writes it (schemas/measurement.schema.json).
const file = (body, over = {}) => ({
  schema_version: 1,
  generated_at: '2026-09-27T03:06:40Z',
  run_id: 'abc',
  inputs_digest: 'd',
  devices: { status: 'available', reason: null, count: 4, last_seen_at: [] },
  ...body,
  ...over,
})

const ready = (over = {}) => ({
  status: 'available',
  unavailable_reason: null,
  window: { first: '2026-09-16T11:05:30Z', last: '2026-09-24T10:03:00Z', pulled_at: '2026-09-27T03:06:42Z' },
  totals: counts({ shown: 120, decided: 5, acted: 3, declined: 1, deferred: 1, not_in_this_run: 1 }),
  by_family: {
    'hygiene.negative_stock': counts({ shown: 100, decided: 1, declined: 1 }),
    'price.inverted': counts({ shown: 20, decided: 4, acted: 3, deferred: 1, not_in_this_run: 1 }),
  },
  money: [
    { kind: 'per_sale', certainty: 'confirmed', amount: 5.75, decisions: 2 },
    { kind: 'per_sale', certainty: 'estimated', amount: 2, decisions: 1 },
  ],
  declined_reasons: { wrong_data: 1 },
  ...over,
})

describe('what the page can say', () => {
  it('says the measurement was not published, when there is no file yet', () => {
    expect(viewMeasurement(null).state).toBe('missing')
  })

  it('says it is unavailable, with its reason, and carries no count (FR-142)', () => {
    const view = viewMeasurement(file({ status: 'unavailable', unavailable_reason: 'pull_failed: RuntimeError',
      window: { first: null, last: null, pulled_at: null } }))
    expect(view).toMatchObject({ state: 'unavailable', reason: 'pull_failed: RuntimeError' })
    expect(view.totals).toBeUndefined()
  })
})

describe('a published measurement', () => {
  it('carries the totals as published, and the share acted on within the decisions only', () => {
    const view = viewMeasurement(file(ready()))
    expect(view.state).toBe('ready')
    expect(view.totals).toEqual(ready().totals)
    expect(view.actedShare).toBe(0.6)
    expect(view.generatedAt).toBe('2026-09-27T03:06:40Z')
    expect(view.devices).toBe(4)
  })

  it('has no share, not 0%, when nothing is decided (INV-068)', () => {
    const view = viewMeasurement(file(ready({ totals: counts({ shown: 120 }), by_family: {}, money: [], declined_reasons: {} })))
    expect(view.nothingDecided).toBe(true)
    expect(view.actedShare).toBeNull()
    expect(view.wrongDataShare).toBeNull()
  })

  it('lists the families by what this run shows, with each one\'s share of its own decisions', () => {
    const view = viewMeasurement(file(ready()))
    expect(view.families.map((f) => f.family)).toEqual(['hygiene.negative_stock', 'price.inverted'])
    expect(view.families[1]).toMatchObject({ acted: 3, notInThisRun: 1, actedShare: 0.75 })
  })

  it('keeps each money row as published: never summed across kinds or certainties (FR-139)', () => {
    const view = viewMeasurement(file(ready()))
    expect(view.money).toEqual([
      { kind: 'per_sale', certainty: 'confirmed', amount: 5.75, decisions: 2 },
      { kind: 'per_sale', certainty: 'estimated', amount: 2, decisions: 1 },
    ])
  })

  it('lists every dismissal reason, with the wrong-data share of the dismissals', () => {
    const view = viewMeasurement(file(ready({ declined_reasons: { wrong_data: 1, none: 1 },
      totals: counts({ decided: 2, declined: 2 }) })))
    expect(view.reasons.map((r) => [r.reason, r.count])).toEqual([
      ['wrong_data', 1], ['not_worth_it', 0], ['already_handled', 0], ['none', 1]])
    expect(view.wrongDataShare).toBe(0.5)
  })

  it('omits the device count when it is not published, rather than saying 0', () => {
    expect(viewMeasurement(file(ready(), { devices: null })).devices).toBeNull()
  })
})
