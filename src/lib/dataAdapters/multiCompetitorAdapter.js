/**
 * Multi-Brand Competitor XML Adapter
 *
 * Israeli "Hok HaMazon" mandates that retailers publish hourly XML snapshots
 * of prices and inventory to https://url.retail.publishedprices.co.il/.
 * Each chain uses one of two POS export formats:
 *
 *   - NCR / IBM (Paz):       <Item><ItemCode>X</ItemCode><ItemPrice>Y</ItemPrice>...</Item>
 *   - Cerberus (Delek/Sonol): <Product><Barcode>X</Barcode><ItemPrice>Y</ItemPrice>
 *                              <PriceUpdateDate>...</PriceUpdateDate>...</Product>
 *
 * This adapter normalizes both to a single { itemCode, price, isAvailable }
 * shape so downstream engines never care which chain a row came from.
 *
 * The "Vanishing Barcode" rule:
 *   - If <ItemCode> existed in the previous snapshot but is missing from
 *     the current snapshot → OUT OF STOCK.
 *   - If <ItemStatus>=0 (or equivalent) and the item is still present → OOS.
 *   - If the item reappears in a later snapshot → back in stock.
 *
 * Demo posture: no live HTTP. `buildLocalMarketSnapshot` is fed
 * COMPETITOR_STORES from mockMarketData.js directly.
 */

/* ------------------------------------------------------------------ */
/* 4a. XML Parser                                                      */
/* ------------------------------------------------------------------ */

/**
 * Parse an Israeli retail XML snapshot string into a normalized array.
 * Uses the browser's DOMParser (no external dependency).
 *
 * @param {string} xmlString
 * @param {string} brand   informational label
 * @returns {Array<{itemCode: string, price: number, isAvailable: boolean, brand: string}>}
 */
export function parseRetailXML(xmlString, brand = 'unknown') {
  if (typeof xmlString !== 'string' || !xmlString.trim()) return []
  if (typeof DOMParser === 'undefined') return []

  const doc = new DOMParser().parseFromString(xmlString, 'text/xml')
  if (doc.querySelector('parsererror')) return []

  // Both NCR (<Item>) and Cerberus (<Product>) variants — try both.
  const rows = [
    ...doc.querySelectorAll('Item'),
    ...doc.querySelectorAll('Product'),
  ]

  const out = []
  for (const row of rows) {
    const itemCode =
      textOf(row, 'ItemCode') ||
      textOf(row, 'Barcode') ||
      textOf(row, 'ProductCode')
    if (!itemCode) continue

    const priceText =
      textOf(row, 'ItemPrice') ||
      textOf(row, 'Price') ||
      textOf(row, 'UnitOfMeasurePrice')
    const price = Number(priceText)
    if (!Number.isFinite(price)) continue

    // ItemStatus: 0 = inactive/OOS in NCR-style feeds. Cerberus may use
    // <Status> or omit it; absence is treated as available.
    const statusText = textOf(row, 'ItemStatus') || textOf(row, 'Status')
    const isAvailable = statusText === '' ? true : statusText !== '0'

    out.push({ itemCode: itemCode.trim(), price, isAvailable, brand })
  }
  return out
}

function textOf(node, tagName) {
  const el = node.querySelector(tagName)
  return el ? (el.textContent ?? '').trim() : ''
}

/* ------------------------------------------------------------------ */
/* 4b. Snapshot Builder                                                */
/* ------------------------------------------------------------------ */

/**
 * Collapse an item array into a barcode-keyed Map.
 * Last entry per barcode wins (matches real portal "latest update" semantics).
 *
 * @param {Array<{itemCode: string, price: number, isAvailable: boolean}>} itemArray
 * @returns {Map<string, {price: number, isAvailable: boolean}>}
 */
export function buildSnapshot(itemArray = []) {
  const snapshot = new Map()
  for (const item of itemArray) {
    if (!item?.itemCode) continue
    snapshot.set(item.itemCode, {
      price: item.price,
      isAvailable: item.isAvailable !== false,
    })
  }
  return snapshot
}

/* ------------------------------------------------------------------ */
/* 4c. Vanishing Barcode Detector                                      */
/* ------------------------------------------------------------------ */

/**
 * Returns barcodes that were in the previous snapshot but vanished from the
 * current snapshot → competitor went OOS on those items.
 *
 * @param {Map<string, any>} previousMap
 * @param {Map<string, any>} currentMap
 * @returns {string[]} vanished barcodes
 */
export function detectStockouts(previousMap, currentMap) {
  if (!(previousMap instanceof Map) || !(currentMap instanceof Map)) return []
  const vanished = []
  for (const barcode of previousMap.keys()) {
    if (!currentMap.has(barcode)) vanished.push(barcode)
  }
  return vanished
}

/* ------------------------------------------------------------------ */
/* 4d. Unified Local Market Snapshot                                   */
/* ------------------------------------------------------------------ */

/**
 * Pivots an array of competitor stores into a barcode-indexed view of
 * the local market. Each barcode maps to an array of competitor entries,
 * one per chain that carries it.
 *
 * @param {Array} competitorStores  shape from mockMarketData.COMPETITOR_STORES
 * @returns {Object<string, Array<{brand, storeName, storeId, price, isAvailable, distance_m}>>}
 */
export function buildLocalMarketSnapshot(competitorStores = []) {
  const out = {}
  for (const store of competitorStores) {
    const entries = Object.entries(store.snapshot ?? {})
    for (const [barcode, { price, isAvailable, ageDays, observedAt }] of entries) {
      if (!out[barcode]) out[barcode] = []
      out[barcode].push({
        brand: store.brand,
        storeName: store.storeName,
        storeId: store.storeId,
        // Store format travels with every price. Downstream, competitorEngine
        // refuses to compare a forecourt shop against a big box, and it can only
        // do that if it knows which kind of store the number came from.
        storeType: store.storeType ?? null,
        storeTypeVerified: store.storeTypeVerified ?? null,
        price,
        isAvailable,
        // How old this observation is. Carried through so the UI can label a price
        // rather than presenting a months-old figure as today's shelf price.
        ageDays: ageDays ?? null,
        observedAt: observedAt ?? null,
        distance_m: store.distance_m,
      })
    }
  }
  return out
}
