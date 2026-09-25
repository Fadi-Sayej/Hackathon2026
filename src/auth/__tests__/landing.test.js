import { describe, expect, it } from 'vitest'

import { landingFor, safeNext, TEAM_HOME } from '../landing.js'
import { clearedSessionCookie, sessionCookie } from '../cookie.js'

// ADR-029 §3: a team account lands on the telemetry page, an owner on his app, and a
// `next` left by the gate is followed only when it is one of our own pages.

describe('where a signed-in account lands', () => {
  it('sends the team to the telemetry page and the owner to his app', () => {
    expect(landingFor('team', null)).toBe(TEAM_HOME)
    expect(landingFor('owner', null)).toBe('/')
  })

  it('follows the page the gate sent them from', () => {
    expect(landingFor('team', '/')).toBe('/')
    expect(landingFor('team', TEAM_HOME)).toBe(TEAM_HOME)
  })

  it('never sends the owner to the page the gate refuses him', () => {
    expect(landingFor('owner', TEAM_HOME)).toBe('/')
  })

  it.each(['//evil.test', 'https://evil.test/', '/data/dashboard.json', 'javascript:alert(1)', '', null])(
    'ignores an unsafe next (%s)', (next) => {
      expect(safeNext(next)).toBeNull()
    })
})

describe('the session cookie', () => {
  it('carries the token for an hour, to our own pages, Secure over https', () => {
    expect(sessionCookie('abc', { secure: true })).toBe('__session=abc; Path=/; Max-Age=3600; SameSite=Lax; Secure')
    expect(sessionCookie('abc', { secure: false })).toBe('__session=abc; Path=/; Max-Age=3600; SameSite=Lax')
  })

  it('is cleared, not left to expire, on sign-out', () => {
    expect(clearedSessionCookie()).toBe('__session=; Path=/; Max-Age=0; SameSite=Lax')
  })
})
