/**
 * foldPolicyBreach — F3's breaches back inside `competitor_position`, as the owner's screens show them.
 *
 * ADR-043: the engine publishes the breaches as their own capability, `policy_breach`, so that they
 * can wait for the owner's price rule (D-39) while the comparison and the purchase-cost check go
 * on. That is a fact about availability, not about what the owner sees: every screen was approved
 * with the breaches among F3's findings, on F3's page and in F3's turn on Today. So the browser
 * folds them back here, once, where the artefact is loaded, and no page or composer knows of the
 * split. For a store with the rule, the folded `competitor_position` is exactly what the engine
 * published before the split (the test holds it byte for byte, key order included).
 *
 * Without the rule, `competitor_position` keeps its comparison and purchase-cost findings and
 * carries `waiting_for: 'no_price_rule'`, which F3's page states where the breaches would be.
 */
const CP = 'competitor_position'
const PB = 'policy_breach'

// The engine's order (competitor_position.py): same-day attention first, then the highest
// premium, then the barcode as Python compares strings.
function byEngineOrder(a, b) {
  const today = (e) => (e.attention === 'today' ? 0 : 1)
  if (today(a) !== today(b)) return today(a) - today(b)
  const premium = (e) => e.ordering_key?.value ?? 0
  if (premium(a) !== premium(b)) return premium(b) - premium(a)
  const x = String(a.barcode ?? '')
  const y = String(b.barcode ?? '')
  return x < y ? -1 : x > y ? 1 : 0
}

export function foldPolicyBreach(artefact) {
  const capabilities = artefact?.capabilities
  const breaches = capabilities?.[PB]
  if (!capabilities || !breaches) return artefact
  const rest = Object.fromEntries(Object.entries(capabilities).filter(([id]) => id !== PB))
  const position = capabilities[CP]
  if (!position || position.status !== 'available') return { ...artefact, capabilities: rest }
  if (breaches.status !== 'available') {
    return { ...artefact, capabilities: { ...rest, [CP]: { ...position, waiting_for: breaches.unavailable_reason ?? null } } }
  }
  // The breach counts sat right after `evaluated`, of which they are a part.
  const counts = {}
  for (const [name, value] of Object.entries(position.counts || {})) {
    counts[name] = value
    if (name === 'evaluated') Object.assign(counts, breaches.counts)
  }
  if (!('evaluated' in counts)) Object.assign(counts, breaches.counts)
  const entries = [...(position.entries || []), ...(breaches.entries || []).map((e) => ({ ...e, capability: CP }))]
    .sort(byEngineOrder)
  return {
    ...artefact,
    capabilities: {
      ...rest,
      [CP]: { ...position, counts, thresholds: { ...(breaches.thresholds || {}), ...(position.thresholds || {}) }, entries },
    },
  }
}
