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
