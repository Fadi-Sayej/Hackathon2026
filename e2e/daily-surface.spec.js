import { expect, test } from '@playwright/test'

/**
 * The owner's daily surface, driven in a real browser against the built app.
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
 * EVERY TEST HERE MUST ASSERT THAT SOMETHING IS THERE
 *   The first version of this file did not, and review proved the cost: deleting
 *   the entire money block from EntryCard left all seventeen tests green. Five of
 *   them claimed to protect the money display, and every one was an `evaluateAll`
 *   over a collection that had silently become empty — `[]` equals `[]`. A
 *   surface rendering nothing at all still passed fourteen.
 *
 *   So `openDailySurface` refuses to return until a card is on screen, and any
 *   test that reads a set of elements asserts the set is non-empty before
 *   asserting anything about its contents. A negative assertion over an empty
 *   page is not evidence.
 *
 * CONVENTIONS FOLLOWED FROM THE EXISTING SUITE
 *   CSS class locators, because this repository has no data-testid anywhere and
 *   inventing one here would make this the odd file out. Language via
 *   `.lang-switch-select`, matching navigation.spec.js. Layout invariants via
 *   page.evaluate over the live DOM, reusing the rect-counting approach from
 *   ui-invariants.spec.js — formatShekel wraps money in LRI/PDI isolates, which
 *   yields several client rects per line, so counting distinct rect tops is the
 *   only measurement that survives bidi.
 */

/** What the engine published, read from the same URL the page reads. */
async function artefactFacts(page) {
  return page.evaluate(async () => {
    const artefact = await (await fetch('/data/dashboard.json')).json()
    // compose.js admits every capability except these two, so this is the pool
    // the bound is applied to. Counted here rather than reimplementing compose:
    // the point is only "are there more candidates than places?".
    const excluded = new Set(['margin_below_cost', 'owner_questions'])
    const candidates = Object.entries(artefact.capabilities)
      .filter(([id, capability]) => !excluded.has(id) && capability.status === 'available')
      .reduce((sum, [, capability]) => sum + (capability.entries?.length ?? 0), 0)
    return { bound: artefact.thresholds.surface.bound, candidates }
  })
}

/**
 * The artefact is 4.6 MB; the spine shows `.spine__loading` until it lands.
 * Returns only once a card is actually rendered — see the header.
 */
async function openDailySurface(page, language = 'en') {
  await page.goto('/')
  await expect(page.locator('.spine__loading')).toHaveCount(0, { timeout: 30_000 })
  await page.selectOption('.lang-switch-select', language)
  await expect(page.locator('html')).toHaveAttribute('lang', language)
  await expect(page.locator('.daily')).toBeVisible()
  await expect(page.locator('.entry-card').first()).toBeVisible()
  return artefactFacts(page)
}

test.describe('the owner opens the app', () => {
  test('lands on the daily surface without navigating', async ({ page }) => {
    // There is no router: '/' is the daily surface and the only way to another
    // page is a .nav-item click. If that ever stops being true the owner's first
    // screen has changed, which is a product decision, not a refactor.
    await openDailySurface(page)
    await expect(page.locator('.nav-item[aria-current="page"] .nav-item-name')).toHaveText('Today')
  })

  test('AC-100 — fills all ten places, and never more', async ({ page }) => {
    const { bound, candidates } = await openDailySurface(page)
    const shown = await page.locator('.entry-card').count()

    expect(shown).toBeLessThanOrEqual(bound)
    // `<= bound` alone is satisfied by showing one entry. Narrowing the
    // allocation from ten places to four — losing most of the owner's day —
    // passed that assertion. While there are more candidates than places the
    // surface must fill every place, so assert the exact number.
    if (candidates > bound) expect(shown).toBe(bound)
    else expect(shown).toBe(candidates)
  })

  test('AC-109 — no product appears twice', async ({ page }) => {
    await openDailySurface(page)
    const ids = await page.locator('.entry-card').evaluateAll((cards) =>
      cards.map((card) => card.getAttribute('data-entry-id')),
    )
    expect(ids.length).toBeGreaterThan(0)
    expect(ids.every(Boolean)).toBe(true)
    expect(new Set(ids).size).toBe(ids.length)

    // Product names are deliberately NOT asserted unique. compose dedupes by
    // barcode, and two barcodes sharing a name is legitimate and already present
    // in the artefact — `דנונה פרו 20 גרם` exists under two barcodes in
    // reconciliation. Asserting name uniqueness would go red on correct
    // behaviour the first time both were ranked into the same ten.
  })
})

test.describe('money, which is the thing this repository has been burned by', () => {
  test('AC-103 — the two value kinds are never interleaved', async ({ page }) => {
    // The committed artefact declares exactly one kind (`per_sale`), so against
    // real data this invariant cannot fail however badly compose is broken —
    // deleting the `data-kind` attribute outright left it green. The artefact is
    // therefore doctored to carry a second kind. Only the INPUT is fabricated:
    // real routing, real loadDashboard, real compose and the real DailyPage all
    // still run, which is the part worth testing.
    await page.route('**/data/dashboard.json', async (route) => {
      const artefact = await (await route.fetch()).json()
      // Exactly two entries are retagged, not half of them. compose orders the
      // kinds alphabetically and runs them contiguously, so marking half would
      // put 34 `one_off` rows ahead of every `per_sale` row and fill all seven
      // valued places with a single kind — the surface would be correct and the
      // test would still see one kind.
      const valued = artefact.capabilities.price_consistency.entries.filter((entry) => entry.value)
      valued.slice(0, 2).forEach((entry) => { entry.value.kind = 'one_off' })
      artefact.value_kinds_present = ['one_off', 'per_sale']
      await route.fulfill({ json: artefact })
    })

    await openDailySurface(page)
    const kinds = await page
      .locator('.entry-card__value')
      .evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-kind')))

    expect(kinds.length).toBeGreaterThan(1)
    expect(kinds.every(Boolean)).toBe(true)
    expect(new Set(kinds).size).toBe(2)

    // Collapse to runs. Two runs of the same kind means the list interleaves
    // them, and an interleaved list is one a reader can add up — the
    // "₪106,164 per sale" headline, in the shape the owner would see it.
    const runs = kinds.filter((kind, index) => kind !== kinds[index - 1])
    expect(new Set(runs).size).toBe(runs.length)
  })

  test('every rendered amount is a real figure, never a bare zero', async ({ page }) => {
    await openDailySurface(page)
    const amounts = await page.locator('.entry-card__amount').allInnerTexts()

    // Without this the whole test evaporates the moment the value block stops
    // rendering, which is exactly how it passed while the money display was gone.
    expect(amounts.length).toBeGreaterThan(0)

    for (const amount of amounts) {
      expect(amount.trim()).not.toBe('')
      // Unicode-aware: `\d` is ASCII-only and the Arabic locale renders
      // Arabic-Indic digits, which would strip to the empty string and then
      // match /^0*$/ — reporting "no number" as "a zero".
      const digits = [...amount].filter((character) => /\p{Nd}/u.test(character))
      expect(digits.length).toBeGreaterThan(0)
      expect(digits.some((digit) => Number(digit) !== 0)).toBe(true)
    }
  })
})

test.describe('capabilities that could not run', () => {
  test('AC-107 — an unavailable capability reads as unavailable, never as zero', async ({ page }) => {
    // Every capability in the committed artefact is `available`, so this is the
    // one acceptance criterion that cannot be reached without doctoring the
    // input. One status field is changed; everything downstream of the fetch is
    // the real app.
    await page.route('**/data/dashboard.json', async (route) => {
      const artefact = await (await route.fetch()).json()
      artefact.capabilities.reconciliation.status = 'unavailable'
      artefact.capabilities.reconciliation.unavailable_reason = 'inputs_missing'
      artefact.capabilities.reconciliation.entries = []
      await route.fulfill({ json: artefact })
    })

    await openDailySurface(page)

    const unavailable = page.locator('.daily__unavailable li[data-capability="reconciliation"]')
    await expect(unavailable).toHaveCount(1)

    const text = await unavailable.innerText()
    expect(text.trim()).not.toBe('')
    // The whole point of AC-107: "we could not compute this" must never be
    // rendered as "we computed this and the answer is none".
    expect(text).not.toMatch(/\b0\b/)
    expect(text).not.toMatch(/\p{Nd}/u)
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
    await expect(page.locator('.entry-card').first()).toBeVisible()
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

  test('a mistaken Later can be taken back, and the entry returns', async ({ page }) => {
    // "Later" sends no date. `recordOutcome` writes `deferred_until` only when it is
    // non-null and `compose` treats a missing one as deferred indefinitely, so the gentlest
    // button on the surface is the destructive one. How long "later" should last is OQ-604
    // and still open; this proves the press is recoverable in the meantime.
    await openDailySurface(page)

    const first = page.locator('.entry-card').first()
    const id = await first.getAttribute('data-entry-id')
    expect(id).toBeTruthy()

    await first.getByRole('button', { name: 'Later' }).click()
    await expect(page.locator(`[data-entry-id="${id}"]`)).toHaveCount(0)

    // The deferral really was written, and really was dateless — this is the defect, not a
    // rendering quirk, and asserting it here keeps the reason for the Undo visible.
    const deferred = await page.evaluate(
      (entryId) => JSON.parse(localStorage.getItem('smartshelf.ownerState.v2')).outcomes[entryId],
      id,
    )
    expect(deferred).toMatchObject({ status: 'deferred' })
    expect(deferred.deferred_until).toBeUndefined()

    await page.locator(`[data-undo="${id}"]`).click()
    await expect(page.locator(`[data-entry-id="${id}"]`)).toBeVisible()

    // And it is gone from the store, not merely re-rendered — otherwise the next reload
    // would hide it again.
    const cleared = await page.evaluate(
      (entryId) => JSON.parse(localStorage.getItem('smartshelf.ownerState.v2')).outcomes[entryId],
      id,
    )
    expect(cleared).toBeUndefined()

    await page.reload()
    await expect(page.locator('.spine__loading')).toHaveCount(0, { timeout: 30_000 })
    await expect(page.locator(`[data-entry-id="${id}"]`)).toBeVisible()
  })

  test('deferring an entry replaces it rather than leaving a gap', async ({ page }) => {
    const { bound, candidates } = await openDailySurface(page)
    test.skip(candidates <= bound, 'no spare candidate to refill the vacated place')

    const before = await page.locator('.entry-card').evaluateAll((cards) =>
      cards.map((card) => card.getAttribute('data-entry-id')),
    )
    await page.locator('.entry-card').first().getByRole('button', { name: 'Later' }).click()

    // Asserting only that the count is unchanged is satisfied by "Later" doing
    // nothing at all — proven: making deferral a no-op left the old version of
    // this test green. So assert the specific card left AND that a card which
    // was not previously on screen took its place.
    await expect(page.locator(`[data-entry-id="${before[0]}"]`)).toHaveCount(0)
    await expect(page.locator('.entry-card')).toHaveCount(before.length)

    const after = await page.locator('.entry-card').evaluateAll((cards) =>
      cards.map((card) => card.getAttribute('data-entry-id')),
    )
    expect(after.filter((id) => !before.includes(id))).toHaveLength(1)
  })
})

test.describe('C-53 / AC-112 — the three languages, on a phone', () => {
  const LANGUAGES = [
    { code: 'ar', dir: 'rtl' },
    { code: 'he', dir: 'rtl' },
    { code: 'en', dir: 'ltr' },
  ]

  for (const language of LANGUAGES) {
    test(`renders in ${language.code} on a 390px phone`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 })
      const { candidates } = await openDailySurface(page, language.code)
      await expect(page.locator('html')).toHaveAttribute('dir', language.dir)

      // 1. No untranslated key anywhere the owner can see, heading included.
      //    This was scoped to `.page-body` first and passed while the product was
      //    broken: AppShell renders the <h1> inside `.topbar`, a SIBLING of
      //    `.page-body`, so the scan never saw that the heading was the literal
      //    string "page.daily.title" in all three languages.
      //
      //    Note what this CANNOT catch: createTranslator falls back to Arabic
      //    before falling back to the key, so a key missing from en.js and he.js
      //    renders as Arabic prose inside the English UI with no dotted key in
      //    sight. src/lib/i18n/__tests__/parity.test.js is what covers that, by
      //    comparing the three key sets directly.
      const leaked = await page.locator('body').evaluate((node) => {
        const matches = node.innerText.match(/\b[a-z][a-z_]*\.[a-z][a-zA-Z_.]+\b/g) ?? []
        return matches.filter((candidate) =>
          /^(page|daily|entry|value|outcome|questions|data|spine|capability|count|threshold|unavailable|characterisation|evidence|app|common|provenance|group|nav|receiving|surface|money)\./.test(
            candidate,
          ),
        )
      })
      expect(leaked).toEqual([])

      // 2. AC-101, in every language rather than only English. The English word
      //    list cannot see a backlog counter written in Arabic, so the count
      //    itself is searched for in the locale's own digits.
      const backlog = await page.evaluate(
        ([total, lang]) => {
          const text = document.body.innerText
          return [total, total - 10].some((value) => text.includes(value.toLocaleString(lang)))
        },
        [candidates, language.code],
      )
      expect(backlog).toBe(false)

      const text = await page.locator('body').innerText()
      expect(text).not.toMatch(/\b\d+\s*(?:more|remaining|others?|hidden|left)\b/i)

      // 3. No horizontal scroll.
      const overflow = await page.evaluate(
        () => document.scrollingElement.scrollWidth - window.innerWidth,
      )
      expect(overflow).toBeLessThanOrEqual(1)

      // 4. No number split across lines. Counted by distinct rect tops because
      //    formatShekel wraps its output in LRI/PDI isolates, so one line
      //    legitimately produces several rects.
      const amounts = page.locator('.entry-card__amount')
      expect(await amounts.count()).toBeGreaterThan(0)
      const split = await amounts.evaluateAll((nodes) =>
        nodes
          .filter((node) => {
            const range = document.createRange()
            range.selectNodeContents(node)
            const tops = new Set([...range.getClientRects()].map((rect) => Math.round(rect.top)))
            return tops.size > 1
          })
          .map((node) => node.textContent),
      )
      expect(split).toEqual([])
    })
  }
})
