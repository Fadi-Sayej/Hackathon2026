/**
 * signInErrors.js — which sentence a failed sign-in shows (the sign-in page, 2026-10-03).
 *
 * Firebase says why a sign-in failed, in an error code. The page showed one sentence for every
 * reason, so a blocked pop-up, an old link and an address Firebase does not accept all read
 * "Sign-in didn't work". Anything not listed keeps that sentence.
 */
const KEYS = {
  'auth/unauthorized-domain': 'auth.error.address',
  'auth/unauthorized-continue-uri': 'auth.error.address',
  'auth/popup-blocked': 'auth.error.popup',
  'auth/invalid-action-code': 'auth.error.link',
  'auth/expired-action-code': 'auth.error.link',
  'auth/invalid-email': 'auth.error.email',
  'auth/missing-email': 'auth.error.email',
  'auth/network-request-failed': 'auth.error.offline',
  'auth/too-many-requests': 'auth.error.tooMany',
}

export function errorKey(code) {
  return (typeof code === 'string' && KEYS[code]) || 'auth.error'
}
