import { describe, expect, it } from 'vitest'

import { validatePlan, RULE_SEVERITY } from '../planValidation.js'

/**
 * Gate 2 of the roadmap: a generator that always returns a physically valid
 * plan, and can prove it. These tests define what "valid" means.
 */

const shelf = (overrides = {}) => ({
  code: 'الرف ١',
  shelfLevel: 'MIDDLE',
  levelLabel: 'مستوى اليد',
  runCm: 100,
  usedCm: 0,
  clearanceCm: 45,
  fillRatio: 0,
  items: [],
  ...overrides,
})

const item = (overrides = {}) => ({
  productId: 'p1',
  productName: 'منتج',
  facings: 1,
  widthCm: 10,
  heightCm: 20,
  litres: 0.5,
  onShelf: 10,
  currentStock: 50,
  status: 'ok',
  ...overrides,
})

describe('shelf width', () => {
  it('passes a plan whose facings fit the run', () => {
    const plan = { shelves: [shelf({ items: [item({ facings: 5, widthCm: 10 })], usedCm: 50 })] }

    expect(validatePlan(plan).valid).toBe(true)
  })

  it('reports an overfilled shelf as a hard violation', () => {
    // 12 facings x 10cm = 120cm on a 100cm run.
    const plan = { shelves: [shelf({ items: [item({ facings: 12, widthCm: 10 })], usedCm: 120 })] }

    const report = validatePlan(plan)

    expect(report.valid).toBe(false)
    expect(report.violations).toHaveLength(1)
    expect(report.violations[0].rule).toBe('SHELF_WIDTH')
    expect(report.violations[0].severity).toBe(RULE_SEVERITY.hard)
  })

  it('names the shelf and the overflow so it can be fixed', () => {
    const plan = { shelves: [shelf({ items: [item({ facings: 12, widthCm: 10 })], usedCm: 120 })] }

    const [violation] = validatePlan(plan).violations

    expect(violation.shelfCode).toBe('الرف ١')
    expect(violation.overflowCm).toBe(20)
  })
})

describe('vertical clearance', () => {
  it('reports a package taller than its shelf', () => {
    const plan = {
      shelves: [shelf({ clearanceCm: 20, items: [item({ heightCm: 32 })], usedCm: 10 })],
    }

    const report = validatePlan(plan)

    expect(report.violations.map((entry) => entry.rule)).toContain('SHELF_CLEARANCE')
  })
})

describe('heavy goods', () => {
  it('reports a heavy package placed above the bottom shelf', () => {
    const plan = {
      shelves: [shelf({ shelfLevel: 'EYE_LEVEL', items: [item({ litres: 4 })], usedCm: 10 })],
    }

    const report = validatePlan(plan)

    expect(report.violations.map((entry) => entry.rule)).toContain('HEAVY_GOODS_LOW')
  })

  it('accepts the same package on the bottom shelf', () => {
    const plan = {
      shelves: [shelf({ shelfLevel: 'BOTTOM', items: [item({ litres: 4 })], usedCm: 10 })],
    }

    expect(validatePlan(plan).valid).toBe(true)
  })
})

describe('soft findings', () => {
  it('flags a badly underfilled shelf without failing the plan', () => {
    const plan = { shelves: [shelf({ items: [item()], usedCm: 10 })] }

    const report = validatePlan(plan)

    expect(report.valid).toBe(true)
    expect(report.warnings.map((entry) => entry.rule)).toContain('EMPTY_SPACE')
  })
})

describe('report shape', () => {
  it('counts what it checked, so an empty pass is distinguishable from no check', () => {
    const plan = { shelves: [shelf({ items: [item(), item({ productId: 'p2' })], usedCm: 20 })] }

    const report = validatePlan(plan)

    expect(report.checkedPositions).toBe(2)
    expect(report.checkedShelves).toBe(1)
  })

  it('treats a plan with no shelves as valid but unchecked', () => {
    const report = validatePlan({ shelves: [] })

    expect(report.valid).toBe(true)
    expect(report.checkedPositions).toBe(0)
  })
})
