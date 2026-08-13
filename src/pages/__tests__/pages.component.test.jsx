/** @vitest-environment jsdom */
import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { analyzeProducts } from '../../lib/analytics/inventoryEngine.js'
import { EMPTY_OPERATIONAL_DATA } from '../../lib/dataAdapters/loadOperationalData.js'

import { ApprovedOrdersPage } from '../ApprovedOrdersPage.jsx'
import { AssortmentGapPage } from '../AssortmentGapPage.jsx'
import { DashboardPage } from '../DashboardPage.jsx'
import { DataSourcePage } from '../DataSourcePage.jsx'
import { ExpiryPage } from '../ExpiryPage.jsx'
import { OperationalPage } from '../OperationalPage.jsx'
import { PriceGapPage } from '../PriceGapPage.jsx'
import { ProductsPage } from '../ProductsPage.jsx'
import { RecommendationsPage } from '../RecommendationsPage.jsx'
import { ReportPage } from '../ReportPage.jsx'
import { ShelfPlanPage } from '../ShelfPlanPage.jsx'
import { StoreLayoutPage } from '../StoreLayoutPage.jsx'

/**
 * Every page renders, in every language, without throwing.
 *
 * This is the cheapest test that would have caught the whole class of bug this
 * work introduced: a page reading `t()` without the provider, a translation key
 * that does not exist, a helper that lost an argument during the i18n pass. The
 * unit tests never touch a component, and the end-to-end suite is too slow to
 * run thirty-nine combinations.
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

const baseProps = {
  analyzedProducts: products,
  products,
  operationalData: EMPTY_OPERATIONAL_DATA,
  operationalStatus: 'ready',
  recommendations: [],
  approvedOrders: [],
  productIndex: new Map(products.map((product) => [product.id, product])),
  dashboardStats: {
    totalProducts: products.length,
    highRiskStockouts: 0,
    reorderSuggestions: 0,
    estimatedOrderCost: 0,
    overstockedItems: 0,
    wasteRisk: 0,
  },
  inventorySummary: { total: products.length, stockoutRisks: 0, lowStock: 0, overstocked: 0 },
  competitorSummary: {},
  affinitySuggestions: [],
  affinitySummary: {},
  planogramItems: [],
  planogramSummary: { totalItems: 0, eyeLevelItems: 0, totalFacings: 0, topScore: 0 },
  shelfGroups: [],
  marketContext: {},
  dataProvenance: { catalog: 'demo', competitor: 'demo' },
  storeData: { connectorMode: 'DEMO', products },
  connectorStatus: { state: 'ready', message: 'ok' },
  decisions: {},
}

const PAGES = [
  ['OperationalPage', OperationalPage],
  ['RecommendationsPage', RecommendationsPage],
  ['ApprovedOrdersPage', ApprovedOrdersPage],
  ['PriceGapPage', PriceGapPage],
  ['AssortmentGapPage', AssortmentGapPage],
  ['StoreLayoutPage', StoreLayoutPage],
  ['ShelfPlanPage', ShelfPlanPage],
  ['ProductsPage', ProductsPage],
  ['ExpiryPage', ExpiryPage],
  ['DashboardPage', DashboardPage],
  ['ReportPage', ReportPage],
  ['DataSourcePage', DataSourcePage],
]

describe.each(['ar', 'he', 'en'])('every page renders in %s', (language) => {
  it.each(PAGES)('%s', (_name, Page) => {
    expect(() => renderWithI18n(<Page {...baseProps} />, { language })).not.toThrow()
  })
})

describe('no untranslated keys leak to the screen', () => {
  it.each(['ar', 'he', 'en'])('%s renders no raw dotted keys', (language) => {
    renderWithI18n(<StoreLayoutPage {...baseProps} />, { language })
    // A missing translation renders as its key, e.g. `sl.totalRun`. That is by
    // design so it is noticeable — this test is what notices.
    expect(document.body.textContent).not.toMatch(/\b(sl|sp|op|nav|page|common)\.[a-zA-Z]+\b/)
  })
})

describe('product names are never translated', () => {
  it.each(['ar', 'he', 'en'])('keeps Hebrew product names in %s', (language) => {
    renderWithI18n(<ProductsPage {...baseProps} />, { language })
    // The manager searches the shelf and the invoice in Hebrew. Translating the
    // name would break the only string tying the screen to the physical product.
    expect(screen.getAllByText(/פסטה 500 גרם/).length).toBeGreaterThan(0)
  })
})
