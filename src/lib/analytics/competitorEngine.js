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
 *
 * Every competitor entry passes the store-format filter first (see storeFormat.js):
 * a hypermarket is not a price source for a forecourt shop, and proximity alone
 * does not make it one.
 */

import { PRODUCT_ID_TO_BARCODE } from '../../data/marketData.js'
import { MIN_AFFINITY, partitionByFormat } from './storeFormat.js'

const PROXIMITY_RADIUS_M = 3000
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
 * Nearby entries the store format allows us to act on.
 *
 * `comparable` drives every number below. `contextOnly` is shown but never acted
 * on. `excluded` is gone — a hypermarket price is not evidence about a forecourt
 * shop no matter how close it is.
 */
function comparableEntries(barcode, snapshot, radiusMeters = PROXIMITY_RADIUS_M) {
  return partitionByFormat(nearbyEntries(barcode, snapshot, radiusMeters))
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
  // A stockout at a store we would never compare prices against is not evidence
  // that demand is about to land here, so the boost sees comparable stores only.
  const { comparable } = comparableEntries(barcode, localMarketSnapshot)
  if (comparable.length === 0) return 1.0

  const oosCount = comparable.filter((entry) => entry.isAvailable === false).length
  if (oosCount === 0) return 1.0
  if (oosCount === comparable.length) return 1.25
  return 1.15
}

/**
 * Analyze a single product against the local market snapshot.
 */
function analyzeProductMarket(product, snapshot, barcodeMap) {
  const barcode = resolveBarcode(product, barcodeMap)
  const { comparable, contextOnly, excluded } = barcode
    ? comparableEntries(barcode, snapshot)
    : { comparable: [], contextOnly: [], excluded: [] }

  // From here down, "nearby" means nearby AND comparable. Everything else is
  // reported as a count so the UI can explain the gap, never mixed into a number.
  const nearby = comparable
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

  // Age of the specific observation behind cheapestCompetitor. The UI must be able to
  // say "seen 3 months ago" instead of stating a stale price as current fact.
  const cheapestEntry =
    cheapestCompetitor !== null
      ? available.find((entry) => entry.price === cheapestCompetitor)
      : null
  const priceAgeDays = cheapestEntry?.ageDays ?? null
  const priceObservedAt = cheapestEntry?.observedAt ?? null

  // How comparable the store behind the cheapest price actually is. A 1.0 is the
  // forecourt shop down the road; a 0.3 is a mid-size grocery whose scale we
  // cannot match, so its gap has to be bigger before it means anything.
  const priceAffinity = cheapestEntry?.formatAffinity ?? null

  if (cheapestCompetitor !== null && Number.isFinite(product.price)) {
    priceDelta = round(product.price - cheapestCompetitor)
    isPriceLeader = available.length > 0 && product.price < cheapestCompetitor + 0.001
    isPriceSensitive = priceDelta > 0.001
    // ≥15% cheaper triggers price protection — but the threshold widens as the
    // source gets less comparable, so a distant format needs a starker gap.
    const affinity = priceAffinity ?? 1
    const threshold = affinity > 0 ? PRICE_PROTECTION_THRESHOLD / affinity : Infinity
    if (product.price > 0 && cheapestCompetitor / product.price <= 1 - threshold) {
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
    // Nearby but not comparable. Split so the UI can say "3 nearby stores, none of
    // them your format" instead of silently showing no competitors at all.
    contextOnlyCompetitors: contextOnly.length,
    excludedByFormat: excluded.length,
    excludedStoreTypes: [...new Set(excluded.map((entry) => entry.storeType))],
    cheapestCompetitorPrice: cheapestCompetitor,
    priciestCompetitorPrice: priciestCompetitor,
    priceAgeDays,
    priceObservedAt,
    priceAffinity,
    priceStoreType: cheapestEntry?.storeType ?? null,
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
    // Products whose only nearby price came from a store format we refuse to
    // compare against. These are not "no data" — they are a deliberate silence.
    productsExcludedByFormat: enrichedProducts.filter(
      (p) => (p.competitor?.nearbyCompetitors ?? 0) === 0 && (p.competitor?.excludedByFormat ?? 0) > 0,
    ).length,
  }
}

/** Re-exported so callers can reason about the gate without importing two modules. */
export { MIN_AFFINITY }

function round(value) {
  return Math.round(value * 100) / 100
}
