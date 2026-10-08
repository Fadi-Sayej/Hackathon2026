import { describe, expect, it } from 'vitest'

import { UNITS_SCHEMA, blankUnit, cleaned, startingUnits, unitProblem } from '../shelfUnits.js'

/** D-38, F12-S1 FR-228, AC-215: what the form saves. The Python side is src/owner_state/shelf_units.py. */
const unit = (over = {}) => ({ ...blankUnit(), name: 'Fridge 1', departments: ['drinks'],
  shelves: [{ length_cm: '100', height_cm: '' }, { length_cm: '100', height_cm: '35' }], ...over })

describe('a unit the form can save', () => {
  it('needs a name, a department, and each shelf\'s length and height, the top one\'s may be empty', () => {
    expect(unitProblem(unit(), [])).toBeNull()
    expect(unitProblem(unit({ name: ' ' }), [])).toBe('incomplete')
    expect(unitProblem(unit({ departments: [] }), [])).toBe('incomplete')
    expect(unitProblem(unit({ shelves: [{ length_cm: '100', height_cm: '35' }, { length_cm: '100', height_cm: '' }] }), []))
      .toBe('incomplete')                                         // only the top shelf may be open above
    expect(unitProblem(unit({ shelves: [{ length_cm: '0', height_cm: '' }] }), [])).toBe('incomplete')
    expect(unitProblem(unit({ shelves: [{ length_cm: '10.5', height_cm: '' }] }), [])).toBe('incomplete')
  })

  it('may not take another unit\'s name', () => {
    expect(unitProblem(unit({ name: 'Fridge 1 ' }), [unit()])).toBe('nameTwice')
  })

  it('is saved in whole centimetres, with no height where the top shelf is open', () => {
    expect(cleaned(unit({ eye_level_shelf: 2 }))).toEqual({
      name: 'Fridge 1', departments: ['drinks'], chilled: false, eye_level_shelf: 2,
      shelves: [{ length_cm: 100, height_cm: null }, { length_cm: 100, height_cm: 35 }],
    })
  })
})

describe('where the form starts', () => {
  const published = [{ name: 'Old', departments: ['drinks'], chilled: false, eye_level_shelf: null, shelves: [{ length_cm: 90, height_cm: '' }] }]
  const saved = { schema: UNITS_SCHEMA, saved_at: '2026-10-08T09:00:00.000Z',
    units: [{ name: 'New', departments: ['drinks'], chilled: false, eye_level_shelf: null, shelves: [{ length_cm: 100, height_cm: null }] }] }

  it('from the owner\'s last save while the layout file has not taken it', () => {
    expect(startingUnits(published, saved, null)[0].name).toBe('New')
    expect(startingUnits(published, saved, '2026-10-07T20:00:00.000Z')[0].shelves[0].height_cm).toBe('')
  })

  it('from the published units once the file has taken that save, or when nothing was saved', () => {
    expect(startingUnits(published, saved, '2026-10-08T09:00:00.000Z')).toBe(published)
    expect(startingUnits(published, null, null)).toBe(published)
    expect(startingUnits(published, { ...saved, schema: 2 }, null)).toBe(published)
  })
})
