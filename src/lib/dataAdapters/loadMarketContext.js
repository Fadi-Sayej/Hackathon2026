// Loads the market context the pipeline committed to public/data/market-context.json
// (written by src/context/build.py).
//
// This replaces fetching weather and the calendars in the browser. Fetching at render
// time meant the Python recommender could not see any of it, two page loads could
// disagree about the same day, and the inputs to a decision were never written down.
// The pipeline now fetches once and both sides read the same artifact.
//
// Returns null when the artifact is absent, so the caller can fall back to the older
// live-fetch path rather than showing a confidently wrong empty context.

export async function loadMarketContext() {
  const url = `${import.meta.env.BASE_URL}data/market-context.json`
  try {
    const response = await fetch(url, { cache: 'no-store' })
    if (!response.ok) return null
    const data = await response.json()
    if (!data || typeof data !== 'object' || !data.date) return null
    return data
  } catch {
    return null
  }
}

/** Shape the artifact into the flat context the demand engines already consume. */
export function toEngineContext(artifact, fallback) {
  if (!artifact) return fallback

  const islamic = artifact.islamic ?? null
  const hebrew = artifact.hebrew ?? null
  const holidayToday = hebrew?.holidays?.[0] ?? null
  const inIslamicEvent = Boolean(islamic?.isRamadan || islamic?.isEidAlFitr || islamic?.isEidAlAdha)

  return {
    ...fallback,
    currentDate: artifact.date,
    weather: artifact.weather?.label ?? fallback.weather,
    temperatureC: artifact.weather?.temperatureC ?? null,
    weekend: [4, 5].includes(new Date(`${artifact.date}T00:00:00Z`).getUTCDay()),
    holiday: Boolean(holidayToday) || inIslamicEvent,
    holidayName: holidayToday?.hebrew ?? holidayToday?.title ?? (islamic?.isRamadan ? 'رمضان' : null),
    hebrew,
    islamic,
    // Which gate the pipeline decided applies today. The UI renders this; it does
    // not recompute it.
    islamicPhase: islamic?.phase ?? null,
    chametz: hebrew?.chametz ?? null,
    // The multipliers the pipeline decided, keyed on real catalog categories. The
    // previous table was keyed in English ('Cold Drinks', 'Snacks') while every
    // category in the catalog is Hebrew, so it silently matched nothing and every
    // multiplier was 1. reorderEngine.js renders this; it no longer decides it.
    demandSignals: artifact.demandSignals ?? {},
    // The shelf-life table and the owner's answers must reach the engine, not just
    // the browser. Omitting them here silently disabled the perishability cap in the
    // running app — the croissant ordered 51 units instead of 16 — while every unit
    // test passed, because those hand the table straight to computeMetrics and never
    // cross this boundary.
    shelfLife: artifact.shelfLife ?? null,
    ownerAnswers: artifact.ownerAnswers ?? {},
    demandBasis: artifact.demandBasis ?? {},
    activeReasons: artifact.activeReasons ?? [],
    sourceLabel: artifact.status === 'ok' ? 'live' : artifact.status,
    provenance: artifact.sources ?? null,
    generatedAt: artifact.generatedAt ?? null,
  }
}
