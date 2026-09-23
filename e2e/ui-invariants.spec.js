import { expect, test } from '@playwright/test'

/**
 * Open every collapsible nav group.
 *
 * The six capability pages sit behind one heading, closed by default — the owner asked for a
 * shorter nav and dropping a route to get there would have cost him 1,671 findings. They are
 * one tap away, so a test that walks "every page" has to take the tap rather than conclude
 * the pages are gone.
 */
async function expandNav(page) {
  // Visible ones only. On a phone the nav is a bottom bar, the toggle is hidden and the
  // group is never collapsed — the items are always in the DOM and CSS hides them only
  // above 900px. Clicking a `display: none` heading there just times out.
  const shut = page.locator('.nav-group-toggle[aria-expanded="false"]')
  for (const toggle of await shut.all()) {
    if (await toggle.isVisible()) await toggle.click()
  }
}

/**
 * SKIPPED AT THE CUT-OVER (2026-09-12).
 *
 * The browser now reads the engine's artefact and the nav carries the ten V1 pages
 * (design §20.1). The pages this file drives — the V2/V4 pages — are no longer reachable.
 *
 * Their code is still in the tree: §20.2 keeps one release of overlap so a rollback has
 * somewhere to land, and Phase 4 Task 4.1 deletes the pages and this file together. Skipped
 * rather than deleted so that removal is one commit with its subject, not a test quietly
 * disappearing ahead of the code it covered.
 */
test.describe.configure({ mode: 'serial' })


/**
 * UI invariants that hold on every screen, in every language.
 *
 * Each one is here because it was broken and shipped. They are written as
 * measurements rather than screenshots because the failures are two pixels
 * wide: "₪63,571.87" splitting into "₪63,5" and "71.87" is invisible in a
 * review and obvious to a manager reading a figure.
 */

const PAGES = [
  'operational', 'recommendations', 'orders', 'prices', 'assortment',
  'store-layout', 'shelf-plan', 'products', 'expiry', 'dashboard',
  'report', 'data-source',
]

/** Numbers rendered across more than one line. */
async function wrappedNumbers(page) {
  return page.evaluate(() =>
    [...document.querySelectorAll('body *')]
      .filter((el) => {
        const style = getComputedStyle(el)
        if (style.display === 'none' || style.visibility === 'hidden') return false
        const raw = (el.textContent || '').trim()
        if (!/\d/.test(raw)) return false
        const ownText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())
        if (!ownText) return false
        return /^[^\p{L}]*[\d][\d.,\s⁦-⁩₪%+-]*$/u.test(raw)
      })
      .filter((el) => {
        const range = document.createRange()
        range.selectNodeContents(el)
        // Distinct line tops, not rects: bidi isolation splits one line into
        // several rects and counting those reports 150 phantom failures.
        return new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size > 1
      })
      .map((el) => `${el.className || el.tagName}: ${(el.textContent || '').trim().slice(0, 30)}`),
  )
}

for (const language of ['ar', 'he', 'en']) {
  test(`no number is split across lines in ${language}`, async ({ page }) => {
    await page.goto('/')
  await expandNav(page)
    await page.selectOption('.lang-switch-select', language)
    await page.waitForTimeout(300)

    for (const [index, id] of PAGES.entries()) {
      const nav = page.locator('.nav-item').nth(index)
      await nav.scrollIntoViewIfNeeded()
      await nav.click()
      await page.waitForTimeout(400)
      expect(await wrappedNumbers(page), `${id} in ${language}`).toEqual([])
    }
  })
}

test('no page scrolls horizontally on a phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expandNav(page)

  for (const [index, id] of PAGES.entries()) {
    const nav = page.locator('.nav-item').nth(index)
    await nav.scrollIntoViewIfNeeded()
    await nav.click()
    await page.waitForTimeout(400)
    const overflow = await page.evaluate(
      () => document.scrollingElement.scrollWidth - window.innerWidth,
    )
    expect(overflow, `${id} overflows by ${overflow}px`).toBeLessThanOrEqual(1)
  }
})

/**
 * Text cut off by an ANCESTOR's overflow.
 *
 * The element itself looks fine — `overflow: visible`, nothing wrong with it —
 * and the parent clips. That is how "₪63,571.87" reached the screen as
 * "₪63,57" for weeks: a fixed six-column metric grid sized every card to 132px
 * and the card's own `overflow: hidden` did the cutting. A truncated number
 * reads as a smaller real number rather than as an error, which makes it the
 * most expensive thing on this page to get wrong.
 */
async function textCutByAncestor(page) {
  return page.evaluate(() =>
    [...document.querySelectorAll('body *')]
      .filter((el) => {
        const style = getComputedStyle(el)
        if (style.display === 'none' || style.visibility === 'hidden') return false
        if (style.overflowX === 'hidden' || style.overflow === 'hidden') return false
        return [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 2)
      })
      .filter((el) => {
        const range = document.createRange()
        range.selectNodeContents(el)
        const rects = [...range.getClientRects()]
        if (!rects.length) return false
        const inkRight = Math.max(...rects.map((r) => r.right))
        const inkLeft = Math.min(...rects.map((r) => r.left))
        let node = el.parentElement
        while (node && node !== document.body) {
          const overflow = getComputedStyle(node).overflowX
          // Stop at the first ancestor that manages the x-axis: a scroller
          // above means the overhang is reachable, not cut off.
          if (overflow === 'visible') { node = node.parentElement; continue }
          if (overflow !== 'hidden' && overflow !== 'clip') return false
          const box = node.getBoundingClientRect()
          return inkRight > box.right + 1 || inkLeft < box.left - 1
        }
        return false
      })
      .map((el) => `${el.className || el.tagName}: ${(el.textContent || '').trim().slice(0, 30)}`),
  )
}

/**
 * Controls and labels left in English on a right-to-left screen.
 *
 * The prose check in the audit needs three Latin words, which is right for a
 * paragraph and blind to interface chrome — "Done", "Dismiss" and "Later" sat
 * untranslated on every Arabic and Hebrew screen and nothing reported it. A
 * label's caption is often a span inside the label, so those count too.
 */
const LATIN_BY_DESIGN = [
  'smartshelf ai', 'smartshelf', 'ai', 'csv', 'comax', 'wolt', 'pos', 'sku',
  'default', 'ils', 'llm', 'mcp', 'api', 'json', 'parquet', 'kaggle',
]

async function untranslatedControls(page, allowed) {
  return page.evaluate((allowList) => {
    const DATA_TEXT = [
      '[data-product-name]', '.product-name', '.cell-hebrew', '.hebrew-text',
      'td', 'th', '.pg-position-label', '.pg-tip-name', '.recommendation-product',
      '.op-handled-row', 'code', 'pre', '[dir="auto"]',
      // A language picker names each language in its own script — "English"
      // stays English there however the rest of the interface is set. Its
      // options are the one place Latin text is the correct translation.
      '.lang-switch',
    ].join(',')
    return [...document.querySelectorAll(
      'button, label, label > span, .eyebrow, .metric-label, [class*="-label"], option, legend',
    )]
      .filter((el) => {
        const style = getComputedStyle(el)
        if (style.display === 'none' || style.visibility === 'hidden') return false
        if (el.closest(DATA_TEXT)) return false
        const own = [...el.childNodes]
          .filter((n) => n.nodeType === 3)
          .map((n) => n.textContent.trim())
          .join(' ')
          .trim()
        if (own.length < 2) return false
        if (allowList.includes(own.toLowerCase())) return false
        return /^[A-Za-z][A-Za-z\s'’,.&+·/-]*$/.test(own)
      })
      .map((el) => (el.textContent || '').trim().slice(0, 40))
  }, allowed)
}

for (const language of ['ar', 'he']) {
  test(`no control is left in English in ${language}`, async ({ page }) => {
    await page.goto('/')
  await expandNav(page)
    await page.selectOption('.lang-switch-select', language)
    await page.waitForTimeout(300)

    for (const [index, id] of PAGES.entries()) {
      const nav = page.locator('.nav-item').nth(index)
      await nav.scrollIntoViewIfNeeded()
      await nav.click()
      await page.waitForTimeout(400)
      expect(await untranslatedControls(page, LATIN_BY_DESIGN), `${id} in ${language}`).toEqual([])
    }
  })
}

test('no text is cut off by a clipping ancestor', async ({ page }) => {
  await page.goto('/')
  await expandNav(page)

  for (const [index, id] of PAGES.entries()) {
    const nav = page.locator('.nav-item').nth(index)
    await nav.scrollIntoViewIfNeeded()
    await nav.click()
    await page.waitForTimeout(400)
    expect(await textCutByAncestor(page), `${id}`).toEqual([])
  }
})

/**
 * The phone nav is one row.
 *
 * It is a fixed bottom bar, and the shell reserves a fixed 72px for it. When
 * the nav was regrouped under `.nav-group` wrappers, those wrappers became the
 * flex children: each group stacked its own items and the bar silently became
 * two rows, cutting labels mid-word and covering the page beneath it. Nothing
 * measured it — the strip scrolls, so no overflow check fired, and it took
 * looking at a screenshot to notice.
 */
test('the phone nav stays a single row', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expandNav(page)
  await page.waitForTimeout(400)

  const rows = await page.evaluate(
    () => new Set(
      [...document.querySelectorAll('.nav-item')].map((el) => Math.round(el.getBoundingClientRect().top)),
    ).size,
  )
  expect(rows, 'nav items sit on more than one row').toBe(1)

  // And the shell must reserve at least the height the bar actually occupies.
  const { barHeight, reserved } = await page.evaluate(() => ({
    barHeight: document.querySelector('.sidebar-nav').getBoundingClientRect().height,
    reserved: parseFloat(getComputedStyle(document.querySelector('.app-shell')).paddingBottom),
  }))
  expect(reserved, `bar is ${barHeight}px but only ${reserved}px is reserved`).toBeGreaterThanOrEqual(barHeight)
})
