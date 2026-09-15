// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, screen } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { DataPage } from '../DataPage.jsx'

afterEach(cleanup)

const artefact = (over = {}) => ({
  schema_version: 2,
  generated_at: '2026-09-12T11:00:00+00:00',
  run: { status: 'ok', steps: [{ step: 'load_inputs', status: 'ok', ms: 10, error: null }] },
  vintages: {
    pos: { file: 'yomyom-inventory.csv', as_of: '2026-08-02' },
    sales: { months: ['2026-01', '2026-07'], first: '2026-01', last: '2026-07', full_annual_cycle: false },
    competitor: { snapshot_date: '2026-09-05', sources: ['wolt'] },
    owner_state: { pulled_at: '2026-09-12T11:00:00+00:00', status: 'available' },
  },
  capabilities: { price_consistency: { status: 'available', unavailable_reason: null, counts: {}, entries: [] } },
  ...over,
})

describe('ADR-017 — whether this run’s reports arrived', () => {
  it('renders unknown when the field is absent, never true', () => {
    renderWithI18n(<DataPage artefact={artefact()} />)
    const el = document.querySelector('[data-field="imported_this_run"]')
    expect(el.textContent).toMatch(/unknown|غير معروف|לא ידוע/i)
    expect(el.textContent).not.toMatch(/^yes$|^true$/i)
  })

  it('renders the value when the engine publishes it', () => {
    const a = artefact()
    a.vintages.sales.imported_this_run = false
    renderWithI18n(<DataPage artefact={a} />)
    const el = document.querySelector('[data-field="imported_this_run"]')
    expect(el.textContent).toMatch(/no|لا|לא/i)
  })
})

describe('the run verdict', () => {
  it('names the step that caused a degraded run', () => {
    renderWithI18n(<DataPage artefact={artefact({
      run: { status: 'degraded', steps: [
        { step: 'owner_state_pull', status: 'degraded', ms: 5, error: 'no_credentials' },
        { step: 'load_inputs', status: 'ok', ms: 10, error: null },
      ] },
    })} />)
    const cause = document.querySelector('.data__cause')
    expect(cause.textContent).toMatch(/owner_state_pull/)
  })

  it('names the step that errored in a partial run', () => {
    renderWithI18n(<DataPage artefact={artefact({
      run: { status: 'partial', steps: [{ step: 'sales_import', status: 'error', ms: 5, error: 'boom' }] },
    })} />)
    expect(document.querySelector('.data__cause').textContent).toMatch(/sales_import/)
  })

  it('shows no cause for an ok run', () => {
    renderWithI18n(<DataPage artefact={artefact()} />)
    expect(document.querySelector('.data__cause')).toBeNull()
  })
})

describe('vintages', () => {
  it('shows the POS export date and the sales window', () => {
    renderWithI18n(<DataPage artefact={artefact()} />)
    expect(screen.getByText('2026-08-02')).toBeTruthy()
    expect(document.querySelector('[data-field="sales_window"]').textContent).toMatch(/2026-01.*2026-07/)
  })

  it('shows the owner-state status and when it was pulled', () => {
    renderWithI18n(<DataPage artefact={artefact()} />)
    expect(document.querySelector('[data-field="owner_state"]').textContent).toMatch(/available|متاح|זמין/i)
  })

  it('shows a null vintage as absent rather than blank', () => {
    const a = artefact()
    a.vintages.competitor.snapshot_date = null
    renderWithI18n(<DataPage artefact={a} />)
    expect(document.querySelector('[data-field="competitor"]').textContent).toMatch(/none|no data|لا|אין/i)
  })
})

describe('capability statuses', () => {
  it('lists every capability with its status', () => {
    renderWithI18n(<DataPage artefact={artefact({
      capabilities: {
        price_consistency: { status: 'available', unavailable_reason: null, counts: {}, entries: [] },
        owner_questions: { status: 'unavailable', unavailable_reason: 'answer_storage_unavailable', counts: {}, entries: [] },
      },
    })} />)
    expect(document.querySelectorAll('[data-capability-status]')).toHaveLength(2)
    expect(document.querySelector('[data-capability-status="owner_questions"]').textContent)
      .toMatch(/answers|إجابات|תשובות/i)
  })
})

describe('ADR-021 — the device register on the data page', () => {
  const withDevices = (devices) => {
    const a = artefact()
    a.vintages.owner_state.devices = devices
    return a
  }

  it('shows the count and the most recent save', () => {
    renderWithI18n(<DataPage artefact={withDevices({
      status: 'available', reason: null, count: 3,
      last_seen_at: ['2026-08-30T11:02:00Z', '2026-09-12T09:14:02Z', '2026-09-13T07:41:55Z'],
    })} />)
    const el = document.querySelector('[data-field="owner_devices"]')
    expect(el.textContent).toContain('3')
    expect(el.textContent).toContain('2026-09-13T07:41:55Z')   // the latest, not the first
  })

  it('shows nothing rather than zero when nobody has registered', () => {
    // ARCH-DRIVER-002 and rule 8. "0 browsers" is a claim about the pilot; the absence of a
    // register is a fact about the artefact, and only one of them is true here.
    renderWithI18n(<DataPage artefact={withDevices({
      status: 'unavailable', reason: 'not_registered', count: null, last_seen_at: [],
    })} />)
    const el = document.querySelector('[data-field="owner_devices"]')
    expect(el.textContent).not.toMatch(/\b0\b/)
    expect(el.textContent).toMatch(/none|لا يوجد|אין/i)
  })

  it('shows nothing on an artefact published before the register existed', () => {
    renderWithI18n(<DataPage artefact={artefact()} />)
    expect(document.querySelector('[data-field="owner_devices"]').textContent).not.toMatch(/\b0\b/)
  })

  it('never calls them devices, in any of the three dictionaries', async () => {
    // ADR-021: clearing site data mints a new id and two browsers on one phone count twice,
    // so a label saying "devices" states a bound the number does not have.
    for (const lang of ['he', 'en', 'ar']) {
      const dict = Object.values(await import(`../../lib/i18n/dictionaries/${lang}.js`))[0]
      expect(dict['data.devices']).toBeTruthy()
      expect(dict['data.devices.counted']).toContain('{n}')
    }
    const en = Object.values(await import('../../lib/i18n/dictionaries/en.js'))[0]
    expect(en['data.devices']).not.toMatch(/device|phone/i)
  })
})
