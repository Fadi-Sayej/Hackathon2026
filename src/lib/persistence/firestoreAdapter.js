// Firestore-backed persistence for the pilot.
//
// Why it looks the way it does: the persistence interface is SYNCHRONOUS and
// App.jsx reads it at mount and uses the return values inline. Firestore is
// async. So this adapter is local-first:
//
//   • Reads are served synchronously from the localStorage mirror — instant,
//     and correct even offline or before the network responds.
//   • Writes go write-through to localStorage synchronously (returning exactly
//     what the local adapter returns, so callers are unchanged) and are then
//     mirrored to Firestore in the background.
//   • On load and on every reconnect it hydrates from Firestore and reconciles
//     both ways (last-write-wins by updatedAt), which also performs the
//     first-load migration of anything already sitting in localStorage.
//
// The manager never loses a decision: it is durable in localStorage the instant
// they act, and Firestore's own offline cache queues the mirror write and
// flushes it on reconnect. A Firestore hiccup only ever delays the cloud copy —
// it can never lose the local one, and it never throws to the caller.

import {
  collection,
  doc,
  getDocs,
  setDoc,
  deleteDoc,
  writeBatch,
} from 'firebase/firestore'

import {
  getDb,
  isFirebaseConfigured,
  ensureAnonymousAuth,
  STORE_ID,
} from '../../firebase.js'
import {
  localStorageAdapter,
  mergeRemoteState,
  localRecordsNewerThan,
} from './localStorageAdapter.js'

const ORDERS = 'approvedOrders'
const DECISIONS = 'recommendationDecisions'

// Firestore doc ids cannot contain "/" and a few other characters; the real id
// always lives in the record's own `id` field, so the doc id is just a key.
function docId(id) {
  return encodeURIComponent(String(id))
}

function colRef(db, name) {
  return collection(db, 'stores', STORE_ID, name)
}

function docRef(db, name, id) {
  return doc(db, 'stores', STORE_ID, name, docId(id))
}

function reportSyncError(error) {
  if (typeof console !== 'undefined') {
    console.warn(
      'SmartShelf Firestore sync issue (your data is safe in localStorage).',
      error,
    )
  }
}

// ── Background mirroring (fire-and-forget; offline-safe via Firestore cache) ──

function mirror(name, record) {
  const db = getDb()
  if (!db || !record || record.id == null) return
  setDoc(docRef(db, name, record.id), record, { merge: true }).catch(reportSyncError)
}

function removeRemote(name, id) {
  const db = getDb()
  if (!db || id == null) return
  deleteDoc(docRef(db, name, id)).catch(reportSyncError)
}

function pushRecords(records) {
  for (const order of records.approvedOrders) mirror(ORDERS, order)
  for (const decision of Object.values(records.recommendationDecisions)) {
    mirror(DECISIONS, decision)
  }
}

// ── Change notification (optional; lets a subscribed UI refresh after sync) ──

const listeners = new Set()

export function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function notify() {
  for (const listener of listeners) {
    try {
      listener()
    } catch (err) {
      reportSyncError(err)
    }
  }
  if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
    window.dispatchEvent(new CustomEvent('smartshelf:persistence-updated'))
  }
}

// ── Hydration + two-way reconciliation ───────────────────────────────────────

async function hydrateAndReconcile() {
  const db = getDb()
  if (!db) return

  try {
    const [ordersSnap, decisionsSnap] = await Promise.all([
      getDocs(colRef(db, ORDERS)),
      getDocs(colRef(db, DECISIONS)),
    ])

    const remote = {
      approvedOrders: ordersSnap.docs.map((d) => d.data()),
      recommendationDecisions: Object.fromEntries(
        decisionsSnap.docs.map((d) => {
          const data = d.data()
          return [data.id, data]
        }),
      ),
      storeProducts: {},
    }

    // Compute what is newer locally BEFORE merging remote in (this is also the
    // first-load migration: when remote is empty, everything local is pushed).
    const toPush = localRecordsNewerThan(remote)
    // Pull remote-newer records into the local mirror.
    mergeRemoteState(remote)
    // Push local-newer records up.
    pushRecords(toPush)

    notify()
  } catch (error) {
    reportSyncError(error)
  }
}

async function clearRemote() {
  const db = getDb()
  if (!db) return
  try {
    const [ordersSnap, decisionsSnap] = await Promise.all([
      getDocs(colRef(db, ORDERS)),
      getDocs(colRef(db, DECISIONS)),
    ])
    const batch = writeBatch(db)
    ordersSnap.docs.forEach((d) => batch.delete(d.ref))
    decisionsSnap.docs.forEach((d) => batch.delete(d.ref))
    await batch.commit()
  } catch (error) {
    reportSyncError(error)
  }
}

// ── Public interface: the same six synchronous methods, unchanged signatures ──

function saveApprovedOrder(order) {
  const saved = localStorageAdapter.saveApprovedOrder(order)
  mirror(ORDERS, saved)
  return saved
}

function listApprovedOrders() {
  return localStorageAdapter.listApprovedOrders()
}

function saveRecommendationDecision(decision) {
  const saved = localStorageAdapter.saveRecommendationDecision(decision)
  mirror(DECISIONS, saved)
  // Mirror the local adapter's side effect: rejecting a recommendation removes
  // its approved order.
  if (decision.status === 'REJECTED') removeRemote(ORDERS, decision.id)
  return saved
}

function loadRecommendationDecisions() {
  return localStorageAdapter.loadRecommendationDecisions()
}

function loadStoreProducts(storeId) {
  return localStorageAdapter.loadStoreProducts(storeId)
}

function resetDemoState() {
  localStorageAdapter.resetDemoState()
  clearRemote()
}

export const firestoreAdapter = {
  listApprovedOrders,
  loadRecommendationDecisions,
  loadStoreProducts,
  resetDemoState,
  saveApprovedOrder,
  saveRecommendationDecision,
  // Extra, non-breaking: lets callers opt into a refresh after cloud sync.
  subscribe,
  hydrate: hydrateAndReconcile,
}

// Kick off the first hydration and reconnect handling — but only when Firebase
// is actually configured, so importing this module is a harmless no-op
// otherwise.
let started = false
export function startSync() {
  if (started || !isFirebaseConfigured()) return
  started = true
  // Sign in (anonymously) first, then hydrate — the rules require an auth token.
  ensureAnonymousAuth().then(() => hydrateAndReconcile())
  if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
    window.addEventListener('online', () => {
      ensureAnonymousAuth().then(() => hydrateAndReconcile())
    })
  }
}

startSync()
