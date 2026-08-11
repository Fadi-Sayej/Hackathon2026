/**
 * demandEngine — turns external factors into a per-product demand index.
 *
 * WHAT IT COMPUTES
 *   demand(p, d) = base(p)
 *                x product over families of (family_effect ^ family_weight)
 *                x gates(p, d)                       // 0 or 1, evaluated LAST
 *                clamped to [0.2, 3.0]
 *
 * THE FOUR COMPOSITION RULES, AND WHY EACH EXISTS
 *   1. Group WITHIN a family before multiplying ACROSS families.
 *      temp_max_c, season and month_of_year all say "summer". Multiplied straight
 *      through that is the same fact counted three times.
 *   2. Neutral is 1.0 and unlisted parameters are skipped entirely.
 *      A missing factor has to vanish without trace — that is what makes it safe
 *      to declare 109 parameters while only 58 are collected.
 *   3. Clamp the result. There is no day on which a shop sells 47x normal; twenty
 *      mild multipliers otherwise compound into nonsense.
 *   4. Gates evaluate last and override everything above them. A gate is not a very
 *      small multiplier — no amount of heat makes chametz sellable during Pesach.
 *
 * WHAT IT IS NOT
 *   No LLM. Every input is an API reading, a calendar computation, or a number from
 *   our own till. The classification layer (#51) only decides WHICH archetype a
 *   product belongs to; it never participates in this arithmetic.
 */

export const DEFAULT_CLAMP = [0.2, 3.0]

/**
 * A gate may only fire on a product whose flag a human has approved.
 *
 * One wrong chametz call means a forbidden sale in a client's store, so this is
 * enforced here rather than left to whoever assembles the profiles.
 */
export function gateMayFire(gate, profile) {
  if (!gate?.requiresFlag) return true
  if (!profile?.flags?.[gate.requiresFlag]) return false
  if (gate.requiresHumanReview && !profile.reviewedBy) return false
  return true
}

/**
 * Combine parameters inside one family. Weighted mean in log space, so a family
 * with one strong factor and three neutral ones does not get diluted to nothing,
 * and so the combination stays symmetric for boosts and suppressions.
 */
export function combineFamily(effects) {
  const live = effects.filter((entry) => Number.isFinite(entry?.value) && entry.value > 0)
  if (!live.length) return 1
  let weightSum = 0
  let logSum = 0
  for (const { value, weight = 1 } of live) {
    logSum += Math.log(value) * weight
    weightSum += weight
  }
  return weightSum ? Math.exp(logSum / weightSum) : 1
}

function clamp(value, [low, high]) {
  return Math.min(high, Math.max(low, value))
}

/**
 * Resolve one product's sensitivity to a parameter.
 * Absent from the archetype ⇒ 1.0 ⇒ contributes nothing.
 */
function sensitivity(archetype, paramId) {
  const value = archetype?.sensitivities?.[paramId]
  return Number.isFinite(value) ? value : 1
}

/**
 * How strongly a factor is present today, 0..1.
 * A sensitivity of 1.45 at intensity 0.5 applies as 1.45^0.5, so a mild day gets a
 * mild effect instead of the full one.
 */
function applyIntensity(sensitivityValue, intensity) {
  if (sensitivityValue === 1) return 1
  const strength = Number.isFinite(intensity) ? clamp(intensity, [0, 1]) : 1
  return Math.pow(sensitivityValue, strength)
}

/**
 * @param {object} args
 * @param {object} args.product      canonical product (needs id, name)
 * @param {object} args.profile      { archetype, flags, reviewedBy } from #51, optional
 * @param {object} args.archetypes   name -> { sensitivities, flags }
 * @param {object} args.registry     { families: { name: { weight, params: [...] } }, gates, clamp }
 * @param {object} args.factors      paramId -> { value: 0..1 intensity, label? }
 * @param {number} args.base         baseline units/day, or 1 to get a pure index
 */
export function computeDemand({
  product,
  profile = null,
  archetypes = {},
  registry,
  factors = {},
  base = 1,
}) {
  const clampRange = registry?.clamp ?? DEFAULT_CLAMP
  const archetypeName = profile?.archetype ?? 'unclassified'
  const archetype = archetypes[archetypeName] ?? archetypes.unclassified ?? {}

  const drivers = []
  const familyEffects = []

  for (const [familyName, family] of Object.entries(registry?.families ?? {})) {
    const effects = []
    for (const param of family.params ?? []) {
      if (param.type === 'gate' || param.type === 'signal') continue
      if (param.active === false) continue

      const factor = factors[param.id]
      if (!factor) continue                       // rule 2: not collected ⇒ absent

      const raw = sensitivity(archetype, param.id)
      if (raw === 1) continue                     // product is indifferent to it

      const value = applyIntensity(raw, factor.value)
      effects.push({ value, weight: 1 })
      drivers.push({
        family: familyName,
        param: param.id,
        sensitivity: raw,
        intensity: factor.value ?? 1,
        effect: value,
        label: factor.label ?? null,
      })
    }

    const combined = combineFamily(effects)      // rule 1: group inside the family
    if (combined !== 1) {
      familyEffects.push({ family: familyName, value: combined, weight: family.weight ?? 1 })
    }
  }

  // Multiply across families, each raised to its own family weight.
  let multiplier = 1
  for (const { value, weight } of familyEffects) {
    multiplier *= Math.pow(value, weight)
  }

  const beforeClamp = base * multiplier
  const clamped = clamp(beforeClamp, clampRange)   // rule 3

  // Rule 4: gates last, and they override everything above.
  const gatesEvaluated = []
  let blocked = null
  for (const [gateName, gate] of Object.entries(registry?.gates ?? {})) {
    const factor = factors[gateName]
    if (!factor?.active) { gatesEvaluated.push({ gate: gateName, status: 'inactive' }); continue }
    if (!gateMayFire(gate, profile)) {
      gatesEvaluated.push({
        gate: gateName,
        status: profile?.flags?.[gate.requiresFlag] ? 'awaiting_human_review' : 'not_applicable',
      })
      continue
    }
    gatesEvaluated.push({ gate: gateName, status: 'fired', action: factor.action, reason: factor.reason })
    if (factor.action === 'BLOCK') blocked = { gate: gateName, ...factor }
  }

  drivers.sort((a, b) => Math.abs(b.effect - 1) - Math.abs(a.effect - 1))

  return {
    productId: product?.id ?? null,
    archetype: archetypeName,
    demandIndex: blocked ? 0 : Number(clamped.toFixed(4)),
    baseline: base,
    multiplier: Number(multiplier.toFixed(4)),
    clamped: beforeClamp !== clamped,
    blocked,
    // The decomposition is what makes 109 parameters debuggable instead of a black
    // box: it shows which factors moved this number, feeds the Arabic explanation
    // with real evidence, and later reveals which parameters ever predicted anything.
    topDrivers: drivers.slice(0, 5).map((d) => ({
      family: d.family,
      param: d.param,
      effect: Number((d.effect - 1).toFixed(4)),
      label: d.label,
    })),
    familyEffects: familyEffects.map((f) => ({
      family: f.family,
      effect: Number((f.value - 1).toFixed(4)),
    })),
    gatesEvaluated,
    // 'none' unless real velocity backs the baseline. The caller owns this, but the
    // default must be the honest one.
    velocityConfidence: base > 1 ? 'low' : 'none',
  }
}
