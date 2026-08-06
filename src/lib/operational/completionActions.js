// Per-item completion-action state for OperationalPage (Issue #31).
//
// OperationalPage is the store-floor home screen. Staff clear a recommendation
// once they have acted on it (Done), hide ones that don't apply (Dismiss), or
// defer ones they'll handle later (Snooze). This module owns the pure state and
// persistence logic so it can be unit-tested without rendering React, and so a
// future networked store can replace `persistActions` without touching the page.
//
// It is also the single canonical home for the dismissal-reason enum. PLAN.md §5
// and nagham.md B-3 grade the pilot on *why* a manager rejected an alert — "wrong
// data across a whole type" tells us more than any acceptance rate. Do not define
// a second copy of these values anywhere else.

export const ACTIONS_STORAGE_KEY = 'smartshelf.operationalActions.v1'

// ---------------------------------------------------------------------------
// Outcome status (closed enum)
// ---------------------------------------------------------------------------

export const ACTION_STATUS = Object.freeze({
  DONE: 'DONE',
  DISMISSED: 'DISMISSED',
  SNOOZED: 'SNOOZED',
})

export const ACTION_STATUS_VALUES = Object.freeze(Object.values(ACTION_STATUS))

export const OUTCOME_LABEL = Object.freeze({
  [ACTION_STATUS.DONE]: 'Done',
  [ACTION_STATUS.DISMISSED]: 'Dismissed',
  [ACTION_STATUS.SNOOZED]: 'Snoozed',
})

// Older records (pre-#31) used lowercase status strings. Read them, but only ever
// write the canonical uppercase form.
const LEGACY_STATUS = Object.freeze({
  done: ACTION_STATUS.DONE,
  dismissed: ACTION_STATUS.DISMISSED,
  snoozed: ACTION_STATUS.SNOOZED,
})

export function normalizeStatus(value) {
  if (typeof value !== 'string') return null
  const upper = value.toUpperCase()
  if (ACTION_STATUS_VALUES.includes(upper)) return upper
  return LEGACY_STATUS[value] ?? null
}

// ---------------------------------------------------------------------------
// Dismissal reasons (closed enum) — the pilot's most valuable output
// ---------------------------------------------------------------------------

// Stored values are stable and machine-readable. They are what lands in
// persistence and telemetry, and they must not change once the pilot starts —
// renaming one silently rewrites history. Labels are display-only and may change
// freely; never store a label.
export const DISMISS_REASON = Object.freeze({
  WRONG_DATA: 'WRONG_DATA',
  NOT_WORTH_IT: 'NOT_WORTH_IT',
  ALREADY_HANDLED: 'ALREADY_HANDLED',
})

export const DISMISS_REASON_VALUES = Object.freeze(Object.values(DISMISS_REASON))

export const DISMISS_REASON_LABEL = Object.freeze({
  [DISMISS_REASON.WRONG_DATA]: 'The data is wrong',
  [DISMISS_REASON.NOT_WORTH_IT]: 'Not worth doing',
  [DISMISS_REASON.ALREADY_HANDLED]: 'Already handled',
})

// Render order for the picker. Kept separate from the enum so reordering the UI
// is not a data change.
export const DISMISS_REASON_ORDER = Object.freeze([
  DISMISS_REASON.WRONG_DATA,
  DISMISS_REASON.NOT_WORTH_IT,
  DISMISS_REASON.ALREADY_HANDLED,
])

export function isDismissReason(value) {
  return typeof value === 'string' && DISMISS_REASON_VALUES.includes(value)
}

// An unknown or missing reason is reported as unknown. It is NEVER silently
// mapped onto a valid reason — doing so would fabricate pilot evidence, which is
// exactly what the reason field exists to prevent.
export function dismissReasonLabel(value) {
  if (!isDismissReason(value)) return 'Reason not recorded'
  return DISMISS_REASON_LABEL[value]
}

// ---------------------------------------------------------------------------
// Snooze
// ---------------------------------------------------------------------------

export const SNOOZE_OPTIONS = Object.freeze([
  { id: '4h', label: '4 hours', ms: 4 * 60 * 60 * 1000 },
  { id: '24h', label: 'Tomorrow', ms: 24 * 60 * 60 * 1000 },
  { id: '1w', label: 'Next week', ms: 7 * 24 * 60 * 60 * 1000 },
])

export function snoozeOptionById(id) {
  return SNOOZE_OPTIONS.find((option) => option.id === id) ?? null
}

// ---------------------------------------------------------------------------
// Entry construction and validation
// ---------------------------------------------------------------------------

/**
 * Build a canonical stored entry. Returns null for an unusable input rather than
 * guessing — callers treat null as "leave the item open".
 */
export function buildEntry({ status, reason, snoozeOptionId, now = Date.now() }) {
  const normalized = normalizeStatus(status)
  if (!normalized) return null

  const entry = { status: normalized, at: now }

  if (normalized === ACTION_STATUS.DISMISSED) {
    // Record the reason when it is one we recognise; record its absence honestly
    // otherwise. Never substitute a default.
    entry.reason = isDismissReason(reason) ? reason : null
  }

  if (normalized === ACTION_STATUS.SNOOZED) {
    const option = snoozeOptionById(snoozeOptionId)
    if (!option) return null
    entry.snoozeOptionId = option.id
    entry.snoozeUntil = now + option.ms
  }

  return entry
}

/** Coerce a stored record (possibly legacy or corrupt) into a canonical entry. */
export function normalizeEntry(raw) {
  if (!raw || typeof raw !== 'object') return null
  const status = normalizeStatus(raw.status)
  if (!status) return null

  const entry = { status, at: Number.isFinite(raw.at) ? raw.at : null }

  if (status === ACTION_STATUS.DISMISSED) {
    entry.reason = isDismissReason(raw.reason) ? raw.reason : null
  }

  if (status === ACTION_STATUS.SNOOZED) {
    if (!Number.isFinite(raw.snoozeUntil)) return null
    entry.snoozeUntil = raw.snoozeUntil
    if (snoozeOptionById(raw.snoozeOptionId)) entry.snoozeOptionId = raw.snoozeOptionId
  }

  return entry
}

// ---------------------------------------------------------------------------
// Persistence
// ---------------------------------------------------------------------------

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
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    // Drop anything that does not survive validation rather than rendering a
    // half-understood record as if it were a decision.
    const clean = {}
    for (const [id, value] of Object.entries(parsed)) {
      const entry = normalizeEntry(value)
      if (entry) clean[id] = entry
    }
    return clean
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
  const status = normalizeStatus(entry.status)
  if (status === ACTION_STATUS.DONE || status === ACTION_STATUS.DISMISSED) return true
  if (status === ACTION_STATUS.SNOOZED) return (entry.snoozeUntil ?? 0) > now
  return false
}

/**
 * Seed local state from decisions already persisted through App.jsx's
 * `decisions` prop (src/lib/persistence). Those predate #31 and carry no snooze
 * deadline, so they are read as terminal outcomes. Local entries win — they are
 * the newer write path.
 */
export function mergeDecisions(actions, decisions) {
  if (!decisions || typeof decisions !== 'object') return actions
  const merged = { ...actions }
  for (const [id, decision] of Object.entries(decisions)) {
    if (merged[id]) continue
    const entry = normalizeEntry(decision)
    if (entry) merged[id] = entry
  }
  return merged
}

/** The payload handed to `onDecide` — the shape App.jsx already persists. */
export function toDecisionRecord(action, entry) {
  return {
    id: action.id,
    status: entry.status,
    reason: entry.reason ?? null,
    snoozeUntil: entry.snoozeUntil ?? null,
    type: action.type,
    productName: action.productName,
    barcode: action.barcode,
    impactIls: action.impactIls ?? null,
  }
}
