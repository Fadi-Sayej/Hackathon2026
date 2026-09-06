import { localStorageAdapter } from './localStorageAdapter.js'

const persistence = localStorageAdapter

export function saveApprovedOrder(order) {
  return persistence.saveApprovedOrder(order)
}

export function listApprovedOrders() {
  return persistence.listApprovedOrders()
}

export function saveRecommendationDecision(decision) {
  return persistence.saveRecommendationDecision(decision)
}

export function loadRecommendationDecisions() {
  return persistence.loadRecommendationDecisions()
}

export function loadStoreProducts(storeId) {
  return persistence.loadStoreProducts(storeId)
}

export function resetDemoState() {
  return persistence.resetDemoState()
}
