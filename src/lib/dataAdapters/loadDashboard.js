/**
 * loadDashboard — read the engine's artefact, or say why it could not be read.
 *
 * Never throws, and never falls back. An unreachable or invalid artefact is a state the UI
 * renders; showing yesterday's numbers as though they were today's is the one outcome this
 * module exists to prevent.
 *
 * It performs NO schema validation (ADR-018). The schema is enforced where the artefact is
 * produced (`src/engine/publish.py`) and again in CI, so an artefact that reaches the
 * browser has passed it twice. What is checked here is only what the UI cannot render
 * without — four preconditions, each with a rendering reason rather than a schema reason.
 */

const SCHEMA_VERSION = 2

const result = (status, artefact, reason) => ({ status, artefact, reason })

/**
 * @returns {Promise<{status: 'ok'|'unreachable'|'invalid', artefact: object|null, reason: string|null}>}
 */
export async function loadDashboard({ fetchImpl = fetch, url = '/data/dashboard.json' } = {}) {
  let body
  try {
    const response = await fetchImpl(url)
    if (!response || !response.ok) {
      return result('unreachable', null, `HTTP ${response ? response.status : 'no response'}`)
    }
    body = await response.json()
  } catch (error) {
    // A network failure and unparseable JSON are the same thing to the reader: the artefact
    // did not arrive. Neither is a reason to render something older.
    return result('unreachable', null, error && error.message ? error.message : 'fetch failed')
  }

  if (!body || typeof body !== 'object') {
    return result('invalid', null, 'artefact is not an object')
  }

  // A different schema version has a shape this build does not know. Rendering it would be
  // guessing at field meanings.
  if (body.schema_version !== SCHEMA_VERSION) {
    return result('invalid', null,
      `schema_version ${body.schema_version} is not ${SCHEMA_VERSION}`)
  }

  if (!body.capabilities || typeof body.capabilities !== 'object' || Array.isArray(body.capabilities)) {
    return result('invalid', null, 'capabilities is missing or not an object')
  }

  // AC-107: an unavailable capability must read as unavailable, never as zero findings.
  // Without a status that is not merely wrong — it is unachievable, because an entry list
  // of length zero is indistinguishable from a capability that could not run.
  for (const [id, capability] of Object.entries(body.capabilities)) {
    if (!capability || typeof capability !== 'object' || typeof capability.status !== 'string') {
      return result('invalid', null, `capability ${id} has no status`)
    }
  }

  return result('ok', body, null)
}
