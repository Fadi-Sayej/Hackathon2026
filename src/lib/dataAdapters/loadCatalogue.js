/**
 * loadCatalogue — read the product catalogue published beside the artefact (ADR-024).
 *
 * The same contract as `loadDashboard`: never throws, never falls back, and an unreadable
 * file is a state the UI renders rather than a reason to show something older.
 *
 * It is a SEPARATE fetch on purpose. `dashboard.json` publishes findings and is read on every
 * page; the catalogue is 7,523 products the owner's daily screen needs none of. Only the
 * pages that list products ask for it.
 *
 * WHY `absent` IS ITS OWN STATUS
 *   `products: null` and `products: []` are different claims and the schema keeps them apart.
 *   Null means the engine could not load the population. An empty array means it loaded it
 *   and the store has no products. Collapsing them would let a failed load render as an empty
 *   shop — the same class of mistake as rendering an unknown sales rate as "No sales".
 *
 * WHY THE DIGEST IS CHECKED HERE
 *   The catalogue and the artefact are two files fetched separately and can drift: a browser
 *   can hold a cached one and a fresh other. `inputs_digest` lets a caller PROVE they came
 *   from one run. `matchesArtefact` is exported rather than enforced, because a mismatch is a
 *   caller's decision — the products page can still list products honestly; a page that joins
 *   catalogue rows to artefact findings must not.
 */

const SCHEMA_VERSION = 1

const result = (status, catalogue, reason) => ({ status, catalogue, reason })

/**
 * @returns {Promise<{status: 'ok'|'absent'|'unreachable'|'invalid', catalogue: object|null, reason: string|null}>}
 */
export async function loadCatalogue({ fetchImpl = fetch, url = '/data/catalogue.json' } = {}) {
  let body
  try {
    const response = await fetchImpl(url)
    if (!response || !response.ok) {
      // 404 is the expected state before the first nightly commits one, and it is not an
      // error — it is "not published yet", which the page says in its own words.
      return result('unreachable', null, `HTTP ${response ? response.status : 'no response'}`)
    }
    body = await response.json()
  } catch (error) {
    return result('unreachable', null, error && error.message ? error.message : 'fetch failed')
  }

  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return result('invalid', null, 'catalogue is not an object')
  }
  if (body.schema_version !== SCHEMA_VERSION) {
    return result('invalid', null, `schema_version ${body.schema_version} is not ${SCHEMA_VERSION}`)
  }
  if (body.products === null) {
    return result('absent', body, 'the engine could not load the product population')
  }
  if (!Array.isArray(body.products)) {
    return result('invalid', null, 'products is neither an array nor null')
  }

  return result('ok', body, null)
}

/**
 * Whether a catalogue and an artefact came from the same engine run.
 *
 * Returns `null` — not `false` — when either side carries no digest. Unknown is not a
 * mismatch, and a caller that treats it as one would refuse to render over a perfectly good
 * pair of files (ADR-017).
 */
export function matchesArtefact(catalogue, artefact) {
  const a = catalogue?.inputs_digest
  const b = artefact?.inputs_digest
  if (!a || !b) return null
  return a === b
}
