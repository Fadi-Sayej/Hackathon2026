import { afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest'
import middleware, { setKeyFetcherForTests, verifyIdToken } from '../../middleware.ts'

// ADR-029: the edge gate verifies a Firebase ID token and its `role` claim on every request.
// It is the only gate: Basic Auth was removed on 2026-09-26, once sign-in had been live in
// production. middleware.ts is not covered by eslint (the config matches **/*.{js,jsx} only),
// and Vite does not run Vercel middleware, so its behaviour is pinned here, by importing the
// module directly. These tests sign real RS256 tokens with a throwaway
// key pair, so the signature check is exercised, not mocked: a forged key, `alg: none`, an
// expired token, the wrong project and an unverified email must all fail, and the
// owner/team split must hold on every path the ADR's table names.

const PROJECT = 'test-project'
const NOW = Math.floor(Date.now() / 1000)
let signer
let otherSigner
let jwks
let fetches

const b64url = (bytes) => btoa(String.fromCharCode(...new Uint8Array(bytes)))
  .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
const enc = (obj) => b64url(new TextEncoder().encode(JSON.stringify(obj)))

async function keyPair(kid) {
  const pair = await crypto.subtle.generateKey(
    { name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' },
    true, ['sign', 'verify'])
  const jwk = { ...(await crypto.subtle.exportKey('jwk', pair.publicKey)), kid, alg: 'RS256', use: 'sig' }
  return { kid, privateKey: pair.privateKey, jwk }
}

async function sign(key, payload, header = {}) {
  const head = enc({ alg: 'RS256', typ: 'JWT', kid: key.kid, ...header })
  const body = enc(payload)
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', key.privateKey, new TextEncoder().encode(`${head}.${body}`))
  return `${head}.${body}.${b64url(sig)}`
}

const claims = (over = {}) => ({
  iss: `https://securetoken.google.com/${PROJECT}`, aud: PROJECT, sub: 'uid-1',
  iat: NOW - 60, exp: NOW + 3000, auth_time: NOW - 60, email_verified: true, ...over,
})

const req = (path, token, extraCookie = '') => new Request(`https://pilot.test${path}`, {
  headers: token ? { cookie: `${extraCookie}__session=${token}` } : {},
})

beforeAll(async () => {
  signer = await keyPair('k1')
  otherSigner = await keyPair('k1') // same kid, different key: a forgery
  jwks = [signer.jwk]
})

beforeEach(() => {
  process.env.FIREBASE_PROJECT_ID = PROJECT
  fetches = 0
  setKeyFetcherForTests(async () => { fetches += 1; return { keys: jwks, maxAge: 3600 } })
})

afterEach(() => {
  delete process.env.FIREBASE_PROJECT_ID
  setKeyFetcherForTests(null)
})

describe('verifyIdToken', () => {
  it('accepts a token Google would issue for this project', async () => {
    expect(await verifyIdToken(await sign(signer, claims({ role: 'owner' })), PROJECT)).toMatchObject({ role: 'owner' })
  })

  it.each([
    ['a forged signature', async () => sign(otherSigner, claims({ role: 'team' }))],
    ['alg none', async () => `${enc({ alg: 'none', kid: 'k1' })}.${enc(claims({ role: 'team' }))}.`],
    ['an unknown key id', async () => sign(signer, claims({ role: 'team' }), { kid: 'nope' })],
    ['an expired token', async () => sign(signer, claims({ role: 'team', exp: NOW - 1 }))],
    ['another project', async () => sign(signer, claims({ role: 'team', aud: 'other' }))],
    ['another issuer', async () => sign(signer, claims({ role: 'team', iss: 'https://evil.test' }))],
    ['an unverified email', async () => sign(signer, claims({ role: 'team', email_verified: false }))],
    ['a token issued in the future', async () => sign(signer, claims({ role: 'team', iat: NOW + 3600 }))],
    ['no subject', async () => sign(signer, claims({ role: 'team', sub: '' }))],
    ['garbage', async () => 'not.a.token'],
  ])('refuses %s', async (_name, make) => {
    expect(await verifyIdToken(await make(), PROJECT)).toBeNull()
  })

  it('fetches Google\'s keys once and caches them', async () => {
    const token = await sign(signer, claims({ role: 'owner' }))
    await verifyIdToken(token, PROJECT)
    await verifyIdToken(token, PROJECT)
    expect(fetches).toBe(1)
  })
})

describe('the gate, by path and role', () => {
  const owner = () => sign(signer, claims({ role: 'owner' }))
  const team = () => sign(signer, claims({ role: 'team' }))
  const noRole = () => sign(signer, claims())

  it('fails closed with 503 when the project is not configured', async () => {
    delete process.env.FIREBASE_PROJECT_ID
    expect((await middleware(req('/data/dashboard.json'))).status).toBe(503)
  })

  it.each(['/', '/assets/main-abc.js', '/favicon.svg'])('serves the app shell at %s without a sign-in', async (path) => {
    expect(await middleware(req(path))).toBeUndefined()
  })

  it.each(['/data/dashboard.json', '/data/catalogue.json'])('refuses %s with 401 when signed out', async (path) => {
    expect((await middleware(req(path))).status).toBe(401)
  })

  it.each(['/data/dashboard.json', '/data/catalogue.json'])('serves %s to both roles', async (path) => {
    expect(await middleware(req(path, await owner()))).toBeUndefined()
    expect(await middleware(req(path, await team()))).toBeUndefined()
  })

  it('refuses the data to an account with no role (403)', async () => {
    expect((await middleware(req('/data/dashboard.json', await noRole()))).status).toBe(403)
  })

  // ADR-040 keeps a product's picture, cut from the store's own shelf photos, at
  // public/store/shelf-pictures/. It is store data like /data/: any role may see it, and nobody
  // signed out. Until 2026-10-06 the gate let /store/ through, unchecked.
  it('refuses a store picture to a visitor who is not signed in (401, not a redirect)', async () => {
    const res = await middleware(req('/store/shelf-pictures/7290000467511.jpg'))
    expect(res.status).toBe(401)
    expect(res.headers.get('cache-control')).toBe('no-store')
  })

  it('serves a store picture to the owner and the team, and refuses an account with no role', async () => {
    const path = '/store/shelf-pictures/7290000467511.jpg'
    expect(await middleware(req(path, await owner()))).toBeUndefined()
    expect(await middleware(req(path, await team()))).toBeUndefined()
    expect((await middleware(req(path, await noRole()))).status).toBe(403)
  })

  it.each(['//store/shelf-pictures/a.jpg', '/%73tore/shelf-pictures/a.jpg', '/STORE/shelf-pictures/a.jpg'])(
    'does not let %s past a signed-out visitor', async (path) => {
      expect((await middleware(req(path))).status).toBe(401)
    })

  it.each(['/telemetry.html', '/assets/telemetry-9f8e.js', '/data/measurement.json', '/data/operational.json'])(
    'serves %s to the team and refuses it to the owner', async (path) => {
      expect(await middleware(req(path, await team()))).toBeUndefined()
      expect((await middleware(req(path, await owner()))).status).toBe(403)
    })

  it.each(['//telemetry.html', '/%74elemetry.html', '/Telemetry.html', '/DATA/measurement.json', '/data//operational.json'])(
    'does not let %s past the owner', async (path) => {
      expect((await middleware(req(path, await owner()))).status).toBe(403)
    })

  it('sends a signed-out visitor of the telemetry page to sign-in, and back after', async () => {
    const res = await middleware(req('/telemetry.html'))
    expect(res.status).toBe(302)
    expect(res.headers.get('location')).toBe('/?next=%2Ftelemetry.html')
  })

  it('reads the session cookie among others', async () => {
    expect(await middleware(req('/data/dashboard.json', await owner(), 'theme=dark; '))).toBeUndefined()
  })

  it('never caches or indexes a refusal', async () => {
    const res = await middleware(req('/data/dashboard.json'))
    expect(res.headers.get('cache-control')).toBe('no-store')
    expect(res.headers.get('x-robots-tag')).toContain('noindex')
  })

  it('opens nothing to the old shared password, even with its variables still set', async () => {
    process.env.BASIC_AUTH_USER = 'u'
    process.env.BASIC_AUTH_PASSWORD = 'p'
    try {
      const res = await middleware(new Request('https://pilot.test/data/dashboard.json', {
        headers: { authorization: `Basic ${btoa('u:p')}` },
      }))
      expect(res.status).toBe(401)
      expect(res.headers.get('www-authenticate')).toBeNull()
    } finally {
      delete process.env.BASIC_AUTH_USER
      delete process.env.BASIC_AUTH_PASSWORD
    }
  })
})

describe('key rotation', () => {
  it('refetches Google\'s keys for an unseen kid once the cached copy is over a minute old', async () => {
    const t0 = Date.now()
    const oldToken = await sign(signer, claims({ role: 'owner' }))
    await verifyIdToken(oldToken, PROJECT, t0)
    const rotated = await keyPair('k2')
    jwks = [signer.jwk, rotated.jwk]
    const newToken = await sign(rotated, claims({ role: 'owner' }))
    expect(await verifyIdToken(newToken, PROJECT, t0 + 5_000)).toBeNull() // too soon: no refetch
    expect(await verifyIdToken(newToken, PROJECT, t0 + 90_000)).toMatchObject({ role: 'owner' })
    expect(fetches).toBe(2)
    jwks = [signer.jwk]
  })
})
