/**
 * Composes a live marketContext object from real APIs:
 *   - holidays  (Date Nager)
 *   - weather   (Open-Meteo)
 *   - news      (GDELT DOC 2.0)
 *
 * The returned object is shape-compatible with src/data/marketContext.js so
 * the reorderEngine, planogramEngine, and mockAI can consume it without any
 * change. Each remote call is independent and degrades to null on failure.
 *
 * Usage:
 *   const live = await buildLiveMarketContext()
 *   const recs = generateReorderRecommendations(products, live)
 */

import { getHebrewContext } from './hebcal.js'
import { getIslamicContext } from './hijri.js'
import { fetchCurrentWeather } from './weather.js'
import { fetchNewsHeadlines, hasDemandSignal } from './news.js'

const HOT_WEATHER_BOOSTS = {
  'Cold Drinks': 1.2,
  'Energy Drinks': 1.15,
  Water: 1.25,
  'Ice Cream': 1.2,
  Snacks: 1.05,
}

const WEEKEND_BOOSTS = {
  Snacks: 1.1,
  'Energy Drinks': 1.1,
  Cigarettes: 1.08,
  'Cold Drinks': 1.1,
  Chocolate: 1.08,
}

const HOLIDAY_BOOSTS = {
  Snacks: 1.18,
  Chocolate: 1.18,
  'Cold Drinks': 1.15,
  Water: 1.1,
  'Ice Cream': 1.15,
  Bakery: 1.12,
}

export async function buildLiveMarketContext({
  date,
  coords,
  newsQuery,
} = {}) {
  const currentDate = (date ?? new Date()).toString().slice(0, 10)
  const dayOfWeek = new Date(`${currentDate}T00:00:00Z`).getUTCDay()
  // Israel's weekend is Friday–Saturday.
  const weekend = dayOfWeek === 5 || dayOfWeek === 6

  const [hebrew, weather, headlines] = await Promise.all([
    safe(getHebrewContext(currentDate)),
    safe(fetchCurrentWeather(coords)),
    safe(fetchNewsHeadlines({ query: newsQuery, max: 5 })),
  ])
  // Purely arithmetic — no network, so it cannot fail or be slow.
  const islamic = getIslamicContext(currentDate)

  const eventHeadline = headlines ? hasDemandSignal(headlines) : null
  const hebrewHoliday = hebrew?.holidays?.[0] ?? null
  const holidayName =
    hebrewHoliday?.hebrew ??
    hebrewHoliday?.title ??
    (islamic?.isRamadan ? 'רמדאן' : null) ??
    (islamic?.isEidAlFitr ? 'עיד אל-פיטר' : null) ??
    (islamic?.isEidAlAdha ? 'עיד אל-אדחא' : null)

  return {
    currentDate,
    weather: weather?.label ?? null,
    temperatureC: weather?.temperatureC ?? null,
    weekend,
    holiday: Boolean(hebrewHoliday) || Boolean(islamic?.isEidAlFitr || islamic?.isEidAlAdha),
    holidayName,
    upcomingHolidayInDays: hebrew?.chametz?.daysToPesach ?? islamic?.daysToRamadan ?? null,
    localEvent: eventHeadline?.title ?? null,
    season: inferSeason(currentDate),
    newsHeadlines: headlines ?? [],

    // Both calendars, kept whole rather than flattened into one boolean. The
    // demand engine needs the structure — a chametz window and an iftar hour are
    // not the same kind of fact as "today is a holiday".
    hebrew: hebrew ?? null,
    islamic,

    demandSignals: composeDemandSignals({
      weather: weather?.label,
      weekend,
      holiday: Boolean(hebrewHoliday),
    }),
    sources: {
      weather: weather ? 'open-meteo' : null,
      // Was date.nager.at, which returns an EMPTY response for Israel — so the
      // app had no holiday data at all once the country was corrected to IL.
      hebrewCalendar: hebrew?.source ?? null,
      islamicCalendar: islamic?.source ?? null,
      news: headlines && headlines.length ? 'gdelt' : null,
    },
  }
}

/**
 * Translate the live context into the factor map the demand engine consumes.
 * Each entry is an intensity in 0..1 — how strongly the factor is present today —
 * and the archetype supplies the sensitivity. A factor that is absent is simply
 * left out, which is what makes an uncollected parameter vanish without trace.
 */
export function toDemandFactors(context) {
  const factors = {}
  if (!context) return factors

  const temp = context.temperatureC
  if (Number.isFinite(temp)) {
    // 22 °C is unremarkable here; 38 °C is as hot as it gets.
    if (temp > 22) factors.temp_max_c = { value: Math.min(1, (temp - 22) / 16), label: `${Math.round(temp)}°C` }
    if (temp < 16) factors.temp_min_c = { value: Math.min(1, (16 - temp) / 12), label: `${Math.round(temp)}°C` }
  }
  if (context.weather === 'rain') factors.precipitation_mm = { value: 0.8, label: 'مطر' }
  if (context.season) factors.season = { value: 1, label: context.season }

  const day = new Date(`${context.currentDate}T00:00:00Z`).getUTCDay()
  if (day === 4) factors.pre_weekend_thu = { value: 1, label: 'خميس' }
  if (context.weekend) factors.weekend_fri_sat = { value: 1, label: 'عطلة نهاية الأسبوع' }

  const dom = Number(context.currentDate?.slice(8, 10))
  if (dom >= 1 && dom <= 5) factors.month_start = { value: 1, label: 'بداية الشهر' }
  if (dom >= 26) factors.month_end = { value: 1, label: 'نهاية الشهر' }

  if (context.hebrew?.isShabbatEve) factors.shabbat_eve = { value: 1, label: 'ערב שבת' }
  if (context.hebrew?.isErevChag) factors.erev_chag = { value: 1, label: 'ערב חג' }

  const islamic = context.islamic
  if (islamic?.isRamadan) {
    const phase = islamic.ramadanPhase
    if (phase === 'daytime') factors.ramadan_daytime = { value: 1, label: 'رمضان — نهاراً' }
    if (phase === 'iftar' || phase === 'pre_iftar') factors.ramadan_iftar = { value: 1, label: 'رمضان — الإفطار' }
    if (phase === 'suhoor') factors.ramadan_suhoor = { value: 1, label: 'رمضان — السحور' }
    if (islamic.isLastTenNights) factors.ramadan_last_10 = { value: 1, label: 'العشر الأواخر' }
  }
  if (islamic?.isEidEve) factors.eid_eve = { value: 1, label: 'ليلة العيد' }
  if (islamic?.isEidAlFitr) factors.eid_al_fitr = { value: 1, label: 'عيد الفطر' }
  if (islamic?.isEidAlAdha) factors.eid_al_adha = { value: 1, label: 'عيد الأضحى' }

  // Gates carry an action rather than an intensity — they do not scale.
  if (context.hebrew?.chametz) {
    factors.pesach_chametz_window = {
      active: true,
      action: context.hebrew.chametz.action,
      reason: context.hebrew.chametz.reasonAr,
      daysToPesach: context.hebrew.chametz.daysToPesach,
    }
  }
  return factors
}

function composeDemandSignals({ weather, weekend, holiday }) {
  const signals = {}
  if (weather === 'hot') merge(signals, HOT_WEATHER_BOOSTS)
  if (weekend) merge(signals, WEEKEND_BOOSTS)
  if (holiday) merge(signals, HOLIDAY_BOOSTS)
  for (const key of Object.keys(signals)) {
    signals[key] = round(signals[key])
  }
  return signals
}

function merge(target, source) {
  for (const [key, multiplier] of Object.entries(source)) {
    target[key] = (target[key] ?? 1) * multiplier
  }
}

function inferSeason(dateStr) {
  const month = Number(dateStr.slice(5, 7))
  if (month >= 6 && month <= 8) return 'summer'
  if (month >= 9 && month <= 11) return 'autumn'
  if (month === 12 || month <= 2) return 'winter'
  return 'spring'
}

function round(value) {
  return Math.round(value * 100) / 100
}

async function safe(promise) {
  try {
    return await promise
  } catch (error) {
    if (typeof console !== 'undefined') console.warn('liveMarketContext source failed:', error.message)
    return null
  }
}
