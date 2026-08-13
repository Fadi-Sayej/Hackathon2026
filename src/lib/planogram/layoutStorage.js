/**
 * Persistence for the drawn store layout.
 *
 * Deliberately standalone rather than a new method on the persistence adapters
 * in `src/lib/persistence/`. That interface is a fixed set of six methods
 * implemented twice (localStorage and Firestore); adding a seventh means
 * touching both adapters and the reconcile path, which is a bigger change than
 * these two screens need. When the layout has to sync across devices, move it
 * in there properly — the two functions below are the whole surface to migrate.
 */

const STORAGE_KEY = 'smartshelf.storeLayout.v1'

function storage() {
  try {
    return typeof window !== 'undefined' ? window.localStorage : null
  } catch {
    // Safari in private mode throws on any localStorage access.
    return null
  }
}

/** Read the saved layout, or null when nothing has been drawn yet. */
export function loadStoreLayout() {
  const store = storage()
  if (!store) return null
  try {
    const raw = store.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || !Array.isArray(parsed.units)) return null
    return parsed
  } catch {
    return null
  }
}

/** Persist the layout. Returns false when storage is unavailable. */
export function saveStoreLayout(layout) {
  const store = storage()
  if (!store) return false
  try {
    store.setItem(STORAGE_KEY, JSON.stringify({ ...layout, savedAt: new Date().toISOString() }))
    return true
  } catch {
    return false
  }
}
