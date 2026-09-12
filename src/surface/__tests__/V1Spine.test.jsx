// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import fixture from '../../__fixtures__/dashboard.fixture.json'
import { V1Spine } from '../V1Spine.jsx'
import { V1_PAGES } from '../pages.js'
import { STORAGE_KEY, loadOwnerState, resetCacheForTests } from '../../owner/ownerState.js'

afterEach(cleanup)

function createStorage() {
  const backing = new Map()
  return {
    getItem: (k) => (backing.has(k) ? backing.get(k) : null),
    setItem: (k, v) => backing.set(k, v),
    removeItem: (k) => backing.delete(k),
  }
}

beforeEach(() => {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
})

const ok = async () => ({ ok: true, status: 200, json: async () => fixture })
const NOW = 1_757_000_000_000

describe('the ten V1 pages', () => {
  it('names exactly ten', () => {
    expect(V1_PAGES).toHaveLength(10)
  })

  it('renders every one of them against a real artefact without throwing', async () => {
    for (const page of V1_PAGES) {
      const { unmount } = renderWithI18n(<V1Spine page={page} fetchImpl={ok} now={NOW} />)
      await waitFor(() => expect(document.querySelector('.spine__loading')).toBeNull())
      unmount()
    }
  })
})

describe('an artefact that cannot be read', () => {
  it('says the file did not arrive, and shows no numbers', async () => {
    renderWithI18n(<V1Spine page="daily" fetchImpl={async () => { throw new Error('offline') }} now={NOW} />)
    await waitFor(() => expect(document.querySelector('[data-load-status="unreachable"]')).not.toBeNull())
    expect(document.querySelector('.entry-card')).toBeNull()
  })

  it('refuses a shape it does not know rather than guessing', async () => {
    const wrong = async () => ({ ok: true, status: 200, json: async () => ({ ...fixture, schema_version: 99 }) })
    renderWithI18n(<V1Spine page="daily" fetchImpl={wrong} now={NOW} />)
    await waitFor(() => expect(document.querySelector('[data-load-status="invalid"]')).not.toBeNull())
  })
})

describe('recording an outcome through the spine', () => {
  it('writes the signal family and removes the entry (ADR-016, AC-105)', async () => {
    renderWithI18n(<V1Spine page="daily" fetchImpl={ok} now={NOW} />)
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

describe('the daily surface against the real artefact', () => {
  it('never shows more than the published bound', async () => {
    renderWithI18n(<V1Spine page="daily" fetchImpl={ok} now={NOW} />)
    await waitFor(() => expect(document.querySelectorAll('.entry-card').length).toBeGreaterThan(0))
    expect(document.querySelectorAll('.entry-card').length)
      .toBeLessThanOrEqual(fixture.thresholds.surface.bound)
  })

  it('shows no product twice (AC-109)', async () => {
    renderWithI18n(<V1Spine page="daily" fetchImpl={ok} now={NOW} />)
    await waitFor(() => expect(document.querySelectorAll('.entry-card').length).toBeGreaterThan(0))
    const ids = [...document.querySelectorAll('[data-entry-id]')].map((n) => n.getAttribute('data-entry-id'))
    expect(new Set(ids).size).toBe(ids.length)
  })
})
