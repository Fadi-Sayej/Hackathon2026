// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { cleanup } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { ApprovedOrdersPage } from '../ApprovedOrdersPage.jsx'
import { approvedLines, ordersCsv } from '../approvedOrders.js'

/**
 * Phase 5 Task 5.13: Approved orders, as the repository owner approved it on 2026-09-27.
 * A projection of his recorded approvals joined to the catalogue for the name and department
 * (ADR-034 Decision 5, ADR-024). No arithmetic, and no ₪ (FR-162, INV-069).
 */
afterEach(cleanup)

const NOW = Date.parse('2026-08-27T08:00:00Z')
const CATALOGUE = { products: [
  { barcode: '7290001', product_name: 'מים', department: 'משקאות' },
  { barcode: '7290005', product_name: 'פיוז טי, אפרסק', department: 'משקאות' },
  { barcode: '7290011', product_name: 'לחם אחיד', department: 'מאפים' },
] }

const acted = (barcode, orderDay, suggested, approved) => ({
  status: 'acted', at: 1, snapshot: { signal_family: 'order.suggestion', capability: 'order_quantity', barcode,
    order_day: orderDay, kind: 'net', suggested_quantity: suggested,
    ...(approved !== undefined ? { approved_quantity: approved } : {}) },
})

const OUTCOMES = {
  a: acted('7290001', '2026-08-30', 23),
  b: acted('7290005', '2026-08-30', 28, 24),
  c: acted('7290011', '2026-08-30', 12),
  past: acted('7290001', '2026-08-23', 20),                          // an order day already gone
  dismissed: { ...acted('7290011', '2026-08-30', 9), status: 'declined' },
  other: { status: 'acted', at: 1, snapshot: { signal_family: 'price.inverted', barcode: '7290001' } },
}

describe('what is listed', () => {
  it('his approvals for an order day still to come, with his quantity when he changed it', () => {
    const lines = approvedLines(OUTCOMES, CATALOGUE, NOW)
    expect(lines.map((l) => [l.barcode, l.quantity, l.suggested])).toEqual([
      ['7290011', 12, 12], ['7290001', 23, 23], ['7290005', 24, 28]])
    expect(lines.find((l) => l.barcode === '7290005')).toMatchObject({ product: 'פיוז טי, אפרסק', department: 'משקאות', changed: true })
  })

  it('renders them by department, with product, quantity and order day, and what he changed', () => {
    renderWithI18n(<ApprovedOrdersPage ownerState={{ outcomes: OUTCOMES }} catalogue={CATALOGUE} now={NOW} />, { language: 'en' })
    const drinks = document.querySelector('[data-department="משקאות"]')
    expect(drinks.textContent).toContain('מים')
    expect(drinks.textContent).toContain('you changed it from 28')
    expect(document.querySelector('[data-department="מאפים"]').textContent).toContain('12')
    expect(document.body.textContent).toContain('Sun 30 Aug')
  })

  it('shows no shekel figure, no price and no total (INV-069)', () => {
    renderWithI18n(<ApprovedOrdersPage ownerState={{ outcomes: OUTCOMES }} catalogue={CATALOGUE} now={NOW} />, { language: 'en' })
    expect(document.body.textContent).not.toMatch(/₪|\bNIS\b|\bILS\b|shekel|\btotal\b/i)
  })
})

describe('the CSV for his supplier', () => {
  it('has exactly the columns ADR-034 names, in order, and quotes what needs quoting', () => {
    const csv = ordersCsv(approvedLines(OUTCOMES, CATALOGUE, NOW))
    expect(csv.split('\n')).toEqual([
      'product,barcode,quantity,order_day',
      'לחם אחיד,7290011,12,2026-08-30',
      'מים,7290001,23,2026-08-30',
      '"פיוז טי, אפרסק",7290005,24,2026-08-30',
    ])
  })

  it('is offered only when there is something to send', () => {
    renderWithI18n(<ApprovedOrdersPage ownerState={{ outcomes: {} }} catalogue={CATALOGUE} now={NOW} />, { language: 'en' })
    expect(document.querySelector('[data-action="csv"]').disabled).toBe(true)
  })
})
