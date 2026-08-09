/**
 * check_firebase_live.mjs — does Firestore ACTUALLY work? (npm run check:firebase-live)
 *
 * `check:firebase` validates the values. This one uses them: it signs in
 * anonymously and does a real write/read/delete against the pilot store, so it
 * tells you which of the two console steps is still outstanding instead of
 * leaving you to guess from a silent localStorage fallback.
 *
 * Safe: writes one doc named __connectivity_probe__ and deletes it again.
 */
import { initializeApp } from 'firebase/app'
import { getAuth, signInAnonymously } from 'firebase/auth'
import { getFirestore, doc, setDoc, getDoc, deleteDoc } from 'firebase/firestore'
import { readFileSync } from 'node:fs'

const env = Object.fromEntries(
  readFileSync('.env','utf8').split('\n')
    .filter(l => l && !l.startsWith('#') && l.includes('='))
    .map(l => [l.slice(0, l.indexOf('=')).trim(), l.slice(l.indexOf('=')+1).trim()]))

const app = initializeApp({
  apiKey: env.VITE_FIREBASE_API_KEY,
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: env.VITE_FIREBASE_PROJECT_ID,
  appId: env.VITE_FIREBASE_APP_ID,
})
const STORE = env.VITE_STORE_ID

console.log('project:', env.VITE_FIREBASE_PROJECT_ID, '| store:', STORE)

let uid = null
try {
  const cred = await signInAnonymously(getAuth(app))
  uid = cred.user.uid
  console.log('STEP 1 anonymous sign-in : ✅ enabled (uid ' + uid.slice(0,8) + '…)')
} catch (e) {
  console.log('STEP 1 anonymous sign-in : ❌ ' + e.code)
  if (e.code === 'auth/configuration-not-found')
    console.log('   → Authentication has never been set up on this project.')
    console.log('     Firebase console → Authentication → Get started,')
    console.log('     then Sign-in method → Anonymous → Enable.')
  else if (e.code === 'auth/operation-not-allowed' || e.code === 'auth/admin-restricted-operation')
    console.log('   → Firebase console → Authentication → Sign-in method → Anonymous → Enable')
  else if (e.code === 'auth/api-key-not-valid')
    console.log('   → VITE_FIREBASE_API_KEY is wrong. Re-copy it from the console.')
  process.exit(1)
}

const db = getFirestore(app)
const ref = doc(db, 'stores', STORE, 'recommendationDecisions', '__connectivity_probe__')
try {
  await setDoc(ref, { probe: true, at: new Date().toISOString() })
  const snap = await getDoc(ref)
  console.log('STEP 2 write + read back : ✅ rules allow it (' + JSON.stringify(snap.data()).slice(0,40) + '…)')
  await deleteDoc(ref)
  console.log('       probe cleaned up  : ✅')
  console.log('\nB-2 IS FULLY WORKING — nothing left but the Vercel env vars.')
} catch (e) {
  console.log('STEP 2 write             : ❌ ' + e.code)
  if (String(e.code).includes('permission-denied'))
    console.log('   → rules not deployed yet:  npx firebase-tools deploy --only firestore:rules')
  process.exit(2)
}
process.exit(0)
