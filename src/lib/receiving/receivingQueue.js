/**
 * The receiving queue — every decision about a delivery line except how it looks.
 *
 * Kept separate from the form component for two reasons. The obvious one is that
 * vitest runs in a node environment with no DOM, so this is the only layer that
 * can be tested at all. The load-bearing one is that a mis-typed quantity or a
 * dropped queue is a data-integrity failure, and those rules should not live
 * inside a render function.
 *
 * Nothing here touches the network. The shop's connection drops, and a delivery
 * that cannot be recorded is a delivery that gets written on paper instead.
 */

export const RECEIVING_QUEUE_KEY = 'receiving_queue'
export const LAST_SUPPLIER_KEY = 'receiving_last_supplier'
// The pre-T7 expiry capture wrote here. Reusing the same key means the lines a
// worker recorded before this branch are still in the list and can still be
// exported, instead of sitting in localStorage with nothing able to drain them.
export const EXPIRY_QUEUE_KEY = 'expiry_scan_queue'

/**
 * Two things get captured at the same counter and they are not the same event.
 *
 * DELIVERY is goods arriving: how many, from whom — the receiving ledger.
 * EXPIRY_ONLY is a date read off a package already on the shelf. There is no
 * delivery and no supplier to name, and requiring one would mean inventing a
 * fake one. Both write the barcode and a date; only the delivery path can
 * honestly claim a quantity and a supplier, so the two exports go to two
 * different Python importers and must not be mixed into one file.
 */
export const CAPTURE_MODE_DELIVERY = 'delivery'
export const CAPTURE_MODE_EXPIRY = 'expiry'

// Must stay in lockstep with RECEIVING_COLUMNS in src/internal/receiving.py.
// receipt_id is derived server-side and is deliberately absent here.
export const RECEIVING_CSV_HEADER =
  'barcode,product_name,quantity,supplier,unit_cost,received_at,expiry_date,recorded_at,source'

// The shape src/expiry/expiry_tracking.py's import_expiry_csv already reads.
// Deliberately not extended: that importer exists and works, and a second
// column set would mean a second import path for the same fact.
export const EXPIRY_CSV_HEADER = 'barcode,expiry_date'

const CSV_FIELDS = [
  'barcode', 'productName', 'quantity', 'supplier',
  'unitCost', 'receivedAt', 'expiryDate', 'recordedAt', 'source',
]

const EXPIRY_CSV_FIELDS = ['barcode', 'expiryDate']

/**
 * Today's LOCAL calendar date.
 *
 * Not `toISOString()`: Israel is UTC+2/+3, so between midnight and 03:00 local
 * the UTC date is still yesterday. YomYom is a 24-hour forecourt shop and night
 * deliveries are ordinary, and `received_at` is the single date the lead-time
 * median and the restock reconciliation window both rest on — a delivery
 * silently filed a day early moves both.
 */
export function todayIso(now = new Date()) {
  const pad = (value) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

/** The real localStorage when there is one — absent in the node test environment. */
export function getStorage() {
  return typeof globalThis.localStorage !== 'undefined' ? globalThis.localStorage : null
}

function text(value) {
  return String(value ?? '').trim()
}

export function makeEntry(input, { now = new Date() } = {}) {
  const barcode = text(input?.barcode)
  if (!barcode) throw new Error('Scan or type a barcode first.')

  const rawQuantity = text(input?.quantity)
  if (!/^\d+$/.test(rawQuantity)) {
    throw new Error('Quantity must be a whole number of units.')
  }
  const quantity = Number(rawQuantity)
  if (quantity <= 0) throw new Error('Quantity must be at least 1 unit.')

  const supplier = text(input?.supplier)
  if (!supplier) throw new Error('Enter the supplier on the delivery note.')

  const rawCost = text(input?.unitCost)
  let unitCost = ''
  if (rawCost) {
    const parsed = Number(rawCost)
    if (!Number.isFinite(parsed) || parsed < 0) {
      throw new Error('Unit cost must be a number of shekels, or left blank.')
    }
    unitCost = parsed
  }

  return {
    barcode,
    productName: text(input?.productName),
    quantity,
    supplier,
    unitCost,
    receivedAt: text(input?.receivedAt) || todayIso(now),
    expiryDate: text(input?.expiryDate),
    recordedAt: now.toISOString(),
    source: 'manual_ui',
  }
}

/**
 * One expiry observation: a barcode and the date printed on the package.
 *
 * No quantity and no supplier — not "optional", absent. Stock already on the
 * shelf did not arrive today from anyone in particular, and the only way to
 * push it through makeEntry() would be to type a supplier that never delivered
 * it, which would then be counted as a real delivery date by
 * supplier_lead_times().
 */
export function makeExpiryEntry(input, { now = new Date() } = {}) {
  const barcode = text(input?.barcode)
  if (!barcode) throw new Error('Scan or type a barcode first.')

  const expiryDate = text(input?.expiryDate)
  if (!expiryDate) throw new Error('Enter the expiry date printed on the package.')

  return {
    barcode,
    productName: text(input?.productName),
    expiryDate,
    recordedAt: now.toISOString(),
    source: 'manual_ui',
  }
}

export function isExpiryOnlyMode(mode) {
  return mode === CAPTURE_MODE_EXPIRY
}

/**
 * The mode decision itself, kept out of the render function so it is testable:
 * which validation rules apply, and therefore which required fields the form
 * can drop. Everything else about the mode (which queue, which CSV, which
 * filename) follows from this one branch.
 */
export function makeEntryForMode(mode, input, options = {}) {
  return isExpiryOnlyMode(mode) ? makeExpiryEntry(input, options) : makeEntry(input, options)
}

export function queueKeyForMode(mode) {
  return isExpiryOnlyMode(mode) ? EXPIRY_QUEUE_KEY : RECEIVING_QUEUE_KEY
}

export function appendEntry(queue, entry) {
  return [entry, ...(Array.isArray(queue) ? queue : [])]
}

export function undoLast(queue) {
  return Array.isArray(queue) ? queue.slice(1) : []
}

export function knownSuppliers(queue) {
  const seen = new Set()
  for (const entry of Array.isArray(queue) ? queue : []) {
    const supplier = text(entry?.supplier)
    if (supplier) seen.add(supplier)
  }
  return [...seen].sort((a, b) => a.localeCompare(b))
}

// productName is the one column that is genuinely free text a worker typed —
// it is always quoted so a comma or an embedded quote in a product name can
// never be mistaken for a column boundary by Python's csv.DictReader. Every
// other column is machine-shaped (barcode, quantity, an ISO date/timestamp,
// the fixed 'manual_ui' source) and is quoted only when it actually needs it.
function csvCell(field, value) {
  const raw = value === '' || value === null || value === undefined ? '' : String(value)
  const needsQuoting = field === 'productName' || /[",\n]/.test(raw)
  return needsQuoting ? `"${raw.replace(/"/g, '""')}"` : raw
}

export function toCsv(queue) {
  const rows = (Array.isArray(queue) ? queue : []).map((entry) =>
    CSV_FIELDS.map((field) => csvCell(field, entry?.[field])).join(','),
  )
  return [RECEIVING_CSV_HEADER, ...rows].join('\n') + '\n'
}

export function toExpiryCsv(queue) {
  const rows = (Array.isArray(queue) ? queue : []).map((entry) =>
    EXPIRY_CSV_FIELDS.map((field) => csvCell(field, entry?.[field])).join(','),
  )
  return [EXPIRY_CSV_HEADER, ...rows].join('\n') + '\n'
}

/**
 * What to download for a mode: the file the matching Python importer reads,
 * under a filename that says which importer that is.
 */
export function exportForMode(mode, queue, { now = new Date() } = {}) {
  return isExpiryOnlyMode(mode)
    ? { filename: `expiry_scans_${todayIso(now)}.csv`, csv: toExpiryCsv(queue) }
    : { filename: `receiving_${todayIso(now)}.csv`, csv: toCsv(queue) }
}

export function loadQueue(storage = getStorage(), key = RECEIVING_QUEUE_KEY) {
  if (!storage) return []
  try {
    const parsed = JSON.parse(storage.getItem(key) ?? '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveQueue(queue, storage = getStorage(), key = RECEIVING_QUEUE_KEY) {
  if (!storage) return
  try {
    storage.setItem(key, JSON.stringify(queue))
  } catch {
    // A full quota must not lose the line the manager just typed — it stays in
    // React state and the CSV export still sees it.
  }
}

export function readLastSupplier(storage = getStorage()) {
  if (!storage) return ''
  try {
    return text(storage.getItem(LAST_SUPPLIER_KEY))
  } catch {
    return ''
  }
}

export function rememberLastSupplier(supplier, storage = getStorage()) {
  if (!storage) return
  try {
    storage.setItem(LAST_SUPPLIER_KEY, text(supplier))
  } catch {
    /* nothing to do — the field simply will not pre-fill next time */
  }
}
