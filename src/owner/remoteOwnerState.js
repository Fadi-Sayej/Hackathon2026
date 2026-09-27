/**
 * remoteOwnerState — the write-through half of the owner-state contract (design §9.3, §9.4,
 * §10.3, §11.5), which was specified and never built (#94).
 *
 * WHAT WAS WRONG
 *   `ownerState.js` wrote the owner's outcomes and cost answers to localStorage and returned.
 *   The engine reads owner state only from Firestore, at `stores/{store}/ownerState/{doc}`,
 *   and nothing in the browser ever wrote there. So nothing the owner answered or settled
 *   reached the system: `answered_cost()` was always None, questions never closed, and the
 *   mirror the nightly pulled held `answers: 0, outcomes: 0` whatever he did.
 *
 * WHAT THIS DOES
 *   After the local write succeeds, the changed record is written to its document. The UI
 *   still commits on the local write alone (§9.3) — this is fired, never awaited by it.
 *
 * WHY FIREBASE IS IMPORTED DYNAMICALLY
 *   The owner's first screen should not pay for a network SDK he needs only once he acts.
 *   `import()` keeps it off `index.html`'s critical path; `check:bundle` reports it as a lazy
 *   chunk rather than counting it against Checkpoint 4's target.
 *
 * WHY EACH RECORD REPLACES ITS FIELD WHOLE
 *   Firestore's `merge: true` deep-merges nested maps. An outcome moving deferred -> acted
 *   would keep its stale `deferred_until` remotely while localStorage dropped it, and the two
 *   copies would disagree with no error. `mergeFields` replaces exactly the named record and
 *   leaves every sibling alone — the same thing the local write does.
 *
 * WHAT ELSE RIDES ON THIS PATH
 *   ADR-021's device register. Every write below also stamps this browser profile into the
 *   `devices` document, and `pushAll` — which runs on every load, not only when the owner
 *   acts — is the one that matters: the case Task 4.3 risks is a profile that OPENED the app
 *   and recorded nothing, which no outcome could ever stamp.
 *
 * WHAT THIS DOES NOT DO (yet)
 *   It writes; it does not read the remote state back into this device. A second device
 *   therefore still shows what it has itself recorded, not what the first did. That is the
 *   browser-reader half of §11.5, and it is separate work.
 */

import { deviceField } from './deviceRegister.js'
import { canWriteOwnerState } from '../auth/current.js'

/** design §10.3 `meta: { schema: 1, updated_at }`. MUST equal `SCHEMA` in
 *  src/owner_state/model.py, which rejects anything else as `owner_state_schema`. */
export const FIRESTORE_SCHEMA = 1

const RECORD_DOCS = ['answers', 'outcomes', 'revivals']
const DEVICES_DOC = 'devices'

async function defaultLoader() {
  // One lazy module that imports the SDK by name — see firestoreOwnerStateWriter.js for why
  // this is not `import('firebase/firestore')`.
  return (await import('./firestoreOwnerStateWriter.js')).remote
}

let loader = defaultLoader

/** Test seam, in the style of `resetCacheForTests`: no test should load the Firebase SDK. */
export function setRemoteLoaderForTests(fn) { loader = fn ?? defaultLoader }

let pushed = false
export function resetPushForTests() { pushed = false }

function report(error) {
  if (typeof console !== 'undefined') {
    console.warn('SmartShelf: owner state was saved on this device but not sent; it will be sent on the next load.', error)
  }
}

/** Resolve a usable remote, or say why there is none. Never throws. */
async function connect() {
  // ADR-029 §4–5: only the owner's account records owner state. A team account is shown the
  // app read-only, and nothing it does is sent under the owner's name. The rules refuse it too.
  if (!canWriteOwnerState()) return { reason: 'read_only' }
  const r = await loader()
  if (!r.isConfigured()) return { reason: 'unconfigured' }
  const user = await r.ensureAuth()
  if (!user) return { reason: 'no_auth' }
  return { r, db: r.getDb() }
}

const ref = (r, db, name) => r.doc(db, 'stores', r.storeId, 'ownerState', name)

/**
 * ADR-021. One field per browser profile, replaced whole — `mergeFields` for the same reason
 * the records use it, and `first_seen_at` is carried from localStorage so replacing it whole
 * cannot lose it. Returns nothing to push when the profile cannot keep an id.
 */
function stampDevice(r, db, now) {
  const field = deviceField({ now })
  if (!field) return null
  return r.setDoc(ref(r, db, DEVICES_DOC), { [field.key]: field.record },
    { mergeFields: [new r.FieldPath(field.key)] })
}

function stampMeta(r, db, now) {
  return r.setDoc(ref(r, db, 'meta'), { schema: FIRESTORE_SCHEMA, updated_at: now() }, { merge: true })
}

/**
 * Write one record to its document. Returns `{ written }` and, when false, the `reason` —
 * never throws, because a failed send must not undo a decision the owner has already made.
 */
export async function writeThrough(docName, key, record, { now = Date.now, field = null } = {}) {
  try {
    const { r, db, reason } = await connect()
    if (reason) return { written: false, reason }
    // With `field`, only `key.field` is replaced: an answer is one fact of a product's record,
    // and the product's other answers must survive it (Phase 5 Task 5.14).
    const data = field ? { [key]: { [field]: record } } : { [key]: record }
    const path = field ? new r.FieldPath(key, field) : new r.FieldPath(key)
    await Promise.all([
      r.setDoc(ref(r, db, docName), data, { mergeFields: [path] }),
      stampMeta(r, db, now),
      stampDevice(r, db, now),
    ].filter(Boolean))
    return { written: true }
  } catch (error) {
    report(error)
    return { written: false, reason: 'error' }
  }
}

/**
 * Send every local record once per session. This is what recovers the decisions the owner
 * recorded between the cut-over and this fix, which are on his phone and nowhere else; it is
 * also what retries any send that failed last time. Idempotent: each record replaces its own
 * field, so sending one twice changes nothing.
 */
export async function pushAll(state, { now = Date.now } = {}) {
  if (pushed) return { written: false, reason: 'already_pushed' }
  pushed = true
  try {
    const { r, db, reason } = await connect()
    if (reason) { pushed = false; return { written: false, reason } }
    const writes = []
    for (const name of RECORD_DOCS) {
      const map = state?.[name] || {}
      const keys = Object.keys(map)
      if (!keys.length) continue
      // Answers go fact by fact, so this device's copy never overwrites an answer another
      // device gave to a different question about the same product.
      const paths = name === 'answers'
        ? keys.flatMap((k) => Object.keys(map[k] || {}).map((fact) => new r.FieldPath(k, fact)))
        : keys.map((k) => new r.FieldPath(k))
      writes.push(r.setDoc(ref(r, db, name), map, { mergeFields: paths }))
    }
    writes.push(stampMeta(r, db, now))
    // Unconditional — the loop above skips a document with no records, but the register
    // must not skip a profile with none. A profile that opened the app and recorded nothing
    // is precisely what Task 4.3's precondition asks about.
    const device = stampDevice(r, db, now)
    if (device) writes.push(device)
    await Promise.all(writes)
    return { written: true }
  } catch (error) {
    pushed = false
    report(error)
    return { written: false, reason: 'error' }
  }
}
