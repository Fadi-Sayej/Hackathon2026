import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest'

import {
  CAPTURE_MODE_DELIVERY,
  CAPTURE_MODE_EXPIRY,
  EXPIRY_CSV_HEADER,
  EXPIRY_QUEUE_KEY,
  RECEIVING_CSV_HEADER,
  RECEIVING_QUEUE_KEY,
  appendEntry,
  exportForMode,
  isExpiryOnlyMode,
  knownSuppliers,
  loadQueue,
  makeEntry,
  makeEntryForMode,
  makeExpiryEntry,
  queueKeyForMode,
  readLastSupplier,
  rememberLastSupplier,
  saveQueue,
  toCsv,
  toExpiryCsv,
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

  it('defaults receivedAt to the local calendar date', () => {
    // Local components, not an instant: this must hold in whatever timezone the
    // suite happens to run in, and the date it defaults to is the shop's day.
    const entry = makeEntry(validInput({ receivedAt: '' }), { now: new Date(2026, 7, 13, 9, 0, 0) })
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

// received_at is the one date the lead-time median and the restock
// reconciliation window both rest on, and YomYom is a 24-hour forecourt shop
// where a 01:00 delivery is ordinary. Under toISOString() every delivery
// recorded between midnight and 03:00 Israel time was filed as yesterday.
describe('todayIso — the LOCAL business date, not the UTC one', () => {
  const originalTz = process.env.TZ

  beforeAll(() => {
    process.env.TZ = 'Asia/Jerusalem'
  })
  afterAll(() => {
    process.env.TZ = originalTz
  })

  it('files a 01:30 Israel-time delivery under that morning, not the previous day', () => {
    // 22:30Z on the 13th is 01:30 on the 14th in Jerusalem (UTC+3 in August).
    expect(todayIso(new Date('2026-08-13T22:30:00Z'))).toBe('2026-08-14')
  })

  it('returns the calendar date the shop is standing in, whatever the machine TZ', () => {
    expect(todayIso(new Date(2026, 7, 14, 0, 30, 0))).toBe('2026-08-14')
    expect(todayIso(new Date(2026, 0, 5, 23, 59, 0))).toBe('2026-01-05')
  })

  // The mirror image, west of UTC. It also proves the TZ override above is
  // doing something: this repo's own machines sit at UTC+3, where the broken
  // UTC implementation would agree with the Jerusalem case by luck.
  it('does not run ahead of the local day in a timezone behind UTC', () => {
    process.env.TZ = 'Pacific/Honolulu'
    // 05:00Z on the 14th is still 19:00 on the 13th in Honolulu (UTC-10).
    expect(todayIso(new Date('2026-08-14T05:00:00Z'))).toBe('2026-08-13')
    process.env.TZ = 'Asia/Jerusalem'
  })
})

describe('expiry-only capture mode', () => {
  it('recognises the mode', () => {
    expect(isExpiryOnlyMode(CAPTURE_MODE_EXPIRY)).toBe(true)
    expect(isExpiryOnlyMode(CAPTURE_MODE_DELIVERY)).toBe(false)
    expect(isExpiryOnlyMode(undefined)).toBe(false)
  })

  it('keeps the two queues apart, so the exports cannot be mixed', () => {
    expect(queueKeyForMode(CAPTURE_MODE_EXPIRY)).toBe(EXPIRY_QUEUE_KEY)
    expect(queueKeyForMode(CAPTURE_MODE_DELIVERY)).toBe(RECEIVING_QUEUE_KEY)
    expect(EXPIRY_QUEUE_KEY).not.toBe(RECEIVING_QUEUE_KEY)
  })

  it('records stock already on the shelf with no quantity and no supplier', () => {
    const entry = makeExpiryEntry(
      { barcode: ' 7290000066318 ', productName: 'במבה', expiryDate: '2026-12-31' },
      { now: new Date('2026-08-13T09:00:00Z') },
    )
    expect(entry).toEqual({
      barcode: '7290000066318',
      productName: 'במבה',
      expiryDate: '2026-12-31',
      recordedAt: '2026-08-13T09:00:00.000Z',
      source: 'manual_ui',
    })
  })

  it('still requires a barcode and an expiry date', () => {
    expect(() => makeExpiryEntry({ barcode: '', expiryDate: '2026-12-31' })).toThrow(/barcode/i)
    expect(() => makeExpiryEntry({ barcode: '111', expiryDate: '' })).toThrow(/expiry/i)
  })

  it('routes the mode to the matching validation rules', () => {
    // The same input that is a complete expiry line is an incomplete delivery.
    const expiryOnlyInput = { barcode: '111', expiryDate: '2026-12-31' }
    expect(makeEntryForMode(CAPTURE_MODE_EXPIRY, expiryOnlyInput).barcode).toBe('111')
    expect(() => makeEntryForMode(CAPTURE_MODE_DELIVERY, expiryOnlyInput)).toThrow(/quantity/i)

    // ...and a delivery line still goes through the full rules by default.
    expect(makeEntryForMode(CAPTURE_MODE_DELIVERY, validInput()).quantity).toBe(24)
  })

  it('exports the two-column shape import_expiry_csv already reads', () => {
    const queue = [
      makeExpiryEntry({ barcode: '111', productName: 'ignored', expiryDate: '2026-12-31' }),
    ]
    expect(toExpiryCsv(queue)).toBe('barcode,expiry_date\n111,2026-12-31\n')
    expect(toExpiryCsv([]).trim()).toBe(EXPIRY_CSV_HEADER)
  })

  it('names the file after the importer that reads it', () => {
    const now = new Date(2026, 7, 13, 12, 0, 0)
    expect(exportForMode(CAPTURE_MODE_EXPIRY, [], { now }).filename)
      .toBe('expiry_scans_2026-08-13.csv')
    expect(exportForMode(CAPTURE_MODE_DELIVERY, [], { now }).filename)
      .toBe('receiving_2026-08-13.csv')
  })

  it('exports each mode with its own header', () => {
    expect(exportForMode(CAPTURE_MODE_EXPIRY, []).csv.trim()).toBe(EXPIRY_CSV_HEADER)
    expect(exportForMode(CAPTURE_MODE_DELIVERY, []).csv.trim()).toBe(RECEIVING_CSV_HEADER)
  })

  // Lines captured by the pre-T7 expiry form are still sitting under this key.
  it('drains a queue left behind by the old expiry form', () => {
    const legacy = [{ barcode: '111', expiryDate: '2026-12-31', addedAt: '2026-01-01T00:00:00Z' }]
    const storage = fakeStorage({ [EXPIRY_QUEUE_KEY]: JSON.stringify(legacy) })
    const loaded = loadQueue(storage, EXPIRY_QUEUE_KEY)
    expect(loaded).toEqual(legacy)
    expect(toExpiryCsv(loaded)).toBe('barcode,expiry_date\n111,2026-12-31\n')
  })

  it('round-trips an expiry queue under its own key without touching the delivery queue', () => {
    const storage = fakeStorage()
    saveQueue([makeExpiryEntry({ barcode: '111', expiryDate: '2026-12-31' })], storage,
      EXPIRY_QUEUE_KEY)
    expect(loadQueue(storage, EXPIRY_QUEUE_KEY)).toHaveLength(1)
    expect(loadQueue(storage, RECEIVING_QUEUE_KEY)).toEqual([])
  })
})
