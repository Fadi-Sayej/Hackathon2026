import { generateMockAIExplanation } from '../analytics/mockAI.js'

export const mockExplanationProvider = {
  id: 'mock',
  label: 'Mock AI explanation',
  enabled: true,
  generateExplanation({ product, recommendation, marketContext }) {
    return {
      provider: 'mock',
      explanation: generateMockAIExplanation(product, recommendation, marketContext),
      riskReason: recommendation.reason ?? '',
      businessImpact: summarizeBusinessImpact(recommendation),
      confidenceNote: `Confidence: ${Math.round((recommendation.confidence ?? 0) * 100)}% based on local demo rules.`,
    }
  },
}

function summarizeBusinessImpact(recommendation) {
  switch (recommendation.type) {
    case 'REORDER':
      return 'Protects availability and reduces stockout risk.'
    case 'REDUCE_STOCK':
      return 'Reduces excess inventory and frees working capital.'
    case 'PROMOTION':
      return 'Helps move slow or expiring stock before waste increases.'
    case 'SHELF_INCREASE':
      return 'Gives more visibility to a high-performing product.'
    case 'SHELF_DECREASE':
      return 'Returns shelf space to stronger-moving products.'
    default:
      return 'Supports a manager review decision.'
  }
}
