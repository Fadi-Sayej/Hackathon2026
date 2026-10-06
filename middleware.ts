function protectionNotConfigured() {
  return new Response('Deployment access protection is not configured.', {
    status: 503,
    headers: {
      'Cache-Control': 'no-store',
      'X-Robots-Tag': 'noindex, nofollow, noarchive',
    },
  })
}

// ── ADR-029: the signed-in gate ──────────────────────────────────────────────────────────
//
// The gate verifies a Firebase ID token, carried in the `__session` cookie the app sets after
// sign-in, plus its `role` claim (set per account by scripts/set_user_role.py). It is the only
// gate: the shared Basic Auth password it replaced was removed on 2026-09-26. Without
// FIREBASE_PROJECT_ID it fails closed, with a 503 on every request.
//
// What is public: the app shell and its code, which hold no store data and render the
// sign-in page themselves. What is not: every /data/ and /store/ file (any role), and the team's
// telemetry page, its chunks and its data (team only). An owner who types the telemetry URL
// is refused on the server, not hidden from in the browser.

const SESSION_COOKIE = '__session'
const JWKS_URL = 'https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com'
const CLOCK_SKEW_S = 60
const ROLES = new Set(['owner', 'team'])
const TEAM_ONLY = [
  /^\/telemetry(\.html)?\/?$/,
  /^\/assets\/telemetry-[^/]*$/,
  /^\/data\/measurement\.json$/,
  /^\/data\/operational\.json$/,
]
// Store data any role may read: the artefacts (/data/), and the product pictures ADR-040 cuts
// from the store's own shelf photos (/store/). Signed out, both are refused.
const DATA = /^\/(data|store)\//

async function defaultKeyFetcher() {
  const res = await fetch(JWKS_URL)
  if (!res.ok) throw new Error(`Google key fetch failed: ${res.status}`)
  const maxAge = Number(/max-age=(\d+)/.exec(res.headers.get('cache-control') || '')?.[1] || 3600)
  return { keys: (await res.json()).keys || [], maxAge }
}

let keyFetcher = defaultKeyFetcher
let keyCache = { keys: null, expires: 0, fetchedAt: 0 }

/** Test seam: supply Google's keys without the network. `null` restores the real fetch. */
export function setKeyFetcherForTests(fn) {
  keyFetcher = fn ?? defaultKeyFetcher
  keyCache = { keys: null, expires: 0, fetchedAt: 0 }
}

function bytesFromBase64Url(text) {
  const b64 = text.replace(/-/g, '+').replace(/_/g, '/')
  const binary = atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4))
  return Uint8Array.from(binary, (c) => c.charCodeAt(0))
}

function jsonFromBase64Url(text) {
  return JSON.parse(new TextDecoder().decode(bytesFromBase64Url(text)))
}

async function publicKey(kid, nowMs) {
  const refresh = async () => {
    const { keys, maxAge } = await keyFetcher()
    keyCache = { keys, expires: nowMs + maxAge * 1000, fetchedAt: nowMs }
  }
  if (!keyCache.keys || nowMs >= keyCache.expires) await refresh()
  let jwk = keyCache.keys.find((k) => k.kid === kid)
  // Google rotates its keys; a kid we have not seen may be one it has just added. Refetch,
  // but at most once a minute, so a stream of made-up kids cannot hammer Google.
  if (!jwk && nowMs - keyCache.fetchedAt > 60 * 1000) {
    await refresh()
    jwk = keyCache.keys.find((k) => k.kid === kid)
  }
  if (!jwk) return null
  return crypto.subtle.importKey('jwk', { kty: jwk.kty, n: jwk.n, e: jwk.e, alg: 'RS256', ext: true },
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify'])
}

/**
 * The token's claims if Firebase issued it for this project and it is still valid, else null.
 * Follows Firebase's published verification rules: RS256 with one of Google's current keys,
 * `aud` = project, `iss` = securetoken for the project, a subject, not expired, not issued in
 * the future. It also requires a verified email: the role is set per email.
 */
export async function verifyIdToken(token, projectId, nowMs = Date.now()) {
  try {
    const parts = typeof token === 'string' ? token.split('.') : []
    if (parts.length !== 3) return null
    const header = jsonFromBase64Url(parts[0])
    const claims = jsonFromBase64Url(parts[1])
    if (header.alg !== 'RS256' || typeof header.kid !== 'string') return null
    const key = await publicKey(header.kid, nowMs)
    if (!key) return null
    const signed = new TextEncoder().encode(`${parts[0]}.${parts[1]}`)
    if (!(await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, bytesFromBase64Url(parts[2]), signed))) {
      return null
    }
    const now = Math.floor(nowMs / 1000)
    if (claims.aud !== projectId) return null
    if (claims.iss !== `https://securetoken.google.com/${projectId}`) return null
    if (typeof claims.sub !== 'string' || !claims.sub) return null
    if (!(typeof claims.exp === 'number' && claims.exp > now)) return null
    if (!(typeof claims.iat === 'number' && claims.iat <= now + CLOCK_SKEW_S)) return null
    if (claims.auth_time !== undefined && !(claims.auth_time <= now + CLOCK_SKEW_S)) return null
    if (claims.email_verified !== true) return null
    return claims
  } catch {
    return null
  }
}

function readCookie(request, name) {
  for (const part of (request.headers.get('cookie') || '').split(';')) {
    const [key, ...rest] = part.trim().split('=')
    if (key === name) return rest.join('=')
  }
  return null
}

/**
 * The path as the rules should see it: percent-decoded, repeated slashes collapsed and lower
 * case, so `//telemetry.html`, `/%74elemetry.html` and `/Telemetry.html` cannot slip past a
 * pattern that the file server would still resolve to the same file.
 */
function normalisedPath(url) {
  let path = new URL(url).pathname
  try { path = decodeURIComponent(path) } catch { /* malformed escapes stay as they are */ }
  return path.replace(/\/{2,}/g, '/').toLowerCase()
}

function refuse(status, text) {
  return new Response(text, {
    status,
    headers: { 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow, noarchive' },
  })
}

export default async function middleware(request) {
  const projectId = process.env.FIREBASE_PROJECT_ID
  if (!projectId) return protectionNotConfigured()

  const pathname = normalisedPath(request.url)
  const teamOnly = TEAM_ONLY.some((pattern) => pattern.test(pathname))
  if (!teamOnly && !DATA.test(pathname)) return undefined

  const claims = await verifyIdToken(readCookie(request, SESSION_COOKIE), projectId)
  if (!claims) {
    // A page gets the sign-in screen and comes back afterwards; a file gets a status.
    if (!DATA.test(pathname) && !pathname.startsWith('/assets/')) {
      return new Response(null, {
        status: 302,
        headers: { Location: `/?next=${encodeURIComponent(pathname)}`, 'Cache-Control': 'no-store' },
      })
    }
    return refuse(401, 'Sign-in required')
  }
  if (!ROLES.has(claims.role)) return refuse(403, 'This account has no access')
  if (teamOnly && claims.role !== 'team') return refuse(403, 'Not available for this account')
  return undefined
}

export const config = {
  matcher: '/(.*)',
}
