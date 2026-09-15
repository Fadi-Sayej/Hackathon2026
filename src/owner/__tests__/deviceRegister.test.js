import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DEVICE_KEY, deviceField, localDevice } from '../deviceRegister'

/**
 * ADR-021's browser half. The register answers "how many profiles have written owner state",
 * and Task 4.3 deletes the legacy migration on the strength of that answer — so the tests
 * here are about the ways the answer could be wrong: an id that changes, an id that is not
 * random, and a profile counted once per page view because it cannot keep one.
 */
function createStorage({ readonly = false } = {}) {
  const m = new Map()
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => { if (readonly) throw new DOMException('QuotaExceededError'); m.set(k, v) },
    removeItem: (k) => m.delete(k),
    clear: () => m.clear(),
  }
}

beforeEach(() => { globalThis.localStorage = createStorage() })

describe('the device register mints one opaque id per browser profile', () => {
  it('mints once and returns the same id afterwards', () => {
    const first = localDevice()
    const second = localDevice()
    expect(first.id).toBeTruthy()
    expect(second.id).toBe(first.id)
    expect(second.first_seen_at).toBe(first.first_seen_at)
  })

  it('keeps first_seen_at across sessions, so a later write cannot overwrite it', () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    try {
      vi.setSystemTime(Date.UTC(2026, 7, 30))
      const minted = localDevice()
      vi.setSystemTime(Date.UTC(2026, 8, 13))
      const field = deviceField()
      expect(field.record.first_seen_at).toBe(minted.first_seen_at)
      expect(field.record.last_seen_at).toBe(Date.UTC(2026, 8, 13))
    } finally { vi.useRealTimers() }
  })

  it('is random, not derived from the browser', () => {
    // Two profiles differ only in their storage. Anything read off the user agent, the
    // screen or the clock would collide here, and a colliding id undercounts.
    const a = localDevice().id
    globalThis.localStorage = createStorage()
    const b = localDevice().id
    expect(b).not.toBe(a)
    expect(a).not.toContain(navigator.userAgent.slice(0, 8))
  })

  it('does not register a profile that cannot keep the id', () => {
    // A private window, or storage that is full. Minting a fresh id on every load would make
    // one browser read as a growing fleet, which is worse than not being counted.
    globalThis.localStorage = createStorage({ readonly: true })
    expect(localDevice()).toBeNull()
    expect(deviceField()).toBeNull()
  })

  it('does not invent an id without a CSPRNG', () => {
    const real = globalThis.crypto
    try {
      Object.defineProperty(globalThis, 'crypto', { value: {}, configurable: true })
      expect(localDevice()).toBeNull()
    } finally {
      Object.defineProperty(globalThis, 'crypto', { value: real, configurable: true })
    }
  })

  it('writes the id under its own key, not into the owner-state key', () => {
    // A migration rewrites smartshelf.ownerState.v2 whole; the id must survive that.
    localDevice()
    expect(JSON.parse(globalThis.localStorage.getItem(DEVICE_KEY)).id).toBeTruthy()
    expect(globalThis.localStorage.getItem('smartshelf.ownerState.v2')).toBeNull()
  })
})
