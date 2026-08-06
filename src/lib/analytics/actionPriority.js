/**
 * actionPriority.js — rank operational recommendations by money at stake.
 *
 * The pipeline emits 2,183 recommendations. A store manager has ten minutes, so the
 * order they appear in matters more than the list itself. Ranking is by estimated
 * shekels, not by category or count.
 *
 * Two rules come straight from what the YomYom manager told us on 05/08:
 *
 *   1. He said the stock counts are substantially wrong in both directions ("the
 *      report may say 8 Kinder chocolates when there is 1"). So anything derived from
 *      a stock quantity is data hygiene, not a money action, and must not lead the
 *      list or carry a shekel figure.
 *
 *   2. Prices are reliable. Selling below cost and shelf-vs-Wolt gaps are computed
 *      from prices alone, so they keep their full weight. These carry the product.
 */

import { credibleGap, credibleLoss, toNumber } from './credibility.js'

// Re-exported so existing consumers keep importing it from here; the guard
// thresholds themselves now live in credibility.js and are shared with
// reorderEngine's valueAtStake (Issue #39).
export { credibleLoss }

export const ACTION_GROUP = {
  MONEY: 'money',
  DATA: 'data',
}

const TYPE_RULES = {
  // Losing money on every single sale. Highest confidence we have.
  CHECK_MARGIN: { group: ACTION_GROUP.MONEY, weight: 1.0 },
  // Shelf and delivery prices disagree; one of them is wrong.
  CHECK_WOLT_PRICE_GAP: { group: ACTION_GROUP.MONEY, weight: 0.8 },
  // Expiry is real money, when we have a date at all.
  PROMOTE_EXPIRING_PRODUCT: { group: ACTION_GROUP.MONEY, weight: 0.9 },
  // Derived from stock counts the manager has told us not to trust.
  CHECK_NEGATIVE_STOCK: { group: ACTION_GROUP.DATA, weight: 0 },
  // Admin: can't scan or match it. No money attached.
  VERIFY_UNKNOWN_BARCODE: { group: ACTION_GROUP.DATA, weight: 0 },
}

const DEFAULT_RULE = { group: ACTION_GROUP.DATA, weight: 0 }

/**
 * Money at stake per unit sold, in shekels. Null when we cannot state a figure
 * honestly — the UI must then show no number rather than a zero.
 */
export function estimateImpact(rec) {
  const selling = toNumber(rec?.sellingPrice)
  const cost = toNumber(rec?.costPrice)
  const wolt = toNumber(rec?.woltPrice)

  switch (rec?.type) {
    case 'CHECK_MARGIN':
      return credibleLoss(selling, cost)
    case 'CHECK_WOLT_PRICE_GAP':
      return credibleGap(selling, wolt)
    case 'PROMOTE_EXPIRING_PRODUCT':
      // The value of ONE unit at risk, deliberately not multiplied by stock: the
      // manager told us stock counts are unreliable, so a lot value would be a
      // guess dressed up as a number.
      return selling
    default:
      return null
  }
}

export function actionGroup(rec) {
  return (TYPE_RULES[rec?.type] ?? DEFAULT_RULE).group
}

/**
 * Sort key. Impact in shekels, scaled by how much we trust the signal.
 */
export function priorityScore(rec) {
  const rule = TYPE_RULES[rec?.type] ?? DEFAULT_RULE
  if (rule.weight === 0) return 0

  const impact = estimateImpact(rec)
  if (impact == null) return 0

  const confidence = toNumber(rec?.confidence) ?? 0.5
  return impact * rule.weight * confidence
}

/**
 * Split recommendations into money actions (ranked) and data-quality items.
 */
export function rankActions(recommendations = []) {
  const money = []
  const data = []

  // A default parameter only covers `undefined`, so an explicit null would throw.
  // loadOperationalData() currently guarantees an array, but this function should not
  // depend on a caller two modules away staying defensive.
  if (!Array.isArray(recommendations)) return { money, data }

  for (const rec of recommendations) {
    const scored = {
      ...rec,
      impactIls: estimateImpact(rec),
      priorityScore: priorityScore(rec),
      group: actionGroup(rec),
    }
    if (scored.group === ACTION_GROUP.MONEY && scored.priorityScore > 0) {
      money.push(scored)
    } else {
      data.push(scored)
    }
  }

  money.sort((a, b) => b.priorityScore - a.priorityScore)
  data.sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))

  return { money, data }
}

/**
 * Total shekels represented by the ranked money actions — per unit sold, so it is
 * deliberately NOT presented as a total saving. We have no reliable sales volume yet.
 */
export function totalImpact(actions = []) {
  return actions.reduce((sum, action) => sum + (action.impactIls ?? 0), 0)
}
