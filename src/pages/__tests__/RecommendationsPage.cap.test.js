/**
 * The list must never truncate silently.
 *
 * Reorder now runs on the whole catalogue rather than only competitor-matched
 * products, so the candidate count is larger. Capping is fine; hiding the cap is
 * not — the owner has to know a shorter list is a view, not the whole answer.
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

const source = readFileSync('src/pages/RecommendationsPage.jsx', 'utf8')

describe('reorder list capping', () => {
  it('ranks by money at stake before capping', () => {
    expect(source).toMatch(/sort\(\(a, b\) => \(b\.valueAtStake \?\? 0\) - \(a\.valueAtStake \?\? 0\)\)/)
    // The slice must come after the sort, or the cap keeps arbitrary rows.
    expect(source.indexOf('.sort(')).toBeLessThan(source.indexOf('.slice(0, MAX_VISIBLE_RECOMMENDATIONS)'))
  })

  it('states the cap on screen rather than truncating silently', () => {
    expect(source).toContain('rec.showingTopOf')
    expect(source).toContain('rec.showingAll')
  })

  it('reports the true total, not the capped length', () => {
    // `total` must come from the full ranked list; reporting the slice length
    // would say "showing 30 of 30" on a list of 101.
    expect(source).toMatch(/total: ranked\.length/)
  })
})

describe('the cap message exists in every language', () => {
  it.each(['he', 'ar', 'en'])('%s carries both keys', async (lang) => {
    const dict = Object.values(await import(`../../lib/i18n/dictionaries/${lang}.js`))[0]
    expect(dict['rec.showingTopOf']).toBeTruthy()
    expect(dict['rec.showingAll']).toBeTruthy()
    expect(dict['rec.showingTopOf']).toContain('{shown}')
    expect(dict['rec.showingTopOf']).toContain('{total}')
  })
})
