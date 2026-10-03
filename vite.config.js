import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readStoreSettings, siteTitlePlugin } from './scripts/store_settings.mjs'

// The address sign-in works at, for the sign-in page's "only works at …" line: the store's own
// `site.address` (configs/store.yaml, ADR-036). Not Vercel's VERCEL_PROJECT_PRODUCTION_URL:
// that is the project's shortest alias, which Firebase does not accept. Vite reads VITE_* from
// process.env.
process.env.VITE_SITE_ADDRESS ??= readStoreSettings().siteAddress

// https://vite.dev/config/
export default defineConfig({
  // ADR-036: the tab title is the store's, from configs/store.yaml.
  plugins: [react(), siteTitlePlugin()],
  build: {
    // Two entry points: the store app (index.html) and the internal pilot
    // telemetry dashboard (telemetry.html, nagham.md B-3). Both are static and
    // ship behind the same sign-in gate, middleware.ts. Vercel serves the built
    // /telemetry.html directly (the filesystem is checked before the SPA
    // rewrite in vercel.json), so no rewrite change is needed.
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL('./index.html', import.meta.url)),
        telemetry: fileURLToPath(new URL('./telemetry.html', import.meta.url)),
      },
    },
  },
})
