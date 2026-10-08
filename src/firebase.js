/**
 * firebase.js — browser Firebase client for the pilot (B-2).
 *
 * Consumed by `auth/session.js` and `owner/firestoreOwnerStateWriter.js`.
 * Everything here is lazy and fails soft: if the `VITE_FIREBASE_*` values are not
 * set, `isFirebaseConfigured()` returns false, nothing is ever initialised, and the
 * owner state stays in this device's localStorage.
 *
 * Config comes from env, never from a literal in this file. An earlier version
 * hardcoded the project's web API key here. Firebase web keys are not secrets
 * (they identify the project; Firestore rules do the actual protecting), but
 * committing one means the pilot silently points at a live project from any
 * clone or fork, which is not a decision a checkout should make for you.
 *
 * Activation, in order:
 *   1. Firebase console → Project settings → your web app → copy the config
 *      into `VITE_FIREBASE_*` (see .env.example).
 *   2. Authentication → Sign-in method → Google, and Email link (ADR-029). Each account
 *      is given its role with `scripts/set_user_role.py`; the rules accept nothing else.
 *   3. `firebase deploy --only firestore:rules`
 */

import { initializeApp, getApps, getApp } from 'firebase/app'
import {
  initializeFirestore,
  persistentLocalCache,
  persistentMultipleTabManager,
} from 'firebase/firestore'
import { getAuth } from 'firebase/auth'
import { authMode } from './auth/mode.js'

import { STORE_ID, firebaseConfig, isFirebaseConfigured } from './firebaseConfig.js'

export { STORE_ID, isFirebaseConfigured }

let appInstance = null
let dbInstance = null

function getFirebaseApp() {
  if (appInstance) return appInstance
  // Vite HMR and the two build entries (index + telemetry) can both reach this;
  // re-initialising the same app throws, so reuse whatever already exists.
  appInstance = getApps().length ? getApp() : initializeApp(firebaseConfig)
  return appInstance
}

/**
 * Lazily created Firestore handle. Throws when unconfigured rather than
 * returning a broken client — callers are expected to check
 * `isFirebaseConfigured()` first, as the owner-state writer does.
 */
export function getDb() {
  if (!isFirebaseConfigured()) {
    throw new Error(
      'Firebase is not configured. Set VITE_FIREBASE_* (see .env.example) or use localStorage.',
    )
  }
  if (dbInstance) return dbInstance

  try {
    // Offline cache: a convenience store's Wi-Fi drops, and the manager must not
    // lose a morning of decisions. Multi-tab manager so two open tabs share it.
    dbInstance = initializeFirestore(getFirebaseApp(), {
      localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }),
    })
  } catch {
    // Private browsing and some embedded webviews refuse IndexedDB. Falling back
    // to an in-memory client is strictly better than failing to load the app:
    // the owner state's localStorage copy still holds the data.
    dbInstance = initializeFirestore(getFirebaseApp(), {})
  }
  return dbInstance
}

/**
 * The signed-in user, for Firestore reads and writes, under the build's access model.
 *
 * `firebase`: the account the person signed in with (Google or email link). Resolves null
 * when nobody is signed in.
 * `basic` (local development and the tests, no sign-in): null, always. There is no account,
 * so owner state stays in this browser. Anonymous sign-in, which this used to attempt, was
 * disabled on 2026-09-26, and the role rules refuse an account without a role anyway.
 */
export async function ensureAuthForMode() {
  if (authMode() !== 'firebase') return null
  if (!isFirebaseConfigured()) return null
  try {
    const auth = getAuth(getFirebaseApp())
    await auth.authStateReady()
    return auth.currentUser
  } catch {
    return null
  }
}

export default getFirebaseApp
