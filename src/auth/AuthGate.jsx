import { useCallback, useEffect, useRef, useState } from 'react'

import { AppShell } from '../components/layout/AppShell.jsx'
import { authMode } from './mode.js'
import { setCurrentRole } from './current.js'
import { landingFor } from './landing.js'
import { SignInPage } from './SignInPage.jsx'
import { AuthContext } from './useAuth.js'

/**
 * Renders the app only for an account with a role. Until then it renders the approved
 * sign-in screens inside the bare shell. In `basic` mode it renders the app untouched and
 * loads nothing: the Firebase SDK stays off the page.
 */
export function AuthGate({ children }) {
  if (authMode() !== 'firebase') return children
  return <SignedIn>{children}</SignedIn>
}

function SignedIn({ children }) {
  const [state, setState] = useState({ status: 'loading' })
  const session = useRef(null)
  // Set before a sign-in starts, because Firebase may report the new session before the
  // sign-in call itself returns. Only a fresh sign-in sends the team to its own page; a team
  // member who opens the owner's app later stays on it.
  const justSignedIn = useRef(false)

  useEffect(() => {
    let live = true
    let stop = () => {}
    import('./session.js')
      .then(async (s) => {
        session.current = s
        if (s.pendingEmailLink()) {
          const email = s.rememberedEmail()
          if (!email) {
            if (live) setState({ status: 'needEmail' })
          } else {
            justSignedIn.current = true
            try { await s.finishEmailLink(email) } catch {
              justSignedIn.current = false
              if (live) setState({ status: 'signedOut', error: true })
            }
          }
        }
        stop = s.watchSession(({ user, role, error }) => {
          if (!live) return
          if (error) { setCurrentRole(null); setState({ status: 'signedOut', error: true }); return }
          if (!user) {
            setCurrentRole(null)
            // Waiting on an email link is not "signed out": keep that screen.
            setState((prev) => (['needEmail', 'linkSent'].includes(prev.status) || prev.error ? prev : { status: 'signedOut' }))
            return
          }
          setCurrentRole(role)
          if (!role) { setState({ status: 'noAccess', email: user.email }); return }
          const next = new URLSearchParams(window.location.search).get('next')
          const target = landingFor(role, next)
          if ((justSignedIn.current || next) && target !== window.location.pathname) {
            window.location.assign(target)
            return
          }
          if (next) window.history.replaceState(null, '', window.location.pathname)
          setState({ status: 'ready', role, email: user.email })
        })
      })
      .catch(() => { if (live) setState({ status: 'signedOut', error: true }) })
    return () => { live = false; stop() }
  }, [])

  const attempt = useCallback(async (action, onFail) => {
    justSignedIn.current = true
    try {
      await action()
    } catch (error) {
      justSignedIn.current = false
      // Closing Google's window is a choice, not a failure.
      if (error?.code === 'auth/popup-closed-by-user' || error?.code === 'auth/cancelled-popup-request') return
      onFail()
    }
  }, [])

  const onGoogle = useCallback(() => attempt(
    () => session.current.signInWithGoogle(),
    () => setState({ status: 'signedOut', error: true }),
  ), [attempt])

  const onSendLink = useCallback(async (email) => {
    try {
      await session.current.sendEmailLink(email)
      setState({ status: 'linkSent', email })
    } catch {
      setState({ status: 'signedOut', error: true })
    }
  }, [])

  const onFinish = useCallback((email) => attempt(
    () => session.current.finishEmailLink(email),
    () => setState({ status: 'needEmail', error: true }),
  ), [attempt])

  const signOut = useCallback(async () => {
    try { await session.current?.signOutEverywhere() } finally {
      setCurrentRole(null)
      setState({ status: 'signedOut' })
    }
  }, [])

  if (state.status === 'ready') {
    const value = { mode: 'firebase', role: state.role, readOnly: state.role === 'team', email: state.email, signOut }
    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  }

  return (
    <AppShell bare activePage="daily">
      <SignInPage
        status={state.status}
        email={state.email}
        error={Boolean(state.error)}
        onGoogle={onGoogle}
        onSendLink={onSendLink}
        onFinish={onFinish}
        onUseDifferentEmail={() => setState({ status: 'signedOut' })}
        onSignOut={signOut}
      />
    </AppShell>
  )
}
