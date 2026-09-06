import fs from 'node:fs/promises'
import { existsSync, readFileSync } from 'node:fs'
import { execSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { marketContext } from '../src/data/marketContext.js'
import { loadDemoStoreData } from '../src/lib/dataAdapters/loadDemoStoreData.js'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const rootDir = path.resolve(scriptDir, '..')
const ragDir = path.join(rootDir, 'data', 'processed', 'rag')

const SILVER_PARQUET = path.join(rootDir, 'data', 'internal', 'silver_pos', 'yomyom_products.parquet')
const EXPORT_JSON = path.join(rootDir, 'data', 'internal', 'silver_pos', 'yomyom_products_export.json')

function loadRealProducts() {
  if (!existsSync(SILVER_PARQUET)) return null
  try {
    execSync(
      `python -c "import polars as pl; df=pl.read_parquet('${SILVER_PARQUET}'); open('${EXPORT_JSON}','w',encoding='utf-8').write(df.write_json())"`,
      { stdio: 'inherit' },
    )
    const raw = JSON.parse(readFileSync(EXPORT_JSON, 'utf-8'))
    return raw.map((row) => ({
      id: `ym-${row.barcode ?? row.product_name}`,
      name: row.product_name ?? '',
      category: row.category ?? 'Uncategorized',
      price: row.selling_price ?? 0,
      cost: row.cost_price ?? 0,
      currentStock: Math.max(0, row.current_stock ?? 0),
      shelfQuantity: 0,
      shelfCapacity: 10,
      salesLast7Days: 0,
      salesLast30Days: 0,
      supplier: 'Unknown',
      leadTimeDays: 3,
      returnedUnits: 0,
      damagedUnits: 0,
    }))
  } catch {
    return null
  }
}

const CATEGORY_PLAYBOOKS = {
  Water: {
    guidance: 'Prioritize availability during hot weather, weekends, and local traffic spikes. Water is a high-frequency convenience purchase with strong stockout sensitivity.',
    tags: ['water', 'hot-weather', 'stockout-risk'],
  },
  'Cold Drinks': {
    guidance: 'Cold drinks should stay visible and well-stocked in warm weather. Fast movers deserve eye-level placement and higher reorder urgency.',
    tags: ['cold-drinks', 'weather-sensitive', 'fast-mover'],
  },
  'Energy Drinks': {
    guidance: 'Energy drinks perform well around commute, weekend, and event traffic. Protect shelf facings for high-margin fast movers.',
    tags: ['energy-drinks', 'high-margin', 'impulse'],
  },
  Snacks: {
    guidance: 'Snacks respond to weekend and event traffic. Use promotions for slow movers and pair shelf placement with drinks.',
    tags: ['snacks', 'cross-sell', 'weekend'],
  },
  Chocolate: {
    guidance: 'Chocolate is an impulse category. Keep compact high-margin products visible but watch slow-moving inventory.',
    tags: ['chocolate', 'impulse', 'margin'],
  },
  Bakery: {
    guidance: 'Bakery requires tight expiry control. Reorder conservatively and promote items approaching expiry.',
    tags: ['bakery', 'expiry-risk', 'waste-reduction'],
  },
  Dairy: {
    guidance: 'Dairy stock should balance availability with freshness. Near-expiry items should trigger waste-prevention actions.',
    tags: ['dairy', 'freshness', 'expiry-risk'],
  },
  'Ice Cream': {
    guidance: 'Ice cream demand rises with heat. Keep adequate stock in hot weather but monitor freezer capacity and expiry.',
    tags: ['ice-cream', 'hot-weather', 'capacity'],
  },
}

const PLANOGRAM_RULES = [
  {
    id: 'planogram-eye-level-premium',
    category: 'Shelf Optimization',
    text: 'Use eye-level shelf space for products with strong sales velocity, strong margin, or high stockout risk. Eye-level placement should make the best product decision easy for shoppers.',
    tags: ['planogram', 'eye-level', 'margin', 'velocity'],
  },
  {
    id: 'planogram-bottom-bulky-slow',
    category: 'Shelf Optimization',
    text: 'Use lower shelves for bulky, slower-moving, or low-urgency products. This preserves premium visual space for products that need faster conversion.',
    tags: ['planogram', 'bottom-shelf', 'slow-moving'],
  },
  {
    id: 'planogram-expiry-visibility',
    category: 'Shelf Optimization',
    text: 'Near-expiry products should be made visible only when paired with a clearance or promotion action. Placement alone is not enough to reduce waste risk.',
    tags: ['planogram', 'expiry-risk', 'promotion'],
  },
]

const REORDER_RULES = [
  {
    id: 'reorder-lead-time-cover',
    category: 'Smart Reorder',
    text: 'Recommend reorder when expected demand during supplier lead time plus safety stock exceeds current stock. Higher sales velocity and longer lead time increase urgency.',
    tags: ['reorder', 'lead-time', 'safety-stock'],
  },
  {
    id: 'reorder-avoid-slow-mover-overbuy',
    category: 'Smart Reorder',
    text: 'Avoid replenishing slow-moving products unless there is a clear market signal. Slow movers should usually receive promotion or shelf reduction recommendations first.',
    tags: ['reorder', 'slow-moving', 'overstock'],
  },
  {
    id: 'reorder-expiry-waste-control',
    category: 'Smart Reorder',
    text: 'For perishable products, near-expiry inventory should trigger waste-reduction actions before new purchasing decisions.',
    tags: ['reorder', 'expiry-risk', 'waste-reduction'],
  },
]

const MARKET_CONTEXT_TEMPLATES = [
  {
    id: 'market-weather-template',
    category: 'Market Context',
    text: 'Weather signals can raise demand for water, cold drinks, energy drinks, snacks, and ice cream. Hot weather should be clearly labeled as a demand multiplier, not as a guaranteed sales outcome.',
    tags: ['market-context', 'weather', 'demand-signal'],
  },
  {
    id: 'market-weekend-template',
    category: 'Market Context',
    text: 'Weekend and holiday signals can increase impulse purchases. Use these signals to explain why high-velocity categories receive higher reorder urgency.',
    tags: ['market-context', 'weekend', 'holiday'],
  },
  {
    id: 'market-event-template',
    category: 'Market Context',
    text: 'Local events may increase store foot traffic. Event context should be presented as an external signal and combined with inventory and sales data before recommending action.',
    tags: ['market-context', 'local-event', 'foot-traffic'],
  },
]

async function main() {
  const realProducts = loadRealProducts()
  const { products: demoProducts } = loadDemoStoreData()
  const products = realProducts ?? demoProducts
  console.log(`Building RAG corpus from ${products.length} products${realProducts ? ' (real YomYom data)' : ' (demo data)'}`)
  await fs.mkdir(ragDir, { recursive: true })

  const files = {
    'products.jsonl': buildProductChunks(products),
    'category-playbooks.jsonl': buildCategoryPlaybookChunks(products),
    'planogram-rules.jsonl': buildRuleChunks(PLANOGRAM_RULES, 'planogram_rule'),
    'reorder-rules.jsonl': buildRuleChunks(REORDER_RULES, 'reorder_rule'),
    'market-context-templates.jsonl': buildMarketContextChunks(),
  }

  await Promise.all(
    Object.entries(files).map(([filename, chunks]) =>
      writeJsonl(path.join(ragDir, filename), chunks),
    ),
  )

  await writeReadme(files)

  const totalChunks = Object.values(files).reduce((total, chunks) => total + chunks.length, 0)
  process.stdout.write(
    [
      `RAG corpus generated: ${path.relative(rootDir, ragDir)}`,
      `Files: ${Object.keys(files).length}`,
      `Chunks: ${totalChunks}`,
    ].join('\n'),
  )
}

function buildProductChunks(products) {
  return products.map((product) => ({
    id: `product-${product.id}`,
    source: 'src/data/demoProducts.js',
    type: 'product',
    category: product.category,
    text: [
      `${product.name} is a ${product.category} product supplied by ${product.supplier}.`,
      `Current stock is ${product.currentStock} units, shelf quantity is ${product.shelfQuantity}/${product.shelfCapacity}, and sales are ${product.salesLast7Days} units over 7 days and ${product.salesLast30Days} over 30 days.`,
      `Price is ILS ${product.price}, cost is ILS ${product.cost}, and supplier lead time is ${product.leadTimeDays} days.`,
      product.expiryDate ? `Expiry date is ${product.expiryDate}.` : 'No expiry date is recorded.',
    ].join(' '),
    tags: compact([
      'product',
      slug(product.category),
      product.expiryDate ? 'perishable' : null,
      product.salesLast30Days >= 40 ? 'fast-mover' : null,
    ]),
    metadata: {
      productId: product.id,
      name: product.name,
      supplier: product.supplier,
      currentStock: product.currentStock,
      shelfQuantity: product.shelfQuantity,
      shelfCapacity: product.shelfCapacity,
      salesLast7Days: product.salesLast7Days,
      salesLast30Days: product.salesLast30Days,
      price: product.price,
      cost: product.cost,
      leadTimeDays: product.leadTimeDays,
      expiryDate: product.expiryDate ?? null,
    },
  }))
}

function buildCategoryPlaybookChunks(products) {
  const categories = summarizeCategories(products)

  return categories.map((summary) => {
    const playbook = CATEGORY_PLAYBOOKS[summary.category] ?? {
      guidance: 'Use sales velocity, stockout risk, margin, and shelf constraints to decide reorder and placement actions.',
      tags: ['category', 'general-retail'],
    }

    return {
      id: `category-${slug(summary.category)}`,
      source: 'SmartShelf category playbooks',
      type: 'category_playbook',
      category: summary.category,
      text: [
        `${summary.category} has ${summary.productCount} demo products with ${summary.salesLast30Days} total units sold over 30 days and ${summary.currentStock} units currently on hand.`,
        playbook.guidance,
      ].join(' '),
      tags: ['category-playbook', ...playbook.tags],
      metadata: summary,
    }
  })
}

function buildRuleChunks(rules, type) {
  return rules.map((rule) => ({
    id: rule.id,
    source: 'SmartShelf technical rules',
    type,
    category: rule.category,
    text: rule.text,
    tags: rule.tags,
    metadata: {
      ruleId: rule.id,
      sprint: 'C4',
    },
  }))
}

function buildMarketContextChunks() {
  return MARKET_CONTEXT_TEMPLATES.map((template) => ({
    id: template.id,
    source: 'SmartShelf market context templates',
    type: 'market_context_template',
    category: template.category,
    text: `${template.text} Current fallback context: weather=${marketContext.weather}, weekend=${marketContext.weekend}, holiday=${marketContext.holiday}, localEvent=${marketContext.localEvent ?? 'none'}.`,
    tags: template.tags,
    metadata: {
      templateId: template.id,
      fallbackWeather: marketContext.weather,
      fallbackWeekend: marketContext.weekend,
      fallbackHoliday: marketContext.holiday,
      fallbackLocalEvent: marketContext.localEvent ?? null,
      fallbackSeason: marketContext.season ?? null,
    },
  }))
}

function summarizeCategories(products) {
  const map = new Map()

  for (const product of products) {
    if (!map.has(product.category)) {
      map.set(product.category, {
        category: product.category,
        productCount: 0,
        currentStock: 0,
        salesLast30Days: 0,
        averageMargin: 0,
      })
    }

    const summary = map.get(product.category)
    summary.productCount += 1
    summary.currentStock += product.currentStock
    summary.salesLast30Days += product.salesLast30Days
    summary.averageMargin += product.price - product.cost
  }

  return [...map.values()]
    .map((summary) => ({
      ...summary,
      averageMargin: round(summary.averageMargin / summary.productCount),
    }))
    .sort((left, right) => right.salesLast30Days - left.salesLast30Days)
}

async function writeJsonl(filePath, chunks) {
  await fs.writeFile(filePath, `${chunks.map((chunk) => JSON.stringify(chunk)).join('\n')}\n`)
}

async function writeReadme(files) {
  const lines = [
    '# SmartShelf AI RAG Corpus',
    '',
    'Generated by `scripts/build-rag-corpus.mjs`.',
    '',
    'This folder is RAG-ready only. It does not include a vector database, embeddings, or LLM calls.',
    '',
    '## Files',
    '',
    ...Object.entries(files).map(([filename, chunks]) => `- \`${filename}\`: ${chunks.length} JSONL chunks`),
    '',
    '## Chunk Schema',
    '',
    'Each line is a JSON object with:',
    '',
    '- `id`',
    '- `source`',
    '- `type`',
    '- `category`',
    '- `text`',
    '- `tags`',
    '- `metadata`',
    '',
    '## Future Embedding Path',
    '',
    'A future sprint can read these JSONL files, embed the `text` field, store vectors in a database, and retrieve chunks by product, category, rule type, or market signal tags.',
    '',
  ]

  await fs.writeFile(path.join(ragDir, 'README.md'), lines.join('\n'))
}

function slug(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function compact(values) {
  return values.filter(Boolean)
}

function round(value) {
  return Math.round(value * 100) / 100
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
