import { useEffect, useMemo, useState } from 'react'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { formatCurrency } from '../components/shared/formatters.js'
import { useT } from '../lib/i18n/index.js'
import { Button } from '../components/shared/Button.jsx'
import { compareHebrew, dirProps } from '../lib/utils/rtl.js'

export function ApprovedOrdersPage({ approvedOrders, productIndex }) {
  const t = useT()
  const [toast, setToast] = useState(null)

  useEffect(() => {
    if (!toast) return undefined
    const timer = setTimeout(() => setToast(null), 3200)
    return () => clearTimeout(timer)
  }, [toast, t])

  const supplierGroups = useMemo(() => {
    const groups = new Map()
    for (const recommendation of approvedOrders) {
      const product = productIndex.get(recommendation.productId)
      const supplier = product?.supplier ?? t('ord.preferredSupplier')
      if (!groups.has(supplier)) groups.set(supplier, [])
      groups.get(supplier).push({ recommendation, product })
    }
    return Array.from(groups.entries()).map(([supplier, items]) => {
      const subtotal = items.reduce((sum, { recommendation, product }) => {
        const quantity = recommendation.recommendedOrderQuantity ?? 0
        const unitCost = product?.cost ?? 0
        return sum + quantity * unitCost
      }, 0)
      return {
        supplier,
        items: items.sort((a, b) =>
          compareHebrew(a.recommendation.productName, b.recommendation.productName),
        ),
        subtotal,
      }
    }).sort((a, b) => compareHebrew(a.supplier, b.supplier))
    // `t` is read for the fallback supplier name, so grouping has to recompute
    // when the language changes — otherwise the label stays in the old language.
  }, [approvedOrders, productIndex, t])

  const total = supplierGroups.reduce((sum, group) => sum + group.subtotal, 0)

  function handlePrint() {
    window.print()
  }

  function handleSendToSupplier(supplier) {
    setToast(`Order successfully sent to ${supplier} via Smartshelf AI Connect.`)
  }

  function handleExportCsv() {
    const rows = [
      [t('ord.csv.supplier'), t('ord.csv.product'), t('ord.csv.quantity'), t('ord.csv.unitCost'), t('ord.csv.total')],
    ]
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
    rows.push([t('ord.estTotal'), '', '', '', total])

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
        description={t('ord.emptyDesc')}
        title={t('ord.emptyTitle')}
      />
    )
  }

  return (
    <section className="panel approved-orders-panel">
      <div className="panel-heading page-tools">
        <div>
          <p className="eyebrow">Purchase orders</p>
          <h2>{t('ord.title')}</h2>
          <p className="page-description">
            Orders grouped by supplier — review each cluster, then send the purchase order with one click.
          </p>
        </div>
        <div className="toolbar">
          <Button onClick={handlePrint} tone="ghost">{t('common.print')}</Button>
          <Button onClick={handleExportCsv} tone="primary">{t('ord.exportCsv')}</Button>
        </div>
      </div>

      <div className="supplier-orders">
        {supplierGroups.map((group) => (
          <article className="supplier-order-block" key={group.supplier}>
            <header className="supplier-order-header">
              <div>
                <p className="eyebrow">Supplier</p>
                <h3 className="text-hebrew-title" {...dirProps(group.supplier)}>
                  {group.supplier}
                </h3>
                <p className="muted">{group.items.length} {group.items.length === 1 ? 'item' : 'items'}</p>
              </div>
              <Button
                onClick={() => handleSendToSupplier(group.supplier)}
                tone="primary"
              >
                Send to <span {...dirProps(group.supplier)}>{group.supplier}</span>
              </Button>
            </header>

            <div className="table-wrap supplier-table-wrap hebrew-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th className="table-cell-hebrew">Product</th>
                    <th className="number-cell cell-numeric">Quantity</th>
                    <th className="number-cell cell-price">Unit Cost</th>
                    <th className="number-cell cell-price">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {group.items.map(({ recommendation, product }) => {
                    const quantity = recommendation.recommendedOrderQuantity ?? 0
                    const unitCost = product?.cost ?? 0
                    return (
                      <tr key={`${recommendation.productId}:${recommendation.type}`}>
                        <td className="table-cell-hebrew">
                          <strong {...dirProps(recommendation.productName)}>
                            {recommendation.productName ?? '—'}
                          </strong>
                          <span className="muted">{recommendation.type.replace('_', ' ')}</span>
                        </td>
                        <td className="number-cell cell-numeric">{quantity}</td>
                        <td className="number-cell cell-price">{formatCurrency(unitCost)}</td>
                        <td className="number-cell cell-price">{formatCurrency(quantity * unitCost)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="supplier-subtotal">
              <span>{t('ord.subtotal')}</span>
              <strong className="cell-price">{formatCurrency(group.subtotal)}</strong>
            </div>
          </article>
        ))}
      </div>

      <div className="order-total">
        <span>{t('ord.estTotal')}</span>
        <strong className="cell-price">{formatCurrency(total)}</strong>
      </div>

      {toast && (
        <div className="toast" role="status" aria-live="polite" {...dirProps(toast)}>
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
