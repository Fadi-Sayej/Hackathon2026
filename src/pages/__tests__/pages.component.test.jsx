/** @vitest-environment jsdom */
import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { analyzeProducts } from '../../lib/analytics/inventoryEngine.js'

import { ProductsPage } from '../ProductsPage.jsx'

/**
 * The Products page renders, in every language, without throwing or leaking a key.
 *
 * This file used to render all twelve pre-V1 pages from demo props. Eleven of them left the
 * build under ADR-028 (2026-09-24): no screen had rendered them since the restore, where the
 * nav shows each entry's awaiting state instead, and their tests went with them. Products is
 * the one pre-V1 page still live, routed at the published catalogue, so its checks stay.
 * Every page's heading and body are asserted in all three languages by the App-level walk in
 * `src/surface/__tests__/checkpoint2.test.jsx` and by `e2e/v1-navigation.spec.js`.
 */

const products = analyzeProducts([
  {
    id: 'ym-1',
    name: 'פסטה 500 גרם',
    category: 'מוצרי מכולת',
    currentStock: 40,
    shelfQuantity: 0,
    shelfCapacity: 10,
    salesLast7Days: 0,
    salesLast30Days: 0,
    price: 10,
    cost: 6,
    supplier: 'YomYom',
    leadTimeDays: 3,
    returnedUnits: 0,
    damagedUnits: 0,
  },
  {
    id: 'ym-2',
    name: 'מים 1.5 ליטר',
    category: 'משקאות',
    currentStock: 0,
    shelfQuantity: 0,
    shelfCapacity: 10,
    salesLast7Days: 0,
    salesLast30Days: 0,
    price: 6,
    cost: 3,
    supplier: 'YomYom',
    leadTimeDays: 3,
    returnedUnits: 0,
    damagedUnits: 0,
  },
])

describe.each(['ar', 'he', 'en'])('the Products page renders in %s', (language) => {
  it('without throwing', () => {
    expect(() => renderWithI18n(<ProductsPage analyzedProducts={products} />, { language })).not.toThrow()
  })

  it('with no raw dotted keys', () => {
    renderWithI18n(<ProductsPage analyzedProducts={products} />, { language })
    // A missing translation renders as its key. That is by design so it is noticeable, and
    // this is what notices.
    expect(document.body.textContent).not.toMatch(/\b(pr|inv|nav|page|common|status)\.[a-zA-Z]+\b/)
  })
})

describe('product names are never translated', () => {
  it.each(['ar', 'he', 'en'])('keeps Hebrew product names in %s', (language) => {
    renderWithI18n(<ProductsPage analyzedProducts={products} />, { language })
    // The manager searches the shelf and the invoice in Hebrew. Translating the
    // name would break the only string tying the screen to the physical product.
    expect(screen.getAllByText(/פסטה 500 גרם/).length).toBeGreaterThan(0)
  })
})
