// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

/**
 * Every prop App hands a page must be one that page actually accepts.
 *
 * WHY THIS EXISTS
 *   App.jsx passed `actions={ownerState.outcomes}` to OperationalPage for five days.
 *   OperationalPage destructures `decisions = {}` and has no `actions` prop, so the value
 *   arrived as nothing and the default `{}` won every time. An entry the owner settled on
 *   the daily surface still showed as open on the old Today page.
 *
 *   The commit that shipped it claimed the opposite in as many words — "the two surfaces
 *   write through the same path, so they cannot disagree about what the owner has already
 *   dealt with". True of the writes. The reads were never connected.
 *
 *   Nothing caught it and nothing could have: React does not warn about an unknown prop on
 *   a custom component, the page's own tests pass `decisions` directly, and App's behaviour
 *   is only exercised end-to-end where both pages are checked separately. A misspelt prop
 *   is silent by construction.
 *
 * WHAT IT CHECKS, AND WHAT IT DOES NOT
 *   Source-level, deliberately: it reads the props App passes at each call site and the
 *   parameters each component destructures, and asserts the first is a subset of the second.
 *   It does NOT check that a prop is used correctly, only that it is received at all. That
 *   is the whole failure mode here — the value was right and the name was wrong.
 */
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const read = (p) => readFileSync(resolve(ROOT, p), 'utf8')

/** Props passed at `<Name ... />` in App.jsx — `foo={...}` and bare `foo`. */
function propsPassedTo(source, name) {
  // Non-greedy to the first `/>` or `>` that closes the opening tag.
  const open = new RegExp(`<${name}(\\s[^]*?)(?:/>|>)`, 'g')
  const found = new Set()
  for (const match of source.matchAll(open)) {
    const attrs = match[1]
    // Strip JSX comments and nested braces conservatively: only take identifiers that sit
    // at the start of a line or after whitespace and are followed by `=` or whitespace.
    for (const attr of attrs.matchAll(/(?:^|\s)([a-zA-Z_$][\w$]*)=/g)) found.add(attr[1])
  }
  return found
}

/** Parameters a component destructures from its single props object. */
function propsAcceptedBy(source, name) {
  const fn = source.match(new RegExp(`export function ${name}\\(\\s*\\{([^]*?)\\}\\s*\\)`))
  if (!fn) return null
  return new Set(
    fn[1]
      .replace(/\/\*[^]*?\*\//g, '')
      .replace(/\/\/[^\n]*/g, '')
      .split(',')
      .map((part) => part.split('=')[0].trim())
      .filter(Boolean),
  )
}

const app = read('src/App.jsx')

// OperationalPage left this list on 2026-09-23 with the old Today page. It is no longer
// rendered by App, so there are no props to check — and asserting on a component App does
// not mount would pass forever without meaning anything.
const PAGES = [
  ['ProductsPage', 'src/pages/ProductsPage.jsx'],
  ['PriceGapPage', 'src/pages/PriceGapPage.jsx'],
  ['CapabilityPage', 'src/pages/CapabilityPage.jsx'],
  ['DataPage', 'src/pages/DataPage.jsx'],
  ['PageAwaitingData', 'src/pages/PageAwaitingData.jsx'],
  ['DailyPage', 'src/surface/DailyPage.jsx'],
]

describe('every prop App passes is one the page accepts', () => {
  for (const [name, path] of PAGES) {
    it(`${name}`, () => {
      const accepted = propsAcceptedBy(read(path), name)
      expect(accepted, `${name} should destructure a props object`).not.toBeNull()
      const passed = propsPassedTo(app, name)
      expect(passed.size, `App should pass props to ${name}`).toBeGreaterThan(0)
      const unknown = [...passed].filter((prop) => !accepted.has(prop))
      expect(unknown, `${name} does not accept: ${unknown.join(', ')}`).toEqual([])
    })
  }

  it('catches the exact regression it was written for', () => {
    // A guard that cannot fail is not a guard. The original case re-broke the live App.jsx;
    // the page it broke is gone, so the mechanism is proved against a fixture carrying the
    // exact shape that shipped — `actions=` passed to a component destructuring `decisions`.
    const brokenApp = '<OperationalPage operationalData={x} actions={y} onDecide={z} />'
    const component = 'export function OperationalPage({ operationalData, decisions = {}, onDecide }) {'
    const accepted = propsAcceptedBy(component, 'OperationalPage')
    const passed = propsPassedTo(brokenApp, 'OperationalPage')
    expect([...passed].filter((prop) => !accepted.has(prop))).toEqual(['actions'])
  })

  it('still finds props on the pages App does render', () => {
    // Guards the guard: if the JSX regex stopped matching, every page would report zero
    // unknown props and the suite would go green on a check that had stopped running.
    expect(propsPassedTo(app, 'DailyPage').size).toBeGreaterThan(0)
    expect(propsPassedTo(app, 'DataPage').size).toBeGreaterThan(0)
  })
})
