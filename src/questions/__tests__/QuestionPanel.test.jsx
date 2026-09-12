// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { QuestionPanel } from '../QuestionPanel.jsx'

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
