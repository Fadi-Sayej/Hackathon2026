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

// Must stay in lockstep with RECEIVING_COLUMNS in src/internal/receiving.py.
// receipt_id is derived server-side and is deliberately absent here.
export const RECEIVING_CSV_HEADER =
  'barcode,product_name,quantity,supplier,unit_cost,received_at,expiry_date,recorded_at,source'

const CSV_FIELDS = [
  'barcode', 'productName', 'quantity', 'supplier',
  'unitCost', 'receivedAt', 'expiryDate', 'recordedAt', 'source',
]

export function todayIso(now = new Date()) {
  return now.toISOString().slice(0, 10)
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

export function loadQueue(storage = getStorage()) {
  if (!storage) return []
  try {
    const parsed = JSON.parse(storage.getItem(RECEIVING_QUEUE_KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveQueue(queue, storage = getStorage()) {
  if (!storage) return
  try {
    storage.setItem(RECEIVING_QUEUE_KEY, JSON.stringify(queue))
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
