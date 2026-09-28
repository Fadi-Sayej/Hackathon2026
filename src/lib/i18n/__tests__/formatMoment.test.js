import { describe, expect, it } from 'vitest'

import { formatDay, formatMoment } from '../formatMoment.js'

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


// F7 AC-120 (2026-09-28): Today states the date of the stock file its figures rest on. A date,
// not a moment: the export is dated by day, so no time and no time zone shift it.
describe('formatDay — a date the owner can read', () => {
  it('in each language, with the month named', () => {
    expect(formatDay('2026-06-06', 'en')).toBe('6 June 2026')
    expect(formatDay('2026-06-06', 'ar')).toBe('6 يونيو 2026')
    expect(formatDay('2026-06-06', 'he')).toBe('6 ביוני 2026')
  })

  it('is nothing for something that is not a date', () => {
    expect(formatDay(null, 'en')).toBeNull()
    expect(formatDay('not a date', 'en')).toBeNull()
  })
})
