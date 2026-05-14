const statusLabels = {
  healthy: 'Healthy',
  lowStock: 'Low stock',
  stockoutRisk: 'Stockout risk',
  overstocked: 'Overstocked',
  slowMoving: 'Slow moving',
  nearExpiry: 'Near expiry',
  highPriority: 'High priority',
}

export function analyzeProducts(products, context = {}) {
  return products.map((product) => analyzeProduct(product, context))
}

export function analyzeProduct(product, context = {}) {
  const avgDailySales7 = safeDivide(product.salesLast7Days, 7)
  const avgDailySales30 = safeDivide(product.salesLast30Days, 30)
  const demandMultiplier = context.demandSignals?.[product.category] ?? 1
  const weightedAvgDailySales = (avgDailySales7 * 0.7 + avgDailySales30 * 0.3) * demandMultiplier
  const daysUntilStockout =
    weightedAvgDailySales > 0 ? product.currentStock / weightedAvgDailySales : Number.POSITIVE_INFINITY
  const nearExpiry = isNearExpiry(product.expiryDate, context.currentDate)
  const slowMoving = product.salesLast30Days < 5 || weightedAvgDailySales < 0.3
  const stockoutRisk = daysUntilStockout <= product.leadTimeDays
  const lowStock = !stockoutRisk && daysUntilStockout <= product.leadTimeDays + 2
  const overstocked = !slowMoving && product.currentStock > weightedAvgDailySales * 30
  const highPriority = stockoutRisk || (nearExpiry && product.currentStock > product.shelfQuantity)
  const statuses = collectStatuses({
    healthy: !stockoutRisk && !lowStock && !overstocked && !slowMoving && !nearExpiry,
    lowStock,
    stockoutRisk,
    overstocked,
    slowMoving,
    nearExpiry,
    highPriority,
  })

  return {
    ...product,
    analytics: {
      avgDailySales7: round(avgDailySales7),
      avgDailySales30: round(avgDailySales30),
      weightedAvgDailySales: round(weightedAvgDailySales),
      daysUntilStockout: Number.isFinite(daysUntilStockout) ? round(daysUntilStockout) : null,
      margin: round(product.price - product.cost),
      marginRate: product.price > 0 ? round((product.price - product.cost) / product.price) : 0,
      primaryStatus: pickPrimaryStatus(statuses),
      statuses,
      riskScore: calculateRiskScore({
        daysUntilStockout,
        leadTimeDays: product.leadTimeDays,
        nearExpiry,
        slowMoving,
        overstocked,
      }),
    },
  }
}

export function summarizeInventory(analyzedProducts) {
  const totals = analyzedProducts.reduce(
    (summary, product) => {
      const statuses = new Set(product.analytics.statuses)
      summary.totalProducts += 1
      summary.estimatedInventoryValue += product.currentStock * product.cost
      summary.totalSalesLast30Days += product.salesLast30Days

      if (statuses.has(statusLabels.stockoutRisk)) summary.stockoutRisks += 1
      if (statuses.has(statusLabels.lowStock)) summary.lowStock += 1
      if (statuses.has(statusLabels.overstocked)) summary.overstocked += 1
      if (statuses.has(statusLabels.nearExpiry)) summary.wasteRisk += 1
      if (statuses.has(statusLabels.highPriority)) summary.highPriority += 1

      return summary
    },
    {
      totalProducts: 0,
      stockoutRisks: 0,
      lowStock: 0,
      overstocked: 0,
      wasteRisk: 0,
      highPriority: 0,
      totalSalesLast30Days: 0,
      estimatedInventoryValue: 0,
    },
  )

  return {
    ...totals,
    estimatedInventoryValue: round(totals.estimatedInventoryValue),
  }
}

function collectStatuses(flags) {
  const statuses = Object.entries(flags)
    .filter(([, enabled]) => enabled)
    .map(([key]) => statusLabels[key])

  return statuses.length ? statuses : [statusLabels.healthy]
}

function pickPrimaryStatus(statuses) {
  const order = [
    statusLabels.highPriority,
    statusLabels.stockoutRisk,
    statusLabels.nearExpiry,
    statusLabels.lowStock,
    statusLabels.overstocked,
    statusLabels.slowMoving,
    statusLabels.healthy,
  ]

  return order.find((status) => statuses.includes(status)) ?? statusLabels.healthy
}

function calculateRiskScore({ daysUntilStockout, leadTimeDays, nearExpiry, slowMoving, overstocked }) {
  let score = 0

  if (!Number.isFinite(daysUntilStockout)) score += 8
  else if (daysUntilStockout <= leadTimeDays) score += 55
  else if (daysUntilStockout <= leadTimeDays + 2) score += 35

  if (nearExpiry) score += 25
  if (slowMoving) score += 10
  if (overstocked) score += 12

  return Math.min(100, score)
}

function isNearExpiry(expiryDate, currentDate) {
  if (!expiryDate) return false

  const reference = currentDate ? new Date(`${currentDate}T00:00:00Z`) : new Date()
  const expiry = new Date(`${expiryDate}T00:00:00Z`)
  if (Number.isNaN(expiry.getTime()) || Number.isNaN(reference.getTime())) return false

  const daysUntilExpiry = (expiry.getTime() - reference.getTime()) / 86_400_000
  return daysUntilExpiry >= 0 && daysUntilExpiry <= 7
}

function safeDivide(value, divisor) {
  return divisor === 0 ? 0 : value / divisor
}

function round(value) {
  return Math.round(value * 100) / 100
}
