/**
 * Which access model this build runs (ADR-029).
 *
 * `basic` until the switch-over: the edge's Basic Auth gate and anonymous Firebase, exactly as
 * before. `firebase` once VITE_AUTH_MODE=firebase is set for the build: Google or email-link
 * sign-in, and a role per account. The edge reads its own AUTH_MODE; both are flipped together.
 */
const env = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {}

let override = null

export function authMode() {
  return (override ?? env.VITE_AUTH_MODE) === 'firebase' ? 'firebase' : 'basic'
}

/** Test seam. `null` goes back to the build's own setting. */
export function setAuthModeForTests(mode) { override = mode }
