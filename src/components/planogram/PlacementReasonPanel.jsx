import { useT } from '../../lib/i18n/index.js'
import { formatCurrency, formatDays } from '../shared/formatters.js'
import { getCategoryColor } from './categoryColors.js'
import { compareHebrew, dirProps } from '../../lib/utils/rtl.js'

export function PlacementReasonPanel({
  selectedItem,
  analyzedProducts = [],
  planogramItems = [],
  planogramSummary,
}) {
  const t = useT()
  const product = selectedItem
    ? analyzedProducts.find((entry) => entry.id === selectedItem.productId)
    : null

  if (selectedItem) {
    return (
      <aside className="panel insight-panel">
        <p className="eyebrow">Placement reason</p>
        <h2 className="text-hebrew-title" {...dirProps(selectedItem.productName)}>
          {selectedItem.productName ?? '—'}
        </h2>
        <p {...dirProps(selectedItem.reason)}>{selectedItem.reason ?? '—'}</p>
        {product && (
          <dl className="insight-list">
            <div>
              <dt>Sales velocity</dt>
              <dd className="numeric-cell">
                {product.analytics.weightedAvgDailySales ?? '—'} units/day
              </dd>
            </div>
            <div>
              <dt>Margin</dt>
              <dd className="price-cell">{formatCurrency(product.analytics.margin)}</dd>
            </div>
            <div>
              <dt>Stockout risk</dt>
              <dd className="numeric-cell">{formatDays(product.analytics.daysUntilStockout, t)}</dd>
            </div>
            <div>
              <dt>Expiry risk</dt>
              <dd>
                {product.analytics.statuses.includes('Near expiry') ? 'Near expiry' : 'Normal'}
              </dd>
            </div>
          </dl>
        )}
      </aside>
    )
  }

  // ── Default insights summary (no selection) ──────────────────────────
  const productIndex = new Map(analyzedProducts.map((entry) => [entry.id, entry]))

  const itemsWithVelocity = planogramItems.map((item) => ({
    ...item,
    dailySales: productIndex.get(item.productId)?.analytics?.weightedAvgDailySales ?? 0,
  }))

  const topMovers = itemsWithVelocity
    .slice()
    .sort((a, b) => b.dailySales - a.dailySales || compareHebrew(a.productName, b.productName))
    .slice(0, 3)

  const eyeLevelDailySales = round(
    itemsWithVelocity
      .filter((item) => item.shelfLevel === 'EYE_LEVEL')
      .reduce((sum, item) => sum + item.dailySales, 0),
  )

  const totalItems = planogramSummary?.totalItems ?? planogramItems.length

  return (
    <aside className="panel insight-panel insight-panel-default">
      <p className="eyebrow">Planogram overview</p>
      <h2>Shelf summary</h2>

      <dl className="insight-list">
        <div>
          <dt>Total products</dt>
          <dd>{totalItems}</dd>
        </div>
        <div>
          <dt>Eye Level daily sales</dt>
          <dd>{eyeLevelDailySales} units/day</dd>
        </div>
      </dl>

      <div className="insight-section">
        <p className="eyebrow">Top movers</p>
        <ul className="top-movers-list">
          {topMovers.length === 0 ? (
            <li className="top-movers-empty">No velocity data yet.</li>
          ) : (
            topMovers.map((item, index) => (
              <li key={item.productId} className="top-movers-row">
                <span className="top-movers-rank">{index + 1}</span>
                <span
                  className="top-movers-swatch"
                  aria-hidden="true"
                  style={{ background: getCategoryColor(item.category) }}
                />
                <span className="top-movers-name">
                  <strong {...dirProps(item.productName)}>{item.productName ?? '—'}</strong>
                  <small {...dirProps(item.category)}>{item.category ?? '—'}</small>
                </span>
                <span className="top-movers-velocity numeric-cell">{item.dailySales}/day</span>
              </li>
            ))
          )}
        </ul>
      </div>

      <p className="insight-tip muted">Click any product to see its placement reasoning.</p>
    </aside>
  )
}

function round(value) {
  return Math.round(value * 100) / 100
}
