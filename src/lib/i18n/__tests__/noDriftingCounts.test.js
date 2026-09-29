// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { LANGUAGES } from '../index.js'

/**
 * A figure in a translated string must be one that does not move.
 *
 * WHAT HAPPENED
 *   `awaiting.competitor.why` shipped on 2026-09-21 saying the run had matched 2,618
 *   products, evaluated 860 and withheld 854. By the next morning the artefact said 2,619,
 *   856 and 850 — with no scrape and no code change, because competitor freshness is
 *   measured against RUN TIME, so products age out of `evaluated` into `stale_skipped` while
 *   nobody touches anything. Three dictionaries, three languages, wrong within a day.
 *
 * THE DISTINCTION THIS GUARDS, WHICH IS NOT "NO NUMBERS"
 *   Some figures in these strings are stable and belong there. "24.3% of the catalogue" is a
 *   property of the seven sales reports (rule 13) and will be true for as long as those are
 *   the reports. "9 August" is the date a file was frozen. Those are facts about the world.
 *
 *   A count of what a capability produced last night is not. It belongs in the artefact the
 *   page is rendering, read at render time, or nowhere.
 *
 * So this is an allowlist with reasons rather than a ban, and adding to it should require
 * writing down why the number cannot move.
 */
const FIGURES_ALLOWED = {
  'awaiting.demand.why':
    '24.3% catalogue coverage is a property of the seven monthly reports (rule 13), fixed for as long as they are the reports',
  'awaiting.expiry.why':
    'the date capture began is a date',
  'awaiting.expiry.what':
    'the date capture began is a date',
  'awaiting.demand.when':
    '"V2" is a release name, not a measurement',
  'awaiting.withdrawn.why':
    '"D-12" is a decision id, not a measurement',
}

const AWAITING = /^awaiting\.[a-z]+\.(title|what|why|when)$/

describe('no drifting count reaches a translated string', () => {
  for (const [code, { dict }] of Object.entries(LANGUAGES)) {
    it(`${code}`, () => {
      const offenders = []
      for (const [key, value] of Object.entries(dict)) {
        if (!AWAITING.test(key)) continue
        if (FIGURES_ALLOWED[key]) continue
        // Arabic-Indic digits too: the dictionaries are written with Western digits today,
        // but a translator working in ar would not necessarily keep them.
        if (/[0-9٠-٩]/.test(value)) offenders.push(key)
      }
      expect(offenders, `figures in ${offenders.join(', ')} — read the count from the `
        + 'artefact at render time, or add it to FIGURES_ALLOWED with a reason it cannot move')
        .toEqual([])
    })
  }

  it('the allowlist names only keys that exist, in every language', () => {
    // An entry left behind after its string was rewritten silently stops guarding it.
    for (const [code, { dict }] of Object.entries(LANGUAGES)) {
      for (const key of Object.keys(FIGURES_ALLOWED)) {
        expect(dict[key], `${key} missing from ${code}`).toBeTruthy()
      }
    }
  })

  it('catches the regression it was written for', () => {
    // Proving the mechanism rather than trusting it: the exact string that shipped.
    const shipped = 'matched 2,618 of your products ... the other 854 do not'
    expect(/[0-9٠-٩]/.test(shipped)).toBe(true)
  })
})
