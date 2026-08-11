import { describe, expect, it } from 'vitest'

import {
  MIN_AFFINITY,
  OUR_STORE_TYPE,
  affinityForEntry,
  canDriveRecommendation,
  comparableStores,
  formatAffinity,
  isNeverComparable,
  partitionByFormat,
  storeTypeOf,
} from '../storeFormat.js'
import {
  analyzeLocalMarket,
  getCompetitorDemandBoost,
  selectPriceProtectionAlerts,
  summarizeCompetitorIntelligence,
} from '../competitorEngine.js'
import { buildLocalMarketSnapshot } from '../../dataAdapters/multiCompetitorAdapter.js'
import { generateReorderRecommendations } from '../reorderEngine.js'
import { RECOMMENDATION_TYPES } from '../recommendationTypes.js'

const BARCODE = '7290000000001'

function competitorStore(overrides = {}) {
  return {
    brand: 'Test',
    storeName: 'Test store',
    storeId: 'dor-alon-kq-01',
    distance_m: 1400,
    snapshot: { [BARCODE]: { price: 8, isAvailable: true } },
    ...overrides,
  }
}

function product(overrides = {}) {
  return {
    id: 'p-1',
    barcode: BARCODE,
    name: 'Test product',
    category: 'Grocery',
    currentStock: 10,
    shelfQuantity: 5,
    salesLast7Days: 0,
    salesLast30Days: 0,
    leadTimeDays: 3,
    price: 12,
    cost: 6,
    velocityConfidence: 'none',
    ...overrides,
  }
}

describe('store format affinity', () => {
  it('anchors on YomYom being a forecourt shop', () => {
    expect(OUR_STORE_TYPE).toBe('gas_convenience')
    expect(storeTypeOf('yomyom-kq-01')).toBe('gas_convenience')
  })

  it('never compares a hypermarket to a forecourt shop', () => {
    expect(formatAffinity('gas_convenience', 'hypermarket')).toBe(0)
    expect(isNeverComparable({ storeId: 'shufersal-pt-01' })).toBe(true)
  })

  it('rates the forecourt shop down the road above the supermarket', () => {
    expect(affinityForEntry({ storeId: 'dor-alon-kq-01' })).toBeGreaterThan(
      affinityForEntry({ storeId: 'rami-levy-pt-01' }),
    )
  })

  it('treats an unclassified store as unknown rather than a perfect match', () => {
    expect(storeTypeOf('some-branch-we-never-saw')).toBe('unknown')
    expect(affinityForEntry({ storeId: 'some-branch-we-never-saw' })).toBeLessThan(MIN_AFFINITY)
    expect(canDriveRecommendation({ storeId: 'some-branch-we-never-saw' })).toBe(false)
  })

  it('splits entries into comparable, context-only and excluded', () => {
    const { comparable, contextOnly, excluded } = partitionByFormat([
      { storeId: 'dor-alon-kq-01' },   // gas_convenience → 1.0
      { storeId: 'rami-levy-pt-01' },  // supermarket     → 0.1
      { storeId: 'shufersal-pt-01' },  // hypermarket     → 0.0
    ])
    expect(comparable.map((e) => e.storeId)).toEqual(['dor-alon-kq-01'])
    expect(contextOnly.map((e) => e.storeId)).toEqual(['rami-levy-pt-01'])
    expect(excluded.map((e) => e.storeId)).toEqual(['shufersal-pt-01'])
  })

  it('lists comparable stores most comparable first, never a zero', () => {
    const stores = comparableStores()
    expect(stores.length).toBeGreaterThan(0)
    expect(stores).not.toContain('shufersal-pt-01')
    const affinities = stores.map((id) => formatAffinity(OUR_STORE_TYPE, storeTypeOf(id)))
    expect(affinities).toEqual([...affinities].sort((a, b) => b - a))
  })
})

describe('competitorEngine store-format enforcement', () => {
  it('ignores a hypermarket price entirely when pricing a forecourt shop', () => {
    const snapshot = buildLocalMarketSnapshot([
      competitorStore({
        storeId: 'shufersal-pt-01',
        distance_m: 1800,
        snapshot: { [BARCODE]: { price: 4, isAvailable: true } },
      }),
    ])
    const [enriched] = analyzeLocalMarket([product()], snapshot)

    expect(enriched.competitor.cheapestCompetitorPrice).toBeNull()
    expect(enriched.competitor.nearbyCompetitors).toBe(0)
    expect(enriched.competitor.excludedByFormat).toBe(1)
    expect(enriched.competitor.excludedStoreTypes).toEqual(['hypermarket'])
  })

  it('still uses the forecourt shop next door', () => {
    const snapshot = buildLocalMarketSnapshot([competitorStore()])
    const [enriched] = analyzeLocalMarket([product()], snapshot)

    expect(enriched.competitor.cheapestCompetitorPrice).toBe(8)
    expect(enriched.competitor.priceAffinity).toBe(1)
    expect(enriched.competitor.priceStoreType).toBe('gas_convenience')
  })

  it('keeps a barely-comparable format as context but not as a price basis', () => {
    const snapshot = buildLocalMarketSnapshot([
      competitorStore({ storeId: 'rami-levy-pt-01', distance_m: 2100 }),
    ])
    const [enriched] = analyzeLocalMarket([product()], snapshot)

    expect(enriched.competitor.contextOnlyCompetitors).toBe(1)
    expect(enriched.competitor.cheapestCompetitorPrice).toBeNull()
    expect(enriched.competitor.excludedByFormat).toBe(0)
  })

  it('does not let a hypermarket stockout inflate demand', () => {
    const snapshot = buildLocalMarketSnapshot([
      competitorStore({
        storeId: 'shufersal-pt-01',
        distance_m: 1800,
        snapshot: { [BARCODE]: { price: 4, isAvailable: false } },
      }),
    ])
    expect(getCompetitorDemandBoost(BARCODE, snapshot)).toBe(1.0)
  })

  it('widens the price-protection threshold as the format gets less comparable', () => {
    // 30% cheaper — well past the 15% bar for a same-format store.
    const priceSnapshot = { [BARCODE]: { price: 8.4, isAvailable: true } }

    const sameFormat = analyzeLocalMarket(
      [product()],
      buildLocalMarketSnapshot([competitorStore({ snapshot: priceSnapshot })]),
    )
    expect(selectPriceProtectionAlerts(sameFormat)).toHaveLength(1)

    // Same 30% gap from a mid-size grocery (affinity 0.3) needs 50% to fire.
    const distantFormat = analyzeLocalMarket(
      [product()],
      buildLocalMarketSnapshot([
        competitorStore({ storeId: '6576d161608e6c09be0c0e54', snapshot: priceSnapshot }),
      ]),
    )
    expect(selectPriceProtectionAlerts(distantFormat)).toHaveLength(0)
  })

  it('counts products silenced by the format filter separately from no-data', () => {
    const snapshot = buildLocalMarketSnapshot([
      competitorStore({ storeId: 'shufersal-pt-01', distance_m: 1800 }),
    ])
    const enriched = analyzeLocalMarket([product()], snapshot)
    const summary = summarizeCompetitorIntelligence(enriched)

    expect(summary.productsWithCoverage).toBe(0)
    expect(summary.productsExcludedByFormat).toBe(1)
  })
})

describe('acceptance: no affinity-0.0 source ever reaches a recommendation', () => {
  it('produces no PRICE_GAP from a hypermarket, however large the gap', () => {
    const snapshot = buildLocalMarketSnapshot([
      competitorStore({
        storeId: 'shufersal-pt-01',
        distance_m: 1800,
        // A 24-pack price a forecourt shop could never match.
        snapshot: { [BARCODE]: { price: 1.5, isAvailable: true } },
      }),
    ])
    const [enriched] = analyzeLocalMarket([product()], snapshot)
    const recommendations = generateReorderRecommendations([enriched], {}, '2026-08-12')

    expect(
      recommendations.filter((r) => r.type === RECOMMENDATION_TYPES.PRICE_GAP),
    ).toHaveLength(0)
  })

  it('does produce one when the same gap comes from a comparable format', () => {
    const snapshot = buildLocalMarketSnapshot([
      competitorStore({ snapshot: { [BARCODE]: { price: 1.5, isAvailable: true } } }),
    ])
    const [enriched] = analyzeLocalMarket([product()], snapshot)
    const recommendations = generateReorderRecommendations([enriched], {}, '2026-08-12')

    expect(
      recommendations.filter((r) => r.type === RECOMMENDATION_TYPES.PRICE_GAP),
    ).toHaveLength(1)
  })

  it('holds when a comparable and an excluded source disagree', () => {
    // The forecourt shop is 8. The big box is 1.5. The recommendation must be
    // built on 8 — the cheaper number is real, but it is not our market.
    const snapshot = buildLocalMarketSnapshot([
      competitorStore(),
      competitorStore({
        storeId: 'shufersal-pt-01',
        distance_m: 1800,
        snapshot: { [BARCODE]: { price: 1.5, isAvailable: true } },
      }),
    ])
    const [enriched] = analyzeLocalMarket([product()], snapshot)

    expect(enriched.competitor.cheapestCompetitorPrice).toBe(8)

    const priceGap = generateReorderRecommendations([enriched], {}, '2026-08-12').find(
      (r) => r.type === RECOMMENDATION_TYPES.PRICE_GAP,
    )
    expect(priceGap.competitorPrice).toBe(8)
    expect(priceGap.competitorStoreType).toBe('gas_convenience')
    expect(priceGap.competitorFormatAffinity).toBe(1)
  })
})
