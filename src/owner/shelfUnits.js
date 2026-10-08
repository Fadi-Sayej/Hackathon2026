/**
 * D-38: the owner's own description of each shelving unit, as the form edits and saves it
 * (F12-S1 FR-228). Whole centimetres; the top shelf may have no height when nothing is above it.
 */

/** MUST equal SCHEMA in src/owner_state/shelf_units.py, which leaves any other save unwritten. */
export const UNITS_SCHEMA = 1

export const blankShelf = () => ({ length_cm: '', height_cm: '' })
export const blankUnit = () => ({ name: '', departments: [], chilled: false, eye_level_shelf: null, shelves: [blankShelf()] })
const whole = (v) => /^\d{1,4}$/.test(String(v ?? '').trim()) && Number(v) >= 1

/** What the form asks for, or why it cannot be saved yet. */
export function unitProblem(unit, others) {
  const name = unit.name.trim()
  if (!name || !unit.departments.length) return 'incomplete'
  if (!unit.shelves.length) return 'incomplete'
  for (const [i, s] of unit.shelves.entries()) {
    if (!whole(s.length_cm)) return 'incomplete'
    const open = i === 0 && String(s.height_cm ?? '').trim() === ''
    if (!open && !whole(s.height_cm)) return 'incomplete'
  }
  if (others.some((o) => o.name.trim() === name)) return 'nameTwice'
  return null
}

/** The unit as it is saved: whole centimetres, and no height where the top shelf is open above. */
export function cleaned(unit) {
  return {
    name: unit.name.trim(), departments: [...unit.departments], chilled: Boolean(unit.chilled),
    eye_level_shelf: unit.eye_level_shelf || null,
    shelves: unit.shelves.map((s) => ({
      length_cm: Number(s.length_cm),
      height_cm: String(s.height_cm ?? '').trim() === '' ? null : Number(s.height_cm),
    })),
  }
}

/** The units to start the form from: the owner's last save when the layout file has not taken it
 *  yet (the nightly writes it), else the units the artefact publishes. */
export function startingUnits(published, saved, takenAt) {
  if (saved?.schema === UNITS_SCHEMA && Array.isArray(saved.units) && (!takenAt || saved.saved_at > takenAt)) {
    return saved.units.map((u) => ({ ...u, shelves: u.shelves.map((s) => ({ ...s, height_cm: s.height_cm ?? '' })) }))
  }
  return published
}

export function within(ms, promise) {
  let timer
  const late = new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('timeout')), ms) })
  return Promise.race([promise, late]).finally(() => clearTimeout(timer))
}
