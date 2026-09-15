/**
 * The only module that binds owner state to the Firebase SDK. It is imported dynamically by
 * remoteOwnerState.js, so none of it is on `index.html`'s critical path.
 *
 * Named imports rather than `import('firebase/firestore')` from the caller, and that is a
 * measured difference, not style: a dynamic import of the SDK's namespace returns every export,
 * which defeats tree-shaking. The first build of #94 did exactly that and grew the total output
 * by 48 KB for three functions. Importing them by name here lets the bundler share the
 * tree-shaken Firestore code the telemetry entry already carries.
 */
import { FieldPath, doc, setDoc } from 'firebase/firestore'
import { STORE_ID, ensureAnonymousAuth, getDb, isFirebaseConfigured } from '../firebase.js'

export const remote = {
  storeId: STORE_ID,
  isConfigured: isFirebaseConfigured,
  ensureAuth: ensureAnonymousAuth,
  getDb,
  doc,
  setDoc,
  FieldPath,
}
