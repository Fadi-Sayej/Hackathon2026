import { describe, expect, it } from 'vitest'

import { formatMoment } from '../formatMoment.js'

// The Data page printed the engine's timestamps as they are stored,
// `2026-09-27T03:06:42.142275+00:00`, which a phone breaks mid-string. Approved on
// 2026-09-27: day, short month, year and a 24-hour time, in the reader's own time zone.
// Pinned to Israel here so the expected strings can be written out by hand.
const IL = 'Asia/Jerusalem'
const PULLED = '2026-09-27T03:06:42.142275+00:00'

describe('formatMoment — a timestamp the owner can read', () => {
  it('English', () => {
    expect(formatMoment(PULLED, 'en', IL)).toBe('27 Sept 2026, 06:06')
  })

  it('Hebrew', () => {
    expect(formatMoment(PULLED, 'he', IL)).toBe('27 בספט׳ 2026, 06:06')
  })

  it('Arabic, with the Latin digits the other date screens use', () => {
    expect(formatMoment(PULLED, 'ar', IL)).toBe('27 سبتمبر 2026، 06:06')
  })

  it('is local time, not UTC: late evening in UTC is the next day in Israel', () => {
    expect(formatMoment('2026-09-13T22:30:00Z', 'en', IL)).toBe('14 Sept 2026, 01:30')
  })

  it.each([[null], [undefined], [''], ['not a date']])('returns null for %j, so the page shows "none"', (value) => {
    expect(formatMoment(value, 'en', IL)).toBeNull()
  })
})
