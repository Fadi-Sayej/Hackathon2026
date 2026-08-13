import { useT } from '../../lib/i18n/index.js'
export function MarketContextPanel({ marketContext }) {
  const t = useT()
  const sourceLabel = marketContext.sourceLabel ?? marketContext.contextSource ?? 'mock'
  const signals = [
    {
      label: t('mc.weatherSignal'),
      value: marketContext.weather,
      detail: t('mc.weatherNote'),
    },
    {
      label: t('mc.weekendHoliday'),
      value: marketContext.weekend ? t('mc.weekendActive') : marketContext.holiday ? t('mc.holidayActive') : t('mc.normalDay'),
      detail: t('mc.impulseNote'),
    },
    {
      label: t('mc.localEvent'),
      value: marketContext.localEventKey
        ? t(marketContext.localEventKey)
        : marketContext.localEvent || t('mc.noEvent'),
      detail: t('mc.footTrafficNote'),
    },
  ]

  return (
    <section className="panel market-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{sourceLabel === 'live' ? t('mc.liveSignals') : t('mc.signals')}</p>
          <h2>{t('mc.aiContext')}</h2>
          <p className="muted" style={{ marginTop: '0.25rem', fontSize: '0.8rem' }}>
            {marketContext.sourceSummary ?? t('mc.contextNote')}
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
