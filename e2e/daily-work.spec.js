import { expect, test } from '@playwright/test'

/**
 * SKIPPED AT THE CUT-OVER (2026-09-12).
 *
 * This drives the pre-cut-over operational page — `.topbar h1` reading "Today's tasks",
 * `.operational-search`, the pill row. The daily surface is now DailyPage over the engine's
 * artefact and none of those selectors exist.
 *
 * Its coverage is not lost. `npm run check:surface`
 * (src/surface/__tests__/checkpoint2.test.jsx) asserts the same invariants — AC-100, AC-101,
 * AC-103, AC-107, AC-109 — against the artefact the engine actually produced, and runs in CI
 * where this never did.
 *
 * Deleted with the old page in Phase 4 Task 4.1.
 */


/**
 * The daily journey: what the manager does before opening the shop.
 */

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await page.selectOption('.lang-switch-select', 'en')
})

test('the old Today page explains itself', async ({ page }) => {
  // No longer the LANDING screen: the V1 daily surface is, and the pilot's acceptance
  // criteria are written against it. This page is the first of the twelve restored behind
  // it. Selected by `data-nav` rather than by name because `page.daily.name` and
  // `page.operational.name` are both the literal string 'Today' in English with the same
  // hint — two nav items a reader cannot tell apart, which is a live question for the owner
  // and not something a test should paper over by guessing at an index.
  await page.locator('[data-nav="operational"]').click()
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

// Prices and Products are on their `catalogue` awaiting state: `dashboard.json` publishes
// findings, not a product list.
//
// ADR-024 was accepted and #129 merged on 2026-09-17, so the nightly (cron `0 0 * * *`)
// writes the first `public/data/catalogue.json` on 2026-09-18. These return when the pages
// are routed at it.
//
// Phrased as a DATE, not as a condition — and that is not pedantry, it is this file's own
// argument applied to itself. The first version of this comment said "until ADR-024 is
// accepted and the nightly writes one", and ADR-024 was accepted within a day of it being
// written. A reason that names an open condition sends the next reader looking for something
// that already happened, which is precisely how the cut-over skip this replaced went stale.
test.skip('prices, gaps and products all render their tables', async ({ page }) => {
  for (const [name, marker] of [
    ['Prices', 'Price comparison'],
    ['Products', 'Inventory table'],
  ]) {
    await page.locator('.nav-item', { hasText: name }).click()
    // `.first()` because the page title and a panel heading share the wording.
    await expect(page.getByText(marker).first()).toBeVisible()
  }
})

// Returned 2026-09-21, when the nightly published the first catalogue.json and Products was
// routed at it. This is the invariant it was skipped to protect: the manager searches the
// shelf and the invoice in Hebrew, so a translated product name breaks the only link to the
// physical item. It now runs against 7,523 real rows.
test('product names stay in Hebrew whatever the interface language', async ({ page }) => {
  await page.locator('.nav-item', { hasText: 'Products' }).click()
  const table = page.locator('table').first()
  await expect(table).toBeVisible()
  // The manager searches the shelf and the invoice in Hebrew; translating a
  // product name would break the only link to the physical item.
  await expect(table).toContainText(/[֐-׿]/)
})
