import { nonNegativeNumber } from './validation.js'

export function normalizeSales(rawProduct, issues = []) {
  const sales = rawProduct.sales ?? rawProduct

  return {
    salesLast7Days: nonNegativeNumber(
      sales.salesLast7Days ?? sales.last7Days ?? sales.units7d,
      0,
      'salesLast7Days',
      issues,
    ),
    salesLast30Days: nonNegativeNumber(
      sales.salesLast30Days ?? sales.last30Days ?? sales.units30d,
      0,
      'salesLast30Days',
      issues,
    ),
  }
}
