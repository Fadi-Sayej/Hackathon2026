/**
 * ADR-036: the browser has no default store. `STORE_ID` fell back to 'yomyom-kafr-qasim'
 * when VITE_STORE_ID was unset, so a copy built without one would have written its owner's
 * decisions under another store's root. Unset, it now stays on this device's storage.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

const KEYS = { VITE_FIREBASE_API_KEY: 'k', VITE_FIREBASE_PROJECT_ID: 'p', VITE_FIREBASE_APP_ID: 'a' }

async function load(env) {
  vi.resetModules()
  for (const [key, value] of Object.entries(env)) vi.stubEnv(key, value)
  return import('../firebase.js')
}

afterEach(() => vi.unstubAllEnvs())

describe('the store the browser writes under', () => {
  it('is the deployment\'s VITE_STORE_ID', async () => {
    const firebase = await load({ ...KEYS, VITE_STORE_ID: 'store-a' })
    expect(firebase.STORE_ID).toBe('store-a')
    expect(firebase.isFirebaseConfigured()).toBe(true)
  })

  it('is no store at all when VITE_STORE_ID is unset, and nothing is written remotely', async () => {
    const firebase = await load({ ...KEYS, VITE_STORE_ID: '' })
    expect(firebase.STORE_ID).toBe('')
    expect(firebase.isFirebaseConfigured()).toBe(false)
  })
})
