/**
 * The one module that binds the owner's units to the Firebase SDK (D-38, ADR-043 Decision 2).
 * Imported with `import()` when the form saves or opens, by name, as firestoreShelfPhotos.js is.
 * The list is one document of the owner's state, written whole on each save; the nightly writes it
 * into the layout file (src/owner_state/shelf_units.py).
 */
import { doc, getDoc, setDoc } from 'firebase/firestore'
import { STORE_ID, ensureAuthForMode, getDb, isFirebaseConfigured } from '../firebase.js'
import { canWriteOwnerState } from '../auth/current.js'
import { UNITS_SCHEMA, within } from './shelfUnits.js'

const SAVE_TIMEOUT_MS = 30_000

async function layoutDoc() {
  if (!isFirebaseConfigured()) throw new Error('unconfigured')
  if (!(await ensureAuthForMode())) throw new Error('no_auth')
  return doc(getDb(), 'stores', STORE_ID, 'ownerState', 'layout')
}

/** Save the whole list. Throws when it did not save, and the form says so. */
export async function save(units) {
  // ADR-029: a team account's view is read-only, and the rules refuse its writes as well.
  if (!canWriteOwnerState()) throw new Error('read_only')
  const ref = await layoutDoc()
  await within(SAVE_TIMEOUT_MS, setDoc(ref, { schema: UNITS_SCHEMA, saved_at: new Date().toISOString(), units }))
}

/** The owner's last save, or null. */
export async function load() {
  const snap = await getDoc(await layoutDoc())
  return snap.exists() ? snap.data() : null
}
