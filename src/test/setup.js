/**
 * Shared test setup.
 *
 * TWO THINGS, BOTH ABOUT ISOLATION
 *
 * 1. `localStorage` backs persistence, layout, plan versions and shelf photos.
 *    jsdom keeps one per worker, so a plan approved in one test would leak into
 *    the next. Cleared around every test.
 *
 * 2. React Testing Library only auto-cleans when Vitest globals are enabled, and
 *    they are not here — the suite imports `describe`/`it` explicitly. Without
 *    an explicit cleanup, renders accumulate and every `getByRole` throws
 *    "found multiple elements".
 */
import { afterEach, beforeEach } from 'vitest'
import { resetPushForTests, setRemoteLoaderForTests } from '../owner/remoteOwnerState.js'

/*
 * 3. Owner state now writes through to Firestore (#94). No test may load the Firebase SDK
 *    or reach a network by accident, so every test starts "unconfigured" — the same state a
 *    build without VITE_FIREBASE_* is in — and a test that exercises the write-through
 *    installs its own fake with setRemoteLoaderForTests().
 */
const UNCONFIGURED = async () => ({ isConfigured: () => false })

beforeEach(() => {
  globalThis.localStorage?.clear?.()
  setRemoteLoaderForTests(UNCONFIGURED)
  resetPushForTests()
})

afterEach(async () => {
  globalThis.localStorage?.clear?.()
  // Imported lazily so the node-environment engine tests never pull in React DOM.
  if (typeof document !== 'undefined') {
    const { cleanup } = await import('@testing-library/react')
    cleanup()
  }
})
