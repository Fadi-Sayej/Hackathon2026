import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  I18nContext,
  LANGUAGES,
  LANGUAGE_STORAGE_KEY,
  createTranslator,
  readStoredLanguage,
} from './index.js'

/**
 * Holds the chosen language and keeps the document in sync with it.
 *
 * Only a component lives in this file — constants and hooks are in `index.js`,
 * because React Fast Refresh breaks when one module exports both.
 */
export function I18nProvider({ children }) {
  const [language, setLanguageState] = useState(readStoredLanguage)

  // The document itself has to carry language and direction. CSS alone cannot
  // fix bidirectional text, form controls or scrollbar side — the browser needs
  // `dir` on <html>.
  useEffect(() => {
    const root = document?.documentElement
    if (!root) return
    root.lang = language
    root.dir = LANGUAGES[language].dir
  }, [language])

  const setLanguage = useCallback((next) => {
    if (!LANGUAGES[next]) return
    setLanguageState(next)
    try {
      globalThis.localStorage?.setItem(LANGUAGE_STORAGE_KEY, next)
    } catch {
      // The preference is lost on reload; the app still works.
    }
  }, [])

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      dir: LANGUAGES[language].dir,
      t: createTranslator(language),
    }),
    [language, setLanguage],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}
