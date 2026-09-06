/**
 * report_reorder_explanations.mjs — the reorder explanations, as the owner sees them.
 *
 *   node scripts/report_reorder_explanations.mjs [--lang he] [--top 10]
 *
 * Renders through the same fact + i18n path the UI uses, so what is printed here is
 * what appears on screen. Nothing is recomputed for the report.
 */
import { writeFileSync } from 'fs'
import { readFileSync } from 'fs'

const args = process.argv.slice(2)
const argOf = (flag, fallback) => {
  const i = args.indexOf(flag)
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback
}
const lang = argOf('--lang', 'he')
const top = Number(argOf('--top', '10'))

const [{ demoProducts }, { normalizeProducts }, { generateReorderRecommendations }, i18n, explain] =
  await Promise.all([
    import('../src/data/demoProducts.js'),
    import('../src/lib/dataAdapters/productAdapter.js'),
    import('../src/lib/analytics/reorderEngine.js'),
    import('../src/lib/i18n/index.js'),
    import('../src/lib/i18n/explainReorder.js'),
  ])

const ctx = JSON.parse(readFileSync('public/data/market-context.json', 'utf8'))
const marketContext = {
  demandSignals: ctx.demandSignals ?? {},
  activeReasons: ctx.activeReasons ?? [],
  shelfLife: ctx.shelfLife ?? null,
}

const { products } = normalizeProducts(demoProducts)
const recs = generateReorderRecommendations(products, marketContext)
  .filter((r) => r.type === 'REORDER' && r.facts)
  .sort((a, b) => (b.valueAtStake ?? 0) - (a.valueAtStake ?? 0))

const t = i18n.createTranslator(lang)
const n = (v) => i18n.formatNumber(v, lang)
const L = []
const rule = (ch) => L.push(ch.repeat(78))

L.push(`הסברי הזמנה — ${top} ההמלצות המובילות`)
L.push(`נוצר: ${ctx.generatedAt} · מזג אוויר: ${ctx.weather?.label} ${ctx.weather?.temperatureC}°C`)
L.push(`גורמים פעילים היום: ${(ctx.activeReasons ?? []).join(', ') || 'אין'}`)
rule('='); L.push('')

const block = (r, index) => {
  const f = r.facts
  const p = explain.renderReorderExplanation(f, t, n)
  if (index !== null) L.push(`${index}. ${f.productName}`)
  else L.push(`${f.productName}`)
  L.push(
    `   ${t('explain.orderQty')}: ${f.orderQty} יחידות   ·   ` +
      `${t('explain.urgency')}: ${r.urgency}   ·   ` +
      `${t('explain.orderCost')}: ₪${(r.valueAtStake ?? 0).toFixed(2)}`,
  )
  L.push('')
  L.push('   למה הכמות הזו:'); L.push('   ' + p.quantity); L.push('')
  L.push('   למה עכשיו:'); L.push('   ' + p.timing); L.push('')
  L.push('   מה לא ידוע בוודאות:'); L.push('   ' + p.uncertainty); L.push('')
  L.push('   מה עולה להתעלם:')
  L.push('   ' + (p.cost ?? '— לא מוצג: אין מחיר עלות לפריט זה. —'))
  L.push(''); rule('-'); L.push('')
}

recs.slice(0, top).forEach((r, i) => block(r, i + 1))

// The weakest-evidence case, shown in full rather than hidden.
const worst =
  recs.find((r) => !r.facts.unitCost) ?? recs.find((r) => r.facts.rateConfidence === 'low')
if (worst) {
  L.push('נספח — המקרה הגרוע: פריט עם הנתונים החלשים ביותר')
  rule('='); L.push('')
  block(worst, null)
}

writeFileSync('reports/reorder_explanations_he.txt', L.join('\n'), 'utf8')
const capped = recs.filter((r) => r.facts.shelfLifeCapped).length
const preventable = recs.slice(0, top).filter((r) => r.facts.currentStock > 0).length
console.log(
  `candidates=${recs.length} capped_by_shelf_life=${capped} ` +
    `top${top}_not_yet_empty=${preventable} -> reports/reorder_explanations_he.txt`,
)
