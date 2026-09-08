/**
 * Every failure path must land on the rule-based Hebrew — never a blank card.
 *
 * The owner opens this screen each morning. A spinner that never resolves, or an
 * empty explanation, is worse than the rule-based text it replaced: the rule-based
 * text is already good, so there is no failure mode worth degrading for.
 */
import { describe, expect, it, vi } from 'vitest'
import { llmExplanationProvider } from '../llmExplanationProvider.js'
import { annotateRecommendationsWithExplanations } from '../explanationProvider.js'

const facts = {
  kind: 'REORDER',
  productName: 'קרואסון',
  currentStock: 0,
  dailyRate: 8.38,
  leadTimeDays: 3,
  leadTimeAssumed: true,
  expectedDemandDuringLeadTime: 25.14,
  safetyStock: 25.14,
  orderQty: 20,
  uncappedOrderQty: 51,
  shelfLifeDays: 2,
  shelfLifeCapped: true,
  coverDays: 0,
  unitCost: 5.5,
  costToIgnore: 138.27,
  caseSize: null,
  demandMultiplier: 1,
  competitorLift: 1,
}

const product = { id: 'p1', name: 'קרואסון', category: 'מחלקת -barista' }
const recommendation = {
  productId: 'p1',
  type: 'REORDER',
  facts,
  reason: 'rule-based reason',
  recommendedOrderQuantity: 20,
}

function withFetch(impl, run) {
  const original = globalThis.fetch
  globalThis.fetch = impl
  return run().finally(() => {
    globalThis.fetch = original
  })
}

const opts = { enabled: true, proxyUrl: 'http://localhost:8000/explain', timeoutMs: 200 }

describe('the provider surfaces a failure rather than a half-answer', () => {
  it('rejects a response that invents a figure, keeping nothing from it', async () => {
    await withFetch(
      async () => new Response(JSON.stringify({
        shortExplanation: 'להזמין 47 יחידות.',   // 47 is in no field of the record
        riskReason: 'r', businessImpact: 'b', confidenceNote: 'c',
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
      async () => {
        const result = await llmExplanationProvider.generateExplanation(
          { product, recommendation, marketContext: {}, facts }, opts,
        )
        expect(result.provider).toBe('llm-rejected')
        expect(result.explanation).toBeNull()
        expect(result.rejected.invented).toContain(47)
      },
    )
  })

  it.each([
    ['proxy down', async () => { throw new TypeError('fetch failed') }],
    ['429 rate limit', async () => new Response('rate limited', { status: 429 })],
    ['504 upstream timeout', async () => new Response('deadline', { status: 504 })],
    ['malformed JSON', async () => new Response('not json at all', { status: 200 })],
  ])('%s throws rather than returning something unusable', async (_name, impl) => {
    await withFetch(impl, async () => {
      await expect(
        llmExplanationProvider.generateExplanation(
          { product, recommendation, marketContext: {}, facts }, opts,
        ),
      ).rejects.toBeTruthy()
    })
  })
})

describe('the batch keeps the rule-based text through every failure', () => {
  const cases = [
    ['proxy down', async () => { throw new TypeError('fetch failed') }],
    ['429 rate limit', async () => new Response('rate limited', { status: 429 })],
    ['malformed JSON', async () => new Response('<html>', { status: 200 })],
    ['hangs past the timeout', () => new Promise(() => {})],
    ['invents a figure', async () => new Response(JSON.stringify({
      shortExplanation: 'להזמין 47 יחידות.', riskReason: 'r',
      businessImpact: 'b', confidenceNote: 'c',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })],
  ]

  it.each(cases)('%s -> rule-based text survives, no blank card', async (_name, impl) => {
    await withFetch(impl, async () => {
      const out = await annotateRecommendationsWithExplanations({
        provider: llmExplanationProvider,
        products: [product],
        recommendations: [recommendation],
        marketContext: {},
        timeoutMs: 150,
        t: (k) => k,
        language: 'he',
      })
      expect(out).toHaveLength(1)
      // Something is always displayable; never null, never empty.
      expect(out[0].explanation).toBeTruthy()
      expect(typeof out[0].explanation).toBe('string')
    })
  })

  it('never rejects the batch, so one bad row cannot blank the screen', async () => {
    await withFetch(async () => { throw new Error('boom') }, async () => {
      await expect(
        annotateRecommendationsWithExplanations({
          provider: llmExplanationProvider,
          products: [product],
          recommendations: [recommendation, { ...recommendation, productId: 'p1' }],
          marketContext: {},
          timeoutMs: 150,
          t: (k) => k,
          language: 'he',
        }),
      ).resolves.toBeTruthy()
    })
  })
})

describe('with the proxy switched off', () => {
  it('returns disabled rather than attempting a call', async () => {
    const spy = vi.fn()
    await withFetch(spy, async () => {
      const result = await llmExplanationProvider.generateExplanation(
        { product, recommendation, marketContext: {}, facts },
        { enabled: false, proxyUrl: null },
      )
      expect(result.provider).toBe('llm-disabled')
      expect(spy).not.toHaveBeenCalled()
    })
  })
})
