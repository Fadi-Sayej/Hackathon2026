export function formatCurrency(value) {
  return `ILS ${Number(value ?? 0).toLocaleString(undefined, {
    maximumFractionDigits: 2,
    minimumFractionDigits: Number.isInteger(Number(value ?? 0)) ? 0 : 2,
  })}`
}

export function formatDays(days) {
  if (days === null || days === undefined) return 'No sales'
  if (days < 1) return '<1 day'
  return `${days} days`
}

export function percent(value) {
  return `${Math.round((value ?? 0) * 100)}%`
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
