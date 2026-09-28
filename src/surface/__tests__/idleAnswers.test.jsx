// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { EntryCard } from '../EntryCard.jsx'
import { OUTCOME_REASONS } from '../../owner/ownerState.js'
import { en } from '../../lib/i18n/dictionaries/en.js'
import { ar } from '../../lib/i18n/dictionaries/ar.js'
import { he } from '../../lib/i18n/dictionaries/he.js'

/**
 * F4 FR-070 / AC-071b, approved by the repository owner on 2026-09-28 ("yes to all"): a product
 * that has stock and sold nothing is answered with what he found, not with the generic Done /
 * Not worth it. Three answers, each recorded apart, and none called the right one (FR-071):
 *   - on the shelf, not selling      → acted,    reason still_stocked
 *   - the count is wrong             → declined, reason wrong_data (the data is wrong)
 *   - we don't sell it anymore       → acted,    reason no_longer_carried
 * "Later" stays.
 */
afterEach(cleanup)

const IDLE = { id: 'i1', signal_family: 'catalogue.idle', capability: 'catalogue_lifecycle', barcode: '3',
  product_name: 'מטען', department: 'd', action: 'decide_idle', characterisation: 'idle',
  evidence: { unit_cost: 12.5, cost_source: 'pos', evidence_state: 'no_row', window_id: '2026-01..2026-07' },
  value: null, ordering_key: { name: 'unit_cost', value: 12.5 }, actionable: true, attention: 'today' }

const PRICE = { ...IDLE, id: 'p1', signal_family: 'price.inverted', capability: 'price_consistency',
  action: 'verify_price', characterisation: 'confirmed_loss' }

const draw = (entry, { readOnly = false, language = 'en' } = {}) => {
  const onOutcome = vi.fn()
  renderWithI18n(<EntryCard entry={entry} onOutcome={onOutcome} formatMoney={(x) => `₪${x}`} readOnly={readOnly} />, { language })
  return onOutcome
}
const outcomes = () => [...document.querySelectorAll('[data-outcome]')].map((b) => b.dataset.outcome)

describe('an idle product is answered with what he found', () => {
  it('offers the three answers and Later, instead of Done and Not worth it', () => {
    draw(IDLE)
    expect(outcomes()).toEqual(['still_stocked', 'wrong_count', 'no_longer_carried', 'deferred'])
  })

  it('records each answer apart', () => {
    const onOutcome = draw(IDLE)
    fireEvent.click(document.querySelector('[data-outcome="still_stocked"]'))
    fireEvent.click(document.querySelector('[data-outcome="wrong_count"]'))
    fireEvent.click(document.querySelector('[data-outcome="no_longer_carried"]'))
    expect(onOutcome.mock.calls.map(([, o]) => o)).toEqual([
      { status: 'acted', reason: 'still_stocked' },
      { status: 'declined', reason: 'wrong_data' },
      { status: 'acted', reason: 'no_longer_carried' },
    ])
  })

  it('words the answers in all three languages', () => {
    for (const key of ['still_stocked', 'wrong_count', 'no_longer_carried']) {
      for (const dict of [en, ar, he]) expect(dict[`outcome.idle.${key}`], key).toBeTruthy()
    }
  })

  it('stores the new reasons, which the owner store accepts', () => {
    expect(Object.values(OUTCOME_REASONS)).toEqual(expect.arrayContaining(['still_stocked', 'no_longer_carried', 'wrong_data']))
  })

  it('leaves every other card with the answers it had', () => {
    draw(PRICE)
    expect(outcomes()).toEqual(['acted', 'declined', 'deferred'])
  })

  it('a team account can press none of them (ADR-029)', () => {
    const onOutcome = draw(IDLE, { readOnly: true })
    const buttons = [...document.querySelectorAll('[data-outcome]')]
    expect(buttons.every((b) => b.disabled)).toBe(true)
    fireEvent.click(buttons[0])
    expect(onOutcome).not.toHaveBeenCalled()
  })
})
