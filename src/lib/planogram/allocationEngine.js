/**
 * Shelf-space allocation — the SSAP layer.
 *
 * WHAT PROBLEM THIS SOLVES
 *   Given a fixture with a known shelf run, and a set of products with known
 *   package widths, decide which product goes on which shelf and how many
 *   facings it gets. That is the Shelf Space Allocation Problem, and it is a
 *   constrained optimisation, not a ranking.
 *
 *   `src/lib/analytics/planogramEngine.js` scores products and calls the top of
 *   the list "eye level". It never asks whether the products it placed there
 *   physically fit, because it has no widths and no shelf. This module does.
 *
 * THE OBJECTIVE
 *   profit per centimetre of shelf:
 *
 *     value(p) = (price − cost) × demand(p) ÷ packageWidthCm(p)
 *
 *   Space is the scarce resource, so profit has to be expressed per unit of it.
 *   A ₪3 margin on a 5cm gum packet beats a ₪4 margin on a 22cm rice sack.
 *
 * THE DEMAND TERM IS PARTIAL, AND SAYS SO
 *   1,564 of the 7,451 catalogue products carry usable velocity (504 high, 1,060
 *   medium); the remaining 5,887 do not. So `demand` is measured for some rows
 *   and a category-level assumption for the rest, and the split varies by
 *   department.
 *
 *   `estimateDemand()` therefore blends the two in proportion to confidence and
 *   returns that confidence alongside every figure. `summary.demandConfidence`
 *   carries the mix up to the UI, which states it per fixture rather than making
 *   a blanket claim — an earlier version asserted flatly that there was no sales
 *   history at all, which was false and visible on screen.
 *
 *   Where confidence is `none` the objective degrades to margin-per-centimetre,
 *   which is a defensible ranking rather than a fabricated one.
 *
 * WHY GREEDY AND NOT MILP
 *   Marginal profit per centimetre is decreasing in facings (see
 *   SPACE_ELASTICITY), so allocating each next centimetre to whichever product
 *   values it most is the textbook greedy solution to a fractional-knapsack
 *   shape, and lands within a few percent of optimal. A MILP would buy that few
 *   percent at the cost of a solver in the browser, and would still be solving
 *   for a demand term we do not have. Revisit when sales data lands.
 */

import { packageGeometry, isShelvable } from './packageShapes.js'
import { describeShelves } from './fixtures.js'
import { resolveVelocityConfidence, VELOCITY_CONFIDENCE } from '../analytics/velocityConfidence.js'

/**
 * Space elasticity of demand: doubling facings does NOT double sales.
 *
 * Drèze, Hoch & Purk's shelf-management work puts the exposure elasticity of a
 * typical grocery item around 0.1–0.2 — the second facing of a product earns far
 * less than the first. Without this, the greedy loop hands the entire shelf to
 * whichever product scored highest.
 */
export const SPACE_ELASTICITY = 0.2

/** How much of a velocity figure we believe, by how much history backs it. */
const CONFIDENCE_WEIGHT = {
  [VELOCITY_CONFIDENCE.high]: 1,
  [VELOCITY_CONFIDENCE.medium]: 0.7,
  [VELOCITY_CONFIDENCE.low]: 0.35,
  [VELOCITY_CONFIDENCE.none]: 0,
}

/** Packages above this volume go low: heavy to lift, and they block sightlines. */
const HEAVY_LITRES = 2.5

/** Shelf levels in descending commercial desirability. */
const LEVEL_PRIORITY = ['EYE_LEVEL', 'MIDDLE', 'TOP', 'BOTTOM']

/** Bottles and jars topple; flat boxes stack. Cap the optimism either way. */
const MAX_STACK = 3

/**
 * Facing caps. Both are needed, and neither alone is enough.
 *
 * Greedy allocation with a decreasing marginal value still hands a six-metre
 * shelf to one product when nothing else competes — an early run of this engine
 * produced 66 facings of a single bottled water, which is not a planogram, it is
 * a wall of water. Real planograms cap facings in the low teens, and no single
 * product blocks more than about a third of a bay.
 */
const MAX_FACINGS = 12
const MAX_SHELF_SHARE = 0.35

/**
 * Facings the average carried product should get.
 *
 * This is the assortment decision, and it has to be made BEFORE facings are
 * allocated. A 6m gondola holds about 266 nine-centimetre facings; the beverage
 * department has 500 SKUs. Feeding all 500 in produces a "planogram" of 266
 * products at one facing each — technically full, operationally useless, and
 * nothing like what a shop looks like.
 *
 * So the bay carries the top N by profit per centimetre, where N is chosen to
 * leave room for roughly three facings each, and everything below the line is
 * reported as not carried. That report is the useful half of the answer: it is
 * the assortment recommendation for this bay.
 */
const TARGET_AVERAGE_FACINGS = 3

/**
 * How far above its department's median margin a product may sit before it is
 * treated as a data error rather than a very profitable line.
 *
 * The YomYom export files a 65-inch television, a gaming desk and a headset
 * under `מוצרי מכולת` — groceries. Their margins are three orders of magnitude
 * above a bag of pasta, so profit-per-centimetre handed them the best shelf in
 * the store, and the screen ended up recommending facings for a television.
 *
 * Twenty times the median is deliberately far out. A premium olive oil is two or
 * three times its category; nothing legitimately sold off a grocery gondola is
 * twenty. Anything past it is reported for a human to look at, never silently
 * dropped and never acted on.
 */
const MARGIN_OUTLIER_MULTIPLE = 20

/**
 * Units per day for a product, with an explicit confidence.
 *
 * `contextMultiplier` is the demand index from `demandEngine.computeDemand()` —
 * weather, holidays, season. It is a multiplier around 1.0 and applies whether
 * or not velocity is known, because it describes the day, not the product's
 * history.
 */
export function estimateDemand(product, { contextMultiplier = 1, categoryBaseline = 1 } = {}) {
  const confidence = resolveVelocityConfidence(product)
  const weight = CONFIDENCE_WEIGHT[confidence] ?? 0
  const measured = product?.analytics?.weightedAvgDailySales ?? 0

  // Blend measured velocity toward the category baseline in proportion to how
  // much history stands behind it. At confidence `none` this is pure baseline.
  const blended = weight * measured + (1 - weight) * categoryBaseline

  return {
    unitsPerDay: Math.max(0, blended * contextMultiplier),
    confidence,
    measured,
    contextMultiplier,
  }
}

/**
 * Per-product inputs to the allocation: geometry, demand, and value density.
 */
export function scoreProductForShelf(product, options = {}) {
  const geometry = packageGeometry(product)
  const demand = estimateDemand(product, options)
  const marginPerUnit = Math.max(0, (product.price ?? 0) - (product.cost ?? 0))
  const litres = (geometry.widthCm * geometry.heightCm * geometry.depthCm) / 1000

  return {
    product,
    ...geometry,
    demand,
    marginPerUnit,
    litres,
    heavy: litres >= HEAVY_LITRES,
    // The objective. Guard the divisor — a zero-width archetype would be a data
    // bug, but it must not produce Infinity and win the whole shelf.
    profitPerCm: geometry.widthCm > 0 ? (marginPerUnit * demand.unitsPerDay) / geometry.widthCm : 0,
    // Ranking fallback for the all-zero-demand case: margin alone, per cm.
    marginPerCm: geometry.widthCm > 0 ? marginPerUnit / geometry.widthCm : 0,
  }
}

/** Marginal value of adding the nth facing, given space elasticity. */
function marginalFacingValue(candidate, nth) {
  const growth = nth ** SPACE_ELASTICITY - (nth - 1) ** SPACE_ELASTICITY
  return (candidate.profitPerCm || candidate.marginPerCm) * growth
}

/**
 * Allocate products across one fixture unit.
 *
 * @param unit               fixture from the layout editor
 * @param products           analysed products (post `analyzeProducts`)
 * @param demandIndexById    optional map of productId -> context multiplier
 * @param shelfDepthCm       usable depth; defaults to the unit's own footprint
 * @param replenishmentDays  how long until the shelf is refilled
 */
export function allocateUnit({
  unit,
  products,
  demandIndexById = {},
  shelfDepthCm = null,
  replenishmentDays = 2,
}) {
  const shelves = describeShelves(unit)
  if (!shelves.length || !Array.isArray(products) || !products.length) {
    return { shelves: [], unplaced: products ?? [], notCarried: [], suspect: [], summary: emptySummary() }
  }

  const depthCm = shelfDepthCm ?? Math.min(unit.w, unit.d) * 100

  // Services and till-only rows never reach the shelf. See `isShelvable()`.
  const shelvable = products.filter(isShelvable)
  if (!shelvable.length) {
    return { shelves: [], unplaced: [], notCarried: [], suspect: [], summary: emptySummary() }
  }

  const categoryBaselines = buildCategoryBaselines(shelvable)

  const scored = shelvable.map((product) =>
    scoreProductForShelf(product, {
      contextMultiplier: demandIndexById[product.id] ?? 1,
      categoryBaseline: categoryBaselines.get(product.category) ?? 1,
    }),
  )

  // Pull out the products whose margin cannot be true for their department
  // before they can win the best shelf in the store.
  const { keep, suspect } = partitionMarginOutliers(scored)

  const ranked = keep.sort(
    (left, right) => right.profitPerCm - left.profitPerCm || right.marginPerCm - left.marginPerCm,
  )

  // The assortment decision, made before any facing is allocated.
  const carried = selectAssortment(ranked, shelves)
  const candidates = carried.selected
  const notCarried = carried.rejected

  // Pass 1 — seed one facing per product, best products onto the best shelves,
  // but spread across the bay rather than filling shelf one and leaving the rest
  // empty. The quota is what does the spreading: a shelf stops accepting new
  // products once it holds its share, so the next-ranked product moves down.
  const allocation = shelves.map((shelf) => ({ ...shelf, usedCm: 0, items: [] }))
  const quota = Math.ceil(candidates.length / allocation.length)
  const unplaced = []

  for (const candidate of candidates) {
    const shelf = pickShelf(allocation, candidate, quota) ?? pickShelf(allocation, candidate, Infinity)
    if (!shelf) {
      unplaced.push(candidate.product)
      continue
    }
    shelf.items.push({ candidate, facings: 1 })
    shelf.usedCm += candidate.widthCm
  }

  // Pass 2 — spend each shelf's remaining centimetres on whichever product on it
  // values the next facing most, until the shelf is full or every product has
  // hit its cap.
  for (const shelf of allocation) {
    let guard = 0
    while (guard++ < 500) {
      const remaining = shelf.runCm - shelf.usedCm

      let best = null
      let bestValue = 0
      for (const entry of shelf.items) {
        if (entry.candidate.widthCm > remaining) continue
        if (entry.facings >= facingCap(entry.candidate, shelf.runCm)) continue
        const value = marginalFacingValue(entry.candidate, entry.facings + 1) / entry.candidate.widthCm
        if (value > bestValue) {
          bestValue = value
          best = entry
        }
      }
      if (!best || bestValue <= 0) break

      best.facings += 1
      shelf.usedCm += best.candidate.widthCm
    }
  }

  return {
    shelves: allocation.map((shelf) => finaliseShelf(shelf, depthCm, replenishmentDays)),
    unplaced,
    notCarried,
    suspect,
    summary: buildSummary(allocation, unplaced, notCarried, suspect),
  }
}

/**
 * Split off products whose margin marks them as miscategorised.
 *
 * Median rather than mean, because the mean is exactly what a television drags
 * upward — the outlier would raise the threshold enough to admit itself.
 */
export function partitionMarginOutliers(scored) {
  const byCategory = new Map()
  for (const candidate of scored) {
    const bucket = byCategory.get(candidate.product.category) ?? []
    bucket.push(candidate.marginPerUnit)
    byCategory.set(candidate.product.category, bucket)
  }

  const thresholds = new Map()
  for (const [category, margins] of byCategory) {
    // A handful of products has no meaningful median; leave those alone.
    if (margins.length < 8) continue
    const sorted = [...margins].sort((left, right) => left - right)
    const median = sorted[Math.floor(sorted.length / 2)]
    if (median > 0) thresholds.set(category, median * MARGIN_OUTLIER_MULTIPLE)
  }

  const keep = []
  const suspect = []
  for (const candidate of scored) {
    const limit = thresholds.get(candidate.product.category)
    if (limit !== undefined && candidate.marginPerUnit > limit) {
      suspect.push({
        product: candidate.product,
        reason: 'MARGIN_OUTLIER',
        marginPerUnit: round(candidate.marginPerUnit),
        categoryLimit: round(limit),
      })
    } else {
      keep.push(candidate)
    }
  }

  return { keep, suspect }
}

/**
 * Decide how many products the bay carries, before allocating any facings.
 *
 * Take the top N by profit per centimetre, where N leaves room for roughly
 * TARGET_AVERAGE_FACINGS each at the average package width of the ranked list.
 * The rejected tail is returned, not discarded — it is the assortment
 * recommendation for this bay, and the more useful half of the answer when a
 * 500-SKU department is being planned onto a six-metre gondola.
 */
function selectAssortment(ranked, shelves) {
  const totalRunCm = shelves.reduce((sum, shelf) => sum + shelf.runCm, 0)
  const averageWidthCm =
    ranked.reduce((sum, candidate) => sum + candidate.widthCm, 0) / ranked.length || 1
  const capacity = Math.max(1, Math.floor(totalRunCm / (averageWidthCm * TARGET_AVERAGE_FACINGS)))

  return {
    selected: ranked.slice(0, capacity),
    rejected: ranked.slice(capacity).map((candidate) => candidate.product),
  }
}

/** Most facings this product may take on a shelf of the given run. */
function facingCap(candidate, runCm) {
  const byShare = Math.floor((runCm * MAX_SHELF_SHARE) / candidate.widthCm)
  return Math.max(1, Math.min(MAX_FACINGS, byShare))
}

/**
 * Choose the best shelf a candidate physically fits on.
 *
 * Constraints, in order of authority:
 *   1. vertical clearance — a 32cm bottle cannot go on a 25cm shelf
 *   2. heavy goods sit low — safety and sightlines, not profitability
 *   3. remaining run — one facing has to fit
 * Only then does commercial desirability decide.
 */
function pickShelf(allocation, candidate, quota) {
  const eligible = allocation.filter(
    (shelf) =>
      shelf.items.length < quota &&
      shelf.clearanceCm >= candidate.heightCm &&
      shelf.runCm - shelf.usedCm >= candidate.widthCm,
  )
  // Heavy goods are restricted to the bottom shelf, and that is a hard rule, not
  // a preference. Falling back to a higher shelf when the bottom is full is what
  // an earlier version did; it put 30 five-kilo rice sacks at eye level, which
  // `planValidation.js` then correctly reported as 28 safety violations. When
  // there is no room low down the product goes unplaced, and the shortage is
  // reported rather than resolved by breaking the rule.
  if (candidate.heavy) {
    return eligible.find((shelf) => shelf.shelfLevel === 'BOTTOM') ?? null
  }

  if (!eligible.length) return null

  return eligible.sort(
    (left, right) =>
      LEVEL_PRIORITY.indexOf(left.shelfLevel) - LEVEL_PRIORITY.indexOf(right.shelfLevel) ||
      right.runCm - right.usedCm - (left.runCm - left.usedCm),
  )[0]
}

/** Turn an allocated shelf into the shape the renderer consumes. */
function finaliseShelf(shelf, depthCm, replenishmentDays) {
  return {
    index: shelf.index,
    code: shelf.code,
    shelfLevel: shelf.shelfLevel,
    levelLabel: shelf.levelLabel,
    runCm: Math.round(shelf.runCm),
    usedCm: Math.round(shelf.usedCm),
    clearanceCm: shelf.clearanceCm,
    fillRatio: shelf.runCm > 0 ? shelf.usedCm / shelf.runCm : 0,
    items: shelf.items.map(({ candidate, facings }) => {
      const depthUnits = depthCapacity(depthCm, candidate.depthCm)
      const stack = stackLimit(shelf.clearanceCm, candidate.heightCm)
      const onShelf = facings * depthUnits * stack
      return {
        productId: candidate.product.id,
        productName: candidate.product.name,
        category: candidate.product.category,
        shapeKey: candidate.shapeKey,
        estimatedGeometry: candidate.estimatedGeometry,
        facings,
        depthUnits,
        stack,
        onShelf,
        widthCm: candidate.widthCm,
        // Height and volume travel with the placement so `planValidation.js` can
        // re-check clearance and heavy-goods placement independently, rather
        // than trusting that this engine applied its own constraints.
        heightCm: candidate.heightCm,
        litres: round(candidate.litres),
        currentStock: stockOnHand(candidate.product),
        marginPerUnit: round(candidate.marginPerUnit),
        profitPerCm: round(candidate.profitPerCm),
        demandPerDay: round(candidate.demand.unitsPerDay),
        demandConfidence: candidate.demand.confidence,
        ...fillStatus(candidate, onShelf, replenishmentDays),
      }
    }),
  }
}

/**
 * How urgently this position needs restocking.
 *
 * When velocity is trustworthy, days-of-supply against the replenishment cycle
 * is the right question. When it is not — which is the current state of the data
 * for almost every product — days-of-supply is infinite and meaningless, so the
 * question becomes the one the stock figure can actually answer: is there enough
 * in the back room to fill the facings we just allocated?
 */
function fillStatus(candidate, onShelf, replenishmentDays) {
  const stock = stockOnHand(candidate.product)

  if (candidate.demand.confidence !== VELOCITY_CONFIDENCE.none && candidate.demand.unitsPerDay > 0) {
    const daysOfSupply = onShelf / candidate.demand.unitsPerDay
    if (daysOfSupply < replenishmentDays) {
      return { status: 'out', daysOfSupply: round(daysOfSupply), statusBasis: 'days_of_supply' }
    }
    if (daysOfSupply < replenishmentDays * 1.5) {
      return { status: 'low', daysOfSupply: round(daysOfSupply), statusBasis: 'days_of_supply' }
    }
    return { status: 'ok', daysOfSupply: round(daysOfSupply), statusBasis: 'days_of_supply' }
  }

  if (stock <= 0) return { status: 'out', daysOfSupply: null, statusBasis: 'stock_on_hand' }
  if (stock < onShelf) return { status: 'low', daysOfSupply: null, statusBasis: 'stock_on_hand' }
  return { status: 'ok', daysOfSupply: null, statusBasis: 'stock_on_hand' }
}

/**
 * Stock on hand, floored at zero.
 *
 * 625 rows in the YomYom export carry negative stock — a till artefact, not a
 * negative quantity of anything. `normalize-datasets.mjs` clamps these on the
 * data path, but products can also reach this engine from a CSV connector, so
 * the clamp is repeated here rather than assumed.
 */
function stockOnHand(product) {
  return Math.max(0, product?.currentStock ?? 0)
}

/**
 * Units that fit behind one facing.
 *
 * Exported so the baselines in `baselines.js` count depth the same way. When
 * they did not, the baseline reported only its front row and the comparison
 * measured bookkeeping rather than allocation quality — a 30x flattering error.
 */
export function depthCapacity(shelfDepthCm, packageDepthCm) {
  if (!(packageDepthCm > 0)) return 1
  return Math.max(1, Math.floor(shelfDepthCm / packageDepthCm))
}

/** Round packages stack; tall ones topple. */
export function stackLimit(clearanceCm, heightCm) {
  if (heightCm <= 0) return 1
  if (heightCm > 15) return 1
  return Math.max(1, Math.min(MAX_STACK, Math.floor(clearanceCm / heightCm)))
}

/**
 * Category-level demand baseline, used where a product has no usable velocity.
 *
 * Derived from stock on hand: a store carrying 400 units of a category is
 * turning more of it than one carrying 8. This is a proxy, not a measurement,
 * and every figure built on it carries `confidence: 'none'`.
 */
function buildCategoryBaselines(products) {
  const totals = new Map()
  for (const product of products) {
    const entry = totals.get(product.category) ?? { stock: 0, count: 0 }
    entry.stock += Math.max(0, product.currentStock ?? 0)
    entry.count += 1
    totals.set(product.category, entry)
  }

  const baselines = new Map()
  for (const [category, entry] of totals) {
    const perProduct = entry.count ? entry.stock / entry.count : 0
    // Compress the range: stock differences of 50x do not mean sales
    // differences of 50x. The square root keeps the ordering and kills the tail.
    baselines.set(category, Math.max(0.2, Math.min(6, Math.sqrt(perProduct) / 2)))
  }
  return baselines
}

function buildSummary(allocation, unplaced, notCarried = [], suspect = []) {
  const items = allocation.flatMap((shelf) => shelf.items)

  // How much of this plan rests on measured velocity rather than a category
  // assumption. The screen used to state flatly that there is no sales history,
  // which is false for this store — 1,564 of 7,451 products carry medium or high
  // confidence. A blanket claim in either direction misleads; the mix does not.
  const demandConfidence = { none: 0, low: 0, medium: 0, high: 0 }
  for (const item of items) {
    // `buildSummary` runs on the pre-finalised allocation, where an item is
    // still `{ candidate, facings }` — the enriched shape comes later.
    const level = item.candidate?.demand?.confidence
    if (level in demandConfidence) demandConfidence[level] += 1
  }
  const runCm = allocation.reduce((sum, shelf) => sum + shelf.runCm, 0)
  const usedCm = allocation.reduce((sum, shelf) => sum + shelf.usedCm, 0)
  return {
    placedProducts: items.length,
    unplacedProducts: unplaced.length,
    notCarriedProducts: notCarried.length,
    suspectProducts: suspect.length,
    demandConfidence,
    totalFacings: items.reduce((sum, entry) => sum + entry.facings, 0),
    fillRatio: runCm > 0 ? usedCm / runCm : 0,
    estimatedGeometryCount: items.filter((entry) => entry.candidate.estimatedGeometry).length,
  }
}

function emptySummary() {
  return {
    placedProducts: 0,
    unplacedProducts: 0,
    notCarriedProducts: 0,
    suspectProducts: 0,
    demandConfidence: { none: 0, low: 0, medium: 0, high: 0 },
    totalFacings: 0,
    fillRatio: 0,
    estimatedGeometryCount: 0,
  }
}

function round(value) {
  return Math.round(value * 100) / 100
}
