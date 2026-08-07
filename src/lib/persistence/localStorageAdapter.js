const STORAGE_KEY = 'smartshelf.demoState.v1'

const emptyState = {
  approvedOrders: [],
  recommendationDecisions: {},
  storeProducts: {},
}

export const localStorageAdapter = {
  listApprovedOrders,
  loadRecommendationDecisions,
  loadStoreProducts,
  resetDemoState,
  saveApprovedOrder,
  saveRecommendationDecision,
}

export function saveApprovedOrder(order) {
  const state = readState()
  const existingIndex = state.approvedOrders.findIndex((item) => item.id === order.id)
  const nextOrder = {
    ...order,
    updatedAt: new Date().toISOString(),
  }

  if (existingIndex >= 0) {
    state.approvedOrders[existingIndex] = nextOrder
  } else {
    state.approvedOrders.push(nextOrder)
  }

  writeState(state)
  return nextOrder
}

export function listApprovedOrders() {
  return readState().approvedOrders
}

export function saveRecommendationDecision(decision) {
  const state = readState()
  state.recommendationDecisions[decision.id] = {
    ...decision,
    updatedAt: new Date().toISOString(),
  }

  if (decision.status === 'REJECTED') {
    state.approvedOrders = state.approvedOrders.filter((order) => order.id !== decision.id)
  }

  writeState(state)
  return state.recommendationDecisions[decision.id]
}

export function loadRecommendationDecisions() {
  return readState().recommendationDecisions
}

export function loadStoreProducts(storeId) {
  return readState().storeProducts[storeId] ?? null
}

export function resetDemoState() {
  if (!hasLocalStorage()) return
  try {
    globalThis.localStorage.removeItem(STORAGE_KEY)
  } catch (error) {
    if (typeof console !== 'undefined') {
      console.warn('SmartShelf persistence reset failed.', error)
    }
  }
}

function readState() {
  if (!hasLocalStorage()) return cloneState(emptyState)

  try {
    const raw = globalThis.localStorage.getItem(STORAGE_KEY)
    if (!raw) return cloneState(emptyState)
    const parsed = JSON.parse(raw)
    return {
      approvedOrders: Array.isArray(parsed.approvedOrders) ? parsed.approvedOrders : [],
      recommendationDecisions:
        parsed.recommendationDecisions && typeof parsed.recommendationDecisions === 'object'
          ? parsed.recommendationDecisions
          : {},
      storeProducts:
        parsed.storeProducts && typeof parsed.storeProducts === 'object'
          ? parsed.storeProducts
          : {},
    }
  } catch {
    return cloneState(emptyState)
  }
}

function writeState(state) {
  if (!hasLocalStorage()) return
  try {
    globalThis.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch (error) {
    if (typeof console !== 'undefined') {
      console.warn('SmartShelf persistence write failed; demo state will be in-memory only.', error)
    }
  }
}

function hasLocalStorage() {
  return typeof globalThis.localStorage !== 'undefined'
}

function cloneState(state) {
  return JSON.parse(JSON.stringify(state))
}

// ── Reconciliation helpers (used by firestoreAdapter) ────────────────────────
//
// These keep the local mirror and Firestore in sync using last-write-wins on
// each record's `updatedAt`. They are pure with respect to their inputs (they
// operate on plain state objects), so they are unit-testable in Node without a
// localStorage or Firestore. The two that touch storage (getRawState /
// mergeRemoteState) simply read and write the same STORAGE_KEY as everything
// else above.

function normalizeState(state) {
  const s = state && typeof state === 'object' ? state : {}
  return {
    approvedOrders: Array.isArray(s.approvedOrders) ? s.approvedOrders : [],
    recommendationDecisions:
      s.recommendationDecisions && typeof s.recommendationDecisions === 'object'
        ? s.recommendationDecisions
        : {},
    storeProducts:
      s.storeProducts && typeof s.storeProducts === 'object' ? s.storeProducts : {},
  }
}

function stamp(record) {
  return (record && record.updatedAt) || ''
}

// Returns true when `candidate` is strictly newer than `existing`. A record with
// no counterpart is always "newer" (it needs to be propagated).
function isNewer(candidate, existing) {
  if (!existing) return true
  return stamp(candidate) > stamp(existing)
}

function mergeArrayById(base, incoming) {
  const byId = new Map()
  for (const item of base) byId.set(item.id, item)
  for (const item of incoming) {
    const existing = byId.get(item.id)
    if (isNewer(item, existing)) byId.set(item.id, item)
  }
  return [...byId.values()]
}

function mergeMapByKey(base, incoming) {
  const merged = { ...base }
  for (const [key, value] of Object.entries(incoming)) {
    if (isNewer(value, merged[key])) merged[key] = value
  }
  return merged
}

// Pure last-write-wins merge of two state objects. Order does not matter for the
// outcome; the newer `updatedAt` always wins.
export function mergeStates(base, incoming) {
  const b = normalizeState(base)
  const i = normalizeState(incoming)
  return {
    approvedOrders: mergeArrayById(b.approvedOrders, i.approvedOrders),
    recommendationDecisions: mergeMapByKey(
      b.recommendationDecisions,
      i.recommendationDecisions,
    ),
    storeProducts: { ...b.storeProducts, ...i.storeProducts },
  }
}

// Given a remote snapshot, return only the LOCAL records that are newer than
// their remote counterpart — i.e. what needs to be pushed up. Drives both the
// first-load migration (remote empty ⇒ everything local is pushed) and ongoing
// reconciliation.
export function localRecordsNewerThan(remoteState) {
  const local = readState()
  const remote = normalizeState(remoteState)
  const remoteOrders = new Map(remote.approvedOrders.map((o) => [o.id, o]))

  const approvedOrders = local.approvedOrders.filter((order) =>
    isNewer(order, remoteOrders.get(order.id)),
  )
  const recommendationDecisions = {}
  for (const [id, decision] of Object.entries(local.recommendationDecisions)) {
    if (isNewer(decision, remote.recommendationDecisions[id])) {
      recommendationDecisions[id] = decision
    }
  }
  return { approvedOrders, recommendationDecisions }
}

// Read the raw local mirror (normalized clone). Safe when localStorage is absent.
export function getRawState() {
  return readState()
}

// Merge a remote snapshot into the local mirror (remote newer wins) and persist.
// Returns the merged state.
export function mergeRemoteState(remoteState) {
  const merged = mergeStates(readState(), remoteState)
  writeState(merged)
  return merged
}
