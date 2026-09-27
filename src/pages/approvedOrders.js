/**
 * Approved orders, as data: his recorded approvals joined to the catalogue, and the CSV for his
 * supplier (F8-S1 FR-162, ADR-034 Decision 5). Pure, so the page and the CSV cannot disagree,
 * and kept apart from the page so the page file exports only its component.
 */

const FAMILY = 'order.suggestion'
export const CSV_COLUMNS = ['product', 'barcode', 'quantity', 'order_day']

/** The lines, from recorded outcomes: pure, so the page and the CSV cannot disagree. */
export function approvedLines(outcomes, catalogue, now) {
  const today = new Date(now).toISOString().slice(0, 10)
  const byBarcode = new Map((catalogue?.products || []).filter((p) => p.barcode).map((p) => [String(p.barcode), p]))
  const lines = []
  for (const rec of Object.values(outcomes || {})) {
    const snap = rec?.snapshot || {}
    if (rec?.status !== 'acted' || snap.signal_family !== FAMILY || !snap.order_day || snap.order_day < today) continue
    const product = byBarcode.get(String(snap.barcode))
    const suggested = snap.suggested_quantity ?? null
    const quantity = Number.isFinite(snap.approved_quantity) ? snap.approved_quantity : suggested
    lines.push({ barcode: String(snap.barcode), product: product?.product_name ?? String(snap.barcode),
      department: product?.department ?? null, orderDay: snap.order_day, quantity, suggested,
      changed: Number.isFinite(snap.approved_quantity) && snap.approved_quantity !== suggested })
  }
  return lines.sort((a, b) => a.orderDay.localeCompare(b.orderDay)
    || String(a.department).localeCompare(String(b.department)) || a.product.localeCompare(b.product))
}

const cell = (value) => {
  const text = String(value ?? '')
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

/** product, barcode, quantity, order day: the fields ADR-034 names, and only those. */
export function ordersCsv(lines) {
  return [CSV_COLUMNS.join(','), ...lines.map((l) => [l.product, l.barcode, l.quantity, l.orderDay].map(cell).join(','))]
    .join('\n')
}
