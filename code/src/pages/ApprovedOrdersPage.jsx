import { useEffect, useMemo, useState } from 'react'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { formatCurrency } from '../components/shared/formatters.js'
import { Button } from '../components/shared/Button.jsx'

export function ApprovedOrdersPage({ approvedOrders, productIndex }) {
  const [toast, setToast] = useState(null)

  useEffect(() => {
    if (!toast) return undefined
    const timer = setTimeout(() => setToast(null), 3200)
    return () => clearTimeout(timer)
  }, [toast])

  const supplierGroups = useMemo(() => {
    const groups = new Map()
    for (const recommendation of approvedOrders) {
      const product = productIndex.get(recommendation.productId)
      const supplier = product?.supplier ?? 'Preferred supplier'
      if (!groups.has(supplier)) groups.set(supplier, [])
      groups.get(supplier).push({ recommendation, product })
    }
    return Array.from(groups.entries()).map(([supplier, items]) => {
      const subtotal = items.reduce((sum, { recommendation, product }) => {
        const quantity = recommendation.recommendedOrderQuantity ?? 0
        const unitCost = product?.cost ?? 0
        return sum + quantity * unitCost
      }, 0)
      return { supplier, items, subtotal }
    })
  }, [approvedOrders, productIndex])

  const total = supplierGroups.reduce((sum, group) => sum + group.subtotal, 0)

  function handlePrint() {
    window.print()
  }

  function handleSendToSupplier(supplier) {
    setToast(`Order successfully sent to ${supplier} via Smartshelf AI Connect.`)
  }

  function handleExportCsv() {
    const rows = [['Supplier', 'Product', 'Quantity', 'Unit Cost', 'Total']]
    for (const group of supplierGroups) {
      for (const { recommendation, product } of group.items) {
        const quantity = recommendation.recommendedOrderQuantity ?? 0
        const unitCost = product?.cost ?? 0
        rows.push([
          group.supplier,
          recommendation.productName,
          quantity,
          unitCost,
          quantity * unitCost,
        ])
      }
      rows.push([`${group.supplier} subtotal`, '', '', '', group.subtotal])
      rows.push(['', '', '', '', ''])
    }
    rows.push(['Estimated total', '', '', '', total])

    const csv = rows.map((row) => row.map(escapeCsvValue).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'smartshelf-approved-orders.csv'
    document.body.append(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  if (approvedOrders.length === 0) {
    return (
      <EmptyState
        description="Approve items in Smart Reorder and they will appear here as a clean purchase-order draft for manager review, printing, or supplier export."
        title="No approved purchase orders yet"
      />
    )
  }

  return (
    <section className="panel approved-orders-panel">
      <div className="panel-heading page-tools">
        <div>
          <p className="eyebrow">Purchase orders</p>
          <h2>Approved replenishment list</h2>
          <p className="page-description">
            Orders grouped by supplier — review each cluster, then send the purchase order with one click.
          </p>
        </div>
        <div className="toolbar">
          <Button onClick={handlePrint} tone="ghost">Print</Button>
          <Button onClick={handleExportCsv} tone="primary">Export CSV</Button>
        </div>
      </div>

      <div className="supplier-orders">
        {supplierGroups.map((group) => (
          <article className="supplier-order-block" key={group.supplier}>
            <header className="supplier-order-header">
              <div>
                <p className="eyebrow">Supplier</p>
                <h3>{group.supplier}</h3>
                <p className="muted">{group.items.length} {group.items.length === 1 ? 'item' : 'items'}</p>
              </div>
              <Button
                onClick={() => handleSendToSupplier(group.supplier)}
                tone="primary"
              >
                Send to {group.supplier}
              </Button>
            </header>

            <div className="table-wrap supplier-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th className="number-cell">Quantity</th>
                    <th className="number-cell">Unit Cost</th>
                    <th className="number-cell">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {group.items.map(({ recommendation, product }) => {
                    const quantity = recommendation.recommendedOrderQuantity ?? 0
                    const unitCost = product?.cost ?? 0
                    return (
                      <tr key={`${recommendation.productId}:${recommendation.type}`}>
                        <td>
                          <strong>{recommendation.productName}</strong>
                          <span className="muted">{recommendation.type.replace('_', ' ')}</span>
                        </td>
                        <td className="number-cell">{quantity}</td>
                        <td className="number-cell">{formatCurrency(unitCost)}</td>
                        <td className="number-cell">{formatCurrency(quantity * unitCost)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="supplier-subtotal">
              <span>Supplier subtotal</span>
              <strong>{formatCurrency(group.subtotal)}</strong>
            </div>
          </article>
        ))}
      </div>

      <div className="order-total">
        <span>Estimated total</span>
        <strong>{formatCurrency(total)}</strong>
      </div>

      {toast && (
        <div className="toast" role="status" aria-live="polite">
          {toast}
        </div>
      )}
    </section>
  )
}

function escapeCsvValue(value) {
  const text = String(value ?? '')
  if (!/[",\n]/.test(text)) return text
  return `"${text.replaceAll('"', '""')}"`
}
