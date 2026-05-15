import { normalizeProducts } from '../dataAdapters/productAdapter.js'
import { CONNECTOR_MODES, mergeFeedsById } from './posConnectorInterface.js'

/**
 * RFC 4180-lite CSV parser. Supports:
 *  - quoted fields, "escaped""quotes" inside fields, embedded commas/newlines
 *  - LF or CRLF line endings
 *  - first row is the header row
 */
export function parseCsv(text) {
  if (typeof text !== 'string' || !text.trim()) return { headers: [], rows: [] }

  const rows = []
  let currentRow = []
  let currentField = ''
  let inQuotes = false

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i]
    const next = text[i + 1]

    if (inQuotes) {
      if (char === '"' && next === '"') {
        currentField += '"'
        i += 1
      } else if (char === '"') {
        inQuotes = false
      } else {
        currentField += char
      }
      continue
    }

    if (char === '"') {
      inQuotes = true
      continue
    }
    if (char === ',') {
      currentRow.push(currentField)
      currentField = ''
      continue
    }
    if (char === '\r') {
      continue
    }
    if (char === '\n') {
      currentRow.push(currentField)
      rows.push(currentRow)
      currentRow = []
      currentField = ''
      continue
    }
    currentField += char
  }

  if (currentField.length > 0 || currentRow.length > 0) {
    currentRow.push(currentField)
    rows.push(currentRow)
  }

  const nonEmpty = rows.filter((row) => row.some((cell) => cell !== ''))
  if (nonEmpty.length === 0) return { headers: [], rows: [] }

  const headers = nonEmpty[0].map((header) => header.trim())
  const data = nonEmpty.slice(1).map((row) => {
    const obj = {}
    headers.forEach((header, idx) => {
      if (!header) return
      const value = (row[idx] ?? '').trim()
      obj[header] = value
    })
    return obj
  })

  return { headers, rows: data }
}

function coerceNumericFields(row) {
  const numericKeys = [
    'currentStock', 'stock', 'onHand', 'qty',
    'shelfQuantity', 'onShelf',
    'shelfCapacity', 'capacity',
    'salesLast7Days', 'sales7d', 'weeklySales',
    'salesLast30Days', 'sales30d', 'monthlySales',
    'price', 'unitPrice', 'sellPrice',
    'cost', 'unitCost',
    'leadTimeDays', 'leadTime',
    'returnedUnits', 'damagedUnits',
  ]
  const coerced = { ...row }
  for (const key of numericKeys) {
    if (coerced[key] === undefined || coerced[key] === '') continue
    const parsed = Number(coerced[key])
    if (Number.isFinite(parsed)) coerced[key] = parsed
  }
  return coerced
}

export function createCsvConnector({ file, csvText, fileName } = {}) {
  let cachedRows = null
  let cachedFileName = fileName ?? (file?.name ?? 'uploaded.csv')

  async function readText() {
    if (typeof csvText === 'string') return csvText
    if (file && typeof file.text === 'function') return file.text()
    throw new Error('No CSV file or text was provided to the CSV connector.')
  }

  async function ensureRows() {
    if (cachedRows) return cachedRows
    const text = await readText()
    const { rows } = parseCsv(text)
    cachedRows = rows.map(coerceNumericFields)
    return cachedRows
  }

  async function connect() {
    try {
      const rows = await ensureRows()
      if (rows.length === 0) {
        return { ok: false, message: 'CSV parsed but no data rows were found.' }
      }
      return { ok: true, message: `CSV ready (${rows.length} rows from ${cachedFileName}).` }
    } catch (error) {
      return { ok: false, message: error.message ?? 'Failed to read CSV file.' }
    }
  }

  async function fetchProducts() {
    return ensureRows()
  }

  async function fetchInventory() {
    return ensureRows()
  }

  async function fetchSales() {
    return ensureRows()
  }

  function normalizeToSmartShelfSchema(raw) {
    const merged = mergeFeedsById(raw)
    const { products, issues } = normalizeProducts(merged)
    return {
      products,
      validationIssues: issues,
      source: {
        type: 'csv-upload',
        fileName: cachedFileName,
        productCount: products.length,
        generatedAt: new Date().toISOString(),
      },
    }
  }

  async function load() {
    const [products, inventory, sales] = await Promise.all([
      fetchProducts(),
      fetchInventory(),
      fetchSales(),
    ])
    return normalizeToSmartShelfSchema({ products, inventory, sales })
  }

  return {
    id: 'csv',
    label: 'Upload CSV',
    description: 'Drop in a POS export. Rows flow through the same adapter as the demo data.',
    status: 'ready',
    mode: CONNECTOR_MODES.CSV,
    connect,
    fetchProducts,
    fetchInventory,
    fetchSales,
    normalizeToSmartShelfSchema,
    load,
  }
}
