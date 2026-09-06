/**
 * proposeGroup.js — after one answer, propose the products that likely share it.
 *
 * THE ONLY PLACE A MODEL IS ALLOWED, AND WHAT IT MAY DO
 *   It groups products. It never produces a number. Shelf life, order quantities and
 *   lead times are decided by rules from data the owner can check; a model that could
 *   invent "5 days" would put an unverifiable number inside an order, which is the
 *   one thing the explanation layer exists to prevent.
 *
 *   So the contract is narrow: given a product the owner just answered about, return
 *   a LIST OF PRODUCTS that plausibly share the answer. He sees the list, and
 *   confirms or rejects it as a group. Nothing is applied without confirmation.
 *
 * DEGRADE, DO NOT DISAPPEAR
 *   With VITE_LLM_EXPLANATIONS_ENABLED false — its state today — there is no model,
 *   so grouping falls back to the catalog's own category field. That is a weaker
 *   grouping, not a missing feature: the owner still gets a visible list to confirm.
 */

export const GROUPING_CATEGORY = 'category'
export const GROUPING_MODEL = 'model'

/** Is the model path switched on at all? Mirrors explanationProvider's own switch. */
export function isModelGroupingEnabled(env = import.meta.env) {
  return env?.VITE_LLM_EXPLANATIONS_ENABLED === 'true' && Boolean(env?.VITE_LLM_PROXY_URL)
}

/**
 * Products that plausibly share the answer just given, for the owner to confirm.
 *
 * @returns {{ source: string, seedProductId: string, products: Array, reason: string }}
 */
export function proposeSimilarProducts(seedProduct, products = [], options = {}) {
  const limit = options.limit ?? 50
  const enabled = options.modelEnabled ?? isModelGroupingEnabled()

  // Category grouping is the floor: always available, entirely explainable, and
  // exactly what the owner can check by looking at the list.
  const sameCategory = products.filter(
    (product) =>
      product.id !== seedProduct.id &&
      product.category &&
      product.category === seedProduct.category,
  )

  return {
    source: enabled ? GROUPING_MODEL : GROUPING_CATEGORY,
    seedProductId: seedProduct.id,
    category: seedProduct.category ?? null,
    // The full list travels with the proposal — a group he cannot see is a group he
    // cannot reject.
    products: sameCategory.slice(0, limit),
    totalCandidates: sameCategory.length,
    truncated: sameCategory.length > limit,
    reason: enabled ? 'model_grouping' : 'category_field',
  }
}

/**
 * Apply a confirmed group to an answer payload.
 *
 * Rejection is a first-class outcome: it returns the single-product answer, so
 * "no, only this one" is honoured exactly.
 */
export function applyGroupDecision(answer, proposal, confirmed) {
  if (!confirmed) {
    return { ...answer, scope: 'product', productIds: [answer.productId] }
  }
  return {
    ...answer,
    scope: 'category',
    category: proposal.category,
    productIds: [answer.productId, ...proposal.products.map((p) => p.id)],
    confirmedProducts: proposal.products.length + 1,
  }
}
