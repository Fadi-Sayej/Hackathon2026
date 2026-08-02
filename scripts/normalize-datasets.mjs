import fs from 'node:fs/promises'
import { existsSync, readFileSync } from 'node:fs'
import { execSync } from 'node:child_process'
import path from 'node:path'

const rootDir = process.cwd()
const rawDir = path.join(rootDir, 'data', 'raw')
const processedDemoDir = path.join(rootDir, 'data', 'processed', 'demo')
const processedAnalyticsDir = path.join(rootDir, 'data', 'processed', 'analytics')
const exportsDir = path.join(rootDir, 'data', 'exports', 'sample-app-data')
const appDataDir = path.join(rootDir, 'src', 'data')

const SILVER_PARQUET = path.join(rootDir, 'data', 'internal', 'silver_pos', 'yomyom_products.parquet')
const SILVER_SALES_PARQUET = path.join(rootDir, 'data', 'internal', 'silver_pos', 'yomyom_sales.parquet')
const SILVER_INVENTORY_PARQUET = path.join(rootDir, 'data', 'internal', 'silver_pos', 'yomyom_inventory.parquet')
const SILVER_JSON_CACHE = path.join(rootDir, 'data', 'internal', 'silver_pos', 'yomyom_products_export.json')
const VELOCITY_CONFIDENCE_LEVELS = ['none', 'low', 'medium', 'high']
const validVelocityConfidenceLevels = new Set(VELOCITY_CONFIDENCE_LEVELS)

// Stock and velocity live outside the products table, so the silver tables are
// joined before the rows reach the normalizer. Barcode is the join key; the ~300
// rows with no barcode fall back to product name, matching how `id` is derived below.
const exportSilverPy = `
import os
import polars as pl

def keyed(df):
    return df.with_columns(
        pl.when(pl.col('barcode').is_null() | (pl.col('barcode') == ''))
          .then(pl.concat_str([pl.lit('name:'), pl.col('product_name')]))
          .otherwise(pl.col('barcode'))
          .alias('_join_key')
    )

products = keyed(pl.read_parquet('${SILVER_PARQUET}'))

if os.path.exists('${SILVER_INVENTORY_PARQUET}'):
    inventory = keyed(pl.read_parquet('${SILVER_INVENTORY_PARQUET}')).select(
        ['_join_key', 'current_stock']
    ).unique(subset=['_join_key'], keep='first')
    merged = products.join(inventory, on='_join_key', how='left')
else:
    merged = products.with_columns(pl.lit(None).cast(pl.Int64).alias('current_stock'))

if os.path.exists('${SILVER_SALES_PARQUET}'):
    sales = keyed(pl.read_parquet('${SILVER_SALES_PARQUET}'))
    velocity_columns = [
        column for column in ['units_sold_7d', 'units_sold_30d', 'velocity_confidence']
        if column in sales.columns
    ]
    sales = sales.select(['_join_key', *velocity_columns]).unique(
        subset=['_join_key'], keep='first'
    )
    merged = merged.join(sales, on='_join_key', how='left')

merged = merged.drop('_join_key')
open('${SILVER_JSON_CACHE}', 'w', encoding='utf-8').write(merged.write_json())
`

function normalizeVelocityConfidence(value) {
  return validVelocityConfidenceLevels.has(value) ? value : 'none'
}

function parseFiniteNumber(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value !== 'string' || value.trim() === '') return null

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function loadYomYomSilver() {
  if (!existsSync(SILVER_PARQUET)) return null
  try {
    execSync(`python3 -c "${exportSilverPy}"`, { stdio: 'pipe', cwd: rootDir })
    const raw = JSON.parse(readFileSync(SILVER_JSON_CACHE, 'utf-8'))
    return raw
      .filter(row => row.selling_price && row.selling_price > 0 && row.product_name)
      .map(row => {
        const currentStock = parseFiniteNumber(row.current_stock)
        const salesLast7Days = parseFiniteNumber(row.units_sold_7d)
        const salesLast30Days = parseFiniteNumber(row.units_sold_30d)
        const hasVelocityData = salesLast7Days !== null && salesLast30Days !== null

        return {
          id: row.barcode ? `ym-${String(row.barcode).replace(/^0+/, '')}` : `ym-${row.product_name}`,
          name: row.product_name,
          category: row.category ?? 'Uncategorized',
          price: Number(row.selling_price) || 0,
          cost: Number(row.cost_price) || 0,
          currentStock: currentStock ?? 0,
          shelfQuantity: 0,
          shelfCapacity: 10,
          salesLast7Days: salesLast7Days ?? 0,
          salesLast30Days: salesLast30Days ?? 0,
          velocityConfidence: hasVelocityData
            ? normalizeVelocityConfidence(row.velocity_confidence)
            : 'none',
          supplier: 'YomYom',
          leadTimeDays: 3,
          returnedUnits: 0,
          damagedUnits: 0,
          expiryDate: undefined,
        }
      })
  } catch (err) {
    process.stderr.write(`Warning: could not load YomYom silver Parquet: ${err.message}\n`)
    return null
  }
}

const aliases = {
  productId: ['product id', 'product_id', 'sku', 'sku id', 'item id', 'item_id'],
  productName: [
    'product name',
    'product_name',
    'item',
    'item name',
    'item_name',
    'product',
    'name',
  ],
  category: ['category', 'product category', 'segment', 'department'],
  date: ['date', 'transaction date', 'sales date', 'day'],
  stock: [
    'inventory level',
    'inventory',
    'current stock',
    'current_stock',
    'stock',
    'stock on hand',
    'quantity on hand',
  ],
  sold: ['units sold', 'sales', 'quantity sold', 'qty sold', 'demand', 'units'],
  ordered: ['units ordered', 'order qty', 'order quantity', 'ordered'],
  forecast: ['demand forecast', 'forecast', 'predicted demand'],
  price: ['price', 'unit price', 'selling price'],
  cost: ['cost', 'unit cost'],
  supplier: ['supplier', 'vendor', 'brand owner'],
  leadTimeDays: ['lead time days', 'lead_time_days', 'lead time', 'leadtime'],
  shelfCapacity: ['shelf capacity', 'shelf_capacity', 'capacity'],
  shelfQuantity: ['shelf quantity', 'shelf_quantity', 'facings'],
  returnedUnits: ['returned units', 'returns'],
  damagedUnits: ['damaged units', 'damaged'],
}

const leadTimeByCategory = {
  'Cold Drinks': 3,
  'Energy Drinks': 3,
  Snacks: 5,
  Chocolate: 5,
  Cigarettes: 4,
  Dairy: 2,
  Coffee: 6,
  Water: 4,
  'Ice Cream': 2,
  Bakery: 1,
  'Gum & Candy': 5,
  'Car Accessories': 7,
}

const perishableCategories = new Set(['Dairy', 'Bakery', 'Ice Cream'])

async function main() {
  await ensureDirectories()

  const yomyomProducts = loadYomYomSilver()

  let demoProducts
  let normalized
  let source

  if (yomyomProducts && yomyomProducts.length > 0) {
    demoProducts = yomyomProducts
    normalized = { products: yomyomProducts, generatedFields: [], notes: [] }
    source = {
      mode: 'real-silver',
      label: `YomYom silver Parquet (${yomyomProducts.length} products)`,
      rowCount: yomyomProducts.length,
      rows: Array.from({ length: yomyomProducts.length }),
      path: SILVER_PARQUET,
    }
    process.stdout.write(`Using real YomYom inventory: ${yomyomProducts.length} products\n`)
  } else {
    const discovered = await discoverDataFiles(rawDir)
    source = discovered.length > 0 ? await chooseBestSource(discovered) : buildFallbackSource()
    normalized = normalizeSource(source)
    demoProducts = buildDemoSlice(normalized.products)
    process.stdout.write(`Falling back to demo data: ${demoProducts.length} products\n`)
  }

  const analyticsSummary = buildAnalyticsSummary(normalized.products)
  const report = buildReport(source, normalized.products, normalized.generatedFields ?? [], normalized.notes ?? [])
  const velocityConfidenceCounts = Object.fromEntries(
    VELOCITY_CONFIDENCE_LEVELS.map(level => [level, 0]),
  )
  for (const product of normalized.products) {
    velocityConfidenceCounts[normalizeVelocityConfidence(product.velocityConfidence)] += 1
  }

  await fs.writeFile(
    path.join(processedDemoDir, 'demo-products.json'),
    `${JSON.stringify(demoProducts, null, 2)}\n`,
  )
  await fs.writeFile(
    path.join(processedAnalyticsDir, 'normalized-products.json'),
    `${JSON.stringify(normalized.products, null, 2)}\n`,
  )
  await fs.writeFile(
    path.join(processedAnalyticsDir, 'analytics-summary.json'),
    `${JSON.stringify(analyticsSummary, null, 2)}\n`,
  )
  await fs.writeFile(
    path.join(processedAnalyticsDir, 'normalization-report.json'),
    `${JSON.stringify(report, null, 2)}\n`,
  )
  await fs.writeFile(
    path.join(exportsDir, 'demo-products.json'),
    `${JSON.stringify(demoProducts, null, 2)}\n`,
  )
  await fs.writeFile(
    path.join(appDataDir, 'demoProducts.js'),
    [
      '// Generated by scripts/normalize-datasets.mjs. Edit the source dataset or pipeline, not this file.',
      `export const demoProducts = ${JSON.stringify(demoProducts, null, 2)}`,
      '',
    ].join('\n'),
  )

  process.stdout.write(
    [
      `Normalization mode: ${report.mode}`,
      `Source: ${report.sourceLabel}`,
      `Rows processed: ${report.sourceRowCount}`,
      `Products normalized: ${report.normalizedProductCount}`,
      `Velocity confidence: ${VELOCITY_CONFIDENCE_LEVELS.map(level => `${level}=${velocityConfidenceCounts[level]}`).join(', ')}`,
      `Demo export: ${path.relative(rootDir, path.join(exportsDir, 'demo-products.json'))}`,
      `App data export: ${path.relative(rootDir, path.join(appDataDir, 'demoProducts.js'))}`,
    ].join('\n'),
  )
}

async function ensureDirectories() {
  await Promise.all([
    fs.mkdir(processedDemoDir, { recursive: true }),
    fs.mkdir(processedAnalyticsDir, { recursive: true }),
    fs.mkdir(exportsDir, { recursive: true }),
    fs.mkdir(appDataDir, { recursive: true }),
  ])
}

async function discoverDataFiles(startDir) {
  const entries = await fs.readdir(startDir, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    const entryPath = path.join(startDir, entry.name)
    if (entry.isDirectory()) {
      files.push(...(await discoverDataFiles(entryPath)))
      continue
    }

    if (!entry.isFile()) continue
    if (entry.name === '.gitkeep') continue

    const extension = path.extname(entry.name).toLowerCase()
    if (extension === '.csv' || extension === '.json') {
      files.push(entryPath)
    }
  }

  return files
}

async function chooseBestSource(files) {
  const scored = []

  for (const filePath of files) {
    const extension = path.extname(filePath).toLowerCase()
    let rows = []
    try {
      rows = extension === '.csv' ? parseCsv(await fs.readFile(filePath, 'utf8')) : parseJson(await fs.readFile(filePath, 'utf8'))
    } catch {
      continue
    }

    if (!rows.length) continue

    const headers = Object.keys(rows[0])
    const score = scoreHeaders(headers, filePath)
    scored.push({ filePath, rows, headers, score })
  }

  if (!scored.length) {
    return buildFallbackSource()
  }

  scored.sort((left, right) => right.score - left.score)
  return {
    mode: 'raw',
    label: path.basename(scored[0].filePath),
    path: scored[0].filePath,
    rows: scored[0].rows,
  }
}

function parseJson(raw) {
  const parsed = JSON.parse(raw)

  if (Array.isArray(parsed)) {
    return parsed.filter((row) => row && typeof row === 'object' && !Array.isArray(row))
  }

  if (parsed && typeof parsed === 'object') {
    for (const value of Object.values(parsed)) {
      if (Array.isArray(value) && value.every((row) => row && typeof row === 'object')) {
        return value
      }
    }
  }

  return []
}

function parseCsv(raw) {
  const rows = []
  const parsedRows = []
  let current = ''
  let row = []
  let inQuotes = false

  for (let index = 0; index < raw.length; index += 1) {
    const char = raw[index]
    const next = raw[index + 1]

    if (char === '"') {
      if (inQuotes && next === '"') {
        current += '"'
        index += 1
      } else {
        inQuotes = !inQuotes
      }
      continue
    }

    if (char === ',' && !inQuotes) {
      row.push(current)
      current = ''
      continue
    }

    if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') {
        index += 1
      }
      row.push(current)
      parsedRows.push(row)
      row = []
      current = ''
      continue
    }

    current += char
  }

  if (current.length > 0 || row.length > 0) {
    row.push(current)
    parsedRows.push(row)
  }

  const nonEmptyRows = parsedRows.filter((entry) => entry.some((value) => String(value).trim() !== ''))
  if (!nonEmptyRows.length) return rows

  const headers = nonEmptyRows[0].map((header) => header.trim())

  for (const values of nonEmptyRows.slice(1)) {
    const record = {}
    headers.forEach((header, index) => {
      record[header] = (values[index] ?? '').trim()
    })
    rows.push(record)
  }

  return rows
}

function scoreHeaders(headers, filePath) {
  const headerScore =
    countAliasMatches(headers, aliases.productName) * 8 +
    countAliasMatches(headers, aliases.stock) * 7 +
    countAliasMatches(headers, aliases.sold) * 7 +
    countAliasMatches(headers, aliases.price) * 5 +
    countAliasMatches(headers, aliases.category) * 5 +
    countAliasMatches(headers, aliases.date) * 4

  const loweredPath = filePath.toLowerCase()
  const filenameScore =
    (loweredPath.includes('inventory') ? 10 : 0) +
    (loweredPath.includes('forecast') ? 7 : 0) +
    (loweredPath.includes('grocery') ? 5 : 0) +
    (loweredPath.includes('retail') ? 5 : 0)

  return headerScore + filenameScore
}

function countAliasMatches(headers, candidates) {
  const normalized = headers.map(normalizeKey)
  return candidates.reduce((total, candidate) => total + (normalized.includes(normalizeKey(candidate)) ? 1 : 0), 0)
}

function normalizeSource(source) {
  const generatedFields = new Set()
  const notes = []
  const headers = Object.keys(source.rows[0] ?? {})
  const columnMap = {
    productId: findHeader(headers, aliases.productId),
    productName: findHeader(headers, aliases.productName),
    category: findHeader(headers, aliases.category),
    date: findHeader(headers, aliases.date),
    stock: findHeader(headers, aliases.stock),
    sold: findHeader(headers, aliases.sold),
    ordered: findHeader(headers, aliases.ordered),
    forecast: findHeader(headers, aliases.forecast),
    price: findHeader(headers, aliases.price),
    cost: findHeader(headers, aliases.cost),
    supplier: findHeader(headers, aliases.supplier),
    leadTimeDays: findHeader(headers, aliases.leadTimeDays),
    shelfCapacity: findHeader(headers, aliases.shelfCapacity),
    shelfQuantity: findHeader(headers, aliases.shelfQuantity),
    returnedUnits: findHeader(headers, aliases.returnedUnits),
    damagedUnits: findHeader(headers, aliases.damagedUnits),
  }

  const groups = new Map()

  for (const row of source.rows) {
    const productName = readString(row, columnMap.productName) || readString(row, columnMap.productId) || 'Unknown Product'
    const category = standardizeCategory(readString(row, columnMap.category))
    const key = `${readString(row, columnMap.productId) || productName}::${category}`
    const observedDate = parseDateValue(readString(row, columnMap.date))

    if (!groups.has(key)) {
      groups.set(key, {
        id: slugify(readString(row, columnMap.productId) || productName),
        name: titleCase(productName),
        category,
        observations: [],
      })
    }

    groups.get(key).observations.push({
      row,
      observedDate,
      stock: parseNumber(readString(row, columnMap.stock)),
      sold: parseNumber(readString(row, columnMap.sold)),
      ordered: parseNumber(readString(row, columnMap.ordered)),
      forecast: parseNumber(readString(row, columnMap.forecast)),
      price: parseNumber(readString(row, columnMap.price)),
      cost: parseNumber(readString(row, columnMap.cost)),
      supplier: readString(row, columnMap.supplier),
      leadTimeDays: parseNumber(readString(row, columnMap.leadTimeDays)),
      shelfCapacity: parseNumber(readString(row, columnMap.shelfCapacity)),
      shelfQuantity: parseNumber(readString(row, columnMap.shelfQuantity)),
      returnedUnits: parseNumber(readString(row, columnMap.returnedUnits)),
      damagedUnits: parseNumber(readString(row, columnMap.damagedUnits)),
    })
  }

  const products = Array.from(groups.values())
    .map((group) => {
      const ordered = group.observations
        .slice()
        .sort((left, right) => (left.observedDate?.getTime() ?? 0) - (right.observedDate?.getTime() ?? 0))
      const latestObservation = ordered.at(-1)
      const latestDate = latestObservation?.observedDate ?? newestDateFromObservations(ordered) ?? new Date()
      const salesLast7Days = sumWithinDays(ordered, latestDate, 7, 'sold')
      const salesLast30Days = sumWithinDays(ordered, latestDate, 30, 'sold')
      const currentStock = fallbackNumber(latestObservation?.stock, maxNumber(ordered.map((entry) => entry.stock)), 0)
      const price = roundCurrency(fallbackNumber(latestObservation?.price, averageNumber(ordered.map((entry) => entry.price)), 0))
      const costCandidate = fallbackNumber(latestObservation?.cost, averageNumber(ordered.map((entry) => entry.cost)), null)
      const cost = roundCurrency(costCandidate ?? price * 0.67)
      if (costCandidate === null) generatedFields.add('cost')

      const leadTimeCandidate = fallbackNumber(
        latestObservation?.leadTimeDays,
        averageNumber(ordered.map((entry) => entry.leadTimeDays)),
        null,
      )
      const leadTimeDays = Math.max(1, Math.round(leadTimeCandidate ?? inferLeadTime(group.category)))
      if (leadTimeCandidate === null) generatedFields.add('leadTimeDays')

      const shelfCapacityCandidate = fallbackNumber(
        latestObservation?.shelfCapacity,
        maxNumber(ordered.map((entry) => entry.shelfCapacity)),
        null,
      )
      const shelfCapacity = Math.max(6, Math.round(shelfCapacityCandidate ?? inferShelfCapacity(currentStock, salesLast7Days)))
      if (shelfCapacityCandidate === null) generatedFields.add('shelfCapacity')

      const shelfQuantityCandidate = fallbackNumber(
        latestObservation?.shelfQuantity,
        averageNumber(ordered.map((entry) => entry.shelfQuantity)),
        null,
      )
      const shelfQuantity = Math.min(
        shelfCapacity,
        Math.max(2, Math.round(shelfQuantityCandidate ?? inferShelfQuantity(currentStock, salesLast7Days, shelfCapacity))),
      )
      if (shelfQuantityCandidate === null) generatedFields.add('shelfQuantity')

      const supplierCandidate = latestObservation?.supplier || inferSupplier(group.category)
      if (!latestObservation?.supplier) generatedFields.add('supplier')

      const returnedUnits = Math.max(
        0,
        Math.round(fallbackNumber(latestObservation?.returnedUnits, averageNumber(ordered.map((entry) => entry.returnedUnits)), 0)),
      )
      const damagedUnits = Math.max(
        0,
        Math.round(fallbackNumber(latestObservation?.damagedUnits, averageNumber(ordered.map((entry) => entry.damagedUnits)), 0)),
      )

      const expiryDate = inferExpiryDate(group.category, latestDate)
      if (expiryDate) generatedFields.add('expiryDate')

      return {
        id: group.id,
        name: group.name,
        category: group.category,
        currentStock: roundNumber(currentStock),
        shelfQuantity,
        shelfCapacity,
        salesLast7Days: roundNumber(salesLast7Days),
        salesLast30Days: roundNumber(Math.max(salesLast30Days, salesLast7Days)),
        velocityConfidence: 'none',
        price,
        cost,
        expiryDate,
        supplier: supplierCandidate,
        leadTimeDays,
        returnedUnits,
        damagedUnits,
      }
    })
    .filter((product) => product.name !== 'Unknown Product')
    .sort((left, right) => right.salesLast30Days - left.salesLast30Days || left.name.localeCompare(right.name))

  if (!columnMap.cost) notes.push('No explicit cost column detected, so cost was estimated from price.')
  if (!columnMap.leadTimeDays) notes.push('Lead times were inferred from product category defaults.')
  if (!columnMap.shelfCapacity) notes.push('Shelf capacity was generated heuristically from stock and weekly sales.')
  if (!columnMap.shelfQuantity) notes.push('Shelf quantity was generated heuristically from stock and weekly sales.')

  return { products, generatedFields: [...generatedFields].sort(), notes }
}

function buildDemoSlice(products) {
  const grouped = new Map()
  for (const product of products) {
    if (!grouped.has(product.category)) grouped.set(product.category, [])
    grouped.get(product.category).push(product)
  }

  const result = []
  const perCategoryLimit = 4

  for (const items of grouped.values()) {
    for (const item of items.slice(0, perCategoryLimit)) {
      result.push(item)
    }
  }

  return result
    .sort((left, right) => right.salesLast30Days - left.salesLast30Days || left.name.localeCompare(right.name))
    .slice(0, 36)
}

function buildAnalyticsSummary(products) {
  const categoryMap = new Map()
  let totalStockValue = 0

  for (const product of products) {
    totalStockValue += product.currentStock * product.cost
    if (!categoryMap.has(product.category)) {
      categoryMap.set(product.category, {
        category: product.category,
        products: 0,
        salesLast30Days: 0,
        currentStock: 0,
      })
    }

    const entry = categoryMap.get(product.category)
    entry.products += 1
    entry.salesLast30Days += product.salesLast30Days
    entry.currentStock += product.currentStock
  }

  return {
    totalProducts: products.length,
    estimatedStockValue: roundCurrency(totalStockValue),
    categories: [...categoryMap.values()].sort((left, right) => right.salesLast30Days - left.salesLast30Days),
  }
}

function buildReport(source, products, generatedFields, notes) {
  const latestObservedDate = newestDateFromProducts(products)
  return {
    mode: source.mode,
    sourceLabel: source.label,
    sourcePath: source.path ?? null,
    sourceRowCount: source.rows.length,
    normalizedProductCount: products.length,
    latestObservedDate,
    generatedFields,
    notes: [
      ...(source.mode === 'fallback'
        ? ['No raw dataset file was found, so the Sprint 2 fallback retail sample was used.']
        : []),
      ...notes,
    ],
  }
}

function buildFallbackSource() {
  const products = [
    ['RB-001', 'Red Bull 250ml', 'Energy Drinks', 34, 8, 6.95],
    ['XL-002', 'XL Energy 250ml', 'Energy Drinks', 28, 6, 5.75],
    ['CC-003', 'Coca Cola 500ml', 'Cold Drinks', 42, 10, 4.5],
    ['PP-004', 'Pepsi 500ml', 'Cold Drinks', 40, 9, 4.5],
    ['WT-005', 'Mineral Water 1.5L', 'Water', 54, 13, 3.25],
    ['BM-006', 'Bamba 70g', 'Snacks', 26, 5, 3.8],
    ['DR-007', 'Doritos Nacho', 'Snacks', 22, 5, 6.2],
    ['PR-008', 'Pringles Original', 'Snacks', 18, 4, 8.9],
    ['KB-009', 'Kinder Bueno', 'Chocolate', 20, 4, 5.5],
    ['MS-010', 'Mars Bar', 'Chocolate', 24, 4, 4.1],
    ['ML-011', 'Milk 1L', 'Dairy', 16, 6, 6.4],
    ['YG-012', 'Greek Yogurt Cup', 'Dairy', 14, 5, 5.8],
    ['CF-013', 'Turkish Coffee 200g', 'Coffee', 15, 3, 13.5],
    ['IC-014', 'Ice Cream Cup Vanilla', 'Ice Cream', 17, 4, 7.3],
    ['SG-015', 'Marlboro Gold', 'Cigarettes', 60, 7, 32],
    ['SA-016', 'Car Air Freshener', 'Car Accessories', 12, 2, 11.5],
    ['BK-017', 'Butter Croissant', 'Bakery', 10, 6, 4.8],
    ['GW-018', 'Orbit Gum', 'Gum & Candy', 30, 4, 3.1],
    ['CD-019', 'Chocolate Donut', 'Bakery', 11, 5, 4.2],
    ['LK-020', 'Laban Drink', 'Dairy', 18, 6, 5.2],
    ['SP-021', 'Sprite 500ml', 'Cold Drinks', 31, 7, 4.4],
    ['FN-022', 'Fanta Orange 500ml', 'Cold Drinks', 27, 6, 4.4],
    ['TN-023', 'Tuna Sandwich', 'Bakery', 9, 4, 9.5],
    ['ND-024', 'Nescafe Gold Sachets', 'Coffee', 19, 3, 12.8],
    ['TW-025', 'Twix Bar', 'Chocolate', 21, 4, 4.3],
    ['WW-026', 'Small Water 500ml', 'Water', 48, 12, 2.4],
    ['OR-027', 'Orange Juice 330ml', 'Cold Drinks', 23, 5, 6.1],
    ['SN-028', 'Sunflower Seeds', 'Snacks', 17, 3, 4.7],
    ['HM-029', 'Hummus Crackers', 'Snacks', 13, 2, 7.4],
    ['GD-030', 'Galaxy Dark', 'Chocolate', 16, 3, 5.9],
  ]

  const observationOffsets = [30, 20, 10, 5, 0]
  const baseDate = new Date('2026-05-15T00:00:00Z')
  const rows = []

  products.forEach(([productId, productName, category, baseStock, salesVelocity, price], productIndex) => {
    observationOffsets.forEach((offset, observationIndex) => {
      const date = new Date(baseDate)
      date.setUTCDate(baseDate.getUTCDate() - offset)

      const seasonalityBoost = category === 'Cold Drinks' || category === 'Energy Drinks' || category === 'Water' ? 1.15 : 1
      const sold = Math.max(0, Math.round((salesVelocity + observationIndex + (productIndex % 3)) * seasonalityBoost))
      const inventoryLevel = Math.max(2, Math.round(baseStock - observationIndex * (salesVelocity * 0.55) + (productIndex % 5)))
      const unitsOrdered = observationIndex === 0 ? salesVelocity * 3 : Math.max(0, Math.round(salesVelocity * 1.2))

      rows.push({
        Date: date.toISOString().slice(0, 10),
        'Store ID': 'GAS-01',
        'Product ID': productId,
        'Product Name': productName,
        Category: category,
        Region: 'Central',
        'Inventory Level': inventoryLevel,
        'Units Sold': sold,
        'Units Ordered': unitsOrdered,
        'Demand Forecast': Math.round(sold * 1.18),
        Price: price.toFixed(2),
        Discount: observationIndex >= 3 ? '0.05' : '0',
        'Weather Condition': ['Hot', 'Hot', 'Warm', 'Warm', 'Hot'][observationIndex],
        'Holiday/Promotion': observationIndex === 4 ? 'Weekend Campaign' : 'None',
        'Competitor Pricing': (price * 0.96).toFixed(2),
        Seasonality: 'Summer',
      })
    })
  })

  return {
    mode: 'fallback',
    label: 'built-in-retail-store-inventory-forecasting-sample',
    path: null,
    rows,
  }
}

function findHeader(headers, candidates) {
  const normalizedHeaders = new Map(headers.map((header) => [normalizeKey(header), header]))
  for (const candidate of candidates) {
    const match = normalizedHeaders.get(normalizeKey(candidate))
    if (match) return match
  }
  return null
}

function readString(row, key) {
  if (!key) return ''
  const value = row[key]
  return value == null ? '' : String(value).trim()
}

function parseNumber(value) {
  if (value == null || value === '') return null
  const normalized = String(value).replace(/[$,%]/g, '').replace(/,/g, '').trim()
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

function parseDateValue(value) {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function normalizeKey(value) {
  return String(value).trim().toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ')
}

function newestDateFromObservations(observations) {
  return observations.reduce((latest, entry) => {
    if (!entry.observedDate) return latest
    if (!latest || entry.observedDate > latest) return entry.observedDate
    return latest
  }, null)
}

function newestDateFromProducts(products) {
  return products.length ? new Date('2026-05-15T00:00:00Z').toISOString().slice(0, 10) : null
}

function sumWithinDays(observations, latestDate, days, field) {
  const threshold = new Date(latestDate)
  threshold.setUTCDate(threshold.getUTCDate() - days + 1)
  return observations.reduce((total, entry) => {
    if (!entry.observedDate || entry.observedDate < threshold || entry.observedDate > latestDate) return total
    return total + (entry[field] ?? 0)
  }, 0)
}

function fallbackNumber(...values) {
  for (const value of values) {
    if (value == null) continue
    if (Number.isFinite(value)) return value
  }
  return null
}

function maxNumber(values) {
  const filtered = values.filter(Number.isFinite)
  return filtered.length ? Math.max(...filtered) : null
}

function averageNumber(values) {
  const filtered = values.filter(Number.isFinite)
  return filtered.length ? filtered.reduce((sum, value) => sum + value, 0) / filtered.length : null
}

function inferLeadTime(category) {
  return leadTimeByCategory[category] ?? 4
}

function inferShelfCapacity(currentStock, salesLast7Days) {
  return Math.max(8, Math.min(30, Math.ceil(Math.max(currentStock, salesLast7Days) * 0.5)))
}

function inferShelfQuantity(currentStock, salesLast7Days, shelfCapacity) {
  const velocity = Math.ceil(salesLast7Days / 4)
  return Math.min(shelfCapacity, Math.max(2, Math.min(currentStock, velocity)))
}

function inferSupplier(category) {
  return `${category} Preferred Supplier`
}

function inferExpiryDate(category, referenceDate) {
  if (!perishableCategories.has(category)) return undefined
  const date = new Date(referenceDate)
  const addedDays = category === 'Bakery' ? 2 : category === 'Dairy' ? 6 : 14
  date.setUTCDate(date.getUTCDate() + addedDays)
  return date.toISOString().slice(0, 10)
}

function roundCurrency(value) {
  return Number(value.toFixed(2))
}

function roundNumber(value) {
  return Math.max(0, Math.round(value))
}

function slugify(value) {
  return String(value)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function titleCase(value) {
  return String(value)
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function standardizeCategory(value) {
  const raw = String(value || '').trim()
  if (!raw) return 'General'

  const knownCategories = [
    'Cold Drinks',
    'Energy Drinks',
    'Snacks',
    'Chocolate',
    'Cigarettes',
    'Dairy',
    'Coffee',
    'Water',
    'Ice Cream',
    'Car Accessories',
    'Bakery',
    'Gum & Candy',
  ]

  const exact = knownCategories.find((category) => normalizeKey(category) === normalizeKey(raw))
  if (exact) return exact

  const normalized = normalizeKey(raw)
  if (normalized.includes('drink') && normalized.includes('energy')) return 'Energy Drinks'
  if (normalized.includes('drink')) return 'Cold Drinks'
  if (normalized.includes('water')) return 'Water'
  if (normalized.includes('snack') || normalized.includes('chips') || normalized.includes('cracker')) return 'Snacks'
  if (normalized.includes('chocolate') || normalized.includes('candy')) return 'Chocolate'
  if (normalized.includes('coffee')) return 'Coffee'
  if (normalized.includes('milk') || normalized.includes('dairy') || normalized.includes('yogurt')) return 'Dairy'
  if (normalized.includes('ice')) return 'Ice Cream'
  if (normalized.includes('bakery') || normalized.includes('bread') || normalized.includes('sandwich')) return 'Bakery'
  if (normalized.includes('cig')) return 'Cigarettes'

  return titleCase(raw)
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
