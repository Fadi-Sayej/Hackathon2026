import { formatPercent, formatShekel } from '../../lib/utils/format.js'

// ₪, not "ILS" — this is an Israeli shop and the manager reads prices in shekels all
// day. The symbol stays on the left of the number even though the product names beside
// it are Hebrew; currency is not mirrored by direction.
export function formatCurrency(value) {
  return formatShekel(value)
}

export function formatDays(days) {
  if (days === null || days === undefined) return 'No sales'
  if (days < 1) return '<1 day'
  return `${days} days`
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
