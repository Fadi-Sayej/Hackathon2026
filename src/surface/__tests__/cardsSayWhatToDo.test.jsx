// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { cleanup } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { DailyPage } from '../DailyPage.jsx'
import { en } from '../../lib/i18n/dictionaries/en.js'
import { ar } from '../../lib/i18n/dictionaries/ar.js'
import { he } from '../../lib/i18n/dictionaries/he.js'

/**
 * Found by the 2026-09-28 validations (docs/reviews/F3…F7-validation.md):
 *   - no card said what to do, though every entry carries an action (F6 AC-110c);
 *   - a finding with a list or an object in its evidence printed "[object Object]" (F3);
 *   - codes and the engine's English note printed raw, under labels left in English in
 *     Arabic and Hebrew (F3, F4 AC-069, F6 AC-112);
 *   - an unknown value printed "null" (D-3);
 *   - Today stated its figures without the date of the stock file they rest on (F7 AC-120).
 * The entries below have the shape the engine publishes today, one per kind of evidence.
 */
afterEach(cleanup)

const base = { department: 'dept', value: null, ordering_key: { name: 'k', value: 1 }, actionable: true, attention: 'today' }

const PRICE = { ...base, id: 'p1', signal_family: 'price.inverted', capability: 'price_consistency', barcode: '1',
  product_name: 'מים', action: 'verify_price', characterisation: 'confirmed_loss',
  value: { amount: 16, kind: 'per_sale', certainty: 'confirmed' },
  evidence: { shelf_price: 9.9, delivery_price: 8.9, difference: -1, markup_pct: -10.1, ceiling_pct: 18, commission_compounds: true } }

const COMPETITOR = { ...base, id: 'c1', signal_family: 'competitor.policy_breach', capability: 'competitor_position', barcode: '2',
  product_name: 'במבה', action: 'review_policy', characterisation: 'policy_breach_review', attention: 'review',
  evidence: { shelf_price: 9.9, cost_price: 2.59,
    reference: { value: 5.5681, kind: 'supermarket_plus_allowance', same_format: null, supermarket: 5.2, allowance_pct: 7.0779 },
    premium_pct: 77.8, policy_pct: 60, attention_pct: 100, cost_floor_pct: 10,
    sources: [{ store_id: 'a', format: 'supermarket', price: 5.2, role: 'context' }, { store_id: 'b', format: 'unknown', price: 5.9, role: 'context' }],
    format_note: 'part of any difference is attributable to store format' } }

const IMPLAUSIBLE = { ...base, id: 'i1', signal_family: 'catalogue.implausible_quantity', capability: 'catalogue_lifecycle', barcode: '3',
  product_name: 'כוס', action: 'decide_idle', characterisation: 'implausible_quantity',
  evidence: { recorded_stock: 4005, unit_cost: null, evidence_state: 'no_row', window_id: '2026-01..2026-07', question: 'is_this_quantity_right' } }

const DUPLICATE = { ...base, id: 'h1', signal_family: 'hygiene.conflicting_duplicate', capability: 'hygiene', barcode: '4',
  product_name: 'קפה', action: 'fix_record', characterisation: 'hygiene',
  evidence: { reason: 'conflicting_duplicate', fields: { cost_price: [3.1, 3.4], department: ['a', 'b'] }, cost_source: 'pos' } }

const artefact = (entries) => ({
  schema_version: 2,
  vintages: { pos: { as_of: '2026-06-06' } },
  thresholds: { surface: { bound: 10, unvalued_places: 3, unvalued_order: ['reconciliation', 'competitor_position', 'catalogue_lifecycle', 'hygiene'] } },
  capabilities: {
    price_consistency: { status: 'available', entries: entries.filter((e) => e.capability === 'price_consistency') },
    competitor_position: { status: 'available', entries: entries.filter((e) => e.capability === 'competitor_position') },
    catalogue_lifecycle: { status: 'available', entries: entries.filter((e) => e.capability === 'catalogue_lifecycle') },
    hygiene: { status: 'available', entries: entries.filter((e) => e.capability === 'hygiene') },
  },
})

const draw = (language, entries = [PRICE, COMPETITOR, IMPLAUSIBLE]) =>
  renderWithI18n(<DailyPage artefact={artefact(entries)} ownerState={{ outcomes: {} }} onOutcome={() => {}}
    now={1_790_208_000_000} />, { language })

const card = (id) => document.querySelector(`[data-entry-id="${id}"]`)

describe('every card says what to do (F6 AC-110c)', () => {
  it('states the action the engine chose, in the owner\'s words', () => {
    draw('en', [PRICE, COMPETITOR, IMPLAUSIBLE, DUPLICATE])
    expect(card('p1').querySelector('.entry-card__action').textContent).toBe(en['action.verify_price'])
    expect(card('c1').querySelector('.entry-card__action').textContent).toBe(en['action.review_policy'])
    expect(card('i1').querySelector('.entry-card__action').textContent).toBe(en['action.decide_idle'])
  })

  it('has words for every action the engine can publish, in all three languages', () => {
    for (const action of ['verify_price', 'count_product', 'fix_record', 'decide_idle', 'review_policy', 'check_purchase_cost', 'raise_delivery_price']) {
      for (const dict of [en, ar, he]) expect(dict[`action.${action}`], action).toBeTruthy()
    }
  })
})

describe('the evidence reads as words and figures, never as code', () => {
  for (const language of ['ar', 'he', 'en']) {
    it(`prints no object, no null, no raw code and no engine English, in ${language}`, () => {
      draw(language, [PRICE, COMPETITOR, IMPLAUSIBLE])
      const text = document.body.textContent
      expect(text).not.toMatch(/\[object Object\]|\bnull\b|undefined/)
      expect(text).not.toMatch(/is_this_quantity_right|no_row|supermarket_plus_allowance|attributable to store format/)
      if (language !== 'en') expect(text).not.toMatch(/\b(pct|premium|reference|sources|format note|question)\b/)
    })
  }

  it('states the reference as a price and how it was made', () => {
    draw('en', [COMPETITOR])
    const text = card('c1').textContent
    expect(text).toContain('₪5.57')
    expect(text).toContain('₪5.20')
    expect(text).toContain('7.1%')
  })

  it('counts the shops a comparison rests on', () => {
    draw('en', [COMPETITOR])
    expect(card('c1').textContent).toContain('2 shops')
  })

  it('puts shekels on prices and a percent sign on percentages', () => {
    draw('en', [PRICE])
    const text = card('p1').textContent
    expect(text).toContain('₪9.90')
    expect(text).toContain('10.1%')                  // how far the delivery price is below the shelf
  })

  it('leaves out a value the engine does not have, rather than printing null (D-3)', () => {
    draw('en', [IMPLAUSIBLE])
    const labels = [...card('i1').querySelectorAll('.entry-card__evidence dt')].map((dt) => dt.textContent)
    expect(labels).not.toContain(en['evidence.unit_cost'])
    expect(labels).toContain(en['evidence.recorded_stock'])
  })

  it('asks the question once, as the card\'s line, not again as a row', () => {
    draw('en', [IMPLAUSIBLE])
    expect(card('i1').querySelector('.entry-card__what').textContent).toBe(en['characterisation.implausible_quantity'])
    expect([...card('i1').querySelectorAll('.entry-card__evidence dt')].map((dt) => dt.textContent))
      .not.toContain(en['evidence.question'])
  })

  it('names the fields a duplicate disagrees on', () => {
    draw('en', [DUPLICATE])
    const text = card('h1').textContent
    expect(text).toContain(en['evidence.cost_price'])
    expect(text).toContain(en['evidence.department'])
  })
})

describe('an implausible quantity is asked, not asserted (F4 AC-069)', () => {
  it('reads as a question in every language', () => {
    for (const dict of [en, ar, he]) expect(dict['characterisation.implausible_quantity']).toMatch(/[?؟]$/)
  })
})

describe('Today says what date its figures come from (F7 AC-120)', () => {
  it('states the stock file\'s date once, above the cards', () => {
    draw('en', [PRICE])
    expect(document.querySelector('.daily__as-of').textContent).toContain('6 June 2026')
  })

  it('says nothing about a date the artefact does not carry', () => {
    renderWithI18n(<DailyPage artefact={{ ...artefact([PRICE]), vintages: {} }} ownerState={{ outcomes: {} }}
      onOutcome={() => {}} now={1_790_208_000_000} />, { language: 'en' })
    expect(document.querySelector('.daily__as-of')).toBeNull()
  })
})

describe('no label the owner can see is left in English (F6 AC-112)', () => {
  it('every evidence, threshold and action label in Arabic and Hebrew is written in that language', () => {
    for (const [name, dict] of [['ar', ar], ['he', he]]) {
      const english = Object.entries(dict)
        .filter(([key]) => /^(evidence|threshold|action)\./.test(key))
        .filter(([, value]) => typeof value === 'string' && /^[A-Za-z0-9 ,.%()'/-]+$/.test(value))
      expect(english, name).toEqual([])
    }
  })
})
