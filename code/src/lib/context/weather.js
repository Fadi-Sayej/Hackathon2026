/**
 * Weather via Open-Meteo (no API key required).
 * Docs: https://open-meteo.com/en/docs
 */

const BASE_URL = 'https://api.open-meteo.com/v1/forecast'

function readEnv() {
  const env = typeof import.meta !== 'undefined' ? import.meta.env ?? {} : {}
  return {
    lat: env.VITE_WEATHER_LAT ?? '31.95',
    lon: env.VITE_WEATHER_LON ?? '35.93',
  }
}

export async function fetchCurrentWeather({ lat, lon } = {}, options = {}) {
  const env = readEnv()
  const latitude = lat ?? env.lat
  const longitude = lon ?? env.lon
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    current: 'temperature_2m,weather_code,precipitation,wind_speed_10m',
    timezone: 'auto',
  })
  const response = await fetch(`${BASE_URL}?${params.toString()}`, {
    signal: options.signal,
  })
  if (!response.ok) {
    throw new Error(`Weather request failed (${response.status})`)
  }
  const data = await response.json()
  const current = data.current ?? {}
  return {
    temperatureC: current.temperature_2m ?? null,
    weatherCode: current.weather_code ?? null,
    precipitation: current.precipitation ?? null,
    windSpeed: current.wind_speed_10m ?? null,
    observedAt: current.time ?? null,
    label: classifyWeather(current.temperature_2m, current.weather_code, current.precipitation),
  }
}

/**
 * Reduces the WMO weather code + temperature to a coarse label that the
 * recommendation engines and mockAI already understand: hot | warm | mild | cold | rainy | snowy.
 */
export function classifyWeather(tempC, code, precipitation) {
  if (code != null) {
    if (code >= 71 && code <= 77) return 'snowy'
    if (code >= 80 && code <= 82) return 'rainy'
    if (code >= 61 && code <= 67) return 'rainy'
    if (code >= 51 && code <= 57) return 'rainy'
    if (code === 95 || code === 96 || code === 99) return 'rainy'
  }
  if (precipitation != null && precipitation > 0.2) return 'rainy'
  if (tempC == null) return 'mild'
  if (tempC >= 30) return 'hot'
  if (tempC >= 22) return 'warm'
  if (tempC >= 12) return 'mild'
  return 'cold'
}
