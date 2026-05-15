/**
 * Hyper-Local Multi-Brand Competitor Intelligence — Mock neighborhood.
 *
 * Real source: https://url.retail.publishedprices.co.il/ — Israeli "Food Law"
 * (Hok HaMazon) transparency portal. Every major chain publishes hourly
 * XML snapshots with <ItemCode>, <ItemPrice>, <ItemStatus>. Login per chain:
 *
 *   Paz / Yellow      → username via PORTAL_USER_PAZ
 *   Delek / Menta     → username via PORTAL_USER_DELEK
 *   Sonol / So Good   → username via PORTAL_USER_SONOL
 *   Dor Alon / Alonit → username via PORTAL_USER_DORALON
 *
 * For the hackathon demo we never hit the live portal — this file
 * synthesizes a believable neighborhood snapshot keyed by EAN-13 barcode.
 *
 * BARCODE_TO_PRODUCT_ID lets the engine join real barcodes back to our
 * internal demo product IDs (`rb-001`, `cc-003`, …) without modifying
 * the generated demoProducts.js file.
 */

export const OUR_STORE = {
  brand: 'SmartShelf',
  storeName: 'Our Station',
  storeId: 'us-001',
  coords: { lat: 32.0853, lng: 34.7818 }, // Tel Aviv reference point
}

/** EAN-13 barcode → internal demo product id. */
export const BARCODE_TO_PRODUCT_ID = Object.freeze({
  '7290000066794': 'rb-001', // Red Bull 250ml         — the demo headline OOS trigger
  '7290000140360': 'xl-002', // XL Energy 250ml
  '7290010048988': 'cc-003', // Coca Cola 500ml
  '7290000130118': 'wt-005', // Mineral Water 1.5L
  '7290003937851': 'bm-006', // Bamba 70g
  '7290000208022': 'kb-009', // Kinder Bueno
})

/** Reverse lookup for the engine. */
export const PRODUCT_ID_TO_BARCODE = Object.freeze(
  Object.fromEntries(Object.entries(BARCODE_TO_PRODUCT_ID).map(([bc, id]) => [id, bc])),
)

/**
 * Four chains, two close (Paz Yellow 200m, Delek Menta 450m) and two further
 * (Sonol 1.1km, Dor Alon 1.4km). The 1km radius filter will scope the engine
 * to the two closest for boost calculations — the outer two still appear in
 * the snapshot for completeness.
 *
 * Demo trigger (must remain): Red Bull (7290000066794) is OOS at Yellow (200m)
 * but in stock at Menta (450m). That asymmetry produces a 1.15× demand boost.
 */
export const COMPETITOR_STORES = [
  {
    brand: 'Paz',
    storeName: 'Yellow',
    storeId: '118',
    portalFolder: 'paz_bo',
    distance_m: 200,
    coords: { lat: 32.0870, lng: 34.7820 },
    snapshot: {
      '7290000066794': { price: 7.90, isAvailable: false }, // Red Bull — OOS (vanishing barcode trigger)
      '7290000140360': { price: 7.50, isAvailable: true },  // XL Energy
      '7290010048988': { price: 5.50, isAvailable: true },  // Coca Cola
      '7290000130118': { price: 3.50, isAvailable: true },  // Water
      '7290003937851': { price: 4.20, isAvailable: true },  // Bamba
      '7290000208022': { price: 6.90, isAvailable: true },  // Kinder Bueno
    },
  },
  {
    brand: 'Delek',
    storeName: 'Menta',
    storeId: '45',
    portalFolder: 'delek',
    distance_m: 450,
    coords: { lat: 32.0840, lng: 34.7835 },
    snapshot: {
      '7290000066794': { price: 8.20, isAvailable: true },  // Red Bull — in stock
      '7290000140360': { price: 7.20, isAvailable: false }, // XL Energy — OOS (secondary trigger)
      '7290010048988': { price: 5.20, isAvailable: true },  // Coca Cola — cheapest nearby
      '7290000130118': { price: 3.20, isAvailable: true },
      '7290003937851': { price: 4.50, isAvailable: true },
      '7290000208022': { price: 7.40, isAvailable: true },
    },
  },
  {
    brand: 'Sonol',
    storeName: 'So Good',
    storeId: '17',
    portalFolder: 'sonol',
    distance_m: 1100, // just outside the 1km boost radius
    coords: { lat: 32.0790, lng: 34.7860 },
    snapshot: {
      '7290000066794': { price: 8.50, isAvailable: true },
      '7290000140360': { price: 7.80, isAvailable: true },
      '7290010048988': { price: 5.40, isAvailable: true },
      '7290000130118': { price: 3.40, isAvailable: true },
      '7290003937851': { price: 4.10, isAvailable: false }, // Bamba — OOS but outside radius
      '7290000208022': { price: 6.50, isAvailable: true },  // cheapest Kinder Bueno (price-protection trigger if our price > 7.48)
    },
  },
  {
    brand: 'Dor Alon',
    storeName: 'Alonit',
    storeId: '76',
    portalFolder: 'doralon',
    distance_m: 1400,
    coords: { lat: 32.0780, lng: 34.7910 },
    snapshot: {
      '7290000066794': { price: 8.10, isAvailable: true },
      '7290000140360': { price: 7.40, isAvailable: true },
      '7290010048988': { price: 5.30, isAvailable: true },
      '7290000130118': { price: 3.30, isAvailable: true },
      '7290003937851': { price: 4.30, isAvailable: true },
      '7290000208022': { price: 7.00, isAvailable: true },
    },
  },
]
