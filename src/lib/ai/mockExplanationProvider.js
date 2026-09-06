import { createTranslator, DEFAULT_LANGUAGE, formatNumber } from '../i18n/index.js'
import { renderReorderExplanation, renderReorderExplanationText } from '../i18n/explainReorder.js'

/**
 * Rule-based explanations, rendered from the facts the decision carried.
 *
 * WHAT WAS DELETED AND WHY
 *   This module used to answer every reorder with "Protects availability and
 *   reduces stockout risk." — a sentence true of every reorder ever written, which
 *   told the owner nothing and could not be checked against anything. With the LLM
 *   path switched off it was also the ONLY text he would actually see. The generic
 *   per-type strings are gone; there is no canned fallback to drift back to.
 *
 *   Reorder text now comes from recommendation.facts (src/lib/analytics/reorderFacts.js)
 *   via the i18n layer, so every figure in the sentence is the figure that produced
 *   the order quantity, in the reader's own language. Other recommendation types
 *   carry their own specific `reason` from the engine; that is used verbatim rather
 *   than replaced with a slogan.
 */
export const mockExplanationProvider = {
  id: 'mock',
  label: 'Rule-based explanation',
  enabled: true,
  generateExplanation({ recommendation, t, language }) {
    const translate = t ?? createTranslator(language ?? DEFAULT_LANGUAGE)
    const n = (value) => formatNumber(value, language ?? DEFAULT_LANGUAGE)

    if (recommendation?.type === 'REORDER' && recommendation.facts) {
      const parts = renderReorderExplanation(recommendation.facts, translate, n)
      return {
        provider: 'mock',
        explanation: renderReorderExplanationText(recommendation.facts, translate, n),
        // The four parts kept separate so a UI can lay them out rather than
        // re-splitting a paragraph.
        parts,
        riskReason: parts.timing,
        // Only stated when a cost price exists — null, never a zero that would
        // read as "nothing at stake".
        businessImpact: parts.cost,
        confidenceNote: parts.uncertainty,
      }
    }

    // Non-reorder types: the engine already wrote something specific.
    return {
      provider: 'mock',
      explanation: recommendation?.reason ?? '',
      parts: null,
      riskReason: recommendation?.reason ?? '',
      businessImpact: null,
      confidenceNote: null,
    }
  },
}
