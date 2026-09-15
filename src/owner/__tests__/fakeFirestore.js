/**
 * A Firestore stand-in that applies the SAME write semantics the real SDK does for the calls
 * the owner-state writer makes, so a test can assemble the documents the engine would read.
 *
 *  - setDoc(ref, data, { merge: true })          → deep merge (the real SDK's behaviour)
 *  - setDoc(ref, data, { mergeFields: [paths] })  → each named top-level field REPLACED
 *                                                   wholesale; every other field untouched
 *
 * The distinction is load-bearing. A deep merge of `{ [id]: record }` keeps nested keys the new
 * record omits — a stale `deferred_until` survives an outcome changing to `acted` — so the
 * remote copy silently diverges from localStorage, which replaces the record whole.
 */
export class FakeFieldPath {
  constructor(...segments) { this.segments = segments }
  toString() { return this.segments.join('.') }
}

const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v)

function deepMerge(target, source) {
  const out = { ...target }
  for (const [k, v] of Object.entries(source)) {
    out[k] = isPlainObject(v) && isPlainObject(out[k]) ? deepMerge(out[k], v) : v
  }
  return out
}

export function createFakeFirestore({ storeId = 'yomyom-kafr-qasim', configured = true, user = { uid: 'anon' }, failWrites = false } = {}) {
  const docs = new Map()               // 'stores/x/ownerState/outcomes' -> object
  const calls = []
  const db = { __fake: true }

  const api = {
    storeId,
    isConfigured: () => configured,
    ensureAuth: async () => user,
    getDb: () => db,
    FieldPath: FakeFieldPath,
    doc: (_db, ...segments) => ({ path: segments.join('/') }),
    setDoc: async (ref, data, options = {}) => {
      calls.push({ path: ref.path, data, options })
      if (failWrites) throw new Error('permission-denied')
      const prev = docs.get(ref.path) || {}
      if (options.mergeFields) {
        const next = { ...prev }
        for (const field of options.mergeFields) {
          const name = String(field)
          if (Object.prototype.hasOwnProperty.call(data, name)) next[name] = data[name]
        }
        docs.set(ref.path, next)
      } else if (options.merge) {
        docs.set(ref.path, deepMerge(prev, data))
      } else {
        docs.set(ref.path, { ...data })
      }
    },
  }
  return {
    api,
    calls,
    loader: async () => api,
    doc: (name) => docs.get(`stores/${storeId}/ownerState/${name}`),
    /** Every document exactly as `src/owner_state/pull.py` would stream them. */
    ownerStateDocs: () => Object.fromEntries(
      ['answers', 'outcomes', 'revivals', 'devices', 'meta']
        .map((n) => [n, docs.get(`stores/${storeId}/ownerState/${n}`)])
        .filter(([, v]) => v !== undefined),
    ),
  }
}
