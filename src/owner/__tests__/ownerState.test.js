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
// supplies it.
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

// Phase 4 Task 4.3 (#78). The one-shot migration from these three keys was removed once the
// owner confirmed, on 2026-09-24, that every device had opened the app since the cut-over,
// so each already holds smartshelf.ownerState.v2. The keys are still there on those devices.
// Nothing reads them, and nothing may delete them: removing the migration is reversible,
// deleting a user's data is not.
describe('the pre-V1 keys (Task 4.3)', () => {
  const legacy = {
    [LEGACY_ACTIONS]: JSON.stringify({ old1: { status: 'DONE', at: 1 } }),
    [LEGACY_ANSWERS]: JSON.stringify({ carried: { '123': 4.5 } }),
    [LEGACY_DEMO]: JSON.stringify({ recommendationDecisions: { rec9: { status: 'DONE', at: 7 } } }),
  }

  it('are not read: a device holding only pre-V1 keys starts with an empty state', () => {
    for (const [key, value] of Object.entries(legacy)) globalThis.localStorage.setItem(key, value)
    const state = loadOwnerState()
    expect(state.outcomes).toEqual({})
    expect(state.answers).toEqual({})
  })

  it('are left in place and unchanged, unread but not destroyed', () => {
    for (const [key, value] of Object.entries(legacy)) globalThis.localStorage.setItem(key, value)
    loadOwnerState()
    for (const [key, value] of Object.entries(legacy)) {
      expect(globalThis.localStorage.getItem(key)).toBe(value)
    }
  })

  it('do not disturb a device that holds v2 state', () => {
    const v2 = {
      meta: { schema: 2 }, revivals: {}, answers: {},
      outcomes: { a1: { status: 'acted', at: 5, reason: null, snapshot: { signal_family: 'price.inverted' } } },
    }
    globalThis.localStorage.setItem(STORAGE_KEY, JSON.stringify(v2))
    for (const [key, value] of Object.entries(legacy)) globalThis.localStorage.setItem(key, value)
    expect(loadOwnerState().outcomes).toEqual(v2.outcomes)
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
    await recordAnswer('7290000041445', 'cost_price', { value: 4.5, status: ANSWER_STATUS.ANSWERED })
    expect(loadOwnerState().answers['7290000041445'].cost_price.value).toBe(4.5)
  })

  it('refuses a non-positive cost rather than storing a number nobody can use', async () => {
    await expect(recordAnswer('7290000041445', 'cost_price', { value: 0, status: ANSWER_STATUS.ANSWERED }))
      .rejects.toThrow(/value/)
  })
})

describe('#139 — the store refuses a deferral with no date', () => {
  const entry = { id: 'e1', signal_family: 'price.inverted', capability: 'price_consistency',
    barcode: 'b1', characterisation: 'confirmed_loss' }

  it('throws rather than recording a permanent dismissal', async () => {
    await expect(recordOutcome(entry, { status: OUTCOME_STATUS.DEFERRED }))
      .rejects.toThrow(/deferral needs deferredUntil/)
  })

  it('accepts one that carries a date', async () => {
    await recordOutcome(entry, { status: OUTCOME_STATUS.DEFERRED, deferredUntil: 1_800_000_000_000 })
    expect(loadOwnerState().outcomes.e1.deferred_until).toBe(1_800_000_000_000)
  })

  it('still accepts acted and declined, which carry no date', async () => {
    await recordOutcome({ ...entry, id: 'e2' }, { status: OUTCOME_STATUS.ACTED })
    expect(loadOwnerState().outcomes.e2.status).toBe('acted')
  })
})

describe('an order suggestion\'s outcome (ADR-034 Decision 2, FR-161)', () => {
  const suggestion = entry({ id: 'f1e2d3c4b5a69788', signal_family: 'order.suggestion', capability: 'order_quantity',
    characterisation: 'order_suggestion', value: null,
    evidence: { order_day: '2026-08-30', kind: 'net', quantity: 11 } })

  it('carries the order day, net or gross, and the quantity suggested, and no ₪ field', async () => {
    await recordOutcome(suggestion, { status: OUTCOME_STATUS.ACTED })
    const { snapshot } = loadOwnerState().outcomes[suggestion.id]
    expect(snapshot).toMatchObject({ signal_family: 'order.suggestion', order_day: '2026-08-30', kind: 'net',
      suggested_quantity: 11 })
    expect(snapshot).not.toHaveProperty('approved_quantity')
    expect(snapshot).not.toHaveProperty('value')
  })

  it('records his own quantity beside the suggested one (SCN-143)', async () => {
    await recordOutcome(suggestion, { status: OUTCOME_STATUS.ACTED, approvedQuantity: 20 })
    const { snapshot } = loadOwnerState().outcomes[suggestion.id]
    expect(snapshot.suggested_quantity).toBe(11)
    expect(snapshot.approved_quantity).toBe(20)
  })

  it('never records a quantity that is not a positive whole number', async () => {
    await recordOutcome(suggestion, { status: OUTCOME_STATUS.ACTED, approvedQuantity: -4 })
    expect(loadOwnerState().outcomes[suggestion.id].snapshot).not.toHaveProperty('approved_quantity')
  })

  it('leaves every other family\'s snapshot as it was', async () => {
    await recordOutcome(entry(), { status: OUTCOME_STATUS.ACTED, approvedQuantity: 20 })
    const { snapshot } = loadOwnerState().outcomes[entry().id]
    expect(snapshot).not.toHaveProperty('order_day')
    expect(snapshot).not.toHaveProperty('approved_quantity')
  })
})

describe('answers are stored per fact (Phase 5 Task 5.14, ADR-034 Decision 3)', () => {
  const B = '7290000041445'

  it('a disagreement answer never erases a cost answer, and the reverse', async () => {
    await recordAnswer(B, 'cost_price', { value: 4.5, status: ANSWER_STATUS.ANSWERED })
    await recordAnswer(B, 'market_disagreement', { value: 'weak_market', status: ANSWER_STATUS.ANSWERED })
    expect(loadOwnerState().answers[B]).toMatchObject({
      cost_price: { value: 4.5, status: 'answered' },
      market_disagreement: { value: 'weak_market', status: 'answered' },
    })
    await recordAnswer(B, 'cost_price', { value: 5.2, status: ANSWER_STATUS.ANSWERED })
    expect(loadOwnerState().answers[B].market_disagreement.value).toBe('weak_market')
    expect(loadOwnerState().answers[B].cost_price.value).toBe(5.2)
  })

  it('refuses a disagreement answer outside the four it offers', async () => {
    await expect(recordAnswer(B, 'market_disagreement', { value: 'dunno', status: ANSWER_STATUS.ANSWERED }))
      .rejects.toThrow(/market_disagreement/)
  })

  it('refuses a fact nobody asks', async () => {
    await expect(recordAnswer(B, 'shelf_colour', { value: 'red' })).rejects.toThrow(/fact/)
  })
})
