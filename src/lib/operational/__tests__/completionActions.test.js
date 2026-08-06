import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  SNOOZE_OPTIONS,
  isHandled,
  loadActions,
  persistActions,
} from '../completionActions.js'

// Regression coverage for the OperationalPage completion actions (Issue #31):
// the Done / Snooze / Dismiss state machine and its localStorage persistence.

const NOW = 1_700_000_000_000

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('isHandled — completion-action state machine (#31)', () => {
  it('treats an unactioned item as active', () => {
    expect(isHandled(undefined, NOW)).toBe(false)
    expect(isHandled(null, NOW)).toBe(false)
  })

  it('marks done and dismissed items as handled', () => {
    expect(isHandled({ status: 'done' }, NOW)).toBe(true)
    expect(isHandled({ status: 'dismissed' }, NOW)).toBe(true)
  })

  it('keeps a snoozed item handled until its deadline passes', () => {
    const future = { status: 'snoozed', snoozeUntil: NOW + 60_000 }
    const past = { status: 'snoozed', snoozeUntil: NOW - 60_000 }
    expect(isHandled(future, NOW)).toBe(true)
    // An elapsed snooze returns the row to the active list.
    expect(isHandled(past, NOW)).toBe(false)
  })

  it('exposes three snooze durations in ascending order', () => {
    expect(SNOOZE_OPTIONS.map((option) => option.id)).toEqual(['4h', '24h', '1w'])
    const durations = SNOOZE_OPTIONS.map((option) => option.ms)
    expect(durations).toEqual([...durations].sort((a, b) => a - b))
    expect(durations.every((ms) => ms > 0)).toBe(true)
  })
})

describe('action persistence (#31)', () => {
  function stubStorage() {
    const store = new Map()
    vi.stubGlobal('localStorage', {
      getItem: (key) => (store.has(key) ? store.get(key) : null),
      setItem: (key, value) => store.set(key, String(value)),
      removeItem: (key) => store.delete(key),
    })
    return store
  }

  it('round-trips actions through localStorage so state survives reload', async () => {
    stubStorage()
    const state = { 'op-1': { status: 'done', at: NOW } }
    await persistActions(state)
    // A fresh load (as on the next mount) recovers the persisted decision.
    expect(loadActions()).toEqual(state)
  })

  it('rejects when the store write fails, letting the caller roll back', async () => {
    vi.stubGlobal('localStorage', {
      getItem: () => null,
      setItem: () => {
        throw new Error('QuotaExceededError')
      },
    })
    await expect(persistActions({ 'op-1': { status: 'done' } })).rejects.toThrow()
  })

  it('degrades to a no-op (and empty load) when storage is unavailable', async () => {
    // No localStorage global at all (e.g. SSR / private-mode edge cases).
    await expect(persistActions({ 'op-1': { status: 'done' } })).resolves.toBeTruthy()
    expect(loadActions()).toEqual({})
  })

  it('recovers gracefully from corrupt persisted JSON', () => {
    const store = stubStorage()
    store.set('smartshelf.operationalActions.v1', '{ not valid json')
    expect(loadActions()).toEqual({})
  })
})
