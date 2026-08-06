// Per-item completion-action state for OperationalPage (Issue #31).
//
// OperationalPage is the store-floor home screen. Staff clear a recommendation
// once they have acted on it (Done), hide ones that don't apply (Dismiss), or
// defer ones they'll handle later (Snooze). This module owns the pure state and
// persistence logic so it can be unit-tested without rendering React, and so a
// future networked store can replace `persistActions` without touching the page.

export const ACTIONS_STORAGE_KEY = 'smartshelf.operationalActions.v1'

export const SNOOZE_OPTIONS = [
  { id: '4h', label: '4 hours', ms: 4 * 60 * 60 * 1000 },
  { id: '24h', label: 'Tomorrow', ms: 24 * 60 * 60 * 1000 },
  { id: '1w', label: 'Next week', ms: 7 * 24 * 60 * 60 * 1000 },
]

export const OUTCOME_LABEL = {
  done: 'Done',
  dismissed: 'Dismissed',
  snoozed: 'Snoozed',
}

export function hasLocalStorage() {
  try {
    return typeof globalThis.localStorage !== 'undefined'
  } catch {
    return false
  }
}

export function loadActions() {
  if (!hasLocalStorage()) return {}
  try {
    const raw = globalThis.localStorage.getItem(ACTIONS_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

// Persist asynchronously so callers see a real pending → success/failure cycle
// (and so swapping to a networked store later needs no call-site change).
export function persistActions(next) {
  return new Promise((resolve, reject) => {
    if (!hasLocalStorage()) {
      resolve(next)
      return
    }
    try {
      globalThis.localStorage.setItem(ACTIONS_STORAGE_KEY, JSON.stringify(next))
      resolve(next)
    } catch (error) {
      reject(error)
    }
  })
}

// A snoozed item whose deadline has passed is active again.
export function isHandled(entry, now) {
  if (!entry) return false
  if (entry.status === 'done' || entry.status === 'dismissed') return true
  if (entry.status === 'snoozed') return (entry.snoozeUntil ?? 0) > now
  return false
}
