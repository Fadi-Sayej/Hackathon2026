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

import { getHolidayForDate, getNearbyHoliday } from './holidays.js'
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
  countryCode,
  coords,
  newsQuery,
} = {}) {
  const currentDate = (date ?? new Date()).toString().slice(0, 10)
  const dayOfWeek = new Date(`${currentDate}T00:00:00Z`).getUTCDay()
  const weekend = dayOfWeek === 5 || dayOfWeek === 6

  const [holidayToday, nearbyHoliday, weather, headlines] = await Promise.all([
    safe(getHolidayForDate(currentDate, countryCode)),
    safe(getNearbyHoliday(currentDate, countryCode, 2)),
    safe(fetchCurrentWeather(coords)),
    safe(fetchNewsHeadlines({ query: newsQuery, max: 5 })),
  ])

  const eventHeadline = headlines ? hasDemandSignal(headlines) : null

  const context = {
    currentDate,
    weather: weather?.label ?? null,
    temperatureC: weather?.temperatureC ?? null,
    weekend,
    holiday: Boolean(holidayToday),
    holidayName: holidayToday?.name ?? nearbyHoliday?.name ?? null,
    upcomingHolidayInDays: holidayToday ? 0 : nearbyHoliday?.diffNumber ?? nearbyHoliday?.diffDays ?? null,
    localEvent: eventHeadline?.title ?? null,
    season: inferSeason(currentDate),
    newsHeadlines: headlines ?? [],
    demandSignals: composeDemandSignals({
      weather: weather?.label,
      weekend,
      holiday: Boolean(holidayToday || nearbyHoliday),
    }),
    sources: {
      weather: weather ? 'open-meteo' : null,
      holidays: holidayToday || nearbyHoliday ? 'date.nager.at' : null,
      news: headlines && headlines.length ? 'gdelt' : null,
    },
  }

  return context
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
