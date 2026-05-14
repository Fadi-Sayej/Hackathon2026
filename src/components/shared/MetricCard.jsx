export function MetricCard({ detail, label, tone = 'neutral', value }) {
  return (
    <article className={`metric-card metric-card-${tone}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
  )
}
