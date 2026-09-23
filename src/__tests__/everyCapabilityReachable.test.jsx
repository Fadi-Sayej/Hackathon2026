// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, waitFor } from '@testing-library/react'

import { renderWithI18n } from '../test/renderWithI18n.jsx'
import fixture from '../__fixtures__/dashboard.fixture.json'
import App from '../App.jsx'
import { resetCacheForTests } from '../owner/ownerState.js'

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
 *   QuestionPanel's tests render the panel; `check:surface` renders pages through V1Spine,
 *   which App has not mounted since the cut-over; the e2e nav walk asserts that every nav
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
 */

function createStorage() {
  const m = new Map()
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k), clear: () => m.clear() }
}

beforeEach(() => {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
  globalThis.fetch = async (url) => (String(url).includes('dashboard.json')
    ? { ok: true, status: 200, json: async () => fixture }
    : { ok: false, status: 404, json: async () => ({}) })
})
afterEach(cleanup)

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
    const published = Object.keys(fixture.capabilities)
    expect(published.filter((id) => !reached.has(id))).toEqual([])
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
    expect(pages.length).toBeGreaterThan(Object.keys(fixture.capabilities).length)
    expect(reached.size).toBe(Object.keys(fixture.capabilities).length)
  })
})
