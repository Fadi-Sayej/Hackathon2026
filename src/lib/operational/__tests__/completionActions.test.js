import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ACTIONS_STORAGE_KEY,
  ACTION_STATUS,
  DISMISS_REASON,
  DISMISS_REASON_LABEL,
  DISMISS_REASON_ORDER,
  DISMISS_REASON_VALUES,
  OUTCOME_LABEL,
  SNOOZE_OPTIONS,
  buildEntry,
  dismissReasonLabel,
  isDismissReason,
  isHandled,
  loadActions,
  mergeDecisions,
  normalizeEntry,
  normalizeStatus,
  persistActions,
  snoozeOptionById,
  toDecisionRecord,
} from '../completionActions.js'

function createStorage({ failOnWrite = false } = {}) {
  const backing = new Map()
  return {
    getItem: (key) => (backing.has(key) ? backing.get(key) : null),
    setItem: (key, value) => {
      if (failOnWrite) throw new Error('QuotaExceededError')
      backing.set(key, value)
    },
    removeItem: (key) => backing.delete(key),
    _backing: backing,
  }
}

beforeEach(() => {
  globalThis.localStorage = createStorage()
})

afterEach(() => {
  delete globalThis.localStorage
  vi.restoreAllMocks()
})

describe('dismissal reason enum', () => {
  it('exposes exactly the three pilot-graded reasons', () => {
    expect(DISMISS_REASON_VALUES).toEqual(['WRONG_DATA', 'NOT_WORTH_IT', 'ALREADY_HANDLED'])
  })

  it('gives every enum value a distinct label, and never stores the label', () => {
    const labels = DISMISS_REASON_VALUES.map((value) => DISMISS_REASON_LABEL[value])
    expect(new Set(labels).size).toBe(DISMISS_REASON_VALUES.length)
    for (const value of DISMISS_REASON_VALUES) {
      expect(DISMISS_REASON_LABEL[value]).not.toBe(value)
    }
  })

  it('renders every enum value in the picker order', () => {
    expect([...DISMISS_REASON_ORDER].sort()).toEqual([...DISMISS_REASON_VALUES].sort())
  })

  it.each(DISMISS_REASON_VALUES)('accepts %s as a valid reason', (value) => {
    expect(isDismissReason(value)).toBe(true)
    expect(dismissReasonLabel(value)).toBe(DISMISS_REASON_LABEL[value])
  })

  it.each([undefined, null, '', 'wrong_data', 'MADE_UP', 42, {}])(
    'rejects %p rather than mapping it to a valid reason',
    (value) => {
      expect(isDismissReason(value)).toBe(false)
      expect(dismissReasonLabel(value)).toBe('Reason not recorded')
      expect(DISMISS_REASON_VALUES).not.toContain(dismissReasonLabel(value))
    },
  )
})

describe('buildEntry', () => {
  it.each(DISMISS_REASON_VALUES)('stores the machine value for %s', (reason) => {
    const entry = buildEntry({ status: ACTION_STATUS.DISMISSED, reason, now: 1000 })
    expect(entry).toEqual({ status: 'DISMISSED', at: 1000, reason })
  })

  it('records a missing dismissal reason as null instead of defaulting', () => {
    const entry = buildEntry({ status: ACTION_STATUS.DISMISSED, now: 1000 })
    expect(entry.reason).toBeNull()
  })

  it('records an unknown dismissal reason as null instead of coercing', () => {
    const entry = buildEntry({ status: ACTION_STATUS.DISMISSED, reason: 'NOPE', now: 1000 })
    expect(entry.reason).toBeNull()
  })

  it('builds a done entry with no reason field', () => {
    expect(buildEntry({ status: ACTION_STATUS.DONE, now: 5 })).toEqual({ status: 'DONE', at: 5 })
  })

  it.each(SNOOZE_OPTIONS.map((o) => o.id))('builds a snooze entry for %s', (id) => {
    const option = snoozeOptionById(id)
    const entry = buildEntry({ status: ACTION_STATUS.SNOOZED, snoozeOptionId: id, now: 1000 })
    expect(entry).toEqual({
      status: 'SNOOZED',
      at: 1000,
      snoozeOptionId: id,
      snoozeUntil: 1000 + option.ms,
    })
  })

  it('refuses a snooze with an unknown duration', () => {
    expect(buildEntry({ status: ACTION_STATUS.SNOOZED, snoozeOptionId: '99y' })).toBeNull()
    expect(buildEntry({ status: ACTION_STATUS.SNOOZED })).toBeNull()
  })

  it.each([undefined, null, '', 'ARCHIVED', 7])('refuses status %p', (status) => {
    expect(buildEntry({ status })).toBeNull()
  })

  it('accepts legacy lowercase status but normalizes it on write', () => {
    expect(normalizeStatus('done')).toBe('DONE')
    expect(buildEntry({ status: 'dismissed', reason: DISMISS_REASON.WRONG_DATA, now: 1 }).status)
      .toBe('DISMISSED')
  })
})

describe('normalizeEntry', () => {
  it('drops a corrupt record rather than half-reading it', () => {
    expect(normalizeEntry(null)).toBeNull()
    expect(normalizeEntry('DONE')).toBeNull()
    expect(normalizeEntry({ status: 'ARCHIVED' })).toBeNull()
    expect(normalizeEntry({ status: 'SNOOZED' })).toBeNull() // no deadline
  })

  it('nulls an unrecognised stored reason instead of trusting it', () => {
    expect(normalizeEntry({ status: 'DISMISSED', reason: 'HACKED', at: 1 }).reason).toBeNull()
  })

  it('round-trips every valid dismissal reason', () => {
    for (const reason of DISMISS_REASON_VALUES) {
      expect(normalizeEntry({ status: 'DISMISSED', reason, at: 1 }).reason).toBe(reason)
    }
  })
})

describe('isHandled', () => {
  it('treats done and dismissed as terminal', () => {
    expect(isHandled({ status: 'DONE' }, 0)).toBe(true)
    expect(isHandled({ status: 'DISMISSED' }, 0)).toBe(true)
  })

  it('treats a live snooze as handled and an expired one as open again', () => {
    expect(isHandled({ status: 'SNOOZED', snoozeUntil: 100 }, 50)).toBe(true)
    expect(isHandled({ status: 'SNOOZED', snoozeUntil: 100 }, 150)).toBe(false)
  })

  it('treats missing or unknown entries as open', () => {
    expect(isHandled(undefined, 0)).toBe(false)
    expect(isHandled({ status: 'ARCHIVED' }, 0)).toBe(false)
  })
})

describe('persistence round-trip', () => {
  it('restores every dismissal reason after a reload', async () => {
    const stored = {}
    for (const [index, reason] of DISMISS_REASON_VALUES.entries()) {
      stored[`rec-${index}`] = buildEntry({ status: ACTION_STATUS.DISMISSED, reason, now: 1 })
    }
    await persistActions(stored)
    const reloaded = loadActions()
    for (const [index, reason] of DISMISS_REASON_VALUES.entries()) {
      expect(reloaded[`rec-${index}`].reason).toBe(reason)
    }
  })

  it('restores a snooze deadline after a reload', async () => {
    await persistActions({ a: buildEntry({ status: 'SNOOZED', snoozeOptionId: '4h', now: 1000 }) })
    expect(loadActions().a.snoozeUntil).toBe(1000 + snoozeOptionById('4h').ms)
  })

  it('discards corrupt JSON and corrupt individual records', () => {
    globalThis.localStorage.setItem(ACTIONS_STORAGE_KEY, '{not json')
    expect(loadActions()).toEqual({})

    globalThis.localStorage.setItem(
      ACTIONS_STORAGE_KEY,
      JSON.stringify({ good: { status: 'DONE', at: 1 }, bad: { status: 'ARCHIVED' } }),
    )
    const loaded = loadActions()
    expect(Object.keys(loaded)).toEqual(['good'])
  })

  it('rejects when the store fails, so the caller can roll back', async () => {
    globalThis.localStorage = createStorage({ failOnWrite: true })
    await expect(persistActions({ a: { status: 'DONE' } })).rejects.toThrow()
  })

  it('resolves without a store rather than throwing', async () => {
    delete globalThis.localStorage
    await expect(persistActions({ a: { status: 'DONE' } })).resolves.toBeTruthy()
    expect(loadActions()).toEqual({})
  })
})

describe('mergeDecisions', () => {
  it('seeds from App-level decisions when there is no local entry', () => {
    const merged = mergeDecisions({}, { r1: { status: 'DONE', at: 1 } })
    expect(merged.r1.status).toBe('DONE')
  })

  it('lets the newer local entry win', () => {
    const merged = mergeDecisions(
      { r1: { status: 'DISMISSED', reason: DISMISS_REASON.WRONG_DATA, at: 2 } },
      { r1: { status: 'DONE', at: 1 } },
    )
    expect(merged.r1.status).toBe('DISMISSED')
  })

  it('ignores unusable decision records', () => {
    expect(mergeDecisions({}, { r1: { status: 'ARCHIVED' } })).toEqual({})
    expect(mergeDecisions({}, null)).toEqual({})
  })
})

describe('toDecisionRecord', () => {
  it('carries the reason through to the onDecide payload', () => {
    const action = { id: 'a1', type: 'CHECK_MARGIN', productName: 'במבה', barcode: '729', impactIls: 4 }
    const entry = buildEntry({
      status: ACTION_STATUS.DISMISSED,
      reason: DISMISS_REASON.NOT_WORTH_IT,
      now: 1,
    })
    expect(toDecisionRecord(action, entry)).toEqual({
      id: 'a1',
      status: 'DISMISSED',
      reason: 'NOT_WORTH_IT',
      snoozeUntil: null,
      type: 'CHECK_MARGIN',
      productName: 'במבה',
      barcode: '729',
      impactIls: 4,
    })
  })

  it('reports a null reason for non-dismiss outcomes rather than omitting the field', () => {
    const record = toDecisionRecord({ id: 'a1' }, buildEntry({ status: 'DONE', now: 1 }))
    expect(record.reason).toBeNull()
  })
})

describe('outcome labels', () => {
  it.each(Object.values(ACTION_STATUS))('labels %s', (status) => {
    expect(OUTCOME_LABEL[status]).toBeTruthy()
  })
})
