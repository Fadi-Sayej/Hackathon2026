import { demoProducts } from '../../data/demoProducts.js'
import { normalizeProducts } from '../dataAdapters/productAdapter.js'
import { CONNECTOR_MODES, mergeFeedsById } from './posConnectorInterface.js'

export function createDemoDataConnector({ rows = demoProducts } = {}) {
  const sourceRows = Array.isArray(rows) ? rows : []

  async function connect() {
    return {
      ok: true,
      message: `Demo dataset ready (${sourceRows.length} SKUs).`,
    }
  }

  async function fetchProducts() {
    return sourceRows
  }

  async function fetchInventory() {
    return sourceRows
  }

  async function fetchSales() {
    return sourceRows
  }

  function normalizeToSmartShelfSchema(raw) {
    const merged = mergeFeedsById(raw)
    const { products, issues } = normalizeProducts(merged)
    return {
      products,
      validationIssues: issues,
      source: {
        type: 'local-demo',
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
    id: 'demo',
    label: 'Demo Dataset',
    description: 'Bundled 40+ SKU sample data. Always available offline.',
    status: 'ready',
    mode: CONNECTOR_MODES.DEMO,
    connect,
    fetchProducts,
    fetchInventory,
    fetchSales,
    normalizeToSmartShelfSchema,
    load,
  }
}
