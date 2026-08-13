/**
 * Resolve a product's supplier and lead time from the receiving ledger.
 *
 * Every product reached the UI with `leadTimeDays: 3` and `supplier: 'YomYom'`
 * because the POS export carries neither field. The ledger (T7 / #52) is the
 * first place either is ever observed, so this module is the one place that
 * decides when a measured value replaces the assumed one.
 *
 * The rule is deliberately conservative: below three deliveries from a supplier
 * we keep the default lead time, because a median over two observations is a
 * guess with a decimal point on it.
 */

export const DEFAULT_LEAD_TIME_DAYS = 3
export const DEFAULT_SUPPLIER = 'YomYom'

export function emptyLedger() {
  return {
    defaultLeadTimeDays: DEFAULT_LEAD_TIME_DAYS,
    leadTimes: {},
    supplierByBarcode: {},
  }
}

function isPlainObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Tolerates a missing file, a null payload, or a malformed one. Never throws. */
export function normalizeLedger(raw) {
  if (!isPlainObject(raw)) return emptyLedger()
  const defaultDays = Number(raw.defaultLeadTimeDays)
  return {
    defaultLeadTimeDays: Number.isFinite(defaultDays) && defaultDays > 0
      ? defaultDays
      : DEFAULT_LEAD_TIME_DAYS,
    leadTimes: isPlainObject(raw.leadTimes) ? raw.leadTimes : {},
    supplierByBarcode: isPlainObject(raw.supplierByBarcode) ? raw.supplierByBarcode : {},
  }
}

/** Product ids arrive as `ym-<barcode>`; ledger keys are bare, unpadded barcodes. */
function barcodeKeys(barcode) {
  const raw = String(barcode ?? '').trim().replace(/^ym-/, '')
  if (!raw) return []
  const unpadded = raw.replace(/^0+/, '')
  return unpadded && unpadded !== raw ? [raw, unpadded] : [raw]
}

/**
 * True when a product's `leadTimeDays` is the assumed default rather than a
 * median measured from recorded deliveries.
 *
 * Anything that writes `leadTimeDays` into a sentence a manager reads must ask
 * this first. The trap it guards against is not the current all-defaults state
 * — it is the state right after the first supplier crosses three delivery
 * dates, when the resolver starts returning that supplier's real NAME with the
 * fallback lead time for its other barcodes. A sentence that names a real
 * supplier and states a number is read as a measurement of that supplier.
 *
 * A missing field counts as assumed: a product that never carried the metadata
 * certainly never had a delivery interval observed.
 */
export function isAssumedLeadTime(product) {
  return product?.leadTimeSource !== 'measured'
}

export function resolveSupplierAndLeadTime(barcode, ledger = emptyLedger()) {
  const safe = normalizeLedger(ledger)
  const fallback = {
    supplier: DEFAULT_SUPPLIER,
    leadTimeDays: safe.defaultLeadTimeDays,
    leadTimeConfidence: 'low',
    leadTimeSource: 'default',
  }

  let supplier = null
  for (const key of barcodeKeys(barcode)) {
    if (Object.prototype.hasOwnProperty.call(safe.supplierByBarcode, key)) {
      supplier = safe.supplierByBarcode[key]
      break
    }
  }
  if (!supplier) return fallback

  const entry = safe.leadTimes[supplier]
  const median = Number(entry?.median_days)
  if (!isPlainObject(entry) || entry.median_days === null || !Number.isFinite(median)) {
    return { ...fallback, supplier }
  }

  return {
    supplier,
    leadTimeDays: Math.max(1, Math.round(median)),
    leadTimeConfidence: entry.confidence ?? 'low',
    leadTimeSource: 'measured',
  }
}
