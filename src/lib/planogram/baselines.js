/**
 * Baselines, and the harness that compares plans against them.
 *
 * A planogram engine that has never been measured against a dumb rule is a
 * claim, not a result. The literature's standard set is:
 *
 *   B0  the shelf as it stands today
 *   B1  facings proportional to sales share
 *   B2  facings proportional to margin share
 *   B3  greedy, capacity-aware
 *
 * B1 is only partly available — 1,564 of 7,451 products carry usable velocity,
 * so a sales-proportional rule would rank most of the catalogue on nothing — and B0
 * needs a physical audit of the store. B2 is computable today, and B3 is what
 * `allocationEngine.js` already does. So B2 is the bar the greedy allocator has
 * to clear, and this module exists to hold it to that.
 *
 * If B3 does not beat B2 on margin per linear metre AND on stability, the extra
 * machinery is not earning its keep and the objective is what needs fixing.
 */

import { packageGeometry, isShelvable } from './packageShapes.js'
import { describeShelves } from './fixtures.js'
import { depthCapacity, partitionMarginOutliers, stackLimit } from './allocationEngine.js'

/** Same ceiling the greedy allocator uses, so the comparison is like-for-like. */
const MAX_FACINGS = 12

/**
 * B2 — facings proportional to each product's share of total margin.
 *
 * The classic space-to-sales heuristic with margin substituted for sales. It is
 * a genuinely reasonable rule, which is what makes it a fair opponent: it
 * ignores package width, replenishment, shelf height and substitution, and the
 * greedy allocator has to prove those omissions cost something.
 */
export function allocateMarginProportional({ unit, products, shelfDepthCm = null }) {
  const depthCm = shelfDepthCm ?? Math.min(unit.w, unit.d) * 100
  const shelves = describeShelves(unit).map((shelf) => ({ ...shelf, usedCm: 0, items: [] }))
  const shelvable = (products ?? []).filter(isShelvable)
  if (!shelves.length || !shelvable.length) {
    return { shelves, summary: { placedProducts: 0, totalFacings: 0 } }
  }

  // The same miscategorisation gate the allocator applies. Without it the
  // baseline keeps a television that the allocator dropped, and the comparison
  // measures which side inherited the data error rather than which allocation is
  // better — it once reported the engine 66% WORSE than its own baseline.
  const { keep } = partitionMarginOutliers(
    shelvable.map((product) => ({
      product,
      ...packageGeometry(product),
      marginPerUnit: Math.max(0, (product.price ?? 0) - (product.cost ?? 0)),
    })),
  )
  const scored = keep.sort((left, right) => right.marginPerUnit - left.marginPerUnit)

  const totalMargin = scored.reduce((sum, entry) => sum + entry.marginPerUnit, 0)
  const totalRunCm = shelves.reduce((sum, shelf) => sum + shelf.runCm, 0)

  // Desired facings from the margin share alone — the whole of the rule.
  const desired = scored.map((entry) => {
    const share = totalMargin > 0 ? entry.marginPerUnit / totalMargin : 1 / scored.length
    const fromShare = Math.floor((share * totalRunCm) / entry.widthCm)
    return { entry, facings: Math.max(1, Math.min(MAX_FACINGS, fromShare)) }
  })

  // Pack in margin order until the fixture is full. Anything that no longer fits
  // is simply not carried, which is the rule's implicit assortment decision.
  let shelfIndex = 0
  for (const { entry, facings } of desired) {
    while (shelfIndex < shelves.length) {
      const shelf = shelves[shelfIndex]
      const free = shelf.runCm - shelf.usedCm
      const affordable = Math.floor(free / entry.widthCm)
      if (affordable >= 1) {
        const placed = Math.min(facings, affordable)
        // Depth and stacking are computed exactly as the greedy allocator does,
        // via the shared helpers, so `comparePlans` compares allocations rather
        // than two different ways of counting the same shelf.
        const depthUnits = depthCapacity(depthCm, entry.depthCm)
        const stack = stackLimit(shelf.clearanceCm, entry.heightCm)
        shelf.items.push({
          productId: entry.product.id,
          productName: entry.product.name,
          facings: placed,
          widthCm: entry.widthCm,
          heightCm: entry.heightCm,
          depthUnits,
          stack,
          marginPerUnit: entry.marginPerUnit,
          onShelf: placed * depthUnits * stack,
        })
        shelf.usedCm = round(shelf.usedCm + placed * entry.widthCm)
        break
      }
      shelfIndex += 1
    }
    if (shelfIndex >= shelves.length) break
  }

  const items = shelves.flatMap((shelf) => shelf.items)
  return {
    shelves,
    summary: {
      placedProducts: items.length,
      totalFacings: items.reduce((sum, item) => sum + item.facings, 0),
    },
  }
}

/**
 * Compare any set of plans on the measures that decide whether one is better.
 *
 * Margin per linear METRE, not total margin: space is the scarce resource, and a
 * plan that earns the same money in half the run is twice as good.
 */
export function comparePlans(plans, { reference = null } = {}) {
  const result = {}

  for (const [name, plan] of Object.entries(plans)) {
    const items = (plan?.shelves ?? []).flatMap((shelf) => shelf.items ?? [])
    const usedMetres = items.reduce((sum, item) => sum + (item.facings * item.widthCm) / 100, 0)
    const marginOnShelf = items.reduce(
      (sum, item) => sum + (item.marginPerUnit ?? 0) * (item.onShelf ?? 0),
      0,
    )

    result[name] = {
      positions: items.length,
      totalFacings: items.reduce((sum, item) => sum + item.facings, 0),
      usedMetres: round(usedMetres),
      marginOnShelf: round(marginOnShelf),
      marginPerMetre: usedMetres > 0 ? marginOnShelf / usedMetres : 0,
      // Null rather than zero: "nothing to compare against" is not "nothing
      // changed", and a dash on screen is honest where a 0 would not be.
      changedPositions: reference ? countChanges(plan, reference) : null,
    }
  }

  return result
}

function countChanges(plan, reference) {
  const before = facingsById(reference)
  const after = facingsById(plan)
  const ids = new Set([...before.keys(), ...after.keys()])

  let changed = 0
  for (const id of ids) {
    if (before.get(id) !== after.get(id)) changed += 1
  }
  return changed
}

function facingsById(plan) {
  const map = new Map()
  for (const shelf of plan?.shelves ?? []) {
    for (const item of shelf.items ?? []) map.set(item.productId, item.facings)
  }
  return map
}

function round(value) {
  return Math.round(value * 100) / 100
}
