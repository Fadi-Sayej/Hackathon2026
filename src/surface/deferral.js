/**
 * How long "Later" lasts.
 *
 * WHAT WAS WRONG (#139)
 *   `EntryCard`'s third button sent `{ status: 'deferred' }` with no date. `recordOutcome`
 *   writes `deferred_until` only when it is given one, and `compose`'s `isSettled` reads a
 *   missing `deferred_until` as *deferred indefinitely*. So the button labelled لاحقاً /
 *   אחר כך / Later removed the entry for good, and nothing said so.
 *
 *   F6-S1 anticipated it exactly. OQ-604: *"FR-114 suppresses a deferred entry while the
 *   deferral stands, but nothing defines its duration. Without it, deferral is
 *   indistinguishable from permanent dismissal."* The state machine at §11 requires
 *   `deferred → presented` when the deferral lapses. The code shipped the failure the spec
 *   had written down.
 *
 * WHY THIS DOES NOT ANSWER OQ-604
 *   OQ-604 is open and it is the PM's. This picks the one duration that cannot be wrong:
 *   the **next local day boundary**.
 *
 *   The surface is regenerated nightly and is called "today's work". Whatever OQ-604
 *   eventually settles on — four hours, a week, until the evidence changes — the minimum
 *   honest meaning of a button reading "Later" is *"not in today's list"*. Shipping that is
 *   not choosing an answer; it is refusing to ship *forever* while the question is open, and
 *   every longer answer remains available. If OQ-604 later says a week, this becomes a
 *   floor rather than a mistake.
 *
 * WHY THE CLOCK IS A PARAMETER
 *   The same reason `compose` takes one: a function that reads the clock renders differently
 *   on two identical inputs, and a deferral must lapse because time passed in the app's
 *   state, not because something happened to re-render. `EntryCard` never sees it — the card
 *   reports which button was pressed, and the surface decides what that means.
 */

/**
 * The next local midnight strictly after `now`, as epoch milliseconds.
 *
 * Local, not UTC: the owner's day ends when his shop's day ends, and the nightly that
 * rebuilds the surface runs at ~02:40 UTC, which is already the next local day in Israel.
 * Strictly after, so a deferral made exactly at midnight lasts a day rather than no time.
 */
export function nextDayBoundary(now) {
  const at = new Date(now)
  if (Number.isNaN(at.getTime())) {
    throw new Error(`nextDayBoundary: ${String(now)} is not a time`)
  }
  const boundary = new Date(at.getFullYear(), at.getMonth(), at.getDate() + 1, 0, 0, 0, 0)
  return boundary.getTime()
}

/**
 * Fill in what a bare outcome from the card leaves out.
 *
 * Only deferral needs it today. Kept as one function rather than a branch inside the click
 * handler so the rule has somewhere to be tested, and so the next outcome that needs a
 * parameter has an obvious home.
 */
export function settleOutcome(outcome, { now }) {
  if (outcome?.status !== 'deferred') return outcome
  if (Number.isFinite(outcome.deferredUntil)) return outcome
  return { ...outcome, deferredUntil: nextDayBoundary(now) }
}
