/**
 * check_firebase_config.mjs — will B-2 actually switch on? (npm run check:firebase)
 *
 * Firestore activation fails *silently*: the owner state stays in localStorage
 * whenever `isFirebaseConfigured()` is false, so a typo'd or half-filled config
 * looks exactly like a working app — until you discover at the end of the pilot
 * that every decision lived on one laptop and the team saw nothing.
 *
 * This validates the values BEFORE you deploy, and says which of the two remaining
 * console steps is missing.
 *
 *   npm run check:firebase                 # checks .env
 *   npm run check:firebase -- --env .env.production
 */

import { existsSync, readFileSync } from 'node:fs'
import process from 'node:process'
import { readStoreSettings } from './store_settings.mjs'

const REQUIRED = {
  VITE_FIREBASE_API_KEY: {
    hint: 'Firebase console → Project settings → Your apps → Web app → apiKey',
    check: (v) => (v.startsWith('AIza') ? null : 'should start with "AIza"'),
  },
  VITE_FIREBASE_PROJECT_ID: {
    hint: 'same panel → projectId (e.g. hackathon26-a6ebd)',
    check: (v) => (/^[a-z0-9-]+$/.test(v) ? null : 'lowercase letters, digits and hyphens only'),
  },
  VITE_FIREBASE_APP_ID: {
    hint: 'same panel → appId',
    check: (v) => (/^\d+:\d+:web:[a-f0-9]+$/i.test(v) ? null : 'expected the form 1:123456:web:abcdef'),
  },
}

const OPTIONAL = {
  VITE_FIREBASE_AUTH_DOMAIN: 'used by anonymous sign-in; usually <projectId>.firebaseapp.com',
  VITE_FIREBASE_STORAGE_BUCKET: 'not needed for Firestore',
  VITE_FIREBASE_MESSAGING_SENDER_ID: 'not needed for Firestore',
}

// ADR-036: which store this copy serves is configs/store.yaml's `id`, never a default.
const STORE = readStoreSettings()

const argIndex = process.argv.indexOf('--env')
const envPath = argIndex > -1 ? process.argv[argIndex + 1] : '.env'

function parseEnv(path) {
  if (!existsSync(path)) return null
  const out = {}
  for (const rawLine of readFileSync(path, 'utf8').split('\n')) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const eq = line.indexOf('=')
    if (eq < 1) continue
    out[line.slice(0, eq).trim()] = line.slice(eq + 1).trim().replace(/^["']|["']$/g, '')
  }
  return out
}

const green = (s) => `[32m${s}[0m`
const red = (s) => `[31m${s}[0m`
const yellow = (s) => `[33m${s}[0m`
const bold = (s) => `[1m${s}[0m`

const env = parseEnv(envPath)
console.log(bold(`\nFirebase config check — ${envPath}\n`))

if (!env) {
  console.log(`${yellow('!')} ${envPath} does not exist.`)
  console.log('  Copy .env.example to .env and fill in the VITE_FIREBASE_* values.')
  console.log(`\n  ${bold('B-2 is OFF')} — persistence stays on localStorage (which works).\n`)
  process.exit(2)
}

let missing = 0
let invalid = 0

for (const [key, { hint, check }] of Object.entries(REQUIRED)) {
  const value = env[key]
  if (!value) {
    console.log(`${red('✗')} ${key} — missing`)
    console.log(`    ${hint}`)
    missing += 1
    continue
  }
  const problem = check(value)
  if (problem) {
    console.log(`${red('✗')} ${key} — ${problem}`)
    console.log(`    got: ${value.slice(0, 12)}…`)
    invalid += 1
  } else {
    console.log(`${green('✓')} ${key}`)
  }
}

console.log()
for (const [key, note] of Object.entries(OPTIONAL)) {
  const value = env[key]
  console.log(value ? `${green('✓')} ${key}` : `${yellow('·')} ${key} — not set (${note})`)
}

// The store id (ADR-036). The rules must pin configs/store.yaml's `id`, and the env being
// checked must carry it: that is Production's. Preview's is `preview-sandbox` on purpose
// (deployment.md), so run this against Production's values, not Preview's. There is no
// fallback: an unset VITE_STORE_ID means the browser writes nothing remotely at all.
if (missing < Object.keys(REQUIRED).length) {
  const configured = env.VITE_STORE_ID || ''
  if (!configured) {
    console.log(`\n${red('✗')} VITE_STORE_ID — missing. It must be configs/store.yaml's id, "${STORE.id}".`)
    invalid += 1
  } else if (configured !== STORE.id) {
    console.log(`\n${red('✗')} STORE ID MISMATCH: VITE_STORE_ID is "${configured}", but configs/store.yaml's id is "${STORE.id}".`)
    console.log('    This copy serves one store (D-28). Production must use its id.')
    invalid += 1
  } else {
    console.log(`\n${green('✓')} VITE_STORE_ID is configs/store.yaml's id ("${STORE.id}")`)
  }
}
// The Firebase project is the copy's own (ADR-036 §1): the web config and the rules-deploy
// default must both be configs/store.yaml's `firebase.project_id`.
if (env.VITE_FIREBASE_PROJECT_ID && env.VITE_FIREBASE_PROJECT_ID !== STORE.firebaseProjectId) {
  console.log(`${red('✗')} PROJECT MISMATCH: VITE_FIREBASE_PROJECT_ID is "${env.VITE_FIREBASE_PROJECT_ID}", but configs/store.yaml's firebase.project_id is "${STORE.firebaseProjectId}".`)
  invalid += 1
}
if (existsSync('.firebaserc')) {
  const deployTo = JSON.parse(readFileSync('.firebaserc', 'utf8'))?.projects?.default
  if (deployTo !== STORE.firebaseProjectId) {
    console.log(`${red('✗')} .firebaserc deploys the rules to "${deployTo}", but configs/store.yaml's firebase.project_id is "${STORE.firebaseProjectId}".`)
    invalid += 1
  }
}
if (existsSync('firestore.rules')) {
  const rules = readFileSync('firestore.rules', 'utf8')
  const pinned = rules.match(/match \/stores\/([a-z0-9-]+)\//)
  if (pinned && pinned[1] !== STORE.id) {
    console.log(`${red('✗')} STORE ID MISMATCH: firestore.rules pins "${pinned[1]}", but configs/store.yaml's id is "${STORE.id}".`)
    console.log('    Every read and write would be denied. Make them identical, then deploy the rules.')
    invalid += 1
  } else if (pinned) {
    console.log(`${green('✓')} firestore.rules pins the same store ("${pinned[1]}")`)
  }
}

console.log()
if (missing === Object.keys(REQUIRED).length) {
  console.log(bold('B-2 is OFF') + ' — persistence stays on localStorage.')
  console.log('That is a working state, not a failure. Decisions survive on that one')
  console.log('device but do not sync, and the telemetry dashboard sees only that device.\n')
  process.exit(2)
}
if (missing || invalid) {
  console.log(red(bold('B-2 is HALF-CONFIGURED — the worst state.')))
  console.log('isFirebaseConfigured() requires all three, so it will return false and')
  console.log('fall back to localStorage silently. Fix the above or clear the values.\n')
  process.exit(1)
}

console.log(green(bold('Config is valid.')) + ' Two console steps remain — neither is code:\n')
console.log('  1. Firebase console → Authentication → Sign-in method → Anonymous → Enable')
console.log('     Without it every request is unauthenticated and the rules deny it.')
console.log('  2. Deploy the rules:  firebase deploy --only firestore:rules')
console.log('     Without it the default rules deny everything.\n')
console.log('Then set the SAME values in Vercel (Production AND Preview), redeploy, and')
console.log('confirm on /telemetry.html that the footer reads "Firestore · ' + STORE.id + '"')
console.log('rather than "localStorage (this device only)".\n')
