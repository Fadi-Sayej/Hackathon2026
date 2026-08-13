import { useEffect, useMemo, useRef, useState } from 'react'
import { useNumbers, useT } from '../../lib/i18n/index.js'
import { Button } from '../shared/Button.jsx'
import { formatBarcode, formatDate } from '../../lib/utils/format.js'
import { dirProps } from '../../lib/utils/rtl.js'
import {
  CAPTURE_MODE_DELIVERY,
  CAPTURE_MODE_EXPIRY,
  EXPIRY_QUEUE_KEY,
  RECEIVING_QUEUE_KEY,
  appendEntry,
  exportForMode,
  getStorage,
  isExpiryOnlyMode,
  knownSuppliers,
  loadQueue,
  makeEntryForMode,
  readLastSupplier,
  rememberLastSupplier,
  saveQueue,
  todayIso,
  undoLast,
} from '../../lib/receiving/receivingQueue.js'

/**
 * Recording a delivery has to beat writing it on paper. If it does not, the
 * manager stops after a week and every downstream track that needs this data
 * dies with it. That is why the barcode field jumps straight to the next field,
 * why the supplier is remembered between lines, and why nothing here waits on a
 * network call.
 *
 * Two capture modes share this one screen. A delivery (the default) is goods
 * arriving and needs a quantity and a supplier. An expiry-only line is a date
 * read off something already on the shelf: no delivery happened, so there is
 * nobody to name as the supplier, and demanding one would only get a made-up
 * name typed into the ledger. They are separate queues and separate exports
 * because they feed two different Python importers.
 */
export function ReceivingCaptureForm({ products = [] }) {
  const t = useT()
  const { n } = useNumbers()
  const [mode, setMode] = useState(CAPTURE_MODE_DELIVERY)
  const [deliveryQueue, setDeliveryQueue] = useState(() =>
    loadQueue(getStorage(), RECEIVING_QUEUE_KEY),
  )
  const [expiryQueue, setExpiryQueue] = useState(() => loadQueue(getStorage(), EXPIRY_QUEUE_KEY))
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
  const expiryRef = useRef(null)

  const expiryOnly = isExpiryOnlyMode(mode)
  const queue = expiryOnly ? expiryQueue : deliveryQueue
  const setQueue = expiryOnly ? setExpiryQueue : setDeliveryQueue

  useEffect(() => saveQueue(deliveryQueue, getStorage(), RECEIVING_QUEUE_KEY), [deliveryQueue])
  useEffect(() => saveQueue(expiryQueue, getStorage(), EXPIRY_QUEUE_KEY), [expiryQueue])

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

  const supplierOptions = useMemo(() => knownSuppliers(deliveryQueue), [deliveryQueue])

  function switchMode(next) {
    setMode(next)
    setError('')
    setJustAdded(null)
    barcodeRef.current?.focus()
  }

  function handleBarcodeKeyDown(event) {
    if (event.key !== 'Enter') return
    // A barcode gun sends Enter after the digits. Submitting here would save a
    // line with no quantity, so Enter moves to the next field instead.
    event.preventDefault()
    if (!trimmed) return
    if (expiryOnly) expiryRef.current?.focus()
    else quantityRef.current?.focus()
  }

  function handleSubmit(event) {
    event.preventDefault()
    let entry
    try {
      entry = makeEntryForMode(mode, {
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
    const label = entry.productName || formatBarcode(entry.barcode)
    if (expiryOnly) {
      setJustAdded(`${label} — expires ${entry.expiryDate}`)
    } else {
      rememberLastSupplier(entry.supplier)
      setJustAdded(`${entry.quantity} × ${label}`)
    }
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
    const { filename, csv } = exportForMode(mode, queue)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  }

  // Most shelf-life dates a worker reads are a few days or a few weeks out, and
  // a date picker on a phone is several taps. todayIso() is the local calendar
  // date of whatever Date it is given, which is what the <input type="date">
  // expects — a UTC-derived string would set the wrong day after midnight local.
  function setExpiryInDays(days) {
    const date = new Date()
    date.setDate(date.getDate() + days)
    setExpiryDate(todayIso(date))
    setError('')
  }

  return (
    <>
      <div
        className="receiving-mode"
        role="radiogroup"
        aria-label={t('rc.whatRecording')}
      >
        <label>
          <input
            type="radio"
            name="capture-mode"
            checked={!expiryOnly}
            onChange={() => switchMode(CAPTURE_MODE_DELIVERY)}
          />
          <span>{t('rc.delivery')}</span>
        </label>
        <label>
          <input
            type="radio"
            name="capture-mode"
            checked={expiryOnly}
            onChange={() => switchMode(CAPTURE_MODE_EXPIRY)}
          />
          <span>{t('rc.expiryOnly')}</span>
        </label>
      </div>

      <form
        className={expiryOnly ? 'expiry-capture' : 'receiving-capture'}
        onSubmit={handleSubmit}
      >
        <label className="expiry-field receiving-field-barcode">
          <span>{t('rc.barcode')}</span>
          <input
            ref={barcodeRef}
            className="expiry-input"
            value={barcode}
            onChange={(e) => { setBarcode(e.target.value); setJustAdded(null); setError('') }}
            onKeyDown={handleBarcodeKeyDown}
            placeholder={t('rc.scanOrType')}
            inputMode="numeric"
            autoComplete="off"
            aria-describedby="receiving-match"
          />
        </label>

        {!expiryOnly && (
          <>
            <label className="expiry-field receiving-field-quantity">
              <span>{t('rc.quantity')}</span>
              <input
                ref={quantityRef}
                className="expiry-input"
                value={quantity}
                onChange={(e) => { setQuantity(e.target.value); setError('') }}
                placeholder={t('rc.units')}
                inputMode="numeric"
                autoComplete="off"
              />
            </label>

            <label className="expiry-field">
              <span>{t('rc.supplier')}</span>
              <input
                className="expiry-input"
                value={supplier}
                onChange={(e) => { setSupplier(e.target.value); setError('') }}
                list="receiving-suppliers"
                placeholder={t('rc.fromNote')}
                autoComplete="off"
              />
              <datalist id="receiving-suppliers">
                {supplierOptions.map((name) => <option key={name} value={name} />)}
              </datalist>
            </label>

            <label className="expiry-field receiving-field-cost">
              <span>{t('rc.unitCost')}</span>
              <input
                className="expiry-input"
                value={unitCost}
                onChange={(e) => { setUnitCost(e.target.value); setError('') }}
                placeholder={t('rc.optional')}
                inputMode="decimal"
                autoComplete="off"
              />
            </label>

            <label className="expiry-field">
              <span>{t('rc.received')}</span>
              <input
                className="expiry-input"
                type="date"
                value={receivedAt}
                onChange={(e) => setReceivedAt(e.target.value)}
              />
            </label>
          </>
        )}

        <label className="expiry-field">
          <span>{expiryOnly ? t('rc.expiryDateReq') : t('rc.expiryDate')}</span>
          <input
            ref={expiryRef}
            className="expiry-input"
            type="date"
            value={expiryDate}
            onChange={(e) => { setExpiryDate(e.target.value); setError('') }}
          />
        </label>

        <Button tone="primary" {...{ type: 'submit' }}>{t('common.save')}</Button>
      </form>

      {expiryOnly && (
        <div className="expiry-quick">
          <span>{t('rc.quickDate')}</span>
          {[
            ['rc.d3', 3],
            ['rc.w1', 7],
            ['rc.w2', 14],
            ['rc.m1', 30],
          ].map(([key, days]) => (
            <Button key={days} tone="ghost" onClick={() => setExpiryInDays(days)}>
              {t(key)}
            </Button>
          ))}
        </div>
      )}

      <p id="receiving-match" className="expiry-match" aria-live="polite">
        {error && <span className="expiry-match-warn">{error}</span>}
        {!error && trimmed && matchedProduct && (
          <span className="expiry-match-ok" dir="auto">✓ {matchedProduct.name}</span>
        )}
        {!error && trimmed && !matchedProduct && (
          <span className="expiry-match-warn">
            {t('rc.notInCatalog')}
          </span>
        )}
        {!error && !trimmed && justAdded && (
          <span className="expiry-match-ok" dir="auto">{t('rc.savedItem', { name: justAdded })}</span>
        )}
      </p>

      {queue.length > 0 && (
        <>
          <div className="recommendation-actions" style={{ marginTop: '1rem', gap: '0.5rem' }}>
            <Button tone="secondary" onClick={downloadCsv}>
              {t('rc.downloadLines', { n: n(queue.length) })}
            </Button>
            <Button tone="ghost" onClick={handleUndo}>{t('rc.undoLast')}</Button>
            <Button tone="ghost" onClick={() => setQueue([])}>{t('rc.clearList')}</Button>
          </div>
          <p className="page-description" style={{ marginTop: '0.5rem' }}>
            {expiryOnly
              ? t('rc.savedLocallyExpiry')
              : t('rc.savedLocallyDelivery')}
          </p>
          <div className="compact-list">
            {queue.slice(0, 10).map((row, idx) => (
              <div className="compact-row" key={`${row.barcode}:${row.recordedAt}:${idx}`}>
                <div>
                  <strong {...dirProps(row.productName || row.barcode)}>
                    {row.productName || formatBarcode(row.barcode)}
                  </strong>
                  <span>
                    {expiryOnly
                      ? (row.productName ? formatBarcode(row.barcode) : t('rc.notInCatalogShort'))
                      : t('rc.unitsFrom', { n: n(row.quantity), supplier: row.supplier })}
                  </span>
                </div>
                <div className="compact-row-end date-cell">
                  {!expiryOnly && <small>{formatDate(row.receivedAt)}</small>}
                  {row.expiryDate && <small>{t('rc.exp')} {formatDate(row.expiryDate)}</small>}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}
