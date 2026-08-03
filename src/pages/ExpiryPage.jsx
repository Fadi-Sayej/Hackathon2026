import { useEffect, useState } from 'react'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { Button } from '../components/shared/Button.jsx'
import { formatBarcode, formatDate } from '../lib/utils/format.js'
import { dirProps } from '../lib/utils/rtl.js'

const SEVERITY_TONE = {
  expired: 'danger',
  critical_7d: 'danger',
  warning_14d: 'warning',
  upcoming_30d: 'info',
  later: 'neutral',
}

const QUEUE_KEY = 'expiry_scan_queue'

function loadQueue() {
  try {
    const raw = localStorage.getItem(QUEUE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveQueue(queue) {
  try {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
  } catch {
    /* ignore quota errors in the demo */
  }
}

function toCsv(queue) {
  const header = 'barcode,expiry_date'
  const rows = queue.map((row) => `${row.barcode},${row.expiryDate}`)
  return [header, ...rows].join('\n') + '\n'
}

export function ExpiryPage({ operationalData }) {
  const { expiry } = operationalData
  const buckets = expiry?.buckets ?? {}
  const alerts = expiry?.alerts ?? []

  const [queue, setQueue] = useState(loadQueue)
  const [barcode, setBarcode] = useState('')
  const [expiryDate, setExpiryDate] = useState('')

  useEffect(() => saveQueue(queue), [queue])

  function addToQueue(event) {
    event.preventDefault()
    if (!barcode.trim() || !expiryDate) return
    setQueue((current) => [
      { barcode: barcode.trim(), expiryDate, addedAt: new Date().toISOString() },
      ...current,
    ])
    setBarcode('')
    setExpiryDate('')
  }

  function downloadCsv() {
    const blob = new Blob([toCsv(queue)], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `expiry_scans_${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

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
            <h2>Record expiry at intake</h2>
          </div>
        </div>
        <p className="page-description">
          <strong>Expiry risk, not batch count.</strong> Each scan records one barcode + date.
          Quantities use current POS stock as an estimate — this is a risk signal, not a
          batch-accurate inventory.
        </p>

        <form className="recommendation-actions" onSubmit={addToQueue} style={{ flexWrap: 'wrap', gap: '0.5rem', alignItems: 'flex-end' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <span>Barcode</span>
            <input value={barcode} onChange={(e) => setBarcode(e.target.value)} placeholder="Scan or type barcode" />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <span>Expiry date</span>
            <input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
          </label>
          <Button tone="primary" {...{ type: 'submit' }}>Add to queue</Button>
          <Button tone="secondary" onClick={downloadCsv} disabled={queue.length === 0}>
            Download CSV ({queue.length})
          </Button>
          {queue.length > 0 && (
            <Button tone="ghost" onClick={() => setQueue([])}>Clear queue</Button>
          )}
        </form>

        {queue.length > 0 && (
          <>
            <p className="page-description" style={{ marginTop: '1rem' }}>
              Then ingest: <code>python scripts/record_expiry_scan.py --input-csv &lt;downloaded.csv&gt;</code> →
              <code> npm run data:refresh</code>
            </p>
            <div className="compact-list">
              {queue.slice(0, 10).map((row, idx) => (
                <div className="compact-row" key={`${row.barcode}:${idx}`}>
                  <div>
                    <strong className="barcode-cell">{formatBarcode(row.barcode)}</strong>
                    <span>queued</span>
                  </div>
                  <div className="compact-row-end date-cell">
                    <small>{formatDate(row.expiryDate)}</small>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
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
                  <span>{row.knownInPos ? `stock ${row.currentStock ?? '—'}` : 'not in POS'}</span>
                </div>
                <div className="compact-row-end">
                  <StatusBadge tone={SEVERITY_TONE[row.severity] ?? 'neutral'}>{row.severity}</StatusBadge>
                  <small className="date-cell">
                    {formatDate(row.expiryDate)} · {row.daysToExpiry ?? '—'} days
                  </small>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  )
}
