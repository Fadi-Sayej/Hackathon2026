/**
 * The `__session` cookie the edge gate reads (middleware.ts). It carries the Firebase ID
 * token, which lives an hour, so the cookie does too; the app rewrites it on every refresh.
 * Not HttpOnly, because the page sets it: the token is already readable by the page from
 * Firebase's own storage, so this adds no exposure.
 */
export const SESSION_COOKIE = '__session'

export function sessionCookie(token, { secure }) {
  return `${SESSION_COOKIE}=${token}; Path=/; Max-Age=3600; SameSite=Lax${secure ? '; Secure' : ''}`
}

export function clearedSessionCookie() {
  return `${SESSION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`
}
