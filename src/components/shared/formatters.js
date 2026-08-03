import { formatPercent, formatShekel } from '../../lib/utils/format.js'

export function formatCurrency(value) {
  return formatShekel(value)
}

export function formatDays(days) {
  if (typeof days === 'string' && !days.trim()) return '—'
  const numericDays = Number(days)
  if (days === null || days === undefined || !Number.isFinite(numericDays)) return '—'
  if (numericDays < 1) return '<1 day'
  return `${numericDays} days`
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
