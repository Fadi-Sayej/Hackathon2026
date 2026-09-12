// @vitest-environment jsdom

import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, waitFor } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { V1Spine } from '../V1Spine.jsx'
import { V1_PAGES } from '../pages.js'
import { compose } from '../compose.js'
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
 * Not Playwright yet. The spine is deliberately not the app's default (D-14 / GAP-009), so
 * there is no URL to drive. When the cut-over happens this becomes e2e/daily-surface.spec.js
 * unchanged in substance.
 */

const ARTEFACT = resolve(process.cwd(), 'public/data/dashboard.json')
const present = existsSync(ARTEFACT)
const artefact = present ? JSON.parse(readFileSync(ARTEFACT, 'utf8')) : null
const NOW = Date.parse('2026-09-12T12:00:00Z')

function createStorage() {
  const backing = new Map()
  return {
    getItem: (k) => (backing.has(k) ? backing.get(k) : null),
    setItem: (k, v) => backing.set(k, v),
    removeItem: (k) => backing.delete(k),
  }
}

beforeEach(() => { globalThis.localStorage = createStorage(); resetCacheForTests() })
afterEach(cleanup)

const ok = async () => ({ ok: true, status: 200, json: async () => artefact })

const describeIf = present ? describe : describe.skip

describeIf('Checkpoint 2 — against the artefact the engine produced', () => {
  it('AC-100 — the surface holds at most the published bound', async () => {
    renderWithI18n(<V1Spine page="daily" fetchImpl={ok} now={NOW} />)
    await waitFor(() => expect(document.querySelector('.spine__loading')).toBeNull())
    const cards = document.querySelectorAll('.entry-card')
    expect(cards.length).toBeLessThanOrEqual(artefact.thresholds.surface.bound)
  })

  it('AC-101 — no count of what is not shown appears anywhere', async () => {
    renderWithI18n(<V1Spine page="daily" fetchImpl={ok} now={NOW} />)
    await waitFor(() => expect(document.querySelector('.spine__loading')).toBeNull())
    const text = document.body.textContent
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
    for (const [id, capability] of Object.entries(artefact.capabilities)) {
      if (capability.status !== 'unavailable') continue
      renderWithI18n(<V1Spine page={id} fetchImpl={ok} now={NOW} />)
      await waitFor(() => expect(document.querySelector('.spine__loading')).toBeNull())
      expect(document.querySelector('.capability__unavailable')).not.toBeNull()
      expect(document.querySelector('.capability__counts')).toBeNull()
      cleanup()
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

  it('AC-112 — every key the surface asks for resolves in Arabic', async () => {
    // The translator falls back to the key itself, so an unresolved key is visible only as
    // a dotted identifier in the page text.
    for (const page of V1_PAGES) {
      renderWithI18n(<V1Spine page={page} fetchImpl={ok} now={NOW} />)
      await waitFor(() => expect(document.querySelector('.spine__loading')).toBeNull())
      const leaked = [...document.body.textContent.matchAll(/\b([a-z][a-z_]*\.[a-z][a-zA-Z_.]+)\b/g)]
        .map((m) => m[1])
        .filter((candidate) => candidate in ar === false && /^(daily|entry|value|outcome|questions|data|spine|capability|count|threshold|unavailable|characterisation|evidence)\./.test(candidate))
      expect(leaked, `unresolved keys on ${page}`).toEqual([])
      cleanup()
    }
  })

  it('every capability the engine published has a page that renders', async () => {
    for (const id of Object.keys(artefact.capabilities)) {
      if (id === 'owner_questions') continue
      renderWithI18n(<V1Spine page={id} fetchImpl={ok} now={NOW} />)
      await waitFor(() => expect(document.querySelector('.spine__loading')).toBeNull())
      expect(document.querySelector('.capability__missing')).toBeNull()
      cleanup()
    }
  })
})
