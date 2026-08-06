import { llmExplanationProvider } from './llmExplanationProvider.js'
import { mockExplanationProvider } from './mockExplanationProvider.js'

/** Outer bound for a single remote explanation attempt. */
const DEFAULT_EXPLANATION_TIMEOUT_MS = 3500
const DEFAULT_EXPLANATION_CONCURRENCY = 8

/**
 * Synchronous mock/rule-based annotation.
 * Used for immediate UI rendering so managers never see blank cards or spinners.
 */
export function annotateRecommendationsWithMockExplanations({
  marketContext,
  products,
  recommendations,
}) {
  const productIndex = new Map(products.map((product) => [product.id, product]))

  return recommendations.map((recommendation) => {
    const product = productIndex.get(recommendation.productId)
    if (!product) {
      return buildFallbackAnnotation(recommendation)
    }

    const result = mockExplanationProvider.generateExplanation({
      marketContext,
      product,
      recommendation,
    })

    return buildAnnotatedRecommendation(recommendation, result)
  })
}

/**
 * Asynchronous annotation pipeline.
 *
 * Always starts from the mock/rule-based explanation so failure paths retain
 * honest text. When a remote provider is selected, each recommendation is
 * upgraded independently with bounded parallelism — never serialized across
 * 2,000+ rows and never sent as one unbounded request burst. HTTP 429, timeouts,
 * proxy errors, malformed payloads, and rejected promises all keep the mock
 * explanation for that row.
 */
export async function annotateRecommendationsWithExplanations({
  marketContext,
  products,
  recommendations,
  provider = mockExplanationProvider,
  timeoutMs = DEFAULT_EXPLANATION_TIMEOUT_MS,
  concurrency = DEFAULT_EXPLANATION_CONCURRENCY,
  signal,
}) {
  const productIndex = new Map(products.map((product) => [product.id, product]))
  const mockAnnotated = annotateRecommendationsWithMockExplanations({
    marketContext,
    products,
    recommendations,
  })

  if (!provider || provider === mockExplanationProvider || provider.id === 'mock') {
    return mockAnnotated
  }

  const upgraded = [...mockAnnotated]
  let nextIndex = 0
  const workerCount = Math.min(
    recommendations.length,
    normalizeConcurrency(concurrency),
  )

  async function upgradeNext() {
    while (!signal?.aborted && nextIndex < recommendations.length) {
      const index = nextIndex
      nextIndex += 1
      const recommendation = recommendations[index]
      const product = productIndex.get(recommendation.productId)
      if (!product) {
        continue
      }

      try {
        const result = await withTimeout(
          (requestSignal) =>
            provider.generateExplanation({
              marketContext,
              product,
              recommendation,
            }, {
              signal: requestSignal,
              timeoutMs,
            }),
          timeoutMs,
          signal,
        )

        if (isUsableExplanationResult(result)) {
          upgraded[index] = buildAnnotatedRecommendation(recommendation, result)
        }
      } catch {
        // Preserve mock text on 429 / timeout / network / parse / any rejection.
        // Never rethrow — one failure must not reject the whole batch or surface
        // as an unhandled Promise rejection.
      }
    }
  }

  await Promise.all(Array.from({ length: workerCount }, () => upgradeNext()))
  return upgraded
}

export function getDefaultExplanationProvider() {
  const proxyUrl = import.meta.env.VITE_LLM_PROXY_URL
  if (proxyUrl) {
    return {
      ...llmExplanationProvider,
      generateExplanation(payload, options = {}) {
        return llmExplanationProvider.generateExplanation(payload, {
          ...options,
          enabled: true,
          proxyUrl,
          timeoutMs: options.timeoutMs ?? DEFAULT_EXPLANATION_TIMEOUT_MS,
        })
      },
    }
  }
  return mockExplanationProvider
}

export function getLLMExplanationProviderStatus() {
  const proxyUrl = import.meta.env.VITE_LLM_PROXY_URL
  return {
    provider: llmExplanationProvider.id,
    enabled: Boolean(proxyUrl),
    reason: proxyUrl
      ? `LLM proxy active at ${proxyUrl}`
      : 'Disabled until a backend/proxy is available. Mock explanations remain the default.',
  }
}

function buildFallbackAnnotation(recommendation) {
  return {
    ...recommendation,
    explanation: getFallbackExplanation(recommendation),
    explanationProvider: 'fallback',
  }
}

function buildAnnotatedRecommendation(recommendation, result) {
  return {
    ...recommendation,
    explanation: result.explanation || getFallbackExplanation(recommendation),
    explanationProvider: result.provider,
    explanationDetails: {
      riskReason: result.riskReason ?? recommendation.reason ?? '',
      businessImpact: result.businessImpact ?? '',
      confidenceNote: result.confidenceNote ?? '',
    },
  }
}

function getFallbackExplanation(recommendation) {
  const reason = recommendation.reason
  return typeof reason === 'string' && reason.trim() ? reason : 'Manager review required.'
}

function isUsableExplanationResult(result) {
  return Boolean(
    result &&
      typeof result === 'object' &&
      typeof result.explanation === 'string' &&
      result.explanation.trim().length > 0,
  )
}

function normalizeConcurrency(concurrency) {
  return Number.isFinite(concurrency) && concurrency > 0
    ? Math.max(1, Math.floor(concurrency))
    : DEFAULT_EXPLANATION_CONCURRENCY
}

function withTimeout(run, timeoutMs, signal) {
  return new Promise((resolve, reject) => {
    const requestController = new AbortController()
    let timeoutId

    function cleanup() {
      if (timeoutId) globalThis.clearTimeout(timeoutId)
      signal?.removeEventListener('abort', handleAbort)
    }

    function handleAbort() {
      requestController.abort(signal?.reason)
      cleanup()
      reject(new Error('Explanation request superseded'))
    }

    function handleTimeout() {
      requestController.abort(new Error('Explanation provider timed out'))
      cleanup()
      reject(new Error('Explanation provider timed out'))
    }

    if (signal?.aborted) {
      handleAbort()
      return
    }

    signal?.addEventListener('abort', handleAbort, { once: true })
    if (Number.isFinite(timeoutMs) && timeoutMs > 0) {
      timeoutId = globalThis.setTimeout(handleTimeout, timeoutMs)
    }

    Promise.resolve()
      .then(() => run(requestController.signal))
      .then(
        (value) => {
          cleanup()
          resolve(value)
        },
        (error) => {
          cleanup()
          reject(error)
        },
      )
  })
}
