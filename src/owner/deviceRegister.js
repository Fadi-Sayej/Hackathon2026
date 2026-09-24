/**
 * deviceRegister — ADR-021, the browser half.
 *
 * WHY THIS EXISTS
 *   Phase 4 Task 4.3 (#78) deleted the one-shot migration that carried the three pre-V1
 *   localStorage keys into `smartshelf.ownerState.v2`. Its precondition was that every pilot
 *   device had opened the app since the cut-over, and nothing measured that. What the
 *   precondition protects — the owner's own recorded decisions — cannot be restored if the
 *   guess is wrong, so the precondition was made checkable instead of guessed. The owner
 *   confirmed against this register (4 profiles) on 2026-09-24, and the migration went.
 *
 * WHAT IT IS, EXACTLY
 *   One random opaque id per browser profile, minted once and kept in localStorage. It is
 *   counted, never resolved to a person: no user agent, no hardware, nothing derived from
 *   the person. The engine publishes a count and a list of dates and never the id itself.
 *
 * WHY A PROFILE THAT CANNOT PERSIST AN ID IS NOT REGISTERED
 *   An id that does not survive the load that minted it is a new device on every page view,
 *   and the count it produces is not a count of anything. Silence is the honest answer:
 *   ADR-021 already says the number is neither a floor nor a ceiling, and the owner still
 *   confirms "that is all of them".
 */

/** Its own key, not a field of `smartshelf.ownerState.v2`: the id is not the owner's state,
 *  it identifies the profile holding a copy of it, and it must survive that key being
 *  rewritten whole, which every owner-state write does. */
export const DEVICE_KEY = 'smartshelf.device.v1'

/** 128 bits from the platform CSPRNG. `Math.random` is deliberately not a fallback — ids that
 *  can collide undercount, and a browser without `crypto` cannot run the rest of the app. */
function mintId() {
  const c = globalThis.crypto
  if (typeof c?.randomUUID === 'function') return c.randomUUID()
  if (typeof c?.getRandomValues === 'function') {
    const bytes = c.getRandomValues(new Uint8Array(16))
    return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
  }
  return null
}

function read() {
  try {
    const raw = globalThis.localStorage?.getItem(DEVICE_KEY)
    const parsed = raw ? JSON.parse(raw) : null
    return typeof parsed?.id === 'string' && parsed.id ? parsed : null
  } catch {
    return null
  }
}

/**
 * This profile's id and when it was first minted, or `null` when it cannot have one.
 * `first_seen_at` is kept locally rather than read back from Firestore so that each remote
 * write can replace the record whole — the same reason `writeThrough` uses `mergeFields`.
 */
export function localDevice({ now = Date.now } = {}) {
  const existing = read()
  if (existing) return existing
  const id = mintId()
  if (!id) return null
  const record = { id, first_seen_at: now() }
  try {
    globalThis.localStorage.setItem(DEVICE_KEY, JSON.stringify(record))
  } catch {
    return null
  }
  return record
}

/**
 * The field this profile occupies in the `devices` document, or `null`. Keyed by the id, the
 * way `answers` is keyed by barcode; the id is repeated inside the record so it is still
 * self-describing if the document is ever read on its own (ADR-021 writes it as
 * `{ device_id, first_seen_at, last_seen_at }`).
 */
export function deviceField({ now = Date.now } = {}) {
  const device = localDevice({ now })
  if (!device) return null
  return {
    key: device.id,
    record: { device_id: device.id, first_seen_at: device.first_seen_at, last_seen_at: now() },
  }
}
