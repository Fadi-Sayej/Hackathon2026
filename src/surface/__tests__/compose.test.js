import { describe, expect, it } from 'vitest'
import { compose, deferredEntries, NOT_ON_TODAY, NOT_YET_SHOWN } from '../compose'

const NOW = 1_757_000_000_000

const THRESHOLDS = {
  surface: { bound: 10, unvalued_places: 3, unvalued_order: ['reconciliation', 'competitor_position', 'catalogue_lifecycle', 'hygiene'] },
}

let seq = 0
const entry = (over = {}) => ({
  id: `id${(seq += 1)}`,
  signal_family: 'price.inverted',
  capability: 'price_consistency',
  barcode: `bc${seq}`,
  product_name: `p${seq}`,
  characterisation: 'confirmed_loss',
  evidence: {},
  value: null,
  ordering_key: { name: 'x', value: 1 },
  ...over,
})

const valued = (amount, over = {}) =>
  entry({ value: { amount, kind: 'per_sale', certainty: 'confirmed' }, ...over })

const artefact = (capabilities, thresholds = THRESHOLDS) => ({
  schema_version: 2, thresholds, capabilities,
})

const cap = (entries, over = {}) => ({ status: 'available', unavailable_reason: null, counts: {}, entries, ...over })

const state = (outcomes = {}) => ({ outcomes, answers: {}, revivals: {} })

describe('AC-100 — at most ten entries', () => {
  it('bounds the surface however many candidates exist', () => {
    const many = Array.from({ length: 40 }, (_, i) => valued(100 - i))
    const out = compose(artefact({ price_consistency: cap(many) }), state(), { now: NOW })
    expect(out.entries).toHaveLength(10)
  })

  it('reads the bound from the artefact rather than hard-coding it', () => {
    const many = Array.from({ length: 40 }, (_, i) => valued(100 - i))
    const out = compose(
      artefact({ price_consistency: cap(many) }, { surface: { ...THRESHOLDS.surface, bound: 4 } }),
      state(), { now: NOW })
    expect(out.entries).toHaveLength(4)
  })
})

describe('AC-101 — no count of what is not shown', () => {
  it('returns no backlog, remaining or total field', () => {
    const many = Array.from({ length: 40 }, (_, i) => valued(100 - i))
    const out = compose(artefact({ price_consistency: cap(many) }), state(), { now: NOW })
    const keys = Object.keys(out).join(' ')
    expect(keys).not.toMatch(/remaining|backlog|total|hidden|more/i)
    expect(Object.keys(out).sort()).toEqual(['entries', 'nothingToDo', 'unavailable'])
  })
})

describe('AC-102 / AC-103 — ordering is within a kind, never across kinds', () => {
  it('orders valued entries by descending value', () => {
    const out = compose(artefact({ price_consistency: cap([valued(5), valued(90), valued(40)]) }),
      state(), { now: NOW })
    expect(out.entries.map((e) => e.value.amount)).toEqual([90, 40, 5])
  })

  it('never interleaves two kinds, and emits no cross-kind aggregate', () => {
    // V1's schema permits one kind (per_sale). This constructs a second so the rule is
    // exercised before a second kind exists — D-2 is the rule this project has broken once,
    // and a suite that only ever sees per_sale can never fail it.
    const perSale = valued(10)
    const oneOff = entry({ value: { amount: 900, kind: 'one_off', certainty: 'confirmed' } })
    const out = compose(artefact({ price_consistency: cap([perSale, oneOff]) }), state(), { now: NOW })
    const kinds = out.entries.map((e) => e.value.kind)
    const firstChange = kinds.findIndex((k, i) => i > 0 && k !== kinds[i - 1])
    // each kind occupies one contiguous run: at most one change of kind across the list
    expect(kinds.slice(firstChange === -1 ? kinds.length : firstChange).every((k) => k === kinds[kinds.length - 1])).toBe(true)
    expect(out.summary).toBeUndefined()
  })
})

describe('AC-105 — a recorded outcome removes the entry', () => {
  it('drops an acted entry', () => {
    const e = valued(10)
    const out = compose(artefact({ price_consistency: cap([e]) }),
      state({ [e.id]: { status: 'acted' } }), { now: NOW })
    expect(out.entries).toHaveLength(0)
  })

  it('drops a declined entry', () => {
    const e = valued(10)
    const out = compose(artefact({ price_consistency: cap([e]) }),
      state({ [e.id]: { status: 'declined' } }), { now: NOW })
    expect(out.entries).toHaveLength(0)
  })

  it('hides a deferred entry until its time, then shows it again', () => {
    const e = valued(10)
    const deferred = state({ [e.id]: { status: 'deferred', deferred_until: NOW + 1000 } })
    expect(compose(artefact({ price_consistency: cap([e]) }), deferred, { now: NOW }).entries).toHaveLength(0)
    expect(compose(artefact({ price_consistency: cap([e]) }), deferred, { now: NOW + 2000 }).entries).toHaveLength(1)
  })
})

describe('AC-109 — one product appears once', () => {
  it('keeps the highest-value entry when a product is found twice', () => {
    const a = valued(10, { barcode: 'same' })
    const b = valued(90, { barcode: 'same', capability: 'margin_below_cost' })
    const out = compose(artefact({ price_consistency: cap([a]), competitor_position: cap([b]) }),
      state(), { now: NOW })
    expect(out.entries).toHaveLength(1)
    expect(out.entries[0].value.amount).toBe(90)
  })

  it('does not collapse two entries that merely lack a barcode', () => {
    const out = compose(artefact({ hygiene: cap([entry({ barcode: null }), entry({ barcode: null })]) }),
      state(), { now: NOW })
    expect(out.entries).toHaveLength(2)
  })
})

describe('AC-107 — an unavailable capability is reported, never shown as zero', () => {
  it('lists it with its reason and contributes no entries', () => {
    const out = compose(artefact({
      price_consistency: cap([], { status: 'unavailable', unavailable_reason: 'no_delivery_prices' }),
    }), state(), { now: NOW })
    expect(out.unavailable).toEqual([{ id: 'price_consistency', reason: 'no_delivery_prices' }])
    expect(out.nothingToDo).toBe(false)
  })
})

describe('AC-108 — nothing to do is explicit', () => {
  it('is true only with no entries and no unavailability', () => {
    const out = compose(artefact({ price_consistency: cap([]) }), state(), { now: NOW })
    expect(out.entries).toHaveLength(0)
    expect(out.unavailable).toHaveLength(0)
    expect(out.nothingToDo).toBe(true)
  })

  it('is false when everything was acted on but a capability is unavailable', () => {
    const e = valued(10)
    const out = compose(artefact({
      price_consistency: cap([e]),
      hygiene: cap([], { status: 'unavailable', unavailable_reason: 'no_inventory_data' }),
    }), state({ [e.id]: { status: 'acted' } }), { now: NOW })
    expect(out.nothingToDo).toBe(false)
  })
})

describe('unvalued entries', () => {
  it('reserves at most unvalued_places, in the declared capability order', () => {
    const out = compose(artefact({
      hygiene: cap([entry({ capability: 'hygiene' }), entry({ capability: 'hygiene' })]),
      reconciliation: cap([entry({ capability: 'reconciliation' })]),
      catalogue_lifecycle: cap([entry({ capability: 'catalogue_lifecycle' })]),
    }), state(), { now: NOW })
    expect(out.entries).toHaveLength(3)
    expect(out.entries.map((e) => e.capability)).toEqual(['reconciliation', 'catalogue_lifecycle', 'hygiene'])
  })

  it('puts valued entries ahead of unvalued ones', () => {
    const out = compose(artefact({
      hygiene: cap([entry({ capability: 'hygiene' })]),
      price_consistency: cap([valued(3)]),
    }), state(), { now: NOW })
    expect(out.entries[0].value).not.toBeNull()
  })
})

describe('margin_below_cost is browse-only', () => {
  it('never reaches the surface, however large its value', () => {
    // SPEC-GAP-A: no specification produces it, so it is not admitted until SPEC-008 exists.
    const out = compose(artefact({
      margin_below_cost: cap([valued(9999, { capability: 'margin_below_cost' })]),
    }), state(), { now: NOW })
    expect(out.entries).toHaveLength(0)
    expect(out.nothingToDo).toBe(true)
  })
})

describe('determinism', () => {
  it('returns the same surface for the same inputs', () => {
    const caps = { price_consistency: cap([valued(5), valued(5), valued(9)]) }
    const a = compose(artefact(caps), state(), { now: NOW })
    const b = compose(artefact(caps), state(), { now: NOW })
    expect(a.entries.map((e) => e.id)).toEqual(b.entries.map((e) => e.id))
  })
})

describe('FR-106 — unvalued entries are allocated places, not ranked against valued ones', () => {
  it('reserves places for unvalued entries even when valued ones could fill the bound', () => {
    // The pilot's shape: 53 confirmed losses and a long tail of unvalued work. Without the
    // reservation the owner would never see a reconciliation or hygiene finding (F6-S1 §12).
    const many = Array.from({ length: 40 }, (_, i) => valued(100 - i))
    const chores = [entry({ capability: 'reconciliation' }), entry({ capability: 'hygiene' })]
    const out = compose(artefact({ price_consistency: cap(many), hygiene: cap(chores) }),
      state(), { now: NOW })
    expect(out.entries).toHaveLength(10)
    expect(out.entries.filter((e) => e.value === null)).toHaveLength(2)
    expect(out.entries.filter((e) => e.value !== null)).toHaveLength(8)
  })

  it('gives unused reserved places back to valued entries rather than leaving the surface short', () => {
    const many = Array.from({ length: 40 }, (_, i) => valued(100 - i))
    const out = compose(artefact({ price_consistency: cap(many) }), state(), { now: NOW })
    expect(out.entries).toHaveLength(10)
  })

  it('never gives unvalued entries more than their allocation', () => {
    const chores = Array.from({ length: 9 }, () => entry({ capability: 'hygiene' }))
    const out = compose(artefact({ price_consistency: cap([valued(5)]), hygiene: cap(chores) }),
      state(), { now: NOW })
    expect(out.entries.filter((e) => e.value === null)).toHaveLength(3)
  })
})

describe('Phase 5 Task 5.0 — the F8 capabilities reach no screen before their mockups are approved', () => {
  // All three states a capability can be published in: unavailable with a reason, available
  // with entries (valued and not), and available with none. Each would reach the owner today:
  // an unavailable one as a line on Today, an available one as entries.
  const f8 = () => ({
    order_quantity: cap([], { status: 'unavailable', unavailable_reason: 'no_daily_sales' }),
    market_running_out: cap([entry({ capability: 'market_running_out', signal_family: 'market.running_out' })]),
    market_boost: cap([valued(9, { capability: 'market_boost' })]),
  })

  it('keeps all three F8 ids off Today for good, and the two facts off every screen', () => {
    // FR-160: suggestions live on Reorder. Task 5.13 took order_quantity off NOT_YET_SHOWN;
    // the market signal and the boost are shown only as facts on its cards (approved 2026-09-27).
    expect([...NOT_ON_TODAY].sort()).toEqual(['market_boost', 'market_running_out', 'order_quantity'])
    expect([...NOT_YET_SHOWN].sort()).toEqual(['market_boost', 'market_running_out'])
  })

  it('composes an artefact carrying them exactly as one without them', () => {
    const base = {
      price_consistency: cap([valued(5)]),
      reconciliation: cap([entry({ capability: 'reconciliation' })]),
      hygiene: cap([], { status: 'unavailable', unavailable_reason: 'no_catalogue' }),
    }
    const without = compose(artefact(base), state(), { now: NOW })
    const carrying = compose(artefact({ ...base, ...f8() }), state(), { now: NOW })
    expect(carrying).toEqual(without)
  })

  it('does not name an unavailable one, and does not call the day empty because of one', () => {
    const out = compose(artefact(f8()), state(), { now: NOW })
    expect(out).toEqual({ entries: [], unavailable: [], nothingToDo: true })
  })

  it('does not offer one of their entries back as hidden', () => {
    const caps = f8()
    const id = caps.market_running_out.entries[0].id
    const hidden = deferredEntries(artefact(caps),
      state({ [id]: { status: 'deferred', at: NOW - 1 } }), { now: NOW })
    expect(hidden).toEqual([])
  })
})
