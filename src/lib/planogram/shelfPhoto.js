/**
 * Storage for photographs of the shelf as it actually stands.
 *
 * Each record pairs an image with the plan it was photographed against and the
 * manager's verdict on whether the two agree. That triple — photo, intended
 * plan, human judgement — is exactly the labelled pair a compliance model needs
 * later, and nobody has any of it today.
 *
 * Images are downscaled and stored as JPEG data URLs in localStorage. That is a
 * deliberate limit, not an oversight: localStorage holds roughly 5MB, so one
 * photo per fixture-and-category at ~1280px is affordable while a full-
 * resolution phone capture is not. When a backend exists these move to object
 * storage and only the key stays here.
 */

const STORAGE_KEY = 'smartshelf.shelfPhotos.v1'

/** Long edge, in pixels, after downscaling. Enough to read a facing. */
const MAX_EDGE = 1280
const JPEG_QUALITY = 0.72
/** Refuse anything that would crowd out the rest of localStorage. */
const MAX_STORED_BYTES = 1_400_000

const memoryStore = new Map()

function storageAvailable() {
  try {
    return Boolean(globalThis.localStorage)
  } catch {
    return false
  }
}

function readAll() {
  // When localStorage works it is the ONLY source of truth. Falling back to the
  // in-memory copy while storage is available meant clearing browser storage did
  // not actually clear anything — stale approvals came back from memory.
  if (storageAvailable()) {
    try {
      const raw = globalThis.localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  }
  return Object.fromEntries(memoryStore)
}

function writeAll(all) {
  memoryStore.clear()
  for (const [key, value] of Object.entries(all)) memoryStore.set(key, value)
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify(all))
  } catch {
    // Quota exceeded — the memory copy above keeps this session working.
  }
}

const keyFor = (unitId, category) => `${unitId}::${category}`

/** The stored photo record for a fixture and category, or null. */
export function loadShelfPhoto(unitId, category) {
  return readAll()[keyFor(unitId, category)] ?? null
}

export function clearShelfPhoto(unitId, category) {
  const all = readAll()
  delete all[keyFor(unitId, category)]
  writeAll(all)
}

/**
 * Save a photo, a verdict, or both.
 *
 * `keepImage` updates the verdict on the existing record without re-encoding —
 * the manager changing their mind should not cost an image round trip.
 */
export function saveShelfPhoto({ unitId, category, file, verdict, planSummary, keepImage }) {
  const all = readAll()
  const key = keyFor(unitId, category)
  const existing = all[key] ?? null

  if (keepImage || !file) {
    if (!existing) return null
    const updated = { ...existing, verdict: verdict ?? existing.verdict, verdictAt: new Date().toISOString() }
    all[key] = updated
    writeAll(all)
    return updated
  }

  // Async path is handled by the caller awaiting this promise.
  return downscale(file).then((dataUrl) => {
    if (dataUrl.length > MAX_STORED_BYTES) {
      throw new Error('image-too-large')
    }
    const record = {
      unitId,
      category,
      dataUrl,
      capturedAt: new Date().toISOString(),
      verdict: null,
      // The plan this photo is evidence about. Without it the image is just a
      // picture of a shelf, with no way to say what it was supposed to show.
      planSummary: planSummary ?? null,
    }
    const next = readAll()
    next[key] = record
    writeAll(next)
    return record
  })
}

/** Read an image file, scale its long edge to MAX_EDGE, return a JPEG data URL. */
function downscale(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const image = new Image()
    image.onload = () => {
      URL.revokeObjectURL(url)
      const scale = Math.min(1, MAX_EDGE / Math.max(image.width, image.height))
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(image.width * scale)
      canvas.height = Math.round(image.height * scale)
      const context = canvas.getContext('2d')
      context.drawImage(image, 0, 0, canvas.width, canvas.height)
      resolve(canvas.toDataURL('image/jpeg', JPEG_QUALITY))
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('image-unreadable'))
    }
    image.src = url
  })
}
