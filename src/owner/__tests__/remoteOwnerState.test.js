import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { FIRESTORE_SCHEMA, pushAll, resetPushForTests, setRemoteLoaderForTests, writeThrough } from '../remoteOwnerState'
import {
  ANSWER_STATUS, OUTCOME_STATUS, STORAGE_KEY, loadOwnerState, recordAnswer, recordOutcome, resetCacheForTests,
} from '../ownerState'
import { createFakeFirestore } from './fakeFirestore'

// #94. Owner state was written to localStorage and nowhere else, while the engine reads it
// only from Firestore. Every test below crosses the seam that was never crossed: what the
// browser WRITES, not what it keeps.

function createStorage() {
  const backing = new Map()
  return {
    getItem: (k) => (backing.has(k) ? backing.get(k) : null),
    setItem: (k, v) => { backing.set(k, v) },
    removeItem: (k) => { backing.delete(k) },
    clear: () => backing.clear(),
  }
}

const entry = (over = {}) => ({
  id: 'a1b2c3d4e5f60718', signal_family: 'price.inverted', capability: 'price_consistency',
  barcode: '7290000041445', characterisation: 'confirmed_loss',
  value: { amount: 16, kind: 'per_sale', certainty: 'confirmed' }, ...over,
})

/** recordOutcome/recordAnswer fire the write-through without awaiting it (§9.3: the UI commits
 *  on the local write alone). Let those queued promises settle before asserting. */
const settle = () => new Promise((r) => setTimeout(r, 0))

beforeEach(() => {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
  resetPushForTests()
})
afterEach(() => { vi.useRealTimers() })

describe('the Firestore document contract (design §10.3, §11.5)', () => {
  it('writes meta.schema as 1 — the number src/owner_state/model.py accepts', () => {
    // The browser's local state said schema 2 (the storage KEY is v2). pull.py rejects any
    // schema but 1 as `unavailable: owner_state_schema`, so writing 2 would have turned the
    // fix into a different outage the moment it worked.
    expect(FIRESTORE_SCHEMA).toBe(1)
  })
})

describe('writeThrough', () => {
  it('is a no-op, and says so, when Firebase is not configured', async () => {
    const fake = createFakeFirestore({ configured: false })
    setRemoteLoaderForTests(fake.loader)
    expect(await writeThrough('outcomes', 'e1', { status: 'acted', at: 1 })).toEqual({ written: false, reason: 'unconfigured' })
    expect(fake.calls).toHaveLength(0)
  })

  it('is a no-op, and says so, when anonymous sign-in fails', async () => {
    const fake = createFakeFirestore({ user: null })
    setRemoteLoaderForTests(fake.loader)
    expect(await writeThrough('outcomes', 'e1', { status: 'acted', at: 1 })).toEqual({ written: false, reason: 'no_auth' })
    expect(fake.calls).toHaveLength(0)
  })

  it('writes the record into stores/{store}/ownerState/{doc}, and stamps meta', async () => {
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    const rec = { status: 'acted', at: 5 }
    expect(await writeThrough('outcomes', 'e1', rec, { now: () => 99 })).toEqual({ written: true })
    expect(fake.doc('outcomes')).toEqual({ e1: rec })
    expect(fake.doc('meta')).toEqual({ schema: 1, updated_at: 99 })
  })

  it('replaces a record whole, so a stale nested field cannot survive remotely', async () => {
    // deferred -> acted: localStorage replaces the record and drops deferred_until. A deep
    // merge would keep it in Firestore, and the two copies would disagree with no error.
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    await writeThrough('outcomes', 'e1', { status: 'deferred', at: 1, deferred_until: 500 })
    await writeThrough('outcomes', 'e1', { status: 'acted', at: 2 })
    expect(fake.doc('outcomes')).toEqual({ e1: { status: 'acted', at: 2 } })
  })

  it('leaves every other record in the document untouched', async () => {
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    await writeThrough('outcomes', 'e1', { status: 'acted', at: 1 })
    await writeThrough('outcomes', 'e2', { status: 'declined', at: 2 })
    expect(Object.keys(fake.doc('outcomes')).sort()).toEqual(['e1', 'e2'])
  })

  it('never throws: a failed remote write is reported, not propagated', async () => {
    const fake = createFakeFirestore({ failWrites: true })
    setRemoteLoaderForTests(fake.loader)
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(await writeThrough('outcomes', 'e1', { status: 'acted', at: 1 })).toEqual({ written: false, reason: 'error' })
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })
})

describe('recordOutcome and recordAnswer write through (§9.3, §9.4)', () => {
  it('recordOutcome reaches Firestore — the write that #94 found missing', async () => {
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    await recordOutcome(entry(), { status: OUTCOME_STATUS.ACTED })
    await settle()
    const remote = fake.doc('outcomes')?.['a1b2c3d4e5f60718']
    expect(remote).toBeDefined()
    expect(remote.status).toBe('acted')
    expect(remote.snapshot.signal_family).toBe('price.inverted')
    // and it is the SAME record the device kept
    expect(remote).toEqual(loadOwnerState().outcomes['a1b2c3d4e5f60718'])
  })

  it('recordAnswer reaches Firestore, keyed by barcode', async () => {
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    await recordAnswer('7290000041445', { value: 7.5, status: ANSWER_STATUS.ANSWERED })
    await settle()
    expect(fake.doc('answers')?.['7290000041445']?.cost_price).toMatchObject({ value: 7.5, status: 'answered' })
  })

  it('a failed remote write does not unrecord the local outcome (cache-first, §9.3)', async () => {
    const fake = createFakeFirestore({ failWrites: true })
    setRemoteLoaderForTests(fake.loader)
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    await recordOutcome(entry(), { status: OUTCOME_STATUS.DECLINED, reason: 'not_worth_it' })
    await settle()
    expect(JSON.parse(globalThis.localStorage.getItem(STORAGE_KEY)).outcomes['a1b2c3d4e5f60718'].status).toBe('declined')
    warn.mockRestore()
  })
})

describe('pushAll — decisions recorded before write-through existed', () => {
  it('backfills every existing local record, so nothing recorded since the cut-over is lost', async () => {
    // The owner's phone already holds everything he did since 09-12, none of it ever sent.
    globalThis.localStorage.setItem(STORAGE_KEY, JSON.stringify({
      answers: { '111': { cost_price: { value: 3, at: 1, status: 'answered' } } },
      outcomes: { e1: { status: 'acted', at: 1 }, e2: { status: 'declined', at: 2 } },
      revivals: { '222': { at: 3, window_id: '2026-01..2026-07' } },
      meta: { schema: 2, updated_at: 3 },
    }))
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    // The production trigger, not a direct call: loading the state is what sends it. The
    // first draft of this test called pushAll() itself, which hit the once-per-session guard
    // that loadOwnerState() had already set, and asserted before the real send finished.
    loadOwnerState()
    await settle()
    expect(Object.keys(fake.doc('outcomes')).sort()).toEqual(['e1', 'e2'])
    expect(fake.doc('answers')['111'].cost_price.value).toBe(3)
    expect(fake.doc('revivals')['222'].window_id).toBe('2026-01..2026-07')
    expect(fake.doc('meta').schema).toBe(1)
    expect(typeof fake.doc('meta').updated_at).toBe('number')
  })

  it('runs once per session, however often the state is loaded', async () => {
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    const state = { answers: {}, outcomes: { e1: { status: 'acted', at: 1 } }, revivals: {}, meta: {} }
    await pushAll(state)
    const after = fake.calls.length
    await pushAll(state)
    expect(fake.calls.length).toBe(after)
  })
})
