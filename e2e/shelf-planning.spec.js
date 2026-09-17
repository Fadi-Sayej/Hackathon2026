import { expect, test } from '@playwright/test'

/**
 * SKIPPED AT THE CUT-OVER (2026-09-12).
 *
 * The browser now reads the engine's artefact and the nav carries the ten V1 pages
 * (design §20.1). The pages this file drives — store layout and shelf plan — are no longer reachable.
 *
 * Their code is still in the tree: §20.2 keeps one release of overlap so a rollback has
 * somewhere to land, and Phase 4 Task 4.1 deletes the pages and this file together. Skipped
 * rather than deleted so that removal is one commit with its subject, not a test quietly
 * disappearing ahead of the code it covered.
 */
test.describe.configure({ mode: 'serial' })


/**
 * The shelf-planning journey, end to end, as the manager performs it:
 * draw the store, pick a fixture, read what goes on it, approve, take the
 * build sheet to the aisle.
 */

// Store layout and Shelf plan are on their `demand` awaiting state and render no `.pg-canvas`.
// The blocker is not the cut-over — the pages are back in the nav — it is that every fixture
// here ranks by units sold per day. That is not measurable from seven monthly reports
// (rule 13), and the 30-day table that would supply it was deleted for being synthesised
// from a monthly mean (rule 5). These return with real demand in V2, not with a nav change.
test.skip(true, 'Store layout awaits per-product demand; see rule 13 and PageAwaitingData')

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await page.selectOption('.lang-switch-select', 'en')
  await page.locator('.nav-item', { hasText: 'Store layout' }).click()
  await expect(page.locator('.pg-canvas')).toBeVisible()
})

test('selecting a fixture in the top view opens its shelf plan below', async ({ page }) => {
  await expect(page.locator('.pg-inline-plan')).toHaveCount(0)

  await page.locator('.pg-unit').first().click()

  await expect(page.locator('.pg-inline-plan')).toBeVisible()
  await expect(page.locator('.pg-bay')).toBeVisible()
  // The heading names the fixture that was clicked, so it is obvious which
  // shelf is being planned.
  await expect(page.locator('.pg-inline-plan-head h2')).toContainText('What goes on')
})

test('the plan is checked and the result is stated', async ({ page }) => {
  await page.locator('.pg-unit').first().click()
  await expect(page.getByText('Constraint check')).toBeVisible()
  await expect(page.getByText('Valid ✓')).toBeVisible()
})

test('approving freezes the plan and the change count appears', async ({ page }) => {
  await page.locator('.pg-unit').first().click()

  await expect(page.getByText('No plan has been approved')).toBeVisible()
  await page.getByRole('button', { name: 'Approve plan' }).click()

  await expect(page.getByText('Positions changing')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Approve new version' })).toBeVisible()
})

test('the build sheet caps units at real stock and marks empties', async ({ page }) => {
  await page.locator('.pg-unit').first().click()

  const sheet = page.locator('.pg-sheet')
  await expect(sheet).toBeVisible()
  await expect(sheet.locator('tbody tr')).not.toHaveCount(0)
  // Positions with no stock at all are struck through rather than presented as
  // work; without this the sheet sends someone to fetch nothing.
  await expect(sheet.locator('.pg-sheet-unfillable')).not.toHaveCount(0)
})

test('the build sheet downloads as a CSV', async ({ page }) => {
  await page.locator('.pg-unit').first().click()

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Build sheet' }).click(),
  ])

  expect(download.suggestedFilename()).toMatch(/^shelf-plan-.*\.csv$/)
})

test('switching department re-plans the same fixture', async ({ page }) => {
  await page.locator('.pg-unit').first().click()

  const select = page.locator('.pg-embedded-bar select')
  const before = await page.locator('.pg-position').count()

  const options = await select.locator('option').all()
  await select.selectOption(await options[1].getAttribute('value'))

  await expect
    .poll(async () => page.locator('.pg-position').count())
    .not.toBe(before)
})

test('the shelf photo panel offers capture and states no model is running', async ({ page }) => {
  await page.locator('.pg-unit').first().click()

  await expect(page.getByText('Photo of the shelf as it stands')).toBeVisible()
  await expect(page.locator('.pg-photo-drop')).toBeVisible()
})

test('the layout persists across a reload', async ({ page }) => {
  await page.getByRole('button', { name: 'Save layout' }).click()
  await expect(page.getByRole('button', { name: 'Saved ✓' })).toBeVisible()

  await page.reload()
  await page.locator('.nav-item', { hasText: 'Store layout' }).click()
  await expect(page.locator('.pg-unit')).not.toHaveCount(0)
})
