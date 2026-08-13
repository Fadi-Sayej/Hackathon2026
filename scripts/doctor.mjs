#!/usr/bin/env node
/**
 * `npm run doctor` — data-integrity checks that no test can express.
 *
 * WHY THIS EXISTS SEPARATELY FROM THE TEST SUITE
 *   Unit tests assert on fixtures the author chose. This runs the same
 *   invariants against the *actual* 7,451-row catalogue, where the interesting
 *   failures live. Every problem it reports was found the hard way:
 *
 *     - 83 rows silently dropped by a Map keyed on a non-unique product id
 *     - 625 rows with negative stock from a till artefact
 *     - services (car washes, subscriptions) priced as shelf products
 *     - margins twenty times their department median — miscategorised items
 *
 *   Each check states what it found, why it matters, and what to do. Exits
 *   non-zero on an ERROR so it can gate a release; WARN and NOTE never fail the
 *   run, because a warning that blocks a build gets silenced within a week.
 */

import { loadDemoStoreData } from '../src/lib/dataAdapters/loadDemoStoreData.js'
import { isShelvable, packageGeometry } from '../src/lib/planogram/packageShapes.js'

const ERROR = 'ERROR'
const WARN = 'WARN'
const NOTE = 'NOTE'

const findings = []
const report = (level, check, message, hint) =>
  findings.push({ level, check, message, hint })

const { products, validationIssues } = loadDemoStoreData()

// ── 1. Product ids must be unique ────────────────────────────────────
// Everything downstream indexes by id: `productIndex` in App.jsx, React list
// keys, approved plans, shelf photos. A duplicate means a Map keeps the last
// row and drops the rest — including the one supplying a purchase order's cost.
{
  const ids = products.map((product) => product.id)
  const unique = new Set(ids)
  if (unique.size !== ids.length) {
    report(
      ERROR,
      'unique-ids',
      `${ids.length - unique.size} duplicate product ids survived normalisation`,
      'normalizeProducts() should have disambiguated these — check productAdapter.js',
    )
  } else {
    report(NOTE, 'unique-ids', `${ids.length} products, all ids unique`)
  }

  const disambiguated = validationIssues.filter((issue) => issue.field === 'id')
  if (disambiguated.length) {
    report(
      WARN,
      'id-collisions',
      `${disambiguated.length} ids collided in the source export and were disambiguated`,
      'The generator reuses barcode-or-name across departments; rows were kept, not merged',
    )
  }
}

// ── 2. Prices and costs must be sane ─────────────────────────────────
{
  const noPrice = products.filter((product) => !(product.price > 0))
  const belowCost = products.filter(
    (product) => product.price > 0 && product.cost > 0 && product.price < product.cost,
  )
  const noCost = products.filter((product) => !(product.cost > 0))

  if (noPrice.length) {
    report(WARN, 'pricing', `${noPrice.length} products have no selling price`, 'They cannot be ranked by margin and are excluded from planning')
  }
  if (belowCost.length) {
    report(
      WARN,
      'pricing',
      `${belowCost.length} products sell below cost`,
      'Either a real loss leader or a wrong cost price — the Today screen ranks these',
    )
  }
  if (noCost.length) {
    report(NOTE, 'pricing', `${noCost.length} products have no cost price, so margin is unknown`)
  }
}

// ── 3. Stock must not be negative ────────────────────────────────────
// A till artefact, not a real quantity. Clamped in the engines, but the count
// is a data-quality signal worth watching.
{
  const negative = products.filter((product) => product.currentStock < 0)
  if (negative.length) {
    report(
      WARN,
      'stock',
      `${negative.length} products report negative stock`,
      'Clamped to zero downstream; the underlying count needs a physical check',
    )
  }
}

// ── 4. Velocity: say plainly how much history backs the numbers ──────
{
  // Counted by confidence band, not by "sales > 0". Those are different facts:
  // a product that sold zero units is not the same as one we have no history
  // for, and conflating them is what made 100% of the catalogue read as "slow
  // moving" once already.
  const bands = { none: 0, low: 0, medium: 0, high: 0, missing: 0 }
  for (const product of products) {
    const level = product.velocityConfidence
    if (level in bands) bands[level] += 1
    else bands.missing += 1
  }
  const usable = bands.low + bands.medium + bands.high

  if (!usable) {
    report(
      WARN,
      'velocity',
      'No product carries usable sales history',
      'Every velocity-derived figure is an estimate. Seven monthly sales reports sit in data/internal/raw_pos/yomyom/sales/',
    )
  } else {
    report(
      NOTE,
      'velocity',
      `${usable} of ${products.length} products have usable velocity (high ${bands.high}, medium ${bands.medium}, low ${bands.low}); ${bands.none} have none`,
      usable < products.length / 2
        ? 'The majority still fall back to a category assumption — the shelf plan states this per fixture'
        : undefined,
    )
  }
}

// ── 5. Planogram geometry coverage ───────────────────────────────────
// Facing counts are only as good as the package widths behind them.
{
  const shelvable = products.filter(isShelvable)
  const estimated = shelvable.filter((product) => packageGeometry(product).estimatedGeometry)
  const share = shelvable.length ? Math.round((estimated.length / shelvable.length) * 100) : 0

  report(
    share > 25 ? WARN : NOTE,
    'geometry',
    `${estimated.length} of ${shelvable.length} shelvable products (${share}%) fall back to the default package archetype`,
    'Their facing counts are a guess. Every archetype is unmeasured — see docs/PLANOGRAM_ROADMAP.md §4.1',
  )

  const nonShelvable = products.length - shelvable.length
  if (nonShelvable) {
    report(
      NOTE,
      'geometry',
      `${nonShelvable} rows are services or till-only entries and are excluded from shelf planning`,
    )
  }
}

// ── 6. Categories ────────────────────────────────────────────────────
{
  const uncategorised = products.filter(
    (product) => !product.category || product.category === 'Uncategorized',
  )
  if (uncategorised.length) {
    report(WARN, 'categories', `${uncategorised.length} products have no department`, 'They cannot be planned onto a fixture, which is always per-department')
  }
}

// ── Output ───────────────────────────────────────────────────────────
const ICON = { [ERROR]: '✗', [WARN]: '!', [NOTE]: '·' }
const order = { [ERROR]: 0, [WARN]: 1, [NOTE]: 2 }

console.log('\nSmartShelf doctor — data integrity\n')
for (const finding of findings.sort((a, b) => order[a.level] - order[b.level])) {
  console.log(`${ICON[finding.level]} [${finding.check}] ${finding.message}`)
  if (finding.hint) console.log(`    → ${finding.hint}`)
}

const errors = findings.filter((finding) => finding.level === ERROR).length
const warnings = findings.filter((finding) => finding.level === WARN).length
console.log(`\n${errors} error(s), ${warnings} warning(s), ${findings.length} checks reported.\n`)

process.exit(errors ? 1 : 0)
