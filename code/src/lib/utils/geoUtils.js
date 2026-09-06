/**
 * Pure geospatial helpers. No side effects, no external state.
 */

const EARTH_RADIUS_M = 6_371_000

function toRadians(degrees) {
  return (degrees * Math.PI) / 180
}

/**
 * Haversine great-circle distance between two coordinates.
 *
 * @param {{lat: number, lng: number}} coord1
 * @param {{lat: number, lng: number}} coord2
 * @returns {number} distance in meters
 */
export function getDistanceMeters(coord1, coord2) {
  if (!coord1 || !coord2) return Number.POSITIVE_INFINITY
  const { lat: lat1, lng: lng1 } = coord1
  const { lat: lat2, lng: lng2 } = coord2
  if (
    !Number.isFinite(lat1) ||
    !Number.isFinite(lng1) ||
    !Number.isFinite(lat2) ||
    !Number.isFinite(lng2)
  ) {
    return Number.POSITIVE_INFINITY
  }

  const dLat = toRadians(lat2 - lat1)
  const dLng = toRadians(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(dLng / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return EARTH_RADIUS_M * c
}

/**
 * Returns competitor stores within `radiusMeters` of `ourCoords`.
 * If a store has a precomputed `distance_m` it's preferred (matches the
 * mock data shape); otherwise distance is recomputed from `store.coords`.
 *
 * @param {Array<{coords?: {lat:number,lng:number}, distance_m?: number}>} stores
 * @param {{lat: number, lng: number}} ourCoords
 * @param {number} radiusMeters
 */
export function filterStoresByRadius(stores = [], ourCoords, radiusMeters) {
  if (!Array.isArray(stores) || !ourCoords || !Number.isFinite(radiusMeters)) return []
  return stores.filter((store) => {
    const distance = Number.isFinite(store.distance_m)
      ? store.distance_m
      : getDistanceMeters(ourCoords, store.coords)
    return distance <= radiusMeters
  })
}
