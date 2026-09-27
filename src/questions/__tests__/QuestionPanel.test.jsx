// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { QuestionPanel } from '../QuestionPanel.jsx'
import { ar } from '../../lib/i18n/dictionaries/ar.js'
import { he } from '../../lib/i18n/dictionaries/he.js'
import { en } from '../../lib/i18n/dictionaries/en.js'

afterEach(cleanup)

const item = (i) => ({
  question_id: `q${i}`,
  barcode: `bc${i}`,
  product_name: `Product ${i}`,
  department: 'd',
  fact: 'cost_price',
  why: { products_affected: 1, money_at_stake: 100 * i, money_basis: 'window_revenue_at_shelf_price', window_id: '2026-01..2026-07' },
  expected_value: 100 * i,
})

const cap = (over = {}) => ({
  status: 'available', unavailable_reason: null, limit: 3, items: [], suppressed: {}, counts: {}, ...over,
})

const render = (over, onAnswer = vi.fn()) => {
  renderWithI18n(
    <QuestionPanel artefact={{ schema_version: 2, capabilities: { owner_questions: cap(over) } }} onAnswer={onAnswer} />,
  )
  return onAnswer
}

describe('D-8 — at most three questions, and the limit comes from the artefact', () => {
  it('shows no more than the published limit', () => {
    render({ items: [item(1), item(2), item(3), item(4), item(5)] })
    expect(document.querySelectorAll('[data-question-id]')).toHaveLength(3)
  })

  it('honours a different limit rather than a hard-coded three', () => {
    render({ limit: 1, items: [item(1), item(2), item(3)] })
    expect(document.querySelectorAll('[data-question-id]')).toHaveLength(1)
  })
})

describe('AC-107 applied here — unavailable is not "no questions today"', () => {
  it('names the reason and does not claim there is nothing to ask', () => {
    render({ status: 'unavailable', unavailable_reason: 'answer_storage_unavailable', items: [] })
    expect(document.querySelector('.questions__unavailable')).not.toBeNull()
    expect(document.querySelector('.questions__none')).toBeNull()
  })

  it('says there is nothing to ask only when the capability ran and found nothing', () => {
    render({ items: [] })
    expect(document.querySelector('.questions__none')).not.toBeNull()
    expect(document.querySelector('.questions__unavailable')).toBeNull()
  })
})

describe('answering', () => {
  it('passes the barcode and the value to the owner store', async () => {
    const onAnswer = render({ items: [item(1)] })
    await userEvent.type(screen.getByLabelText(/Product 1/i), '4.5')
    await userEvent.click(screen.getByRole('button', { name: /save|حفظ|שמור/i }))
    expect(onAnswer).toHaveBeenCalledWith('bc1', 'cost_price', { value: 4.5, status: 'answered' })
  })

  it('does not submit a non-numeric answer', async () => {
    const onAnswer = render({ items: [item(1)] })
    await userEvent.type(screen.getByLabelText(/Product 1/i), 'abc')
    await userEvent.click(screen.getByRole('button', { name: /save|حفظ|שמור/i }))
    expect(onAnswer).not.toHaveBeenCalled()
  })

  it('reports a failed write instead of clearing the field', async () => {
    const failing = vi.fn().mockRejectedValue(new Error('QuotaExceeded'))
    render({ items: [item(1)] }, failing)
    await userEvent.type(screen.getByLabelText(/Product 1/i), '4.5')
    await userEvent.click(screen.getByRole('button', { name: /save|حفظ|שמור/i }))
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByLabelText(/Product 1/i).value).toBe('4.5')
  })
})

describe('why the question is being asked', () => {
  it('states the money at stake with the window it rests on', () => {
    render({ items: [item(2)] })
    const why = document.querySelector('.question__why')
    expect(why.textContent).toMatch(/2026-01\.\.2026-07/)
  })
})

describe('ADR-027 — a question with no shelf price shows no figure', () => {
  // `money_at_stake: null` used to reach this panel as 0 and print "Affects ₪0": nothing at
  // stake, for a stake nobody knows. The line names the missing price instead, and shows the
  // only weight the question has: what sold, over which window.
  const unpriced = {
    ...item(9),
    why: { products_affected: 1, money_at_stake: null, money_missing: 'shelf_price',
      money_basis: 'window_revenue_at_shelf_price', units_sold: 80, window_id: '2026-01..2026-07' },
    expected_value: null,
  }

  it.each([['ar', ar], ['he', he], ['en', en]])('in %s it names the missing price, never ₪', (language, dict) => {
    renderWithI18n(
      <QuestionPanel artefact={{ schema_version: 2, capabilities: { owner_questions: cap({ items: [unpriced, item(2)] }) } }}
        onAnswer={vi.fn()} />,
      { language },
    )
    const [first, second] = document.querySelectorAll('.question__why')
    expect(first.textContent).toBe(dict['questions.whyNoPrice'].replace('{units}', '80').replace('{window}', '2026-01..2026-07'))
    expect(first.textContent).not.toContain('₪')
    expect(second.textContent).toContain('₪')                     // a priced question keeps its figure
  })
})

describe('an answer he has saved says so', () => {
  // Approved by the repository owner on 2026-09-24. The engine only drops an answered
  // question at the next nightly run, so until then it looked exactly as before he answered:
  // an empty field, as if nothing had happened.
  const answers = { bc1: { cost_price: { value: 31.5, status: 'answered', at: 1 } } }
  const renderWith = (onAnswer = vi.fn()) => {
    renderWithI18n(
      <QuestionPanel artefact={{ schema_version: 2, capabilities: { owner_questions: cap({ items: [item(1), item(2)] }) } }}
        answers={answers} onAnswer={onAnswer} />,
      { language: 'en' },
    )
    return onAnswer
  }

  it('shows his saved value in place of the empty field', () => {
    renderWith()
    const saved = document.querySelector('[data-question-id="q1"] .question__saved')
    expect(saved.textContent.replace(/[⁦-⁩]/g, '')).toBe(
      en['questions.saved'].replace('{value}', '₪31.50'))
    expect(screen.queryByLabelText(/Product 1/)).toBeNull()
    expect(screen.getByLabelText(/Product 2/)).toBeTruthy()            // an unanswered one keeps its field
  })

  it('reopens the field with his value when he wants to change it', async () => {
    const onAnswer = renderWith()
    await userEvent.click(screen.getByRole('button', { name: en['questions.change'] }))
    const input = screen.getByLabelText(/Product 1/)
    expect(input.value).toBe('31.5')
    await userEvent.clear(input)
    await userEvent.type(input, '29')
    await userEvent.click(within(document.querySelector('[data-question-id="q1"]')).getByRole('button', { name: /save/i }))
    expect(onAnswer).toHaveBeenCalledWith('bc1', 'cost_price', { value: 29, status: 'answered' })
  })
})


// ── Phase 5 Task 5.14: the disagreement question (FR-158, FR-159), as approved 2026-09-27 ──

const disagreement = (i, why = {}) => ({
  question_id: `d${i}`, barcode: `db${i}`, product_name: `סודה ${i}`, department: 'd', fact: 'market_disagreement',
  why: { stores_out: 1, days_absent: [3], units_in_window: 7, weekly_units: [7, 0, 0, 0], report_days: 28,
    no_sales_row: false, ...why },
  answers: ['shelf_place', 'price', 'weak_market', 'sells_elsewhere'], expected_value: null,
})

const drawIn = (language, items, { onAnswer = vi.fn(), readOnly = false } = {}) => {
  renderWithI18n(
    <QuestionPanel artefact={{ schema_version: 2, capabilities: { owner_questions: cap({ items }) } }}
      onAnswer={onAnswer} readOnly={readOnly} />, { language })
  return onAnswer
}

describe('the disagreement question', () => {
  it('states only what was observed, with the week count in words', () => {
    drawIn('en', [disagreement(1)])
    const text = document.querySelector('[data-question-id="d1"]').textContent
    expect(text).toContain('The stores near you have run out of סודה 1.')
    expect(text).toContain('Here you sold 7 in the last four weeks, in only one of them.')
    expect(text).not.toMatch(/a lot|sells well|zero/i)
  })

  it('says his reports have no row for it, in a department they do not itemise', () => {
    drawIn('he', [disagreement(1, { no_sales_row: true, units_in_window: null, weekly_units: null, report_days: null })])
    expect(document.querySelector('[data-question-id="d1"]').textContent).toContain('בדוחות המכירות שלך אין לו שורה')
  })

  it('says it was delivered but did not sell, never that it sold zero', () => {
    drawIn('ar', [disagreement(1, { units_in_window: 0, weekly_units: [0, 0, 0, 0] })])
    expect(document.querySelector('[data-question-id="d1"]').textContent).toContain('وصلتك منه بضاعة')
  })

  it('offers the four answers, and records the one he picks under its own fact', async () => {
    const onAnswer = drawIn('en', [disagreement(1)])
    await userEvent.click(screen.getByRole('button', { name: en['questions.answer.weak_market'] }))
    expect(onAnswer).toHaveBeenCalledWith('db1', 'market_disagreement', { value: 'weak_market', status: 'answered' })
  })

  it('"Not now" hides it here and records nothing, so the one ask is not spent', async () => {
    const onAnswer = drawIn('en', [disagreement(1)])
    await userEvent.click(screen.getByRole('button', { name: en['questions.later'] }))
    expect(onAnswer).not.toHaveBeenCalled()
    expect(document.querySelector('[data-question-id="d1"]')).toBeNull()
  })

  it('counts toward the same limit of three as the cost questions (D-8)', () => {
    drawIn('en', [item(1), item(2), disagreement(1), disagreement(2)])
    expect(document.querySelectorAll('[data-question-id]')).toHaveLength(3)
  })

  it('a team account cannot answer it', () => {
    const onAnswer = drawIn('en', [disagreement(1)], { readOnly: true })
    const buttons = [...document.querySelectorAll('[data-question-id="d1"] button')]
    expect(buttons.length).toBe(5)
    expect(buttons.every((b) => b.disabled)).toBe(true)
    expect(onAnswer).not.toHaveBeenCalled()
  })

  it('the panel has the title he approved', () => {
    drawIn('en', [disagreement(1)])
    expect(screen.getByRole('heading', { name: 'Questions only you can answer' })).toBeTruthy()
  })
})
