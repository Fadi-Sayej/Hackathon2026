import { describe, expect, it, vi, afterEach } from 'vitest'
import {
  annotateRecommendationsWithExplanations,
  annotateRecommendationsWithMockExplanations,
} from '../explanationProvider.js'

/**
 * T9 / #54 Step 6 — graceful degradation. "Mandatory, not optional."
 *
 * The issue lists five failure modes and says the architecture already handles
 * them, then asks for the thing that was missing: *"Verify it, and add a
 * regression test so nobody breaks it later."* This file is that test.
 *
 * Every case asserts the same invariant from the manager's side of the screen:
 * **the rule-based template is still there, and nothing thrown by the proxy
 * reaches him.** A recommendation that renders with no explanation is a worse
 * failure than one that renders with a plain one, because the number alone is
 * an instruction from a machine — which is the whole premise of this track.
 *
 * These run without a funded key and without a deployed proxy, so they stay
 * meaningful while both blockers are open.
 */

const product = {
  id: 'product-1',
  name: 'במבה 200 גרם',
  category: 'חטיפים מלוחים',
  currentStock: 4,
  shelfQuantity: 2,
  shelfCapacity: 8,
  salesLast7Days: 3,
  salesLast30Days: 12,
  price: 10,
  cost: 7,
  leadTimeDays: 2,
}

const recommendation = {
  productId: product.id,
  type: 'REORDER',
  urgency: 'HIGH',
  confidence: 0.8,
  reason: 'Rule-based fallback',
}

const marketContext = { sourceLabel: 'test' }

function annotate(provider, options = {}) {
  return annotateRecommendationsWithExplanations({
    marketContext,
    products: [product],
    recommendations: [recommendation],
    provider,
    ...options,
  })
}

/** What the manager sees when the LLM path never runs at all. */
function templateBaseline() {
  return annotateRecommendationsWithMockExplanations({
    marketContext,
    products: [product],
    recommendations: [recommendation],
  })
}

function hasVisibleExplanation(row) {
  return Boolean(row && typeof row.explanation === 'string' && row.explanation.trim())
}

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('#54 Step 6 — the UI never breaks when the proxy fails', () => {
  it('proxy unreachable: template stays, nothing is thrown at the caller', async () => {
    const rows = await annotate({
      id: 'llm',
      generateExplanation() {
        return Promise.reject(new TypeError('Failed to fetch'))
      },
    })

    expect(hasVisibleExplanation(rows[0])).toBe(true)
    expect(rows[0].explanation).toBe(templateBaseline()[0].explanation)
  })

  it('proxy returns 429: template stays', async () => {
    const rateLimited = Object.assign(new Error('Too Many Requests'), {
      status: 429,
      retryAfter: 30,
    })

    const rows = await annotate({
      id: 'llm',
      generateExplanation: () => Promise.reject(rateLimited),
    })

    expect(hasVisibleExplanation(rows[0])).toBe(true)
    expect(rows[0].explanation).toBe(templateBaseline()[0].explanation)
  })

  it('proxy times out: template stays and the batch does not hang', async () => {
    vi.useFakeTimers()

    const pending = annotate(
      {
        id: 'llm',
        // Never settles. Without the timeout this await would hang for ever.
        generateExplanation: () => new Promise(() => {}),
      },
      { timeoutMs: 50 },
    )

    await vi.advanceTimersByTimeAsync(60)
    const rows = await pending

    expect(hasVisibleExplanation(rows[0])).toBe(true)
    expect(rows[0].explanation).toBe(templateBaseline()[0].explanation)
  })

  it('key unfunded: a 503 from a keyless proxy leaves the template in place', async () => {
    // src/api/llm_proxy.py returns 503 rather than crashing at import when no
    // key is configured — which is exactly today's production state.
    const unfunded = Object.assign(new Error('Service Unavailable'), { status: 503 })

    const rows = await annotate({
      id: 'llm',
      generateExplanation: () => Promise.reject(unfunded),
    })

    expect(hasVisibleExplanation(rows[0])).toBe(true)
    expect(rows[0].explanation).toBe(templateBaseline()[0].explanation)
  })

  it('slow network: recommendations are readable immediately, upgrades land later', async () => {
    // The progressive-enhancement contract. The synchronous mock pass is what
    // App.jsx renders first; the async pass only ever replaces text that is
    // already on screen.
    const immediate = templateBaseline()
    expect(hasVisibleExplanation(immediate[0])).toBe(true)

    let release
    const slow = new Promise((resolve) => {
      release = () =>
        resolve({
          provider: 'llm',
          explanation: 'اطلب ٢٤ وحدة — بقي ١٢ فقط',
          riskReason: 'r',
          businessImpact: 'b',
          confidenceNote: 'c',
        })
    })

    const pending = annotate({ id: 'llm', generateExplanation: () => slow })
    release()
    const rows = await pending

    expect(rows[0].explanation).toBe('اطلب ٢٤ وحدة — بقي ١٢ فقط')
  })

  it('a malformed provider payload is discarded rather than rendered', async () => {
    // A 200 carrying junk is not a success. Rendering it would put a blank or
    // an object into the one line the manager actually reads.
    for (const bad of [null, undefined, {}, { explanation: '' }, { explanation: '   ' }]) {
      const rows = await annotate({
        id: 'llm',
        generateExplanation: () => Promise.resolve(bad),
      })
      expect(rows[0].explanation).toBe(templateBaseline()[0].explanation)
    }
  })

  it('one failing row does not cost the others their explanations', async () => {
    const products = [product, { ...product, id: 'product-2' }]
    const recommendations = [
      recommendation,
      { ...recommendation, productId: 'product-2' },
    ]

    const rows = await annotateRecommendationsWithExplanations({
      marketContext,
      products,
      recommendations,
      provider: {
        id: 'llm',
        generateExplanation({ product: p }) {
          if (p.id === 'product-1') return Promise.reject(new Error('boom'))
          return Promise.resolve({
            provider: 'llm',
            explanation: 'second row upgraded',
            riskReason: 'r',
            businessImpact: 'b',
            confidenceNote: 'c',
          })
        },
      },
      concurrency: 1,
    })

    expect(rows).toHaveLength(2)
    expect(hasVisibleExplanation(rows[0])).toBe(true)
    expect(rows[1].explanation).toBe('second row upgraded')
  })

  it('every recommendation carries an explanation even when nothing succeeds', async () => {
    const products = Array.from({ length: 12 }, (_, i) => ({ ...product, id: `p-${i}` }))
    const recommendations = products.map((p) => ({ ...recommendation, productId: p.id }))

    const rows = await annotateRecommendationsWithExplanations({
      marketContext,
      products,
      recommendations,
      provider: { id: 'llm', generateExplanation: () => Promise.reject(new Error('down')) },
    })

    expect(rows).toHaveLength(12)
    expect(rows.every(hasVisibleExplanation)).toBe(true)
  })
})
