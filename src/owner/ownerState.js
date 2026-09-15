/**
 * ownerState — the browser's half of the owner-state contract (design §10.3, §11.5).
 *
 * One key, `smartshelf.ownerState.v2`. The three pre-V1 keys are read once into it and then
 * left in place, unread (§20.2): a migration that deletes its source cannot be re-run and
 * cannot be checked.
 *
 * The cache is written first and the caller commits only after that write succeeds (§9.3).
 * An outcome the owner believes is recorded, which is not, is worse than an error.
 *
 * Then the record is written through to Firestore (remoteOwnerState.js). Until #94 it was not:
 * this module wrote localStorage and returned, and the engine — which reads owner state only
 * from Firestore — never saw a single answer or outcome. The write-through is fired, never
 * awaited here, so a slow or failed send cannot undo a decision already made.
 */

import { pushAll, writeThrough } from './remoteOwnerState.js'

export const STORAGE_KEY = 'smartshelf.ownerState.v2'

const LEGACY_ACTIONS = 'smartshelf.operationalActions.v1'
const LEGACY_ANSWERS = 'smartshelf.ownerAnswers.v1'
const LEGACY_DEMO = 'smartshelf.demoState.v1'

export const OUTCOME_STATUS = Object.freeze({
  ACTED: 'acted', DECLINED: 'declined', DEFERRED: 'deferred',
})

export const OUTCOME_REASONS = Object.freeze({
  WRONG_DATA: 'wrong_data', NOT_WORTH_IT: 'not_worth_it', ALREADY_HANDLED: 'already_handled',
})

export const ANSWER_STATUS = Object.freeze({ ANSWERED: 'answered', DEFERRED: 'deferred' })

// DONE/DISMISSED/SNOOZED are the pre-V1 vocabulary (§20.1). The mapping is one-way and
// one-shot; nothing writes the old words again.
const LEGACY_STATUS = Object.freeze({
  DONE: OUTCOME_STATUS.ACTED,
  DISMISSED: OUTCOME_STATUS.DECLINED,
  SNOOZED: OUTCOME_STATUS.DEFERRED,
})

const empty = () => ({ answers: {}, outcomes: {}, revivals: {}, meta: { schema: 2, updated_at: null } })

let cache = null

/** Test seam: the module caches, and a test that writes localStorage must be able to reset. */
export function resetCacheForTests() { cache = null }

function readKey(key) {
  try {
    const raw = globalThis.localStorage?.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function writeState(state) {
  // Throws on a full or disabled localStorage. The caller must see that: §9.3 commits only
  // after the cache write succeeds.
  globalThis.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  cache = state
  return state
}

function migratedOutcome(raw) {
  const status = LEGACY_STATUS[raw?.status]
  if (!status) return null
  const out = {
    status,
    at: Number.isFinite(raw.at) ? raw.at : null,
    reason: Object.values(OUTCOME_REASONS).includes(raw.reason) ? raw.reason : null,
    // ADR-016: the family is the durable grouping key and a legacy record has none.
    // Written as an explicit null — a stated absence, never a guess (D-3).
    snapshot: { signal_family: null, capability: null, barcode: null, characterisation: null },
  }
  if (status === OUTCOME_STATUS.DEFERRED && Number.isFinite(raw.snoozeUntil)) {
    out.deferred_until = raw.snoozeUntil
  }
  return out
}

function migrate() {
  const state = empty()

  for (const [id, raw] of Object.entries(readKey(LEGACY_ACTIONS) || {})) {
    const outcome = migratedOutcome(raw)
    if (outcome) state.outcomes[id] = outcome
  }

  const demo = readKey(LEGACY_DEMO)
  for (const [id, raw] of Object.entries(demo?.recommendationDecisions || {})) {
    const outcome = migratedOutcome(raw)
    if (outcome) state.outcomes[id] = outcome
  }

  const answers = readKey(LEGACY_ANSWERS)
  for (const [barcode, value] of Object.entries(answers?.carried || {})) {
    const num = Number(value)
    if (Number.isFinite(num) && num > 0) {
      state.answers[barcode] = { cost_price: { value: num, at: null, status: ANSWER_STATUS.ANSWERED } }
    }
  }

  state.meta.updated_at = Date.now()
  try {
    return writeState(state)
  } catch {
    // A migration that cannot persist still serves this session honestly; it runs again
    // next time rather than silently reporting an empty history.
    cache = state
    return state
  }
}

/** The owner state, migrating the three legacy keys once if v2 does not exist yet. */
export function loadOwnerState() {
  if (cache) return cache
  const existing = readKey(STORAGE_KEY)
  const state = existing ? (cache = { ...empty(), ...existing }) : migrate()
  // Once per session: send what this device holds. It recovers everything recorded before
  // write-through existed, and retries anything a failed send left behind (#94).
  void pushAll(state)
  return state
}

export async function recordOutcome(entry, { status, reason = null, deferredUntil = null } = {}) {
  if (!entry?.id) throw new Error('recordOutcome: entry.id is required')
  // ADR-016. entry_id is a hash with no inverse, so an outcome written without the family
  // loses the only durable grouping key INT-MEAS has, for good.
  if (!entry.signal_family) {
    throw new Error(`recordOutcome: entry ${entry.id} has no signal_family (ADR-016)`)
  }
  if (!Object.values(OUTCOME_STATUS).includes(status)) {
    throw new Error(`recordOutcome: status ${String(status)} is not a recorded outcome`)
  }
  if (reason !== null && !Object.values(OUTCOME_REASONS).includes(reason)) {
    throw new Error(`recordOutcome: reason ${String(reason)} is outside the enum`)
  }

  const state = loadOwnerState()
  const next = {
    ...state,
    outcomes: {
      ...state.outcomes,
      [entry.id]: {
        status,
        reason,
        at: Date.now(),
        ...(deferredUntil !== null ? { deferred_until: deferredUntil } : {}),
        snapshot: {
          signal_family: entry.signal_family,
          capability: entry.capability ?? null,
          barcode: entry.barcode ?? null,
          characterisation: entry.characterisation ?? null,
          // certainty travels with the amount, for the same reason signal_family does
          // (ADR-016): the snapshot is the only durable record, and a ₪ total that mixes
          // confirmed and estimated recovery without being able to separate them is not a
          // defensible number. D-10 — an uncertain figure is labelled uncertain BEFORE it
          // is questioned, not after. Every valued entry is `confirmed` today, which is
          // exactly why adding it costs nothing now and is unrecoverable later.
          ...(entry.value
            ? { value: entry.value.amount, kind: entry.value.kind, certainty: entry.value.certainty }
            : {}),
        },
      },
    },
    meta: { ...state.meta, updated_at: Date.now() },
  }
  writeState(next)
  void writeThrough('outcomes', entry.id, next.outcomes[entry.id])
}

export async function recordAnswer(barcode, { value, status = ANSWER_STATUS.ANSWERED } = {}) {
  if (!barcode) throw new Error('recordAnswer: barcode is required')
  const num = Number(value)
  if (status === ANSWER_STATUS.ANSWERED && (!Number.isFinite(num) || num <= 0)) {
    // A cost of zero is not an answer; storing it would put a number in front of the owner
    // that no one can act on (D-3).
    throw new Error(`recordAnswer: value ${String(value)} is not a usable cost`)
  }
  const state = loadOwnerState()
  const record = { cost_price: { value: num, at: Date.now(), status } }
  writeState({
    ...state,
    answers: { ...state.answers, [barcode]: record },
    meta: { ...state.meta, updated_at: Date.now() },
  })
  void writeThrough('answers', barcode, record)
}
