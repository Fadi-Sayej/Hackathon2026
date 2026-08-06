import { useEffect, useMemo, useState } from 'react'
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

function isoInDays(days) {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}

export function ExpiryPage({ operationalData, products = [] }) {
  const { expiry } = operationalData
  const buckets = expiry?.buckets ?? {}
  const alerts = expiry?.alerts ?? []

  const [queue, setQueue] = useState(loadQueue)
  const [barcode, setBarcode] = useState('')
  const [expiryDate, setExpiryDate] = useState('')
  const [justAdded, setJustAdded] = useState(null)

  useEffect(() => saveQueue(queue), [queue])

  // Look the product up as soon as a barcode is entered. Staff must be able to confirm
  // they scanned the right thing before saving — otherwise a mis-scan is invisible.
  const byBarcode = useMemo(() => {
    const map = new Map()
    for (const product of products) {
      const code = String(product.id ?? '').replace(/^ym-/, '')
      if (code) map.set(code, product)
    }
    return map
  }, [products])

  const trimmed = barcode.trim()
  const matchedProduct = trimmed ? byBarcode.get(trimmed.replace(/^0+/, '')) ?? byBarcode.get(trimmed) : null

  function addToQueue(event) {
    event.preventDefault()
    if (!trimmed || !expiryDate) return
    setQueue((current) => [
      {
        barcode: trimmed,
        expiryDate,
        productName: matchedProduct?.name ?? null,
        addedAt: new Date().toISOString(),
      },
      ...current,
    ])
    setJustAdded(matchedProduct?.name ?? trimmed)
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
          When goods arrive, enter the barcode and the date on the package. Takes a few seconds
          per item, and it is the only way the system can warn you before something expires —
          the POS export does not contain expiry dates.
        </p>

        <form className="expiry-capture" onSubmit={addToQueue}>
          <label className="expiry-field">
            <span>Barcode</span>
            <input
              className="expiry-input"
              value={barcode}
              onChange={(e) => { setBarcode(e.target.value); setJustAdded(null) }}
              placeholder="Scan or type"
              inputMode="numeric"
              autoComplete="off"
              aria-describedby="expiry-match"
            />
          </label>

          <label className="expiry-field">
            <span>Expiry date</span>
            <input
              className="expiry-input"
              type="date"
              value={expiryDate}
              onChange={(e) => setExpiryDate(e.target.value)}
            />
          </label>

          <Button tone="primary" {...{ type: 'submit' }} disabled={!trimmed || !expiryDate}>
            Save
          </Button>
        </form>

        <div className="expiry-quick">
          <span>Quick date:</span>
          {[
            ['3 days', 3],
            ['1 week', 7],
            ['2 weeks', 14],
            ['1 month', 30],
          ].map(([label, days]) => (
            <Button key={days} tone="ghost" onClick={() => setExpiryDate(isoInDays(days))}>
              {label}
            </Button>
          ))}
        </div>

        <p id="expiry-match" className="expiry-match" aria-live="polite">
          {trimmed && matchedProduct && (
            <span className="expiry-match-ok" dir="auto">✓ {matchedProduct.name}</span>
          )}
          {trimmed && !matchedProduct && (
            <span className="expiry-match-warn">
              Not found in the catalog — check the barcode. You can still save it.
            </span>
          )}
          {!trimmed && justAdded && <span className="expiry-match-ok" dir="auto">Saved: {justAdded}</span>}
        </p>

        {queue.length > 0 && (
          <>
            <div className="recommendation-actions" style={{ marginTop: '1rem', gap: '0.5rem' }}>
              <Button tone="secondary" onClick={downloadCsv}>
                Download {queue.length} recorded {queue.length === 1 ? 'date' : 'dates'}
              </Button>
              <Button tone="ghost" onClick={() => setQueue([])}>Clear list</Button>
            </div>
            <p className="page-description" style={{ marginTop: '0.5rem' }}>
              Dates are saved on this device. Send the downloaded file to the SmartShelf team and
              they will load it in — after that, expiry warnings appear below automatically.
            </p>
            <div className="compact-list">
              {queue.slice(0, 10).map((row, idx) => (
                <div className="compact-row" key={`${row.barcode}:${idx}`}>
                  <div>
                    <strong {...dirProps(row.productName || row.barcode)}>
                      {row.productName || formatBarcode(row.barcode)}
                    </strong>
                    <span>{row.productName ? formatBarcode(row.barcode) : 'not in catalog'}</span>
                  </div>
                  <div className="compact-row-end date-cell"><small>{formatDate(row.expiryDate)}</small></div>
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
