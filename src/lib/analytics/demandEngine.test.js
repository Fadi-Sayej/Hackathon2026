import { describe, expect, it } from 'vitest'
import { chametzWindow } from '../context/hebcal.js'
import { getIslamicContext, ramadanPhase, toHijri } from '../context/hijri.js'
import { combineFamily, computeDemand, gateMayFire } from './demandEngine.js'

// Minimal stand-ins for configs/market_params.yaml and configs/archetypes.yaml.
// Fixtures, not production data — the engine must be testable without a classified
// catalogue or any API key.
const registry = {
  clamp: [0.2, 3.0],
  families: {
    weather: {
      weight: 1.0,
      params: [
        { id: 'temp_max_c', type: 'multiplier', active: true },
        { id: 'season', type: 'multiplier', active: true },
        { id: 'wind_speed_kmh', type: 'multiplier', active: false },
      ],
    },
    calendar_islamic: {
      weight: 1.0,
      params: [
        { id: 'ramadan_iftar', type: 'multiplier', active: true },
        { id: 'ramadan_daytime', type: 'multiplier', active: true },
      ],
    },
  },
  gates: {
    pesach_chametz_window: { requiresFlag: 'is_chametz', requiresHumanReview: true },
  },
}

const archetypes = {
  water_bottle: { sensitivities: { temp_max_c: 1.45, season: 1.4, ramadan_iftar: 1.55 } },
  chametz_snack: { sensitivities: { temp_max_c: 1.05, ramadan_daytime: 0.4 } },
  unclassified: { sensitivities: {} },
}

const product = { id: 'p1', name: 'מים מינרלים 1.5 ליטר' }

describe('composition rule 1 — group within a family before multiplying across', () => {
  it('does not count the same fact twice', () => {
    // temp_max_c and season both say "summer". Multiplied naively that is
    // 1.45 * 1.4 = 2.03; grouped it is their weighted geometric mean.
    const grouped = combineFamily([{ value: 1.45 }, { value: 1.4 }])
    expect(grouped).toBeLessThan(1.45 * 1.4)
    expect(grouped).toBeGreaterThan(1.4)
  })

  it('a single strong factor is not diluted by neutral siblings', () => {
    expect(combineFamily([{ value: 1.6 }])).toBeCloseTo(1.6, 5)
  })
})

describe('composition rule 2 — neutral 1.0, absent factors vanish', () => {
  it('an uncollected parameter changes nothing', () => {
    const withNothing = computeDemand({ product, profile: { archetype: 'water_bottle' }, archetypes, registry, factors: {} })
    expect(withNothing.demandIndex).toBe(1)
    expect(withNothing.topDrivers).toHaveLength(0)
  })

  it('an inactive parameter is skipped even when a factor is supplied', () => {
    const result = computeDemand({
      product, profile: { archetype: 'water_bottle' }, archetypes, registry,
      factors: { wind_speed_kmh: { value: 1 } },
    })
    expect(result.demandIndex).toBe(1)
  })

  it('an unclassified product is inert — we know nothing, so we claim nothing', () => {
    const result = computeDemand({
      product, profile: null, archetypes, registry,
      factors: { temp_max_c: { value: 1 }, season: { value: 1 } },
    })
    expect(result.archetype).toBe('unclassified')
    expect(result.demandIndex).toBe(1)
  })
})

describe('composition rule 3 — hard clamp', () => {
  it('no combination of mild multipliers escapes the ceiling', () => {
    const greedy = {
      clamp: [0.2, 3.0],
      families: Object.fromEntries(
        Array.from({ length: 12 }, (_, i) => [
          `f${i}`, { weight: 3, params: [{ id: 'temp_max_c', type: 'multiplier', active: true }] },
        ]),
      ),
      gates: {},
    }
    const result = computeDemand({
      product, profile: { archetype: 'water_bottle' }, archetypes,
      registry: greedy, factors: { temp_max_c: { value: 1 } },
    })
    expect(result.demandIndex).toBeLessThanOrEqual(3.0)
    expect(result.clamped).toBe(true)
  })
})

describe('composition rule 4 — gates evaluate last and override everything', () => {
  const reviewed = { archetype: 'chametz_snack', flags: { is_chametz: true }, reviewedBy: 'anas' }

  it('a fired BLOCK zeroes demand however favourable the factors', () => {
    const result = computeDemand({
      product, profile: reviewed, archetypes, registry,
      factors: {
        temp_max_c: { value: 1 },
        pesach_chametz_window: { active: true, action: 'BLOCK', reason: 'אסור למכירה' },
      },
    })
    expect(result.demandIndex).toBe(0)
    expect(result.blocked.gate).toBe('pesach_chametz_window')
  })

  it('an unreviewed profile cannot fire a gate — a wrong call is a forbidden sale', () => {
    const unreviewed = { archetype: 'chametz_snack', flags: { is_chametz: true }, reviewedBy: null }
    expect(gateMayFire(registry.gates.pesach_chametz_window, unreviewed)).toBe(false)

    const result = computeDemand({
      product, profile: unreviewed, archetypes, registry,
      factors: { pesach_chametz_window: { active: true, action: 'BLOCK' } },
    })
    expect(result.demandIndex).not.toBe(0)
    expect(result.gatesEvaluated[0].status).toBe('awaiting_human_review')
  })

  it('a product without the flag is untouched by the gate', () => {
    const water = { archetype: 'water_bottle', flags: {}, reviewedBy: 'anas' }
    const result = computeDemand({
      product, profile: water, archetypes, registry,
      factors: { pesach_chametz_window: { active: true, action: 'BLOCK' } },
    })
    expect(result.demandIndex).toBe(1)
    expect(result.gatesEvaluated[0].status).toBe('not_applicable')
  })
})

describe('contribution attribution', () => {
  it('reports which factors moved the number, strongest first', () => {
    const result = computeDemand({
      product, profile: { archetype: 'water_bottle' }, archetypes, registry,
      factors: {
        temp_max_c: { value: 1, label: '36°C' },
        ramadan_iftar: { value: 0.5 },
      },
    })
    expect(result.demandIndex).toBeGreaterThan(1)
    expect(result.topDrivers[0].param).toBe('temp_max_c')
    expect(result.topDrivers[0].label).toBe('36°C')
    expect(result.topDrivers.every((d) => d.effect > 0)).toBe(true)
  })

  it('suppression is reported as a negative contribution', () => {
    const result = computeDemand({
      product, profile: { archetype: 'chametz_snack' }, archetypes, registry,
      factors: { ramadan_daytime: { value: 1 } },
    })
    expect(result.demandIndex).toBeLessThan(1)
    expect(result.topDrivers[0].effect).toBeLessThan(0)
  })
})

describe('hebcal — chametz windows', () => {
  const pesach = '2027-04-22' // verified live against the Hebcal API

  it('is silent outside the run-up', () => {
    expect(chametzWindow('2027-03-01', pesach)).toBeNull()
    expect(chametzWindow('2027-05-05', pesach)).toBeNull()
  })

  it('stops reorders about a month out', () => {
    expect(chametzWindow('2027-03-25', pesach).action).toBe('STOP_REORDER')
  })

  it('switches to clearing stock two weeks out', () => {
    expect(chametzWindow('2027-04-10', pesach).action).toBe('CLEAR_STOCK')
  })

  it('blocks during the festival itself', () => {
    expect(chametzWindow('2027-04-23', pesach).action).toBe('BLOCK')
  })
})

describe('hijri — no API, no key', () => {
  it('converts a Gregorian date to the Hijri calendar', () => {
    const h = toHijri('2027-02-10')
    expect(h.month).toBe(9) // Ramadan
    expect(h.year).toBe(1448)
  })

  it('detects Ramadan and counts down to it otherwise', () => {
    expect(getIslamicContext('2027-02-10', { hour: 12 }).isRamadan).toBe(true)
    const outside = getIslamicContext('2026-08-12', { hour: 12 })
    expect(outside.isRamadan).toBe(false)
    expect(outside.daysToRamadan).toBeGreaterThan(0)
  })

  it('splits the fasting day into phases that move demand differently', () => {
    expect(ramadanPhase(4)).toBe('suhoor')
    expect(ramadanPhase(12)).toBe('daytime')
    expect(ramadanPhase(21)).toBe('iftar')
  })
})
