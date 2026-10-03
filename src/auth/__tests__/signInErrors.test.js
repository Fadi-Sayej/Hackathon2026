import { describe, expect, it } from 'vitest'
import { errorKey } from '../signInErrors.js'

// Firebase says why a sign-in failed. The page used to show one sentence for every reason,
// so a blocked pop-up, an old link and a wrong address all read "Sign-in didn't work".
describe('errorKey', () => {
  it.each([
    ['auth/unauthorized-domain', 'auth.error.address'],
    ['auth/unauthorized-continue-uri', 'auth.error.address'],
    ['auth/popup-blocked', 'auth.error.popup'],
    ['auth/invalid-action-code', 'auth.error.link'],
    ['auth/expired-action-code', 'auth.error.link'],
    ['auth/invalid-email', 'auth.error.email'],
    ['auth/missing-email', 'auth.error.email'],
    ['auth/network-request-failed', 'auth.error.offline'],
    ['auth/too-many-requests', 'auth.error.tooMany'],
    ['auth/invalid-credential', 'auth.error.password'],
    ['auth/wrong-password', 'auth.error.password'],
    ['auth/user-not-found', 'auth.error.password'],
    ['auth/missing-password', 'auth.error.noPassword'],
    ['auth/operation-not-allowed', 'auth.error.passwordOff'],
  ])('%s says %s', (code, key) => {
    expect(errorKey(code)).toBe(key)
  })

  it.each([true, 'auth/internal-error', undefined, null])('anything else keeps the general sentence (%s)', (code) => {
    expect(errorKey(code)).toBe('auth.error')
  })
})
