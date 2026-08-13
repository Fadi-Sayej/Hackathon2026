/**
 * Arabic-Indic numeral formatting for the planogram screens.
 *
 * The two planogram pages are the only Arabic/RTL surface in an otherwise
 * English app, so the digit conversion lives here rather than in a global i18n
 * layer. Everything else in `src/` keeps Western digits.
 */

const ARABIC_DIGITS = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩']

/** Convert Western digits in a value to Arabic-Indic digits. */
export function ar(value) {
  return String(value)
    .split('')
    .map((char) => ARABIC_DIGITS[Number(char)] ?? char)
    .join('')
}

/** Round to one decimal place, then render in Arabic-Indic digits. */
export function arDecimal(value) {
  return ar(Math.round(Number(value) * 10) / 10)
}

/**
 * Darken a #rrggbb colour by a factor. Used to derive bottle caps and necks
 * from a single body colour so a package reads as one object.
 */
export function shade(hex, factor) {
  const parsed = Number.parseInt(String(hex).slice(1), 16)
  const channels = [(parsed >> 16) & 255, (parsed >> 8) & 255, parsed & 255].map((value) =>
    Math.round(value * factor),
  )
  return `rgb(${channels.join(',')})`
}
