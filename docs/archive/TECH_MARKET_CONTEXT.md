> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# SmartShelf AI Market Context Adapter

Sprint C3 prepares live market signals while preserving the local-first demo.

## Default Behavior

The app defaults to `fallbackMarketContext`, which wraps `src/data/marketContext.js` and labels the source as `mock`.

This keeps the hackathon demo safe when offline, on weak Wi-Fi, or when free public APIs are slow.

## Optional Live Mode

Set this environment variable to opt into live free signals:

```txt
VITE_ENABLE_LIVE_MARKET_CONTEXT=true
```

Optional configuration:

```txt
VITE_WEATHER_LAT=31.95
VITE_WEATHER_LON=35.93
VITE_HOLIDAY_COUNTRY=JO
VITE_NEWS_QUERY=Jordan football retail
```

No API keys are required.

## Public Sources

- Weather: Open-Meteo
- Holidays: Nager.Date
- Local events/news: GDELT DOC 2.0

## Adapter API

`src/lib/context/marketContextAdapter.js` exports:

```js
fetchWeatherContext(location)
fetchHolidayContext(countryCode)
fetchEventContext(query)
buildMarketContext(options)
```

`buildMarketContext()` returns a shape-compatible context object for the existing recommendation, planogram, and mock AI engines.

## Source Labels

The adapter uses these labels:

- `live`: at least one free public API returned usable data.
- `static-fallback`: live mode was requested but a source failed or timed out.
- `mock`: local static demo context.

The dashboard market panel shows whether signals are live or mock and also lists per-signal source labels.

## Failure Handling

Each public API call is wrapped with a timeout. Failures never block the UI. If an API fails, that signal falls back to the local static context.

## Not Included In C3

- No Gemini.
- No paid APIs.
- No secrets.
- No backend proxy.
- No persistence.
