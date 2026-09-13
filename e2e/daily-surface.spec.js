import { expect, test } from '@playwright/test'

/**
 * The owner's daily surface, driven in a real browser.
 *
 * WHY THIS EXISTS SEPARATELY FROM check:surface
 *   `npm run check:surface` (src/surface/__tests__/checkpoint2.test.jsx) already
 *   runs the real crossing loadDashboard → compose → DailyPage → ownerState in
 *   jsdom against the artefact the engine actually produced, and it is green.
 *   What jsdom cannot do is the part a browser does: real routing, real layout,
 *   real RTL, a real 390px phone, and — the one that matters most — a real page
 *   reload, which is the only honest way to test that a recorded outcome
 *   survives (AC-105). jsdom keeps module state alive across a "reload"; a
 *   browser does not.
 *
 *   Phase 2 Task 2.9 chose jsdom "for now" because the cut-over was deferred and
 *   there was no URL to drive. The cut-over happened on 2026-09-12. This is the
 *   spec that note promised, written against the surface that now ships.
 *
 * CONVENTIONS FOLLOWED FROM THE EXISTING SUITE
 *   CSS class locators, because this repository has no data-testid anywhere and
 *   inventing one here would make this the odd file out. Language via
 *   `.lang-switch-select`, matching navigation.spec.js. Layout invariants via
 *   page.evaluate over the live DOM, reusing the rect-counting approach from
 *   ui-invariants.spec.js — formatShekel wraps money in LRI/PDI isolates, which
 *   yields several client rects per line, so counting distinct rect tops is the
 *   only measurement that survives bidi.
 *
 * WHAT THIS DELIBERATELY DOES NOT ASSERT
 *   AC-104 (estimated certainty), AC-107 (an unavailable capability) and AC-108
 *   (nothing to do) cannot be driven from the committed artefact: every
 *   capability in it is `available`, every valued entry is `confirmed`, and the
 *   surface is full. Rather than stub a doctored artefact through page.route and
 *   call that an end-to-end test of the real thing, those stay in
 *   checkpoint2.test.jsx where the input can be constructed honestly. A test
 *   that fabricates its own input is not evidence about what ships.
 */

/** The artefact is 4.6 MB; the spine shows `.spine__loading` until it lands. */
async function openDailySurface(page, language = 'en') {
  await page.goto('/')
  await expect(page.locator('.spine__loading')).toHaveCount(0, { timeout: 30_000 })
  await page.selectOption('.lang-switch-select', language)
  await expect(page.locator('html')).toHaveAttribute('lang', language)
  await expect(page.locator('.daily')).toBeVisible()
}

test.describe('the owner opens the app', () => {
  test('lands on the daily surface without navigating', async ({ page }) => {
    // There is no router: '/' is the daily surface and the only way to another
    // page is a .nav-item click. If that ever stops being true the owner's first
    // screen has changed, which is a product decision, not a refactor.
    await openDailySurface(page)
    await expect(page.locator('.daily')).toBeVisible()
    await expect(page.locator('.nav-item[aria-current="page"] .nav-item-name')).toHaveText('Today')
  })

  test('AC-100 — presents at most ten entries', async ({ page }) => {
    await openDailySurface(page)
    const bound = await page.evaluate(async () => {
      const response = await fetch('/data/dashboard.json')
      return (await response.json()).thresholds.surface.bound
    })
    expect(bound).toBeGreaterThan(0)
    const shown = await page.locator('.entry-card').count()
    expect(shown).toBeGreaterThan(0)
    expect(shown).toBeLessThanOrEqual(bound)
  })

  test('AC-101 — no count of what is not shown appears anywhere', async ({ page }) => {
    await openDailySurface(page)
    // The surface has thousands of candidates behind these ten. Telling the
    // owner that is telling him he is behind, which is the thing the bound
    // exists to prevent.
    const text = await page.locator('body').innerText()
    expect(text).not.toMatch(/\b\d+\s*(?:more|remaining|others?|hidden|left)\b/i)
    expect(text).not.toMatch(/\bof\s+\d{2,}\b/i)
  })

  test('AC-109 — no product appears twice', async ({ page }) => {
    await openDailySurface(page)
    const ids = await page.locator('.entry-card').evaluateAll((cards) =>
      cards.map((card) => card.getAttribute('data-entry-id')),
    )
    expect(ids.every(Boolean)).toBe(true)
    expect(new Set(ids).size).toBe(ids.length)

    const names = await page.locator('.entry-card__name').allInnerTexts()
    expect(new Set(names).size).toBe(names.length)
  })

  test('AC-103 — no two money kinds are mixed into one run of values', async ({ page }) => {
    await openDailySurface(page)
    // The DOM form of the invariant checkpoint2 checks by calling compose()
    // directly: read the kinds in document order and collapse runs. Two runs of
    // the same kind would mean the ordering interleaved them, and an interleaved
    // list is one a reader can sum. Rule 8 in the shape the owner sees it.
    const kinds = await page
      .locator('.entry-card__value')
      .evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-kind')))
    const runs = kinds.filter((kind, index) => kind !== kinds[index - 1])
    expect(new Set(runs).size).toBe(runs.length)
  })

  test('a money figure is never rendered as a bare zero', async ({ page }) => {
    await openDailySurface(page)
    // When a figure cannot be stated honestly the entry carries no value block
    // at all. A zero standing in for "unknown" is the failure rule 8 names.
    const amounts = await page.locator('.entry-card__amount').allInnerTexts()
    for (const amount of amounts) {
      expect(amount.replace(/[^\d]/g, '')).not.toMatch(/^0*$/)
    }
  })
})

test.describe('recording an outcome', () => {
  test('AC-105 — the entry is gone, and stays gone across a real reload', async ({ page }) => {
    await openDailySurface(page)

    const first = page.locator('.entry-card').first()
    const id = await first.getAttribute('data-entry-id')
    expect(id).toBeTruthy()

    await first.getByRole('button', { name: 'Done' }).click()
    await expect(page.locator(`[data-entry-id="${id}"]`)).toHaveCount(0)

    // The part jsdom cannot do. ownerState.js caches state in a module-level
    // variable; only a real navigation throws that away and forces the page to
    // read localStorage again. A "reload" that keeps the module alive proves
    // nothing about persistence.
    await page.reload()
    await expect(page.locator('.spine__loading')).toHaveCount(0, { timeout: 30_000 })
    await expect(page.locator('.daily')).toBeVisible()
    await expect(page.locator(`[data-entry-id="${id}"]`)).toHaveCount(0)

    // And corroborate against the store itself, so a rendering quirk cannot pass
    // for persistence.
    const outcome = await page.evaluate(
      (entryId) => JSON.parse(localStorage.getItem('smartshelf.ownerState.v2')).outcomes[entryId],
      id,
    )
    expect(outcome).toMatchObject({ status: 'acted' })
    expect(outcome.snapshot.signal_family).toBeTruthy()
  })

  test('the surface refills to the bound rather than leaving a hole', async ({ page }) => {
    await openDailySurface(page)
    const before = await page.locator('.entry-card').count()
    await page.locator('.entry-card').first().getByRole('button', { name: 'Later' }).click()
    await expect(page.locator('.entry-card')).toHaveCount(before)
  })
})

test.describe('C-53 / AC-112 — the three languages, on a phone', () => {
  const LANGUAGES = [
    { code: 'ar', dir: 'rtl' },
    { code: 'he', dir: 'rtl' },
    { code: 'en', dir: 'ltr' },
  ]

  for (const language of LANGUAGES) {
    test(`renders in ${language.code} with no untranslated key`, async ({ page }) => {
      await openDailySurface(page, language.code)
      await expect(page.locator('html')).toHaveAttribute('dir', language.dir)

      // The whole document, heading included. This was scoped to `.page-body`
      // first and passed while the product was broken: AppShell renders the <h1>
      // inside `.topbar`, which is a SIBLING of `.page-body`, so the scan never
      // saw that the heading was the literal string "page.daily.title" in all
      // three languages. Verified by reverting the dictionary fix and watching
      // this fail.
      const leaked = await page.locator('body').evaluate((node) => {
        const matches = node.innerText.match(/\b[a-z][a-z_]*\.[a-z][a-zA-Z_.]+\b/g) ?? []
        return matches.filter((candidate) =>
          /^(page|daily|entry|value|outcome|questions|data|spine|capability|count|threshold|unavailable|characterisation|evidence|app|common|provenance|group|nav|receiving)\./.test(
            candidate,
          ),
        )
      })
      expect(leaked).toEqual([])
    })

    test(`does not scroll sideways on a 390px phone in ${language.code}`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 })
      await openDailySurface(page, language.code)
      const overflow = await page.evaluate(
        () => document.scrollingElement.scrollWidth - window.innerWidth,
      )
      expect(overflow).toBeLessThanOrEqual(1)
    })

    test(`splits no number across lines in ${language.code}`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 })
      await openDailySurface(page, language.code)
      // A shekel figure broken over two lines reads as two numbers. Counted by
      // distinct rect tops because formatShekel wraps its output in LRI/PDI
      // isolates, so one line legitimately produces several rects.
      const split = await page.locator('.entry-card__amount').evaluateAll((nodes) =>
        nodes
          .filter((node) => {
            const range = document.createRange()
            range.selectNodeContents(node)
            const tops = new Set(
              [...range.getClientRects()].map((rect) => Math.round(rect.top)),
            )
            return tops.size > 1
          })
          .map((node) => node.textContent),
      )
      expect(split).toEqual([])
    })
  }
})
