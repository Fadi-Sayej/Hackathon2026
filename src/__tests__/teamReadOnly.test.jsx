// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'

import { renderWithI18n } from '../test/renderWithI18n.jsx'
import fixture from '../__fixtures__/dashboard.fixture.json'
import App from '../App.jsx'
import { DataPage } from '../pages/DataPage.jsx'
import { AuthContext } from '../auth/useAuth.js'
import { loadOwnerState, resetCacheForTests } from '../owner/ownerState.js'
import { en } from '../lib/i18n/dictionaries/en.js'

/**
 * ADR-029 §5, approved as mockups on 2026-09-25: a team account sees the owner's app exactly
 * as he does, with a notice at the top, and nothing it presses is saved. The Firestore rules
 * refuse the write too; these pin the browser half, so a team click never even reaches it.
 */

const TEAM = { mode: 'firebase', role: 'team', readOnly: true, email: 'team@example.com', signOut: null }

const QUESTION = {
  question_id: 'q-7290110578978', barcode: '7290110578978', product_name: 'קפה טורקי', department: 'd',
  fact: 'cost_price', expected_value: 495.6,
  why: { products_affected: 1, money_at_stake: 495.6, money_basis: 'window_revenue_at_shelf_price',
    units_sold: 12, window_id: '2026-01..2026-07' },
}

function artefactWithQuestion() {
  const artefact = structuredClone(fixture)
  artefact.capabilities.owner_questions = {
    ...artefact.capabilities.owner_questions,
    status: 'available', unavailable_reason: null, limit: 3, items: [QUESTION],
    suppressed: { withdrawn: 0, idle: 0, answered: 0, no_effect: 0 },
  }
  return artefact
}

function createStorage() {
  const m = new Map()
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k), clear: () => m.clear() }
}

beforeEach(() => {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
  const artefact = artefactWithQuestion()
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => artefact })
})
afterEach(cleanup)

const asTeam = (ui) => renderWithI18n(<AuthContext.Provider value={TEAM}>{ui}</AuthContext.Provider>, { language: 'en' })

describe('a team account on Today', () => {
  it('is told it is the team view, above the page', async () => {
    asTeam(<App />)
    const banner = await screen.findByText(en['auth.team.banner'])
    const topbar = document.querySelector('.topbar')
    expect(banner.compareDocumentPosition(topbar) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('cannot answer a cost question', async () => {
    asTeam(<App />)
    const input = await screen.findByLabelText(en['questions.costOf'].replace('{product}', 'קפה טורקי'))
    expect(input.disabled).toBe(true)
    expect(screen.getByRole('button', { name: en['questions.save'] }).disabled).toBe(true)
  })

  it('cannot record an outcome, and a click saves nothing', async () => {
    asTeam(<App />)
    await waitFor(() => expect(document.querySelectorAll('.entry-card__actions button').length).toBeGreaterThan(0))
    const buttons = [...document.querySelectorAll('.entry-card__actions button')]
    expect(buttons.every((b) => b.disabled)).toBe(true)
    fireEvent.click(buttons[0])
    expect(Object.keys(loadOwnerState().outcomes)).toHaveLength(0)
  })
})

describe('the owner on Today', () => {
  it('sees no notice and can act', async () => {
    renderWithI18n(<App />, { language: 'en' })
    await waitFor(() => expect(document.querySelectorAll('.entry-card__actions button').length).toBeGreaterThan(0))
    expect(screen.queryByText(en['auth.team.banner'])).toBeNull()
    expect([...document.querySelectorAll('.entry-card__actions button')].some((b) => b.disabled)).toBe(false)
  })
})

describe('the Data page for a team account', () => {
  it('lists what the owner hid, but cannot restore it', () => {
    // The Data page lists what the owner put off with "Later" (compose.deferredEntries).
    const entry = Object.entries(fixture.capabilities)
      .filter(([id, c]) => c.status === 'available' && id !== 'owner_questions')
      .flatMap(([, c]) => c.entries || [])[0]
    const now = Date.now()
    const ownerState = {
      answers: {}, revivals: {}, meta: { schema: 2 },
      outcomes: { [entry.id]: { status: 'deferred', reason: null, at: now - 1000, deferred_until: now + 86400000,
        snapshot: { signal_family: entry.signal_family } } },
    }
    asTeam(<DataPage artefact={fixture} ownerState={ownerState} onRestore={() => {}} readOnly now={now} />)
    const restore = document.querySelector(`[data-restore="${entry.id}"]`)
    expect(restore).not.toBeNull()
    expect(restore.disabled).toBe(true)
  })
})
