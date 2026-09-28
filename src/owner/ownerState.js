/**
 * ownerState — the browser's half of the owner-state contract (design §10.3, §11.5).
 *
 * One key, `smartshelf.ownerState.v2`. The three pre-V1 keys (`smartshelf.operationalActions.v1`,
 * `smartshelf.ownerAnswers.v1`, `smartshelf.demoState.v1`) were read into it once, by a
 * one-shot migration that Phase 4 Task 4.3 (#78) removed on 2026-09-24, after the owner
 * confirmed every device had opened the app since the cut-over. The keys stay on those
 * devices, unread and never deleted: removing the migration is reversible, deleting a
 * user's data is not. The migration is at `v1-attic-2026-09-24` if it is ever needed.
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

export const OUTCOME_STATUS = Object.freeze({
  ACTED: 'acted', DECLINED: 'declined', DEFERRED: 'deferred',
})

export const OUTCOME_REASONS = Object.freeze({
  WRONG_DATA: 'wrong_data', NOT_WORTH_IT: 'not_worth_it', ALREADY_HANDLED: 'already_handled',
  // F4 FR-070 (approved 2026-09-28): what he found when he checked an idle product. Both are
  // `acted`; the third answer, "the count is wrong", is `declined` with WRONG_DATA.
  STILL_STOCKED: 'still_stocked', NO_LONGER_CARRIED: 'no_longer_carried',
})

export const ANSWER_STATUS = Object.freeze({ ANSWERED: 'answered', DEFERRED: 'deferred' })

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

/** The owner state: this device's v2 record, or an empty one if it has none yet. */
export function loadOwnerState() {
  if (cache) return cache
  const existing = readKey(STORAGE_KEY)
  const state = (cache = existing ? { ...empty(), ...existing } : empty())
  // Once per session: send what this device holds. It recovers everything recorded before
  // write-through existed, and retries anything a failed send left behind (#94).
  void pushAll(state)
  return state
}

export async function recordOutcome(entry, { status, reason = null, deferredUntil = null, approvedQuantity = null } = {}) {
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
  // #139. A deferral with no date is written without `deferred_until`, and compose reads
  // that absence as deferred indefinitely — so the button labelled "Later" removed the
  // entry for good. The store refuses it here rather than recording it, for the same reason
  // it refuses an unknown status: a silently-accepted wrong value became an artefact-level
  // fact nobody saw for four days. OQ-604 may lengthen the duration; it may not restore
  // "forever".
  if (status === OUTCOME_STATUS.DEFERRED && !Number.isFinite(deferredUntil)) {
    throw new Error('recordOutcome: a deferral needs deferredUntil; without one it is a permanent dismissal (#139)')
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
          // ADR-034 Decision 2: an order suggestion's outcome carries the order day it is for,
          // net or gross, the quantity suggested, and his own when he changed it (FR-161). No
          // ₪ field (D-1). Approved orders lists these, and the engine reads `order_day` to
          // say when a schedule change leaves an approval pointing at another day.
          ...(entry.signal_family === 'order.suggestion'
            ? {
                order_day: entry.evidence?.order_day ?? null,
                kind: entry.evidence?.kind ?? null,
                suggested_quantity: entry.evidence?.quantity ?? null,
                ...(Number.isInteger(approvedQuantity) && approvedQuantity > 0 ? { approved_quantity: approvedQuantity } : {}),
              }
            : {}),
        },
      },
    },
    meta: { ...state.meta, updated_at: Date.now() },
  }
  writeState(next)
  void writeThrough('outcomes', entry.id, next.outcomes[entry.id])
}

/**
 * Take an outcome back. Returns false when there was nothing to take back.
 *
 * WHY THIS HAS TO EXIST
 *   `EntryCard`'s "Later" sends `{ status: 'deferred' }` with no date, `recordOutcome`
 *   writes `deferred_until` only when it is non-null, and `compose` reads a missing
 *   `deferred_until` as deferred indefinitely. So the button labelled "Later" hid the entry
 *   for good. F6-S1 saw it coming — OQ-604, verbatim: "nothing defines its duration. Without
 *   it, deferral is indistinguishable from permanent dismissal."
 *
 *   How long "later" means is a product decision (OQ-604) and is not taken here. Making the
 *   press recoverable takes no decision at all, and it is the difference between a mistake
 *   that costs a tap and one that costs the entry.
 *
 * The remote write is a `null` tombstone rather than a field delete: `writeThrough` merges a
 * single field, and nothing reads outcomes back from Firestore today (see #134), so a null
 * is both the cheapest correct thing and honest about what happened.
 */
export async function clearOutcome(entryId) {
  if (!entryId) throw new Error('clearOutcome: entryId is required')
  const state = loadOwnerState()
  if (!state.outcomes?.[entryId]) return false
  const outcomes = { ...state.outcomes }
  delete outcomes[entryId]
  writeState({ ...state, outcomes, meta: { ...state.meta, updated_at: Date.now() } })
  void writeThrough('outcomes', entryId, null)
  return true
}

// The facts a question can ask, and for a disagreement the four answers it offers (F8-S1
// FR-158). Permanent names, like every one in design §10.1: an answer is stored under its fact.
export const ANSWER_FACTS = Object.freeze({ COST_PRICE: 'cost_price', MARKET_DISAGREEMENT: 'market_disagreement' })
export const DISAGREEMENT_ANSWERS = Object.freeze(['shelf_place', 'price', 'weak_market', 'sells_elsewhere'])

/**
 * Record his answer to one question: `answers[barcode][fact]`, beside any answer he gave to
 * another question about the same product (Phase 5 Task 5.14, ADR-034 Decision 3).
 *
 * It used to replace the barcode's whole record with `{ cost_price }`, which was harmless while
 * cost was the only fact and would now erase a cost answer the moment he answered a
 * disagreement. The remote write names the same `barcode.fact` path for the same reason.
 */
export async function recordAnswer(barcode, fact, { value, status = ANSWER_STATUS.ANSWERED } = {}) {
  if (!barcode) throw new Error('recordAnswer: barcode is required')
  if (!Object.values(ANSWER_FACTS).includes(fact)) {
    throw new Error(`recordAnswer: fact ${String(fact)} is not one any question asks`)
  }
  let stored = value
  if (fact === ANSWER_FACTS.COST_PRICE) {
    stored = Number(value)
    if (status === ANSWER_STATUS.ANSWERED && (!Number.isFinite(stored) || stored <= 0)) {
      // A cost of zero is not an answer; storing it would put a number in front of the owner
      // that no one can act on (D-3).
      throw new Error(`recordAnswer: value ${String(value)} is not a usable cost`)
    }
  } else if (status === ANSWER_STATUS.ANSWERED && !DISAGREEMENT_ANSWERS.includes(value)) {
    throw new Error(`recordAnswer: ${String(value)} is not one of the market_disagreement answers`)
  }
  const state = loadOwnerState()
  const record = { value: stored, at: Date.now(), status }
  writeState({
    ...state,
    answers: { ...state.answers, [barcode]: { ...(state.answers?.[barcode] || {}), [fact]: record } },
    meta: { ...state.meta, updated_at: Date.now() },
  })
  void writeThrough('answers', barcode, record, { field: fact })
}
