/**
 * D-37, ADR-042: a shelf photo sent from the app, as the nightly collects it (F12-S1 FR-225).
 *
 *   stores/<store>/shelfPhotos/<photo>/parts/<n>   { data, n, at }   at most PART_MAX bytes each
 *   stores/<store>/shelfPhotos/<photo>             the manifest, written last
 *
 * The parts first and the manifest last, so a manifest means the whole photo is there. A photo's
 * id is fixed when it is chosen, so sending it again rewrites the same documents. Nothing here
 * touches Firebase: firestoreShelfPhotos.js binds the two writes, so this is tested without it.
 */

export const PART_MAX = 900_000                    // a Firestore document holds at most 1 MiB
export const AS_TAKEN_MAX = 12 * 1024 * 1024       // a JPEG up to this is sent byte for byte
export const LONG_SIDE = 4096                      // a redrawn photo's longest side: ~0.5 mm a pixel across 2 m
export const QUALITY = 0.92
export const SEND_TIMEOUT_MS = 120_000
/** MUST equal SCHEMA in src/owner_state/shelf_photos.py, which leaves any other manifest unread. */
export const PHOTO_SCHEMA = 1

export function isJpeg(bytes) {
  return bytes.length > 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff
}

export function newPhotoId() {
  const c = globalThis.crypto
  if (c?.randomUUID) return c.randomUUID()
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}

/** The photo redrawn once as a JPEG, turned as the camera's tag says, its longest side at most LONG_SIDE. */
export async function redrawAsJpeg(file) {
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  const scale = Math.min(1, LONG_SIDE / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  bitmap.close?.()
  const blob = await new Promise((resolve, reject) => canvas.toBlob(
    (b) => (b ? resolve(b) : reject(new Error('the photo could not be redrawn'))), 'image/jpeg', QUALITY))
  return new Uint8Array(await blob.arrayBuffer())
}

/** The bytes that are sent: the camera's own when it is a JPEG small enough, else a redrawing. */
export async function asSent(file, redraw = redrawAsJpeg) {
  const bytes = new Uint8Array(await file.arrayBuffer())
  if (bytes.length <= AS_TAKEN_MAX && isJpeg(bytes)) return bytes
  return redraw(file)
}

export function split(bytes) {
  const parts = []
  for (let at = 0; at < bytes.length; at += PART_MAX) parts.push(bytes.subarray(at, at + PART_MAX))
  return parts
}

export async function sha256Hex(bytes) {
  const digest = new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', bytes))
  return Array.from(digest, (b) => b.toString(16).padStart(2, '0')).join('')
}

function within(ms, promise) {
  let timer
  const late = new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('timeout')), ms) })
  return Promise.race([promise, late]).finally(() => clearTimeout(timer))
}

/**
 * Send one photo: its parts, then its manifest. Throws when it did not send, and the screen says
 * so. Offline, nothing is started; a send cut off part-way leaves no manifest, so nothing half
 * sent is ever collected, and sending again finishes it under the same id.
 */
export async function sendPhoto({ id, unit, file }, { writePart, writeManifest, now = Date.now,
  online = () => globalThis.navigator?.onLine !== false, redraw, timeoutMs = SEND_TIMEOUT_MS }) {
  if (!online()) throw new Error('offline')
  const bytes = await asSent(file, redraw)
  const parts = split(bytes)
  const at = now()
  const sha256 = await sha256Hex(bytes)
  await within(timeoutMs, (async () => {
    for (const [n, data] of parts.entries()) await writePart(id, n, { data, n, at })
    await writeManifest(id, { schema: PHOTO_SCHEMA, unit, sentAt: at, size: bytes.length, parts: parts.length,
      sha256, type: 'image/jpeg' })
  })())
}

/**
 * The photos sent, newest first, each with its state (FR-227): sent this visit, still waiting in
 * Firestore, or in the artefact as collected or read. A photo is listed once, at its latest state.
 */
export function sentList({ collected = [], pending = [], mine = [] }) {
  const arrived = new Set(collected.map((c) => c.id))
  const waiting = []
  for (const p of [...mine, ...[...pending].sort((a, b) => (b.sentAt ?? 0) - (a.sentAt ?? 0))]) {
    if (!arrived.has(p.id) && !waiting.some((w) => w.id === p.id)) {
      waiting.push({ id: p.id, unit: p.unit, status: 'sent', date: null })
    }
  }
  const latest = (c) => c.read ?? c.collected
  return [...waiting, ...[...collected].sort((a, b) => latest(b).localeCompare(latest(a))).map((c) => (
    { id: c.id, unit: c.unit, status: c.read ? 'read' : 'collected', date: latest(c) }))]
}
