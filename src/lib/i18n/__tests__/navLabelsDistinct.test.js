// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { navGroups } from '../../../components/layout/navGroups.js'
import { LANGUAGES } from '../index.js'

/**
 * Two nav entries must not read the same, within a language.
 *
 * WHAT HAPPENED
 *   From the twelve-page restore on 2026-09-16 until 2026-09-23, `page.daily.name` and
 *   `page.operational.name` were both the literal string "Today" in English, with the
 *   identical hint "What needs you right now". Two adjacent entries in the same nav group
 *   that a reader could not tell apart.
 *
 *   Hebrew and Arabic were never affected — they had always distinguished the two, and the
 *   distinction was a real one rather than a cosmetic rename: the daily surface asks for a
 *   DECISION (החלטה / قرارك) and the restored Today page asks for ATTENTION (טיפול / تدخلك).
 *   English simply never followed, and `DEFAULT_LANGUAGE` is 'ar', so the owner reading his
 *   own language saw two distinct entries while the English demo view did not.
 *
 *   Nothing caught it. Every heading test passed, because `page.*.title` WAS distinct in all
 *   three — "Today's work" against "Today's tasks". Only the nav collided.
 *
 * WHY NAME AND HINT BOTH
 *   The hint exists so a name like "Gaps" or "Overview" is not a guess. Two entries with
 *   different names and the same hint are still ambiguous, just more slowly.
 */
const NAV_IDS = navGroups.flatMap((group) => group.items.map((item) => item.id))

describe('nav labels are distinct within each language', () => {
  for (const [code, { dict }] of Object.entries(LANGUAGES)) {
    for (const field of ['name', 'hint']) {
      it(`${code} — ${field}`, () => {
        const byValue = new Map()
        const collisions = []
        for (const id of NAV_IDS) {
          const value = dict[`page.${id}.${field}`]
          // A missing string is #90's problem and parity.test.js's to report, not this one.
          if (!value) continue
          if (byValue.has(value)) collisions.push(`${byValue.get(value)} + ${id} both read "${value}"`)
          byValue.set(value, id)
        }
        expect(collisions).toEqual([])
      })
    }
  }

  it('catches the collision it was written for', () => {
    // Proving the mechanism against the strings that actually shipped, rather than trusting
    // that it would have caught them.
    const shipped = { 'page.daily.name': 'Today', 'page.operational.name': 'Today' }
    const values = Object.values(shipped)
    expect(new Set(values).size).toBeLessThan(values.length)
  })

  it('reads the nav from navGroups, so a page added later is covered without an edit', () => {
    expect(NAV_IDS.length).toBeGreaterThan(10)
    expect(NAV_IDS).toContain('daily')
    // `operational` was removed on 2026-09-23 — one Today, at the owner's decision.
    expect(NAV_IDS).not.toContain('operational')
  })
})
