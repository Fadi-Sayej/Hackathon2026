/**
 * The ten V1 pages (design §20.1: "nav reduced to 10 items").
 *
 * Its own file because a module that exports both components and constants breaks fast
 * refresh, and because this list is the nav's contract — the shell and the spine must agree
 * on it without importing each other's components.
 */
export const V1_PAGES = Object.freeze([
  'daily', 'price_consistency', 'reconciliation', 'hygiene',
  'competitor_position', 'catalogue_lifecycle', 'margin_below_cost',
  'questions', 'receiving', 'data',
])

export const CAPABILITY_PAGES = Object.freeze(new Set([
  'price_consistency', 'reconciliation', 'hygiene',
  'competitor_position', 'catalogue_lifecycle', 'margin_below_cost',
]))
