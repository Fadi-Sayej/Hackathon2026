import { describe, expect, it } from 'vitest'

import { buildSheetRows, toBuildSheetCsv } from '../buildSheet.js'

/**
 * The artefact a shop worker carries to the shelf. Everything else in this
 * module is a picture on a screen; this is the only output that gets executed.
 *
 * It is therefore ordered the way the work is done — shelf by shelf, left to
 * right — not by score.
 */

const plan = {
  shelves: [
    {
      code: 'الرف ١',
      shelfLevel: 'EYE_LEVEL',
      levelLabel: 'مستوى النظر',
      runCm: 200,
      usedCm: 60,
      items: [
        { productId: 'b1', productName: 'מים 1.5 ליטר', facings: 3, depthUnits: 4, stack: 1, onShelf: 12, widthCm: 9, currentStock: 40, status: 'ok' },
        { productId: 'b2', productName: 'קולה 330', facings: 2, depthUnits: 6, stack: 1, onShelf: 12, widthCm: 6.6, currentStock: 5, status: 'low' },
      ],
    },
    {
      code: 'الرف ٢',
      shelfLevel: 'BOTTOM',
      levelLabel: 'مستوى سفلي',
      runCm: 200,
      usedCm: 20,
      items: [
        { productId: 'b3', productName: 'אורז 5 קג', facings: 2, depthUnits: 2, stack: 1, onShelf: 4, widthCm: 22, currentStock: 0, status: 'out' },
      ],
    },
  ],
}

describe('row order', () => {
  it('follows the shelves in build order, not by score', () => {
    const rows = buildSheetRows(plan)

    expect(rows.map((row) => row.productId)).toEqual(['b1', 'b2', 'b3'])
  })

  it('numbers positions from the start of each shelf', () => {
    const rows = buildSheetRows(plan)

    expect(rows.map((row) => row.position)).toEqual([1, 2, 1])
  })
})

describe('what the worker needs', () => {
  it('states facings, depth and the resulting unit count', () => {
    const [row] = buildSheetRows(plan)

    expect(row.facings).toBe(3)
    expect(row.depthUnits).toBe(4)
    expect(row.unitsToPlace).toBe(12)
  })

  it('caps units to place at what is actually in stock', () => {
    // The plan wants 12 units of b2; there are 5. Asking for 12 is a wasted trip.
    const rows = buildSheetRows(plan)
    const cola = rows.find((row) => row.productId === 'b2')

    expect(cola.unitsToPlace).toBe(5)
    expect(cola.shortfall).toBe(7)
  })

  it('marks a zero-stock position as unfillable rather than asking for 4 units', () => {
    const rice = buildSheetRows(plan).find((row) => row.productId === 'b3')

    expect(rice.unitsToPlace).toBe(0)
    expect(rice.unfillable).toBe(true)
  })

  it('gives the running centimetre offset so the position is findable', () => {
    const rows = buildSheetRows(plan)

    expect(rows[0].startCm).toBe(0)
    expect(rows[1].startCm).toBe(27) // 3 facings x 9cm
  })
})

describe('csv export', () => {
  it('starts with a header row', () => {
    const csv = toBuildSheetCsv(plan)

    expect(csv.split('\n')[0]).toContain('shelf')
  })

  it('has one line per position plus the header', () => {
    const csv = toBuildSheetCsv(plan)

    expect(csv.trim().split('\n')).toHaveLength(4)
  })

  it('quotes product names so a comma cannot break the file', () => {
    const withComma = {
      shelves: [
        {
          code: 'الرف ١',
          levelLabel: 'مستوى النظر',
          runCm: 100,
          items: [{ productId: 'x', productName: 'מוצר, עם פסיק', facings: 1, depthUnits: 1, stack: 1, onShelf: 1, widthCm: 5, currentStock: 9, status: 'ok' }],
        },
      ],
    }

    const line = toBuildSheetCsv(withComma).split('\n')[1]

    expect(line).toContain('"מוצר, עם פסיק"')
    expect(line.split('","')).toHaveLength(2)
  })
})
