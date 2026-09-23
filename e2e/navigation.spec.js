import { expect, test } from '@playwright/test'

/**
 * SKIPPED AT THE CUT-OVER (2026-09-12).
 *
 * The browser now reads the engine's artefact and the nav carries the ten V1 pages
 * (design §20.1). The pages this file drives — the V2/V4 nav entries — are no longer reachable.
 *
 * Their code is still in the tree: §20.2 keeps one release of overlap so a rollback has
 * somewhere to land, and Phase 4 Task 4.1 deletes the pages and this file together. Skipped
 * rather than deleted so that removal is one commit with its subject, not a test quietly
 * disappearing ahead of the code it covered.
 */
test.describe.configure({ mode: 'serial' })
// Un-skipped 2026-09-16. It was switched off at the cut-over because its twelve pages left
// the nav; they are back, on the repository owner's decision, and its PAGES list already
// matches the restored nav exactly and in order.
//
// This is the net that #90 slipped through — nine of the ten V1 pages shipped rendering a
// raw i18n key as their heading during the months it was off. It asserts a non-empty
// heading, no `page.<id>.title` left in the body, no console errors, six nav groups and a
// nav item per page, in all three languages. Everything the restored pages need to be
// caught by, including the ones that render PageAwaitingData: an awaiting page still has a
// heading and a sentence, so "empty because it is waiting" and "empty because it broke"
// stay distinguishable.


/**
 * Every page opens, in every language, with no console error.
 *
 * The broadest safety net in the suite: it would have caught the provider that
 * was not mounted, the page that crashed on a missing prop, and every key that
 * renders as `page.expiry.title` instead of a sentence.
 */

const PAGES = [
  'daily',
  'recommendations',
  'orders',
  'prices',
  'assortment',
  'store-layout',
  'shelf-plan',
  'products',
  'expiry',
  'dashboard',
  'report',
  'margin_below_cost',
  'catalogue_lifecycle',
  'competitor_position',
  'data-source',
]

const LANGUAGES = [
  { code: 'ar', dir: 'rtl' },
  { code: 'he', dir: 'rtl' },
  { code: 'en', dir: 'ltr' },
]

async function setLanguage(page, code) {
  await page.selectOption('.lang-switch-select', code)
  await expect(page.locator('html')).toHaveAttribute('lang', code)
}

for (const language of LANGUAGES) {
  test.describe(`language: ${language.code}`, () => {
    test(`sets the document direction to ${language.dir}`, async ({ page }) => {
      await page.goto('/')
      await setLanguage(page, language.code)
      await expect(page.locator('html')).toHaveAttribute('dir', language.dir)
    })

    test('opens every page without a console error or a raw key', async ({ page }) => {
      const errors = []
      page.on('pageerror', (error) => errors.push(String(error)))
      page.on('console', (message) => {
        // Chrome's message for a failed fetch is "Failed to load resource: the
        // server responded with a status of 404 ()" — no URL, so a failure here
        // says nothing about what is missing. The response handler below
        // records the URL instead; this one keeps everything else.
        if (message.type() !== 'error') return
        if (message.text().startsWith('Failed to load resource')) return
        errors.push(message.text())
      })
      // This test has failed intermittently (roughly one full-suite run in
      // four) on a 404 that could not be reproduced in isolation, under
      // sequential navigation, or under six parallel contexts with the dev
      // server churning HMR updates. Every occurrence was during a run where
      // source files were being edited. Rather than suppress it on a guess
      // about which URL it was, record the URL so the next occurrence says.
      page.on('response', (response) => {
        if (response.status() >= 400) {
          errors.push(`HTTP ${response.status()} — ${response.url()}`)
        }
      })

      await page.goto('/')
      await setLanguage(page, language.code)

      for (const id of PAGES) {
        await page.locator(`.nav-item`).nth(PAGES.indexOf(id)).click()
        await expect(page.locator('.topbar h1')).not.toBeEmpty()

        // A missing translation renders as its dotted key. That is deliberate so
        // it is noticeable — this is what notices.
        const body = await page.locator('.main-panel').innerText()
        expect(body, `${id} in ${language.code}`).not.toMatch(
          /\b(nav|page|common|op|sl|sp|pg|gap|exp|dash|rep|ds|ord|rec|prod|prov|photo|plan)\.[a-zA-Z]{3,}\b/,
        )
      }

      expect(errors, `console errors in ${language.code}`).toEqual([])
    })
  })
}

test('the language choice survives a reload', async ({ page }) => {
  await page.goto('/')
  await setLanguage(page, 'en')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
})

test('navigation is grouped and every item explains itself', async ({ page }) => {
  await page.goto('/')

  // Six groups, and a hint under every entry — the fix for "I do not understand
  // what each page is".
  await expect(page.locator('.nav-group')).toHaveCount(6)
  const items = page.locator('.nav-item')
  await expect(items).toHaveCount(PAGES.length)
  for (let index = 0; index < PAGES.length; index += 1) {
    await expect(items.nth(index).locator('.nav-item-hint')).not.toBeEmpty()
  }
})
