// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { DailyPage } from '../DailyPage.jsx'
import { en } from '../../lib/i18n/dictionaries/en.js'
import { ar } from '../../lib/i18n/dictionaries/ar.js'
import { he } from '../../lib/i18n/dictionaries/he.js'

/**
 * Phase 6 Task 6.5: F9's card (F9-S1 FR-173, FR-175, FR-177).
 *
 * The entry has the shape the engine publishes (src/engine/assortment_gap.py): the stores by
 * name, how many of the recent days it ran out, the last day it did, and which stores list it
 * today. The card must say all of that in the owner's words, and nothing else: no ₪ figure
 * (D-25), no code, no ISO date, and the two answers he was promised.
 */
afterEach(cleanup)

const GAP = {
  id: 'g1', signal_family: 'assortment.market_ran_out', capability: 'assortment_gap', barcode: '7290000467511',
  product_name: 'ביסלי ברביקיו 5×55 גרם', department: null, action: 'try_product', characterisation: 'market_ran_out',
  value: null, ordering_key: { name: 'nights_ran_out', value: 6 }, actionable: true, attention: 'today',
  evidence: {
    stores_ran_out: ['Wolt Market | Lev Haaretz', 'Super Alonit Einat (Wolt)'], nights_ran_out: 6,
    last_ran_out: '2026-09-27', listed_at: [],
    window: { first: '2026-09-15', last: '2026-09-28', days: 14, usable_nights: 13 },
    market_name: 'ביסלי ברביקיו 5×55 גרם',
    market_prices: [
      { store: 'Rami Levy In The Neighborhood', price: 42.9, sale_price: 34.9, on: '2026-09-22' },
      { store: 'Super Alonit Einat (Wolt)', price: 46.9, sale_price: null, on: '2026-09-14' },
    ],
  },
}

const PRICE = {
  id: 'p1', signal_family: 'price.inverted', capability: 'price_consistency', barcode: '1', product_name: 'מים',
  department: 'd', action: 'verify_price', characterisation: 'confirmed_loss', actionable: true, attention: 'today',
  value: { amount: 16, kind: 'per_sale', certainty: 'confirmed' }, ordering_key: { name: 'k', value: 1 },
  evidence: { shelf_price: 9.9, delivery_price: 8.9, difference: -1, markup_pct: -10.1 },
}

const artefact = (entries) => ({
  schema_version: 2,
  vintages: { pos: { as_of: '2026-06-06' } },
  thresholds: { surface: { bound: 10, unvalued_places: 3,
    unvalued_order: ['assortment_gap', 'reconciliation', 'competitor_position', 'catalogue_lifecycle', 'hygiene'],
    unvalued_caps: { assortment_gap: 1 }, engine_ordered: ['assortment_gap'] } },
  capabilities: {
    price_consistency: { status: 'available', entries: entries.filter((e) => e.capability === 'price_consistency') },
    assortment_gap: { status: 'available', entries: entries.filter((e) => e.capability === 'assortment_gap') },
  },
})

const draw = (language, entries = [GAP], { onOutcome = () => {}, readOnly = false } = {}) =>
  renderWithI18n(<DailyPage artefact={artefact(entries)} ownerState={{ outcomes: {} }} onOutcome={onOutcome}
    now={1_790_208_000_000} readOnly={readOnly} />, { language })

const card = (id) => document.querySelector(`[data-entry-id="${id}"]`)

describe('F9 card — what it says (FR-175)', () => {
  it('says what was seen and what to decide, in the owner\'s words', () => {
    draw('en')
    const c = card('g1')
    expect(c.querySelector('.entry-card__what').textContent).toBe(en['characterisation.market_ran_out'])
    expect(c.querySelector('.entry-card__action').textContent).toBe(en['action.try_product'])
    expect(c.textContent).toContain('Wolt Market | Lev Haaretz')
    expect(c.textContent).toContain('Super Alonit Einat (Wolt)')
    expect(c.textContent).toContain(en['evidence.nights_ran_out.value'].replace('{n}', '6').replace('{days}', '14'))
    expect(c.textContent).toContain(en['evidence.listed_at.none'])
  })

  it('sets its sentences in the text face, not the figures face that spaces Hebrew and Arabic apart', () => {
    draw('he')
    const dds = [...card('g1').querySelectorAll('.entry-card__evidence dd')]
    expect(dds.length).toBe(5)
    expect(dds.every((dd) => dd.hasAttribute('data-text'))).toBe(true)
  })

  it('names the stores that list it today when some do', () => {
    draw('en', [{ ...GAP, evidence: { ...GAP.evidence, listed_at: ['Rami Levy In The Neighborhood'] } }])
    expect(card('g1').textContent).toContain('Rami Levy In The Neighborhood')
    expect(card('g1').textContent).not.toContain(en['evidence.listed_at.none'])
  })

  for (const language of ['ar', 'he', 'en']) {
    it(`prints no code, no ISO date, no object, no price and no repeated name, in ${language}`, () => {
      draw(language)
      const text = card('g1').textContent
      expect(text).not.toMatch(/\[object Object\]|\bnull\b|undefined/)
      expect(text).not.toMatch(/stores_ran_out|nights_ran_out|last_ran_out|listed_at|market_name|usable_nights/)
      expect(text).not.toContain('2026-09-27')
      expect(text).not.toContain('2026-09-22')
      // D-27: the only ₪ on the card is what the market lists it at, in its own row.
      const rows = [...card('g1').querySelectorAll('.entry-card__evidence > div')]
      for (const row of rows) if (!row.textContent.includes('Rami Levy')) expect(row.textContent).not.toMatch(/₪/)
      expect(text.split('ביסלי ברביקיו').length - 1).toBe(1)          // the header only
    })
  }

  it('has every word it uses in all three languages', () => {
    const keys = ['characterisation.market_ran_out', 'action.try_product', 'evidence.stores_ran_out',
      'evidence.nights_ran_out', 'evidence.nights_ran_out.value', 'evidence.last_ran_out', 'evidence.listed_at',
      'evidence.listed_at.none', 'outcome.assortment_gap.acted', 'outcome.assortment_gap.declined', 'capability.assortment_gap',
      'evidence.market_prices', 'evidence.market_prices.item', 'evidence.market_prices.sale', 'outcome.assortment_gap.already_sold']
    for (const key of keys) for (const dict of [en, ar, he]) expect(dict[key], key).toBeTruthy()
  })
})

describe('F9 card — the two answers (FR-173, FR-177)', () => {
  it('offers "I\'ll try it", "Not for my store", "I already sell it" and "Later" (D-27)', () => {
    draw('en')
    const labels = [...card('g1').querySelectorAll('.entry-card__actions button')].map((b) => b.textContent)
    expect(labels).toEqual([en['outcome.assortment_gap.acted'], en['outcome.assortment_gap.declined'],
      en['outcome.assortment_gap.already_sold'], en['outcome.deferred']])
  })

  it('records "I already sell it" as a decline for a reason of its own (D-27)', () => {
    const onOutcome = vi.fn()
    draw('en', [GAP], { onOutcome })
    fireEvent.click(card('g1').querySelector('[data-outcome="already_sold"]'))
    expect(onOutcome.mock.calls[0][1]).toEqual({ status: 'declined', reason: 'already_handled' })
  })

  it('records "I\'ll try it" as acted and "Not for my store" as declined with no reason', () => {
    const onOutcome = vi.fn()
    draw('en', [GAP], { onOutcome })
    fireEvent.click(card('g1').querySelector('[data-outcome="acted"]'))
    fireEvent.click(card('g1').querySelector('[data-outcome="declined"]'))
    expect(onOutcome.mock.calls.map((c) => c[1])).toEqual([{ status: 'acted' }, { status: 'declined', reason: null }])
  })

  it('leaves every other card\'s answers as they were', () => {
    const onOutcome = vi.fn()
    draw('en', [PRICE], { onOutcome })
    const buttons = [...card('p1').querySelectorAll('.entry-card__actions button')]
    expect(buttons.map((b) => b.textContent)).toEqual([en['outcome.acted'], en['outcome.declined'], en['outcome.deferred']])
    fireEvent.click(card('p1').querySelector('[data-outcome="declined"]'))
    expect(onOutcome.mock.calls[0][1]).toEqual({ status: 'declined', reason: 'not_worth_it' })
  })

  it('is read-only for a team account', () => {
    draw('en', [GAP], { readOnly: true })
    expect([...card('g1').querySelectorAll('.entry-card__actions button')].every((b) => b.disabled)).toBe(true)
  })
})

describe('F9 card — what the market lists it at (D-27)', () => {
  it('states each store\'s delivery-app price, the sale price when there is one, and the day', () => {
    draw('en')
    const text = card('g1').textContent
    expect(text).toContain(en['evidence.market_prices'])
    expect(text).toContain('₪42.90'); expect(text).toContain('₪34.90'); expect(text).toContain('₪46.90')
    expect(text).toContain('22 September'); expect(text).toContain('14 September')
    const lines = [...card('g1').querySelectorAll('[data-row="market_prices"] .entry-card__line')].map((l) => l.textContent)
    expect(lines).toHaveLength(2)                               // one store to a line
    expect(lines[0]).toContain('Rami Levy'); expect(lines[1]).toContain('Super Alonit')
  })

  it('shows no price row at all when the snapshot had none, never a zero', () => {
    draw('en', [{ ...GAP, evidence: { ...GAP.evidence, market_prices: [] } }])
    const text = card('g1').textContent
    expect(text).not.toContain(en['evidence.market_prices'])
    expect(text).not.toMatch(/₪/)
  })
})

