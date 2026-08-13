import { MetricCard } from '../components/shared/MetricCard.jsx'
import { useT } from '../lib/i18n/index.js'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { formatBarcode, formatDate } from '../lib/utils/format.js'
import { dirProps } from '../lib/utils/rtl.js'
import { ReceivingCaptureForm } from '../components/receiving/ReceivingCaptureForm.jsx'

const SEVERITY_TONE = {
  expired: 'danger',
  critical_7d: 'danger',
  warning_14d: 'warning',
  upcoming_30d: 'info',
  later: 'neutral',
}

export function ExpiryPage({ operationalData, products = [] }) {
  const t = useT()
  const { expiry } = operationalData
  const buckets = expiry?.buckets ?? {}
  const alerts = expiry?.alerts ?? []

  return (
    <>
      <section className="metric-grid">
        <MetricCard label={t('exp.expired')} value={buckets.expired ?? 0} detail={t('exp.expiredDetail')} tone="danger" />
        <MetricCard label={t('exp.d7')} value={buckets.critical_7d ?? 0} detail={t('exp.d7Detail')} tone="danger" />
        <MetricCard label={t('exp.d14')} value={buckets.warning_14d ?? 0} detail={t('exp.d14Detail')} tone="warning" />
        <MetricCard label={t('exp.d30')} value={buckets.upcoming_30d ?? 0} detail={t('exp.d30Detail')} tone="info" />
        <MetricCard label={t('exp.scans')} value={expiry?.totalScans ?? 0} detail={t('exp.scansDetail')} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Receiving</p>
            <h2>{t('exp.recordTitle')}</h2>
          </div>
        </div>
        <p className="page-description">
          When goods arrive, record what came in: how many, from whom, and the date on
          the package if there is one. For something already on the shelf, switch to
          <strong> Expiry only</strong> and record just the barcode and the date. This is
          the only record of either — the POS export contains neither deliveries nor
          expiry dates.
        </p>

        <ReceivingCaptureForm products={products} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Expiry alerts</p>
            <h2>{t('exp.nearingTitle')}</h2>
          </div>
          <span className="metric-chip">
            {operationalData?.meta?.generatedAt
              ? `From pipeline export · ${formatDate(operationalData.meta.generatedAt)}`
              : t('exp.fromExport')}
          </span>
        </div>
        {alerts.length === 0 ? (
          <EmptyState
            title={t('exp.noAlerts')}
            description={t('exp.noAlertsDesc')}
          />
        ) : (
          <div className="compact-list">
            {alerts.map((row, idx) => (
              <div className="compact-row" key={`${row.barcode}:${idx}`}>
                <div>
                  <strong {...dirProps(row.productName || row.barcode)}>
                    {row.productName || (row.barcode ? formatBarcode(row.barcode) : t('exp.unknown'))}
                  </strong>
                  <span>{row.knownInPos ? `stock ${row.currentStock}` : 'not in POS'}</span>
                </div>
                <div className="compact-row-end">
                  <StatusBadge tone={SEVERITY_TONE[row.severity] ?? 'neutral'}>{row.severity}</StatusBadge>
                  <small className="date-cell">{formatDate(row.expiryDate)} · {row.daysToExpiry ?? '—'} days</small>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  )
}
