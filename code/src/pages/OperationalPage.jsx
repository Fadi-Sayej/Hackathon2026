import { useMemo, useState } from 'react'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { Button } from '../components/shared/Button.jsx'

const TYPE_META = {
  PROMOTE_EXPIRING_PRODUCT: { label: 'Expiring', tone: 'danger' },
  CHECK_NEGATIVE_STOCK: { label: 'Negative stock', tone: 'danger' },
  CHECK_WOLT_PRICE_GAP: { label: 'WOLT price gap', tone: 'warning' },
  CHECK_MARGIN: { label: 'Margin risk', tone: 'warning' },
  VERIFY_UNKNOWN_BARCODE: { label: 'Unknown barcode', tone: 'info' },
  PRICE_CHECK: { label: 'Price check', tone: 'warning' },
  REORDER: { label: 'Reorder', tone: 'success' },
  WATCH_PRODUCT: { label: 'Watch', tone: 'info' },
}

const SOURCE_STATUS_TONE = {
  complete: 'success',
  partial: 'warning',
  running: 'warning',
  not_started: 'neutral',
  error: 'danger',
}

const SCRAPING_LABEL = {
  complete: 'Scraping complete',
  partial: 'Scraping partial — some sources pending',
  running: 'Scraping running…',
  not_started: 'Scraping not started',
}

const MAX_ROWS = 60

function recDetail(rec) {
  switch (rec.type) {
    case 'CHECK_WOLT_PRICE_GAP':
      return `Shelf ${rec.sellingPrice} → WOLT ${rec.woltPrice} (gap ${rec.metricValue}%)`
    case 'CHECK_MARGIN':
      return `Sell ${rec.sellingPrice} · Cost ${rec.costPrice} · Margin ${rec.metricValue}%`
    case 'CHECK_NEGATIVE_STOCK':
      return `On-hand stock ${rec.currentStock}`
    case 'PROMOTE_EXPIRING_PRODUCT':
      return `Expiry ${rec.expiryDate} · ${rec.daysToExpiry} days · stock ${rec.currentStock}`
    case 'VERIFY_UNKNOWN_BARCODE':
      return rec.barcode ? `Barcode ${rec.barcode}` : 'No barcode in catalog'
    default:
      if (rec.competitorPrice != null) {
        return `Local ${rec.sellingPrice} vs competitor ${rec.competitorPrice}`
      }
      return rec.reason ?? ''
  }
}

export function OperationalPage({ operationalData, operationalStatus }) {
  const { meta, posHealth, byFamily, sources, recommendations } = operationalData
  const [activeFamily, setActiveFamily] = useState('ALL')
  const [activeType, setActiveType] = useState('ALL')

  const familyFiltered = useMemo(
    () =>
      activeFamily === 'ALL'
        ? recommendations
        : recommendations.filter((rec) => rec.family === activeFamily),
    [recommendations, activeFamily],
  )

  const typeCounts = useMemo(() => {
    const counts = {}
    for (const rec of familyFiltered) counts[rec.type] = (counts[rec.type] ?? 0) + 1
    return counts
  }, [familyFiltered])

  const types = useMemo(
    () => Object.keys(typeCounts).sort((a, b) => typeCounts[b] - typeCounts[a]),
    [typeCounts],
  )

  const visible = useMemo(() => {
    const filtered =
      activeType === 'ALL'
        ? familyFiltered
        : familyFiltered.filter((rec) => rec.type === activeType)
    return filtered.slice(0, MAX_ROWS)
  }, [familyFiltered, activeType])

  const total = recommendations.length
  const filteredTotal = familyFiltered.length
  const families = Object.keys(byFamily ?? {})

  if (operationalStatus === 'loading') {
    return <EmptyState title="Loading operational data" description="Reading the latest pipeline export…" />
  }

  if (total === 0) {
    return (
      <EmptyState
        title="No operational data yet"
        description="Run `npm run data:refresh` to populate this view. It updates automatically as scraping and imports complete."
      />
    )
  }

  return (
    <>
      <section className="metric-grid">
        <MetricCard label="Total Products" value={posHealth.totalProducts} detail={posHealth.sourceFile ?? 'POS catalog'} />
        <MetricCard label="WOLT Price Gaps" value={posHealth.woltPriceGaps} detail="Shelf vs WOLT > 5%" tone="warning" />
        <MetricCard label="Negative Stock" value={posHealth.negativeStock} detail="POS data to verify" tone="danger" />
        <MetricCard label="Margin Risks" value={posHealth.marginRisks} detail="Thin or negative margin" tone="warning" />
        <MetricCard label="Missing Barcode" value={posHealth.missingBarcode} detail="Can't scan or match" tone="info" />
        <MetricCard label="Total Actions" value={total} detail="Operational + competitor" tone="success" />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Data sources</p>
            <h2>{SCRAPING_LABEL[meta.scrapingStatus] ?? 'Source status'}</h2>
          </div>
          <span className="metric-chip">
            {meta.generatedAt ? `Updated ${new Date(meta.generatedAt).toLocaleString()}` : 'Static export'}
          </span>
        </div>
        <div className="recommendation-actions" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
          {(sources ?? []).map((src) => (
            <StatusBadge key={src.source_id} tone={SOURCE_STATUS_TONE[src.status] ?? 'neutral'}>
              {src.label}: {src.status}{src.row_count ? ` (${src.row_count})` : ''}
            </StatusBadge>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Pipeline output</p>
            <h2>Recommendations</h2>
          </div>
        </div>

        {families.length > 1 && (
          <div className="recommendation-actions" style={{ flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <Button tone={activeFamily === 'ALL' ? 'primary' : 'ghost'} onClick={() => { setActiveFamily('ALL'); setActiveType('ALL') }}>
              All families ({total})
            </Button>
            {families.map((fam) => (
              <Button
                key={fam}
                tone={activeFamily === fam ? 'primary' : 'ghost'}
                onClick={() => { setActiveFamily(fam); setActiveType('ALL') }}
              >
                {fam} ({byFamily[fam]})
              </Button>
            ))}
          </div>
        )}

        <div className="recommendation-actions" style={{ flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
          <Button tone={activeType === 'ALL' ? 'primary' : 'ghost'} onClick={() => setActiveType('ALL')}>
            All ({filteredTotal})
          </Button>
          {types.map((type) => (
            <Button
              key={type}
              tone={activeType === type ? 'primary' : 'ghost'}
              onClick={() => setActiveType(type)}
            >
              {(TYPE_META[type]?.label ?? type)} ({typeCounts[type]})
            </Button>
          ))}
        </div>

        <div className="compact-list">
          {visible.map((rec) => (
            <div className="compact-row" key={rec.id}>
              <div>
                <strong>{rec.productName || rec.barcode || 'Unknown item'}</strong>
                <span>{rec.category || recDetail(rec)}</span>
              </div>
              <div className="compact-row-end">
                <StatusBadge tone={TYPE_META[rec.type]?.tone ?? 'neutral'}>
                  {TYPE_META[rec.type]?.label ?? rec.type}
                </StatusBadge>
                <small>{Math.round((rec.confidence ?? 0) * 100)}% · {recDetail(rec)}</small>
              </div>
            </div>
          ))}
        </div>
        {filteredTotal > visible.length && (
          <p className="page-description">
            Showing {visible.length} of {activeType === 'ALL' ? filteredTotal : typeCounts[activeType]} — refine by type above.
          </p>
        )}
      </section>
    </>
  )
}
