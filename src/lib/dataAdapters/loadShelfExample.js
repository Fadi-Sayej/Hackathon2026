/**
 * loadShelfExample.js — the test shop behind Shelf plan's preview (D-31, F12-S1 FR-200).
 *
 * public/examples/shelf-plan-example.json, built by scripts/build_shelf_example.py from Reorder's
 * example shop with a shelf layout added. Only the preview reads it, and only while shelf_plan is
 * unavailable, so it is fetched rather than bundled. Anything but a file that says it is an example
 * is refused, so the store's own artefact can never be shown as one.
 */
export async function loadShelfExample({ fetchImpl = fetch, url = '/examples/shelf-plan-example.json' } = {}) {
  try {
    const response = await fetchImpl(url, { cache: 'no-store' })
    if (!response.ok) return { status: 'error' }
    const example = await response.json()
    return example?.artefact && example?._example ? { status: 'ok', example } : { status: 'error' }
  } catch {
    return { status: 'error' }
  }
}
