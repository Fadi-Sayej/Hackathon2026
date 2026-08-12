import { MetricCard } from '../components/shared/MetricCard.jsx'
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
  const { expiry } = operationalData
  const buckets = expiry?.buckets ?? {}
  const alerts = expiry?.alerts ?? []

  return (
    <>
      <section className="metric-grid">
        <MetricCard label="Expired" value={buckets.expired ?? 0} detail="Remove from shelf" tone="danger" />
        <MetricCard label="0–7 days" value={buckets.critical_7d ?? 0} detail="Promote / discount now" tone="danger" />
        <MetricCard label="8–14 days" value={buckets.warning_14d ?? 0} detail="Prioritize placement" tone="warning" />
        <MetricCard label="15–30 days" value={buckets.upcoming_30d ?? 0} detail="Keep visible" tone="info" />
        <MetricCard label="Scans recorded" value={expiry?.totalScans ?? 0} detail="Total expiry scans" />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Receiving</p>
            <h2>Record a delivery or an expiry date</h2>
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
            <h2>Items nearing or past expiry</h2>
          </div>
          <span className="metric-chip">
            {operationalData?.meta?.generatedAt
              ? `From pipeline export · ${formatDate(operationalData.meta.generatedAt)}`
              : 'From last pipeline export'}
          </span>
        </div>
        {alerts.length === 0 ? (
          <EmptyState
            title="No expiry alerts yet"
            description="Record expiry dates at receiving, then run npm run data:refresh to populate alerts."
          />
        ) : (
          <div className="compact-list">
            {alerts.map((row, idx) => (
              <div className="compact-row" key={`${row.barcode}:${idx}`}>
                <div>
                  <strong {...dirProps(row.productName || row.barcode)}>
                    {row.productName || (row.barcode ? formatBarcode(row.barcode) : 'Unknown')}
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
