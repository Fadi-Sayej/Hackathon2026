/**
 * Every reason the engine can emit must have words, and an unknown one must still
 * be a sentence.
 *
 * This is the only text the store owner sees on the day a capability could not run,
 * and until #103 eight of the nine reasons had no translation at all — so the screen
 * read `unavailable.no_pos_data`. Nothing caught it: parity.test.js compares the
 * three dictionaries against each other and they were equally empty, and
 * checkpoint2's AC-112 scan only sees keys the committed artefact actually renders,
 * where no capability is unavailable.
 *
 * The reason code is domain vocabulary — the engine decides it and the artefact
 * carries it unchanged. Only this layer knows what it says to a person, which is the
 * same split already used for `characterisation.*`, `capability.*`, `count.*` and
 * `evidence.*`.
 */
import { describe, expect, it } from 'vitest'

import { ar } from '../dictionaries/ar.js'
import { en } from '../dictionaries/en.js'
import { he } from '../dictionaries/he.js'
import { createTranslator } from '../index.js'
import { UNKNOWN_REASON_KEY, unavailableReason } from '../unavailableReason.js'

/**
 * Every `unavailable_reason` src/engine can publish.
 *
 * Kept here rather than derived, because the producers are Python and the consumers
 * are JS with no shared enum between them — `schemas/dashboard.schema.json` types
 * the field as a bare string. Making the artefact contract carry the vocabulary is
 * the real fix and is an architecture change; see #103. Until then this list is the
 * seam, and `tests/engine/test_unavailable_reasons.py` asserts the engine emits
 * nothing outside it, so the two cannot drift apart silently.
 */
const ENGINE_REASONS = [
  // input-level, from registry.INPUT_REASONS
  'no_pos_data',
  'no_inventory_data',
  'no_sales_evidence',
  'no_competitor_data',
  'market_signal_thin',
  // rule-level, raised by the capabilities themselves
  'ceiling_degenerate',
  'no_delivery_prices',
  'no_comparable_source',
  'answer_storage_unavailable',
  'unknown_stock_date',
  'market_signal_stale',
  // run-level
  'capability_error',
]

const DICTIONARIES = { ar, he, en }

describe('every reason the engine can emit has words in every language', () => {
  for (const [language, dict] of Object.entries(DICTIONARIES)) {
    it(`${language} translates all ${ENGINE_REASONS.length}`, () => {
      const missing = ENGINE_REASONS.filter((reason) => !(`unavailable.${reason}` in dict))
      expect(missing, `untranslated in ${language}`).toEqual([])
    })
  }

  it('and the fallback itself is translated, or the fallback has no words either', () => {
    for (const [language, dict] of Object.entries(DICTIONARIES)) {
      expect(UNKNOWN_REASON_KEY in dict, `${language} lacks the fallback`).toBe(true)
    }
  })
})

describe('an unknown reason degrades to a sentence, not an identifier', () => {
  const t = createTranslator('en')

  it('renders the fallback for a reason this build has never heard of', () => {
    const text = unavailableReason(t, 'some_reason_invented_next_year')

    expect(text).not.toContain('unavailable.')
    expect(text).toBe(en[UNKNOWN_REASON_KEY])
  })

  it('renders the fallback when the reason is absent altogether', () => {
    expect(unavailableReason(t, null)).toBe(en[UNKNOWN_REASON_KEY])
    expect(unavailableReason(t, undefined)).toBe(en[UNKNOWN_REASON_KEY])
    expect(unavailableReason(t, '')).toBe(en[UNKNOWN_REASON_KEY])
  })

  it('still prefers the specific answer when there is one', () => {
    // The fallback must not swallow a reason that does have words — it is strictly
    // worse text, and this is the regression that would make it swallow everything.
    expect(unavailableReason(t, 'no_pos_data')).toBe(en['unavailable.no_pos_data'])
    expect(unavailableReason(t, 'no_pos_data')).not.toBe(en[UNKNOWN_REASON_KEY])
  })

  it('works in each language without leaking a key', () => {
    for (const language of Object.keys(DICTIONARIES)) {
      const translate = createTranslator(language)
      for (const reason of [...ENGINE_REASONS, 'not_a_real_reason']) {
        expect(unavailableReason(translate, reason)).not.toMatch(/^unavailable\./)
      }
    }
  })
})
