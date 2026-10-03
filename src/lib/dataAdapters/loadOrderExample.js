/**
 * loadOrderExample.js — the test shop behind the order pages' preview (D-29).
 *
 * public/examples/order-example.json, built by scripts/build_order_example.py from the order
 * probe's fixture world. Only the preview reads it, and only when asked, so it is fetched
 * rather than bundled. Anything but a file that says it is an example is refused.
 */
export async function loadOrderExample({ fetchImpl = fetch, url = '/examples/order-example.json' } = {}) {
  try {
    const response = await fetchImpl(url, { cache: 'no-store' })
    if (!response.ok) return { status: 'error' }
    const example = await response.json()
    return example?.artefact && example?._example ? { status: 'ok', example } : { status: 'error' }
  } catch {
    return { status: 'error' }
  }
}
