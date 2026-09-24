import { describe, expect, it } from 'vitest'

import { createTranslator } from '../index.js'
import { formatWindowId } from '../formatPeriod.js'

// F2-V7 (docs/reviews/F2-validation.md): the reconciliation card printed its period as the
// engine's id, `2026-01..2026-05`, under the label "the period". The id is right since
// ADR-026; it was just not in the owner's language. Expected strings are written out by
// hand, never built with the code under test.
const fmt = (id, language) => formatWindowId(id, createTranslator(language), language)

describe('formatWindowId — the period in the owner\'s language', () => {
  it('Hebrew: one year, a range of months', () => {
    expect(fmt('2026-01..2026-05', 'he')).toBe('ינואר–מאי 2026')
  })

  it('English: one year, a range of months', () => {
    expect(fmt('2026-01..2026-05', 'en')).toBe('January–May 2026')
  })

  it('Arabic: Levantine month names and Arabic-Indic digits, as the rest of the Arabic UI', () => {
    expect(fmt('2026-01..2026-05', 'ar')).toBe('كانون الثاني–أيار ٢٠٢٦')
  })

  it('a range across two years names both years', () => {
    expect(fmt('2025-11..2026-02', 'en')).toBe('November 2025–February 2026')
  })

  it('a single month is not written as a range', () => {
    expect(fmt('2026-03..2026-03', 'en')).toBe('March 2026')
  })

  it('anything that is not a month range is shown exactly as published, never hidden', () => {
    expect(fmt('None..None', 'he')).toBe('None..None')
    expect(fmt('2026-13..2026-14', 'en')).toBe('2026-13..2026-14')
    expect(fmt('garbage', 'ar')).toBe('garbage')
  })
})
