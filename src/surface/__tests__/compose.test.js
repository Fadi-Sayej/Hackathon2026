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
    for (const id of ['market_boost', 'market_running_out', 'order_quantity']) expect(NOT_ON_TODAY.has(id)).toBe(true)
    for (const id of ['market_boost', 'market_running_out']) expect(NOT_YET_SHOWN.has(id)).toBe(true)
    expect(NOT_YET_SHOWN.has('order_quantity')).toBe(false)
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

describe('Phase 8 — the F12 capabilities are never on Today, and only their pages show them', () => {
  // F12-S1 FR-192: never on Today. Task 8.9 (the mockups approved 2026-10-05) took layout_facts and
  // shelf_plan off NOT_YET_SHOWN: Store layout and Shelf plan render them whole, and Data names them.
  // The measurement and the explanation stay on it, shown only inside Shelf plan. Each state a
  // capability can be published in: unavailable with a reason, and available with entries.
  const f12 = () => ({
    layout_facts: cap([], { status: 'unavailable', unavailable_reason: 'no_store_layout' }),
    shelf_plan: cap([entry({ capability: 'shelf_plan', signal_family: 'shelf.plan', barcode: null })]),
    shelf_measurement: cap([], { status: 'unavailable', unavailable_reason: 'no_arrangement_recorded' }),
    shelf_explanation: cap([], { status: 'unavailable', unavailable_reason: 'no_model_key' }),
  })

  it('keeps every F12 id off Today for good, and the two parts of Shelf plan off every other screen', () => {
    for (const id of Object.keys(f12())) expect(NOT_ON_TODAY.has(id)).toBe(true)
    expect([...NOT_ON_TODAY].sort()).toEqual(['layout_facts', 'market_boost', 'market_running_out',
      'order_quantity', 'shelf_explanation', 'shelf_measurement', 'shelf_plan'])
    expect([...NOT_YET_SHOWN].sort()).toEqual(['market_boost', 'market_running_out',
      'shelf_explanation', 'shelf_measurement'])
  })

  it('composes an artefact carrying them exactly as one without them', () => {
    const base = {
      price_consistency: cap([valued(5)]),
      reconciliation: cap([entry({ capability: 'reconciliation' })]),
      hygiene: cap([], { status: 'unavailable', unavailable_reason: 'no_catalogue' }),
    }
    const without = compose(artefact(base), state(), { now: NOW })
    const carrying = compose(artefact({ ...base, ...f12() }), state(), { now: NOW })
    expect(carrying).toEqual(without)
  })

  it('does not name an unavailable one, and does not call the day empty because of one', () => {
    expect(compose(artefact(f12()), state(), { now: NOW })).toEqual({ entries: [], unavailable: [], nothingToDo: true })
  })

  it('does not offer a plan back as hidden', () => {
    const caps = f12()
    const id = caps.shelf_plan.entries[0].id
    const hidden = deferredEntries(artefact(caps), state({ [id]: { status: 'deferred', at: NOW - 1 } }), { now: NOW })
    expect(hidden).toEqual([])
  })
})

// ── Phase 6 Task 6.3: F9-S1 FR-171, FR-172 (F6-S1 FR-106a), FR-175 ───────────────────────────
//
// The two surface mechanisms are pinned here on a stand-in capability, through the same
// published policy lines, so they hold for any capability policy names. AC-167 below pins
// them with assortment_gap itself.

const recon = (n) => Array.from({ length: n }, (_, i) => entry({ id: `r${i}`, capability: 'reconciliation' }))
const stand = (ids) => ids.map((id) => entry({ id, capability: 'competitor_position' }))
const WITH_CAP = {
  surface: {
    bound: 10, unvalued_places: 3,
    unvalued_order: ['competitor_position', 'reconciliation', 'catalogue_lifecycle', 'hygiene'],
    unvalued_caps: { competitor_position: 1 },
    engine_ordered: ['competitor_position'],
  },
}

describe('FR-171 — a capped capability takes at most its cap, first in the order', () => {
  it('gives the capped capability one place and the next in the order the rest', () => {
    const out = compose(artefact({ competitor_position: cap(stand(['c1', 'c2', 'c3'])), reconciliation: cap(recon(5)) },
      WITH_CAP), state(), { now: NOW })
    expect(out.entries.map((e) => e.capability)).toEqual(['competitor_position', 'reconciliation', 'reconciliation'])
  })

  it('does not hold places it was refused: they fall back to valued entries', () => {
    const many = Array.from({ length: 20 }, (_, i) => valued(100 - i))
    const out = compose(artefact({ price_consistency: cap(many), competitor_position: cap(stand(['c1', 'c2', 'c3'])) },
      WITH_CAP), state(), { now: NOW })
    expect(out.entries).toHaveLength(10)
    expect(out.entries.filter((e) => e.value === null)).toHaveLength(1)
  })

  it('without a cap, still gives each kind one place per round (D-26)', () => {
    const caps = { competitor_position: cap(stand(['c1', 'c2', 'c3'])), reconciliation: cap(recon(5)) }
    const uncapped = { surface: { ...WITH_CAP.surface, unvalued_caps: undefined } }
    const out = compose(artefact(caps, uncapped), state(), { now: NOW })
    expect(out.entries.map((e) => e.capability)).toEqual(['competitor_position', 'reconciliation', 'competitor_position'])
  })
})

describe('FR-172 / F6-S1 FR-106a — the surface keeps the published order where policy says so', () => {
  it('shows the first entry the engine published, not the smallest id', () => {
    const out = compose(artefact({ competitor_position: cap(stand(['z9', 'a1', 'm5'])) }, WITH_CAP), state(), { now: NOW })
    expect(out.entries[0].id).toBe('z9')
  })

  it('still orders every other capability by id, until that is changed on its own', () => {
    const shuffled = [entry({ id: 'r9', capability: 'reconciliation' }), entry({ id: 'r1', capability: 'reconciliation' })]
    const out = compose(artefact({ reconciliation: cap(shuffled) }, WITH_CAP), state(), { now: NOW })
    expect(out.entries.map((e) => e.id)).toEqual(['r1', 'r9'])
  })

  it('skips a settled entry and shows the next one in the published order', () => {
    const out = compose(artefact({ competitor_position: cap(stand(['z9', 'm5', 'a1'])) }, WITH_CAP),
      state({ z9: { status: 'declined', at: NOW - 1 } }), { now: NOW })
    expect(out.entries[0].id).toBe('m5')
  })
})

describe('AC-167 — F9 on Today: one place, the first, in the engine\'s order', () => {
  // The policy lines exactly as configs/policy.yaml publishes them (pinned there by test_policy).
  const F9_POLICY = { surface: { ...THRESHOLDS.surface,
    unvalued_order: ['assortment_gap', ...THRESHOLDS.surface.unvalued_order],
    unvalued_caps: { assortment_gap: 1 }, engine_ordered: ['assortment_gap'] } }
  const gaps = (ids) => ids.map((id) => entry({ id, capability: 'assortment_gap', signal_family: 'assortment.market_ran_out' }))

  it('shows exactly one F9 entry, first, and reconciliation keeps the other two places', () => {
    const out = compose(artefact({ assortment_gap: cap(gaps(['g9', 'g1', 'g5'])), reconciliation: cap(recon(355)) }, F9_POLICY),
      state(), { now: NOW })
    expect(out.entries.map((e) => e.capability)).toEqual(['assortment_gap', 'reconciliation', 'reconciliation'])
    expect(out.entries[0].id).toBe('g9')                    // the engine's first, not the smallest id
  })

  it('lets reconciliation have all three on a day with no F9 finding', () => {
    const out = compose(artefact({ assortment_gap: cap([]), reconciliation: cap(recon(355)) }, F9_POLICY), state(), { now: NOW })
    expect(out.entries.map((e) => e.capability)).toEqual(['reconciliation', 'reconciliation', 'reconciliation'])
  })

  it('names it on Today when unavailable, like any capability (AC-107)', () => {
    const out = compose(artefact({ assortment_gap: cap([], { status: 'unavailable', unavailable_reason: 'market_signal_stale' }) }, F9_POLICY),
      state(), { now: NOW })
    expect(out.unavailable).toEqual([{ id: 'assortment_gap', reason: 'market_signal_stale' }])
  })
})

describe('F2-S1 FR-024 on Today — reconciliation, biggest gap first (the owner, 2026-09-29)', () => {
  // The policy lines as configs/policy.yaml publishes them (pinned there by test_policy).
  const POLICY = { surface: { ...THRESHOLDS.surface,
    unvalued_order: ['assortment_gap', ...THRESHOLDS.surface.unvalued_order],
    unvalued_caps: { assortment_gap: 1 }, engine_ordered: ['assortment_gap', 'reconciliation'] } }
  // Published by the engine in gap-ratio order, with ids that sort the other way round.
  const byGap = [['z-melon', 6.39], ['m-yogurt', 4.38], ['c-strawberry', 2.25], ['a-bamba', 0.47]]
    .map(([id, ratio]) => entry({ id, capability: 'reconciliation', ordering_key: { name: 'gap_ratio', value: ratio } }))

  it('shows the biggest gaps, not the smallest ids', () => {
    const out = compose(artefact({ reconciliation: cap(byGap) }, POLICY), state(), { now: NOW })
    expect(out.entries.map((e) => e.id)).toEqual(['z-melon', 'm-yogurt', 'c-strawberry'])
  })

  it('keeps the F9 place first and gives reconciliation its two biggest', () => {
    const f9 = cap([entry({ id: 'g1', capability: 'assortment_gap', signal_family: 'assortment.market_ran_out' })])
    const out = compose(artefact({ assortment_gap: f9, reconciliation: cap(byGap) }, POLICY), state(), { now: NOW })
    expect(out.entries.map((e) => e.id)).toEqual(['g1', 'z-melon', 'm-yogurt'])
  })

  it('moves to the next biggest once one is answered', () => {
    const out = compose(artefact({ reconciliation: cap(byGap) }, POLICY),
      state({ 'z-melon': { status: 'acted', at: NOW - 1 } }), { now: NOW })
    expect(out.entries[0].id).toBe('m-yogurt')
  })
})

describe('D-26 — the places without ₪ take turns', () => {
  // The policy lines as configs/policy.yaml publishes them (pinned there by test_policy).
  const KINDS = ['reconciliation', 'competitor_position', 'catalogue_lifecycle', 'hygiene']
  const POLICY = { surface: { bound: 10, unvalued_places: 3, unvalued_order: ['assortment_gap', ...KINDS],
    unvalued_caps: { assortment_gap: 1 }, engine_ordered: ['assortment_gap', ...KINDS], rotate: KINDS } }
  const many = (capability, n) => Array.from({ length: n }, (_, i) => entry({ id: `${capability}-${i}`, capability }))
  const all = () => ({
    assortment_gap: cap(many('assortment_gap', 3)), reconciliation: cap(many('reconciliation', 355)),
    competitor_position: cap(many('competitor_position', 7)), catalogue_lifecycle: cap(many('catalogue_lifecycle', 50)),
    hygiene: cap(many('hygiene', 50)),
  })
  // The rotation follows the date the artefact was generated (the nightly), not the device's clock.
  const onDay = (caps, day) => ({ ...artefact(caps, POLICY), generated_at: `${day}T03:52:33+00:00` })
  const kinds = (out) => out.entries.map((e) => e.capability)
  const days = ['2026-09-29', '2026-09-30', '2026-10-01', '2026-10-02']

  it('keeps F9 first every day, and gives two other kinds one place each', () => {
    for (const day of days) {
      const k = kinds(compose(onDay(all(), day), state(), { now: NOW }))
      expect(k[0], day).toBe('assortment_gap')
      expect(new Set(k.slice(1)).size, day).toBe(2)
    }
  })

  it('puts every kind on Today twice in four days', () => {
    const seen = Object.fromEntries(KINDS.map((k) => [k, 0]))
    for (const day of days) for (const k of kinds(compose(onDay(all(), day), state(), { now: NOW })).slice(1)) seen[k] += 1
    expect(seen).toEqual({ reconciliation: 2, competitor_position: 2, catalogue_lifecycle: 2, hygiene: 2 })
  })

  it('moves the pair along by one kind a day', () => {
    const pairs = days.map((day) => kinds(compose(onDay(all(), day), state(), { now: NOW })).slice(1))
    for (let i = 1; i < pairs.length; i += 1) expect(pairs[i][0], days[i]).toBe(pairs[i - 1][1])
  })

  it('is the same on every device: it reads the artefact\'s date, not the clock', () => {
    const a = compose(onDay(all(), '2026-09-30'), state(), { now: NOW })
    const b = compose(onDay(all(), '2026-09-30'), state(), { now: NOW + 5 * 86_400_000 })
    expect(kinds(a)).toEqual(kinds(b))
  })

  it('shows each kind\'s most important entry, in the order the engine published', () => {
    for (const day of days) {
      for (const e of compose(onDay(all(), day), state(), { now: NOW }).entries) expect(e.id.endsWith('-0'), e.id).toBe(true)
    }
  })

  it('passes a kind with nothing to do to the next one', () => {
    const caps = { ...all(), competitor_position: cap([]) }
    for (const day of days) {
      const k = kinds(compose(onDay(caps, day), state(), { now: NOW }))
      expect(k, day).toHaveLength(3)
      expect(k, day).not.toContain('competitor_position')
      expect(new Set(k.slice(1)).size, day).toBe(2)
    }
  })

  it('gives a kind a second place only when no other kind has work', () => {
    const caps = { assortment_gap: cap(many('assortment_gap', 3)), reconciliation: cap(many('reconciliation', 355)) }
    expect(kinds(compose(onDay(caps, '2026-09-29'), state(), { now: NOW }))).toEqual(['assortment_gap', 'reconciliation', 'reconciliation'])
  })
})

