// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithI18n } from '../test/renderWithI18n.jsx'
import fixture from '../__fixtures__/dashboard.fixture.json'
import App from '../App.jsx'
import { resetCacheForTests } from '../owner/ownerState.js'
import { en } from '../lib/i18n/dictionaries/en.js'

/**
 * The receiving capture, back on the owner's screen.
 *
 * The 2026-09-16 restore (eaa8834) took the `receiving` nav entry and ReceivingPage out of
 * App, and gave the returning Expiry entry only a waiting note that said "it fills as the
 * receiving screen is used" — a screen that no longer existed. So capture, which F10 needs
 * thirty days of, stopped four days after it started. The repository owner put the form back
 * on the Expiry page on 2026-09-24, below the note, with no new nav entry.
 */

const CATALOGUE = {
  schema_version: 1, generated_at: fixture.generated_at, inputs_digest: fixture.inputs_digest,
  population: 'whole', count: 1,
  products: [{ barcode: '7290000066318', product_name: 'קוקה קולה 1.5 ליטר', department: 'd', shelf_price: 8.9,
    cost_price: 5.1, cost_source: 'pos', delivery_price: null, recorded_stock: 12, has_identifier: true }],
}

function createStorage() {
  const m = new Map()
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k), clear: () => m.clear() }
}

beforeEach(() => {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
  globalThis.fetch = async (url) => ({
    ok: true, status: 200,
    json: async () => (String(url).includes('catalogue.json') ? CATALOGUE : fixture),
  })
})
afterEach(cleanup)

async function openExpiry() {
  renderWithI18n(<App />, { language: 'en' })
  await waitFor(() => expect(document.querySelector('.spine__loading')).toBeNull())
  fireEvent.click(document.querySelector('.nav-item[data-nav="expiry"]'))
}

describe('receiving capture on the Expiry page', () => {
  it('shows the waiting note, and the capture form below it', async () => {
    await openExpiry()
    const note = await waitFor(() => {
      const el = document.querySelector('.page-body [data-needs="expiry"]')
      expect(el).not.toBeNull()
      return el
    })
    const barcode = await screen.findByLabelText(/barcode/i)
    expect(note.compareDocumentPosition(barcode) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByRole('button', { name: /^save$/i })).toBeTruthy()
  })

  it('no longer points the owner at a screen that is not there', async () => {
    await openExpiry()
    await screen.findByLabelText(/barcode/i)
    expect(document.body.textContent).not.toContain(en['page.receiving.title'] + ' screen')
    expect(document.body.textContent).not.toContain('the receiving screen is used')
  })

  it('names a scanned product from the published catalogue', async () => {
    const user = userEvent.setup()
    await openExpiry()
    await user.type(await screen.findByLabelText(/barcode/i), '7290000066318')
    expect(await screen.findByText(/קוקה קולה 1.5 ליטר/)).toBeTruthy()
    expect(screen.queryByText(en['rc.notInCatalog'])).toBeNull()
  })
})
