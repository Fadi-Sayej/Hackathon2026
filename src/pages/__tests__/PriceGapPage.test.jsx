/** @vitest-environment jsdom */
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, within } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { PriceGapPage } from '../PriceGapPage.jsx'

/**
 * The Prices page, built on `capabilities.competitor_position.comparison` (ADR-025) and named
 * from `catalogue.json` (ADR-024). Laid out as the owner approved it on 2026-09-23: three
 * tabs, the engine's own percentage, a flag on a finding, a reason on every product that has
 * no comparison, 25 rows at a time.
 *
 * Every figure here is one the engine published. The page sorts and groups rows; it computes
 * no price, no gap and no verdict (ADR-001).
 */

const NOW = Date.UTC(2026, 8, 23, 12, 0)            // 2026-09-23, the day of the run below

/** Text without the bidi isolates formatShekel and formatDate wrap figures in. */
const plain = (el) => (el?.textContent ?? '').replace(/[⁦-⁩]/g, '').replace(/\s+/g, ' ').trim()

const compared = (barcode, shelf, reference, premium, stores, seen, reason = null) => ({
  barcode, shelf_price: shelf, stores, observed_at: seen,
  reference: { value: reference, kind: 'supermarket_plus_allowance', same_format: null, supermarket: reference, allowance_pct: 7.5 },
  premium_pct: premium, uncompared_reason: reason,
})
const uncompared = (barcode, shelf, stores, seen, reason) => ({
  barcode, shelf_price: shelf, stores, observed_at: seen, reference: null, premium_pct: null, uncompared_reason: reason,
})

const NAMES = {
  7290017888729: 'שופס סודה ליטר',
  7290000000011: 'קפסולות בטעם ונילה',
  7290000000028: 'חלב 3% ליטר',
  7290000000035: 'לחם אחיד',
  7290002331360: 'נביעות 500 מ"ל TO GO',
  7290000000042: 'אטריות בינונים',
  7290000000059: 'חטיף נייצר ואלי שבולת',
  7290000000066: "קולה 330 מ''ל",
  305210464728: 'ממתק ישן',
}

function fixture(overrides = {}) {
  const comparison = overrides.comparison ?? [
    compared('7290017888729', 9.9, 5.5906, 77.08, 118, '2026-09-23'),          // dearer, and a finding
    compared('7290000000011', 30.0, 18.9, 58.73, 3, '2026-09-22'),             // dearer, seen yesterday
    compared('7290000000028', 10.05, 10.0, 0.5, 12, '2026-09-23'),             // dearer by half a percent
    compared('7290000000035', 5.0, 5.0, 0.0, 4, '2026-09-23'),                 // the same price
    compared('7290002331360', 5.9, 21.39, -72.42, 129, '2026-09-23'),          // cheaper
    compared('7290000000042', 6.9, 8.65, -20.23, 70, '2026-09-23', 'no_cost'), // cheaper, not judged
    uncompared('7290000000059', 5.9, 74, '2026-09-23', 'no_reference'),
    uncompared('7290000000066', null, 4, '2026-09-23', 'no_shelf_price'),
    uncompared('305210464728', 12.0, 1, '2026-09-03', 'stale'),
  ]
  return {
    generated_at: '2026-09-23T02:57:38+00:00',
    vintages: { competitor: { snapshot_date: '2026-09-23', sources: ['delivery', 'price_file'], store_count: 164 } },
    capabilities: {
      competitor_position: {
        id: 'competitor_position', status: 'available', unavailable_reason: null,
        entries: [{ id: 'f00d', barcode: '7290017888729', signal_family: 'competitor.policy_breach',
          characterisation: 'policy_breach_review' }],
        comparison,
        ...overrides.capability,
      },
    },
  }
}

const catalogue = { products: Object.entries(NAMES).map(([barcode, product_name]) => ({ barcode, product_name })) }

function renderPage({ artefact = fixture(), onOpenFinding = () => {}, language = 'en' } = {}) {
  return renderWithI18n(
    <PriceGapPage artefact={artefact} catalogue={catalogue} now={NOW} onOpenFinding={onOpenFinding} />,
    { language },
  )
}

const tab = (name) => screen.getByRole('button', { name: new RegExp(`^${name}`) })
const rows = () => [...document.querySelectorAll('tbody tr')]
const rowFor = (barcode) => document.querySelector(`tbody tr[data-barcode="${barcode}"]`)

describe('the Prices page, on the published comparison', () => {
  it('puts every published row in exactly one tab, and says how many', () => {
    renderPage()
    expect(plain(tab('Dearer'))).toBe('Dearer 3')
    expect(plain(tab('Same or cheaper'))).toBe('Same or cheaper 3')
    expect(plain(tab('No comparison'))).toBe('No comparison 3')
  })

  it('opens on the dearer tab, ranked by how much dearer, with the figures the engine published', () => {
    renderPage()
    expect(tab('Dearer').getAttribute('aria-pressed')).toBe('true')
    expect(rows().map((r) => r.dataset.barcode)).toEqual(['7290017888729', '7290000000011', '7290000000028'])
    const soda = rowFor('7290017888729')
    expect(plain(soda)).toContain('שופס סודה ליטר')
    expect(plain(soda)).toContain('₪9.90')
    expect(plain(soda)).toContain('₪5.59')        // the reference, rounded for display only
    expect(plain(soda)).toContain('+77%')
    expect(plain(soda)).toContain('118')
    expect(plain(soda)).toContain('today')
    expect(plain(rowFor('7290000000011'))).toContain('yesterday')
  })

  it('shows half a percent as half a percent', () => {
    // formatPercent multiplies anything between -1 and 1 by 100, which would print +50%.
    renderPage()
    const gap = plain(rowFor('7290000000028'))
    expect(gap).toContain('+0.5%')
    expect(gap).not.toContain('50%')
  })

  it('flags a finding, and the flag opens the finding page', () => {
    const onOpenFinding = vi.fn()
    renderPage({ onOpenFinding })
    const flag = within(rowFor('7290017888729')).getByRole('button', { name: 'Open the finding' })
    fireEvent.click(flag)
    expect(onOpenFinding).toHaveBeenCalledTimes(1)
    expect(within(rowFor('7290000000011')).queryByRole('button', { name: 'Open the finding' })).toBeNull()
  })

  it('ranks the same-or-cheaper tab from the cheapest, and warns about pack sizes there only', () => {
    renderPage()
    expect(document.body.textContent).not.toContain('different pack')
    fireEvent.click(tab('Same or cheaper'))
    expect(rows().map((r) => r.dataset.barcode)).toEqual(['7290002331360', '7290000000042', '7290000000035'])
    expect(document.body.textContent).toContain('different pack under the same barcode')
  })

  it('shows a product with no cost price, marked as not judged', () => {
    // FR-043d withholds the verdict without a cost, not the position (ADR-025).
    renderPage()
    fireEvent.click(tab('Same or cheaper'))
    const noCost = plain(rowFor('7290000000042'))
    expect(noCost).toContain('−20%')
    expect(noCost).toContain('not judged')
    expect(plain(rowFor('7290002331360'))).not.toContain('not judged')
  })

  it('says why for every product it could not compare, and when its price was seen', () => {
    renderPage()
    fireEvent.click(tab('No comparison'))
    expect(plain(rowFor('7290000000059'))).toContain('sold nearby, but in no shop like yours')
    const noShelf = plain(rowFor('7290000000066'))
    expect(noShelf).toContain('you have no shelf price for it')
    expect(noShelf).toContain('—')
    // SCN-047: a stale price is not used, and the page marks its age.
    const stale = plain(rowFor('305210464728'))
    expect(stale).toContain('price too old to use')
    expect(stale).toContain('2026-09-03')
    expect(stale).toContain('₪12.00')
  })

  it('finds a product by name across all three tabs', () => {
    renderPage()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'נביעות' } })
    expect(plain(tab('Dearer'))).toBe('Dearer 0')
    expect(plain(tab('Same or cheaper'))).toBe('Same or cheaper 1')
    expect(plain(tab('No comparison'))).toBe('No comparison 0')
  })

  it('shows 25 rows at a time', () => {
    const many = Array.from({ length: 30 }, (_, i) =>
      compared(String(7290100000000 + i), 10.0, 9.0, 30 - i, 5, '2026-09-23'))
    renderPage({ artefact: fixture({ comparison: many }) })
    expect(rows()).toHaveLength(25)
    fireEvent.click(screen.getByRole('button', { name: 'Show 5 more' }))
    expect(rows()).toHaveLength(30)
    expect(screen.queryByRole('button', { name: /^Show \d+ more$/ })).toBeNull()
  })

  it('says when the prices were seen and how many shops they came from', () => {
    renderPage()
    expect(document.body.textContent).toContain('Prices seen today · 164 nearby shops')
  })

  it('renders an unavailable capability as its reason, with no figures at all', () => {
    // AC-107: a zero here would read as "nothing is dearer", and the capability did not run.
    renderPage({ artefact: fixture({ capability: { status: 'unavailable', unavailable_reason: 'no_competitor_data', comparison: undefined } }) })
    expect(document.body.textContent).toContain('We have no competitor prices to compare against.')
    expect(screen.queryByRole('button', { name: /^Dearer/ })).toBeNull()
    expect(document.querySelector('table')).toBeNull()
  })

  it('says so when the artefact predates the comparison, rather than showing empty tabs', () => {
    renderPage({ artefact: fixture({ capability: { comparison: undefined } }) })
    expect(document.body.textContent).toContain('did not publish the comparison')
    expect(screen.queryByRole('button', { name: /^Dearer/ })).toBeNull()
  })

  it.each(['ar', 'he'])('leaves no raw key and no English label on the page in %s', (language) => {
    renderPage({ language })
    expect(document.querySelectorAll('button[aria-pressed]')).toHaveLength(3)   // it rendered the tabs
    expect(rows().length).toBeGreaterThan(0)
    expect(document.body.textContent).not.toMatch(/\bprices\.[a-z]+/)
    expect(document.body.textContent).not.toMatch(/\b(Dearer|Same or cheaper|No comparison|Reference|not judged)\b/)
  })
})

describe('the Prices page, over the artefact the nightly actually published', () => {
  // Rule 12 at the page: the fixture above is shaped by hand, and a hand-shaped fixture is
  // exactly what let four signals pass every test and change nothing. This reads the real
  // committed files and asserts only what must hold for any artefact.
  const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
  const artefact = JSON.parse(readFileSync(resolve(ROOT, 'public/data/dashboard.json'), 'utf8'))
  const realCatalogue = JSON.parse(readFileSync(resolve(ROOT, 'public/data/catalogue.json'), 'utf8'))
  const published = artefact.capabilities.competitor_position.comparison

  it('accounts for every published row across the three tabs, none dropped', () => {
    renderWithI18n(<PriceGapPage artefact={artefact} catalogue={realCatalogue} now={NOW} onOpenFinding={() => {}} />,
      { language: 'en' })
    const count = (name) => Number(plain(tab(name)).match(/([\d,]+)$/)[1].replaceAll(',', ''))
    expect(count('Dearer') + count('Same or cheaper') + count('No comparison')).toBe(published.length)
  })

  it('leads the dearer tab with the largest premium the engine published', () => {
    renderWithI18n(<PriceGapPage artefact={artefact} catalogue={realCatalogue} now={NOW} onOpenFinding={() => {}} />,
      { language: 'en' })
    const top = Math.max(...published.map((r) => r.premium_pct ?? -Infinity))
    const leaders = published.filter((r) => r.premium_pct === top).map((r) => r.barcode)
    expect(leaders).toContain(rows()[0].dataset.barcode)
  })

  it('names every row from the catalogue, so none falls back to a bare barcode', () => {
    const names = new Set(realCatalogue.products.map((p) => p.barcode))
    expect(published.filter((r) => !names.has(r.barcode))).toEqual([])
  })
})
