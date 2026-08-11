/**
 * Hebrew calendar via Hebcal. Free, no API key, no account.
 * Docs: https://www.hebcal.com/home/195/jewish-calendar-rest-api
 *
 * WHY THIS REPLACES holidays.js (Date Nager)
 *   Date Nager returns an EMPTY response for Israel — verified against
 *   /api/v3/PublicHolidays/2027/IL. Setting VITE_HOLIDAY_COUNTRY from AT to IL
 *   therefore did not fix the source, it silently emptied it: the app went from
 *   Austrian holidays to no holidays at all.
 *
 *   Even where Date Nager has data it only carries civil public holidays. It has
 *   no erev chag, no fast days, and above all no chametz window — which is the
 *   single highest-value gate in the whole parameter registry.
 *
 * NO LLM IS INVOLVED HERE. This is a calendar lookup with a deterministic answer.
 */

const BASE_URL = 'https://www.hebcal.com/hebcal'

// A chametz product stops being sellable at Pesach, so the useful signal is not
// the festival date itself but the run-up to it. These offsets define the windows
// the engine gates on; they are business decisions, not halachic rulings.
export const CHAMETZ_STOP_REORDER_DAYS = 30
export const CHAMETZ_CLEAR_STOCK_DAYS = 14
export const PESACH_LENGTH_DAYS = 8

const DAY_MS = 86_400_000

function toISODate(value) {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date.toISOString().slice(0, 10)
}

function daysBetween(fromISO, toISO) {
  return Math.round((Date.parse(`${toISO}T00:00:00Z`) - Date.parse(`${fromISO}T00:00:00Z`)) / DAY_MS)
}

/**
 * Fetch a year of Hebrew-calendar events.
 * `maj` major holidays, `min` minor, `mod` modern, `mf` minor fasts.
 */
export async function fetchHebrewYear(year, options = {}) {
  const params = new URLSearchParams({
    v: '1',
    cfg: 'json',
    year: String(year),
    month: 'x',
    maj: 'on',
    min: 'on',
    mod: 'on',
    mf: 'on',
    geo: 'none',
  })
  const response = await fetch(`${BASE_URL}?${params}`, { signal: options.signal })
  if (!response.ok) {
    throw new Error(`Hebcal request failed (${response.status}) for ${year}`)
  }
  const payload = await response.json()
  return Array.isArray(payload?.items) ? payload.items : []
}

/**
 * The first day of Pesach for a given year, as an ISO date, or null.
 * Matches on the untranslated title so a Hebrew-locale response cannot break it.
 */
export function findPesachStart(items) {
  const first = items.find((item) => /^Pesach I$/i.test(item?.title ?? ''))
    ?? items.find((item) => /^Pesach\b/i.test(item?.title ?? '') && !/Erev/i.test(item.title))
  return toISODate(first?.date)
}

/**
 * Where today sits relative to Pesach, and what that means for chametz.
 *
 * Returns null when Pesach is not within reach of any window, so the caller can
 * treat "no gate" as the default rather than having to check a phase string.
 */
export function chametzWindow(todayISO, pesachStartISO) {
  if (!todayISO || !pesachStartISO) return null
  const delta = daysBetween(todayISO, pesachStartISO) // >0 means Pesach is ahead

  if (delta <= 0 && delta > -PESACH_LENGTH_DAYS) {
    return { phase: 'pesach', action: 'BLOCK', daysToPesach: delta,
             reasonHe: 'אסור למכירה', reasonAr: 'ممنوع البيع' }
  }
  if (delta > 0 && delta <= CHAMETZ_CLEAR_STOCK_DAYS) {
    return { phase: 'clear_stock', action: 'CLEAR_STOCK', daysToPesach: delta,
             reasonHe: 'צריך למכור לפני החג', reasonAr: 'صفِّ المخزون قبل العيد' }
  }
  if (delta > CHAMETZ_CLEAR_STOCK_DAYS && delta <= CHAMETZ_STOP_REORDER_DAYS) {
    return { phase: 'stop_reorder', action: 'STOP_REORDER', daysToPesach: delta,
             reasonHe: 'לא להזמין חמץ — פסח מתקרב', reasonAr: 'لا تطلب الحمץ — الفصح يقترب' }
  }
  return null
}

const EREV_PATTERN = /^Erev\b/i
const FAST_PATTERN = /(Tzom|Fast of|Ta'anit|Yom Kippur)/i

/**
 * Everything the demand engine needs from the Hebrew calendar for one date.
 * Degrades to a null-filled shape on failure so a dead API cannot take the app
 * down — a missing factor must vanish without trace, never throw.
 */
export async function getHebrewContext(date, options = {}) {
  const todayISO = toISODate(date ?? new Date())
  const empty = {
    date: todayISO, holidays: [], isErevChag: false, isFastDay: false,
    isShabbatEve: false, chametz: null, pesachStart: null, source: null,
  }
  if (!todayISO) return empty

  const year = Number(todayISO.slice(0, 4))
  let items
  try {
    items = await fetchHebrewYear(year, options)
    // Pesach falls in spring; late in the year the next one is in the year after.
    const pesachStart = findPesachStart(items)
    let effectivePesach = pesachStart
    if (pesachStart && daysBetween(todayISO, pesachStart) < -PESACH_LENGTH_DAYS) {
      effectivePesach = findPesachStart(await fetchHebrewYear(year + 1, options)) ?? pesachStart
    }

    const todays = items.filter((item) => toISODate(item?.date) === todayISO)
    // Friday is the eve of Shabbat; UTC is fine here because we compare dates only.
    const weekday = new Date(`${todayISO}T00:00:00Z`).getUTCDay()

    return {
      date: todayISO,
      holidays: todays.map((item) => ({ title: item.title, hebrew: item.hebrew, category: item.category })),
      isErevChag: todays.some((item) => EREV_PATTERN.test(item?.title ?? '')),
      isFastDay: todays.some((item) => FAST_PATTERN.test(item?.title ?? '')),
      isShabbatEve: weekday === 5,
      chametz: chametzWindow(todayISO, effectivePesach),
      pesachStart: effectivePesach,
      source: 'hebcal',
    }
  } catch (error) {
    if (typeof console !== 'undefined') console.warn('hebcal failed:', error.message)
    return empty
  }
}
