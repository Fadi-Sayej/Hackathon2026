/**
 * Public holidays via Date Nager.
 * Docs: https://date.nager.at/Api
 *
 * Example URL: https://date.nager.at/api/v3/publicholidays/2026/AT
 */

const BASE_URL = 'https://date.nager.at/api/v3'

function readEnv() {
  const env = typeof import.meta !== 'undefined' ? import.meta.env ?? {} : {}
  return {
    country: env.VITE_HOLIDAY_COUNTRY || 'AT',
  }
}

export async function fetchPublicHolidays(year, countryCode, options = {}) {
  const code = countryCode || readEnv().country
  const url = `${BASE_URL}/publicholidays/${year}/${encodeURIComponent(code)}`
  const response = await fetch(url, {
    signal: options.signal,
  })
  if (!response.ok) {
    throw new Error(`Holidays request failed (${response.status}) for ${code} ${year}`)
  }
  return response.json()
}

/**
 * Returns the holiday object that matches the reference date, or null.
 * Compares on yyyy-mm-dd so timezone drift does not matter.
 */
export async function getHolidayForDate(date, countryCode, options = {}) {
  const reference = normalizeDate(date)
  if (!reference) return null
  const year = Number(reference.slice(0, 4))
  let holidays
  try {
    holidays = await fetchPublicHolidays(year, countryCode, options)
  } catch {
    return null
  }
  return holidays.find((entry) => entry.date === reference) ?? null
}

/**
 * Returns true if a holiday falls within `windowDays` (forward or backward)
 * of the reference date. Used to bump market-demand signals.
 */
export async function getNearbyHoliday(date, countryCode, windowDays = 2, options = {}) {
  const reference = normalizeDate(date)
  if (!reference) return null
  const refTime = new Date(`${reference}T00:00:00Z`).getTime()
  const year = Number(reference.slice(0, 4))
  let holidays
  try {
    holidays = await fetchPublicHolidays(year, countryCode, options)
  } catch {
    return null
  }
  for (const entry of holidays) {
    const t = new Date(`${entry.date}T00:00:00Z`).getTime()
    const diffDays = Math.abs(t - refTime) / 86_400_000
    if (diffDays <= windowDays) {
      return { ...entry, diffDays: Math.round(diffDays) }
    }
  }
  return null
}

function normalizeDate(date) {
  if (!date) return null
  if (date instanceof Date) {
    return date.toISOString().slice(0, 10)
  }
  if (typeof date === 'string') {
    return date.slice(0, 10)
  }
  return null
}
