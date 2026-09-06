import { CONNECTOR_MODES, EXPECTED_POS_FIELDS } from './posConnectorInterface.js'

/**
 * Comax POS Connector — STUB ONLY.
 *
 * This connector is intentionally inert in the frontend. A real Comax
 * integration must run through a backend proxy that holds the API key
 * and performs the outbound HTTP calls. The browser is not allowed to
 * embed POS credentials, so all methods here return a "backend required"
 * signal until that proxy exists.
 *
 * Expected POS schema after backend normalization:
 *   - product id / barcode
 *   - name
 *   - category
 *   - current stock
 *   - 7-day and 30-day sales
 *   - price and cost
 *   - supplier
 *   - lead time (days)
 */
export function createComaxConnectorStub() {
  const proxyUrl = import.meta.env?.VITE_COMAX_PROXY_URL ?? ''
  const hasProxy = Boolean(proxyUrl)

  const unavailable = () => {
    throw new Error('Comax connector requires a backend proxy. Frontend cannot call POS directly.')
  }

  async function connect() {
    if (!hasProxy) {
      return {
        ok: false,
        message: 'Backend proxy required — Comax is not callable from the browser.',
        hint: 'Set VITE_COMAX_PROXY_URL once a server-side adapter is deployed.',
      }
    }
    return {
      ok: false,
      message: 'Backend proxy detected but live mode is not yet enabled in this build.',
      hint: 'Wire createComaxConnectorStub to a real fetch implementation when ready.',
    }
  }

  async function fetchProducts() {
    unavailable()
  }
  async function fetchInventory() {
    unavailable()
  }
  async function fetchSales() {
    unavailable()
  }

  function normalizeToSmartShelfSchema() {
    unavailable()
  }

  async function load() {
    const probe = await connect()
    const error = new Error(probe.message)
    error.code = 'comax_backend_required'
    error.hint = probe.hint
    throw error
  }

  return {
    id: 'comax',
    label: 'Comax POS Connector',
    description: 'Live Comax sync. Requires a backend proxy — disabled in this build.',
    status: 'disabled',
    mode: CONNECTOR_MODES.COMAX,
    expectedFields: EXPECTED_POS_FIELDS,
    connect,
    fetchProducts,
    fetchInventory,
    fetchSales,
    normalizeToSmartShelfSchema,
    load,
  }
}
