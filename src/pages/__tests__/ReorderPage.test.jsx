// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, screen } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { ReorderPage } from '../ReorderPage.jsx'

/**
 * Phase 5 Task 5.13: Reorder, as the repository owner approved it on 2026-09-27
 * (docs/reviews/F8-screens-mockups.md). It renders the artefact's fields and computes nothing
 * (ADR-001): every figure on it is one the engine published.
 */
afterEach(cleanup)

const NOW = Date.parse('2026-08-27T08:00:00Z')

const suggestion = (barcode, name, evidence) => ({
  id: `${barcode}000000000000`.slice(0, 16), signal_family: 'order.suggestion', capability: 'order_quantity',
  barcode, product_name: name, department: 'משקאות', action: 'place_order', characterisation: 'order_suggestion',
  value: null, ordering_key: { name: 'units_in_window', value: 50 }, actionable: false,
  not_actionable_reason: null, attention: 'today',
  evidence: {
    order_day: '2026-08-30', cycle: { first_day: '2026-08-30', last_day: '2026-09-05', days: 7 },
    schedule: { form: 'weekdays', weekdays: ['sun'], stated_on: '2026-08-01' }, schedule_changed: false,
    shelf_life: { days: 30, stated_on: '2026-08-01' }, capped: false, kind: 'gross',
    boost: { applied: false, pct: null, model_pick_pct: null, reason: null, model: null, not_applied_because: 'market_not_running_out' },
    count: { recorded_stock: 12, as_of: '2026-06-06', used: false, not_used_because: 'count_too_old', flags: [] },
    daily_mean: 2, adjusted_daily_mean: 2, expected_sales: 14, stock_now: null, stock_at_order_day: null,
    quantity: 14, ...evidence,
  },
})

const GROSS = suggestion('7290005', 'פיוז טי אפרסק', {})
const NET = suggestion('7290002', 'קולה', { kind: 'net', quantity: 11, expected_sales: 14, stock_at_order_day: 3,
  count: { recorded_stock: 12, as_of: '2026-08-24', used: true, not_used_because: null, flags: [] } })
const BOOSTED = suggestion('7290001', 'מים', { kind: 'net', quantity: 23, expected_sales: 23.1, stock_at_order_day: 0,
  boost: { applied: true, pct: 10, model_pick_pct: 10, reason: 'المحلات القريبة نفدت منها', model: 'claude-sonnet-5',
    not_applied_because: null } })
const BREAD = { ...suggestion('7290011', 'לחם אחיד', { kind: 'net', quantity: 12, capped: true, expected_sales: 18,
  stock_at_order_day: 0, shelf_life: { days: 2, stated_on: '2026-08-01' },
  cycle: { first_day: '2026-08-30', last_day: '2026-09-01', days: 3 } }), department: 'מאפים' }

function artefact({ entries = [GROSS, NET, BOOSTED, BREAD], status = 'available', reason = null, departments } = {}) {
  return {
    schema_version: 2,
    thresholds: { market_boost: { max_pct: 25 } },
    capabilities: {
      order_quantity: {
        id: 'order_quantity', status, unavailable_reason: reason, entries: status === 'available' ? entries : [],
        counts: {}, thresholds: { window_days: 28, min_report_days: 21 },
        evidence_window: { first_day: '2026-07-30', last_day: '2026-08-26', report_days: 28, weeks: [] },
        departments: departments ?? {
          'משקאות': { reasons: { not_moving: 2 }, suggested: 3, covered_by_stock: 1 },
          'מאפים': { reasons: {}, suggested: 1, covered_by_stock: 0 },
          'סיגריות': { reasons: { no_order_schedule: 1 }, suggested: 0, covered_by_stock: 0 },
        },
      },
      market_running_out: { status: 'available', products: { 7290001: { stores_out: ['s1'], days_absent: { s1: 3 } } } },
    },
  }
}

function draw({ art = artefact(), outcomes = {}, onOutcome = vi.fn(), readOnly = false, language = 'en' } = {}) {
  renderWithI18n(<ReorderPage artefact={art} ownerState={{ outcomes }} onOutcome={onOutcome} now={NOW}
    readOnly={readOnly} />, { language })
  return onOutcome
}

const card = (name) => [...document.querySelectorAll('[data-suggestion]')].find((c) => c.textContent.includes(name))

describe('Reorder waits, and says for what (Checkpoint 5 item 3)', () => {
  it('names no_daily_sales as the capability publishes it', () => {
    draw({ art: artefact({ status: 'unavailable', reason: 'no_daily_sales' }) })
    const root = document.querySelector('section.capability[data-capability="order_quantity"]')
    expect(root).not.toBeNull()
    expect(root.querySelector('.capability__unavailable').textContent).toContain('waiting for the daily sales reports')
    expect(root.querySelector('.capability__counts')).toBeNull()
    expect(document.querySelectorAll('[data-suggestion]')).toHaveLength(0)
  })

  it('without the capability at all, says it could not be worked out rather than "nothing to order"', () => {
    draw({ art: { schema_version: 2, capabilities: {} } })
    expect(document.querySelector('.capability__unavailable').textContent).toContain('could not work this out')
  })
})

describe('Reorder, filled (FR-154, FR-155, as approved)', () => {
  it('groups the suggestions by department, the busiest first', () => {
    draw()
    const heads = [...document.querySelectorAll('[data-department] h2')].map((h) => h.textContent)
    expect(heads).toEqual(['משקאות', 'מאפים', 'סיגריות'])
  })

  it('says gross in the owner\'s own words, and why the count was not used', () => {
    draw()
    const text = card('פיוז טי אפרסק').textContent
    expect(text).toContain('Order 14')
    expect(text).toContain("You'll sell about 14 before your next order.")
    expect(text).toContain("Your stock count wasn't used: it is from")
  })

  it('says net with the stock at the order day, and when it runs out', () => {
    draw()
    expect(card('קולה').textContent).toMatch(/about 3 will still be on the shelf on Sunday/)
    expect(card('מים').textContent).toMatch(/what you have will be gone by Sunday/)
  })

  it('marks the boost as the model\'s estimate, with its reason in «»', () => {
    draw()
    const box = card('מים').querySelector('[data-boost="applied"]')
    expect(box.textContent).toContain('out of it for 3 days')
    expect(box.textContent).toContain("the model's estimate")
    expect(box.textContent).toContain('«المحلات القريبة نفدت منها»')
  })

  it('says a boost was not applied, and why, when the market is out of it', () => {
    const noKey = { ...BOOSTED, evidence: { ...BOOSTED.evidence, boost: { applied: false, pct: null, model_pick_pct: null,
      not_applied_because: 'no_boost_key' } } }
    draw({ art: artefact({ entries: [noKey] }) })
    const box = card('מים').querySelector('[data-boost="not_applied"]')
    expect(box.textContent).toContain('no key for the model has been set up')
  })

  it('says a quantity was capped by the shelf life, in the language\'s own count', () => {
    draw({ language: 'ar' })
    expect(card('לחם אחיד').textContent).toContain('خلال يومين')
  })

  it('names the fact a department needs, and counts what it covers and what does not move', () => {
    draw()
    const drinks = document.querySelector('[data-department="משקאות"]').textContent
    expect(drinks).toContain('1 more covered by your stock')
    expect(drinks).toContain("2 don't sell every week, so no quantity")
    const cigarettes = document.querySelector('[data-department="סיגריות"]').textContent
    expect(cigarettes).toContain('Tell us which days you order this department')
  })

  it('shows no shekel figure anywhere (INV-069)', () => {
    draw()
    expect(document.body.textContent).not.toMatch(/₪|\bNIS\b|\bILS\b|shekel/i)
  })
})

describe('Deciding (FR-161, SCN-143)', () => {
  it('approves the suggestion as it is', () => {
    const onOutcome = draw()
    fireEvent.click(card('קולה').querySelector('[data-action="approve"]'))
    expect(onOutcome).toHaveBeenCalledWith(NET, { status: 'acted', approvedQuantity: null })
  })

  it('records his own quantity beside the suggested one', () => {
    const onOutcome = draw()
    const c = card('קולה')
    fireEvent.click(c.querySelector('[data-action="change"]'))
    fireEvent.change(c.querySelector('input[type="number"]'), { target: { value: '20' } })
    fireEvent.click(c.querySelector('[data-action="approve"]'))
    expect(onOutcome).toHaveBeenCalledWith(NET, { status: 'acted', approvedQuantity: 20 })
  })

  it('does not accept a quantity that is not a positive whole number', () => {
    const onOutcome = draw()
    const c = card('קולה')
    fireEvent.click(c.querySelector('[data-action="change"]'))
    fireEvent.change(c.querySelector('input[type="number"]'), { target: { value: '-3' } })
    fireEvent.click(c.querySelector('[data-action="approve"]'))
    expect(onOutcome).not.toHaveBeenCalled()
  })

  it('dismisses', () => {
    const onOutcome = draw()
    fireEvent.click(card('קולה').querySelector('[data-action="dismiss"]'))
    expect(onOutcome).toHaveBeenCalledWith(NET, { status: 'declined', reason: 'not_worth_it' })
  })

  it('an approval holds the next night: the same entry is not offered again (SCN-145)', () => {
    draw({ outcomes: { [NET.id]: { status: 'acted', snapshot: { signal_family: 'order.suggestion' } } } })
    expect(card('קולה')).toBeUndefined()
    expect(card('פיוז טי אפרסק')).not.toBeUndefined()
  })

  it('a team account sees every suggestion and can press nothing (ADR-029)', () => {
    const onOutcome = draw({ readOnly: true })
    const buttons = [...document.querySelectorAll('[data-suggestion] button')]
    expect(buttons.length).toBeGreaterThan(0)
    expect(buttons.every((b) => b.disabled)).toBe(true)
    fireEvent.click(card('קולה').querySelector('[data-action="approve"]'))
    expect(onOutcome).not.toHaveBeenCalled()
  })
})

it('keeps screen text free of raw keys in every language', () => {
  for (const language of ['ar', 'he', 'en']) {
    draw({ language })
    expect(document.body.textContent).not.toMatch(/\b(reorder|orders)\.[a-zA-Z_.]+/)
    cleanup()
  }
  expect(screen).toBeTruthy()
})
