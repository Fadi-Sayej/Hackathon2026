import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', '.claude/**', 'coverage', 'playwright-report', 'test-results']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
  {
    // Tests, the Playwright suite and its config run under Node, not the browser.
    files: [
      'src/**/__tests__/**/*.{js,jsx}',
      'src/test/**/*.{js,jsx}',
      'e2e/**/*.{js,jsx}',
      '*.config.js',
    ],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
  },
])
