import { createContext, useContext } from 'react'

/**
 * Who is looking (ADR-029). A build without sign-in (local dev, the tests) has no account and
 * treats whoever opens it as the owner, which is what the app has always done.
 */
export const BASIC_AUTH = Object.freeze({ mode: 'basic', role: 'owner', readOnly: false, email: null, signOut: null })

export const AuthContext = createContext(BASIC_AUTH)

export function useAuth() {
  return useContext(AuthContext)
}
