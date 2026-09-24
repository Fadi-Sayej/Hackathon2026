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
    expect(onAnswer).toHaveBeenCalledWith('bc1', { value: 4.5, status: 'answered' })
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
    expect(onAnswer).toHaveBeenCalledWith('bc1', { value: 29, status: 'answered' })
  })
})
