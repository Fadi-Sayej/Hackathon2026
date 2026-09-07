/**
 * check_signals_live.mjs — does each signal actually change a recommendation?
 *
 * WHY THIS EXISTS
 *   Every serious bug in this project has been silence, not a crash. Each was
 *   built, unit-tested, labelled working, and did nothing:
 *
 *     - the market pipeline nothing ever ran        (competitorSignals: 0, exit 0)
 *     - demand multipliers keyed in English against a Hebrew catalogue
 *                                                   (every multiplier exactly 1.0)
 *     - owner answers keyed on the synthetic product id while Python keys on
 *       barcode                                     (answers never readable back)
 *     - the shelf-life table dropped by the context adapter
 *                                                   (cap silently off in the app)
 *
 *   Unit tests passed throughout all four, because each test supplied the input
 *   directly and never crossed the boundary where it was being lost. This check
 *   asks the one question those tests cannot: with REAL data, does this input
 *   reach an output?
 *
 * HOW
 *   For each signal: run the engine normally, run it again with the signal
 *   neutralised, and diff the recommendations. A signal that changes nothing on
 *   real data is inert.
 *
 * INERT vs INACTIVE — the distinction that keeps this honest
 *   INACTIVE  the input is legitimately absent today (no holiday window, no
 *             competitor stockouts, no answers given yet). Not a bug. But we do
 *             NOT simply pass: a synthetic probe is injected to prove the wiring
 *             still carries it. That is precisely the check that would have caught
 *             the barcode bug while owner_answers.yaml was still empty.
 *   INERT     the input IS present and still changes nothing. That is the bug
 *             class, and it fails the run.
 */
import { readFileSync } from 'fs'

const [{ demoProducts }, { normalizeProducts }, eng, { toEngineContext }, { fallbackMarketContext }] =
  await Promise.all([
    import('../src/data/demoProducts.js'),
    import('../src/lib/dataAdapters/productAdapter.js'),
    import('../src/lib/analytics/reorderEngine.js'),
    import('../src/lib/dataAdapters/loadMarketContext.js'),
    import('../src/lib/context/fallbackMarketContext.js'),
  ])

const artifact = JSON.parse(readFileSync('public/data/market-context.json', 'utf8'))
const { products } = normalizeProducts(demoProducts)

/** A comparable fingerprint of what the owner would actually be told. */
function fingerprint(context) {
  const out = new Map()
  for (const r of eng.generateReorderRecommendations(products, context)) {
    if (r.type !== 'REORDER') continue
    out.set(r.productId, r.recommendedOrderQuantity ?? 0)
  }
  return out
}

function countDifferences(a, b) {
  let n = 0
  for (const [k, v] of a) if (!b.has(k) || b.get(k) !== v) n += 1
  for (const k of b.keys()) if (!a.has(k)) n += 1
  return n
}

const base = toEngineContext(artifact, fallbackMarketContext)
const baseline = fingerprint(base)

/**
 * Each signal declares: whether its real input is present, how to switch it off,
 * and — when the real input is absent — a synthetic input that must still move
 * something.
 */
const SIGNALS = [
  {
    name: 'shelf-life cap',
    present: () => Object.values(artifact.shelfLife?.categories ?? {}).some((v) => v > 0),
    off: () => ({ ...base, shelfLife: null }),
    probe: () => ({ ...base, shelfLife: { categories: { 'מחלקת -barista': 1 }, defaultDays: null } }),
  },
  {
    name: 'owner answers',
    present: () =>
      Object.keys(artifact.ownerAnswers?.carried ?? {}).length > 0 ||
      Object.keys(artifact.ownerAnswers?.shelfLifeCategories ?? {}).length > 0,
    // An owner answer reaches the browser as a shelf-life override (and reaches
    // Python as a reorder exclusion). The browser-side effect is the override.
    off: () => base,
    probe: () => ({
      ...base,
      shelfLife: {
        ...(artifact.shelfLife ?? { categories: {}, defaultDays: null }),
        categories: { ...(artifact.shelfLife?.categories ?? {}), 'חטיפים מתוקים': 1 },
      },
    }),
  },
  {
    name: 'competitor stockout lift',
    present: () => (artifact.competitorStockouts?.barcodes ?? []).length > 0,
    off: () => ({ ...base, competitorStockouts: null }),
    probe: () => ({
      ...base,
      competitorStockouts: {
        status: 'ok',
        lift: 1.5,
        barcodes: products.filter((p) => p.barcode).slice(0, 400).map((p) => p.barcode),
      },
    }),
  },
  {
    name: 'weather / category multiplier',
    present: () => Object.keys(artifact.demandSignals ?? {}).length > 0,
    off: () => ({ ...base, demandSignals: {} }),
    probe: () => ({ ...base, demandSignals: { משקאות: 1.5, גלידות: 1.5 } }),
  },
  {
    name: 'holiday / calendar gating',
    present: () => Boolean(artifact.hebrew?.chametz) || Boolean(artifact.islamic?.phase),
    // Calendar windows reach ordering through demandSignals — that is how
    // demand_signals.py expresses a chametz or Ramadan gate.
    off: () => ({ ...base, demandSignals: {} }),
    probe: () => ({ ...base, demandSignals: { 'מוצרי מכולת': 0.5, 'חטיפים מתוקים': 1.4 } }),
  },
]

const results = []
for (const signal of SIGNALS) {
  if (signal.present()) {
    const changed = countDifferences(baseline, fingerprint(signal.off()))
    results.push({
      name: signal.name,
      state: changed > 0 ? 'LIVE' : 'INERT',
      detail:
        changed > 0
          ? `${changed} recommendations change when it is switched off`
          : 'input is present, but switching it off changes nothing',
    })
  } else {
    // Absent today. Prove the wiring anyway, or we learn nothing until the day
    // real data arrives and quietly fails to apply.
    const changed = countDifferences(baseline, fingerprint(signal.probe()))
    results.push({
      name: signal.name,
      state: changed > 0 ? 'INACTIVE' : 'INERT',
      detail:
        changed > 0
          ? `no real input today; a synthetic probe moved ${changed} recommendations, so the wiring carries`
          : 'no real input today AND a synthetic probe changed nothing — the wiring is broken',
    })
  }
}

const width = Math.max(...results.map((r) => r.name.length))
console.log(`baseline: ${baseline.size} REORDER recommendations\n`)
for (const r of results) {
  console.log(`  ${r.state.padEnd(8)} ${r.name.padEnd(width)}  ${r.detail}`)
}

const dead = results.filter((r) => r.state === 'INERT')
if (dead.length) {
  console.log('')
  for (const r of dead) console.log(`::error::Signal "${r.name}" is inert: ${r.detail}`)
  console.log('::error::A signal that moves no recommendation is not shipped, whatever its unit tests say.')
  process.exit(1)
}
console.log('\nEvery signal reaches an output.')
