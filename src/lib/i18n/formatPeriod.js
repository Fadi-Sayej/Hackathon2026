import { formatNumber } from './index.js'

/**
 * A published period in the owner's language (F2-V7, docs/reviews/F2-validation.md).
 *
 * The engine publishes a window as its id, `YYYY-MM..YYYY-MM` (`EvidenceWindow.window_id`).
 * Since ADR-026 that id names the months a reconciliation actually summed, so it is the right
 * period — but the card printed it raw, under the label "the period". This writes it as month
 * names in the interface's language, with the year in the interface's digits
 * (`formatNumber`: Arabic-Indic for Arabic, as everywhere else in the Arabic UI).
 *
 * Anything that is not a month range is returned exactly as published. A value this cannot
 * read is still information, and hiding it would be worse than showing it plainly.
 */
const MONTH_RANGE = /^(\d{4})-(0[1-9]|1[0-2])\.\.(\d{4})-(0[1-9]|1[0-2])$/

export function formatWindowId(windowId, t, language) {
  const match = MONTH_RANGE.exec(String(windowId))
  if (!match) return String(windowId)
  const [, fromYear, fromMonth, toYear, toMonth] = match
  const month = (m) => t(`month.${m}`)
  const year = (y) => formatNumber(y, language)
  if (fromYear === toYear && fromMonth === toMonth) return `${month(fromMonth)} ${year(fromYear)}`
  if (fromYear === toYear) return `${month(fromMonth)}–${month(toMonth)} ${year(fromYear)}`
  return `${month(fromMonth)} ${year(fromYear)}–${month(toMonth)} ${year(toYear)}`
}
