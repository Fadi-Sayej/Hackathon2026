/**
 * Which access model this build runs (ADR-029).
 *
 * `firebase` when VITE_AUTH_MODE=firebase is set for the build, as it is on Vercel: Google or
 * email-link sign-in, and a role per account. `basic` otherwise, which is what `npm run dev` and
 * the tests run: no sign-in, and the app acts as the owner. Its owner state stays in the
 * browser, because the Firestore rules accept only an account with a role.
 */
const env = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {}

let override = null

export function authMode() {
  return (override ?? env.VITE_AUTH_MODE) === 'firebase' ? 'firebase' : 'basic'
}

/** Test seam. `null` goes back to the build's own setting. */
export function setAuthModeForTests(mode) { override = mode }
