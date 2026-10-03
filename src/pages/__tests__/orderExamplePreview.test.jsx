// @vitest-environment jsdom

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, screen, within } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { ApprovedOrdersPage } from '../ApprovedOrdersPage.jsx'
import { ReorderPage } from '../ReorderPage.jsx'

/**
 * D-29: while the order pages wait for daily reports, each may show an example of itself.
 *
 * The example is a test shop (scripts/build_order_example.py), shown inside a preview whose
 * banner says so, with every button disabled. It must never reach the owner's state: nothing
 * pressed in it is recorded, and nothing in it can be exported.
 */
afterEach(cleanup)

// Read from the repository root: jsdom's import.meta.url is not a file URL.
const EXAMPLE = JSON.parse(readFileSync(join(process.cwd(), 'public', 'examples', 'order-example.json'), 'utf8'))
const loaded = async () => ({ status: 'ok', example: EXAMPLE })
const WAITING = { capabilities: { order_quantity: { status: 'unavailable', unavailable_reason: 'no_daily_sales', entries: [] } } }
const BANNER = /Example: a test shop, not your data/
const render = (ui) => renderWithI18n(ui, { language: 'en' })

describe('Reorder, while it waits', () => {
  it('offers to show how the page looks', () => {
    render(<ReorderPage artefact={WAITING} ownerState={{ outcomes: {} }} onOutcome={vi.fn()} loadExample={loaded} />)
    expect(screen.getByRole('button', { name: 'See how this page looks' })).toBeTruthy()
  })

  it('shows the test shop under a banner, and records nothing pressed in it', async () => {
    const onOutcome = vi.fn()
    render(<ReorderPage artefact={WAITING} ownerState={{ outcomes: {} }} onOutcome={onOutcome} loadExample={loaded} />)
    fireEvent.click(screen.getByRole('button', { name: 'See how this page looks' }))
    const preview = await screen.findByRole('region', { name: 'Example' })
    expect(within(preview).getByText(BANNER)).toBeTruthy()
    expect(within(preview).getByText('לחם אחיד')).toBeTruthy()
    const approve = within(preview).getAllByRole('button', { name: 'Approve' })
    expect(approve.length).toBeGreaterThan(0)
    for (const button of approve) {
      expect(button.disabled).toBe(true)
      fireEvent.click(button)
    }
    expect(onOutcome).not.toHaveBeenCalled()
  })

  it('goes back to the waiting page', async () => {
    render(<ReorderPage artefact={WAITING} ownerState={{ outcomes: {} }} onOutcome={vi.fn()} loadExample={loaded} />)
    fireEvent.click(screen.getByRole('button', { name: 'See how this page looks' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Close the example' }))
    expect(screen.queryByRole('region', { name: 'Example' })).toBeNull()
  })

  it('says so when the example cannot be loaded, and shows no page', async () => {
    render(<ReorderPage artefact={WAITING} ownerState={{ outcomes: {} }} onOutcome={vi.fn()}
      loadExample={async () => ({ status: 'error' })} />)
    fireEvent.click(screen.getByRole('button', { name: 'See how this page looks' }))
    expect(await screen.findByText('The example could not be loaded.')).toBeTruthy()
    expect(screen.queryByText('לחם אחיד')).toBeNull()
  })

  it('offers no example once the page has the store\'s own suggestions', () => {
    render(<ReorderPage artefact={EXAMPLE.artefact} ownerState={{ outcomes: {} }} onOutcome={vi.fn()}
      loadExample={loaded} />)
    expect(screen.queryByRole('button', { name: 'See how this page looks' })).toBeNull()
  })
})

describe('Approved orders, before anything is approved', () => {
  it('shows the test shop\'s approvals under a banner, and nothing can be downloaded', async () => {
    render(<ApprovedOrdersPage ownerState={{ outcomes: {} }} catalogue={{ products: [] }} now={Date.now()}
      loadExample={loaded} />)
    fireEvent.click(screen.getByRole('button', { name: 'See how this page looks' }))
    const preview = await screen.findByRole('region', { name: 'Example' })
    expect(within(preview).getByText(BANNER)).toBeTruthy()
    expect(within(preview).getAllByRole('row').length).toBeGreaterThan(3)
    expect(within(preview).getByText('לחם אחיד')).toBeTruthy()
    for (const button of within(preview).getAllByRole('button', { name: /CSV/i })) expect(button.disabled).toBe(true)
  })

  it('offers no example once the owner has approved something', () => {
    render(<ApprovedOrdersPage ownerState={EXAMPLE.owner_state} catalogue={EXAMPLE.catalogue}
      now={Date.parse(EXAMPLE.now)} loadExample={loaded} />)
    expect(screen.queryByRole('button', { name: 'See how this page looks' })).toBeNull()
  })
})
