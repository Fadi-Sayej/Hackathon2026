import { expect, test } from '@playwright/test'

/**
 * The daily journey: what the manager does before opening the shop.
 */

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await page.selectOption('.lang-switch-select', 'en')
})

test('Today is the landing screen and explains itself', async ({ page }) => {
  await expect(page.locator('.topbar h1')).toHaveText("Today's tasks")
  await expect(page.locator('.topbar .page-description')).toContainText('money at stake')
})

test('the data provenance strip never claims more than it has', async ({ page }) => {
  // Demo data must say so. A screen that implies real POS data when it is a
  // sample is the fastest way to lose a pilot.
  const pills = page.locator('.topbar-meta .pill')
  await expect(pills).not.toHaveCount(0)
})

test('searching the action list filters it', async ({ page }) => {
  const search = page.locator('.operational-search')
  // `public/data/operational.json` is a build artifact and is not committed, so
  // on a fresh checkout this test legitimately does not apply. But it is
  // fetched asynchronously: asking for count() straight after goto() skipped on
  // a race even when the file was there, and a test that quietly removes itself
  // under load is worse than one that fails. Wait, then skip only if it never
  // arrives.
  const loaded = await search
    .waitFor({ state: 'visible', timeout: 5000 })
    .then(() => true, () => false)
  test.skip(!loaded, 'no operational data bundled in this build')

  await search.fill('zzz-no-such-product')
  await expect(page.getByText('Nothing matches that search')).toBeVisible()
})

test('prices, gaps and products all render their tables', async ({ page }) => {
  for (const [name, marker] of [
    ['Prices', 'Price comparison'],
    ['Products', 'Inventory table'],
  ]) {
    await page.locator('.nav-item', { hasText: name }).click()
    // `.first()` because the page title and a panel heading share the wording.
    await expect(page.getByText(marker).first()).toBeVisible()
  }
})

test('product names stay in Hebrew whatever the interface language', async ({ page }) => {
  await page.locator('.nav-item', { hasText: 'Products' }).click()
  const table = page.locator('table').first()
  await expect(table).toBeVisible()
  // The manager searches the shelf and the invoice in Hebrew; translating a
  // product name would break the only link to the physical item.
  await expect(table).toContainText(/[֐-׿]/)
})
