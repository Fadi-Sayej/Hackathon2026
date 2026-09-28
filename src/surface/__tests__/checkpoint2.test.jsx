// @vitest-environment jsdom

import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, waitFor } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import App from '../../App.jsx'
import { compose, NOT_YET_SHOWN } from '../compose.js'
import { resetCacheForTests } from '../../owner/ownerState.js'
import { ar } from '../../lib/i18n/dictionaries/ar.js'

/**
 * Checkpoint 2 — the browser's half of CLAUDE.md rule 12.
 *
 * Every other test in Phase 2 hands its unit a fixture. None of them crosses
 * loadDashboard → compose → DailyPage → ownerState with an artefact the engine actually
 * produced, and that is the boundary where four signals in this repository have already
 * been lost. Task 1.9 proved the engine's half; this is the other.
 *
 * It reads `public/data/dashboard.json` — the real file, not the fixture. The fixture is
 * trimmed and cannot exhibit the pilot's shape: the FR-106 allocation defect passed every
 * fixture test and was only visible when 53 confirmed losses met a bound of ten.
 *
 * It renders App — the app the owner runs — and walks App's own nav. Until 2026-09-24 it
 * rendered V1Spine, which App stopped mounting at the cut-over, and a ten-page list of the
 * pre-restore nav: so every check here held of a component no screen showed, which is how
 * the cost questions and the receiving capture could vanish from the app with this gate
 * green (ADR-028).
 */

const ARTEFACT = resolve(process.cwd(), 'public/data/dashboard.json')
const CATALOGUE = resolve(process.cwd(), 'public/data/catalogue.json')
const present = existsSync(ARTEFACT)
const artefact = present ? JSON.parse(readFileSync(ARTEFACT, 'utf8')) : null
const catalogue = existsSync(CATALOGUE) ? JSON.parse(readFileSync(CATALOGUE, 'utf8')) : null
const NOW = Date.parse('2026-09-12T12:00:00Z')

// A capability whose page is named for what the owner does there, not for the capability.
const PAGE_OF = { order_quantity: 'recommendations' }
const pageOf = (id) => PAGE_OF[id] ?? id

function createStorage() {
  const backing = new Map()
  return {
    getItem: (k) => (backing.has(k) ? backing.get(k) : null),
    setItem: (k, v) => backing.set(k, v),
    removeItem: (k) => backing.delete(k),
    clear: () => backing.clear(),
  }
}

beforeEach(() => {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
  globalThis.fetch = async (url) => (String(url).includes('catalogue.json') && catalogue
    ? { ok: true, status: 200, json: async () => catalogue }
    : { ok: true, status: 200, json: async () => artefact })
})
afterEach(cleanup)

async function openApp() {
  renderWithI18n(<App />)
  await waitFor(() => expect(document.querySelector('.spine__loading')).toBeNull())
}

/** Every nav entry App renders, in order. */
const navIds = () => [...document.querySelectorAll('.nav-item[data-nav]')].map((n) => n.dataset.nav)

async function openPage(id) {
  fireEvent.click(document.querySelector(`.nav-item[data-nav="${id}"]`))
  await waitFor(() => expect(document.querySelector('.page-body .spine__loading')).toBeNull())
}

const describeIf = present ? describe : describe.skip

describeIf('Checkpoint 2 — against the artefact the engine produced', () => {
  it('AC-100 — the surface holds at most the published bound', async () => {
    await openApp()
    const cards = document.querySelectorAll('.entry-card')
    expect(cards.length).toBeLessThanOrEqual(artefact.thresholds.surface.bound)
  })

  it('AC-101 — no count of what is not shown appears anywhere', async () => {
    await openApp()
    const text = document.querySelector('.page-body').textContent
    expect(text).not.toMatch(/\b\d+\s*(?:more|remaining|others?|hidden)\b/i)
    expect(text).not.toMatch(/\bof\s+\d{2,}\b/i)
  })

  it('AC-103 — no two value kinds are interleaved on the surface', async () => {
    const { entries } = compose(artefact, { outcomes: {} }, { now: NOW })
    const kinds = entries.filter((e) => e.value).map((e) => e.value.kind)
    const runs = kinds.filter((k, i) => i === 0 || k !== kinds[i - 1])
    expect(runs.length).toBe(new Set(kinds).size)
  })

  it('AC-107 — an unavailable capability never reads as zero findings', async () => {
    await openApp()
    for (const [id, capability] of Object.entries(artefact.capabilities)) {
      if (capability.status !== 'unavailable' || id === 'owner_questions') continue
      // F8's capabilities are published before their screens exist (Phase 5 Task 5.0): no
      // page renders them until Tasks 5.13 and 5.14 take them off NOT_YET_SHOWN.
      if (NOT_YET_SHOWN.has(id)) continue
      await openPage(pageOf(id))
      expect(document.querySelector('.capability__unavailable')).not.toBeNull()
      expect(document.querySelector('.capability__counts')).toBeNull()
    }
  })

  it('AC-109 — no product appears twice', async () => {
    const { entries } = compose(artefact, { outcomes: {} }, { now: NOW })
    const barcodes = entries.map((e) => e.barcode).filter(Boolean)
    expect(new Set(barcodes).size).toBe(barcodes.length)
  })

  it('FR-106 — unvalued work reaches the surface rather than being crowded out', () => {
    // The defect the fixture could not show: with 53 confirmed losses and a bound of ten,
    // ranking instead of allocating gave price_consistency every place, and hygiene,
    // reconciliation and catalogue work would never have surfaced at all.
    const { entries } = compose(artefact, { outcomes: {} }, { now: NOW })
    const unvalued = entries.filter((e) => !e.value)
    const capabilities = new Set(entries.map((e) => e.capability))
    if (entries.length >= artefact.thresholds.surface.bound) {
      expect(unvalued.length).toBeGreaterThan(0)
      expect(capabilities.size).toBeGreaterThan(1)
    }
  })

  it('AC-112 — every key the app asks for resolves in Arabic, on every page of the nav', async () => {
    // The translator falls back to the key itself, so an unresolved key is visible only as
    // a dotted identifier in the page text.
    await openApp()
    const ids = navIds()
    expect(ids.length).toBeGreaterThan(0)
    for (const id of ids) {
      await openPage(id)
      // Not `\b` before the key: a value is rendered right before the next label, so
      // `18threshold.ceiling_source` has no word boundary at the `t` and hid two raw keys on
      // the price page until 2026-09-28. A key is any dotted identifier not preceded by a letter.
      const leaked = [...document.body.textContent.matchAll(/(?<![A-Za-z_.])([a-z][a-z_]*\.[a-z][a-zA-Z_.]+)/g)]
        .map((m) => m[1])
        .filter((candidate) => candidate in ar === false && /^(daily|entry|value|outcome|questions|data|spine|capability|count|threshold|unavailable|characterisation|evidence|prices|awaiting|page)\./.test(candidate))
      expect(leaked, `unresolved keys on ${id}`).toEqual([])
    }
  })

  it('every capability the engine published has a page in the nav that renders it', async () => {
    await openApp()
    const ids = new Set(navIds())
    for (const id of Object.keys(artefact.capabilities)) {
      if (id === 'owner_questions') continue                  // its surface is the panel on Today
      if (NOT_YET_SHOWN.has(id)) {
        // Published by the engine since 2026-09-27, and deliberately without a page until the
        // owner's approved screens are built (Task 5.0). Held to that, not merely skipped.
        expect(ids.has(id), `${id} reached the nav before its screen was built`).toBe(false)
        continue
      }
      expect(ids.has(pageOf(id)), `${id} has no nav entry`).toBe(true)
      await openPage(pageOf(id))
      expect(document.querySelector('.capability__missing')).toBeNull()
      expect(document.querySelector(`.page-body section.capability[data-capability="${id}"]`)).not.toBeNull()
    }
  })
})
