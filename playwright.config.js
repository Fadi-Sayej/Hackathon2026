import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end tests: a real browser against a real dev server.
 *
 * These are the only tests that exercise what actually ships — routing, the
 * language switch writing to `<html dir>`, CSS that only breaks at a real
 * viewport, and file downloads. They are also the slowest, so the unit,
 * component and use-case suites carry the bulk of the coverage and this layer
 * stays focused on whole journeys.
 *
 * Uses the locally installed Chrome rather than downloading a browser, so the
 * suite runs without a 150MB fetch on a fresh checkout.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'line' : [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chrome', use: { ...devices['Desktop Chrome'], channel: 'chrome' } }],
  /**
   * The BUILT app, not the dev server.
   *
   * This ran `npm run dev` until 2026-09-13, so the only tests that exercise what
   * actually ships were exercising unbundled ESM instead: no chunking, no
   * minification, different module identity. That gap stopped being theoretical
   * when the motion layer moved behind a dynamic import — the thing under test is
   * now a property of the BUILD, and dev mode does not have it.
   *
   * `reuseExistingServer` is off in CI, where a stale server can only mean
   * something went wrong, and on locally, where rebuilding for every spec file
   * would make the suite unusable. Run `npm run build` yourself after changing
   * source if you are iterating locally — preview serves dist/, not src/.
   */
  webServer: {
    command: 'npm run build && npx vite preview --port 5173 --strictPort',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
