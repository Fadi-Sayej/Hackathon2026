// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, screen } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { DailyPage } from '../DailyPage.jsx'
import { AppShell } from '../../components/layout/AppShell.jsx'

afterEach(cleanup)

// F2-V4 and F2-V7 (docs/reviews/F2-validation.md), wording approved by the repository owner
// on 2026-09-24. These render the real card and the real page shell and read the screen.

const reconciliationEntry = {
  id: 'r1',
  signal_family: 'recon.impossible_opening',
  capability: 'reconciliation',
  barcode: '7622300489427',
  product_name: 'מוצר לבדיקה',
  department: 'dept',
  action: 'count_product',
  characterisation: 'inconsistent',
  evidence: { recorded_stock: -4, receipts: 20, units_sold: 8, unaccounted: 16,
              window_id: '2026-01..2026-05', reconcile_months: 2 },
  value: null,
  ordering_key: { name: 'gap_ratio', value: 0.8 },
}

const artefact = {
  schema_version: 2,
  thresholds: { surface: { bound: 10, unvalued_places: 3, unvalued_order: ['reconciliation'] } },
  capabilities: {
    reconciliation: { status: 'available', unavailable_reason: null, counts: {}, entries: [reconciliationEntry] },
  },
}

const renderCard = (language) =>
  renderWithI18n(
    <DailyPage artefact={artefact} ownerState={{ outcomes: {} }} onOutcome={() => {}} now={1_790_208_000_000} />,
    { language },
  )

describe('F2-V7 — the reconciliation card speaks the owner\'s language', () => {
  const cases = [
    ['he', 'חודשים בבדיקה', 'ינואר–מאי 2026'],
    ['ar', 'الأشهر في الفحص', 'كانون الثاني–أيار ٢٠٢٦'],
    ['en', 'Months checked', 'January–May 2026'],
  ]

  it.each(cases)('%s: the months label is translated, and the period is months, not an id', (language, label, period) => {
    renderCard(language)

    expect(screen.getByText(label)).toBeTruthy()
    expect(screen.getByText(period)).toBeTruthy()
    expect(screen.queryByText('reconcile months')).toBeNull()
    expect(screen.queryByText('2026-01..2026-05')).toBeNull()
  })
})

describe('F2-V4 / AC-023 — the reconciliation page says the loss is known only after a count', () => {
  // FR-026: the amount is not determinable before a physical count. The F2 intent's own
  // sentence: «والرقم الحقيقي يُعرف بعد العدّ، لا قبله».
  const cases = [
    ['he', 'כמה חסר באמת יודעים רק אחרי ספירה.'],
    ['ar', 'الرقم الحقيقي يُعرف بعد العدّ، لا قبله.'],
    ['en', 'How much is really missing is known only after a count.'],
  ]

  it.each(cases)('%s: the sentence is on the page', (language, sentence) => {
    renderWithI18n(<AppShell activePage="reconciliation" onNavigate={() => {}}>{null}</AppShell>, { language })

    expect(screen.getByText(sentence, { exact: false })).toBeTruthy()
  })
})
