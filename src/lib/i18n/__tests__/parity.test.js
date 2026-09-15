import { describe, expect, it } from 'vitest'
import { ar } from '../dictionaries/ar.js'
import { en } from '../dictionaries/en.js'
import { he } from '../dictionaries/he.js'
import { NAV_PAGE_IDS } from '../../../components/layout/navGroups.js'

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

/**
 * #90 — nine of the ten V1 pages rendered `page.<id>.title` as their heading, live, for
 * days. The parity test above could not see it: parity compares the dictionaries against
 * EACH OTHER, and these keys were missing from all three, so the three agreed perfectly.
 *
 * So this one compares them against the thing that consumes them. AppShell renders
 * `page.<id>.name`, `.hint`, `.title` and `.description` for every id in the nav; a page
 * added to the nav without its four strings is the defect, and it is invisible to every
 * test that starts from the dictionaries.
 *
 * e2e/v1-navigation.spec.js is the other half — it proves the rendered heading is not a raw
 * key — but it can only catch a key missing from Arabic, because the translator falls back
 * to Arabic before it falls back to the key. A Hebrew or English gap shows Arabic on screen
 * and passes there. It fails here instead.
 */
describe('every page in the nav has its four strings, in all three dictionaries', () => {
  it.each(['ar', 'he', 'en'])('%s', (name) => {
    const dict = DICTS[name]
    const missing = NAV_PAGE_IDS.flatMap((id) =>
      ['name', 'hint', 'title', 'description']
        .map((part) => `page.${id}.${part}`)
        .filter((key) => !(key in dict)),
    )
    expect(missing).toEqual([])
  })

  it('the nav is not empty, so the check above is not vacuous', () => {
    expect(NAV_PAGE_IDS.length).toBeGreaterThan(0)
  })
})
