/**
 * Approved planogram versions, and the change cost of moving away from one.
 *
 * WHY A PLAN HAS TO BE FROZEN
 *   The allocator recomputes on every render. Without an approved version the
 *   plan a manager saw on Monday is not the plan they see on Tuesday, nobody can
 *   be asked to execute it, and no sales change can ever be attributed to it.
 *   Versioning is not a convenience feature here; it is what turns a
 *   recommendation into something a store can be held to.
 *
 * WHY CHANGE COST MATTERS MORE THAN IT LOOKS
 *   A plan that reorders 70% of a category for a 1% theoretical gain is a bad
 *   plan. The labour is real and immediate; the gain is modelled and uncertain.
 *   `planStability()` puts the work on screen — as a count and as a list of the
 *   actual moves — so that trade is made deliberately instead of by default.
 *
 * STORAGE
 *   Same reasoning as `layoutStorage.js`: standalone rather than a seventh
 *   method on the persistence adapters. The in-memory fallback keeps this
 *   working under Node (tests, any future SSR) instead of silently doing
 *   nothing.
 */

const STORAGE_KEY = 'smartshelf.planogram.approved.v1'

const memoryStore = new Map()

function storageAvailable() {
  try {
    return Boolean(globalThis.localStorage)
  } catch {
    return false
  }
}

function readAll() {
  // When localStorage works it is the ONLY source of truth. Falling back to the
  // in-memory copy while storage is available meant clearing browser storage did
  // not actually clear anything — stale approvals came back from memory.
  if (storageAvailable()) {
    try {
      const raw = globalThis.localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  }
  return Object.fromEntries(memoryStore)
}

function writeAll(all) {
  memoryStore.clear()
  for (const [key, value] of Object.entries(all)) memoryStore.set(key, value)
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify(all))
  } catch {
    // Memory copy above is the fallback.
  }
}

const keyFor = (fixtureId, category) => `${fixtureId}::${category}`

/**
 * Reduce a rendered plan to the decision it represents.
 *
 * Deliberately drops colours, shapes, tooltips and every other rendering
 * concern. What survives is what a different UI — or a printout, or a solver
 * warm start — would need. The optimiser produces structured placement; drawing
 * it is somebody else's job.
 */
export function toPlanVersion({ unit, category, plan }) {
  return {
    fixtureId: unit?.id ?? null,
    fixtureName: unit?.name ?? null,
    category,
    status: 'draft',
    createdAt: new Date().toISOString(),
    placements: (plan?.shelves ?? []).flatMap((shelf) =>
      (shelf.items ?? []).map((item) => ({
        shelfCode: shelf.code,
        shelfLevel: shelf.shelfLevel,
        productId: item.productId,
        facings: item.facings,
      })),
    ),
    summary: plan?.summary ?? null,
  }
}

/**
 * What it would cost to move from the approved plan to this one.
 *
 * A removal and an addition count separately, because they are two separate
 * trips to the shelf.
 */
export function planStability(plan, approved) {
  if (!approved) return { changedPositions: null, moves: [] }

  const before = new Map(approved.placements.map((entry) => [entry.productId, entry.facings]))
  const after = new Map()
  const names = new Map()
  for (const shelf of plan?.shelves ?? []) {
    for (const item of shelf.items ?? []) {
      after.set(item.productId, item.facings)
      names.set(item.productId, item.productName)
    }
  }

  const moves = []
  let changedPositions = 0

  for (const [productId, facings] of after) {
    if (!before.has(productId)) {
      changedPositions += 1
      moves.push({ productId, productName: names.get(productId), kind: 'added', from: 0, to: facings })
    } else if (before.get(productId) !== facings) {
      changedPositions += 1
      moves.push({
        productId,
        productName: names.get(productId),
        kind: 'facings',
        from: before.get(productId),
        to: facings,
      })
    }
  }

  for (const [productId, facings] of before) {
    if (!after.has(productId)) {
      changedPositions += 1
      moves.push({ productId, productName: null, kind: 'removed', from: facings, to: 0 })
    }
  }

  return { changedPositions, moves }
}

/** Freeze a version as the plan the store is expected to be building. */
export function approvePlan(version) {
  const approved = { ...version, status: 'approved', approvedAt: new Date().toISOString() }
  const all = readAll()
  all[keyFor(version.fixtureId, version.category)] = approved
  writeAll(all)
  return approved
}

/** The approved plan for one fixture and category, or null. */
export function loadApprovedPlan(fixtureId, category) {
  return readAll()[keyFor(fixtureId, category)] ?? null
}
