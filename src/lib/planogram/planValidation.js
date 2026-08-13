/**
 * Independent validation of a finished plan.
 *
 * WHY THIS IS SEPARATE FROM THE ALLOCATOR
 *   `allocationEngine.js` enforces these constraints while it builds. This
 *   module re-checks them afterwards, from the placement data alone. That
 *   redundancy is the point: a plan the store is going to execute should be
 *   provably valid, not valid because the code that produced it believes it is.
 *   A hand edit, a future solver, or an imported plan all pass through here too.
 *
 * HARD VERSUS SOFT
 *   Hard violations mean the plan cannot be built — the packages do not fit, or
 *   a rule exists for safety reasons. They set `valid: false`. Soft findings are
 *   merchandising opinions and are reported as warnings without blocking.
 *   Conflating the two is how a safety rule ends up traded away for margin.
 */

export const RULE_SEVERITY = { hard: 'hard', soft: 'soft' }

/** Packages at or above this volume must sit on the bottom shelf. */
const HEAVY_LITRES = 2.5

/** Below this fill, a shelf is worth flagging as wasted space. */
const UNDERFILL_RATIO = 0.7

export function validatePlan(plan) {
  const shelves = plan?.shelves ?? []
  const violations = []
  const warnings = []
  let checkedPositions = 0

  for (const shelf of shelves) {
    const items = shelf.items ?? []
    checkedPositions += items.length

    // Width is recomputed from the placements rather than read from `usedCm`,
    // so a stale or wrong running total cannot hide an overflow.
    const requiredCm = items.reduce((sum, item) => sum + item.facings * item.widthCm, 0)
    if (requiredCm > shelf.runCm) {
      violations.push({
        rule: 'SHELF_WIDTH',
        severity: RULE_SEVERITY.hard,
        shelfCode: shelf.code,
        overflowCm: round(requiredCm - shelf.runCm),
        message: `${shelf.code}: الوجهات تتجاوز طول الرف بـ${round(requiredCm - shelf.runCm)} سم`,
      })
    }

    for (const item of items) {
      if (Number.isFinite(item.heightCm) && item.heightCm > shelf.clearanceCm) {
        violations.push({
          rule: 'SHELF_CLEARANCE',
          severity: RULE_SEVERITY.hard,
          shelfCode: shelf.code,
          productId: item.productId,
          message: `${item.productName}: ارتفاع ${item.heightCm} سم لا يدخل في مسافة ${shelf.clearanceCm} سم`,
        })
      }

      if (Number.isFinite(item.litres) && item.litres >= HEAVY_LITRES && shelf.shelfLevel !== 'BOTTOM') {
        violations.push({
          rule: 'HEAVY_GOODS_LOW',
          severity: RULE_SEVERITY.hard,
          shelfCode: shelf.code,
          productId: item.productId,
          message: `${item.productName}: عبوة ثقيلة (${item.litres} لتر) في ${shelf.levelLabel ?? shelf.shelfLevel}`,
        })
      }
    }

    const fill = shelf.runCm > 0 ? requiredCm / shelf.runCm : 1
    if (items.length && fill < UNDERFILL_RATIO) {
      warnings.push({
        rule: 'EMPTY_SPACE',
        severity: RULE_SEVERITY.soft,
        shelfCode: shelf.code,
        freeCm: round(shelf.runCm - requiredCm),
        message: `${shelf.code}: ${round(shelf.runCm - requiredCm)} سم غير مستغلة`,
      })
    }
  }

  return {
    valid: violations.length === 0,
    violations,
    warnings,
    checkedShelves: shelves.length,
    checkedPositions,
  }
}

function round(value) {
  return Math.round(value * 100) / 100
}
