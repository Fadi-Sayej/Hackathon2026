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
 *   2. Authentication → Sign-in method → Anonymous → Enable.
 *   3. `firebase deploy --only firestore:rules`
 */

import { initializeApp, getApps, getApp } from 'firebase/app'
import {
  initializeFirestore,
  persistentLocalCache,
  persistentMultipleTabManager,
} from 'firebase/firestore'
import { getAuth, signInAnonymously, onAuthStateChanged } from 'firebase/auth'
import { authMode } from './auth/mode.js'

// import.meta.env is a plain object at build time; guard so this module can also
// be imported from Node (tests, tooling) without Vite's define step.
const env = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {}

function readEnv(key) {
  const value = env[key]
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : ''
}

const firebaseConfig = {
  apiKey: readEnv('VITE_FIREBASE_API_KEY'),
  authDomain: readEnv('VITE_FIREBASE_AUTH_DOMAIN'),
  projectId: readEnv('VITE_FIREBASE_PROJECT_ID'),
  storageBucket: readEnv('VITE_FIREBASE_STORAGE_BUCKET'),
  messagingSenderId: readEnv('VITE_FIREBASE_MESSAGING_SENDER_ID'),
  appId: readEnv('VITE_FIREBASE_APP_ID'),
}

/**
 * Firestore path root: stores/{STORE_ID}/... — see firestore.rules.
 * One store for the pilot; the default keeps paths stable if the env is unset.
 */
export const STORE_ID = readEnv('VITE_STORE_ID') || 'yomyom-kafr-qasim'

// The three values without which nothing can connect. storageBucket / senderId
// are not required for Firestore + anonymous auth, so they are not gated on.
const REQUIRED_KEYS = ['apiKey', 'projectId', 'appId']

/**
 * Is the browser Firebase config present? The owner-state writer checks it before
 * touching Firestore.
 */
export function isFirebaseConfigured() {
  return REQUIRED_KEYS.every((key) => firebaseConfig[key] !== '')
}

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

let authPromise = null

/**
 * Resolve once an anonymous session exists. Firestore rules require
 * `request.auth != null`, so every read/write must wait on this.
 *
 * Resolves (rather than rejects) on failure so a sign-in problem degrades to
 * "local only" instead of taking the page down; the owner state keeps serving
 * from its localStorage copy.
 */
export function ensureAnonymousAuth() {
  if (authPromise) return authPromise

  authPromise = new Promise((resolve) => {
    if (!isFirebaseConfigured()) {
      resolve(null)
      return
    }
    try {
      const auth = getAuth(getFirebaseApp())
      if (auth.currentUser) {
        resolve(auth.currentUser)
        return
      }
      const unsubscribe = onAuthStateChanged(auth, (user) => {
        if (user) {
          unsubscribe()
          resolve(user)
        }
      })
      signInAnonymously(auth).catch((error) => {
        unsubscribe()
        if (typeof console !== 'undefined') {
          console.warn(
            'SmartShelf: anonymous sign-in failed; staying on local storage. ' +
              'Enable Anonymous sign-in in the Firebase console.',
            error,
          )
        }
        resolve(null)
      })
    } catch (error) {
      if (typeof console !== 'undefined') {
        console.warn('SmartShelf: Firebase auth unavailable; staying on local storage.', error)
      }
      resolve(null)
    }
  })

  return authPromise
}

/**
 * The signed-in user, for Firestore reads and writes, under the build's access model.
 *
 * `basic` (before ADR-029's switch-over): anonymous sign-in, exactly as before.
 * `firebase`: the account the person signed in with (Google or email link). It never falls
 * back to an anonymous session, which the role rules would refuse anyway. Resolves null
 * when nobody is signed in.
 */
export async function ensureAuthForMode() {
  if (authMode() !== 'firebase') return ensureAnonymousAuth()
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
