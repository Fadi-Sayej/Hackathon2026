import { formatPercent, formatShekel } from '../../lib/utils/format.js'

// ₪, not "ILS" — this is an Israeli shop and the manager reads prices in shekels all
// day. The symbol stays on the left of the number even though the product names beside
// it are Hebrew; currency is not mirrored by direction.
export function formatCurrency(value) {
  return formatShekel(value)
}

/**
 * Days of cover, or an honest statement that we do not know.
 *
 * `null` used to render as "No sales", and that was a claim the data does not support.
 * `inventoryEngine` is careful about this — it emits `daysUntilStockout: null` under a
 * comment reading "Without sales history every velocity-derived verdict is unknowable, not
 * false" — and this function converted it straight back one layer downstream. The guard was
 * never missing; it was defeated by a string.
 *
 * It matters at the scale the restored pages run at. Fed the published catalogue, every one
 * of 7,523 products reports `null` here, and 1,778 of them appear in `sales_summary.parquet`
 * with `units_total > 0` — products that demonstrably sell, labelled as selling nothing.
 *
 * `t` is optional so the older callers keep working, but the English fallback no longer
 * states the false version either.
 */
export function formatDays(days, t) {
  if (days === null || days === undefined) return t ? t('days.unknown') : 'No sales data'
  if (days < 1) return t ? t('days.lessThanOne') : '<1 day'
  return t ? t('days.count', { days }) : `${days} days`
}

/**
 * i18n key for a status produced by `inventoryEngine`.
 *
 * That module uses the English sentence as both the internal identifier and the display
 * text, which is why these screens showed English badges beside Hebrew product names on an
 * RTL page. Translating here rather than there keeps `primaryStatus` a stable key — the
 * tests and `statusTone`'s substring matching both depend on the English value — while the
 * owner reads his own language.
 */
const STATUS_KEYS = {
  'Healthy': 'status.healthy',
  'Low stock': 'status.lowStock',
  'Stockout risk': 'status.stockoutRisk',
  'Overstocked': 'status.overstocked',
  'Slow moving': 'status.slowMoving',
  'Near expiry': 'status.nearExpiry',
  'High priority': 'status.highPriority',
  'Not enough sales history yet': 'status.noVelocityData',
}

/** Translated status text, falling back to the raw value rather than rendering blank. */
export function formatStatus(status, t) {
  const key = STATUS_KEYS[status]
  if (!key || !t) return status
  return t(key)
}

export function percent(value) {
  return formatPercent(value, 0, true)
}

export function statusTone(status) {
  const normalized = String(status).toLowerCase()
  if (normalized.includes('stockout') || normalized.includes('high')) return 'danger'
  if (normalized.includes('low') || normalized.includes('expiry')) return 'warning'
  if (normalized.includes('healthy')) return 'success'
  if (normalized.includes('overstocked') || normalized.includes('slow')) return 'info'
  return 'neutral'
}

export function urgencyTone(urgency) {
  if (urgency === 'HIGH') return 'danger'
  if (urgency === 'MEDIUM') return 'warning'
  return 'success'
}
