/**
 * Islamic calendar — Ramadan, the two Eids, and the fasting phase of the day.
 *
 * NO API. NO KEY. NO NETWORK.
 *   The Hijri calendar is arithmetic, and every JS runtime already ships it in
 *   Intl.DateTimeFormat under the `islamic` calendar. Calling a service for this
 *   would add a failure mode and a dependency in exchange for nothing.
 *
 * WHY THIS MATTERS MORE THAN THE HEBREW CALENDAR HERE
 *   The pilot store is in Kafr Qasim, a predominantly Arab town. Ramadan reshapes
 *   the whole trading day: food demand collapses during daylight and spikes at
 *   iftar. A model that knows about Pesach and not about Ramadan would be
 *   precisely backwards for this customer base.
 *
 * ACCURACY, STATED HONESTLY
 *   The tabular Islamic calendar can differ from local moon-sighting by a day.
 *   That is fine for demand shaping — a ±1 day error at the edge of Ramadan
 *   slightly mistimes a boost. It is NOT fine for anything religiously binding,
 *   and nothing here is used as such.
 */

const DAY_MS = 86_400_000

const RAMADAN = 9
const SHAWWAL = 10
const DHU_AL_HIJJAH = 12

function toISODate(value) {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date.toISOString().slice(0, 10)
}

/**
 * Hijri {year, month, day} for a Gregorian date, via the runtime's own calendar.
 * Returns null when the runtime lacks the islamic calendar rather than guessing.
 */
export function toHijri(date) {
  const iso = toISODate(date)
  if (!iso) return null
  try {
    const parts = new Intl.DateTimeFormat('en-u-ca-islamic-civil-nu-latn', {
      year: 'numeric', month: 'numeric', day: 'numeric', timeZone: 'UTC',
    }).formatToParts(new Date(`${iso}T12:00:00Z`))

    const read = (type) => Number(parts.find((part) => part.type === type)?.value)
    const year = read('year')
    const month = read('month')
    const day = read('day')
    if (![year, month, day].every(Number.isFinite)) return null
    return { year, month, day }
  } catch {
    return null
  }
}

function shiftDays(iso, days) {
  return new Date(Date.parse(`${iso}T00:00:00Z`) + days * DAY_MS).toISOString().slice(0, 10)
}

/** Walk back to the first day of the current Hijri month. */
function findMonthStart(iso, month) {
  for (let back = 0; back <= 32; back += 1) {
    const candidate = shiftDays(iso, -back)
    const hijri = toHijri(candidate)
    if (!hijri || hijri.month !== month) {
      return back === 0 ? null : shiftDays(iso, -(back - 1))
    }
    if (hijri.day === 1) return candidate
  }
  return null
}

/**
 * Which part of a Ramadan day we are in.
 *
 * Uses fixed local-clock bands rather than computed sunset. Real sunset in central
 * Israel moves roughly 17:30–19:30 across the year, so a band is imprecise — but
 * this drives a demand multiplier, not a prayer time, and the extra machinery of
 * solar position would buy precision the recommendation cannot use. Stated here so
 * nobody mistakes it for an astronomical calculation.
 */
export function ramadanPhase(hour) {
  if (!Number.isFinite(hour)) return null
  if (hour >= 3 && hour < 6) return 'suhoor'
  if (hour >= 6 && hour < 16) return 'daytime'
  if (hour >= 16 && hour < 20) return 'pre_iftar'
  return 'iftar'
}

/**
 * Everything the demand engine needs from the Islamic calendar for one date.
 * Never throws and never returns undefined fields.
 */
export function getIslamicContext(date, options = {}) {
  const iso = toISODate(date ?? new Date())
  const hijri = toHijri(iso)
  const empty = {
    date: iso, hijri: null, isRamadan: false, ramadanDay: null, ramadanPhase: null,
    isLastTenNights: false, isEidAlFitr: false, isEidAlAdha: false, isEidEve: false,
    daysToRamadan: null, source: 'computed_hijri',
  }
  if (!hijri || !iso) return empty

  const hour = Number.isFinite(options.hour) ? options.hour : new Date().getHours()
  const isRamadan = hijri.month === RAMADAN

  // Eid al-Fitr is 1 Shawwal; Eid al-Adha is 10 Dhu al-Hijjah.
  const isEidAlFitr = hijri.month === SHAWWAL && hijri.day <= 3
  const isEidAlAdha = hijri.month === DHU_AL_HIJJAH && hijri.day >= 10 && hijri.day <= 13
  const tomorrow = toHijri(shiftDays(iso, 1))
  const isEidEve =
    (hijri.month === RAMADAN && tomorrow?.month === SHAWWAL) ||
    (hijri.month === DHU_AL_HIJJAH && hijri.day === 9)

  let daysToRamadan = null
  if (!isRamadan) {
    for (let ahead = 1; ahead <= 365; ahead += 1) {
      if (toHijri(shiftDays(iso, ahead))?.month === RAMADAN) { daysToRamadan = ahead; break }
    }
  }

  return {
    date: iso,
    hijri,
    isRamadan,
    ramadanDay: isRamadan ? hijri.day : null,
    ramadanPhase: isRamadan ? ramadanPhase(hour) : null,
    isLastTenNights: isRamadan && hijri.day >= 21,
    isEidAlFitr,
    isEidAlAdha,
    isEidEve,
    daysToRamadan,
    ramadanStart: isRamadan ? findMonthStart(iso, RAMADAN) : null,
    source: 'computed_hijri',
  }
}
