import { createContext, useContext } from 'react'

import { ar } from './dictionaries/ar.js'
import { he } from './dictionaries/he.js'
import { en } from './dictionaries/en.js'

/**
 * Three languages, deliberately — the app used to be trilingual by accident.
 *
 * English chrome, two Arabic screens, Hebrew product names, and no way to
 * change any of it. Nobody could read the whole app comfortably.
 *
 * WHAT IS AND IS NOT TRANSLATED
 *   Interface text is translated. **Product names never are.** They arrive from
 *   the YomYom till in Hebrew, the manager searches for them in Hebrew, and the
 *   supplier invoice says the same Hebrew — translating them would break the
 *   only string tying the screen to the physical product. Same for barcodes and
 *   SKU codes.
 *
 * No i18n library: the whole surface is a few hundred keys in three flat
 * dictionaries, and react-i18next would be more dependency than content.
 *
 * The provider component lives in `I18nProvider.jsx` — this file holds only
 * constants, the context and the hooks, so React Fast Refresh keeps working.
 */

export const LANGUAGES = {
  ar: { code: 'ar', dir: 'rtl', label: 'العربية', dict: ar },
  he: { code: 'he', dir: 'rtl', label: 'עברית', dict: he },
  en: { code: 'en', dir: 'ltr', label: 'English', dict: en },
}

export const DEFAULT_LANGUAGE = 'ar'

export const LANGUAGE_STORAGE_KEY = 'smartshelf.language.v1'

export const I18nContext = createContext(null)

/** The stored preference, or Arabic. */
export function readStoredLanguage() {
  try {
    const stored = globalThis.localStorage?.getItem(LANGUAGE_STORAGE_KEY)
    if (stored && LANGUAGES[stored]) return stored
  } catch {
    // No storage (private mode, SSR). Fall through to the default.
  }
  return DEFAULT_LANGUAGE
}

/**
 * Build the lookup function for a language.
 *
 * Falls back to Arabic, then to the key itself. Returning the key rather than an
 * empty string is deliberate: a missing translation shows up as `nav.expiry` on
 * screen, which someone notices and fixes. A blank space is invisible and ships.
 */
export function createTranslator(language) {
  const dict = LANGUAGES[language]?.dict ?? ar
  return (key, values) => {
    const raw = dict[key] ?? ar[key] ?? key
    if (!values) return raw
    return Object.entries(values).reduce(
      (text, [name, replacement]) => text.replaceAll(`{${name}}`, String(replacement)),
      raw,
    )
  }
}

/** Translation function plus the current language and direction. */
export function useI18n() {
  const context = useContext(I18nContext)
  if (!context) {
    // Rendered outside the provider — still show readable text rather than crash.
    return {
      language: DEFAULT_LANGUAGE,
      setLanguage: () => {},
      dir: LANGUAGES[DEFAULT_LANGUAGE].dir,
      t: createTranslator(DEFAULT_LANGUAGE),
    }
  }
  return context
}

/** Shorthand for the common case. */
export function useT() {
  return useI18n().t
}

/**
 * Number formatting that follows the language.
 *
 * Arabic-Indic digits (٠١٢٣) are correct for the Arabic interface and wrong for
 * the other two — a Hebrew or English reader sees them as symbols, not numbers.
 * The planogram screens used them unconditionally because they used to be
 * Arabic-only.
 */
const ARABIC_DIGITS = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩']

export function formatNumber(value, language) {
  const text = String(value)
  if (language !== 'ar') return text
  return text
    .split('')
    .map((char) => ARABIC_DIGITS[Number(char)] ?? char)
    .join('')
}

/** `n` for whole numbers, `d` for one decimal place. Both follow the language. */
export function useNumbers() {
  const { language } = useI18n()
  return {
    n: (value) => formatNumber(value, language),
    d: (value) => formatNumber(Math.round(Number(value) * 10) / 10, language),
    percentSign: language === 'ar' ? '٪' : '%',
  }
}
