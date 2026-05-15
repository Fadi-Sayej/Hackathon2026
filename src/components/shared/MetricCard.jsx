export function MetricCard({ detail, label, tone = 'neutral', value }) {
  return (
    <article className={`metric-card metric-card-${tone}`}>
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
      <p className="metric-helper">{detail}</p>
    </article>
  )
}
