import { beforeEach, describe, expect, it } from 'vitest'

import {
  RECEIVING_CSV_HEADER,
  RECEIVING_QUEUE_KEY,
  appendEntry,
  knownSuppliers,
  loadQueue,
  makeEntry,
  readLastSupplier,
  rememberLastSupplier,
  saveQueue,
  toCsv,
  todayIso,
  undoLast,
} from '../receivingQueue.js'

function fakeStorage(seed = {}) {
  const store = new Map(Object.entries(seed))
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  }
}

function validInput(overrides = {}) {
  return {
    barcode: '7290000066318',
    productName: 'קוקה קולה 1.5 ליטר',
    quantity: '24',
    supplier: 'Tempo',
    unitCost: '4.5',
    receivedAt: '2026-08-10',
    expiryDate: '2026-12-31',
    ...overrides,
  }
}

describe('makeEntry', () => {
  it('normalizes a complete line', () => {
    const entry = makeEntry(validInput(), { now: new Date('2026-08-13T09:00:00Z') })
    expect(entry).toEqual({
      barcode: '7290000066318',
      productName: 'קוקה קולה 1.5 ליטר',
      quantity: 24,
      supplier: 'Tempo',
      unitCost: 4.5,
      receivedAt: '2026-08-10',
      expiryDate: '2026-12-31',
      recordedAt: '2026-08-13T09:00:00.000Z',
      source: 'manual_ui',
    })
  })

  it('defaults receivedAt to today', () => {
    const entry = makeEntry(validInput({ receivedAt: '' }), { now: new Date('2026-08-13T09:00:00Z') })
    expect(entry.receivedAt).toBe('2026-08-13')
  })

  it('accepts a line with no expiry date and no unit cost', () => {
    const entry = makeEntry(validInput({ expiryDate: '', unitCost: '' }))
    expect(entry.expiryDate).toBe('')
    expect(entry.unitCost).toBe('')
  })

  it('trims the barcode and the supplier', () => {
    const entry = makeEntry(validInput({ barcode: '  111  ', supplier: '  Osem  ' }))
    expect(entry.barcode).toBe('111')
    expect(entry.supplier).toBe('Osem')
  })

  it.each([
    ['', 'barcode'],
    ['   ', 'barcode'],
  ])('rejects a missing barcode (%s)', (barcode) => {
    expect(() => makeEntry(validInput({ barcode }))).toThrow(/barcode/i)
  })

  it.each(['', '0', '-3', 'abc', '2.5'])('rejects quantity %s', (quantity) => {
    expect(() => makeEntry(validInput({ quantity }))).toThrow(/quantity/i)
  })

  it.each(['', '   '])('rejects a missing supplier (%s)', (supplier) => {
    expect(() => makeEntry(validInput({ supplier }))).toThrow(/supplier/i)
  })

  it('rejects a negative or non-numeric unit cost', () => {
    expect(() => makeEntry(validInput({ unitCost: '-1' }))).toThrow(/cost/i)
    expect(() => makeEntry(validInput({ unitCost: 'free' }))).toThrow(/cost/i)
  })
})

describe('queue operations', () => {
  it('puts the newest entry first', () => {
    const first = makeEntry(validInput({ barcode: '111' }))
    const second = makeEntry(validInput({ barcode: '222' }))
    const queue = appendEntry(appendEntry([], first), second)
    expect(queue.map((row) => row.barcode)).toEqual(['222', '111'])
  })

  it('does not mutate the array it is given', () => {
    const queue = []
    appendEntry(queue, makeEntry(validInput()))
    expect(queue).toEqual([])
  })

  it('undo removes only the most recent entry', () => {
    const queue = appendEntry(
      appendEntry([], makeEntry(validInput({ barcode: '111' }))),
      makeEntry(validInput({ barcode: '222' })),
    )
    expect(undoLast(queue).map((row) => row.barcode)).toEqual(['111'])
  })

  it('undo on an empty queue is a no-op', () => {
    expect(undoLast([])).toEqual([])
  })

  it('lists known suppliers uniquely and sorted', () => {
    const queue = [
      makeEntry(validInput({ supplier: 'Tempo' })),
      makeEntry(validInput({ supplier: 'Osem' })),
      makeEntry(validInput({ supplier: 'Tempo' })),
    ]
    expect(knownSuppliers(queue)).toEqual(['Osem', 'Tempo'])
  })
})

describe('toCsv', () => {
  it('emits the header the Python importer reads', () => {
    expect(toCsv([]).trim()).toBe(RECEIVING_CSV_HEADER)
  })

  it('emits one row per entry in the header order', () => {
    const csv = toCsv([makeEntry(validInput(), { now: new Date('2026-08-13T09:00:00Z') })])
    const [header, row] = csv.trim().split('\n')
    expect(header).toBe(RECEIVING_CSV_HEADER)
    expect(row).toBe(
      '7290000066318,"קוקה קולה 1.5 ליטר",24,Tempo,4.5,2026-08-10,2026-12-31,2026-08-13T09:00:00.000Z,manual_ui',
    )
  })

  it('quotes a product name containing a comma or a quote', () => {
    const csv = toCsv([makeEntry(validInput({ productName: 'במבה, גדול "ענק"' }))])
    expect(csv).toContain('"במבה, גדול ""ענק"""')
  })
})

describe('storage', () => {
  let storage
  beforeEach(() => {
    storage = fakeStorage()
  })

  it('round-trips the queue', () => {
    const queue = [makeEntry(validInput())]
    saveQueue(queue, storage)
    expect(loadQueue(storage)).toEqual(queue)
  })

  it('reads an absent, empty or corrupt value as an empty queue', () => {
    expect(loadQueue(fakeStorage())).toEqual([])
    expect(loadQueue(fakeStorage({ [RECEIVING_QUEUE_KEY]: 'not json' }))).toEqual([])
    expect(loadQueue(fakeStorage({ [RECEIVING_QUEUE_KEY]: '{"not":"an array"}' }))).toEqual([])
    expect(loadQueue(null)).toEqual([])
  })

  it('remembers the last supplier across loads', () => {
    rememberLastSupplier('Tempo', storage)
    expect(readLastSupplier(storage)).toBe('Tempo')
  })

  it('reads an unset last supplier as an empty string', () => {
    expect(readLastSupplier(fakeStorage())).toBe('')
    expect(readLastSupplier(null)).toBe('')
  })

  it('never throws when storage rejects a write', () => {
    const failing = {
      getItem: () => null,
      setItem: () => { throw new Error('QuotaExceededError') },
      removeItem: () => {},
    }
    expect(() => saveQueue([], failing)).not.toThrow()
    expect(() => rememberLastSupplier('Tempo', failing)).not.toThrow()
  })
})

describe('todayIso', () => {
  it('returns the UTC calendar date', () => {
    expect(todayIso(new Date('2026-08-13T22:30:00Z'))).toBe('2026-08-13')
  })
})
