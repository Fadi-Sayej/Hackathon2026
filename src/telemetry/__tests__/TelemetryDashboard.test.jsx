// @vitest-environment jsdom

import { readFileSync } from 'node:fs'
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'

import { TelemetryDashboard } from '../TelemetryDashboard.jsx'

/**
 * F13-S1 (Phase 4 Task 4.5): the team's measurement page renders public/data/measurement.json
 * and computes nothing (ADR-023, ADR-001). AC-130, AC-132, AC-134, AC-162, AC-163.
 */
afterEach(cleanup)

const counts = (over = {}) => ({ shown: 0, decided: 0, acted: 0, declined: 0, deferred: 0, not_in_this_run: 0, ...over })

const FILE = {
  schema_version: 1,
  generated_at: '2026-09-27T03:06:40Z',
  run_id: 'abc',
  inputs_digest: 'd',
  devices: { status: 'available', reason: null, count: 4, last_seen_at: [] },
  status: 'available',
  unavailable_reason: null,
  window: { first: '2026-09-16T11:05:30Z', last: '2026-09-24T10:03:00Z', pulled_at: '2026-09-27T03:06:42Z' },
  totals: counts({ shown: 3350, decided: 5, acted: 3, declined: 1, deferred: 1, not_in_this_run: 1 }),
  by_family: {
    'hygiene.negative_stock': counts({ shown: 243, decided: 1, declined: 1 }),
    'price.inverted': counts({ shown: 68, decided: 4, acted: 3, deferred: 1, not_in_this_run: 1 }),
  },
  money: [
    { kind: 'per_sale', certainty: 'confirmed', amount: 5.75, decisions: 2 },
    { kind: 'per_sale', certainty: 'estimated', amount: 2, decisions: 1 },
  ],
  declined_reasons: { wrong_data: 1 },
}

const draw = async (result) => {
  render(<TelemetryDashboard load={async () => result} />)
  await screen.findByRole('heading', { level: 1 })
  await new Promise((r) => setTimeout(r, 0))
}

const text = () => document.body.textContent

describe('a published measurement', () => {
  it('states each count as published, and the share acted on within the decisions', async () => {
    await draw({ status: 'ok', body: FILE })
    const card = (label) => [...document.querySelectorAll('.t-card')].find((c) => c.textContent.includes(label))
    expect(card('Shown in this run').textContent).toContain('3,350')
    expect(card('Decided').textContent).toContain('5')
    expect(card('Acted on').textContent).toContain('3')
    expect(card('Acted on').textContent).toContain('60% of decided')
  })

  it('states money one row per kind and certainty, never a total over them (AC-133, AC-162)', async () => {
    await draw({ status: 'ok', body: FILE })
    const rows = [...document.querySelectorAll('[data-money]')].map((r) => r.textContent)
    expect(rows).toHaveLength(2)
    expect(rows[0]).toContain('₪5.75')
    expect(rows[0]).toContain('per sale')
    expect(rows[0]).toContain('confirmed')
    expect(rows[1]).toContain('₪2.00')
    expect(rows[1]).toContain('estimated')
    expect(text()).not.toContain('₪7.75')
  })

  it('lists each family with what it showed and what was decided, and nothing crossing the two (AC-132)', async () => {
    await draw({ status: 'ok', body: FILE })
    const row = [...document.querySelectorAll('[data-family]')].find((r) => r.dataset.family === 'price.inverted')
    expect(row.textContent).toContain('68')
    expect(row.textContent).toContain('75%')
    expect(text()).not.toMatch(/Ignored/)
    expect(text()).not.toMatch(/Recent decisions/)
  })

  it('names its window, the run it counted and the devices, and no target (AC-163)', async () => {
    await draw({ status: 'ok', body: FILE })
    expect(text()).toContain('2026-09-16')
    expect(text()).toContain('2026-09-24')
    expect(text()).toContain('2026-09-27')
    expect(text()).toMatch(/4 devices/)
    expect(text()).not.toMatch(/target/i)
  })
})

describe('what it says instead of a number', () => {
  it('says nothing is recorded yet, not that everything was dismissed (AC-134, INV-068)', async () => {
    await draw({ status: 'ok', body: { ...FILE, totals: counts({ shown: 3350 }), by_family: {}, money: [], declined_reasons: {} } })
    expect(text()).toContain('No decisions recorded yet')
    expect(text()).not.toMatch(/0% of decided/)
    expect(text()).not.toMatch(/₪\s*\d/)                  // no amount, and no ₪0
  })

  it('says the measurement has not been published yet, and shows no number (FR-142)', async () => {
    await draw({ status: 'missing' })
    expect(text()).toContain('has not been published yet')
    expect(document.querySelectorAll('.t-card')).toHaveLength(0)
  })

  it('says it is unavailable, with the engine\'s reason (AC-134)', async () => {
    await draw({ status: 'ok', body: { ...FILE, status: 'unavailable', unavailable_reason: 'pull_failed: RuntimeError',
      totals: undefined, by_family: undefined, money: undefined, declined_reasons: undefined } })
    expect(text()).toContain('pull_failed: RuntimeError')
    expect(document.querySelectorAll('.t-card')).toHaveLength(0)
  })
})

it('reads the measurement file and no owner state (AC-130)', () => {
  const page = readFileSync('src/telemetry/TelemetryDashboard.jsx', 'utf-8')
  const loader = readFileSync('src/lib/dataAdapters/loadMeasurement.js', 'utf-8')
  expect(page).toContain("from '../lib/dataAdapters/loadMeasurement.js'")
  expect(loader).toContain("'/data/measurement.json'")
  for (const source of [page, loader]) expect(source).not.toMatch(/operational|persistence|ownerState|localStorage/)
})
