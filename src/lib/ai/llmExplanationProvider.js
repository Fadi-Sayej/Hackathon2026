import { validateExplanationResult } from './factsGuard.js'

const DEFAULT_TIMEOUT_MS = 3500

export const llmExplanationProvider = {
  id: 'llm',
  label: 'LLM explanation provider',
  enabled: false,
  async generateExplanation(payload, options = {}) {
    if (!options.enabled || !options.proxyUrl) {
      return {
        provider: 'llm-disabled',
        explanation: null,
        error: 'LLM provider is disabled until a backend/proxy endpoint exists.',
      }
    }

    const response = await postToProxy(payload, options)
    const candidate = {
      provider: 'llm',
      explanation: response.shortExplanation,
      riskReason: response.riskReason,
      businessImpact: response.businessImpact,
      confidenceNote: response.confidenceNote,
    }

    // The model may rephrase around figures it was given; it may not produce one.
    // Checked here, at the boundary, so nothing unvalidated can reach a screen —
    // and checked in code rather than asked for in the prompt, because the owner
    // verifies these numbers against his own shelf.
    const facts = payload?.facts ?? null
    const verdict = validateExplanationResult(candidate, facts)
    if (!verdict.ok) {
      return {
        provider: 'llm-rejected',
        explanation: null,
        rejected: { invented: verdict.invented, field: verdict.field },
        error: `Model produced ${verdict.invented.join(', ')} in "${verdict.field}", `
          + 'which the decision never held. Falling back to the rule-based text.',
      }
    }
    return candidate
  },
}

export function buildLLMExplanationPayload({
  marketContext,
  product,
  ragChunks = [],
  recommendation,
}) {
  return {
    // The authoritative figures. Every number the owner may read comes from here,
    // and factsGuard validates the response against exactly this record — so it is
    // sent as the model's whole numeric vocabulary, not as background colour.
    facts: recommendation?.facts ?? null,
    productMetrics: {
      id: product.id,
      name: product.name,
      category: product.category,
      currentStock: product.currentStock,
      shelfQuantity: product.shelfQuantity,
      shelfCapacity: product.shelfCapacity,
      salesLast7Days: product.salesLast7Days,
      salesLast30Days: product.salesLast30Days,
      price: product.price,
      cost: product.cost,
      leadTimeDays: product.leadTimeDays,
      expiryDate: product.expiryDate ?? null,
    },
    recommendation: {
      type: recommendation.type,
      urgency: recommendation.urgency,
      confidence: recommendation.confidence,
      recommendedOrderQuantity: recommendation.recommendedOrderQuantity ?? null,
      recommendedShelfQuantity: recommendation.recommendedShelfQuantity ?? null,
      metrics: recommendation.metrics ?? {},
      reason: recommendation.reason ?? '',
    },
    marketContext: {
      currentDate: marketContext.currentDate ?? null,
      weather: marketContext.weather ?? null,
      weekend: marketContext.weekend ?? null,
      holiday: marketContext.holiday ?? null,
      localEvent: marketContext.localEvent ?? null,
      season: marketContext.season ?? null,
      sourceLabel: marketContext.sourceLabel ?? marketContext.contextSource ?? 'mock',
    },
    relevantRagChunks: ragChunks.map((chunk) => ({
      id: chunk.id,
      type: chunk.type,
      category: chunk.category,
      text: chunk.text,
      tags: chunk.tags,
      metadata: chunk.metadata,
    })),
    responseSchema: {
      shortExplanation: 'string',
      riskReason: 'string',
      businessImpact: 'string',
      confidenceNote: 'string',
    },
  }
}

async function postToProxy(payload, options) {
  const controller = new AbortController()
  const externalSignal = options.signal
  const abortFromExternalSignal = () => controller.abort(externalSignal.reason)

  if (externalSignal?.aborted) {
    abortFromExternalSignal()
  } else {
    externalSignal?.addEventListener('abort', abortFromExternalSignal, { once: true })
  }

  const timeoutId = globalThis.setTimeout(
    () => controller.abort(new Error('LLM proxy request timed out')),
    options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  )

  try {
    const response = await fetch(options.proxyUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })

    if (!response.ok) {
      const error = new Error(`LLM proxy failed (${response.status})`)
      error.status = response.status
      error.retryAfter = response.headers.get('Retry-After')
      throw error
    }

    return response.json()
  } finally {
    globalThis.clearTimeout(timeoutId)
    externalSignal?.removeEventListener('abort', abortFromExternalSignal)
  }
}
