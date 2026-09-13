import { expect, test } from '@playwright/test'

/**
 * The motion layer must stay off the owner's critical path.
 *
 * gsap, ScrollTrigger and lenis are ~128 KB. As static imports they were a
 * quarter of the owner's 496 KB entry and were fetched before he could read a
 * single line of today's work — including on a machine set to reduce motion,
 * where SmoothScrollProvider bails out immediately and none of it is ever used.
 *
 * `npm run check:bundle` measures the consequence, but it measures bytes on
 * disk. It cannot tell whether a chunk is fetched eagerly at startup, and a
 * single re-added `import gsap from 'gsap'` at the top of any module in the
 * owner's graph would silently put all 128 KB back with the gate still green.
 * These two tests watch the network instead, which is where the claim actually
 * lives.
 *
 * They also guard the other direction: lazy must not mean broken. Smooth
 * scrolling has to genuinely attach once the import lands, or this "saving"
 * would just be a deleted feature.
 */

const MOTION_CHUNK = /gsap|lenis|ScrollTrigger/i

test('smooth scrolling still attaches, just later', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.spine__loading')).toHaveCount(0, { timeout: 30_000 })

  // Lenis puts its own class on <html> when it takes over the wheel. If the
  // dynamic import silently failed, the page would still scroll natively and
  // every other test would pass — this is the one that would not.
  await expect
    .poll(() => page.locator('html').getAttribute('class'), { timeout: 15_000 })
    .toContain('lenis')
})

test('a machine set to reduce motion downloads none of it', async ({ browser }) => {
  const context = await browser.newContext({ reducedMotion: 'reduce' })
  const page = await context.newPage()

  const motionChunks = []
  page.on('response', (response) => {
    const name = response.url().split('/').pop()
    if (MOTION_CHUNK.test(name)) motionChunks.push(name)
  })

  try {
    await page.goto('/')
    await expect(page.locator('.spine__loading')).toHaveCount(0, { timeout: 30_000 })
    await expect(page.locator('.daily')).toBeVisible()
    // Long enough that a deferred fetch would have landed.
    await page.waitForTimeout(1500)

    expect(motionChunks).toEqual([])
    // `?? ''` matters: with no class attribute at all getAttribute returns null,
    // and expect(null).not.toContain() throws rather than passing — which made
    // this assertion fail for the wrong reason the first time it was written.
    expect((await page.locator('html').getAttribute('class')) ?? '').not.toContain('lenis')
  } finally {
    await context.close()
  }
})
