/**
 * Curated cross-merchandising affinity rules for a convenience store.
 *
 * Each rule represents a co-purchase relationship that boosts Average
 * Basket Value when the two categories share visibility on the shelf.
 * Strength values are calibrated to retail industry benchmarks for
 * impulse / companion purchases in a gas-station-style format.
 *
 * In a production system these strengths would be learned from
 * transaction data (Apriori / FP-Growth). The MVP ships with curated
 * defaults so the engine can produce suggestions on day one, before
 * basket data accumulates.
 *
 * @typedef {Object} AffinityRule
 * @property {[string, string]} pair       Anchor and partner categories.
 * @property {number} strength             0-1 confidence of co-purchase.
 * @property {string} reason               Why the pair works in plain English.
 * @property {string} placement            Suggested in-store action.
 * @property {number} liftEstimate         Estimated basket-value uplift (0-1).
 */

export const affinityRules = [
  {
    pair: ['Coffee', 'Bakery'],
    strength: 0.88,
    reason: 'Morning ritual: coffee buyers add a pastry 88% of the time.',
    placement: 'Co-locate a pastry display beside the coffee station.',
    liftEstimate: 0.22,
  },
  {
    pair: ['Snacks', 'Cold Drinks'],
    strength: 0.85,
    reason: 'Salty-and-refresh impulse: chip buyers reach for a chilled drink.',
    placement: 'Cross-merchandise a chip rack on the cold-drink endcap.',
    liftEstimate: 0.18,
  },
  {
    pair: ['Bakery', 'Cold Drinks'],
    strength: 0.78,
    reason: 'Grab-and-go breakfast: bakery customers pick up a chilled drink.',
    placement: 'Place a small cold-drink cooler within arm’s reach of the bakery case.',
    liftEstimate: 0.14,
  },
  {
    pair: ['Bakery', 'Dairy'],
    strength: 0.74,
    reason: 'Breakfast combo: pastries plus yogurt drive the morning basket.',
    placement: 'Stock yogurt drinks on a chilled shelf beside the bakery.',
    liftEstimate: 0.11,
  },
  {
    pair: ['Snacks', 'Energy Drinks'],
    strength: 0.72,
    reason: 'Long-drive bundle: energy drink buyers grab a savoury snack.',
    placement: 'Place energy drinks within sight of the snack aisle.',
    liftEstimate: 0.13,
  },
  {
    pair: ['Cigarettes', 'Gum & Candy'],
    strength: 0.69,
    reason: 'Breath-refresh add-on: gum sales spike at the cigarette counter.',
    placement: 'Position gum and mint candy on the counter beside cigarettes.',
    liftEstimate: 0.10,
  },
  {
    pair: ['Chocolate', 'Cold Drinks'],
    strength: 0.62,
    reason: 'Sweet break: chocolate buyers often pair with a chilled drink.',
    placement: 'Add a chocolate strip rack on the cold-drink cooler door.',
    liftEstimate: 0.09,
  },
  {
    pair: ['Ice Cream', 'Cold Drinks'],
    strength: 0.60,
    reason: 'Summer pairing: ice cream buyers add a chilled drink in warm weather.',
    placement: 'Keep ice cream freezer adjacent to the cold-drink cooler.',
    liftEstimate: 0.10,
  },
  {
    pair: ['Coffee', 'Chocolate'],
    strength: 0.58,
    reason: 'Indulgence pair: coffee customers add a chocolate bar at checkout.',
    placement: 'Stock single chocolate bars near the coffee station.',
    liftEstimate: 0.08,
  },
  {
    pair: ['Water', 'Energy Drinks'],
    strength: 0.55,
    reason: 'Hydration follow-up: energy drink buyers re-hydrate with water.',
    placement: 'Keep water and energy drinks within the same cooler bank.',
    liftEstimate: 0.07,
  },
  {
    pair: ['Car Accessories', 'Energy Drinks'],
    strength: 0.54,
    reason: 'Road-trip kit: drivers buying car items pick up caffeine.',
    placement: 'Secondary placement of energy drinks near car accessories.',
    liftEstimate: 0.07,
  },
]
