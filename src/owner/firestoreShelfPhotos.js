/**
 * The one module that binds the shelf photos to the Firebase SDK (ADR-042). Imported with
 * `import()` when a photo is sent or the page asks what is waiting, so none of it is on
 * `index.html`'s critical path, and by name, so the bundler shares the Firestore code the owner
 * state already loads (see firestoreOwnerStateWriter.js).
 */
import { Bytes, collection, doc, getDocs, setDoc } from 'firebase/firestore'
import { STORE_ID, ensureAuthForMode, getDb, isFirebaseConfigured } from '../firebase.js'
import { canWriteOwnerState } from '../auth/current.js'
import { sendPhoto } from './shelfPhotos.js'

async function database() {
  if (!isFirebaseConfigured()) throw new Error('unconfigured')
  if (!(await ensureAuthForMode())) throw new Error('no_auth')
  return getDb()
}

/** Send one photo under the store's own subtree. Throws when it did not send. */
export async function send(unit, file, id) {
  // ADR-029: a team account's view is read-only, and the rules refuse its writes as well.
  if (!canWriteOwnerState()) throw new Error('read_only')
  const db = await database()
  const photo = ['stores', STORE_ID, 'shelfPhotos', id]
  await sendPhoto({ id, unit, file }, {
    writePart: (_, n, part) => setDoc(doc(db, ...photo, 'parts', String(n)), { ...part, data: Bytes.fromUint8Array(part.data) }),
    writeManifest: (_, manifest) => setDoc(doc(db, ...photo), manifest),
  })
}

/** The photos still waiting in Firestore for the nightly: their manifests, never their bytes. */
export async function pending() {
  const db = await database()
  const snap = await getDocs(collection(db, 'stores', STORE_ID, 'shelfPhotos'))
  return snap.docs.map((d) => ({ id: d.id, unit: d.get('unit'), sentAt: d.get('sentAt') }))
}
