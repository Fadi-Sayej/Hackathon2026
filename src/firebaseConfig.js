/**
 * The browser's Firebase settings, with no SDK in it, so a page can ask whether this deployment
 * can reach Firestore without loading Firebase (D-37's upload screen asks it). firebase.js
 * connects with these and re-exports the two answers, so the rule is decided once.
 */

// import.meta.env is a plain object at build time; guard so this module can also
// be imported from Node (tests, tooling) without Vite's define step.
const env = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {}

function readEnv(key) {
  const value = env[key]
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : ''
}

export const firebaseConfig = {
  apiKey: readEnv('VITE_FIREBASE_API_KEY'),
  authDomain: readEnv('VITE_FIREBASE_AUTH_DOMAIN'),
  projectId: readEnv('VITE_FIREBASE_PROJECT_ID'),
  storageBucket: readEnv('VITE_FIREBASE_STORAGE_BUCKET'),
  messagingSenderId: readEnv('VITE_FIREBASE_MESSAGING_SENDER_ID'),
  appId: readEnv('VITE_FIREBASE_APP_ID'),
}

/**
 * Firestore path root: stores/{STORE_ID}/... — see firestore.rules.
 * The deployment's own VITE_STORE_ID, with no default (ADR-036): Production's is the store's
 * id in configs/store.yaml, and Preview's is `preview-sandbox` on purpose. Unset, nothing is
 * written remotely and the owner state stays on this device.
 */
export const STORE_ID = readEnv('VITE_STORE_ID')

// The three values without which nothing can connect. storageBucket / senderId
// are not required for Firestore or sign-in, so they are not gated on.
const REQUIRED_KEYS = ['apiKey', 'projectId', 'appId']

/**
 * Is the browser Firebase config present? The owner-state writer checks it before
 * touching Firestore.
 */
export function isFirebaseConfigured() {
  return STORE_ID !== '' && REQUIRED_KEYS.every((key) => firebaseConfig[key] !== '')
}
