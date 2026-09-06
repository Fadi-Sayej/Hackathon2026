/**
 * explainReorder.js — render reorder facts into the owner's language.
 *
 * The decision layer (src/lib/analytics/reorderFacts.js) emits values; this turns
 * them into sentences. It is the ONLY place a reorder explanation is worded, and it
 * performs no arithmetic: every number printed is read straight off the fact record
 * that produced the order quantity. If a figure is not in the facts, it does not
 * appear — deriving one here is exactly how a screen starts contradicting an order.
 *
 * Four parts, in the order the owner asked for:
 *   1. why this quantity   2. why now
 *   3. what we are unsure about   4. what it costs to ignore
 *
 * Part 4 is omitted entirely when no cost price exists, rather than shown as zero.
 */

const CONFIDENCE_KEYS = {
  high: 'explain.unsure.confHigh',
  medium: 'explain.unsure.confMedium',
  low: 'explain.unsure.confLow',
  none: 'explain.unsure.confNone',
}

/** Drivers the pipeline recorded, as a readable list. Unknown keys pass through. */
function renderDrivers(drivers, t) {
  return drivers
    .map((driver) => {
      const key = `explain.driver.${driver}`
      const text = t(key)
      return text === key ? null : text
    })
    .filter(Boolean)
}

/**
 * @param facts the record from buildReorderFacts
 * @param t     translator from createTranslator/useT
 * @param n     number formatter (localises digits); defaults to identity
 * @returns {{quantity: string, timing: string, uncertainty: string, cost: string|null}}
 */
export function renderReorderExplanation(facts, t, n = (value) => String(value)) {
  if (!facts) return null

  // ── 1. Why this quantity ────────────────────────────────────────────
  const quantity = [
    t('explain.qty.stock', { stock: n(facts.currentStock) }),
    t(
      facts.rateBasis === 'corrected' ? 'explain.qty.rateCorrected' : 'explain.qty.rateObserved',
      { rate: n(facts.dailyRate) },
    ),
    t(facts.leadTimeAssumed ? 'explain.qty.leadAssumed' : 'explain.qty.leadMeasured', {
      lead: n(facts.leadTimeDays),
    }),
    t('explain.qty.formula', {
      leadDemand: n(facts.expectedDemandDuringLeadTime),
      safety: n(facts.safetyStock),
      stock: n(facts.currentStock),
      qty: n(facts.orderQty),
    }),
    // Units per case is absent from the POS export, so the number is single units
    // and says so rather than implying a case the supplier may not ship.
    facts.caseSize === null
      ? t('explain.qty.noCaseSize')
      : t('explain.qty.caseSize', { caseSize: n(facts.caseSize) }),
  ].join(' ')

  // ── 2. Why now ──────────────────────────────────────────────────────
  const timingParts = [
    facts.coverDays === null
      ? t('explain.now.coverUnknown')
      : facts.coverDays <= 0
        ? t('explain.now.coverNone')
        : t('explain.now.cover', { cover: n(facts.coverDays), lead: n(facts.leadTimeDays) }),
  ]
  const drivers = renderDrivers(facts.drivers ?? [], t)
  if (drivers.length) timingParts.push(t('explain.now.drivers', { drivers: drivers.join('، ') }))
  if (facts.demandMultiplier > 1) {
    timingParts.push(
      t('explain.now.multiplier', {
        // Read off the fact, not recomputed: this is the multiplier that was applied.
        pct: n(Math.round((facts.demandMultiplier - 1) * 100)),
      }),
    )
  }
  const timing = timingParts.join(' ')

  // ── 3. What we are unsure about ─────────────────────────────────────
  const unsure = [t(CONFIDENCE_KEYS[facts.rateConfidence] ?? CONFIDENCE_KEYS.none)]
  // Monthly aggregates: a per-day rate is derived, never observed. Said always,
  // because it qualifies every rate above.
  unsure.push(t('explain.unsure.monthlyBasis'))
  if (facts.rateBasis === 'corrected' && facts.censoredDays) {
    unsure.push(t('explain.unsure.censored', { days: n(facts.censoredDays) }))
  }
  if (facts.leadTimeAssumed) unsure.push(t('explain.unsure.leadAssumed'))
  if (facts.stockReconciles === false) unsure.push(t('explain.unsure.stockBroken'))
  if (facts.availabilityState === 'NEVER_STOCKED') unsure.push(t('explain.unsure.neverStocked'))
  const uncertainty = unsure.join(' ')

  // ── 4. What it costs to ignore ──────────────────────────────────────
  const cost =
    facts.costToIgnore === null
      ? null
      : t('explain.cost.value', {
          amount: n(facts.costToIgnore),
          units: n(facts.expectedDemandDuringLeadTime),
        })

  return { quantity, timing, uncertainty, cost }
}

/** The four parts as one block, for contexts that show a single paragraph. */
export function renderReorderExplanationText(facts, t, n) {
  const parts = renderReorderExplanation(facts, t, n)
  if (!parts) return ''
  return [parts.quantity, parts.timing, parts.uncertainty, parts.cost].filter(Boolean).join('\n\n')
}
