/**
 * Velocity confidence vocabulary.
 *
 * Mirrors the `velocity_confidence` field emitted by the snapshot-diff pipeline
 * (fadi.md A-1). The bands describe how much sales history a velocity figure
 * rests on -- NOT how much the product sold.
 *
 * `units_sold_30d === 0` and `velocity_confidence === 'none'` are different
 * facts: the first says a product did not sell, the second says we have no
 * history to judge it by. Conflating them is what made 100% of the catalog
 * read as "Slow moving".
 */

export const VELOCITY_CONFIDENCE = {
  none: 'none',
  low: 'low',
  medium: 'medium',
  high: 'high',
}

/** Ordered weakest -> strongest. */
export const VELOCITY_CONFIDENCE_LEVELS = [
  VELOCITY_CONFIDENCE.none,
  VELOCITY_CONFIDENCE.low,
  VELOCITY_CONFIDENCE.medium,
  VELOCITY_CONFIDENCE.high,
]

/**
 * Snapshot-count bands, as defined in fadi.md A-1:
 * none (<2 snapshots) - low (2-6) - medium (7-29) - high (30+ days).
 */
export const VELOCITY_CONFIDENCE_BANDS = [
  { level: VELOCITY_CONFIDENCE.none, minSnapshots: 0, maxSnapshots: 1 },
  { level: VELOCITY_CONFIDENCE.low, minSnapshots: 2, maxSnapshots: 6 },
  { level: VELOCITY_CONFIDENCE.medium, minSnapshots: 7, maxSnapshots: 29 },
  { level: VELOCITY_CONFIDENCE.high, minSnapshots: 30, maxSnapshots: Number.POSITIVE_INFINITY },
]

/**
 * Classify a snapshot count into a confidence level.
 * Non-numeric or negative counts fall back to 'none'.
 */
export function velocityConfidenceFromSnapshotCount(snapshotCount) {
  if (typeof snapshotCount !== 'number' || !Number.isFinite(snapshotCount) || snapshotCount < 0) {
    return VELOCITY_CONFIDENCE.none
  }

  const band = VELOCITY_CONFIDENCE_BANDS.find(
    ({ minSnapshots, maxSnapshots }) => snapshotCount >= minSnapshots && snapshotCount <= maxSnapshots,
  )

  return band ? band.level : VELOCITY_CONFIDENCE.none
}

/** True when `value` is one of the four known levels. */
export function isVelocityConfidence(value) {
  return VELOCITY_CONFIDENCE_LEVELS.includes(value)
}

/**
 * Read a product's velocity confidence.
 *
 * Defaults to 'none' when the field is absent -- which is every product today,
 * because `velocity_confidence` is not in the data yet. Unrecognised values
 * also resolve to 'none': failing closed suppresses a velocity claim rather
 * than asserting one we cannot back up.
 */
export function resolveVelocityConfidence(product) {
  const raw = product?.velocityConfidence

  if (typeof raw !== 'string') return VELOCITY_CONFIDENCE.none

  const normalized = raw.trim().toLowerCase()

  return isVelocityConfidence(normalized) ? normalized : VELOCITY_CONFIDENCE.none
}

/**
 * Whether a confidence level supports velocity-derived reasoning
 * (days-until-stockout, slow-moving, overstocked). False only for 'none'.
 */
export function hasUsableVelocity(level) {
  return isVelocityConfidence(level) && level !== VELOCITY_CONFIDENCE.none
}
