import { beforeEach, describe, expect, it } from 'vitest'
import {
  ANSWER_STATUS, OUTCOME_REASONS, OUTCOME_STATUS, STORAGE_KEY,
  loadOwnerState, recordAnswer, recordOutcome, resetCacheForTests,
} from '../ownerState'

const LEGACY_ACTIONS = 'smartshelf.operationalActions.v1'
const LEGACY_ANSWERS = 'smartshelf.ownerAnswers.v1'
const LEGACY_DEMO = 'smartshelf.demoState.v1'

const entry = (over = {}) => ({
  id: 'a1b2c3d4e5f60718',
  signal_family: 'price.inverted',
  capability: 'price_consistency',
  barcode: '7290000041445',
  characterisation: 'confirmed_loss',
  value: { amount: 16, kind: 'per_sale', certainty: 'confirmed' },
  ...over,
})

// The suite runs in the node environment (vitest.config.js): a test that needs storage
// supplies it, the same stub completionActions.test.js uses.
function createStorage({ failOnWrite = false } = {}) {
  const backing = new Map()
  return {
    getItem: (key) => (backing.has(key) ? backing.get(key) : null),
    setItem: (key, value) => {
      if (failOnWrite) throw new Error('QuotaExceededError')
      backing.set(key, value)
    },
    removeItem: (key) => backing.delete(key),
  }
}

beforeEach(() => {
  globalThis.localStorage = createStorage()
  resetCacheForTests()
})

describe('migrations', () => {
  it('maps the legacy action enums and survives a second load without doubling', () => {
    globalThis.localStorage.setItem(LEGACY_ACTIONS, JSON.stringify({
      old1: { status: 'DONE', at: 1 },
      old2: { status: 'DISMISSED', at: 2, reason: 'wrong_data' },
      old3: { status: 'SNOOZED', at: 3, snoozeUntil: 99 },
    }))
    const first = loadOwnerState()
    expect(first.outcomes.old1.status).toBe('acted')
    expect(first.outcomes.old2.status).toBe('declined')
    expect(first.outcomes.old3.status).toBe('deferred')
    expect(first.outcomes.old3.deferred_until).toBe(99)

    resetCacheForTests()
    const second = loadOwnerState()
    expect(Object.keys(second.outcomes)).toHaveLength(3)
  })

  it('records a migrated outcome with signal_family null, present and not guessed', () => {
    globalThis.localStorage.setItem(LEGACY_ACTIONS, JSON.stringify({ old1: { status: 'DONE', at: 1 } }))
    const snapshot = loadOwnerState().outcomes.old1.snapshot
    expect('signal_family' in snapshot).toBe(true)
    expect(snapshot.signal_family).toBeNull()
  })

  it('carries the legacy answers across', () => {
    globalThis.localStorage.setItem(LEGACY_ANSWERS, JSON.stringify({ carried: { '123': 4.5 } }))
    expect(loadOwnerState().answers['123'].cost_price.value).toBe(4.5)
  })

  it('carries the demo recommendation decisions across', () => {
    globalThis.localStorage.setItem(LEGACY_DEMO, JSON.stringify({
      recommendationDecisions: { rec9: { status: 'DONE', at: 7 } },
    }))
    expect(loadOwnerState().outcomes.rec9.status).toBe('acted')
  })

  it('leaves the legacy keys in place, unread but not destroyed', () => {
    globalThis.localStorage.setItem(LEGACY_ACTIONS, JSON.stringify({ old1: { status: 'DONE', at: 1 } }))
    loadOwnerState()
    expect(globalThis.localStorage.getItem(LEGACY_ACTIONS)).not.toBeNull()
  })

  it('does not re-run once v2 exists', () => {
    globalThis.localStorage.setItem(STORAGE_KEY, JSON.stringify({ meta: { schema: 2 }, outcomes: {}, answers: {}, revivals: {} }))
    globalThis.localStorage.setItem(LEGACY_ACTIONS, JSON.stringify({ old1: { status: 'DONE', at: 1 } }))
    expect(loadOwnerState().outcomes).toEqual({})
  })
})

describe('recordOutcome', () => {
  it('writes the snapshot with the signal family (ADR-016)', async () => {
    await recordOutcome(entry(), { status: OUTCOME_STATUS.ACTED })
    const stored = loadOwnerState().outcomes['a1b2c3d4e5f60718']
    expect(stored.snapshot.signal_family).toBe('price.inverted')
    expect(stored.snapshot.capability).toBe('price_consistency')
    // design §10.3: value and kind are flat fields on the snapshot, not a nested object
    expect(stored.snapshot.value).toBe(16)
    expect(stored.snapshot.kind).toBe('per_sale')
    // D-10: a total that cannot separate confirmed from estimated recovery is not
    // defensible. Costs nothing while every entry is confirmed; unrecoverable afterwards.
    expect(stored.snapshot.certainty).toBe('confirmed')
  })

  it('refuses an entry with no signal family', async () => {
    await expect(recordOutcome(entry({ signal_family: undefined }), { status: OUTCOME_STATUS.ACTED }))
      .rejects.toThrow(/signal_family/)
  })

  it('refuses a status outside the enum', async () => {
    await expect(recordOutcome(entry(), { status: 'SNOOZED' })).rejects.toThrow(/status/)
  })

  it('refuses a reason outside the enum', async () => {
    await expect(recordOutcome(entry(), { status: OUTCOME_STATUS.DECLINED, reason: 'meh' }))
      .rejects.toThrow(/reason/)
  })

  it('accepts every reason in the enum', async () => {
    for (const reason of Object.values(OUTCOME_REASONS)) {
      await recordOutcome(entry(), { status: OUTCOME_STATUS.DECLINED, reason })
    }
    expect(loadOwnerState().outcomes['a1b2c3d4e5f60718'].reason).toBe('already_handled')
  })

  it('leaves the outcome unrecorded when the cache write fails, and says so', async () => {
    globalThis.localStorage = createStorage({ failOnWrite: true })
    resetCacheForTests()
    await expect(recordOutcome(entry(), { status: OUTCOME_STATUS.ACTED })).rejects.toThrow()
    // and nothing was persisted: a fresh reader sees no outcome
    globalThis.localStorage = createStorage()
    resetCacheForTests()
    expect(loadOwnerState().outcomes['a1b2c3d4e5f60718']).toBeUndefined()
  })
})

describe('recordAnswer', () => {
  it('stores a cost answer the engine can read back', async () => {
    await recordAnswer('7290000041445', { value: 4.5, status: ANSWER_STATUS.ANSWERED })
    expect(loadOwnerState().answers['7290000041445'].cost_price.value).toBe(4.5)
  })

  it('refuses a non-positive cost rather than storing a number nobody can use', async () => {
    await expect(recordAnswer('7290000041445', { value: 0, status: ANSWER_STATUS.ANSWERED }))
      .rejects.toThrow(/value/)
  })
})
