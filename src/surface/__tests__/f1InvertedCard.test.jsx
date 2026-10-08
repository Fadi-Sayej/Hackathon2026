// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { cleanup } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { DailyPage } from '../DailyPage.jsx'
import { en } from '../../lib/i18n/dictionaries/en.js'
import { ar } from '../../lib/i18n/dictionaries/ar.js'
import { he } from '../../lib/i18n/dictionaries/he.js'

/**
 * F1's inverted-price card, reworded on the repository owner's request (2026-10-08): six figures
 * and "Check this product's prices" did not say what was wrong. It now says the delivery price is
 * below the shelf price, what to do, and what each delivery order loses, with the commission
 * on top (F1-S1 FR-007), and shows only the two prices. A price above the ceiling, a question,
 * is unchanged: the ceiling matters there.
 */
afterEach(cleanup)

const base = { department: 'מוצרי בית', ordering_key: { name: 'loss_per_sale', value: 16 }, actionable: true, attention: 'today' }

const INVERTED = { ...base, id: 'inv', signal_family: 'price.inverted', capability: 'price_consistency', barcode: '1',
  product_name: 'שמן זית קלאסי 500 מ״ל', action: 'raise_delivery_price', characterisation: 'confirmed_loss',
  value: { amount: 16, kind: 'per_sale', certainty: 'confirmed' },
  evidence: { shelf_price: 37.9, delivery_price: 21.9, difference: -16, markup_pct: -42.22, ceiling_pct: 18, commission_compounds: true } }

const ABOVE = { ...base, id: 'abv', signal_family: 'price.above_ceiling', capability: 'price_consistency', barcode: '2',
  product_name: 'במבה', action: 'verify_price', characterisation: 'question', value: null,
  evidence: { shelf_price: 5, delivery_price: 7, difference: 2, markup_pct: 40, ceiling_pct: 18 } }

const artefact = (entries) => ({
  schema_version: 2, vintages: { pos: { as_of: '2026-06-06' } },
  thresholds: { surface: { bound: 10, unvalued_places: 3, unvalued_order: ['price_consistency'] } },
  capabilities: { price_consistency: { status: 'available', entries } },
})

const draw = (language, entries = [INVERTED, ABOVE]) =>
  renderWithI18n(<DailyPage artefact={artefact(entries)} ownerState={{ outcomes: {} }} onOutcome={() => {}}
    now={1_790_208_000_000} />, { language })

const card = (id) => document.querySelector(`[data-entry-id="${id}"]`)
const labels = (id) => [...card(id).querySelectorAll('.entry-card__evidence dt')].map((dt) => dt.textContent)

describe('an inverted delivery price, in words', () => {
  it('says what is wrong, what to do, and what each delivery order loses', () => {
    draw('en')
    const c = card('inv')
    expect(c.querySelector('.entry-card__what').textContent).toBe(en['characterisation.price_inverted'])
    expect(c.querySelector('.entry-card__action').textContent).toBe(en['action.raise_delivery_price'])
    expect(c.querySelector('.entry-card__amount').textContent).toContain('₪16.00')
    expect(c.querySelector('.entry-card__kind').textContent).toBe(en['value.kind.price_inverted'])
  })

  it('still calls it a loss, and says the commission comes on top (F1-S1 FR-007)', () => {
    expect(en['value.kind.price_inverted']).toMatch(/lost/)
    expect(en['value.kind.price_inverted']).toMatch(/commission/)
  })

  it('shows the two prices and how far below the shelf the delivery price is, and nothing else', () => {
    draw('en')
    expect(labels('inv')).toEqual([en['evidence.shelf_price'], en['evidence.delivery_price']])
    const text = card('inv').querySelector('.entry-card__evidence').textContent
    expect(text).toContain('₪37.90'); expect(text).toContain('₪21.90'); expect(text).toContain('42.2%')
    expect(text).not.toContain('18%'); expect(text).not.toMatch(/\byes\b/); expect(text).not.toContain('-₪16')
  })

  for (const language of ['ar', 'he', 'en']) {
    it(`prints no raw key, in ${language}`, () => {
      draw(language)
      expect(card('inv').textContent).not.toMatch(/price_inverted|raise_delivery_price|below_shelf|undefined|null/)
    })
  }

  it('has its words in all three languages', () => {
    for (const key of ['characterisation.price_inverted', 'action.raise_delivery_price', 'value.kind.price_inverted',
      'evidence.delivery_price.below_shelf']) for (const dict of [en, ar, he]) expect(dict[key], key).toBeTruthy()
  })
})

describe('a price above the ceiling is unchanged', () => {
  it('is still a question to check, with the ceiling it is measured against', () => {
    draw('en')
    const c = card('abv')
    expect(c.querySelector('.entry-card__what').textContent).toBe(en['characterisation.question'])
    expect(c.querySelector('.entry-card__action').textContent).toBe(en['action.verify_price'])
    expect(labels('abv')).toContain(en['evidence.ceiling_pct'])
    expect(labels('abv')).toContain(en['evidence.markup_pct'])
  })
})
