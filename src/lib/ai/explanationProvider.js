import { llmExplanationProvider } from './llmExplanationProvider.js'
import { mockExplanationProvider } from './mockExplanationProvider.js'

export function annotateRecommendationsWithExplanations({
  marketContext,
  products,
  recommendations,
  provider = mockExplanationProvider,
}) {
  const productIndex = new Map(products.map((product) => [product.id, product]))

  return recommendations.map((recommendation) => {
    const product = productIndex.get(recommendation.productId)
    if (!product) {
      return {
        ...recommendation,
        explanation: recommendation.reason ?? '',
        explanationProvider: 'fallback',
      }
    }

    const result = provider.generateExplanation({
      marketContext,
      product,
      recommendation,
    })

    return {
      ...recommendation,
      explanation: result.explanation || recommendation.reason || '',
      explanationProvider: result.provider,
      explanationDetails: {
        riskReason: result.riskReason ?? recommendation.reason ?? '',
        businessImpact: result.businessImpact ?? '',
        confidenceNote: result.confidenceNote ?? '',
      },
    }
  })
}

export function getDefaultExplanationProvider() {
  const proxyUrl = import.meta.env.VITE_LLM_PROXY_URL
  if (proxyUrl) {
    return {
      ...llmExplanationProvider,
      generateExplanation(payload) {
        return llmExplanationProvider.generateExplanation(payload, { enabled: true, proxyUrl })
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
