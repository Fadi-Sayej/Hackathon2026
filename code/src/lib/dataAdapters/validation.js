export function createIssue(field, code, message, value, severity = 'warning') {
  return {
    field,
    code,
    message,
    severity,
    value,
  }
}

export function requiredString(value, fallback, field, issues) {
  if (typeof value === 'string' && value.trim()) return value.trim()
  issues.push(createIssue(field, 'missing_required_text', `${field} is missing.`, value))
  return fallback
}

export function nonNegativeNumber(value, fallback, field, issues) {
  const parsed = Number(value)
  if (Number.isFinite(parsed) && parsed >= 0) return parsed
  issues.push(createIssue(field, 'invalid_non_negative_number', `${field} must be 0 or greater.`, value))
  return fallback
}

export function positiveNumber(value, fallback, field, issues) {
  const parsed = Number(value)
  if (Number.isFinite(parsed) && parsed > 0) return parsed
  issues.push(createIssue(field, 'invalid_positive_number', `${field} must be greater than 0.`, value))
  return fallback
}

export function optionalDate(value, field, issues) {
  if (value === undefined || value === null || value === '') return undefined
  const date = new Date(`${value}T00:00:00Z`)
  if (!Number.isNaN(date.getTime())) return String(value)
  issues.push(createIssue(field, 'invalid_date', `${field} must be an ISO date string.`, value))
  return undefined
}

export function withProductContext(issue, productId, rowIndex) {
  return {
    ...issue,
    productId,
    rowIndex,
  }
}
