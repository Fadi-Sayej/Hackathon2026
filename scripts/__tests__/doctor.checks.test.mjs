/**
 * The first test `npm run doctor` has ever had.
 *
 * WHY IT EXISTS
 *   The doctor ran unguarded for months and one of its checks was dead the whole
 *   time: `currentStock < 0` could never be true because the adapter clamped
 *   negatives to zero before the doctor saw them, so it reported a clean bill
 *   while 631 negative rows sat in the source. A check nothing exercises is a
 *   check nobody can trust.
 *
 *   So every check here is driven in BOTH directions — once over an artefact that
 *   should trip it, once over an artefact that should not. CLAUDE.md rule 12: a
 *   check that has never failed is not proven wired, it is only unproven.
 *
 *   The fixtures are hand-built rather than sliced out of the real artefact on
 *   purpose. A fixture cut from today's data encodes today's bugs as the expected
 *   answer.
 */
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

import { ARTEFACT_PATH, ERROR, NOTE, WARN, runChecks } from '../doctor.checks.mjs'

/** The smallest artefact the doctor accepts, so each test varies one thing. */
const artefact = (capabilities, extra = {}) => ({
  schema_version: 2,
  generated_at: '2026-09-13T10:55:29Z',
  population: 'whole',
  value_kinds_present: [],
  run: { status: 'ok', steps: [{ step: 'publish', status: 'ok', ms: 1, error: null }] },
  vintages: {},
  thresholds: {},
  figures: {},
  capabilities,
  ...extra,
})

const entry = (over = {}) => ({
  id: 'a1',
  signal_family: 'hygiene.negative_stock',
  capability: 'hygiene',
  barcode: '729',
  product_name: 'שמן זית',
  department: 'מוצרי בית',
  action: 'fix_record',
  characterisation: 'hygiene',
  evidence: { reason: 'negative_stock', recorded_stock: -3 },
  value: null,
  actionable: true,
  ...over,
})

const capability = (entries, over = {}) => ({
  status: 'available',
  counts: {},
  entries,
  ...over,
})

const find = (findings, check) => findings.filter((f) => f.check === check)
const levels = (findings, check) => find(findings, check).map((f) => f.level)

describe('entry identity (ADR-009)', () => {
  it('reports ERROR when two entries share an id', () => {
    const found = runChecks(
      artefact({ hygiene: capability([entry({ id: 'dup' }), entry({ id: 'dup' })]) }),
    )
    expect(levels(found, 'entry-identity')).toContain(ERROR)
  })

  it('does NOT report ERROR when every id is distinct', () => {
    const found = runChecks(
      artefact({ hygiene: capability([entry({ id: 'a' }), entry({ id: 'b' })]) }),
    )
    expect(levels(found, 'entry-identity')).not.toContain(ERROR)
  })
})

describe('value discipline (rule 8)', () => {
  // Only the agreement between `value_kinds_present` and the entries is checked.
  // Which kinds are legal, and that an amount is a number, are pinned by
  // schemas/dashboard.schema.json and validated in CI — a check for those could
  // only fire on a file publish.py refused to write.
  it('reports WARN when an entry carries a kind the artefact does not declare', () => {
    const found = runChecks(
      artefact(
        { hygiene: capability([entry({ value: { amount: 5, kind: 'one_off', certainty: 'confirmed' } })]) },
        { value_kinds_present: ['per_sale'] },
      ),
    )
    expect(levels(found, 'value-discipline')).toContain(WARN)
  })

  it('reports WARN when a declared kind appears on no entry, because the browser would offer a total nothing backs', () => {
    const found = runChecks(
      artefact({ hygiene: capability([entry()]) }, { value_kinds_present: ['per_sale'] }),
    )
    expect(levels(found, 'value-discipline')).toContain(WARN)
  })

  it('accepts an artefact whose declared kinds match its entries exactly', () => {
    const found = runChecks(
      artefact(
        { hygiene: capability([entry({ value: { amount: 5, kind: 'per_sale', certainty: 'confirmed' } })]) },
        { value_kinds_present: ['per_sale'] },
      ),
    )
    expect(levels(found, 'value-discipline')).not.toContain(WARN)
  })
})

describe('negative-stock flag coherence — the check that used to be dead', () => {
  it('reports WARN when an entry claims negative stock but its evidence is not negative', () => {
    const found = runChecks(
      artefact({
        hygiene: capability([entry({ evidence: { reason: 'negative_stock', recorded_stock: 4 } })], {
          counts: { negative_stock: 1 },
        }),
      }),
    )
    expect(levels(found, 'negative-stock-coherence')).toContain(WARN)
  })

  it('reports WARN when the published count disagrees with the entries it summarises', () => {
    const found = runChecks(
      artefact({ hygiene: capability([entry()], { counts: { negative_stock: 99 } }) }),
    )
    expect(levels(found, 'negative-stock-coherence')).toContain(WARN)
  })

  it('stays quiet when the count and the evidence agree', () => {
    const found = runChecks(
      artefact({ hygiene: capability([entry()], { counts: { negative_stock: 1 } }) }),
    )
    expect(levels(found, 'negative-stock-coherence')).not.toContain(WARN)
  })
})

describe('flagged-row pricing coherence', () => {
  // `characterisation`, not `signal_family`, is what separates these: both ship as
  // signal_family `margin.below_cost`, and a thin_margin row legitimately has cost
  // BELOW shelf price. Keying the check on the family reported all 37 thin-margin
  // rows in the real artefact as incoherent.
  const below = (over) => entry({
    signal_family: 'margin.below_cost',
    characterisation: 'below_cost',
    capability: 'margin_below_cost',
    evidence: { shelf_price: 10, cost_price: 20, margin_pct: -50, cost_source: 'pos' },
    value: { amount: 10, kind: 'per_sale', certainty: 'confirmed' },
    ...over,
  })

  const thin = (over) => below({
    characterisation: 'thin_margin',
    evidence: { shelf_price: 7, cost_price: 6.32, margin_pct: 9.71, cost_source: 'pos' },
    ...over,
  })

  it('reports WARN when a below-cost row is not actually below cost', () => {
    const found = runChecks(
      artefact(
        { margin_below_cost: capability([below({ evidence: { shelf_price: 30, cost_price: 20 } })]) },
        { value_kinds_present: ['per_sale'] },
      ),
    )
    expect(levels(found, 'pricing-coherence')).toContain(WARN)
  })

  it('stays quiet when cost genuinely exceeds shelf price', () => {
    const found = runChecks(
      artefact({ margin_below_cost: capability([below()]) }, { value_kinds_present: ['per_sale'] }),
    )
    expect(levels(found, 'pricing-coherence')).not.toContain(WARN)
  })

  it('does NOT flag a thin-margin row for having cost below shelf price — that is what thin margin means', () => {
    const found = runChecks(
      artefact({ margin_below_cost: capability([thin()]) }, { value_kinds_present: ['per_sale'] }),
    )
    expect(levels(found, 'pricing-coherence')).not.toContain(WARN)
  })

  it('reports WARN when a thin-margin row is actually below cost', () => {
    const found = runChecks(
      artefact(
        { margin_below_cost: capability([thin({ evidence: { shelf_price: 5, cost_price: 9 } })]) },
        { value_kinds_present: ['per_sale'] },
      ),
    )
    expect(levels(found, 'pricing-coherence')).toContain(WARN)
  })
})

describe('run health (rule 10)', () => {
  // The schema's step enum is ok | error | skipped | degraded. An earlier version
  // of this fixture used 'failed' — a value the engine never emits and the schema
  // does not allow — so the check passed its test while being wrong about every
  // real artefact. ADR-017 makes `degraded` a designed outcome, not a fault.
  const withSteps = (steps) =>
    artefact({ hygiene: capability([entry()]) }, { run: { status: 'partial', steps } })

  it('reports ERROR when a step errored but the run still published', () => {
    const found = withSteps([{ step: 'competitor', status: 'error', ms: 2, error: 'no snapshot' }])
    expect(levels(runChecks(found), 'run-health')).toContain(ERROR)
  })

  it('does NOT report ERROR for a degraded step — ADR-017 calls that a run on older evidence', () => {
    const found = withSteps([
      { step: 'sales_import', status: 'degraded', ms: 2, error: 'no_rows_imported' },
    ])
    expect(levels(runChecks(found), 'run-health')).not.toContain(ERROR)
  })

  it('does NOT report ERROR for a skipped step, which is what --skip-market produces', () => {
    const found = withSteps([{ step: 'competitor', status: 'skipped', ms: 0, error: null }])
    expect(levels(runChecks(found), 'run-health')).not.toContain(ERROR)
  })

  it('stays quiet when every step succeeded', () => {
    const found = runChecks(artefact({ hygiene: capability([entry()]) }))
    expect(levels(found, 'run-health')).not.toContain(ERROR)
  })
})

describe('the artefact itself must be readable', () => {
  it('reports ERROR on a schema version it does not understand', () => {
    const found = runChecks(artefact({ hygiene: capability([entry()]) }, { schema_version: 99 }))
    expect(levels(found, 'artefact')).toContain(ERROR)
  })

  it('reports ERROR when there is no artefact at all', () => {
    expect(levels(runChecks(null), 'artefact')).toContain(ERROR)
  })
})

describe('no finding states a bare number (the denominator rule)', () => {
  it('every message carries a denominator or names no quantity at all', () => {
    const found = runChecks(
      artefact(
        { hygiene: capability([entry({ id: 'dup' }), entry({ id: 'dup' })], { counts: { negative_stock: 9 } }) },
        { value_kinds_present: ['per_sale'] },
      ),
    )
    // A message may say "3 of 3,534 ..." but never "3 products have no price".
    // Check 3 died because it claimed catalogue scope while holding artefact scope.
    for (const finding of found) {
      const startsWithBareCount = /^\d[\d,]*\s/.test(finding.message)
      if (startsWithBareCount) {
        expect(finding.message).toMatch(/\bof\b\s[\d,]+/)
      }
    }
  })
})

describe('against the artefact that is actually committed', () => {
  const committed = JSON.parse(readFileSync(ARTEFACT_PATH, 'utf8'))

  it('runs to completion and states its scope', () => {
    const found = runChecks(committed)
    expect(found.length).toBeGreaterThan(0)
    expect(levels(found, 'scope')).toContain(NOTE)
  })

  it('never throws on the real shape, whatever it finds', () => {
    expect(() => runChecks(committed)).not.toThrow()
  })

  // This is the check that keeps #75 unblocked. Prose may still discuss the
  // planogram — it explains what retired and why — so only the import graph is
  // asserted, which is the thing Phase 4 Task 4.1 actually needs gone.
  it('imports nothing on the Phase 4 REMOVE list', () => {
    const importsOf = (file) =>
      readFileSync(new URL(file, import.meta.url), 'utf8')
        .split('\n')
        .filter((line) => /^\s*(import|export)\s.*\sfrom\s|^\s*import\s+['"]/.test(line))

    const doomed = /loadDemoStoreData|planogram|demoProducts|posConnectors|src\/data\/|analytics\//
    for (const file of ['../doctor.mjs', '../doctor.checks.mjs']) {
      for (const line of importsOf(file)) {
        expect(line).not.toMatch(doomed)
      }
    }
  })

  it('imports nothing from src/ at all, so no app refactor can break it', () => {
    const source = readFileSync(new URL('../doctor.mjs', import.meta.url), 'utf8')
    const checks = readFileSync(new URL('../doctor.checks.mjs', import.meta.url), 'utf8')
    expect(source).not.toMatch(/from\s+['"][^'"]*\/src\//)
    expect(checks).not.toMatch(/from\s+['"][^'"]*\/src\//)
  })
})
