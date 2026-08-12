import { useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '../shared/Button.jsx'
import { formatBarcode, formatDate } from '../../lib/utils/format.js'
import { dirProps } from '../../lib/utils/rtl.js'
import {
  appendEntry,
  knownSuppliers,
  loadQueue,
  makeEntry,
  readLastSupplier,
  rememberLastSupplier,
  saveQueue,
  toCsv,
  todayIso,
  undoLast,
} from '../../lib/receiving/receivingQueue.js'

/**
 * Recording a delivery has to beat writing it on paper. If it does not, the
 * manager stops after a week and every downstream track that needs this data
 * dies with it. That is why the barcode field jumps straight to quantity, why
 * the supplier is remembered between lines, and why nothing here waits on a
 * network call.
 */
export function ReceivingCaptureForm({ products = [] }) {
  const [queue, setQueue] = useState(() => loadQueue())
  const [barcode, setBarcode] = useState('')
  const [quantity, setQuantity] = useState('')
  const [supplier, setSupplier] = useState(() => readLastSupplier())
  const [unitCost, setUnitCost] = useState('')
  const [receivedAt, setReceivedAt] = useState(() => todayIso())
  const [expiryDate, setExpiryDate] = useState('')
  const [error, setError] = useState('')
  const [justAdded, setJustAdded] = useState(null)

  const barcodeRef = useRef(null)
  const quantityRef = useRef(null)

  useEffect(() => saveQueue(queue), [queue])

  // Confirming the right item before committing is the whole point of the
  // lookup — a mis-scan is otherwise invisible until the data is already wrong.
  const byBarcode = useMemo(() => {
    const map = new Map()
    for (const product of products) {
      const code = String(product.id ?? '').replace(/^ym-/, '')
      if (code) map.set(code, product)
    }
    return map
  }, [products])

  const trimmed = barcode.trim()
  const matchedProduct = trimmed
    ? byBarcode.get(trimmed.replace(/^0+/, '')) ?? byBarcode.get(trimmed)
    : null

  const supplierOptions = useMemo(() => knownSuppliers(queue), [queue])

  function handleBarcodeKeyDown(event) {
    if (event.key !== 'Enter') return
    // A barcode gun sends Enter after the digits. Submitting here would save a
    // line with no quantity, so Enter moves to the next field instead.
    event.preventDefault()
    if (trimmed) quantityRef.current?.focus()
  }

  function handleSubmit(event) {
    event.preventDefault()
    let entry
    try {
      entry = makeEntry({
        barcode,
        productName: matchedProduct?.name ?? '',
        quantity,
        supplier,
        unitCost,
        receivedAt,
        expiryDate,
      })
    } catch (err) {
      setError(err.message)
      return
    }

    setQueue((current) => appendEntry(current, entry))
    rememberLastSupplier(entry.supplier)
    setJustAdded(`${entry.quantity} × ${entry.productName || formatBarcode(entry.barcode)}`)
    setError('')

    // Supplier, date and cost carry over — a delivery is usually twenty items
    // from one supplier on one day.
    setBarcode('')
    setQuantity('')
    setExpiryDate('')
    barcodeRef.current?.focus()
  }

  function handleUndo() {
    setQueue((current) => undoLast(current))
    setJustAdded(null)
    setError('')
    barcodeRef.current?.focus()
  }

  function downloadCsv() {
    const blob = new Blob([toCsv(queue)], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `receiving_${todayIso()}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <form className="receiving-capture" onSubmit={handleSubmit}>
        <label className="expiry-field receiving-field-barcode">
          <span>Barcode</span>
          <input
            ref={barcodeRef}
            className="expiry-input"
            value={barcode}
            onChange={(e) => { setBarcode(e.target.value); setJustAdded(null); setError('') }}
            onKeyDown={handleBarcodeKeyDown}
            placeholder="Scan or type"
            inputMode="numeric"
            autoComplete="off"
            aria-describedby="receiving-match"
          />
        </label>

        <label className="expiry-field receiving-field-quantity">
          <span>Quantity *</span>
          <input
            ref={quantityRef}
            className="expiry-input"
            value={quantity}
            onChange={(e) => { setQuantity(e.target.value); setError('') }}
            placeholder="Units"
            inputMode="numeric"
            autoComplete="off"
          />
        </label>

        <label className="expiry-field">
          <span>Supplier *</span>
          <input
            className="expiry-input"
            value={supplier}
            onChange={(e) => { setSupplier(e.target.value); setError('') }}
            list="receiving-suppliers"
            placeholder="From the delivery note"
            autoComplete="off"
          />
          <datalist id="receiving-suppliers">
            {supplierOptions.map((name) => <option key={name} value={name} />)}
          </datalist>
        </label>

        <label className="expiry-field receiving-field-cost">
          <span>Unit cost ₪</span>
          <input
            className="expiry-input"
            value={unitCost}
            onChange={(e) => { setUnitCost(e.target.value); setError('') }}
            placeholder="Optional"
            inputMode="decimal"
            autoComplete="off"
          />
        </label>

        <label className="expiry-field">
          <span>Received *</span>
          <input
            className="expiry-input"
            type="date"
            value={receivedAt}
            onChange={(e) => setReceivedAt(e.target.value)}
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

        <Button tone="primary" {...{ type: 'submit' }}>Save</Button>
      </form>

      <p id="receiving-match" className="expiry-match" aria-live="polite">
        {error && <span className="expiry-match-warn">{error}</span>}
        {!error && trimmed && matchedProduct && (
          <span className="expiry-match-ok" dir="auto">✓ {matchedProduct.name}</span>
        )}
        {!error && trimmed && !matchedProduct && (
          <span className="expiry-match-warn">
            Not found in the catalog — check the barcode. You can still save it.
          </span>
        )}
        {!error && !trimmed && justAdded && (
          <span className="expiry-match-ok" dir="auto">Saved: {justAdded}</span>
        )}
      </p>

      {queue.length > 0 && (
        <>
          <div className="recommendation-actions" style={{ marginTop: '1rem', gap: '0.5rem' }}>
            <Button tone="secondary" onClick={downloadCsv}>
              Download {queue.length} recorded {queue.length === 1 ? 'line' : 'lines'}
            </Button>
            <Button tone="ghost" onClick={handleUndo}>Undo last</Button>
            <Button tone="ghost" onClick={() => setQueue([])}>Clear list</Button>
          </div>
          <p className="page-description" style={{ marginTop: '0.5rem' }}>
            Deliveries are saved on this device and survive closing the app. Send the
            downloaded file to the SmartShelf team to load it in.
          </p>
          <div className="compact-list">
            {queue.slice(0, 10).map((row, idx) => (
              <div className="compact-row" key={`${row.barcode}:${row.recordedAt}:${idx}`}>
                <div>
                  <strong {...dirProps(row.productName || row.barcode)}>
                    {row.productName || formatBarcode(row.barcode)}
                  </strong>
                  <span>{row.quantity} units · {row.supplier}</span>
                </div>
                <div className="compact-row-end date-cell">
                  <small>{formatDate(row.receivedAt)}</small>
                  {row.expiryDate && <small>exp {formatDate(row.expiryDate)}</small>}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}
