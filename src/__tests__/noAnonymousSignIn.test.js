import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { ensureAuthForMode } from '../firebase.js'

/**
 * Anonymous sign-in was disabled in the Firebase project on 2026-09-26, and the role rules
 * (ADR-029) refuse any account without a role. The client code that still tried it was removed
 * on 2026-10-01. Nothing shipped may call it again: it would fail, and print a warning,
 * on every page load.
 */
function sources(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) return name === '__tests__' ? [] : sources(path)
    return /\.(js|jsx|mjs)$/.test(name) ? [path] : []
  })
}

describe('no anonymous sign-in', () => {
  it('is called nowhere in the app or its scripts', () => {
    const callers = [...sources('src'), ...sources('scripts')]
      .filter((path) => readFileSync(path, 'utf8').includes('signInAnonymously'))
    expect(callers).toEqual([])
  })

  it('leaves a build without sign-in with no account, so owner state stays in the browser', async () => {
    expect(await ensureAuthForMode()).toBeNull()
  })
})
