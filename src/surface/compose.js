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
  const outcomes = ownerState?.outcomes || {}

  const unavailable = []
  const candidates = []

  for (const [id, capability] of Object.entries(artefact?.capabilities || {})) {
    if (capability?.status === 'unavailable') {
      // AC-107. An unavailable capability is a finding in itself; rendering it as an empty
      // entry list would read as "nothing to act on", which is a different claim.
      unavailable.push({ id, reason: capability.unavailable_reason ?? null })
      continue
    }
    if (NOT_ADMITTED.has(id) || NOT_ENTRIES.has(id)) continue
    for (const entry of capability?.entries || []) {
      if (isSettled(outcomes[entry.id], now)) continue
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
  const orderedUnvalued = unvalued
    .sort((a, b) => rank(a) - rank(b) || String(a.id).localeCompare(String(b.id)))
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
