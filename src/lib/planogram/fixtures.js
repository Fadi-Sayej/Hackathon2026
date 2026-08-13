/**
 * Fixture model — the store's physical shelving, as the manager draws it.
 *
 * WHY THIS EXISTS
 *   Every engine in `src/lib/analytics/` that touches shelf space has been
 *   running on `shelfCapacity: 10`, a constant hardcoded into every one of the
 *   7,674 products by scripts/normalize-datasets.mjs. It is not a measurement of
 *   anything. A planogram built on it cannot be executed in a real store,
 *   because the shelf it describes does not exist.
 *
 *   The fix is not to go measure 7,674 packages. It is to let the manager spend
 *   ten minutes drawing their own floor plan — how many gondolas, how long, how
 *   many shelves high — and derive capacity from that. The person who knows the
 *   store is the person entering the data.
 *
 * SHELF LEVELS COME FROM HEIGHT, NOT FROM RANK
 *   `src/lib/analytics/planogramEngine.js` assigns EYE_LEVEL / MIDDLE / TOP /
 *   BOTTOM by score: the best-scoring products are *called* eye level. That is
 *   backwards. Eye level is a fact about a fixture — roughly 120–170cm off the
 *   floor — and which shelf of a 1.8m gondola qualifies depends on how many
 *   shelves it has. `describeShelves()` computes it from geometry, so a 0.9m
 *   chest freezer correctly has no eye-level shelf at all.
 */

/** Adult eye level in a standing shop, metres from the floor. */
const EYE_LEVEL_BAND = [1.2, 1.7]
/** Comfortable reach without stooping or stretching. */
const HAND_LEVEL_FLOOR = 0.6

/**
 * Fixture types available in the layout editor.
 *
 * `sides` is the merchandisable face count: a gondola is an island shopped from
 * both aisles, so its linear metres are double its length. Getting this wrong
 * halves or doubles every capacity figure downstream.
 */
export const FIXTURE_KINDS = {
  gondola: { label: 'رف مزدوج (جزيرة)', color: '#c8a97e', stroke: '#8d6a45', text: '#3a2a19', radius: '3px', w: 6, d: 1.2, levels: 4, height: 1.8, sides: 2 },
  wall: { label: 'رف جداري', color: '#a8894f', stroke: '#6f5730', text: '#ffffff', radius: '3px', w: 8, d: 0.6, levels: 5, height: 2.2, sides: 1 },
  endcap: { label: 'رأس ممر (إندكاب)', color: '#d98c3c', stroke: '#9c5e21', text: '#3a2a19', radius: '3px', w: 1.2, d: 1.2, levels: 4, height: 1.6, sides: 1 },
  fridge: { label: 'ثلاجة عرض', color: '#7fbcd8', stroke: '#3f7f9c', text: '#12313d', radius: '3px', w: 3, d: 0.9, levels: 5, height: 2, sides: 1 },
  freezer: { label: 'فريزر أفقي', color: '#a9d8e8', stroke: '#5b9cb5', text: '#12313d', radius: '7px', w: 2, d: 1, levels: 1, height: 0.9, sides: 1 },
  produce: { label: 'طاولة خضار', color: '#8fc17a', stroke: '#54803f', text: '#1c3312', radius: '7px', w: 2.5, d: 1.5, levels: 2, height: 1, sides: 1 },
  bakery: { label: 'ركن مخبوزات', color: '#e0b96a', stroke: '#a3803a', text: '#3a2a19', radius: '7px', w: 2.5, d: 1, levels: 3, height: 1.6, sides: 1 },
  checkout: { label: 'صندوق دفع', color: '#b8a9d8', stroke: '#7a6aa0', text: '#241c3a', radius: '4px', w: 2.5, d: 1, levels: 1, height: 1, sides: 1 },
  bin: { label: 'سلة عروض', color: '#e08c8c', stroke: '#a35555', text: '#3a1919', radius: '50%', w: 1.2, d: 1.2, levels: 1, height: 0.9, sides: 1 },
}

/** Starting floor plans, so the editor is never a blank page. */
export const FIXTURE_PRESETS = {
  small: {
    name: 'متجر صغير — ٤ ممرات',
    hint: '١٢×٩ م',
    w: 12,
    h: 9,
    items: [
      ['wall', 'جداري شمال', 0.3, 0.3, 11.4, 0.6],
      ['gondola', 'ممر ١', 1.5, 2, 9, 1.2],
      ['gondola', 'ممر ٢', 1.5, 4, 9, 1.2],
      ['fridge', 'ثلاجة مشروبات', 0.3, 6, 4, 0.9],
      ['produce', 'خضار', 6, 6.2, 2.5, 1.5],
      ['checkout', 'كاشير ١', 9.2, 7.4, 2.5, 1],
    ],
  },
  medium: {
    name: 'سوبرماركت متوسط',
    hint: '٢٠×١٤ م',
    w: 20,
    h: 14,
    items: [
      ['wall', 'جداري شمال', 0.3, 0.3, 19.4, 0.6],
      ['wall', 'جداري غرب', 0.3, 1.2, 0.6, 10],
      ['gondola', 'ممر ١', 2.5, 2.5, 13, 1.2],
      ['gondola', 'ممر ٢', 2.5, 5, 13, 1.2],
      ['gondola', 'ممر ٣', 2.5, 7.5, 13, 1.2],
      ['fridge', 'ثلاجات ألبان', 16.5, 2.5, 0.9, 8],
      ['freezer', 'فريزر', 6, 10, 3, 1],
      ['produce', 'خضار وفواكه', 10.5, 10, 3, 1.6],
      ['bakery', 'مخبوزات', 1, 10.2, 2.5, 1],
      ['checkout', 'كاشير ١', 15, 11.8, 2.5, 1],
      ['checkout', 'كاشير ٢', 17.8, 11.8, 2.5, 1],
    ],
  },
  large: {
    name: 'فرع كبير — ممرات طويلة',
    hint: '٣٠×٢٠ م',
    w: 30,
    h: 20,
    items: [
      ['wall', 'جداري شمال', 0.4, 0.4, 29, 0.6],
      ['wall', 'جداري شرق', 28.9, 1.2, 0.6, 15],
      ['gondola', 'ممر ١', 3, 3, 20, 1.2],
      ['gondola', 'ممر ٢', 3, 5.5, 20, 1.2],
      ['gondola', 'ممر ٣', 3, 8, 20, 1.2],
      ['gondola', 'ممر ٤', 3, 10.5, 20, 1.2],
      ['endcap', 'إندكاب ١', 23.5, 3, 1.2, 1.2],
      ['endcap', 'إندكاب ٢', 23.5, 5.5, 1.2, 1.2],
      ['fridge', 'ثلاجات ألبان', 0.5, 3, 0.9, 9],
      ['freezer', 'فريزر ١', 8, 14, 3, 1],
      ['freezer', 'فريزر ٢', 12, 14, 3, 1],
      ['produce', 'خضار وفواكه', 17, 13.8, 4, 1.8],
      ['bakery', 'مخبوزات', 2, 14, 3, 1],
      ['bin', 'سلة عروض', 23, 14.5, 1.2, 1.2],
      ['checkout', 'كاشير ١', 22, 17, 2.5, 1],
      ['checkout', 'كاشير ٢', 25, 17, 2.5, 1],
      ['checkout', 'كاشير ٣', 1, 17, 2.5, 1],
    ],
  },
}

/** Expand a preset into editable fixture units. */
export function buildPreset(preset) {
  return preset.items.map(([kind, name, x, y, w, d], index) => ({
    id: `s${index}`,
    kind,
    name,
    x,
    y,
    w,
    d,
    levels: FIXTURE_KINDS[kind].levels,
    height: FIXTURE_KINDS[kind].height,
  }))
}

/** Merchandisable faces for a unit, defaulting to one for unknown kinds. */
export function sidesOf(unit) {
  return FIXTURE_KINDS[unit.kind]?.sides ?? 1
}

/**
 * Total shelf run of a unit, in metres.
 *
 * The shopper-facing length is the longer footprint edge — a gondola rotated to
 * run north-south is still shopped along its length.
 */
export function linearMetres(unit) {
  const run = Math.max(unit.w, unit.d)
  return run * (unit.levels || 1) * sidesOf(unit)
}

/** Total linear metres across a whole floor plan. */
export function totalLinearMetres(units) {
  return units.reduce((sum, unit) => sum + linearMetres(unit), 0)
}

/** Share of the floor covered by fixtures, 0–1. */
export function floorOccupancy(units, storeW, storeH) {
  const area = storeW * storeH
  if (area <= 0) return 0
  return units.reduce((sum, unit) => sum + unit.w * unit.d, 0) / area
}

/**
 * Facing capacity of a unit before any product is assigned.
 *
 * A planning figure only. Once products are allocated, capacity is the sum of
 * their real package widths — see `allocateShelf()` — and this estimate is
 * discarded. The default assumes an 8cm average facing, which is about right
 * for a mixed grocery run and wrong for a run of 22cm rice sacks.
 */
export function estimateFacingCapacity(unit, averageFacingWidthCm = 8) {
  const runCm = linearMetres(unit) * 100
  return Math.max(0, Math.floor(runCm / averageFacingWidthCm))
}

/**
 * Break a unit into its individual shelves, top to bottom, each classified by
 * the height it actually sits at.
 *
 * Returns `shelfLevel` values matching the vocabulary already used by
 * `complianceEngine.js` so the two can be compared without a translation table.
 */
export function describeShelves(unit) {
  const levels = Math.max(1, Math.round(unit.levels || 1))
  const unitHeight = unit.height || 1
  const gap = unitHeight / levels
  const runCm = Math.max(unit.w, unit.d) * 100

  return Array.from({ length: levels }, (_, indexFromTop) => {
    const indexFromBottom = levels - 1 - indexFromTop
    const centreHeight = (indexFromBottom + 0.5) * gap
    return {
      index: indexFromTop,
      code: `الرف ${indexFromTop + 1}`,
      centreHeight: Math.round(centreHeight * 100) / 100,
      shelfLevel: classifyHeight(centreHeight),
      levelLabel: LEVEL_LABELS[classifyHeight(centreHeight)],
      runCm,
      // Vertical clearance limits how tall a package may be, and whether a
      // second unit can be stacked on top of the first.
      clearanceCm: Math.round(gap * 100),
    }
  })
}

const LEVEL_LABELS = {
  EYE_LEVEL: 'مستوى النظر',
  MIDDLE: 'مستوى اليد',
  TOP: 'مستوى علوي',
  BOTTOM: 'مستوى سفلي',
}

export { LEVEL_LABELS }

function classifyHeight(metres) {
  if (metres >= EYE_LEVEL_BAND[0] && metres <= EYE_LEVEL_BAND[1]) return 'EYE_LEVEL'
  if (metres > EYE_LEVEL_BAND[1]) return 'TOP'
  if (metres >= HAND_LEVEL_FLOOR) return 'MIDDLE'
  return 'BOTTOM'
}
