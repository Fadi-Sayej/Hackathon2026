// @vitest-environment node
import { describe, expect, it } from 'vitest'

import { catalogueToProducts, productId, toProduct } from '../catalogueToProducts.js'
import { loadCatalogue, matchesArtefact } from '../loadCatalogue.js'
import { analyzeProducts } from '../../analytics/inventoryEngine.js'
import { formatDays, formatStatus } from '../../../components/shared/formatters.js'
import { createTranslator } from '../../i18n/index.js'

/** A row in the frozen shape of schemas/catalogue.schema.json. */
const row = (over = {}) => ({
  barcode: '7290000000001', product_name: 'חלב 3%', department: 'חלב וביצים',
  shelf_price: 6.9, delivery_price: 7.9, cost_price: 5.2, cost_source: 'pos',
  recorded_stock: 12, has_identifier: true, ...over,
})
const payload = (products) => ({
  schema_version: 1, generated_at: '2026-09-16T02:00:00Z', inputs_digest: 'abc123',
  population: 'living', pos: { as_of: '2026-06-06' },
  count: products === null ? null : products.length, products,
})

describe('catalogueToProducts', () => {
  it('never maps the store\'s own delivery price to competitor data', () => {
    // The tempting mapping, and a false one: delivery_price is wolt_price — this store's own
    // listing. Fed to PriceGapPage as `competitor` it would report the owner undercutting
    // himself as a rival undercutting him.
    const p = toProduct(row({ delivery_price: 4.5 }))
    expect(p.competitor).toBeNull()
    expect(p.deliveryPrice).toBe(4.5)
    expect(JSON.stringify(p)).not.toContain('cheapestCompetitorPrice')
  })

  it('identifies a row with no barcode by name, not by collapsing it (ADR-022)', () => {
    const a = toProduct(row({ barcode: null, product_name: 'לחם' }))
    const b = toProduct(row({ barcode: null, product_name: 'ביצים' }))
    expect(a.id).not.toBe(b.id)
    expect(productId({ barcode: null, product_name: null })).toBeNull()
    expect(toProduct({ barcode: null, product_name: null })).toBeNull()
  })

  it('keeps an absent price absent rather than zero (D-3)', () => {
    const p = toProduct(row({ shelf_price: null, cost_price: null }))
    expect(p.price).toBeNull()
    expect(p.cost).toBeNull()
    expect(toProduct(row({ shelf_price: 0 })).price).toBe(0)
  })

  it('passes negative stock through, and attaches no money to it (D-1)', () => {
    const p = toProduct(row({ recorded_stock: -4 }))
    expect(p.currentStock).toBe(-4)
  })

  it('distinguishes a population that could not load from an empty one', () => {
    expect(catalogueToProducts(payload(null))).toBeNull()
    expect(catalogueToProducts(payload([]))).toEqual([])
  })
})

/**
 * The boundary test (rule 12). The mapping being correct in isolation proves nothing —
 * every one of the four signals that shipped and moved nothing had passing unit tests that
 * supplied the input directly. This drives the real analytics engine over real-shaped rows
 * and reads what the page would actually render.
 */
describe('catalogue rows through the analytics engine', () => {
  const t = createTranslator('he')
  const products = catalogueToProducts(payload([
    row(), row({ barcode: '7290000000002', product_name: 'לחם', shelf_price: 5, cost_price: 6 }),
  ]))
  const analyzed = analyzeProducts(products, {})

  it('reports no velocity verdict, rather than a healthy one', () => {
    for (const p of analyzed) {
      expect(p.analytics.daysUntilStockout).toBeNull()
      expect(p.analytics.primaryStatus).toBe('Not enough sales history yet')
      expect(p.analytics.statuses).not.toContain('Healthy')
      expect(p.analytics.statuses).not.toContain('Slow moving')
    }
  })

  it('renders that to the owner as unknown, in his language', () => {
    const shown = formatDays(analyzed[0].analytics.daysUntilStockout, t)
    expect(shown).not.toBe('No sales')
    expect(shown).toBe(t('days.unknown'))
    expect(formatStatus(analyzed[0].analytics.primaryStatus, t)).toBe(t('status.noVelocityData'))
  })

  it('still computes the margin, which needs no velocity at all', () => {
    expect(analyzed[0].analytics.margin).toBeCloseTo(1.7, 5)
    // Below cost: 5 − 6. Real and worth showing; the catalogue carries both figures.
    expect(analyzed[1].analytics.margin).toBeCloseTo(-1, 5)
  })
})

describe('loadCatalogue', () => {
  const respond = (body, ok = true, status = 200) =>
    () => Promise.resolve({ ok, status, json: () => Promise.resolve(body) })

  it('reads a published catalogue', async () => {
    const out = await loadCatalogue({ fetchImpl: respond(payload([row()])) })
    expect(out.status).toBe('ok')
    expect(out.catalogue.count).toBe(1)
  })

  it('calls a null population absent, not ok and not invalid', async () => {
    const out = await loadCatalogue({ fetchImpl: respond(payload(null)) })
    expect(out.status).toBe('absent')
    expect(out.reason).toMatch(/could not load/)
  })

  it('treats a 404 as unreachable rather than throwing', async () => {
    // The expected state until the first nightly commits one.
    const out = await loadCatalogue({ fetchImpl: respond(null, false, 404) })
    expect(out.status).toBe('unreachable')
    expect(out.catalogue).toBeNull()
  })

  it('refuses a schema version it does not know', async () => {
    const out = await loadCatalogue({ fetchImpl: respond({ ...payload([]), schema_version: 99 }) })
    expect(out.status).toBe('invalid')
  })

  it('never throws on a network failure', async () => {
    const out = await loadCatalogue({ fetchImpl: () => Promise.reject(new Error('offline')) })
    expect(out.status).toBe('unreachable')
    expect(out.reason).toBe('offline')
  })

  it('reports an unknown digest pairing as unknown, not as a mismatch (ADR-017)', () => {
    expect(matchesArtefact({ inputs_digest: 'a' }, { inputs_digest: 'a' })).toBe(true)
    expect(matchesArtefact({ inputs_digest: 'a' }, { inputs_digest: 'b' })).toBe(false)
    expect(matchesArtefact({ inputs_digest: 'a' }, {})).toBeNull()
  })
})
