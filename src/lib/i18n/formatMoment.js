/**
 * A stored timestamp as the owner reads it: `27 Sept 2026, 06:06`.
 *
 * The engine publishes ISO timestamps with microseconds and an offset, which a phone breaks
 * mid-string. This is the date and the minute, in the reader's own time zone, with the
 * language's month names. Arabic keeps Latin digits, as the order screens' dates do.
 * Anything that is not a date is null, so the page says "none" rather than "Invalid Date".
 * `timeZone` exists for the tests; the page leaves it to the device.
 */
const LOCALE = { ar: 'ar-u-nu-latn', he: 'he-IL', en: 'en-GB' }

export function formatMoment(value, language, timeZone) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return new Intl.DateTimeFormat(LOCALE[language] || LOCALE.en, {
    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone,
  }).format(date)
}

/**
 * A date as the owner reads it: `6 June 2026`. For values dated by day, such as the stock
 * file's `as_of` (F7 AC-120): no time, and read in UTC so no time zone moves it a day.
 */
export function formatDay(value, language) {
  if (!value) return null
  const date = new Date(`${String(value).slice(0, 10)}T00:00:00Z`)
  if (Number.isNaN(date.getTime())) return null
  return new Intl.DateTimeFormat(LOCALE[language] || LOCALE.en, {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  }).format(date)
}
