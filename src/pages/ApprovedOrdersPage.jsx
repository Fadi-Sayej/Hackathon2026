import { EmptyState } from '../components/shared/EmptyState.jsx'
import { formatCurrency } from '../components/shared/formatters.js'
import { Button } from '../components/shared/Button.jsx'

export function ApprovedOrdersPage({ approvedOrders, productIndex }) {
  const total = approvedOrders.reduce((sum, recommendation) => {
    const product = productIndex.get(recommendation.productId)
    return sum + (recommendation.recommendedOrderQuantity ?? 0) * (product?.cost ?? 0)
  }, 0)

  function handlePrint() {
    window.print()
  }

  function handleExportCsv() {
    const rows = [
      ['Product', 'Supplier', 'Quantity', 'Unit Cost', 'Total'],
      ...approvedOrders.map((recommendation) => {
        const product = productIndex.get(recommendation.productId)
        const quantity = recommendation.recommendedOrderQuantity ?? 0
        const unitCost = product?.cost ?? 0
        return [
          recommendation.productName,
          product?.supplier ?? 'Preferred supplier',
          quantity,
          unitCost,
          quantity * unitCost,
        ]
      }),
      ['Estimated total', '', '', '', total],
    ]
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
    <section className="panel">
      <div className="panel-heading page-tools">
        <div>
          <p className="eyebrow">Purchase order</p>
          <h2>Approved replenishment list</h2>
        </div>
        <div className="toolbar">
          <Button onClick={handlePrint} tone="ghost">Print</Button>
          <Button onClick={handleExportCsv} tone="primary">Export CSV</Button>
        </div>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Supplier</th>
              <th className="number-cell">Quantity</th>
              <th className="number-cell">Unit Cost</th>
              <th className="number-cell">Total</th>
            </tr>
          </thead>
          <tbody>
            {approvedOrders.map((recommendation) => {
              const product = productIndex.get(recommendation.productId)
              const quantity = recommendation.recommendedOrderQuantity ?? 0
              const unitCost = product?.cost ?? 0
              return (
                <tr key={`${recommendation.productId}:${recommendation.type}`}>
                  <td>
                    <strong>{recommendation.productName}</strong>
                    <span className="muted">{recommendation.type.replace('_', ' ')}</span>
                  </td>
                  <td>{product?.supplier ?? 'Preferred supplier'}</td>
                  <td className="number-cell">{quantity}</td>
                  <td className="number-cell">{formatCurrency(unitCost)}</td>
                  <td className="number-cell">{formatCurrency(quantity * unitCost)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="order-total">
        <span>Estimated total</span>
        <strong>{formatCurrency(total)}</strong>
      </div>
    </section>
  )
}

function escapeCsvValue(value) {
  const text = String(value ?? '')
  if (!/[",\n]/.test(text)) return text
  return `"${text.replaceAll('"', '""')}"`
}
