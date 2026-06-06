/**
 * Competitor Intelligence Engine
 *
 * Reads our product catalog + a local market snapshot and produces:
 *   - Price intelligence (price leader vs. price sensitive)
 *   - Stock intelligence (competitor OOS within radius → profit opportunity)
 *   - Demand multipliers (boost projected demand when competitors are OOS)
 *   - Pricing alerts (Price Protection when a competitor is >15% cheaper)
 *
 * Pure analytics. No I/O, no React state. Operates on the LocalMarketSnapshot
 * produced by multiCompetitorAdapter.buildLocalMarketSnapshot.
 */

import { PRODUCT_ID_TO_BARCODE } from '../../data/marketData.js'

const PROXIMITY_RADIUS_M = 1000
const PRICE_PROTECTION_THRESHOLD = 0.15 // competitor must be ≥15% cheaper

/**
 * @typedef {Object} CompetitorEntry
 * @property {string} brand
 * @property {string} storeName
 * @property {string} storeId
 * @property {number} price
 * @property {boolean} isAvailable
 * @property {number} distance_m
 *
 * @typedef {Object<string, CompetitorEntry[]>} LocalMarketSnapshot
 */

/**
 * Resolve a product to its barcode using the BARCODE_TO_PRODUCT_ID map.
 * Falls back to the product's own `barcode` field if present.
 */
function resolveBarcode(product, overrideMap) {
  const map = overrideMap ?? PRODUCT_ID_TO_BARCODE
  return product.barcode ?? map[product.id] ?? null
}

/**
 * Return only competitor entries for a barcode that are within the radius.
 */
function nearbyEntries(barcode, snapshot, radiusMeters = PROXIMITY_RADIUS_M) {
  const entries = snapshot?.[barcode]
  if (!Array.isArray(entries)) return []
  return entries.filter((entry) => Number.isFinite(entry.distance_m) && entry.distance_m <= radiusMeters)
}

/**
 * Demand multiplier driven by competitor stock state within 1km.
 *   - All competitors OOS  → 1.25
 *   - Some (but not all)   → 1.15
 *   - Otherwise            → 1.0
 *
 * @param {string} barcode
 * @param {LocalMarketSnapshot} localMarketSnapshot
 * @returns {number}
 */
export function getCompetitorDemandBoost(barcode, localMarketSnapshot) {
  const nearby = nearbyEntries(barcode, localMarketSnapshot)
  if (nearby.length === 0) return 1.0

  const oosCount = nearby.filter((entry) => entry.isAvailable === false).length
  if (oosCount === 0) return 1.0
  if (oosCount === nearby.length) return 1.25
  return 1.15
}

/**
 * Analyze a single product against the local market snapshot.
 */
function analyzeProductMarket(product, snapshot, barcodeMap) {
  const barcode = resolveBarcode(product, barcodeMap)
  const nearby = barcode ? nearbyEntries(barcode, snapshot) : []
  const available = nearby.filter((entry) => entry.isAvailable !== false)
  const oos = nearby.filter((entry) => entry.isAvailable === false)

  // --- Price intelligence ---
  const competitorPrices = available.map((entry) => entry.price).filter(Number.isFinite)
  const cheapestCompetitor = competitorPrices.length ? Math.min(...competitorPrices) : null
  const priciestCompetitor = competitorPrices.length ? Math.max(...competitorPrices) : null

  let priceDelta = null               // our - cheapest competitor (negative = we're cheaper)
  let isPriceSensitive = false
  let isPriceLeader = false
  let priceProtectionAlert = false

  if (cheapestCompetitor !== null && Number.isFinite(product.price)) {
    priceDelta = round(product.price - cheapestCompetitor)
    isPriceLeader = available.length > 0 && product.price < cheapestCompetitor + 0.001
    isPriceSensitive = priceDelta > 0.001
    // ≥15% cheaper triggers price protection
    if (
      product.price > 0 &&
      cheapestCompetitor / product.price <= 1 - PRICE_PROTECTION_THRESHOLD
    ) {
      priceProtectionAlert = true
    }
  }

  // --- Stock intelligence ---
  const isCompetitorOOS = oos.length > 0
  const triggeredBy = oos.map((entry) => ({
    brand: entry.brand,
    storeName: entry.storeName,
    distance_m: entry.distance_m,
  }))

  // --- Demand multiplier ---
  const demandBoost = barcode ? getCompetitorDemandBoost(barcode, snapshot) : 1.0

  return {
    barcode,
    nearbyCompetitors: nearby.length,
    cheapestCompetitorPrice: cheapestCompetitor,
    priciestCompetitorPrice: priciestCompetitor,
    priceDelta,
    isPriceSensitive,
    isPriceLeader,
    priceProtectionAlert,
    isCompetitorOOS,
    triggeredBy,
    demandBoost,
  }
}

/**
 * Enrich the full product catalog with competitor intelligence.
 *
 * @param {Array} ourProducts                  normalized products (post-adapter)
 * @param {LocalMarketSnapshot} localMarketSnapshot
 * @param {Object} [options]
 * @param {Object<string,string>} [options.barcodeMap]   product.id → barcode
 * @returns {Array} products with `.competitor` payload attached
 */
export function analyzeLocalMarket(ourProducts = [], localMarketSnapshot = {}, options = {}) {
  if (!Array.isArray(ourProducts)) return []
  return ourProducts.map((product) => ({
    ...product,
    competitor: analyzeProductMarket(product, localMarketSnapshot, options.barcodeMap),
  }))
}

/**
 * Convenience selectors used by the UI panel and the App orchestrator.
 */
export function buildCompetitorBoostMap(enrichedProducts) {
  const map = {}
  for (const product of enrichedProducts) {
    const boost = product.competitor?.demandBoost ?? 1.0
    if (boost > 1.0) map[product.id] = boost
  }
  return map
}

export function buildPriceAdvantageSet(enrichedProducts) {
  const set = new Set()
  for (const product of enrichedProducts) {
    if (product.competitor?.isPriceLeader) set.add(product.id)
  }
  return set
}

export function selectPriceLeaders(enrichedProducts) {
  return enrichedProducts
    .filter((product) => product.competitor?.isPriceLeader && product.competitor?.priceDelta !== null)
    .sort((a, b) => a.competitor.priceDelta - b.competitor.priceDelta) // most-negative (biggest lead) first
}

export function selectStockoutOpportunities(enrichedProducts) {
  return enrichedProducts
    .filter((product) => product.competitor?.isCompetitorOOS)
    .sort((a, b) => {
      const aClosest = Math.min(...a.competitor.triggeredBy.map((t) => t.distance_m))
      const bClosest = Math.min(...b.competitor.triggeredBy.map((t) => t.distance_m))
      return aClosest - bClosest
    })
}

export function selectPriceProtectionAlerts(enrichedProducts) {
  return enrichedProducts
    .filter((product) => product.competitor?.priceProtectionAlert)
    .sort(
      (a, b) =>
        (b.competitor.priceDelta ?? 0) - (a.competitor.priceDelta ?? 0), // biggest gap first
    )
}

export function summarizeCompetitorIntelligence(enrichedProducts) {
  return {
    priceLeaderCount: selectPriceLeaders(enrichedProducts).length,
    competitorOOSCount: selectStockoutOpportunities(enrichedProducts).length,
    priceProtectionCount: selectPriceProtectionAlerts(enrichedProducts).length,
    productsWithCoverage: enrichedProducts.filter((p) => (p.competitor?.nearbyCompetitors ?? 0) > 0).length,
  }
}

function round(value) {
  return Math.round(value * 100) / 100
}
