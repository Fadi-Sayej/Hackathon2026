import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'
import { approvedLines, ordersCsv } from './approvedOrders.js'
import { loadOrderExample } from '../lib/dataAdapters/loadOrderExample.js'
import { ExamplePreview } from './OrderExample.jsx'

/**
 * Approved orders: what he approved for his suppliers (F8-S1 FR-162), as the repository owner
 * approved the screen on 2026-09-27 (docs/reviews/F8-screens-mockups.md).
 *
 * A projection and nothing more (ADR-034 Decision 5): his recorded `acted` outcomes on
 * `order.suggestion`, for an order day still to come, joined to the catalogue for the product's
 * name and department (ADR-024). The quantity is his when he changed it, otherwise the one
 * suggested. No price, no subtotal, no total (D-1, INV-069); nothing is written to his POS (D-7).
 */

const LOCALE = { ar: 'ar-u-nu-latn', he: 'he-IL', en: 'en-GB' }

function download(lines) {
  // The byte-order mark lets a spreadsheet read the Hebrew names as UTF-8.
  const blob = new Blob(['﻿', ordersCsv(lines), '\n'], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `approved-orders-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function ApprovedOrdersPage({ ownerState, catalogue, now, example = false, loadExample = loadOrderExample }) {
  const { t, language } = useI18n()
  const locale = LOCALE[language] || LOCALE.en
  const day = (iso) => new Intl.DateTimeFormat(locale, { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })
    .format(new Date(`${iso}T00:00:00Z`))
  const lines = approvedLines(ownerState?.outcomes, catalogue, now)
  const byDepartment = new Map()
  for (const line of lines) {
    if (!byDepartment.has(line.department)) byDepartment.set(line.department, [])
    byDepartment.get(line.department).push(line)
  }

  return (
    <section className="orders" {...dirProps()}>
      <p className="reorder__line">{t('orders.lead')}</p>
      {[...byDepartment.entries()].map(([department, rows]) => (
        <section key={String(department)} className="orders__department" data-department={department ?? ''}>
          <h2><bdi>{department}</bdi></h2>
          <div className="orders__table-wrap">
            <table className="orders__table">
              <thead>
                <tr><th>{t('orders.product')}</th><th>{t('orders.quantity')}</th><th>{t('orders.day')}</th></tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={`${row.barcode}|${row.orderDay}`}>
                    <td><bdi>{row.product}</bdi></td>
                    <td className="orders__quantity">
                      {row.quantity}
                      {row.changed ? <span className="orders__changed">{t('orders.changed', { n: row.suggested })}</span> : null}
                    </td>
                    <td>{day(row.orderDay)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
      <div>
        <button type="button" className="reorder__approve" data-action="csv" disabled={example || lines.length === 0}
          onClick={() => !example && download(lines)}>
          {t('orders.csv')}
        </button>
      </div>
      {/* D-29: before anything is approved, the page as it will look, from a test shop. */}
      {!example && lines.length === 0 ? (
        <ExamplePreview load={loadExample} render={(shop) => (
          <ApprovedOrdersPage ownerState={shop.owner_state} catalogue={shop.catalogue} now={Date.parse(shop.now)} example />
        )} />
      ) : null}
    </section>
  )
}
