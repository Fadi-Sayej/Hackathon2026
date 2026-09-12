import { describe, expect, it } from 'vitest'
import { ar } from '../dictionaries/ar.js'
import { en } from '../dictionaries/en.js'
import { he } from '../dictionaries/he.js'

/**
 * AC-112 — the surface renders in all three languages with no untranslated key.
 *
 * A key present in one dictionary and absent from another does not crash: the translator
 * falls back to Arabic and then to the key itself, so an English page silently shows
 * `daily.nothingToDo` to a judge, or an Arabic string to an English reader. Neither is
 * visible in a screenshot of the language you happen to be testing in.
 *
 * This test is what makes the next task that adds a string break the suite rather than the
 * pilot.
 */

const DICTS = { ar, he, en }

describe('AC-112 — key parity across the three dictionaries', () => {
  it('every dictionary holds exactly the same keys', () => {
    const keys = Object.fromEntries(Object.entries(DICTS).map(([name, d]) => [name, new Set(Object.keys(d))]))
    const union = new Set(Object.values(keys).flatMap((s) => [...s]))

    const missing = {}
    for (const [name, set] of Object.entries(keys)) {
      const gaps = [...union].filter((k) => !set.has(k)).sort()
      if (gaps.length) missing[name] = gaps
    }
    expect(missing).toEqual({})
  })

  it('no value is an empty string, which renders as a missing label', () => {
    const blank = []
    for (const [name, dict] of Object.entries(DICTS)) {
      for (const [key, value] of Object.entries(dict)) {
        if (typeof value !== 'string' || value.trim() === '') blank.push(`${name}:${key}`)
      }
    }
    expect(blank).toEqual([])
  })

  it('every placeholder in a key is present in all three languages', () => {
    // `{product}` missing from one language drops the product name silently.
    const placeholders = (s) => [...String(s).matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(',')
    const mismatched = Object.keys(ar)
      .filter((k) => k in en && k in he)
      .filter((k) => new Set([placeholders(ar[k]), placeholders(he[k]), placeholders(en[k])]).size > 1)
    expect(mismatched).toEqual([])
  })
})
