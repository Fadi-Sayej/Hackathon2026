/**
 * A labelled figure. The label says what it is, the value is the figure, the
 * helper says what it is measured against.
 */
export function MetricCard({ detail, label, tone = 'neutral', value }) {
  return (
    <article className={`metric-card metric-card-${tone}`}>
      <p className="metric-label">{label}</p>
      <p className={`metric-value ${valueSizeClass(value)}`}>{value}</p>
      <p className="metric-helper">{detail}</p>
    </article>
  )
}

/**
 * Display size, chosen from how much there is to display.
 *
 * The card clips its contents, so a value wider than the card is not merely
 * cramped — it is cut mid-digit, and "₪63,57" reads as a smaller amount rather
 * than as an error. Counting characters here is enough to prevent that, and it
 * costs nothing at render.
 *
 * Bidi isolate marks are stripped first: `formatCurrency` wraps its output in
 * U+2066…U+2069 so a shekel figure keeps its digit order inside Arabic text,
 * and those four invisible characters would otherwise push every price a step
 * smaller than it needs to be.
 */
function valueSizeClass(value) {
  const visible = String(value ?? '').replace(/[\u2066-\u2069\u200e\u200f]/g, '')
  if (visible.length >= 10) return 'metric-value--sm'
  if (visible.length >= 7) return 'metric-value--md'
  return ''
}
