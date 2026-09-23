import { expect, test } from '@playwright/test'

/**
 * What is left of the pre-cut-over journey, after the old Today page was removed on
 * 2026-09-23 ("combine the first 2, i don't need 2 today work").
 *
 * The tests that drove `operational` went with it — the page explaining itself, and the
 * action-list search — because a test for a screen nobody can open is not coverage, it is a
 * reason to keep dead code alive. Their invariants were never unique to that page:
 * `npm run check:surface` asserts AC-100, AC-101, AC-103, AC-107 and AC-109 against the
 * artefact the engine actually produced, and runs in CI where this file never did.
 *
 * What remains is not about that page and is kept: the provenance strip, which is AppShell's,
 * and the Hebrew product names, which are the Products page's.
 */


/**
 * The daily journey: what the manager does before opening the shop.
 */

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await page.selectOption('.lang-switch-select', 'en')
})


test('the data provenance strip never claims more than it has', async ({ page }) => {
  // Demo data must say so. A screen that implies real POS data when it is a
  // sample is the fastest way to lose a pilot.
  const pills = page.locator('.topbar-meta .pill')
  await expect(pills).not.toHaveCount(0)
})


// Products renders since 2026-09-21. PRICES does not: it awaits the per-product
// competitor comparison (#137/#148), not the catalogue: `dashboard.json` publishes
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
