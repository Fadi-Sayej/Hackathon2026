/**
 * compose — the only thing that decides what the owner sees.
 *
 * A pure function: no fetch, no persistence, and no clock read (`now` is a parameter), so
 * the same artefact and owner state always produce the same surface.
 *
 * Selection lives here and nowhere else. A component that filtered entries itself could not
 * be tested against AC-100, and would drift from the engine's ordering the first time
 * someone changed a page.
 */

// SPEC-GAP-A: no specification produces margin_below_cost, so it is built browse-only and
// is not admitted to the daily surface until SPEC-008 exists. Its page still renders it.
const NOT_ADMITTED = new Set(['margin_below_cost'])

// owner_questions is a panel of its own (D-8 caps it at three), not entries on this surface.
const NOT_ENTRIES = new Set(['owner_questions'])

// F8 never reaches Today (F8-S1 FR-160, OQ-901): its suggestions live on Reorder, and a line
// saying "waiting for daily sales" every morning would be the day's first thing to read.
export const NOT_ON_TODAY = new Set(['order_quantity', 'market_running_out', 'market_boost'])

// Phase 5 Task 5.0: published before any screen for it existed, so kept off every screen.
// Task 5.13 took `order_quantity` off (Reorder renders it whole, and Data names it). The market
// signal and the boost stay: the owner approved them as facts ON the Reorder cards, not as
// capabilities of their own, and approved no label that would name them on Data.
// Phase 6 Task 6.5 took `assortment_gap` off, once the repository owner approved its card.
export const NOT_YET_SHOWN = new Set(['market_running_out', 'market_boost'])

const SETTLED = new Set(['acted', 'declined'])

function isSettled(outcome, now) {
  if (!outcome) return false
  if (SETTLED.has(outcome.status)) return true
  if (outcome.status === 'deferred') {
    // No deferred_until means deferred indefinitely; a date in the future still hides it.
    return !Number.isFinite(outcome.deferred_until) || outcome.deferred_until > now
  }
  return false
}

export function compose(artefact, ownerState, { now } = {}) {
  const surface = artefact?.thresholds?.surface || {}
  const bound = Number.isFinite(surface.bound) ? surface.bound : 10
  const unvaluedPlaces = Number.isFinite(surface.unvalued_places) ? surface.unvalued_places : 3
  const unvaluedOrder = Array.isArray(surface.unvalued_order) ? surface.unvalued_order : []
  // F9-S1 FR-171: at most this many unvalued places for a capability. Unlisted: no cap.
  const unvaluedCaps = surface.unvalued_caps && typeof surface.unvalued_caps === 'object' ? surface.unvalued_caps : {}
  // F6-S1 FR-106a: these capabilities are shown in the order the engine published them (F9's,
  // and reconciliation's biggest gap first). A capability policy does not list is ordered by id.
  const engineOrdered = new Set(Array.isArray(surface.engine_ordered) ? surface.engine_ordered : [])
  const outcomes = ownerState?.outcomes || {}

  const unavailable = []
  const candidates = []
  const published = new Map()        // entry -> its position in its capability's list

  for (const [id, capability] of Object.entries(artefact?.capabilities || {})) {
    if (NOT_ON_TODAY.has(id) || NOT_YET_SHOWN.has(id)) continue
    if (capability?.status === 'unavailable') {
      // AC-107. An unavailable capability is a finding in itself; rendering it as an empty
      // entry list would read as "nothing to act on", which is a different claim.
      unavailable.push({ id, reason: capability.unavailable_reason ?? null })
      continue
    }
    if (NOT_ADMITTED.has(id) || NOT_ENTRIES.has(id)) continue
    for (const [position, entry] of (capability?.entries || []).entries()) {
      if (isSettled(outcomes[entry.id], now)) continue
      published.set(entry, position)
      candidates.push(entry)
    }
  }

  // AC-109 / INV-056. A barcode-less entry cannot be identified as the same product as
  // another, so it is never collapsed into one — hygiene's no_identifier records are
  // exactly that case and each is a separate thing to fix.
  const byProduct = new Map()
  const unkeyed = []
  for (const entry of candidates) {
    if (!entry.barcode) { unkeyed.push(entry); continue }
    const held = byProduct.get(entry.barcode)
    if (!held || amount(entry) > amount(held)) byProduct.set(entry.barcode, entry)
  }
  const deduped = [...byProduct.values(), ...unkeyed]

  const valued = deduped.filter((e) => e.value && Number.isFinite(e.value.amount))
  const unvalued = deduped.filter((e) => !(e.value && Number.isFinite(e.value.amount)))

  // D-2 / AC-103. Kinds are ordered as contiguous runs and never interleaved, so no reader
  // can add two of them together and no ordering implies they are comparable. Within a run,
  // descending by amount (AC-102).
  const kinds = [...new Set(valued.map((e) => e.value.kind))].sort()
  const orderedValued = kinds.flatMap((kind) =>
    valued.filter((e) => e.value.kind === kind)
      .sort((a, b) => b.value.amount - a.value.amount || String(a.id).localeCompare(String(b.id))))

  // The reserved places go to capabilities in the declared order; hygiene ranks last on
  // purpose, or a thousand records of finite cleanup would hold them for weeks (§9.2).
  const rank = (e) => {
    const i = unvaluedOrder.indexOf(e.capability)
    return i === -1 ? unvaluedOrder.length : i
  }
  const within = (a, b) => (a.capability === b.capability && engineOrdered.has(a.capability)
    ? published.get(a) - published.get(b)
    : String(a.id).localeCompare(String(b.id)))
  const taken = {}
  const orderedUnvalued = unvalued
    .sort((a, b) => rank(a) - rank(b) || within(a, b))
    .filter((e) => {
      const cap = unvaluedCaps[e.capability]
      if (!Number.isFinite(cap)) return true
      taken[e.capability] = (taken[e.capability] || 0) + 1
      return taken[e.capability] <= cap
    })
    .slice(0, unvaluedPlaces)

  // FR-106: unvalued entries are ALLOCATED places, never ranked against valued ones. Without
  // the reservation the pilot's 53 confirmed losses fill all ten every day and hygiene,
  // reconciliation and catalogue work never surface at all (F6-S1 §12). Unused reserved
  // places fall back to valued entries rather than leaving the surface short.
  const reserved = Math.min(unvaluedPlaces, orderedUnvalued.length)
  const entries = [
    ...orderedValued.slice(0, Math.max(0, bound - reserved)),
    ...orderedUnvalued.slice(0, reserved),
  ].slice(0, bound)

  // AC-101: what is not shown is not counted. AC-108: an empty surface with nothing
  // unavailable is a state of its own, not a blank page.
  return { entries, unavailable, nothingToDo: entries.length === 0 && unavailable.length === 0 }
}

function amount(entry) {
  return entry?.value && Number.isFinite(entry.value.amount) ? entry.value.amount : -Infinity
}

/**
 * Entries the owner deferred that are still hidden, oldest first.
 *
 * SEPARATE FROM `compose` ON PURPOSE
 *   AC-101 locks `compose`'s return to exactly `entries`, `unavailable` and `nothingToDo`,
 *   and FR-101 is the reason: "the bound exists to make the day's work finishable;
 *   displaying the remainder restores the firehose the bound removes." Adding a hidden-count
 *   to that object is the shape that rule forbids, and a test asserts the key set to stop it.
 *
 *   FR-102 says where this belongs instead: "The owner MUST be able to reach the full set of
 *   entries for a capability deliberately, ON A SURFACE OTHER THAN THIS ONE." So this is a
 *   function the data page calls, not a field the daily surface renders.
 *
 * WHY IT IS NEEDED AT ALL
 *   Before #142 "Later" sent no date, and `isSettled` reads a missing `deferred_until` as
 *   deferred indefinitely — one tap hid an entry for good. #142 added an Undo for the tap
 *   that just happened; it does nothing for records already written.
 *
 *   And the repair cannot be done server-side: `loadOwnerState` reads localStorage,
 *   `remoteOwnerState` exports only `writeThrough` and `pushAll` and never reads back, and
 *   `pushAll` merges this device's copy UP on the next session — so a `deferred_until`
 *   written straight to Firestore is both invisible here and overwritten on the next visit.
 *   The way back has to run in the browser.
 *
 * Only deferrals. `acted` and `declined` are decisions about the thing itself; a deferral is
 * a decision about WHEN, and these have no when.
 */
export function deferredEntries(artefact, ownerState, { now } = {}) {
  const outcomes = ownerState?.outcomes || {}
  const out = []
  for (const [id, capability] of Object.entries(artefact?.capabilities || {})) {
    if (capability?.status === 'unavailable' || NOT_ENTRIES.has(id) || NOT_ON_TODAY.has(id)) continue
    for (const entry of capability?.entries || []) {
      const outcome = outcomes[entry.id]
      if (outcome?.status !== 'deferred' || !isSettled(outcome, now)) continue
      out.push({
        entry,
        capability: id,
        at: Number.isFinite(outcome.at) ? outcome.at : null,
        until: Number.isFinite(outcome.deferred_until) ? outcome.deferred_until : null,
      })
    }
  }
  // Oldest first: the one hidden longest is the likeliest mistake, and — for anything
  // deferred before #142 — the one that has been invisible the longest.
  return out.sort((a, b) => (a.at ?? 0) - (b.at ?? 0))
}
