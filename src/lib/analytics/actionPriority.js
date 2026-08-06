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

// A shelf price of ₪0.01 against a ₪2.28 cost is a data-entry error, not a -22,700%
// margin. Showing it as the single biggest opportunity in the shop would discredit
// every other number on the screen.
const MIN_CREDIBLE_PRICE = 0.5
const MAX_CREDIBLE_GAP_PCT = 300

// Cost recorded per CASE against a price recorded per UNIT looks identical to a
// catastrophic loss. Real examples from the YomYom export:
//
//   בראוניז (4*4)          sells ₪3.90   "cost" ₪238.00  (a whole case)
//   כוס חד פעמי 4 OZ       sells ₪8.56   "cost" ₪145.00  (a sleeve of cups)
//   שקית נייר 25/50 (2000) sells ₪95.58  "cost" ₪162.00  (2,000 bags)
//
// The pack size is often right there in the product name. Telling a manager he loses
// ₪234 on every brownie would discredit every other number on the screen, so anything
// beyond this ratio is treated as a cost-price data problem, not a loss. Genuine
// below-cost selling looks like ₪24.90 against a ₪30.00 cost — close, not 60x.
const MAX_CREDIBLE_COST_RATIO = 2

function toNumber(value) {
  const parsed = typeof value === 'string' ? Number(value) : value
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * Is this a believable below-cost sale, or a cost-price data problem?
 *
 * Shared so the action list and the price screen never disagree about how many
 * products are selling below cost — two screens giving different counts of the same
 * thing costs more credibility than either number is worth.
 *
 * @returns {number|null} loss per unit in shekels, or null if not credible
 */
export function credibleLoss(sellingPrice, costPrice) {
  const selling = toNumber(sellingPrice)
  const cost = toNumber(costPrice)
  if (selling == null || cost == null) return null
  if (selling < MIN_CREDIBLE_PRICE || cost <= 0) return null
  if (cost / selling > MAX_CREDIBLE_COST_RATIO) return null
  const loss = cost - selling
  return loss > 0 ? loss : null
}

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
    case 'CHECK_WOLT_PRICE_GAP': {
      if (selling == null || wolt == null) return null
      if (selling < MIN_CREDIBLE_PRICE || wolt < MIN_CREDIBLE_PRICE) return null
      const gap = Math.abs(wolt - selling)
      const gapPct = (gap / Math.min(selling, wolt)) * 100
      if (gapPct > MAX_CREDIBLE_GAP_PCT) return null
      return gap
    }
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
