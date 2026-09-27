// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, waitFor } from '@testing-library/react'

import { renderWithI18n } from '../test/renderWithI18n.jsx'
import fixture from '../__fixtures__/dashboard.fixture.json'
import App from '../App.jsx'
import { resetCacheForTests } from '../owner/ownerState.js'
import { NOT_YET_SHOWN } from '../surface/compose.js'

/**
 * Every capability the engine publishes has a screen the owner can reach — asked of the app
 * itself, by walking its nav.
 *
 * WHY
 *   Twice in a week a capability lost its screen and every test stayed green.
 *
 *   - #152 removed the old Today page and with it the only whole view of three capabilities,
 *     1,671 findings, which #153 put back. The check that found it was a count in a PR
 *     description, not a test.
 *   - The 2026-09-16 restore took the cost questions out of App, and for a week the engine
 *     published eleven questions nothing could show (#158).
 *
 *   Nothing caught either, because nothing renders App and asks what it can reach.
 *   QuestionPanel's tests render the panel; `check:surface` rendered pages through V1Spine,
 *   which App had not mounted since the cut-over (it renders App since 2026-09-24, ADR-028); the e2e nav walk asserts that every nav
 *   entry renders SOMETHING, from a list edited whenever the nav is.
 *
 * WHAT COUNTS AS REACHED
 *   A capability's whole set, not a sample of it. A few of its entries on Today do not
 *   count: FR-102 asks for the full set on a surface other than the daily one, and the
 *   daily surface shows at most ten places across all of them. So only CapabilityPage's
 *   section is counted, and for `owner_questions`, whose surface is a panel capped by D-8,
 *   the question panel itself.
 *
 * The capabilities are read from the artefact, not listed here, so one the engine adds
 * later is required to have a screen without anyone editing this file.
 *
 * The one exemption is `NOT_YET_SHOWN` (Phase 5 Task 5.0): the market signal and the boost
 * are shown only as facts on Reorder's cards, as the owner approved on 2026-09-27, so they must
 * reach NO screen of their own, and the last block below asserts exactly that. `order_quantity`
 * left the list in Task 5.13, and Reorder renders it whole.
 */

function createStorage() {
  const m = new Map()
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k), clear: () => m.clear() }
}

/** A fresh browser serving `artefact` as dashboard.json. */
function serve(artefact) {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
  globalThis.fetch = async (url) => (String(url).includes('dashboard.json')
    ? { ok: true, status: 200, json: async () => artefact }
    : { ok: false, status: 404, json: async () => ({}) })
}

beforeEach(() => serve(fixture))
afterEach(cleanup)

const shown = Object.keys(fixture.capabilities).filter((id) => !NOT_YET_SHOWN.has(id))

/** Walk every nav entry and collect the capabilities rendered whole on each page. */
async function walkTheNav() {
  renderWithI18n(<App />, { language: 'en' })
  await waitFor(() => expect(document.querySelector('.spine__loading')).toBeNull())
  const reached = new Map()
  const items = [...document.querySelectorAll('.nav-item[data-nav]')]
  for (const item of items) {
    fireEvent.click(item)
    const page = item.dataset.nav
    document.querySelectorAll('.page-body section.capability[data-capability]')
      .forEach((section) => reached.set(section.dataset.capability, page))
    if (document.querySelector('.page-body section.questions')) reached.set('owner_questions', page)
  }
  return { reached, pages: items.map((item) => item.dataset.nav) }
}

describe('every capability the engine publishes has a screen', () => {
  it('reaches each one, whole, from the nav', async () => {
    const { reached } = await walkTheNav()
    expect(shown.filter((id) => !reached.has(id))).toEqual([])
  })

  it('finds the questions on Today and nowhere else', async () => {
    const { reached } = await walkTheNav()
    expect(reached.get('owner_questions')).toBe('daily')
  })

  it('walks a real nav, so the check above cannot pass on an empty one', async () => {
    // Guards the guard: a selector that stopped matching would reach nothing and assert
    // nothing, and "no capability is missing" would hold of an app with no pages.
    const { reached, pages } = await walkTheNav()
    expect(pages).toContain('daily')
    expect(pages.length).toBeGreaterThan(shown.length)
    expect(reached.size).toBe(shown.length)
  })
})

describe('Phase 5 — the capabilities not yet shown reach no screen', () => {
  // Each state a capability can be published in, so each path to a screen is tried: an
  // unavailable one is a line on Today and on Data, an available one is entries and a line.
  const carrying = {
    ...fixture,
    capabilities: {
      ...fixture.capabilities,
      market_boost_unavailable_probe: undefined,
      market_running_out: {
        status: 'available', unavailable_reason: null, counts: { running_out: 1 }, thresholds: {},
        entries: [{ ...fixture.capabilities.hygiene.entries[0], id: 'f8-running-out', capability: 'market_running_out' }],
      },
      market_boost: { status: 'unavailable', unavailable_reason: 'no_boost_key', counts: {}, thresholds: {}, entries: [] },
    },
  }
  delete carrying.capabilities.market_boost_unavailable_probe

  /** Every page's rendered body, by nav id. */
  async function pagesOf(artefact) {
    serve(artefact)
    renderWithI18n(<App />, { language: 'en' })
    await waitFor(() => expect(document.querySelector('.spine__loading')).toBeNull())
    const bodies = {}
    for (const item of document.querySelectorAll('.nav-item[data-nav]')) {
      fireEvent.click(item)
      bodies[item.dataset.nav] = document.querySelector('.page-body')?.innerHTML ?? null
    }
    cleanup()
    return bodies
  }

  it('renders every page, Today and Data included, exactly as it would without them', async () => {
    // App fixes `now` once per session from the clock; two sessions a moment apart must not
    // differ for that reason alone.
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-09-26T08:00:00Z'))
    try {
      const plain = await pagesOf(fixture)
      const withF8 = await pagesOf(carrying)
      expect(Object.keys(withF8)).toEqual(Object.keys(plain))
      expect(Object.keys(plain)).toEqual(expect.arrayContaining(['daily', 'data-source']))
      for (const page of Object.keys(plain)) expect(withF8[page], page).toBe(plain[page])
    } finally {
      vi.useRealTimers()
    }
  })

  it('reaches none of them from the nav', async () => {
    serve(carrying)
    const { reached } = await walkTheNav()
    expect([...NOT_YET_SHOWN].filter((id) => reached.has(id))).toEqual([])
  })
})

describe('Phase 5 Task 5.13 — order_quantity has its screen', () => {
  it('is reached whole on Reorder, even while it waits for daily sales', async () => {
    serve({ ...fixture, capabilities: { ...fixture.capabilities,
      order_quantity: { status: 'unavailable', unavailable_reason: 'no_daily_sales', counts: {}, thresholds: {}, entries: [] } } })
    const { reached } = await walkTheNav()
    expect(reached.get('order_quantity')).toBe('recommendations')
  })
})
