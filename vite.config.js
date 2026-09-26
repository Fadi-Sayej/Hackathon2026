import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
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
