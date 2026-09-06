export function MarketContextPanel({ marketContext }) {
  const sourceLabel = marketContext.sourceLabel ?? marketContext.contextSource ?? 'mock'
  const signals = [
    {
      label: 'Weather signal',
      value: marketContext.weather,
      detail: 'Demand lift for water, cold drinks, and ice cream.',
    },
    {
      label: 'Weekend / holiday',
      value: marketContext.weekend ? 'Weekend active' : marketContext.holiday ? 'Holiday active' : 'Normal day',
      detail: 'Impulse categories receive a demand multiplier.',
    },
    {
      label: 'Local event',
      value: marketContext.localEvent || 'No event',
      detail: 'Foot traffic signal used for recommendations.',
    },
  ]

  return (
    <section className="panel market-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{sourceLabel === 'live' ? 'Live Market Signals' : 'Market Signals'}</p>
          <h2>AI market context</h2>
          <p className="muted" style={{ marginTop: '0.25rem', fontSize: '0.8rem' }}>
            {marketContext.sourceSummary ?? 'Static demo context with optional live adapters for weather, holidays, and news.'}
          </p>
        </div>
      </div>

      <div className="signal-grid">
        {signals.map((signal) => (
          <div className="signal-card" key={signal.label}>
            <p>{signal.label}</p>
            <strong>{signal.value}</strong>
            <span>{signal.detail}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
