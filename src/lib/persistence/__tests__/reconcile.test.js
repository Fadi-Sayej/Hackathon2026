import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  localStorageAdapter,
  mergeStates,
  localRecordsNewerThan,
} from '../localStorageAdapter.js'

// Minimal in-memory localStorage so we can seed the mirror in the node test env.
function installFakeLocalStorage() {
  const store = new Map()
  globalThis.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
    clear: () => store.clear(),
  }
}

// These pin the last-write-wins reconciliation that keeps the localStorage
// mirror and Firestore consistent (nagham.md B-2). A lost or clobbered decision
// is exactly what would end the pilot, so the merge rules are pinned here. The
// helpers are pure over plain state objects, so no localStorage/Firestore is
// needed.

const order = (id, updatedAt, extra = {}) => ({ id, updatedAt, ...extra })
const decision = (id, updatedAt, extra = {}) => ({ id, updatedAt, status: 'APPROVED', ...extra })

describe('mergeStates — last write wins', () => {
  it('keeps the newer of two versions of the same order', () => {
    const local = { approvedOrders: [order('a', '2026-08-07T10:00:00.000Z', { qty: 1 })] }
    const remote = { approvedOrders: [order('a', '2026-08-07T12:00:00.000Z', { qty: 9 })] }

    const merged = mergeStates(local, remote)

    expect(merged.approvedOrders).toHaveLength(1)
    expect(merged.approvedOrders[0].qty).toBe(9)
  })

  it('does not let an older remote clobber a newer local record', () => {
    const local = { approvedOrders: [order('a', '2026-08-07T12:00:00.000Z', { qty: 9 })] }
    const remote = { approvedOrders: [order('a', '2026-08-07T10:00:00.000Z', { qty: 1 })] }

    const merged = mergeStates(local, remote)

    expect(merged.approvedOrders[0].qty).toBe(9)
  })

  it('unions records that exist on only one side', () => {
    const local = {
      approvedOrders: [order('a', '2026-08-07T10:00:00.000Z')],
      recommendationDecisions: { d1: decision('d1', '2026-08-07T10:00:00.000Z') },
    }
    const remote = {
      approvedOrders: [order('b', '2026-08-07T11:00:00.000Z')],
      recommendationDecisions: { d2: decision('d2', '2026-08-07T11:00:00.000Z') },
    }

    const merged = mergeStates(local, remote)

    expect(merged.approvedOrders.map((o) => o.id).sort()).toEqual(['a', 'b'])
    expect(Object.keys(merged.recommendationDecisions).sort()).toEqual(['d1', 'd2'])
  })

  it('merges recommendation decisions by id with last-write-wins', () => {
    const local = { recommendationDecisions: { d1: decision('d1', '2026-08-07T10:00:00.000Z', { status: 'APPROVED' }) } }
    const remote = { recommendationDecisions: { d1: decision('d1', '2026-08-07T13:00:00.000Z', { status: 'REJECTED' }) } }

    const merged = mergeStates(local, remote)

    expect(merged.recommendationDecisions.d1.status).toBe('REJECTED')
  })

  it('tolerates missing/empty shapes without throwing', () => {
    expect(mergeStates(undefined, undefined)).toEqual({
      approvedOrders: [],
      recommendationDecisions: {},
      storeProducts: {},
    })
  })
})

describe('localRecordsNewerThan — what to push to the cloud', () => {
  beforeEach(() => {
    installFakeLocalStorage()
  })

  afterEach(() => {
    delete globalThis.localStorage
  })

  it('with an empty remote, treats everything local as new (first-load migration)', () => {
    localStorageAdapter.saveApprovedOrder({ id: 'a', qty: 3 })
    localStorageAdapter.saveRecommendationDecision({ id: 'd1', status: 'APPROVED' })

    const toPush = localRecordsNewerThan({ approvedOrders: [], recommendationDecisions: {} })

    expect(toPush.approvedOrders.map((o) => o.id)).toEqual(['a'])
    expect(Object.keys(toPush.recommendationDecisions)).toEqual(['d1'])
  })

  it('does not re-push a local record the cloud already has a newer copy of', () => {
    const saved = localStorageAdapter.saveApprovedOrder({ id: 'a', qty: 3 })
    // Remote copy stamped one second later than the local one.
    const later = new Date(Date.parse(saved.updatedAt) + 1000).toISOString()

    const toPush = localRecordsNewerThan({
      approvedOrders: [{ id: 'a', qty: 3, updatedAt: later }],
      recommendationDecisions: {},
    })

    expect(toPush.approvedOrders).toHaveLength(0)
  })
})
