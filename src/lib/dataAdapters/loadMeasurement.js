// The pilot measurement, public/data/measurement.json (F13-S1, ADR-023). Its own file beside
// dashboard.json, so the edge gate keeps it from the owner (ADR-029 Decision 6); only the
// team's measurement page reads it.

const MEASUREMENT_URL = '/data/measurement.json'

export async function loadMeasurement(fetchImpl = fetch) {
  try {
    const response = await fetchImpl(MEASUREMENT_URL, { cache: 'no-store' })
    // Not published yet: the nightly writes it from the run after this page ships (FR-142).
    // vercel.json rewrites an unmatched path to index.html, so a missing file answers 200 with
    // HTML rather than 404; both mean the same thing.
    if (response.status === 404) return { status: 'missing' }
    if (!response.ok) return { status: 'unreachable', reason: `HTTP ${response.status}` }
    if (!(response.headers?.get('content-type') || '').includes('json')) return { status: 'missing' }
    return { status: 'ok', body: await response.json() }
  } catch (error) {
    return { status: 'unreachable', reason: error?.message || 'fetch failed' }
  }
}
