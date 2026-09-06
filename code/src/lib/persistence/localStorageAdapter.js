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
