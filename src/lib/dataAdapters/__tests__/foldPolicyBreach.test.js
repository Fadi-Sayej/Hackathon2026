import { describe, expect, it } from 'vitest'
import { foldPolicyBreach } from '../foldPolicyBreach'

// ADR-043: the engine publishes F3's breaches as their own capability, `policy_breach`, so they
// can wait for the owner's price rule (D-39). The owner's screens were approved with them inside
// `competitor_position`, so the browser folds them back, and every screen is what it was.

const entry = (barcode, characterisation, attention, premium, capability = 'competitor_position') => ({
  id: `id-${barcode}`, signal_family: characterisation === 'purchase_cost' ? 'competitor.purchase_cost' : 'competitor.policy_breach',
  capability, barcode, product_name: barcode, department: 'd',
  action: characterisation === 'purchase_cost' ? 'check_purchase_cost' : 'review_policy', characterisation,
  evidence: { premium_pct: premium, policy_pct: 60 }, value: null,
  ordering_key: { name: 'premium_pct', value: premium }, actionable: true, not_actionable_reason: null, attention,
})

// The engine's order: same-day attention first, then the highest premium, then the barcode.
const OLD_ENTRIES = [
  entry('101', 'policy_breach_attention', 'today', 150),
  entry('102', 'policy_breach_attention', 'today', 120),
  entry('201', 'purchase_cost', 'review', 95),
  entry('103', 'policy_breach_review', 'review', 80),
  entry('202', 'purchase_cost', 'review', 80),
  entry('104', 'policy_breach_review', 'review', 61),
]
const BEFORE = {
  id: 'competitor_position', spec: 'SPEC-003', status: 'available', unavailable_reason: null,
  requires: ['products', 'observations', 'matches'],
  counts: { catalogue: 10, comparable_population: 9, matched: 8, structurally_uncomparable: 1, no_comparison: 1,
            evaluated: 7, breaches: 4, attention: 2, review: 2, purchase_cost_findings: 2, no_cost_skipped: 0,
            stale_skipped: 0 },
  thresholds: { policy_pct: 60, attention_pct: 100, cost_floor_pct: 10, format_allowance_pct: 6.3,
                format_allowance_basis_count: 12, freshness_days: 14, comparability_floor: 0.3 },
  entries: OLD_ENTRIES, notes: [], window: null, position: [{ store_id: 's' }], comparison: [{ barcode: '101' }],
}

function split(before) {
  const breach = (e) => e.signal_family === 'competitor.policy_breach'
  const { breaches, attention, review, ...counts } = before.counts
  const { policy_pct, attention_pct, ...thresholds } = before.thresholds
  return {
    competitor_position: { ...before, counts, thresholds, entries: before.entries.filter((e) => !breach(e)) },
    policy_breach: {
      id: 'policy_breach', spec: 'SPEC-003', status: 'available', unavailable_reason: null,
      requires: ['products', 'observations', 'matches', 'price_rule'],
      counts: { breaches, attention, review }, thresholds: { policy_pct, attention_pct },
      entries: before.entries.filter(breach).map((e) => ({ ...e, capability: 'policy_breach' })),
      notes: [], window: null, rule: { max_premium_pct: 60 },
    },
  }
}

const artefact = (capabilities) => ({ schema_version: 2, capabilities })

describe('foldPolicyBreach', () => {
  it('gives back competitor_position exactly as it was published before the split, key order included', () => {
    const { competitor_position, policy_breach } = split(BEFORE)
    const folded = foldPolicyBreach(artefact({ hygiene: { status: 'available' }, competitor_position,
                                              policy_breach, assortment_gap: { status: 'available' } }))
    expect(JSON.stringify(folded.capabilities.competitor_position)).toBe(JSON.stringify(BEFORE))
    expect(Object.keys(folded.capabilities)).toEqual(['hygiene', 'competitor_position', 'assortment_gap'])
  })

  it('without the owner\'s rule, keeps the comparison and the purchase-cost check and says what F3 waits for', () => {
    const { competitor_position } = split(BEFORE)
    const waiting = { id: 'policy_breach', status: 'unavailable', unavailable_reason: 'no_price_rule' }
    const folded = foldPolicyBreach(artefact({ competitor_position, policy_breach: waiting }))
    const cp = folded.capabilities.competitor_position
    expect(cp.status).toBe('available')
    expect(cp.waiting_for).toBe('no_price_rule')
    expect(cp.entries.map((e) => e.characterisation)).toEqual(['purchase_cost', 'purchase_cost'])
    expect('policy_breach' in folded.capabilities).toBe(false)
  })

  it('leaves an artefact from before the split as it is', () => {
    const before = artefact({ competitor_position: BEFORE })
    expect(foldPolicyBreach(before)).toBe(before)
  })

  it('leaves an unavailable competitor_position unavailable, with its own reason', () => {
    const cp = { id: 'competitor_position', status: 'unavailable', unavailable_reason: 'no_competitor_data' }
    const pb = { id: 'policy_breach', status: 'unavailable', unavailable_reason: 'no_competitor_data' }
    const folded = foldPolicyBreach(artefact({ competitor_position: cp, policy_breach: pb }))
    expect(folded.capabilities).toEqual({ competitor_position: cp })
  })
})
