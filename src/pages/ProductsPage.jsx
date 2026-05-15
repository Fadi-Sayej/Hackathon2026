import { useMemo, useState } from 'react'
import { CompetitorBadge } from '../components/shared/CompetitorBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { formatCurrency, formatDays, statusTone } from '../components/shared/formatters.js'

export function ProductsPage({ analyzedProducts }) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')

  const categories = useMemo(
    () => ['All', ...new Set(analyzedProducts.map((product) => product.category))],
    [analyzedProducts],
  )

  const filteredProducts = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    return analyzedProducts.filter((product) => {
      const matchesCategory = category === 'All' || product.category === category
      const matchesQuery =
        !normalizedQuery ||
        product.name.toLowerCase().includes(normalizedQuery) ||
        product.category.toLowerCase().includes(normalizedQuery)
      return matchesCategory && matchesQuery
    })
  }, [analyzedProducts, category, query])

  return (
    <section className="panel">
      <div className="panel-heading page-tools">
        <div>
          <p className="eyebrow">Product health</p>
          <h2>Inventory table</h2>
        </div>
        <div className="toolbar">
          <input
            aria-label="Search products"
            className="input"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search products"
            value={query}
          />
          <select
            aria-label="Filter category"
            className="input"
            onChange={(event) => setCategory(event.target.value)}
            value={category}
          >
            {categories.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </div>
      </div>

      {filteredProducts.length === 0 ? (
        <EmptyState
          description="No products match the current search and category filter. Clear the search or choose another category to continue."
          title="No matching products"
        />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Category</th>
                <th className="number-cell">Stock</th>
                <th className="number-cell">7d Sales</th>
                <th className="number-cell">30d Sales</th>
                <th className="number-cell">Price</th>
                <th>Stockout</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredProducts.map((product) => (
                <tr key={product.id}>
                  <td>
                    <strong>{product.name}</strong>
                    <span className="muted">Supplier: {product.supplier}</span>
                  </td>
                  <td>{product.category}</td>
                  <td className="number-cell">{product.currentStock}</td>
                  <td className="number-cell">{product.salesLast7Days}</td>
                  <td className="number-cell">{product.salesLast30Days}</td>
                  <td className="number-cell price-cell">
                    <span className="price-value">{formatCurrency(product.price)}</span>
                    <CompetitorBadge competitor={product.competitor} />
                  </td>
                  <td>{formatDays(product.analytics.daysUntilStockout)}</td>
                  <td>
                    <StatusBadge tone={statusTone(product.analytics.primaryStatus)}>
                      {product.analytics.primaryStatus}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
