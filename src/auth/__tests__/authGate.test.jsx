// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, screen } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { AuthGate } from '../AuthGate.jsx'
import { useAuth } from '../useAuth.js'
import { setAuthModeForTests } from '../mode.js'
import { canWriteOwnerState, setCurrentRole } from '../current.js'

// In a build without sign-in (VITE_AUTH_MODE unset: local dev and the tests) the gate must be
// invisible: the app renders as it always has and the owner may write.

afterEach(() => { cleanup(); setAuthModeForTests(null); setCurrentRole(null) })

function Probe() {
  const auth = useAuth()
  return <p data-testid="probe">{`${auth.mode}|${auth.role}|${auth.readOnly}`}</p>
}

describe('with sign-in switched off', () => {
  it('renders the app untouched, as the owner, able to write', () => {
    renderWithI18n(<AuthGate><Probe /></AuthGate>)
    expect(screen.getByTestId('probe').textContent).toBe('basic|owner|false')
    expect(canWriteOwnerState()).toBe(true)
  })
})

describe('who may write owner state once sign-in is on', () => {
  it('is the owner only', () => {
    setAuthModeForTests('firebase')
    setCurrentRole('team')
    expect(canWriteOwnerState()).toBe(false)
    setCurrentRole(null)
    expect(canWriteOwnerState()).toBe(false)
    setCurrentRole('owner')
    expect(canWriteOwnerState()).toBe(true)
  })
})

describe('with sign-in switched on', () => {
  it('shows nothing of the app before the session is known', () => {
    setAuthModeForTests('firebase')
    renderWithI18n(<AuthGate><Probe /></AuthGate>)
    expect(screen.queryByTestId('probe')).toBeNull()
  })
})
