import { authMode } from './mode.js'

/**
 * The signed-in role, for modules that are not React components (the owner-state writer).
 * Set by AuthGate once the session is known.
 */
let currentRole = null

export function setCurrentRole(role) { currentRole = role }

/**
 * Only the owner records owner state (ADR-029 §4–5). A build without sign-in (local dev, the
 * tests) acts as the owner, as the app always has.
 */
export function canWriteOwnerState() {
  return authMode() !== 'firebase' || currentRole === 'owner'
}
