import { expect, test } from '@playwright/test'

/**
 * Every page opens, in every language, with no console error.
 *
 * The broadest safety net in the suite: it would have caught the provider that
 * was not mounted, the page that crashed on a missing prop, and every key that
 * renders as `page.expiry.title` instead of a sentence.
 */

const PAGES = [
  'operational',
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
        if (message.type() === 'error') errors.push(message.text())
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
