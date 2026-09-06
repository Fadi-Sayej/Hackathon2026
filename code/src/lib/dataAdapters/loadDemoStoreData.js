import { demoProducts } from '../../data/demoProducts.js'
import { normalizeProducts } from './productAdapter.js'

export function loadDemoStoreData(rawProducts = demoProducts) {
  const { products, issues } = normalizeProducts(rawProducts)

  return {
    products,
    validationIssues: issues,
    source: {
      type: 'local-demo',
      productCount: products.length,
      generatedAt: new Date().toISOString(),
    },
  }
}
