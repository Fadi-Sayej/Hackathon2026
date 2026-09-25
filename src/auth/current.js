import { authMode } from './mode.js'

/**
 * The signed-in role, for modules that are not React components (the owner-state writer).
 * Set by AuthGate once the session is known.
 */
let currentRole = null

export function setCurrentRole(role) { currentRole = role }

/**
 * Only the owner records owner state (ADR-029 §4–5). Before the switch-over everyone who
 * passes Basic Auth could, and still can, so nothing changes until the mode does.
 */
export function canWriteOwnerState() {
  return authMode() !== 'firebase' || currentRole === 'owner'
}
