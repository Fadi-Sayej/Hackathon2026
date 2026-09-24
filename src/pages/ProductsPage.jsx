import { useMemo, useState } from 'react'
import { useT } from '../lib/i18n/index.js'
import { CompetitorBadge } from '../components/shared/CompetitorBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { formatCurrency, formatDays, formatStatus, statusTone } from '../components/shared/formatters.js'
import { compareHebrew, dirProps } from '../lib/utils/rtl.js'

/**
 * How many rows reach the DOM at once.
 *
 * Measured, not guessed. Before this cap the page rendered all 7,523 catalogue rows —
 * 98,044 DOM nodes — and took 4.9 SECONDS to show its first row at 390px with the CPU
 * throttled 4× to stand in for a mid-range phone. The owner would have read that as broken.
 * The list is not browsable at that length anyway: nobody scrolls seven thousand rows, they
 * search. So the table shows a bounded slice and says plainly how much it is not showing.
 */
const VISIBLE_ROWS = 250

export function ProductsPage({ analyzedProducts }) {
  const t = useT()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')

  const categories = useMemo(
    () => [
      'All',
      ...new Set(analyzedProducts.map((product) => product.category).filter(Boolean)),
    ].sort((a, b) => {
      if (a === 'All') return -1
      if (b === 'All') return 1
      return compareHebrew(a, b)
    }),
    [analyzedProducts],
  )

  const filteredProducts = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    return analyzedProducts.filter((product) => {
      const matchesCategory = category === 'All' || product.category === category
      // Null-guarded on both. The catalogue adapter publishes `name`/`category` as null
      // where the export has none (D-3), and today every row has both — so this is latent,
      // not live. It would surface as the search box throwing on the first export with a
      // missing department, which is a bad way to find out.
      const matchesQuery =
        !normalizedQuery ||
        (product.name || '').toLowerCase().includes(normalizedQuery) ||
        (product.category || '').toLowerCase().includes(normalizedQuery)
      return matchesCategory && matchesQuery
    }).sort((a, b) => compareHebrew(a.name, b.name))
  }, [analyzedProducts, category, query])

  const visibleProducts = filteredProducts.slice(0, VISIBLE_ROWS)

  return (
    <section className="panel">
      <div className="panel-heading page-tools">
        <div>
          <p className="eyebrow">{t('eb.productHealth')}</p>
          <h2>{t('prod.tableTitle')}</h2>
        </div>
        <div className="toolbar">
          <input
            aria-label={t('prod.searchLabel')}
            className="input"
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('prod.searchLabel')}
            value={query}
          />
          <select
            aria-label={t('prod.filterLabel')}
            className="input"
            onChange={(event) => setCategory(event.target.value)}
            value={category}
          >
            {categories.map((item) => (
              <option key={item} {...dirProps(item)}>{item}</option>
            ))}
          </select>
        </div>
      </div>

      {filteredProducts.length === 0 ? (
        <EmptyState
          description={t('prod.emptyDesc')}
          title={t('prod.emptyTitle')}
        />
      ) : (
        <div className="table-wrap hebrew-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th className="table-cell-hebrew">Product</th>
                <th className="table-cell-hebrew">Category</th>
                <th className="number-cell cell-numeric">Stock</th>
                <th className="number-cell cell-numeric">7d Sales</th>
                <th className="number-cell cell-numeric">30d Sales</th>
                <th className="number-cell cell-price">Price</th>
                <th className="cell-numeric">Stockout</th>
                <th>{t('prod.status')}</th>
              </tr>
            </thead>
            <tbody>
              {/* Ids come from catalogueToProducts: `b:<barcode>`, or `n:<name>` for a row
                  with no barcode (ADR-022). Two unbarcoded rows with one name would collide,
                  so the index stays in the key. None do today: 7,523 rows, 7,523 distinct
                  ids, measured on 2026-09-24. */}
              {visibleProducts.map((product, index) => (
                <tr key={`${product.id}:${index}`}>
                  <td className="table-cell-hebrew">
                    <strong {...dirProps(product.name)}>{product.name ?? '—'}</strong>
                    <span className="muted" {...dirProps(product.supplier)}>
                      Supplier: {product.supplier ?? '—'}
                    </span>
                  </td>
                  <td className="table-cell-hebrew" {...dirProps(product.category)}>
                    {product.category ?? '—'}
                  </td>
                  <td className="number-cell cell-numeric">{product.currentStock ?? '—'}</td>
                  <td className="number-cell cell-numeric">{product.salesLast7Days ?? '—'}</td>
                  <td className="number-cell cell-numeric">{product.salesLast30Days ?? '—'}</td>
                  <td className="number-cell price-cell cell-price">
                    <span className="price-value">{formatCurrency(product.price)}</span>
                    <CompetitorBadge competitor={product.competitor} />
                  </td>
                  <td className="cell-numeric">{formatDays(product.analytics.daysUntilStockout, t)}</td>
                  <td>
                    <StatusBadge tone={statusTone(product.analytics.primaryStatus)}>
                      {formatStatus(product.analytics.primaryStatus, t)}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredProducts.length > VISIBLE_ROWS && (
            /* Said rather than implied. A table that silently stops at 250 of 7,523 teaches
               the reader that a product is absent when it is merely further down. */
            <p className="page-description products-truncated">
              {t('prod.showingCapped', {
                shown: visibleProducts.length,
                total: filteredProducts.length,
              })}
            </p>
          )}
        </div>
      )}
    </section>
  )
}
