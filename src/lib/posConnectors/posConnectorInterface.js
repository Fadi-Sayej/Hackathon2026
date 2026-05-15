/**
 * Generic POS Connector Interface
 *
 * Every connector implements the same shape so the application can swap
 * between Demo data, an uploaded CSV, or a future Comax backend feed
 * without changes to the engines that consume the normalized products.
 *
 * @typedef {Object} ConnectMessage
 * @property {boolean} ok
 * @property {string} message
 * @property {string} [hint]
 *
 * @typedef {Object} NormalizedStoreData
 * @property {Array<Object>} products
 * @property {Array<Object>} validationIssues
 * @property {Object} source
 *
 * @typedef {Object} PosConnector
 * @property {string} id
 * @property {string} label
 * @property {string} description
 * @property {'ready'|'disabled'|'error'} status
 * @property {string} mode
 * @property {() => Promise<ConnectMessage>} connect
 * @property {() => Promise<Array<Object>>} fetchProducts
 * @property {() => Promise<Array<Object>>} fetchInventory
 * @property {() => Promise<Array<Object>>} fetchSales
 * @property {(raw: {products: Array, inventory: Array, sales: Array}) => NormalizedStoreData} normalizeToSmartShelfSchema
 * @property {() => Promise<NormalizedStoreData>} load
 */

export const CONNECTOR_MODES = Object.freeze({
  DEMO: 'demo',
  CSV: 'csv',
  COMAX: 'comax',
})

export const EXPECTED_POS_FIELDS = Object.freeze([
  { field: 'id', aliases: ['sku', 'productId', 'barcode'], required: true },
  { field: 'barcode', aliases: ['ean', 'upc'], required: false },
  { field: 'name', aliases: ['productName', 'description'], required: true },
  { field: 'category', aliases: ['department', 'group'], required: true },
  { field: 'currentStock', aliases: ['stock', 'onHand', 'qty'], required: true },
  { field: 'salesLast7Days', aliases: ['sales7d', 'weeklySales'], required: false },
  { field: 'salesLast30Days', aliases: ['sales30d', 'monthlySales'], required: false },
  { field: 'price', aliases: ['unitPrice', 'sellPrice'], required: true },
  { field: 'cost', aliases: ['unitCost'], required: false },
  { field: 'supplier', aliases: ['vendor'], required: false },
  { field: 'leadTimeDays', aliases: ['leadTime'], required: false },
  { field: 'expiryDate', aliases: ['expiry'], required: false },
  { field: 'shelfQuantity', aliases: ['onShelf'], required: false },
  { field: 'shelfCapacity', aliases: ['capacity'], required: false },
])

/**
 * Merge separate POS feeds (products / inventory / sales) by product id.
 * If a connector returns one combined feed it can simply pass everything
 * through the `products` array and leave the others empty.
 */
export function mergeFeedsById({ products = [], inventory = [], sales = [] }) {
  const byId = new Map()

  for (const row of products) {
    const id = row.id ?? row.sku ?? row.productId ?? row.barcode
    if (!id) continue
    byId.set(String(id), { ...row })
  }

  for (const row of inventory) {
    const id = row.id ?? row.sku ?? row.productId ?? row.barcode
    if (!id) continue
    const key = String(id)
    byId.set(key, { ...(byId.get(key) ?? {}), ...row })
  }

  for (const row of sales) {
    const id = row.id ?? row.sku ?? row.productId ?? row.barcode
    if (!id) continue
    const key = String(id)
    byId.set(key, { ...(byId.get(key) ?? {}), ...row })
  }

  return Array.from(byId.values())
}
