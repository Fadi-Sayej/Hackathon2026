import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

/**
 * Two test environments, chosen by filename.
 *
 * Engine tests run in `node` — they are pure functions over data and a DOM would
 * only slow them down. Component and integration tests declare `@vitest-environment
 * jsdom` in a docblock at the top of the file; that per-file directive replaced
 * `environmentMatchGlobs`, which Vitest 4 removed.
 *
 * End-to-end tests are NOT here: they drive a real browser against a running dev
 * server and live under `e2e/`, run by Playwright via `npm run test:e2e`.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'node',
    // scripts/ is included so `npm run doctor` can be tested. It had no test at all
    // until 2026-09-13, which is how its negative-stock check stayed dead — reading a
    // value the adapter had already clamped to zero — while 631 negative rows existed.
    include: ['src/**/*.{test,spec}.{js,jsx}', 'scripts/**/__tests__/*.{test,spec}.mjs'],
    setupFiles: ['src/test/setup.js'],
  },
})
