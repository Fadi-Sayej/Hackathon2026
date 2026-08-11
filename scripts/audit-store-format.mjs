/**
 * audit-store-format.mjs — the acceptance evidence for the store-identity track.
 *
 * Runs the real catalog and the real competitor prices through the real engines,
 * then checks the one thing that must never happen: a recommendation built on a
 * price from a store format we are not comparable to.
 *
 * Also prints what the filter costs us, because a filter that silently deletes
 * most of the product's signal is a decision someone has to make knowingly.
 *
 *   node scripts/audit-store-format.mjs [--sample 100]
 *
 * Exits non-zero if any recommendation is sourced from an affinity-0.0 store.
 */

import { readFileSync, existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

const { COMPETITOR_STORES, PRODUCT_ID_TO_BARCODE } = await import(
  path.join(rootDir, 'src/data/marketData.js')
)
const { buildLocalMarketSnapshot } = await import(
  path.join(rootDir, 'src/lib/dataAdapters/multiCompetitorAdapter.js')
)
const { analyzeLocalMarket } = await import(path.join(rootDir, 'src/lib/analytics/competitorEngine.js'))
const { generateReorderRecommendations } = await import(
  path.join(rootDir, 'src/lib/analytics/reorderEngine.js')
)
const { OUR_STORE_TYPE, storeTypeOf, formatAffinity, MIN_AFFINITY } = await import(
  path.join(rootDir, 'src/lib/analytics/storeFormat.js')
)

const sampleArg = process.argv.indexOf('--sample')
const SAMPLE_SIZE = sampleArg > -1 ? Number(process.argv[sampleArg + 1]) : 100

const CATALOG = path.join(rootDir, 'data/processed/analytics/normalized-products.json')

function loadProducts() {
  if (existsSync(CATALOG)) {
    return JSON.parse(readFileSync(CATALOG, 'utf-8'))
  }
  console.warn(`No ${path.relative(rootDir, CATALOG)} — falling back to the demo slice.`)
  return null
}

async function main() {
  let products = loadProducts()
  if (!products) {
    const demo = await import(path.join(rootDir, 'src/data/demoProducts.js'))
    products = demo.demoProducts
  }

  const snapshot = buildLocalMarketSnapshot(COMPETITOR_STORES)

  console.log(`Our store format: ${OUR_STORE_TYPE}`)
  console.log('Competitor sources:')
  for (const store of COMPETITOR_STORES) {
    const storeType = store.storeType ?? storeTypeOf(store.storeId)
    const affinity = formatAffinity(OUR_STORE_TYPE, storeType)
    const verdict =
      affinity === 0 ? 'EXCLUDED' : affinity < MIN_AFFINITY ? 'context only' : 'comparable'
    const priceCount = Object.keys(store.snapshot ?? {}).length
    console.log(
      `  ${store.storeId.padEnd(18)} ${storeType.padEnd(16)} ` +
        `affinity=${affinity.toFixed(1)}  ${verdict.padEnd(13)} ${priceCount} prices`,
    )
  }

  const enriched = analyzeLocalMarket(products, snapshot, { barcodeMap: PRODUCT_ID_TO_BARCODE })

  const withComparable = enriched.filter((p) => (p.competitor?.nearbyCompetitors ?? 0) > 0)
  const silenced = enriched.filter(
    (p) => (p.competitor?.nearbyCompetitors ?? 0) === 0 && (p.competitor?.excludedByFormat ?? 0) > 0,
  )
  const contextOnly = enriched.filter(
    (p) => (p.competitor?.nearbyCompetitors ?? 0) === 0 && (p.competitor?.contextOnlyCompetitors ?? 0) > 0,
  )

  const pad = (n) => String(n).padStart(6)
  console.log(`\nCoverage across ${enriched.length} products:`)
  console.log(`  ${pad(withComparable.length)} have a comparable competitor price`)
  console.log(`  ${pad(contextOnly.length)} have prices only from a context-only format`)
  console.log(`  ${pad(silenced.length)} have prices only from an EXCLUDED format`)

  const today = new Date().toISOString().slice(0, 10)
  const recommendations = enriched.flatMap((product) =>
    generateReorderRecommendations([product], {}, today),
  )

  const bySourceType = {}
  for (const rec of recommendations) {
    const key = rec.competitorStoreType ?? 'no competitor source'
    bySourceType[key] = (bySourceType[key] ?? 0) + 1
  }

  console.log(`\n${recommendations.length} recommendations, by the store format behind the price:`)
  for (const [key, count] of Object.entries(bySourceType).sort((a, b) => b[1] - a[1])) {
    console.log(`  ${key.padEnd(24)} ${count}`)
  }

  // The gate. Sampling is what the acceptance criterion asks for; we check all of
  // them anyway, because a filter you only spot-check is not a filter.
  const violations = recommendations.filter(
    (rec) => rec.competitorStoreType && formatAffinity(OUR_STORE_TYPE, rec.competitorStoreType) === 0,
  )

  // Competitor-sourced recommendations first: those are the ones a reviewer has
  // to eyeball for "could a forecourt shop actually sell this?". An internal
  // negative-stock alert cannot come from the wrong kind of store.
  const sample = [
    ...recommendations.filter((rec) => rec.competitorStoreType),
    ...recommendations.filter((rec) => !rec.competitorStoreType),
  ].slice(0, SAMPLE_SIZE)

  console.log(`\nSample of ${sample.length} for manual review (competitor-sourced first):`)
  for (const rec of sample.slice(0, 20)) {
    const name = (rec.productName ?? '').slice(0, 36).padEnd(36)
    const affinity = rec.competitorFormatAffinity
    const source = rec.competitorStoreType
      ? `${rec.competitorStoreType} (affinity ${affinity?.toFixed(1) ?? '?'})`
      : '— internal signal'
    console.log(`  ${rec.type.padEnd(14)} ${name} source=${source}`)
  }
  if (sample.length > 20) console.log(`  … ${sample.length - 20} more`)

  if (violations.length) {
    console.error(
      `\nFAIL: ${violations.length} recommendation(s) sourced from an affinity-0.0 store format.`,
    )
    return 1
  }
  console.log('\nPASS: no recommendation is sourced from an affinity-0.0 store format.')
  return 0
}

process.exit(await main())
