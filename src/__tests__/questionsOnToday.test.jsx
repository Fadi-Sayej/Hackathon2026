// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'

import { renderWithI18n } from '../test/renderWithI18n.jsx'
import fixture from '../__fixtures__/dashboard.fixture.json'
import App from '../App.jsx'
import { loadOwnerState, resetCacheForTests } from '../owner/ownerState.js'
import { en } from '../lib/i18n/dictionaries/en.js'

/**
 * The owner's cost questions, back on his screen.
 *
 * WHAT HAPPENED
 *   At the 2026-09-12 cut-over the questions had a nav entry of their own, and App rendered
 *   QuestionPanel with an `onAnswer` that wrote through `recordAnswer`. The restore of the
 *   twelve pages on 2026-09-16 (eaa8834) took the route, the panel and `recordAnswer` out of
 *   App together with the daily surface. The daily surface came back the next day
 *   (2d1f63a); the questions did not. For a week the engine published eleven open
 *   questions, each a missing purchase cost on a product that sells, and nothing on the
 *   owner's screen could show one or record his answer.
 *
 *   Nothing failed. QuestionPanel's own tests passed, and so did `check:surface`, because
 *   both rendered components directly: the panel through V1Spine, which the app had not
 *   mounted since the cut-over. The loss was one layer up, in App, which no test rendered
 *   with questions in it. (check:surface renders App since 2026-09-24, ADR-028.)
 *
 * WHERE THEY GO
 *   At the top of Today, above the action list: the repository owner's decision on
 *   2026-09-23, which also settles OQ-503 (questions and actions share the daily surface).
 *
 * These render the real App over the committed fixture, with an available owner_questions
 * block shaped as `src/engine/owner_questions.py` publishes it.
 */

const QUESTION = (barcode, name, money, units) => ({
  question_id: `q-${barcode}`, barcode, product_name: name, department: 'd', fact: 'cost_price',
  why: { products_affected: 1, money_at_stake: money, money_basis: 'window_revenue_at_shelf_price',
    units_sold: units, window_id: '2026-01..2026-07' },
  expected_value: money,
})

function withQuestions(items) {
  const artefact = structuredClone(fixture)
  artefact.capabilities.owner_questions = {
    ...artefact.capabilities.owner_questions,
    status: 'available', unavailable_reason: null, limit: 3, items,
    suppressed: { withdrawn: 0, idle: 0, answered: 0, no_effect: 0 },
  }
  return artefact
}

function createStorage() {
  const m = new Map()
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k), clear: () => m.clear() }
}

function serve(artefact) {
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => artefact })
}

beforeEach(() => {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
})
afterEach(cleanup)

describe("the owner's cost questions on Today", () => {
  it('sit at the top of Today, above the action list', async () => {
    serve(withQuestions([QUESTION('7290110578978', 'קפה טורקי', 495.6, 12)]))
    renderWithI18n(<App />, { language: 'en' })
    await waitFor(() => expect(screen.getByText(en['questions.title'])).toBeTruthy())

    const questions = document.querySelector('.page-body section.questions')
    const daily = document.querySelector('.page-body section.daily')
    expect(questions).not.toBeNull()
    expect(daily).not.toBeNull()
    expect(questions.compareDocumentPosition(daily) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it("records the owner's answer when he saves it there", async () => {
    serve(withQuestions([QUESTION('7290110578978', 'קפה טורקי', 495.6, 12)]))
    renderWithI18n(<App />, { language: 'en' })
    const input = await screen.findByLabelText(en['questions.costOf'].replace('{product}', 'קפה טורקי'))

    fireEvent.change(input, { target: { value: '31.5' } })
    fireEvent.click(screen.getByRole('button', { name: en['questions.save'] }))

    await waitFor(() => expect(loadOwnerState().answers['7290110578978']?.cost_price?.value).toBe(31.5))
    expect(loadOwnerState().answers['7290110578978'].cost_price.status).toBe('answered')
    // …and Today shows that it was saved, rather than the same empty field (2026-09-24).
    await waitFor(() => expect(document.querySelector('.page-body .question__saved')).not.toBeNull())
    expect(screen.queryByLabelText(en['questions.costOf'].replace('{product}', 'קפה טורקי'))).toBeNull()
  })

  it('say so, rather than vanish, when there is nowhere to record an answer', async () => {
    // The fixture as committed: owner_questions unavailable (answer_storage_unavailable).
    // "No questions today" would be false; the panel names the reason instead.
    serve(fixture)
    renderWithI18n(<App />, { language: 'en' })
    await waitFor(() => expect(screen.getByText(en['questions.title'])).toBeTruthy())
    expect(document.querySelector('.page-body .questions__unavailable')).not.toBeNull()
  })

  it('are not repeated on the other pages', async () => {
    serve(withQuestions([QUESTION('7290110578978', 'קפה טורקי', 495.6, 12)]))
    renderWithI18n(<App />, { language: 'en' })
    await waitFor(() => expect(screen.getByText(en['questions.title'])).toBeTruthy())
    fireEvent.click(document.querySelector('.nav-item[data-nav="data-source"]'))
    await waitFor(() => expect(document.querySelector('.page-body section.daily')).toBeNull())
    expect(document.querySelector('.page-body section.questions')).toBeNull()
  })
})
