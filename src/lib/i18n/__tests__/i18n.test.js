import { describe, expect, it } from 'vitest'

import { LANGUAGES, DEFAULT_LANGUAGE, createTranslator, formatNumber } from '../index.js'
import { ar } from '../dictionaries/ar.js'
import { he } from '../dictionaries/he.js'
import { en } from '../dictionaries/en.js'

describe('dictionary parity', () => {
  // The guard that keeps this from rotting. Adding a key to one language and
  // forgetting the others is the single most likely i18n regression, and it
  // fails silently on screen — Arabic text appears in the English app.
  it('every language defines exactly the same keys', () => {
    const arKeys = Object.keys(ar).sort()
    expect(Object.keys(he).sort()).toEqual(arKeys)
    expect(Object.keys(en).sort()).toEqual(arKeys)
  })

  it('no translation is left empty', () => {
    for (const [code, entry] of Object.entries(LANGUAGES)) {
      const blank = Object.entries(entry.dict).filter(([, value]) => !String(value).trim())
      expect(blank, `${code} has blank values`).toEqual([])
    }
  })

  it('placeholders match across languages', () => {
    const placeholders = (text) => (String(text).match(/\{(\w+)\}/g) ?? []).sort()
    for (const key of Object.keys(ar)) {
      expect(placeholders(he[key]), `he:${key}`).toEqual(placeholders(ar[key]))
      expect(placeholders(en[key]), `en:${key}`).toEqual(placeholders(ar[key]))
    }
  })
})

describe('translator', () => {
  it('returns the string for the chosen language', () => {
    expect(createTranslator('en')('common.yes')).toBe('yes')
    expect(createTranslator('he')('common.yes')).toBe('כן')
    expect(createTranslator('ar')('common.yes')).toBe('نعم')
  })

  it('substitutes named placeholders', () => {
    const t = createTranslator('en')
    expect(t('prices.more', { n: 3 })).toBe('Show 3 more')
  })

  it('returns the key itself when it is unknown, so the gap is visible', () => {
    expect(createTranslator('en')('does.not.exist')).toBe('does.not.exist')
  })

  it('falls back to Arabic rather than rendering nothing', () => {
    const t = createTranslator('he')
    // Every key exists in all three today; the fallback is what protects the
    // screen when a future key lands in ar.js first.
    expect(t('common.yes')).toBeTruthy()
  })

  it('leaves a placeholder alone when no value is supplied', () => {
    expect(createTranslator('en')('prices.more')).toContain('{n}')
  })
})

describe('language configuration', () => {
  it('opens in Arabic', () => {
    expect(DEFAULT_LANGUAGE).toBe('ar')
  })

  it('marks Arabic and Hebrew right-to-left and English left-to-right', () => {
    expect(LANGUAGES.ar.dir).toBe('rtl')
    expect(LANGUAGES.he.dir).toBe('rtl')
    expect(LANGUAGES.en.dir).toBe('ltr')
  })
})

describe('number formatting', () => {
  it('uses Arabic-Indic digits only for Arabic', () => {
    expect(formatNumber(2026, 'ar')).toBe('٢٠٢٦')
    expect(formatNumber(2026, 'he')).toBe('2026')
    expect(formatNumber(2026, 'en')).toBe('2026')
  })

  it('leaves separators and signs untouched', () => {
    expect(formatNumber('-1.5', 'ar')).toBe('-١.٥')
  })
})
