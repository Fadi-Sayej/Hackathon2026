// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { DailyPage } from '../DailyPage.jsx'

afterEach(cleanup)

const NOW = 1_757_000_000_000
const THRESHOLDS = { surface: { bound: 10, unvalued_places: 3, unvalued_order: ['reconciliation'] } }

let seq = 0
const entry = (over = {}) => ({
  id: `id${(seq += 1)}`,
  signal_family: 'price.inverted',
  capability: 'price_consistency',
  barcode: `bc${seq}`,
  product_name: `Product ${seq}`,
  department: 'dept',
  action: 'verify_price',
  characterisation: 'confirmed_loss',
  evidence: { shelf_price: 29.9 },
  value: null,
  ordering_key: { name: 'x', value: 1 },
  ...over,
})

const artefact = (capabilities) => ({ schema_version: 2, thresholds: THRESHOLDS, capabilities })
const cap = (entries, over = {}) => ({ status: 'available', unavailable_reason: null, counts: {}, entries, ...over })

const render = (capabilities, { outcomes = {}, onOutcome = vi.fn() } = {}) => {
  renderWithI18n(
    <DailyPage artefact={artefact(capabilities)} ownerState={{ outcomes }} onOutcome={onOutcome} now={NOW} />,
  )
  return onOutcome
}

describe('AC-104 — an estimated value is labelled on the card', () => {
  it('labels it where the number is, not in a legend', () => {
    render({ price_consistency: cap([entry({ value: { amount: 7, kind: 'per_sale', certainty: 'estimated' } })]) })
    const card = document.querySelector('.entry-card__value')
    expect(card.getAttribute('data-certainty')).toBe('estimated')
    expect(card.querySelector('.entry-card__estimated')).not.toBeNull()
  })

  it('does not label a confirmed value as estimated', () => {
    render({ price_consistency: cap([entry({ value: { amount: 7, kind: 'per_sale', certainty: 'confirmed' } })]) })
    expect(document.querySelector('.entry-card__estimated')).toBeNull()
  })
})

describe('D-3 — an entry with no value renders no value area', () => {
  it('renders no value element at all, not a dash or a zero', () => {
    render({ price_consistency: cap([entry({ value: null })]) })
    expect(document.querySelector('.entry-card__value')).toBeNull()
    expect(screen.queryByText(/^0(\.00)?$/)).toBeNull()
    expect(screen.queryByText('—')).toBeNull()
  })
})

describe('AC-111 — no velocity claim without sales evidence', () => {
  it('renders only the evidence the entry carries', () => {
    render({ price_consistency: cap([entry({ evidence: { shelf_price: 29.9, delivery_price: 22.9 } })]) })
    const text = document.body.textContent
    expect(text).not.toMatch(/per day|days? (?:left|remaining|to)|units\/day/i)
  })
})

describe('AC-107 — an unavailable capability is named with its reason', () => {
  it('shows it and does not claim there is nothing to do', () => {
    render({ price_consistency: cap([], { status: 'unavailable', unavailable_reason: 'no_delivery_prices' }) })
    expect(document.querySelector('[data-capability="price_consistency"]')).not.toBeNull()
    expect(document.querySelector('.daily__empty')).toBeNull()
  })
})

describe('AC-108 — nothing to do is explicit', () => {
  it('states it rather than rendering a blank page', () => {
    render({ price_consistency: cap([]) })
    expect(document.querySelector('.daily__empty')).not.toBeNull()
  })
})

describe('AC-105 — recording an outcome', () => {
  it('passes the whole entry so the snapshot can carry the signal family', async () => {
    const onOutcome = render({ price_consistency: cap([entry()]) })
    await userEvent.click(screen.getAllByRole('button')[0])
    expect(onOutcome).toHaveBeenCalledTimes(1)
    const [passed, outcome] = onOutcome.mock.calls[0]
    expect(passed.signal_family).toBe('price.inverted')   // ADR-016
    expect(outcome.status).toBe('acted')
  })

  it('does not remove the entry when the write fails, and says so', async () => {
    const failing = vi.fn().mockRejectedValue(new Error('QuotaExceeded'))
    render({ price_consistency: cap([entry()]) }, { onOutcome: failing })
    await userEvent.click(screen.getAllByRole('button')[0])
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(document.querySelectorAll('.entry-card')).toHaveLength(1)
  })

  it('shows an entry whose outcome is already recorded as gone', () => {
    const e = entry()
    render({ price_consistency: cap([e]) }, { outcomes: { [e.id]: { status: 'acted' } } })
    expect(document.querySelectorAll('.entry-card')).toHaveLength(0)
  })
})
