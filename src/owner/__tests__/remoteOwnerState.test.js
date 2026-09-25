import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { FIRESTORE_SCHEMA, pushAll, resetPushForTests, setRemoteLoaderForTests, writeThrough } from '../remoteOwnerState'
import {
  ANSWER_STATUS, OUTCOME_STATUS, STORAGE_KEY, loadOwnerState, recordAnswer, recordOutcome, resetCacheForTests,
} from '../ownerState'
import { createFakeFirestore } from './fakeFirestore'
import { setAuthModeForTests } from '../../auth/mode.js'
import { setCurrentRole } from '../../auth/current.js'

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

describe('the device register rides this path (ADR-021)', () => {
  it('registers a profile that opened the app and recorded nothing', async () => {
    // The case Task 4.3's precondition is actually about. Stamping outcomes with a device
    // was the rejected alternative precisely because a profile that opened the app and did
    // nothing produces no outcome to stamp — so the register must not wait for one.
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    loadOwnerState()
    await settle()
    const devices = fake.doc('devices')
    expect(Object.keys(devices)).toHaveLength(1)
    expect(fake.doc('outcomes')).toBeUndefined()
  })

  it('writes device_id, first_seen_at and last_seen_at, and nothing else', async () => {
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    loadOwnerState()
    await settle()
    const record = Object.values(fake.doc('devices'))[0]
    expect(Object.keys(record).sort()).toEqual(['device_id', 'first_seen_at', 'last_seen_at'])
    expect(Object.keys(fake.doc('devices'))[0]).toBe(record.device_id)
  })

  it('stays one profile across a session, and moves last_seen_at forward', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(Date.UTC(2026, 8, 13, 9, 0, 0))
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    loadOwnerState()
    await settle()
    const first = Object.values(fake.doc('devices'))[0]

    vi.setSystemTime(Date.UTC(2026, 8, 13, 17, 30, 0))
    await recordOutcome(entry(), { status: OUTCOME_STATUS.ACTED })
    await settle()
    const after = fake.doc('devices')
    expect(Object.keys(after)).toHaveLength(1)
    expect(Object.values(after)[0].first_seen_at).toBe(first.first_seen_at)
    expect(Object.values(after)[0].last_seen_at).toBe(Date.UTC(2026, 8, 13, 17, 30, 0))
  })

  it('a second profile is a second field, not a replacement', async () => {
    // mergeFields names one device id, so two browsers writing the same document must both
    // survive. A deep merge or a whole-document set would leave a count of one for ever.
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    loadOwnerState()
    await settle()
    globalThis.localStorage = createStorage()   // a second browser profile, same store
    resetCacheForTests()
    resetPushForTests()
    loadOwnerState()
    await settle()
    expect(Object.keys(fake.doc('devices'))).toHaveLength(2)
  })

  it('a profile that cannot keep an id is not registered, and the rest still writes', async () => {
    const readonly = createStorage()
    const backing = { ...readonly, setItem: (k, v) => { if (k === 'smartshelf.device.v1') throw new Error('nope'); readonly.setItem(k, v) } }
    globalThis.localStorage = backing
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    await recordAnswer('7290000041445', { value: 7.5, status: ANSWER_STATUS.ANSWERED })
    await settle()
    expect(fake.doc('devices')).toBeUndefined()
    expect(fake.doc('answers')['7290000041445'].cost_price.value).toBe(7.5)
  })
})

describe('ADR-029: only the owner writes owner state', () => {
  afterEach(() => { setAuthModeForTests(null); setCurrentRole(null) })

  it('sends nothing for a team account, and says why', async () => {
    setAuthModeForTests('firebase')
    setCurrentRole('team')
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    expect(await writeThrough('outcomes', 'e1', { status: 'acted', at: 1 })).toEqual({ written: false, reason: 'read_only' })
    expect(await pushAll({ outcomes: { e1: { status: 'acted', at: 1 } } })).toEqual({ written: false, reason: 'read_only' })
    expect(fake.calls).toHaveLength(0)
  })

  it('sends nothing for an account with no role', async () => {
    setAuthModeForTests('firebase')
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    expect(await writeThrough('outcomes', 'e1', { status: 'acted', at: 1 })).toEqual({ written: false, reason: 'read_only' })
    expect(fake.calls).toHaveLength(0)
  })

  it('writes for the owner, as before', async () => {
    setAuthModeForTests('firebase')
    setCurrentRole('owner')
    const fake = createFakeFirestore()
    setRemoteLoaderForTests(fake.loader)
    expect(await writeThrough('outcomes', 'e1', { status: 'acted', at: 5 })).toEqual({ written: true })
    expect(fake.doc('outcomes')).toEqual({ e1: { status: 'acted', at: 5 } })
  })
})
