/**
 * Store Format Filter
 *
 * YomYom is a forecourt shop with a few thousand SKUs. A Shufersal Deal box carries
 * ten times that. Treating the two as equivalent price sources is how a system ends
 * up recommending 5 kg rice bags and 24-packs to a gas station, and one absurd
 * recommendation costs the manager's trust in every correct one after it.
 *
 * Comparability is not binary, so this is a weight, not just a filter:
 *
 *   affinity 0.0            → EXCLUDED. Dropped before any engine sees it.
 *   0.0 < affinity < 0.3    → CONTEXT ONLY. Visible in the competitor panel,
 *                             never the basis of a recommendation.
 *   affinity >= 0.3         → COMPARABLE, at strength proportional to affinity.
 *
 * The classification itself is reference data in `configs/store_types.yaml`,
 * published to `src/data/storeTypes.js` by scripts/export_store_types.py.
 */

import {
  MIN_AFFINITY,
  OUR_STORE_TYPE,
  STORE_AFFINITY,
  STORE_FORMATS,
  STORE_TYPES,
} from '../../data/storeTypes.js'

export const UNKNOWN_STORE_TYPE = 'unknown'

/** Format of a branch, or `unknown` when it has never been classified. */
export function storeTypeOf(storeId) {
  return STORE_TYPES[storeId]?.storeType ?? UNKNOWN_STORE_TYPE
}

/** True when a human confirmed the branch's format, rather than a script guessing it. */
export function isVerifiedStoreType(storeId) {
  return STORE_TYPES[storeId]?.verified === 'manual'
}

export function storeFormatLabel(storeType, locale = 'en') {
  const format = STORE_FORMATS[storeType]
  if (!format) return storeType ?? UNKNOWN_STORE_TYPE
  if (locale === 'he') return format.labelHe ?? format.labelEn ?? storeType
  if (locale === 'ar') return format.labelAr ?? format.labelEn ?? storeType
  return format.labelEn ?? storeType
}

/**
 * How comparable `theirType` is to `ourType`, in [0, 1].
 *
 * An unrecognised format resolves through the `unknown` row rather than to 1.0:
 * a missing classification must never read as a perfect match, because that is
 * precisely the state this module exists to make safe.
 */
export function formatAffinity(ourType, theirType) {
  const row = STORE_AFFINITY[ourType] ?? STORE_AFFINITY[UNKNOWN_STORE_TYPE] ?? {}
  const value = row[theirType] ?? row[UNKNOWN_STORE_TYPE] ?? 0
  return Number.isFinite(value) ? value : 0
}

/**
 * Affinity of a competitor branch to our own store.
 *
 * Entries that already carry a `formatAffinity` (baked in by the exporter) are
 * trusted as-is; everything else is resolved from its storeId. Demo and mock data
 * carry neither, and fall back to `unknown` — visible, but never load-bearing.
 */
export function affinityForEntry(entry, ourType = OUR_STORE_TYPE) {
  if (Number.isFinite(entry?.formatAffinity)) return entry.formatAffinity
  const theirType = entry?.storeType ?? storeTypeOf(entry?.storeId)
  return formatAffinity(ourType, theirType)
}

/** A source at 0.0 is never compared, in any context, for any reason. */
export function isNeverComparable(entry, ourType = OUR_STORE_TYPE) {
  return affinityForEntry(entry, ourType) === 0
}

/** A source is only allowed to drive a recommendation at or above MIN_AFFINITY. */
export function canDriveRecommendation(entry, ourType = OUR_STORE_TYPE) {
  return affinityForEntry(entry, ourType) >= MIN_AFFINITY
}

/**
 * Split competitor entries into the three tiers above.
 *
 * @returns {{comparable: Array, contextOnly: Array, excluded: Array}}
 */
export function partitionByFormat(entries = [], ourType = OUR_STORE_TYPE) {
  const comparable = []
  const contextOnly = []
  const excluded = []

  for (const entry of entries) {
    const affinity = affinityForEntry(entry, ourType)
    const tagged = {
      ...entry,
      storeType: entry.storeType ?? storeTypeOf(entry.storeId),
      formatAffinity: affinity,
    }
    if (affinity === 0) excluded.push(tagged)
    else if (affinity < MIN_AFFINITY) contextOnly.push(tagged)
    else comparable.push(tagged)
  }

  return { comparable, contextOnly, excluded }
}

/**
 * Store IDs worth comparing against, most comparable first.
 * Mirrors `comparable_stores()` in src/common/store_types.py.
 */
export function comparableStores(ourType = OUR_STORE_TYPE, minAffinity = MIN_AFFINITY) {
  return Object.keys(STORE_TYPES)
    .map((storeId) => [storeId, formatAffinity(ourType, storeTypeOf(storeId))])
    .filter(([, affinity]) => affinity >= minAffinity)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([storeId]) => storeId)
}

export { MIN_AFFINITY, OUR_STORE_TYPE }
