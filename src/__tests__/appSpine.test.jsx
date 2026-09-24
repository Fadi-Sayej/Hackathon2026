// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithI18n } from '../test/renderWithI18n.jsx'
import fixture from '../__fixtures__/dashboard.fixture.json'
import App from '../App.jsx'
import { STORAGE_KEY, loadOwnerState, resetCacheForTests } from '../owner/ownerState.js'

/**
 * The spine's guarantees, asked of the app the owner actually runs.
 *
 * These lived in V1Spine.test.jsx and were asserted of V1Spine, which App has not mounted
 * since the cut-over (ADR-028): true of a component nothing renders. Here they are asserted
 * of App, which reads the artefact through the same `loadDashboard` and records outcomes
 * through the same owner state.
 */

function createStorage() {
  const backing = new Map()
  return {
    getItem: (k) => (backing.has(k) ? backing.get(k) : null),
    setItem: (k, v) => backing.set(k, v),
    removeItem: (k) => backing.delete(k),
    clear: () => backing.clear(),
  }
}

const serve = (json) => { globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => json }) }

beforeEach(() => {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
  serve(fixture)
})
afterEach(cleanup)

describe('an artefact that cannot be read', () => {
  it('says the file did not arrive, and shows no numbers', async () => {
    globalThis.fetch = async () => { throw new Error('offline') }
    renderWithI18n(<App />)
    await waitFor(() => expect(document.querySelector('[data-load-status="unreachable"]')).not.toBeNull())
    expect(document.querySelector('.entry-card')).toBeNull()
  })

  it('refuses a shape it does not know rather than guessing', async () => {
    serve({ ...fixture, schema_version: 99 })
    renderWithI18n(<App />)
    await waitFor(() => expect(document.querySelector('[data-load-status="invalid"]')).not.toBeNull())
    expect(document.querySelector('.entry-card')).toBeNull()
  })
})

describe('recording an outcome on Today', () => {
  it('writes the signal family and removes the entry (ADR-016, AC-105)', async () => {
    renderWithI18n(<App />)
    await waitFor(() => expect(document.querySelectorAll('.entry-card').length).toBeGreaterThan(0))
    const before = document.querySelectorAll('.entry-card').length
    const id = document.querySelector('.entry-card').getAttribute('data-entry-id')

    await userEvent.click(screen.getAllByRole('button', { name: /done|عالجته|טיפלתי/i })[0])

    await waitFor(() => expect(document.querySelectorAll('.entry-card')).toHaveLength(before - 1))
    const stored = loadOwnerState().outcomes[id]
    expect(stored.status).toBe('acted')
    expect(stored.snapshot.signal_family).toBeTruthy()
    expect(JSON.parse(globalThis.localStorage.getItem(STORAGE_KEY)).outcomes[id]).toBeTruthy()
  })
})

describe('Today against the artefact', () => {
  it('never shows more than the published bound', async () => {
    renderWithI18n(<App />)
    await waitFor(() => expect(document.querySelectorAll('.entry-card').length).toBeGreaterThan(0))
    expect(document.querySelectorAll('.entry-card').length).toBeLessThanOrEqual(fixture.thresholds.surface.bound)
  })

  it('shows no product twice (AC-109)', async () => {
    renderWithI18n(<App />)
    await waitFor(() => expect(document.querySelectorAll('.entry-card').length).toBeGreaterThan(0))
    const ids = [...document.querySelectorAll('.entry-card[data-entry-id]')].map((n) => n.getAttribute('data-entry-id'))
    expect(new Set(ids).size).toBe(ids.length)
  })
})
