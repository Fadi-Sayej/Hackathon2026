// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { cleanup } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { ReorderPage } from '../ReorderPage.jsx'

/**
 * F14 on Reorder (F14-S1 FR-238, FR-242, FR-243), as the repository owner approved the mockups on
 * 2026-10-10 (docs/reviews/F14-screens-mockups.md). The AI's text replaces the engine's sentence
 * and the shelf-life line; the page fills its slots from the suggestion's published facts; a text
 * the page cannot show leaves today's card; one note above the suggestions says what the AI did.
 */
afterEach(cleanup)

const suggestion = (barcode, name, evidence, department = 'משקאות') => ({
  id: `${barcode}000000000000`.slice(0, 16), signal_family: 'order.suggestion', capability: 'order_quantity',
  barcode, product_name: name, department, action: 'place_order', characterisation: 'order_suggestion',
  value: null, ordering_key: { name: 'units_in_window', value: 50 }, actionable: false,
  not_actionable_reason: null, attention: 'today',
  evidence: {
    order_day: '2026-08-30', cycle: { first_day: '2026-08-30', last_day: '2026-09-05', days: 7 },
    schedule: { form: 'weekdays', weekdays: ['sun'], stated_on: '2026-08-01' }, schedule_changed: false,
    shelf_life: { days: 30, stated_on: '2026-08-01' }, capped: false, kind: 'net',
    boost: { applied: false, pct: null, model_pick_pct: null, reason: null, model: null, not_applied_because: 'market_not_running_out' },
    count: { recorded_stock: 12, as_of: '2026-08-24', used: true, not_used_because: null, flags: [] },
    daily_mean: 2, adjusted_daily_mean: 2, expected_sales: 14, stock_now: 12, stock_at_order_day: 3,
    quantity: 11, weekly_units: [14, 14, 14, 14], ...evidence,
  },
})

const COLA = suggestion('7290002', 'קולה', {})
const GROSS = suggestion('7290005', 'ביסלי גריל', { kind: 'gross', quantity: 28, expected_sales: 28, stock_at_order_day: null,
  count: { recorded_stock: -4, as_of: '2026-08-24', used: false, not_used_because: 'count_too_old', flags: [] } })
const BREAD = suggestion('7290011', 'לחם אחיד', { quantity: 16, capped: true, expected_sales: 56, stock_at_order_day: 0,
  shelf_life: { days: 2, stated_on: '2026-08-01' } }, 'מאפים')

const SLOTS = {
  [COLA.id]: ['product', 'quantity', 'expected', 'weeks', 'next_order', 'left'],
  [GROSS.id]: ['product', 'quantity', 'expected', 'weeks', 'next_order'],
  [BREAD.id]: ['product', 'quantity', 'expected', 'weeks', 'next_order', 'runs_out', 'capped'],
}
const TEXT = {
  [COLA.id]: { en: 'Ahead of {next_order}, {product} has {expected}, and {left}.', he: 'עבור {next_order}, ל{product} יש {expected}, ו{left}.', ar: 'بالنسبة إلى {next_order}، لدى {product} {expected}، و{left}.' },
  [GROSS.id]: { en: 'Sales of {product} are steady: {weeks}. So in {next_order}, the suggestion rests on {expected}.', he: 'המכירות של {product} יציבות: {weeks}. עבור {next_order}, {expected}.', ar: 'مبيعات {product} ثابتة: {weeks}. بالنسبة إلى {next_order}، {expected}.' },
  [BREAD.id]: { en: '{product} has {expected}. In {next_order}, the suggestion is {capped}, and {runs_out}.', he: 'ל{product} יש {expected}. עבור {next_order}, ההצעה היא {capped}, ו{runs_out}.', ar: 'لدى {product} {expected}. بالنسبة إلى {next_order}، الاقتراح هو {capped}، و{runs_out}.' },
}

const explained = (entry, overrides = {}) => ({
  suggestion_id: entry.id, slots: SLOTS[entry.id], text: TEXT[entry.id], prompt: 'mockup-sample',
  why_none: null, withheld_because: null, model: 'claude-sonnet-5', reused_from: null, ...overrides,
})
const notWritten = (entry) => ({ ...explained(entry), text: null, prompt: null, model: null, why_none: 'not_written_tonight' })

function artefact(orderExplanation) {
  const entries = [COLA, GROSS, BREAD]
  return {
    schema_version: 2,
    thresholds: { market_boost: { max_pct: 25 } },
    capabilities: {
      order_quantity: {
        id: 'order_quantity', status: 'available', unavailable_reason: null, entries, counts: {},
        thresholds: { window_days: 28, min_report_days: 21 },
        evidence_window: { first_day: '2026-07-30', last_day: '2026-08-26', report_days: 28, weeks: [] },
        departments: { 'משקאות': { reasons: {}, suggested: 2, covered_by_stock: 0 }, 'מאפים': { reasons: {}, suggested: 1, covered_by_stock: 0 } },
      },
      market_running_out: { status: 'available', products: {} },
      ...(orderExplanation ? { order_explanation: orderExplanation } : {}),
    },
  }
}

const available = (records) => ({
  id: 'order_explanation', status: 'available', unavailable_reason: null, explanations: records,
  counts: { suggestions: records.length, explained: records.filter((r) => r.text).length },
})

function draw(orderExplanation, language = 'en') {
  renderWithI18n(<ReorderPage artefact={artefact(orderExplanation)} ownerState={{ outcomes: {} }} onOutcome={() => {}} />, { language })
}

const card = (name) => [...document.querySelectorAll('[data-suggestion]')].find((c) => c.textContent.includes(name))
const note = () => document.querySelector('[data-ai-note]')

describe('without order_explanation, Reorder is today\'s page (FR-242)', () => {
  it('shows no note, no tag, and the engine\'s sentence on every card', () => {
    draw(undefined)
    expect(note()).toBeNull()
    expect(document.querySelector('[data-explanation]')).toBeNull()
    expect(card('קולה').textContent).toMatch(/about 3 will still be on the shelf on Sunday/)
    expect(card('לחם אחיד').textContent).toContain('Only what sells in 2 days, before it spoils.')
  })
})

describe('the AI\'s text on a card (FR-238, FR-242)', () => {
  it('replaces the engine\'s sentence, after the AI tag, with each slot filled from the published facts', () => {
    draw(available([explained(COLA), explained(GROSS), explained(BREAD)]))
    const cola = card('קולה')
    const ai = cola.querySelector('[data-explanation="shown"]')
    expect(ai.querySelector('.plan__ai-tag').textContent).toBe('AI')
    expect(ai.textContent).toContain('your order on Sunday 30 Aug, for the 7 days until the next one')
    expect(ai.textContent).toContain('about 14 expected to sell in the 7 days from the order day')
    expect(ai.textContent).toContain('about 3 left on the order day')
    expect(cola.textContent).not.toContain('will still be on the shelf')
    expect(cola.textContent).toContain('Order 11')
  })

  it('names the date once, in {next_order} only', () => {
    draw(available([explained(COLA), explained(GROSS), explained(BREAD)]))
    const text = card('קולה').querySelector('[data-explanation="shown"]').textContent
    expect(text.match(/30 Aug/g)).toHaveLength(1)
  })

  it('isolates each filled slot for direction', () => {
    draw(available([explained(COLA), explained(GROSS), explained(BREAD)]), 'he')
    const bdis = [...card('קולה').querySelectorAll('[data-explanation="shown"] bdi')].map((b) => b.textContent)
    expect(bdis).toContain('קולה')
    expect(bdis.some((t) => t.includes('ביום ההזמנה'))).toBe(true)
  })

  it('keeps the stock-count notice on a gross card, and lists the weeks oldest first', () => {
    draw(available([explained(COLA), explained(GROSS), explained(BREAD)]))
    const gross = card('ביסלי גריל')
    expect(gross.textContent).not.toContain("You'll sell about")
    expect(gross.textContent).toContain("Your stock count wasn't used")
    expect(gross.textContent).toContain('14, 14, 14 and 14 sold in the 4 weeks to 26 Aug')
  })

  it('replaces the shelf-life line with {capped}, in the language\'s own count of days', () => {
    draw(available([explained(COLA), explained(GROSS), explained(BREAD)]), 'ar')
    const bread = card('לחם אחיד')
    expect(bread.textContent).toContain('فقط ما يُباع خلال يومين، قبل أن يتلف')
    expect(bread.textContent).toContain('سينفد ما لديك قبل يوم الطلب')
    expect(bread.querySelectorAll('[data-explanation="shown"]')).toHaveLength(1)
    expect(bread.textContent).not.toContain('فقط ما يُباع خلال يومين، قبل أن يتلف.')
  })

  it('keeps the three buttons', () => {
    draw(available([explained(COLA), explained(GROSS), explained(BREAD)]))
    expect([...card('קולה').querySelectorAll('[data-action]')].map((b) => b.dataset.action)).toEqual(['approve', 'change', 'dismiss'])
  })
})

describe('a text the page cannot show leaves today\'s card (FR-242)', () => {
  it('when the text holds a slot not offered for it', () => {
    draw(available([explained(COLA), explained(GROSS, { text: { en: '{product}: {expected}, {next_order}, {left}.', he: 'x', ar: 'x' } }), explained(BREAD)]))
    expect(card('ביסלי גריל').querySelector('[data-explanation]')).toBeNull()
    expect(card('ביסלי גריל').textContent).toContain("You'll sell about 28 before your next order.")
  })

  it('when its prompt version is not one the phrases serve', () => {
    draw(available([explained(COLA, { prompt: 'a-prompt-these-phrases-were-not-written-for' }), explained(GROSS), explained(BREAD)]))
    expect(card('קולה').querySelector('[data-explanation]')).toBeNull()
    expect(card('קולה').textContent).toMatch(/about 3 will still be on the shelf on Sunday/)
  })

  it('when the capability is unavailable', () => {
    draw({ id: 'order_explanation', status: 'unavailable', unavailable_reason: 'no_model_key' })
    expect(document.querySelector('[data-explanation]')).toBeNull()
  })
})

describe('the note above the suggestions (FR-243)', () => {
  it('says what the AI does when it explained every suggestion', () => {
    draw(available([explained(COLA), explained(GROSS), explained(BREAD)]))
    expect(note().dataset.aiNote).toBe('all')
    expect(note().textContent).toContain("An AI writes each card's explanation from that suggestion's facts.")
    expect(document.querySelectorAll('[data-ai-note]')).toHaveLength(1)
  })

  it('counts them when only some were explained, from the published counts', () => {
    draw(available([explained(COLA), notWritten(GROSS), explained(BREAD)]))
    expect(note().dataset.aiNote).toBe('some')
    expect(note().textContent).toContain('Tonight the AI explained 2 of 3 suggestions.')
    expect(card('ביסלי גריל').textContent).toContain("You'll sell about 28 before your next order.")
  })

  it('says none were explained', () => {
    draw(available([notWritten(COLA), notWritten(GROSS), notWritten(BREAD)]))
    expect(note().dataset.aiNote).toBe('none')
    expect(note().textContent).toContain("The AI has not explained tonight's suggestions.")
  })

  it('says the explanations are off without a model key, in each language', () => {
    for (const [language, words] of [['en', "The AI's explanations are off"], ['he', 'ההסברים של הבינה המלאכותית כבויים'], ['ar', 'شروح الذكاء الاصطناعي متوقّفة']]) {
      draw({ id: 'order_explanation', status: 'unavailable', unavailable_reason: 'no_model_key' }, language)
      expect(note().textContent).toContain(words)
      cleanup()
    }
  })
})
