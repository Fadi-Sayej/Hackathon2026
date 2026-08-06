import { describe, expect, it } from 'vitest'
import { formatPercent, formatPercentagePoints } from '../format.js'

// Strip the LRI/PDI bidi isolates so assertions read plainly.
const plain = (value) => value.replace(/[⁦-⁩]/g, '')

describe('formatPercentagePoints', () => {
  // The pipeline's `metricValue` is in percentage POINTS. Passing it to
  // formatPercent multiplies anything at or below 1 by 100, which is how a
  // 0.5-point gap became "50%" on the store-floor screen. This is the guard.
  it('does not inflate a sub-1 point value', () => {
    expect(plain(formatPercentagePoints(0.5))).toBe('0.50%')
    expect(plain(formatPercent(0.5))).toBe('50%') // the wrong function, for contrast
  })

  it('keeps whole points whole', () => {
    expect(plain(formatPercentagePoints(12))).toBe('12%')
    expect(plain(formatPercentagePoints(100))).toBe('100%')
  })

  it('keeps two decimals for fractional points', () => {
    expect(plain(formatPercentagePoints(12.5))).toBe('12.50%')
  })

  it('handles negatives', () => {
    expect(plain(formatPercentagePoints(-3))).toBe('-3%')
  })

  it.each([null, undefined, '', '   ', 'abc', NaN, Infinity])(
    'falls back to an em-dash for %p',
    (value) => {
      expect(formatPercentagePoints(value)).toBe('—')
    },
  )

  it('accepts numeric strings', () => {
    expect(plain(formatPercentagePoints('7.25'))).toBe('7.25%')
  })
})
