// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, screen } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { CapabilityPage } from '../CapabilityPage.jsx'

afterEach(cleanup)

const entry = (i) => ({
  id: `id${i}`, signal_family: 'price.inverted', capability: 'price_consistency',
  barcode: `bc${i}`, product_name: `Product ${i}`, department: 'd',
  action: 'verify_price', characterisation: 'confirmed_loss',
  evidence: {}, value: null, ordering_key: { name: 'x', value: i },
})

const artefact = (cap) => ({ schema_version: 2, thresholds: {}, capabilities: { price_consistency: cap } })

describe('AC-110 — the full set stays reachable away from the daily surface', () => {
  it('renders every entry, not the surface bound of ten', () => {
    const many = Array.from({ length: 25 }, (_, i) => entry(i))
    renderWithI18n(<CapabilityPage artefact={artefact({ status: 'available', unavailable_reason: null, counts: { above: 25 }, entries: many })} capabilityId="price_consistency" />)
    expect(document.querySelectorAll('[data-entry-id]')).toHaveLength(25)
  })

  it('shows the capability’s own counts, not the surface’s', () => {
    renderWithI18n(<CapabilityPage artefact={artefact({ status: 'available', unavailable_reason: null, counts: { above: 107, inverted: 53 }, entries: [entry(1)] })} capabilityId="price_consistency" />)
    expect(screen.getByText('107')).toBeTruthy()
    expect(screen.getByText('53')).toBeTruthy()
  })
})

describe('AC-107 — unavailable is not zero', () => {
  it('names the reason and renders no count block', () => {
    renderWithI18n(<CapabilityPage artefact={artefact({ status: 'unavailable', unavailable_reason: 'no_delivery_prices', counts: {}, entries: [] })} capabilityId="price_consistency" />)
    expect(document.querySelector('.capability__unavailable')).not.toBeNull()
    expect(document.querySelector('.capability__counts')).toBeNull()
    expect(screen.queryByText('0')).toBeNull()
  })
})

describe('a capability absent from the artefact', () => {
  it('says so rather than rendering an empty page', () => {
    renderWithI18n(<CapabilityPage artefact={artefact({ status: 'available', counts: {}, entries: [] })} capabilityId="does_not_exist" />)
    expect(document.querySelector('.capability__missing')).not.toBeNull()
  })
})

describe('thresholds travel with the counts', () => {
  it('renders the thresholds that governed the finding (F7-S1)', () => {
    renderWithI18n(<CapabilityPage artefact={artefact({ status: 'available', unavailable_reason: null, counts: { above: 3 }, thresholds: { ceiling_pct: 18 }, entries: [] })} capabilityId="price_consistency" />)
    expect(document.querySelector('.capability__thresholds')).not.toBeNull()
    expect(screen.getByText('18')).toBeTruthy()
  })
})
