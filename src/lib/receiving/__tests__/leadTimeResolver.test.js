import { describe, expect, it } from 'vitest'

import {
  DEFAULT_LEAD_TIME_DAYS,
  DEFAULT_SUPPLIER,
  emptyLedger,
  normalizeLedger,
  resolveSupplierAndLeadTime,
} from '../leadTimeResolver.js'

const LEDGER = normalizeLedger({
  defaultLeadTimeDays: 3,
  leadTimes: {
    Tempo: { median_days: 7, n_observations: 4, confidence: 'medium' },
    Osem: { median_days: null, n_observations: 2, confidence: 'low' },
    Strauss: { median_days: 2.5, n_observations: 8, confidence: 'high' },
  },
  supplierByBarcode: { 111: 'Tempo', 222: 'Osem', 333: 'Strauss' },
})

describe('leadTimeResolver', () => {
  it('falls back to the defaults for a barcode the ledger has never seen', () => {
    expect(resolveSupplierAndLeadTime('999', LEDGER)).toEqual({
      supplier: DEFAULT_SUPPLIER,
      leadTimeDays: DEFAULT_LEAD_TIME_DAYS,
      leadTimeConfidence: 'low',
      leadTimeSource: 'default',
    })
  })

  it('uses the measured median when the supplier has enough deliveries', () => {
    expect(resolveSupplierAndLeadTime('111', LEDGER)).toEqual({
      supplier: 'Tempo',
      leadTimeDays: 7,
      leadTimeConfidence: 'medium',
      leadTimeSource: 'measured',
    })
  })

  it('keeps the real supplier but the default lead time below three deliveries', () => {
    expect(resolveSupplierAndLeadTime('222', LEDGER)).toEqual({
      supplier: 'Osem',
      leadTimeDays: DEFAULT_LEAD_TIME_DAYS,
      leadTimeConfidence: 'low',
      leadTimeSource: 'default',
    })
  })

  it('rounds a fractional median and never returns less than one day', () => {
    expect(resolveSupplierAndLeadTime('333', LEDGER).leadTimeDays).toBe(3)

    const sameDay = normalizeLedger({
      leadTimes: { Fast: { median_days: 0.2, n_observations: 5, confidence: 'medium' } },
      supplierByBarcode: { 444: 'Fast' },
    })
    expect(resolveSupplierAndLeadTime('444', sameDay).leadTimeDays).toBe(1)
  })

  it('strips a ym- prefix and leading zeroes so product ids resolve', () => {
    expect(resolveSupplierAndLeadTime('ym-111', LEDGER).supplier).toBe('Tempo')
    expect(resolveSupplierAndLeadTime('000111', LEDGER).supplier).toBe('Tempo')
  })

  it('treats a missing, null or malformed ledger as empty rather than throwing', () => {
    for (const raw of [null, undefined, 'nonsense', 42, { leadTimes: 'bad' }]) {
      const ledger = normalizeLedger(raw)
      expect(ledger.leadTimes).toEqual({})
      expect(resolveSupplierAndLeadTime('111', ledger).leadTimeSource).toBe('default')
    }
  })

  it('emptyLedger resolves everything to the defaults', () => {
    const resolved = resolveSupplierAndLeadTime('111', emptyLedger())
    expect(resolved.supplier).toBe(DEFAULT_SUPPLIER)
    expect(resolved.leadTimeDays).toBe(DEFAULT_LEAD_TIME_DAYS)
  })

  it('handles a barcode whose supplier has no lead-time entry at all', () => {
    const ledger = normalizeLedger({ leadTimes: {}, supplierByBarcode: { 555: 'Ghost' } })
    expect(resolveSupplierAndLeadTime('555', ledger)).toEqual({
      supplier: 'Ghost',
      leadTimeDays: DEFAULT_LEAD_TIME_DAYS,
      leadTimeConfidence: 'low',
      leadTimeSource: 'default',
    })
  })
})
