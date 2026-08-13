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
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
