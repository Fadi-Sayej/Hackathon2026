/**
 * compare_explanations.mjs — rule-based Hebrew vs Gemini, same 10 products.
 *
 *   node scripts/compare_explanations.mjs [--top 10] [--proxy http://localhost:8000/explain]
 *
 * Exists so the choice can be read rather than argued. The rule-based Hebrew is
 * already good; this produces the evidence for whether paying for the model makes
 * it better, worse, or merely different — and records every figure the guard had
 * to reject.
 */
import { readFileSync, writeFileSync } from 'fs'
import { validateExplanationResult, numbersIn, allowedNumbers } from '../src/lib/ai/factsGuard.js'

const args = process.argv.slice(2)
const argOf = (flag, fallback) => {
  const i = args.indexOf(flag)
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback
}
const top = Number(argOf('--top', '10'))
const proxyUrl = argOf('--proxy', 'http://localhost:8000/explain')

const [{ demoProducts }, { normalizeProducts }, eng, { toEngineContext }, { fallbackMarketContext }, i18n, explain] =
  await Promise.all([
    import('../src/data/demoProducts.js'),
    import('../src/lib/dataAdapters/productAdapter.js'),
    import('../src/lib/analytics/reorderEngine.js'),
    import('../src/lib/dataAdapters/loadMarketContext.js'),
    import('../src/lib/context/fallbackMarketContext.js'),
    import('../src/lib/i18n/index.js'),
    import('../src/lib/i18n/explainReorder.js'),
  ])

const artifact = JSON.parse(readFileSync('public/data/market-context.json', 'utf8'))
const ctx = toEngineContext(artifact, fallbackMarketContext)
const { products } = normalizeProducts(demoProducts)
const recs = eng
  .generateReorderRecommendations(products, ctx)
  .filter((r) => r.type === 'REORDER' && r.facts)
  .sort((a, b) => (b.valueAtStake ?? 0) - (a.valueAtStake ?? 0))
  .slice(0, top)

const t = i18n.createTranslator('he')
const n = (v) => i18n.formatNumber(v, 'he')

async function ask(facts) {
  const started = Date.now()
  try {
    const res = await fetch(proxyUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language: 'he', facts }),
      signal: AbortSignal.timeout(30000),
    })
    const ms = Date.now() - started
    if (!res.ok) return { error: `HTTP ${res.status} ${(await res.text()).slice(0, 120)}`, ms }
    const d = await res.json()
    return {
      ms,
      result: {
        explanation: d.shortExplanation,
        riskReason: d.riskReason,
        businessImpact: d.businessImpact,
        confidenceNote: d.confidenceNote,
      },
    }
  } catch (e) {
    return { error: `${e.name}: ${e.message}`.slice(0, 140), ms: Date.now() - started }
  }
}

const L = []
const rule = (c) => L.push(c.repeat(78))
L.push('השוואת הסברים — כללי מול Gemini')
L.push(`נוצר: ${new Date().toISOString()} · מודל: ${process.env.GEMINI_MODEL ?? '(ברירת מחדל של השרת)'}`)
L.push(`${recs.length} המלצות ההזמנה בעלות הערך הגבוה ביותר`)
rule('=')
L.push('')

let rejected = 0
let failed = 0
let totalMs = 0
const stats = []

for (const [i, r] of recs.entries()) {
  const f = r.facts
  const ruleBased = explain.renderReorderExplanation(f, t, n)
  const { result, error, ms } = await ask(f)
  totalMs += ms

  L.push(`${i + 1}. ${f.productName}`)
  L.push(`   הזמן: ${f.orderQty} יחידות · עלות ההזמנה: ₪${(r.valueAtStake ?? 0).toFixed(2)}`)
  L.push('')
  L.push('   ── כללי (המערכת הנוכחית) ──')
  for (const part of [ruleBased.quantity, ruleBased.timing, ruleBased.uncertainty, ruleBased.cost]) {
    if (part) L.push('   ' + part)
  }
  L.push('')
  L.push(`   ── Gemini (${ms}ms) ──`)

  if (error) {
    failed += 1
    L.push(`   [נכשל: ${error}]`)
    stats.push({ name: f.productName, state: 'failed' })
  } else {
    const verdict = validateExplanationResult(result, f)
    if (!verdict.ok) {
      rejected += 1
      L.push(`   [נדחה: המודל כתב ${verdict.invented.join(', ')} בשדה "${verdict.field}" — מספר שההחלטה לא כללה]`)
      L.push(`   [הטקסט שנדחה: ${result[verdict.field]}]`)
      stats.push({ name: f.productName, state: 'rejected', invented: verdict.invented })
    } else {
      for (const k of ['explanation', 'riskReason', 'businessImpact', 'confidenceNote']) {
        if (result[k]) L.push('   ' + result[k])
      }
      // Did it preserve the honesty the rule-based text carries?
      const joined = Object.values(result).join(' ')
      const keptAssumed = f.leadTimeAssumed
        ? /הנחה|מוערך|ברירת מחדל|לא מדידה/.test(joined)
        : null
      const keptCost = f.costToIgnore != null ? joined.includes(String(Math.round(f.costToIgnore))) : null
      stats.push({ name: f.productName, state: 'ok', keptAssumed, keptCost })
      L.push('')
      L.push(`   [בדיקה: זמן אספקה מוצג כהנחה? ${keptAssumed === null ? 'לא רלוונטי' : keptAssumed ? 'כן' : 'לא'}`
        + ` · סכום העלות מוזכר? ${keptCost === null ? 'לא רלוונטי' : keptCost ? 'כן' : 'לא'}]`)
    }
  }
  L.push('')
  rule('-')
  L.push('')
}

const ok = stats.filter((s) => s.state === 'ok')
L.push('סיכום')
rule('=')
L.push(`  התקבלו: ${ok.length} · נדחו בגלל מספר מומצא: ${rejected} · נכשלו: ${failed}`)
L.push(`  זמן תגובה ממוצע: ${Math.round(totalMs / Math.max(recs.length, 1))}ms`)
const assumedKept = ok.filter((s) => s.keptAssumed === true).length
const assumedTotal = ok.filter((s) => s.keptAssumed !== null).length
const costKept = ok.filter((s) => s.keptCost === true).length
const costTotal = ok.filter((s) => s.keptCost !== null).length
L.push(`  שמרו על הגילוי שזמן האספקה הוא הנחה: ${assumedKept}/${assumedTotal}`)
L.push(`  ציינו את סכום העלות: ${costKept}/${costTotal}`)

writeFileSync('reports/explanation_comparison_he.txt', L.join('\n'), 'utf8')
console.log(`accepted=${ok.length} rejected=${rejected} failed=${failed} avg=${Math.round(totalMs / Math.max(recs.length, 1))}ms`)
console.log(`assumed-lead-time disclosure kept: ${assumedKept}/${assumedTotal}`)
console.log(`cost figure stated: ${costKept}/${costTotal}`)
console.log('-> reports/explanation_comparison_he.txt')
