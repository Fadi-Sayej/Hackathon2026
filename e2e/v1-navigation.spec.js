import { expect, test } from '@playwright/test'

/**
 * Every V1 page opens, in every language, with a real heading and a body.
 *
 * WHY THIS EXISTS
 *   navigation.spec.js said of itself: *"the broadest safety net in the suite — it would
 *   have caught the provider that was not mounted, the page that crashed on a missing prop,
 *   and every key that renders as `page.expiry.title` instead of a sentence."* It was
 *   `test.skip(true)`'d at the cut-over because its twelve pages left the nav, and Phase 4
 *   deletes it with them. Nothing replaced it for the ten pages that arrived.
 *
 *   #90 is what that gap cost: nine of the ten V1 pages shipped rendering a raw i18n key as
 *   their heading. The net that names that exact failure was switched off at the time.
 *
 * WHY IT IS AN E2E TEST AND NOT A PREVIEW URL
 *   #107 argues the frontend work needs a Vercel preview, because *"a preview is exactly
 *   the check that catches a nav item pointing at a route that no longer exists, and #74
 *   removes ten routes."* Previews are blocked for collaborator PRs and unblocking them
 *   needs a paid plan — but CI runs on those PRs and already drives a real browser. A check
 *   a person has to remember to perform by eye is weaker than one that fails the build, so
 *   the guarantee belongs here.
 *
 * THE FAILURE IT IS SHAPED AROUND
 *   App.jsx dispatches on `activePage` and ends `return null`. Delete a page and leave its
 *   nav item — which is what #74 risks — and the owner gets a heading, a description, and
 *   an empty white panel. No error, no crash, nothing in a log. So asserting the body has
 *   content is the load-bearing assertion here, not a nicety.
 */

/**
 * The twelve pages, restored 2026-09-16 on the repository owner's decision.
 *
 * This list read as design §20.1's ten V1 ids until that date. It changed because the nav
 * changed, deliberately: the ten-page surface had dropped Reorder and the two planogram
 * screens, and those are the features the business is being built around. Editing this
 * array is the intended way to record such a decision — the test exists so that a nav
 * change is a deliberate edit here rather than something nobody notices.
 *
 * Asserted as a set, not a count, because a swap keeps the count.
 */
const V1_PAGES = [
  // The daily surface is the landing page and the pilot's acceptance criteria are written
  // against it (AC-100/103/105/107/109/112). The twelve restored pages sit behind it.
  'daily',
  'recommendations', 'orders',
  'prices', 'assortment',
  'store-layout', 'shelf-plan',
  'products', 'expiry',
  'dashboard', 'report',
  // The two capabilities whose entries were reachable from no screen at all until the
  // CapabilityPage was routed: 1,632 catalogue_lifecycle and 6 competitor_position.
  'price_consistency', 'margin_below_cost', 'reconciliation',
  'hygiene', 'catalogue_lifecycle', 'competitor_position',
  'data-source',
]

const LANGUAGES = ['he', 'en', 'ar']

/** `page.daily.title` rather than a sentence — #90's shape. A translated string never looks
 *  like this: every dictionary value carries a space, a letter outside a-z, or both. */
const RAW_I18N_KEY = /^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$/

/** Console errors and uncaught exceptions for the whole visit, collected per page object. */
function watchForErrors(page) {
  const seen = []
  page.on('console', (message) => { if (message.type() === 'error') seen.push(message.text()) })
  page.on('pageerror', (error) => seen.push(`pageerror: ${error.message}`))
  return seen
}

async function open(page) {
  const errors = watchForErrors(page)
  await page.goto('/')
  // Refuse to proceed until the shell is really up. A spec that navigates a page which
  // never rendered asserts nothing, which is the trap daily-surface.spec.js records.
  await expect(page.locator('.nav-item').first()).toBeVisible()
  return errors
}

async function setLanguage(page, code) {
  await page.locator('.lang-switch-select').selectOption(code)
  await expect(page.locator('html')).toHaveAttribute('lang', code)
}

test.describe('the V1 nav', () => {
  test('carries exactly the twelve pages the nav says it does', async ({ page }) => {
    await open(page)
    const ids = await page.locator('.nav-item').evaluateAll(
      (nodes) => nodes.map((n) => n.dataset.nav),
    )
    expect(ids.length).toBeGreaterThan(0)
    expect([...ids].sort()).toEqual([...V1_PAGES].sort())
  })

  for (const language of LANGUAGES) {
    test(`every page opens with a heading and a body — ${language}`, async ({ page }) => {
      const errors = await open(page)
      await setLanguage(page, language)

      for (const id of V1_PAGES) {
        const item = page.locator(`.nav-item[data-nav="${id}"]`)
        await expect(item, `${id} is not in the nav`).toHaveCount(1)
        await item.click()
        await expect(item).toHaveAttribute('aria-current', 'page')

        const heading = (await page.locator('.main-panel h1').innerText()).trim()
        expect(heading, `${id} has no heading in ${language}`).not.toBe('')
        expect(heading, `${id} renders a raw i18n key as its heading in ${language} (#90)`)
          .not.toMatch(RAW_I18N_KEY)

        // Scoped to the topbar: some pages render a .page-description of their own,
        // and an unscoped locator matches both.
        const description = (await page.locator('.topbar .page-description').innerText()).trim()
        expect(description, `${id} renders a raw i18n key as its description in ${language}`)
          .not.toMatch(RAW_I18N_KEY)

        // The one that catches a deleted page with a surviving nav item: App.jsx's
        // `return null` renders the shell around nothing at all.
        const children = await page.locator('.page-body').evaluate((el) => el.childElementCount)
        expect(children, `${id} renders an empty body in ${language}`).toBeGreaterThan(0)
      }

      expect(errors, `console errors while walking the nav in ${language}`).toEqual([])
    })
  }

  test('the heading follows the nav, so no page shows another page’s title', async ({ page }) => {
    // Two ids sharing a title, or a stale `activePage`, both read as "it works" on a single
    // screen. Comparing across pages is the only way to see it.
    await open(page)
    await setLanguage(page, 'en')
    const headings = new Map()
    for (const id of V1_PAGES) {
      await page.locator(`.nav-item[data-nav="${id}"]`).click()
      headings.set(id, (await page.locator('.main-panel h1').innerText()).trim())
    }
    expect(new Set(headings.values()).size, `duplicate headings: ${JSON.stringify([...headings])}`)
      .toBe(V1_PAGES.length)
  })
})
