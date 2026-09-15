// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, screen, waitFor } from '@testing-library/react'

import { renderWithI18n } from '../test/renderWithI18n.jsx'
import fixture from '../__fixtures__/dashboard.fixture.json'
import App from '../App.jsx'
import { resetCacheForTests } from '../owner/ownerState.js'
import { ar } from '../lib/i18n/dictionaries/ar.js'
import { he } from '../lib/i18n/dictionaries/he.js'
import { en } from '../lib/i18n/dictionaries/en.js'

/**
 * #111. The owner's app captioned his real figures "Demo data" from the 09-12 cut-over
 * onwards, because App.jsx built `{generatedAt, population, run}` and AppShell read
 * `catalog` and `competitor`. Both sides were right on their own terms and nothing joined
 * them, so the label fell through to the demo branch in silence.
 *
 * These render the REAL App against a REAL artefact and read the badge off the screen. A
 * test of AppShell with hand-written props could not catch this: it would assert the same
 * mismatch it is meant to detect. Rule 12, in the chrome.
 *
 * Asserted in all three languages, from the dictionaries themselves — Arabic first, because
 * that is what the owner actually reads (C-53, and ar.js is the source dictionary).
 */
const DICTS = { ar, he, en }

function createStorage() {
  const m = new Map()
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k), clear: () => m.clear() }
}

beforeEach(() => {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => fixture })
})
afterEach(cleanup)

describe('what the owner is told his data is (#111)', () => {
  for (const [language, dict] of Object.entries(DICTS)) {
    it(`calls a real POS export real, not demo — in ${language}`, async () => {
      renderWithI18n(<App />, { language })
      await waitFor(() => expect(screen.getByText(dict['provenance.realPos'])).toBeTruthy())
      expect(screen.queryByText(dict['provenance.demo'])).toBeNull()
    })
  }

  it('shows the competitor prices as real when the artefact carries a snapshot', async () => {
    renderWithI18n(<App />)
    await waitFor(() => expect(screen.getByText(ar['provenance.realPrices'])).toBeTruthy())
  })

  it('claims nothing when there is no artefact to claim it from', async () => {
    globalThis.fetch = async () => ({ ok: false, status: 503 })
    renderWithI18n(<App />)
    await waitFor(() => expect(screen.queryByText(ar['provenance.realPos'])).toBeNull())
    expect(screen.queryByText(ar['provenance.realPrices'])).toBeNull()
  })
})
