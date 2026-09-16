// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

import { artefactToOperational } from '../artefactToOperational.js'
import { estimateImpact, rankActions } from '../../analytics/actionPriority.js'

/**
 * Run against the COMMITTED artefact, not a fixture.
 *
 * The whole point of this adapter is that the restored pages read what the nightly actually
 * publishes. A hand-written fixture would pass while the real shape drifted — which is how
 * the pre-cut-over pipeline shipped `competitorSignals: 0` for a month with every test green.
 */
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..')
const artefact = JSON.parse(readFileSync(resolve(ROOT, 'public/data/dashboard.json'), 'utf8'))

describe('artefactToOperational', () => {
  const out = artefactToOperational(artefact)

  it('produces the four fields the old pages actually read', () => {
    expect(Object.keys(out)).toEqual(
      expect.arrayContaining(['meta', 'posHealth', 'recommendations', 'sources']),
    )
    expect(out.recommendations.length).toBeGreaterThan(0)
  })

  it('carries every finding the engine published, under an old type', () => {
    // Families the old UI has no type for are dropped deliberately, not silently: this
    // asserts the ones that DO map are all present, so a new family added upstream and not
    // mapped here shows up as a count change rather than as a quiet absence.
    const mapped = artefact.capabilities.price_consistency.entries.length
      + artefact.capabilities.margin_below_cost.entries.length
      + artefact.capabilities.reconciliation.entries.length
      + artefact.capabilities.hygiene.entries.length
    expect(out.recommendations.length).toBe(mapped)
  })

  it('states no shekel figure on a quantity-derived finding (D-1)', () => {
    // The old ranker prices CHECK_STOCK_DISCREPANCY as metricValue * costPrice. Over the
    // frozen operational.json that was 458 findings summing to ₪103,828.75. D-1 forbids a
    // shekel figure on a signal derived from stock the manager says is unreliable, and the
    // engine agrees: all reconciliation entries publish value: null.
    const stock = out.recommendations.filter((r) => r.type === 'CHECK_STOCK_DISCREPANCY')
    expect(stock.length).toBeGreaterThan(0)
    for (const rec of stock) {
      expect(rec.costPrice).toBeNull()
      expect(estimateImpact(rec)).toBeNull()
    }
    const negative = out.recommendations.filter((r) => r.type === 'CHECK_NEGATIVE_STOCK')
    for (const rec of negative) expect(estimateImpact(rec)).toBeNull()
  })

  it('still surfaces the finding whose price it withholds', () => {
    // D-1 removes the number, not the work. The owner must still see the product.
    const stock = out.recommendations.filter((r) => r.type === 'CHECK_STOCK_DISCREPANCY')
    expect(stock.length).toBe(artefact.capabilities.reconciliation.entries.length)
    expect(stock.every((r) => r.metricValue !== null)).toBe(true)
  })

  it('keeps a real price where the engine published one', () => {
    const priced = out.recommendations.filter((r) => r.type === 'CHECK_WOLT_PRICE_GAP')
    expect(priced.length).toBeGreaterThan(0)
    expect(priced.some((r) => r.sellingPrice !== null && r.woltPrice !== null)).toBe(true)
  })

  it('reads posHealth from the engine counts, so the header cannot drift', () => {
    const h = artefact.capabilities.hygiene.counts
    expect(out.posHealth.negativeStock).toBe(h.negative_stock)
    expect(out.posHealth.missingBarcode).toBe(h.no_identifier)
    expect(out.posHealth.zeroPrice).toBe(h.absent_price)
    expect(out.posHealth.sourceFile).toBe(artefact.vintages.pos.file)
  })

  it('carries unavailability, which the old shape had no way to express', () => {
    expect(Array.isArray(out.meta.unavailable)).toBe(true)
    // Every capability the engine could not run is named, with its reason.
    const expected = Object.entries(artefact.capabilities)
      .filter(([, c]) => c.status === 'unavailable').length
    expect(out.meta.unavailable.length).toBe(expected)
  })

  it('leaves expiry absent rather than zeroed', () => {
    // The engine publishes no expiry capability. A confident set of zero alerts would read
    // as "nothing expiring", which is a claim the artefact cannot support.
    expect(out.expiry).toBeNull()
  })

  it('carries the vintage source, which the old strip never showed', () => {
    const pos = out.sources.find((s) => s.source_id === 'yomyom_pos')
    expect(pos.last_updated).toBe(artefact.vintages.pos.as_of)
    expect(pos.as_of_source).toBe(artefact.vintages.pos.as_of_source)
  })

  it('survives the old ranker without throwing, and ranks money above data', () => {
    const { money, data } = rankActions(out.recommendations)
    expect(money.length + data.length).toBe(out.recommendations.length)
    // Nothing quantity-derived may reach the money column.
    for (const rec of money) {
      expect(['CHECK_STOCK_DISCREPANCY', 'CHECK_NEGATIVE_STOCK']).not.toContain(rec.type)
    }
  })

  it('returns null for a missing artefact rather than an empty-looking one', () => {
    expect(artefactToOperational(null)).toBeNull()
  })
})

/**
 * The degraded run, which the committed artefact cannot demonstrate because everything in it
 * is available today.
 *
 * This is the seam that produced two defects already: a guard placed correctly upstream and
 * flattened one layer down. `inventoryEngine` emitted `daysUntilStockout: null` and the
 * formatter printed "No sales"; `run.py` isolated the catalogue step and the workflow's
 * `git add` undid it. Here the engine marks a capability `unavailable` and a `?? 0` turned
 * that into a count of zero — which AC-107 exists to forbid, because zero findings and
 * "could not look" are indistinguishable once the number is written.
 */
describe('artefactToOperational when capabilities did not run', () => {
  const degraded = {
    generated_at: '2026-09-16T02:00:00Z',
    run: { status: 'partial' },
    population: 'living',
    // competitor_position absent entirely, so its figures are gone with it.
    figures: {},
    vintages: { pos: { file: 'yomyom-inventory.csv', as_of: '2026-06-06' } },
    capabilities: {
      hygiene: { status: 'unavailable', unavailable_reason: 'pos input missing', entries: [] },
    },
  }
  const out = artefactToOperational(degraded)

  it('states no product count rather than zero products', () => {
    // "0 products from the POS export" for a 7,523-product catalogue, because the figure
    // that carries the count declares inputs ['pos', 'competitor'] and the scrape failed.
    expect(out.posHealth.totalProducts).toBeNull()
    expect(out.posHealth.totalProducts).not.toBe(0)
  })

  it('states no hygiene counts rather than a clean bill of health', () => {
    // 0 negative-stock and 0 missing-barcode reads as a tidy catalogue. It means the check
    // never ran.
    expect(out.posHealth.negativeStock).toBeNull()
    expect(out.posHealth.missingBarcode).toBeNull()
    expect(out.posHealth.zeroPrice).toBeNull()
  })

  it('still names which capability could not run, with its reason', () => {
    expect(out.meta.unavailable).toEqual([{ id: 'hygiene', reason: 'pos input missing' }])
  })

  it('keeps real counts real when the capability did run', () => {
    // The guard must not swing the other way and null out healthy figures.
    const healthy = artefactToOperational(artefact)
    expect(healthy.posHealth.negativeStock).toBe(artefact.capabilities.hygiene.counts.negative_stock)
    expect(typeof healthy.posHealth.totalProducts).toBe('number')
  })
})
