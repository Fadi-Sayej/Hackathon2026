/**
 * factsGuard.js — reject any model output containing a figure the decision didn't hold.
 *
 * WHY THIS IS CODE AND NOT A PROMPT
 *   The owner checks these numbers against his own shelf. One invented figure costs
 *   us every explanation on the screen, so "please don't make up numbers" in a
 *   prompt is not a control — it is a hope. This validates the response against the
 *   facts record before anything can be displayed.
 *
 *   It is not theoretical. On the first realistic prompt tried against this key
 *   (2026-09-08), given "order 20 units", gemini-3.5-flash-lite and
 *   gemini-flash-lite-latest both wrote "25 units". Unprompted, on trivial input.
 *
 * WHAT COUNTS AS ALLOWED
 *   Every numeric value carried on the facts record, plus the small set of figures
 *   the rule-based renderer itself derives and prints (percentages from a
 *   multiplier). Rounded forms are accepted because prose legitimately rounds:
 *   8.38/day may be written "8.4" or "8". A number that matches nothing is a
 *   fabrication and rejects the whole response.
 */

/** Every number appearing in a piece of text, Latin or Arabic-Indic digits. */
export function numbersIn(text) {
  if (!text) return []
  const latinised = String(text).replace(/[٠-٩]/g, (d) =>
    String(d.charCodeAt(0) - 0x0660),
  )
  return (latinised.match(/\d+(?:[.,]\d+)?/g) ?? []).map((n) => Number(n.replace(',', '.')))
}

/** Numbers a rendered explanation is permitted to contain, given its facts. */
export function allowedNumbers(facts) {
  if (!facts) return new Set()

  const raw = [
    facts.currentStock,
    facts.dailyRate,
    facts.leadTimeDays,
    facts.expectedDemandDuringLeadTime,
    facts.safetyStock,
    facts.orderQty,
    facts.uncappedOrderQty,
    facts.shelfLifeDays,
    facts.coverDays,
    facts.censoredDays,
    facts.costToIgnore,
    facts.unitCost,
    facts.caseSize,
    // Percentages the renderer derives and prints from the multipliers.
    facts.demandMultiplier == null ? null : Math.round((facts.demandMultiplier - 1) * 100),
    facts.competitorLift == null ? null : Math.round((facts.competitorLift - 1) * 100),
  ].filter((v) => typeof v === 'number' && Number.isFinite(v))

  const allowed = new Set()

  // Numbers inside the product's own name are not claims — they are the name.
  // "קוקה קולה זירו 1.5 ליטר" and "ביצים חופשיות 12 יח" carry figures the model
  // must be able to repeat; rejecting them flagged correct output as fabrication
  // (observed on 2 of 10 products before this was added).
  for (const value of numbersIn(facts.productName)) allowed.add(value)

  for (const value of raw) {
    allowed.add(value)
    // Prose rounds, so accept the two forms a writer actually reaches for. floor
    // and ceil are deliberately NOT accepted: they widen the permitted set around
    // every figure and buy nothing a writer would use.
    allowed.add(Math.round(value))
    allowed.add(Math.round(value * 10) / 10)
  }
  return allowed
}

/**
 * WHAT THIS GUARD DOES NOT CATCH — stated because it decides how far to trust it.
 *
 * It catches INVENTED figures: a number that appears nowhere in the decision. It
 * cannot catch a MISAPPLIED one — a figure that is real but attached to the wrong
 * thing. The live example is exactly this: given orderQty 20 and
 * expectedDemandDuringLeadTime 25.14, the model wrote "order 25 units". 25 is a
 * true rounding of 25.14, so it passes the numeric check while telling the owner
 * to order a quantity the system never decided.
 *
 * Distinguishing the two needs to know which clause a number sits in, which means
 * parsing Hebrew prose — and a parser we trust that far would be doing the model's
 * job. So this is a floor, not a ceiling, and it is a real argument against letting
 * a model near these sentences at all.
 */

/**
 * Does this text stay inside the figures the decision actually used?
 *
 * @returns {{ok: boolean, invented: number[]}}
 */
export function validateAgainstFacts(text, facts) {
  const allowed = allowedNumbers(facts)
  const invented = []
  for (const n of numbersIn(text)) {
    if (!allowed.has(n)) invented.push(n)
  }
  return { ok: invented.length === 0, invented }
}

/**
 * Validate a whole provider result. Any offending field rejects the entire result:
 * a response half-trustworthy is not trustworthy, and mixing a checked sentence
 * with an unchecked one is how a fabricated figure reaches the screen.
 *
 * @returns {{ok: boolean, invented: number[], field: string|null}}
 */
export function validateExplanationResult(result, facts) {
  const fields = ['explanation', 'riskReason', 'businessImpact', 'confidenceNote']
  for (const field of fields) {
    const value = result?.[field]
    if (typeof value !== 'string' || !value) continue
    const { ok, invented } = validateAgainstFacts(value, facts)
    if (!ok) return { ok: false, invented, field }
  }
  return { ok: true, invented: [], field: null }
}
