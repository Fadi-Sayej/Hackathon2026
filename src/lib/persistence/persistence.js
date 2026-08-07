import { localStorageAdapter } from './localStorageAdapter.js'
import { firestoreAdapter } from './firestoreAdapter.js'
import { isFirebaseConfigured } from '../../firebase.js'

// One switch: if the browser Firebase config is present, decisions and orders
// are backed by Firestore (with a localStorage mirror underneath). If not, we
// stay on localStorage exactly as before. The six functions below have
// identical signatures either way, so callers never change.
const persistence = isFirebaseConfigured() ? firestoreAdapter : localStorageAdapter

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

// Optional, non-breaking: subscribe to be notified when a background cloud sync
// updates the local mirror (e.g. a decision made on another device, or offline
// writes reconciling on reconnect). Returns an unsubscribe function.
//
// Same-device persistence works fully without this. It exists so the UI can
// reflect cross-device / post-reconnect changes without a manual reload — wire
// it in App.jsx as, roughly:
//
//   useEffect(() => subscribeToPersistence(() => {
//     setActionDecisions(loadRecommendationDecisions())
//     setRecommendationOverrides(loadRecommendationDecisions())
//   }), [])
//
// (App.jsx is Track C — coordinate with Anas before adding that.)
export function subscribeToPersistence(listener) {
  if (typeof persistence.subscribe === 'function') {
    return persistence.subscribe(listener)
  }
  return () => {}
}
