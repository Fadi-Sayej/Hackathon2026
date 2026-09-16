// @vitest-environment node
import { describe, expect, it } from 'vitest'

import { formatDays, formatStatus } from '../formatters.js'
import { createTranslator, LANGUAGES } from '../../../lib/i18n/index.js'

/**
 * These two functions sat between an engine that was careful and a screen that was not.
 *
 * `inventoryEngine` gates every velocity-derived verdict behind `hasVelocity` and emits
 * `daysUntilStockout: null`, under a comment reading "Without sales history every
 * velocity-derived verdict is unknowable, not false". `formatDays` then rendered that null
 * as "No sales" — converting an explicit unknown back into a claim, one layer downstream of
 * the guard that existed to prevent exactly this.
 *
 * It was not reaching the owner: all four call sites are on pages that left the nav at the
 * cut-over. Restoring those pages is what would have made it live, over a catalogue where
 * every one of 7,523 products reports null and 1,778 of them appear in sales_summary.parquet
 * with units_total > 0.
 */
describe('formatDays', () => {
  it('never states that an unknown rate is zero sales', () => {
    for (const language of Object.keys(LANGUAGES)) {
      const text = formatDays(null, createTranslator(language))
      expect(text).toBeTruthy()
      // The exact string that caused this. Guarding the English rather than the concept is
      // deliberate: it is the regression that actually happened.
      expect(text).not.toBe('No sales')
    }
    expect(formatDays(null)).not.toBe('No sales')
  })

  it('treats undefined the same as null — an absent field is not a zero', () => {
    expect(formatDays(undefined, createTranslator('en'))).toBe(formatDays(null, createTranslator('en')))
  })

  it('still formats a real figure, and carries the number into the translation', () => {
    expect(formatDays(4, createTranslator('en'))).toContain('4')
    expect(formatDays(4, createTranslator('he'))).toContain('4')
    // Interpolation failing silently would leave the placeholder visible.
    expect(formatDays(4, createTranslator('he'))).not.toContain('{days}')
  })

  it('falls back to readable English when no translator is passed', () => {
    expect(formatDays(null)).toBe('No sales data')
    expect(formatDays(0.5)).toBe('<1 day')
  })
})

/**
 * `inventoryEngine` uses the English sentence as both the internal key and the display text,
 * so these badges rendered in English beside Hebrew product names on an RTL page.
 */
describe('formatStatus', () => {
  // Read from the engine rather than restated, so a status added there without a
  // translation fails here instead of reaching the owner in English.
  const ENGINE_STATUSES = [
    'Healthy', 'Low stock', 'Stockout risk', 'Overstocked',
    'Slow moving', 'Near expiry', 'High priority', 'Not enough sales history yet',
  ]

  it('translates every status the engine can produce, in every language', () => {
    for (const language of Object.keys(LANGUAGES)) {
      const t = createTranslator(language)
      for (const status of ENGINE_STATUSES) {
        const text = formatStatus(status, t)
        expect(text).toBeTruthy()
        // A missing key makes the translator echo the key back.
        expect(text).not.toMatch(/^status\./)
        if (language !== 'en') expect(text).not.toBe(status)
      }
    }
  })

  it('shows the raw status rather than nothing when it cannot translate', () => {
    expect(formatStatus('Some new status', createTranslator('he'))).toBe('Some new status')
    expect(formatStatus('Healthy')).toBe('Healthy')
  })
})
