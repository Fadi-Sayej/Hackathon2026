// The pilot measurement, shaped for display (F13-S1, Phase 4 Task 4.5).
//
// The engine computes the measurement and publishes it as public/data/measurement.json, beside
// the artefact and never inside it, so the edge gate keeps it from the owner (ADR-023 revised
// 2026-09-27, ADR-029 Decision 6). This module only shapes that file for the page: it sums
// nothing and joins nothing (ADR-001). The one arithmetic it does is a share of two counts from
// the same set of decisions (acted ÷ decided). It never divides decisions by the run's entries,
// because those are different sets.
//
// It is pure (no React, no DOM, no storage), so the page's numbers are unit-tested directly
// (NFR-065).

export const DISMISS_REASONS = Object.freeze(['wrong_data', 'not_worth_it', 'already_handled', 'none'])

export const DISMISS_REASON_LABEL = Object.freeze({
  wrong_data: 'The data is wrong',
  not_worth_it: 'Not worth doing',
  already_handled: 'Already handled',
  none: 'Reason not recorded',
})

const share = (part, whole) => (whole > 0 ? part / whole : null)

export function viewMeasurement(block) {
  if (!block) return { state: 'missing' }
  if (block.status !== 'available') {
    return { state: 'unavailable', reason: block.unavailable_reason ?? null, pulledAt: block.window?.pulled_at ?? null }
  }

  const totals = block.totals
  const families = Object.entries(block.by_family ?? {})
    .map(([family, c]) => ({
      family,
      shown: c.shown,
      decided: c.decided,
      acted: c.acted,
      declined: c.declined,
      deferred: c.deferred,
      notInThisRun: c.not_in_this_run,
      actedShare: share(c.acted, c.decided),
    }))
    .sort((a, b) => (b.shown - a.shown) || (b.decided - a.decided) || a.family.localeCompare(b.family))

  const declined = block.declined_reasons ?? {}
  const reasons = DISMISS_REASONS.map((reason) => ({
    reason, label: DISMISS_REASON_LABEL[reason], count: declined[reason] ?? 0,
  }))

  const count = block.devices?.count
  return {
    state: 'ready',
    generatedAt: block.generated_at ?? null,
    window: block.window,
    totals,
    nothingDecided: totals.decided === 0,
    actedShare: share(totals.acted, totals.decided),
    families,
    money: (block.money ?? []).map(({ kind, certainty, amount, decisions }) => ({ kind, certainty, amount, decisions })),
    reasons,
    wrongDataShare: share(declined.wrong_data ?? 0, totals.declined),
    devices: Number.isInteger(count) ? count : null,
  }
}
