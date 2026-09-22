// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { compose, deferredEntries } from '../compose.js'

const NOW = 1_700_000_000_000
const DAY = 86_400_000

const entry = (id, over = {}) => ({
  id, signal_family: 'price.inverted', product_name: `p-${id}`, barcode: `b-${id}`,
  value: { amount: 4, kind: 'per_sale', certainty: 'confirmed' }, ...over,
})
const artefact = (entries) => ({
  thresholds: { surface: { bound: 10, unvalued_places: 3, unvalued_order: [] } },
  capabilities: { price_consistency: { status: 'available', entries } },
})
const state = (outcomes) => ({ outcomes })

describe('deferredEntries', () => {
  it('returns what a dateless deferral is hiding — the #139 case', () => {
    // "Later" before #142 sent no date, and compose reads a missing deferred_until as
    // indefinite. Nothing else in the app could name what had been lost that way.
    const out = deferredEntries(
      artefact([entry('a'), entry('b')]),
      state({ a: { status: 'deferred', at: NOW - 5 * DAY } }),
      { now: NOW },
    )
    expect(out).toHaveLength(1)
    expect(out[0].entry.id).toBe('a')
    expect(out[0].until).toBeNull()
    expect(out[0].at).toBe(NOW - 5 * DAY)
  })

  it('leaves a deferral that has lapsed alone — compose is already showing it', () => {
    const out = deferredEntries(
      artefact([entry('a')]),
      state({ a: { status: 'deferred', at: NOW - 2 * DAY, deferred_until: NOW - DAY } }),
      { now: NOW },
    )
    expect(out).toEqual([])
    // ...and prove the premise rather than assume it.
    const shown = compose(artefact([entry('a')]),
      state({ a: { status: 'deferred', at: NOW - 2 * DAY, deferred_until: NOW - DAY } }),
      { now: NOW })
    expect(shown.entries.map((e) => e.id)).toEqual(['a'])
  })

  it('holds a deferral that has not lapsed yet', () => {
    const out = deferredEntries(artefact([entry('a')]),
      state({ a: { status: 'deferred', at: NOW, deferred_until: NOW + DAY } }), { now: NOW })
    expect(out).toHaveLength(1)
    expect(out[0].until).toBe(NOW + DAY)
  })

  it('offers back only deferrals, never acted or declined', () => {
    // A deferral is a decision about WHEN. Acted and declined are decisions about the thing,
    // and re-offering them would be second-guessing the owner rather than helping him.
    const out = deferredEntries(
      artefact([entry('a'), entry('b'), entry('c')]),
      state({
        a: { status: 'acted', at: NOW },
        b: { status: 'declined', at: NOW, reason: 'not_worth_it' },
        c: { status: 'deferred', at: NOW },
      }),
      { now: NOW },
    )
    expect(out.map((d) => d.entry.id)).toEqual(['c'])
  })

  it('puts the longest-hidden first', () => {
    const out = deferredEntries(
      artefact([entry('new'), entry('old')]),
      state({
        new: { status: 'deferred', at: NOW - DAY },
        old: { status: 'deferred', at: NOW - 30 * DAY },
      }),
      { now: NOW },
    )
    expect(out.map((d) => d.entry.id)).toEqual(['old', 'new'])
  })

  it('does not reach into a capability that could not run', () => {
    const broken = {
      thresholds: { surface: { bound: 10 } },
      capabilities: { price_consistency: { status: 'unavailable', unavailable_reason: 'pos', entries: [] } },
    }
    expect(deferredEntries(broken, state({ a: { status: 'deferred', at: NOW } }), { now: NOW })).toEqual([])
  })

  it('is NOT part of compose’s return, which AC-101 locks', () => {
    // FR-101: the ten-item bound exists to make the day finishable, and a count of what is
    // not shown undoes it. FR-102 puts this list on another surface instead — which is why
    // it is a separate export rather than a field.
    const out = compose(artefact([entry('a')]), state({ a: { status: 'deferred', at: NOW } }), { now: NOW })
    expect(Object.keys(out).sort()).toEqual(['entries', 'nothingToDo', 'unavailable'])
  })

  it('survives a missing artefact or owner state rather than throwing', () => {
    expect(deferredEntries(null, null, { now: NOW })).toEqual([])
    expect(deferredEntries(artefact([entry('a')]), null, { now: NOW })).toEqual([])
  })
})
