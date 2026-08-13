import { render } from '@testing-library/react'

import { I18nProvider } from '../lib/i18n/I18nProvider.jsx'
import { LANGUAGE_STORAGE_KEY } from '../lib/i18n/index.js'

/**
 * Render a component inside the i18n provider, in a chosen language.
 *
 * Every screen reads translations, so rendering one bare throws or silently
 * falls back. The language is seeded through storage rather than a prop because
 * that is exactly how the real app picks it up — the test then exercises the
 * same path a user does.
 */
export function renderWithI18n(ui, { language = 'ar' } = {}) {
  globalThis.localStorage?.setItem(LANGUAGE_STORAGE_KEY, language)
  return render(<I18nProvider>{ui}</I18nProvider>)
}
