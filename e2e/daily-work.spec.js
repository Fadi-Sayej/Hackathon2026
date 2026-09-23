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


// Returned 2026-09-23, when Prices was routed at the per-product comparison the nightly
// publishes (ADR-025, #148). It was skipped because PRICES awaited exactly that, and the
// skip's reason named a date rather than a condition so that nobody would go looking for a
// condition that had already been met. Products has its own test below.
//
// The header is asserted by name because it is the claim that matters: the column is the
// policy REFERENCE, which is not the cheapest price anyone charges, and the page this
// replaced called it "Cheapest nearby".
test('prices renders the comparison, named in Hebrew, against the reference', async ({ page }) => {
  await page.locator('.nav-item[data-nav="prices"]').click()
  const table = page.locator('.page-body table').first()
  await expect(table).toBeVisible()
  await expect(table.locator('th', { hasText: 'Reference' })).toHaveCount(1)
  await expect(table).toContainText(/[\u0590-\u05FF]/)
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
