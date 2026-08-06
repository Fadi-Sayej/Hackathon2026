import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import middleware from '../../middleware.ts'

// The Basic Auth gate is the only thing between a public URL and a real store's
// cost and margin data (nagham.md B-1). middleware.ts is not covered by eslint
// (the config matches **/*.{js,jsx} only) and had no tests, so its behaviour is
// pinned here. Vite preview does not run Vercel middleware, so this exercises
// the module directly.

const USER = 'yomyom'
const PASS = 's3cret:with:colons'

const request = (authorization) =>
  new Request('https://example.test/', {
    headers: authorization ? { authorization } : {},
  })

const basic = (user, password) => `Basic ${btoa(`${user}:${password}`)}`

beforeEach(() => {
  process.env.BASIC_AUTH_USER = USER
  process.env.BASIC_AUTH_PASSWORD = PASS
})

afterEach(() => {
  delete process.env.BASIC_AUTH_USER
  delete process.env.BASIC_AUTH_PASSWORD
})

describe('access gate', () => {
  it('lets a correct credential through', () => {
    expect(middleware(request(basic(USER, PASS)))).toBeUndefined()
  })

  it('keeps a password containing colons intact', () => {
    // Splitting on every colon would truncate this password, so the correct
    // credential would be rejected.
    expect(middleware(request(basic(USER, PASS)))).toBeUndefined()
  })

  it.each([
    ['no header', undefined],
    ['empty header', ''],
    ['wrong scheme', 'Bearer abc123'],
    ['malformed base64', 'Basic !!!not-base64!!!'],
    ['no colon in payload', `Basic ${btoa('useronly')}`],
  ])('challenges %s with 401', (_name, header) => {
    const res = middleware(request(header))
    expect(res.status).toBe(401)
    expect(res.headers.get('WWW-Authenticate')).toContain('Basic realm=')
    expect(res.headers.get('Cache-Control')).toBe('no-store')
  })

  it.each([
    ['wrong password', () => basic(USER, 'wrong')],
    ['wrong username', () => basic('nope', PASS)],
    ['both wrong', () => basic('nope', 'wrong')],
    ['password as prefix', () => basic(USER, PASS.slice(0, -1))],
    ['username and password swapped', () => basic(PASS, USER)],
  ])('rejects %s with 401', (_name, build) => {
    expect(middleware(request(build())).status).toBe(401)
  })

  it('marks challenges noindex', () => {
    expect(middleware(request()).headers.get('X-Robots-Tag')).toContain('noindex')
  })
})

describe('fails closed when unconfigured', () => {
  it.each([
    ['both missing', {}],
    ['username missing', { BASIC_AUTH_PASSWORD: PASS }],
    ['password missing', { BASIC_AUTH_USER: USER }],
    ['empty username', { BASIC_AUTH_USER: '', BASIC_AUTH_PASSWORD: PASS }],
    ['empty password', { BASIC_AUTH_USER: USER, BASIC_AUTH_PASSWORD: '' }],
  ])('returns 503 instead of serving the app when %s', (_name, env) => {
    delete process.env.BASIC_AUTH_USER
    delete process.env.BASIC_AUTH_PASSWORD
    Object.assign(process.env, env)
    // The dangerous outcome is `undefined` — that would serve the bundle.
    const res = middleware(request(basic(USER, PASS)))
    expect(res).toBeInstanceOf(Response)
    expect(res.status).toBe(503)
    expect(res.headers.get('Cache-Control')).toBe('no-store')
  })
})
