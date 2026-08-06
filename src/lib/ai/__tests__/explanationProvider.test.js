import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  annotateRecommendationsWithExplanations,
  annotateRecommendationsWithMockExplanations,
} from '../explanationProvider.js'
import { llmExplanationProvider } from '../llmExplanationProvider.js'

const product = {
  id: 'product-1',
  name: 'Test product',
  category: 'Test',
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

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('async explanation pipeline', () => {
  it('awaits a successful provider and upgrades the visible explanation', async () => {
    const result = await annotate({
      id: 'llm',
      async generateExplanation() {
        await Promise.resolve()
        return {
          provider: 'llm',
          explanation: 'Live proxy explanation',
          riskReason: 'Risk',
          businessImpact: 'Impact',
          confidenceNote: 'Confidence',
        }
      },
    })

    expect(result[0]).toMatchObject({
      explanation: 'Live proxy explanation',
      explanationProvider: 'llm',
    })
  })

  it('keeps the mock explanation when the provider rejects without an unhandled rejection', async () => {
    const unhandled = vi.fn()
    globalThis.process.on('unhandledRejection', unhandled)

    try {
      const result = await annotate({
        id: 'llm',
        generateExplanation() {
          return Promise.reject(new Error('rate limited'))
        },
      })
      await new Promise((resolve) => globalThis.setTimeout(resolve, 0))

      expect(result[0].explanation).not.toBe('')
      expect(result[0].explanationProvider).toBe('mock')
      expect(unhandled).not.toHaveBeenCalled()
    } finally {
      globalThis.process.off('unhandledRejection', unhandled)
    }
  })

  it('times out a pending provider and aborts its request signal', async () => {
    vi.useFakeTimers()
    let observedSignal
    const resultPromise = annotate({
      id: 'llm',
      generateExplanation(_payload, { signal }) {
        observedSignal = signal
        return new Promise(() => {})
      },
    }, { timeoutMs: 50 })

    await vi.advanceTimersByTimeAsync(50)
    const result = await resultPromise

    expect(observedSignal.aborted).toBe(true)
    expect(result[0].explanationProvider).toBe('mock')
  })

  it('aborts pending provider work when a run is superseded', async () => {
    const controller = new AbortController()
    let observedSignal
    const resultPromise = annotate({
      id: 'llm',
      generateExplanation(_payload, { signal }) {
        observedSignal = signal
        return new Promise(() => {})
      },
    }, { timeoutMs: 5_000, signal: controller.signal })

    controller.abort(new Error('superseded'))
    const result = await resultPromise

    expect(observedSignal.aborted).toBe(true)
    expect(result[0].explanationProvider).toBe('mock')
  })

  it('keeps the existing synchronous mock API available for immediate rendering', () => {
    const result = annotateRecommendationsWithMockExplanations({
      marketContext,
      products: [product],
      recommendations: [recommendation],
    })

    expect(result[0].explanationProvider).toBe('mock')
    expect(result[0].explanation).not.toBe('')
  })
})

describe('HTTP proxy client semantics', () => {
  it('preserves a 429 status and Retry-After while rejecting the request', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'rate limited' }),
      { status: 429, headers: { 'Retry-After': '17' } },
    )))

    await expect(llmExplanationProvider.generateExplanation(
      { productId: product.id },
      { enabled: true, proxyUrl: 'http://proxy.test/explain' },
    )).rejects.toMatchObject({ status: 429, retryAfter: '17' })
  })

  it('clears its timeout and removes the external abort listener after success', async () => {
    const clearTimeoutSpy = vi.spyOn(globalThis, 'clearTimeout')
    const controller = new AbortController()
    const removeListenerSpy = vi.spyOn(controller.signal, 'removeEventListener')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      shortExplanation: 'Live response',
      riskReason: 'Risk',
      businessImpact: 'Impact',
      confidenceNote: 'Confidence',
    }), { status: 200 })))

    const result = await llmExplanationProvider.generateExplanation(
      { productId: product.id },
      {
        enabled: true,
        proxyUrl: 'http://proxy.test/explain',
        signal: controller.signal,
        timeoutMs: 100,
      },
    )

    expect(result.explanation).toBe('Live response')
    expect(clearTimeoutSpy).toHaveBeenCalled()
    expect(removeListenerSpy).toHaveBeenCalledWith('abort', expect.any(Function))
  })
})
