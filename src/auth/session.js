/**
 * The Firebase side of sign-in (ADR-029 §1). Loaded with `import()` by AuthGate, and only when
 * the build runs in `firebase` mode, so none of the SDK is on the owner's first download
 * before the switch-over.
 */
import {
  GoogleAuthProvider,
  getAuth,
  isSignInWithEmailLink,
  onIdTokenChanged,
  sendSignInLinkToEmail,
  signInWithEmailLink,
  signInWithPopup,
  signOut,
} from 'firebase/auth'

import getFirebaseApp from '../firebase.js'
import { clearedSessionCookie, sessionCookie } from './cookie.js'

const EMAIL_KEY = 'smartshelf.signInEmail'
const ROLES = new Set(['owner', 'team'])

const auth = () => getAuth(getFirebaseApp())

function writeCookie(token) {
  document.cookie = token
    ? sessionCookie(token, { secure: window.location.protocol === 'https:' })
    : clearedSessionCookie()
}

/**
 * Follow the session: `onChange({ user, role })` on sign-in, sign-out and every token refresh,
 * with the cookie rewritten first so the edge sees the same token the page holds. A role set
 * after the token was issued is picked up by forcing one refresh when the token has none.
 * Returns an unsubscribe.
 */
export function watchSession(onChange) {
  const a = auth()
  let forced = false
  const onVisible = () => {
    // A phone left overnight wakes with an expired token; renew it before the page fetches.
    if (document.visibilityState === 'visible') a.currentUser?.getIdToken().catch(() => {})
  }
  document.addEventListener('visibilitychange', onVisible)
  const stop = onIdTokenChanged(a, async (user) => {
    if (!user) { writeCookie(null); onChange({ user: null, role: null }); return }
    try {
      const result = await user.getIdTokenResult()
      const role = ROLES.has(result.claims.role) ? result.claims.role : null
      if (!role && !forced) {
        forced = true
        await user.getIdToken(true) // fires this listener again, with any role set since
        return
      }
      writeCookie(result.token)
      onChange({ user, role })
    } catch {
      // A token that cannot be read or renewed (offline with an expired token, say) must not
      // leave the page on its loading screen: say so, and let the person try again.
      onChange({ user: null, role: null, error: true })
    }
  })
  return () => { stop(); document.removeEventListener('visibilitychange', onVisible) }
}

export async function signInWithGoogle() {
  await signInWithPopup(auth(), new GoogleAuthProvider())
}

export async function sendEmailLink(email) {
  await sendSignInLinkToEmail(auth(), email, {
    url: `${window.location.origin}/${window.location.search}`,
    handleCodeInApp: true,
  })
  try { window.localStorage.setItem(EMAIL_KEY, email) } catch { /* private mode: asked again */ }
}

export function pendingEmailLink() {
  return isSignInWithEmailLink(auth(), window.location.href)
}

export function rememberedEmail() {
  try { return window.localStorage.getItem(EMAIL_KEY) } catch { return null }
}

export async function finishEmailLink(email) {
  await signInWithEmailLink(auth(), email, window.location.href)
  try { window.localStorage.removeItem(EMAIL_KEY) } catch { /* nothing to clear */ }
  // The link's one-time code stays out of the address bar and the history; `next` survives.
  const next = new URLSearchParams(window.location.search).get('next')
  window.history.replaceState(null, '', next ? `/?next=${encodeURIComponent(next)}` : window.location.pathname)
}

export async function signOutEverywhere() {
  await signOut(auth())
  writeCookie(null)
}
