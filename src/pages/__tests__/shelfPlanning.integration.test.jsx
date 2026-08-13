/** @vitest-environment jsdom */
import { describe, expect, it } from 'vitest'
import { fireEvent, screen, within } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { analyzeProducts } from '../../lib/analytics/inventoryEngine.js'
import { loadApprovedPlan } from '../../lib/planogram/planVersion.js'
import { loadStoreLayout } from '../../lib/planogram/layoutStorage.js'
import { StoreLayoutPage } from '../StoreLayoutPage.jsx'
import { ShelfPlanPage } from '../ShelfPlanPage.jsx'

/**
 * Use-case tests: the jobs a store manager actually does, driven through the
 * real components rather than through the engines underneath them.
 *
 * These sit between the unit tests (which prove the maths) and the end-to-end
 * suite (which proves the browser). They catch the wiring — a handler that
 * never reaches storage, a selection that does not open the plan, a button that
 * renders but does nothing.
 */

const product = (id, name, category, price, cost, stock) => ({
  id,
  name,
  category,
  currentStock: stock,
  shelfQuantity: 0,
  shelfCapacity: 10,
  salesLast7Days: 0,
  salesLast30Days: 0,
  price,
  cost,
  supplier: 'YomYom',
  leadTimeDays: 3,
  returnedUnits: 0,
  damagedUnits: 0,
})

const products = analyzeProducts([
  product('ym-1', 'מים 1.5 ליטר', 'משקאות', 6, 3, 80),
  product('ym-2', 'קוקה קולה 330 מ"ל', 'משקאות', 5, 2.5, 40),
  product('ym-3', 'ספרייט 1.5 ליטר', 'משקאות', 6.5, 3.2, 0),
  product('ym-4', 'פסטה 500 גרם', 'מוצרי מכולת', 10, 6, 25),
])

describe('use case: the manager draws the store, then reads a shelf', () => {
  it('opens the plan for a fixture when it is selected in the top view', () => {
    renderWithI18n(<StoreLayoutPage analyzedProducts={products} />, { language: 'en' })

    // No fixture selected yet, so no plan is shown.
    expect(document.querySelector('.pg-inline-plan')).toBeNull()

    fireEvent.click(document.querySelectorAll('.pg-unit')[0])

    // Selecting one reveals what goes on it — the two screens are one job.
    expect(document.querySelector('.pg-inline-plan')).not.toBeNull()
    expect(document.querySelector('.pg-bay')).not.toBeNull()
  })

  it('persists the drawn layout so it survives a reload', () => {
    renderWithI18n(<StoreLayoutPage analyzedProducts={products} />, { language: 'en' })

    expect(loadStoreLayout()).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /save layout/i }))

    const saved = loadStoreLayout()
    expect(saved.units.length).toBeGreaterThan(0)
    expect(saved.storeW).toBeGreaterThan(0)
  })

  it('adds a fixture to the plan from the palette', () => {
    renderWithI18n(<StoreLayoutPage analyzedProducts={products} />, { language: 'en' })

    const before = document.querySelectorAll('.pg-unit').length
    // Scoped to the palette: fixture names in the unit list match the same text.
    const palette = document.querySelectorAll('.pg-palette-item')
    fireEvent.click(palette[1])

    expect(document.querySelectorAll('.pg-unit').length).toBe(before + 1)
  })
})

describe('use case: the manager approves a shelf plan', () => {
  it('records nothing until Approve is pressed', () => {
    renderWithI18n(<ShelfPlanPage analyzedProducts={products} />, { language: 'en' })
    expect(loadApprovedPlan('default', 'משקאות')).toBeNull()
  })

  it('freezes the plan on approval so it stops changing under the manager', () => {
    renderWithI18n(<ShelfPlanPage analyzedProducts={products} />, { language: 'en' })

    fireEvent.click(screen.getByRole('button', { name: /approve plan/i }))

    const approved = loadApprovedPlan('default', 'משקאות')
    expect(approved).not.toBeNull()
    expect(approved.status).toBe('approved')
    expect(approved.placements.length).toBeGreaterThan(0)
  })

  it('reports zero changes immediately after approving', () => {
    renderWithI18n(<ShelfPlanPage analyzedProducts={products} />, { language: 'en' })
    fireEvent.click(screen.getByRole('button', { name: /approve plan/i }))

    const card = screen.getByText(/against the approved plan/i).closest('.pg-card')
    expect(within(card).getByText('0')).toBeTruthy()
  })
})

describe('use case: the manager reads the build sheet before walking the aisle', () => {
  it('shows a row per position, in build order', () => {
    renderWithI18n(<ShelfPlanPage analyzedProducts={products} />, { language: 'en' })

    const rows = document.querySelectorAll('.pg-sheet tbody tr')
    expect(rows.length).toBeGreaterThan(0)
  })

  it('marks a zero-stock position as unbuildable rather than asking for units', () => {
    renderWithI18n(<ShelfPlanPage analyzedProducts={products} />, { language: 'en' })

    // ym-3 has no stock at all; its row must not read as work to do.
    const unfillable = document.querySelectorAll('.pg-sheet-unfillable')
    expect(unfillable.length).toBeGreaterThan(0)
    expect(within(unfillable[0]).getByText('—')).toBeTruthy()
  })
})

describe('use case: the manager switches department', () => {
  it('re-plans the bay for the chosen category', () => {
    renderWithI18n(<ShelfPlanPage analyzedProducts={products} />, { language: 'en' })

    const select = document.querySelector('select')
    const before = document.querySelectorAll('.pg-position').length

    fireEvent.change(select, { target: { value: 'מוצרי מכולת' } })

    // A different department has a different product count, so the bay changes.
    expect(document.querySelectorAll('.pg-position').length).not.toBe(before)
  })
})

describe('use case: the plan is checked before it is trusted', () => {
  it('states the constraint check result on screen', () => {
    renderWithI18n(<ShelfPlanPage analyzedProducts={products} />, { language: 'en' })
    expect(screen.getByText(/constraint check/i)).toBeTruthy()
    expect(screen.getByText(/valid ✓/i)).toBeTruthy()
  })

  it('shows the comparison against the margin-proportional baseline', () => {
    renderWithI18n(<ShelfPlanPage analyzedProducts={products} />, { language: 'en' })
    expect(screen.getByText(/against the margin-proportional rule/i)).toBeTruthy()
  })

  it('states that demand is assumed when no product has history', () => {
    renderWithI18n(<ShelfPlanPage analyzedProducts={products} />, { language: 'en' })
    // None of these fixtures carry velocity, so the screen must say so.
    expect(screen.getByText(/No product on this fixture carries sales history/i)).toBeTruthy()
  })

  it('reports the real mix once some products do have history', () => {
    // The previous version of this test asserted a flat "no sales history"
    // claim. That claim is false for this store — 1,564 of 7,451 products carry
    // medium or high confidence — so the screen now has to count rather than
    // assert, and this is what holds it to that.
    const withHistory = products.map((product, index) =>
      index === 0
        ? {
            ...product,
            velocityConfidence: 'high',
            analytics: { ...product.analytics, weightedAvgDailySales: 12 },
          }
        : product,
    )

    renderWithI18n(<ShelfPlanPage analyzedProducts={withHistory} />, { language: 'en' })

    expect(screen.getByText(/have real sales history/i)).toBeTruthy()
    expect(screen.queryByText(/No product on this fixture carries sales history/i)).toBeNull()
  })
})
