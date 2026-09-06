import { getHolidayForDate, getNearbyHoliday } from './holidays.js'
import { fetchNewsHeadlines, hasDemandSignal } from './news.js'
import { fetchCurrentWeather } from './weather.js'
import { fallbackMarketContext } from './fallbackMarketContext.js'

const DEFAULT_TIMEOUT_MS = 2500

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

export async function fetchWeatherContext(location, options = {}) {
  try {
    const weather = await withAbortableTimeout(
      (signal) => fetchCurrentWeather(location, { signal }),
      options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
      'Open-Meteo weather timed out',
    )

    return {
      source: 'live',
      provider: 'Open-Meteo',
      weather: weather.label,
      temperatureC: weather.temperatureC,
      observedAt: weather.observedAt,
    }
  } catch (error) {
    return {
      source: 'static-fallback',
      provider: 'Open-Meteo',
      weather: fallbackMarketContext.weather,
      temperatureC: fallbackMarketContext.temperatureC ?? null,
      error: error.message,
    }
  }
}

export async function fetchHolidayContext(countryCode, options = {}) {
  const currentDate = normalizeDate(options.date ?? fallbackMarketContext.currentDate)

  try {
    const [holidayToday, nearbyHoliday] = await Promise.all([
      withAbortableTimeout(
        (signal) => getHolidayForDate(currentDate, countryCode, { signal }),
        options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
        'Nager.Date holiday lookup timed out',
      ),
      withAbortableTimeout(
        (signal) => getNearbyHoliday(currentDate, countryCode, 2, { signal }),
        options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
        'Nager.Date nearby holiday lookup timed out',
      ),
    ])

    return {
      source: 'live',
      provider: 'Nager.Date',
      holiday: Boolean(holidayToday),
      holidayName: holidayToday?.name ?? nearbyHoliday?.name ?? null,
      upcomingHolidayInDays: holidayToday ? 0 : nearbyHoliday?.diffDays ?? null,
    }
  } catch (error) {
    return {
      source: 'static-fallback',
      provider: 'Nager.Date',
      holiday: fallbackMarketContext.holiday,
      holidayName: fallbackMarketContext.holidayName ?? null,
      upcomingHolidayInDays: fallbackMarketContext.upcomingHolidayInDays ?? null,
      error: error.message,
    }
  }
}

export async function fetchEventContext(query, options = {}) {
  try {
    const headlines = await withAbortableTimeout(
      (signal) => fetchNewsHeadlines({
        query,
        max: options.max ?? 5,
        timespan: options.timespan ?? '24h',
        signal,
      }),
      options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
      'GDELT event lookup timed out',
    )
    const eventHeadline = hasDemandSignal(headlines)

    return {
      source: 'live',
      provider: 'GDELT',
      localEvent: eventHeadline?.title ?? null,
      newsHeadlines: headlines,
    }
  } catch (error) {
    return {
      source: 'static-fallback',
      provider: 'GDELT',
      localEvent: fallbackMarketContext.localEvent,
      newsHeadlines: [],
      error: error.message,
    }
  }
}

export async function buildMarketContext(options = {}) {
  if (!options.enableLive) {
    return fallbackMarketContext
  }

  const currentDate = normalizeDate(options.date ?? fallbackMarketContext.currentDate)
  const weekend = isWeekend(currentDate)
  const [weather, holiday, event] = await Promise.all([
    fetchWeatherContext(options.location, options),
    fetchHolidayContext(options.countryCode, { ...options, date: currentDate }),
    fetchEventContext(options.query, options),
  ])
  const hasAnyLiveSource = [weather, holiday, event].some((signal) => signal.source === 'live')

  return {
    ...fallbackMarketContext,
    currentDate,
    weather: weather.weather,
    temperatureC: weather.temperatureC,
    weekend,
    holiday: holiday.holiday,
    holidayName: holiday.holidayName,
    upcomingHolidayInDays: holiday.upcomingHolidayInDays,
    localEvent: event.localEvent,
    season: inferSeason(currentDate),
    newsHeadlines: event.newsHeadlines,
    demandSignals: composeDemandSignals({
      baseSignals: fallbackMarketContext.demandSignals,
      weather: weather.weather,
      weekend,
      holiday: holiday.holiday || holiday.upcomingHolidayInDays === 0,
    }),
    contextSource: hasAnyLiveSource ? 'live' : 'static-fallback',
    sourceLabel: hasAnyLiveSource ? 'live' : 'static-fallback',
    sourceSummary: hasAnyLiveSource
      ? 'Live free public APIs with static fallback safety.'
      : 'Static fallback context because live sources were unavailable.',
    signalSources: {
      weather: weather.source,
      holiday: holiday.source,
      event: event.source,
    },
  }
}

function composeDemandSignals({ baseSignals, weather, weekend, holiday }) {
  const signals = { ...(baseSignals ?? {}) }
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

function normalizeDate(date) {
  if (date instanceof Date) return date.toISOString().slice(0, 10)
  if (typeof date === 'string') return date.slice(0, 10)
  return new Date().toISOString().slice(0, 10)
}

function isWeekend(date) {
  const dayOfWeek = new Date(`${date}T00:00:00Z`).getUTCDay()
  return dayOfWeek === 5 || dayOfWeek === 6
}

function inferSeason(date) {
  const month = Number(date.slice(5, 7))
  if (month >= 6 && month <= 8) return 'summer'
  if (month >= 9 && month <= 11) return 'autumn'
  if (month === 12 || month <= 2) return 'winter'
  return 'spring'
}

function round(value) {
  return Math.round(value * 100) / 100
}

function withAbortableTimeout(task, timeoutMs, message) {
  const controller = new AbortController()
  const timeoutId = globalThis.setTimeout(() => {
    controller.abort(new Error(message))
  }, timeoutMs)

  return task(controller.signal).finally(() => {
    globalThis.clearTimeout(timeoutId)
  })
}
