/**
 * Deprecated direct Gemini browser client.
 *
 * Sprint C6 intentionally disables frontend LLM calls because browser-exposed
 * API keys are not safe for SaaS. Use llmExplanationProvider with a backend
 * proxy in a future sprint instead.
 */

export function isGeminiConfigured() {
  return false
}

export async function geminiGenerate() {
  throw new Error('Direct Gemini calls from the frontend are disabled. Use a backend proxy.')
}

export async function generateAIExplanation(_product, recommendation) {
  return recommendation?.reason ?? ''
}
