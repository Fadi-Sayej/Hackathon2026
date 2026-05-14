import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { analyzeProducts, summarizeInventory } from './lib/analytics/inventoryEngine.js'
import {
  generatePlanogram,
  groupPlanogramByShelf,
  summarizePlanogram,
} from './lib/analytics/planogramEngine.js'
import { generateReorderRecommendations } from './lib/analytics/reorderEngine.js'
import {
  annotateRecommendationsWithExplanations,
  getDefaultExplanationProvider,
} from './lib/ai/explanationProvider.js'
import { buildMarketContext } from './lib/context/marketContextAdapter.js'
import { fallbackMarketContext } from './lib/context/fallbackMarketContext.js'
import { loadDemoStoreData } from './lib/dataAdapters/loadDemoStoreData.js'
import {
  loadRecommendationDecisions,
  resetDemoState,
  saveApprovedOrder,
  saveRecommendationDecision,
} from './lib/persistence/persistence.js'
import { AppShell } from './components/layout/AppShell.jsx'
import { ApprovedOrdersPage } from './pages/ApprovedOrdersPage.jsx'
import { DashboardPage } from './pages/DashboardPage.jsx'
import { PlanogramPage } from './pages/PlanogramPage.jsx'
import { ProductsPage } from './pages/ProductsPage.jsx'
import { RecommendationsPage } from './pages/RecommendationsPage.jsx'

const pageMeta = {
  dashboard: {
    title: 'Inventory Intelligence',
    description: 'AI-assisted operating view for stock risk, reorder pressure, and market context.',
  },
  products: {
    title: 'Product Health',
    description: 'Search, filter, and compare every SKU by stock status and sales velocity.',
  },
  recommendations: {
    title: 'Smart Reorder',
    description: 'Manager approval workflow for AI-assisted purchasing recommendations.',
  },
  planogram: {
    title: 'Shelf Optimization',
    description: 'A visual planogram generated from sales velocity, margin, risk, and shelf capacity.',
  },
  orders: {
    title: 'Approved Orders',
    description: 'Purchase-order style summary for approved replenishment actions.',
  },
}

function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const [marketContext, setMarketContext] = useState(fallbackMarketContext)
  const [recommendationOverrides, setRecommendationOverrides] = useState(() =>
    loadRecommendationDecisions(),
  )

  useEffect(() => {
    let cancelled = false

    async function loadMarketContext() {
      const nextContext = await buildMarketContext({
        enableLive: import.meta.env.VITE_ENABLE_LIVE_MARKET_CONTEXT === 'true',
        countryCode: import.meta.env.VITE_HOLIDAY_COUNTRY,
        location: {
          lat: import.meta.env.VITE_WEATHER_LAT,
          lon: import.meta.env.VITE_WEATHER_LON,
        },
        query: import.meta.env.VITE_NEWS_QUERY,
      })
      if (!cancelled) setMarketContext(nextContext)
    }

    loadMarketContext()
    return () => {
      cancelled = true
    }
  }, [])

  const storeData = useMemo(() => loadDemoStoreData(), [])
  const products = storeData.products
  const analyzedProducts = useMemo(
    () => analyzeProducts(products, marketContext),
    [products, marketContext],
  )
  const inventorySummary = useMemo(() => summarizeInventory(analyzedProducts), [analyzedProducts])
  const productIndex = useMemo(
    () => new Map(products.map((product) => [product.id, product])),
    [products],
  )

  const recommendations = useMemo(() => {
    const baseRecommendations = annotateRecommendationsWithExplanations({
      provider: getDefaultExplanationProvider(),
      products,
      recommendations: generateReorderRecommendations(products, marketContext),
      marketContext,
    })

    return baseRecommendations.map((recommendation) => {
      const key = getRecommendationKey(recommendation)
      const override = recommendationOverrides[key] ?? {}
      return {
        ...recommendation,
        status: override.status ?? recommendation.status,
        recommendedOrderQuantity:
          override.recommendedOrderQuantity ?? recommendation.recommendedOrderQuantity,
      }
    })
  }, [marketContext, products, recommendationOverrides])

  const planogramItems = useMemo(
    () => generatePlanogram(analyzedProducts, marketContext),
    [analyzedProducts, marketContext],
  )
  const shelfGroups = useMemo(() => groupPlanogramByShelf(planogramItems), [planogramItems])
  const planogramSummary = useMemo(() => summarizePlanogram(planogramItems), [planogramItems])

  const approvedOrders = useMemo(
    () => recommendations.filter((recommendation) => recommendation.status === 'APPROVED'),
    [recommendations],
  )

  const dashboardStats = useMemo(
    () => buildDashboardStats({
      analyzedProducts,
      inventorySummary,
      recommendations,
    }),
    [analyzedProducts, inventorySummary, recommendations],
  )

  function updateRecommendation(recommendation, changes) {
    const key = getRecommendationKey(recommendation)
    const decision = {
      id: key,
      productId: recommendation.productId,
      productName: recommendation.productName,
      type: recommendation.type,
      status: changes.status ?? recommendation.status,
      recommendedOrderQuantity:
        changes.recommendedOrderQuantity ?? recommendation.recommendedOrderQuantity,
    }

    saveRecommendationDecision(decision)
    if (decision.status === 'APPROVED') {
      saveApprovedOrder(decision)
    }

    setRecommendationOverrides((current) => ({
      ...current,
      [key]: {
        ...(current[key] ?? {}),
        ...changes,
      },
    }))
  }

  function handleResetDemoState() {
    resetDemoState()
    setRecommendationOverrides({})
    setActivePage('dashboard')
  }

  const pageProps = {
    approvedOrders,
    analyzedProducts,
    dashboardStats,
    inventorySummary,
    marketContext,
    planogramItems,
    planogramSummary,
    productIndex,
    recommendations,
    shelfGroups,
    onApprove: (recommendation) =>
      updateRecommendation(recommendation, {
        status: 'APPROVED',
        recommendedOrderQuantity: normalizeOrderQuantity(
          recommendation.recommendedOrderQuantity,
        ),
      }),
    onEditQuantity: (recommendation, recommendedOrderQuantity) =>
      updateRecommendation(recommendation, {
        status: recommendation.status === 'APPROVED' ? 'APPROVED' : 'EDITED',
        recommendedOrderQuantity: normalizeOrderQuantity(recommendedOrderQuantity),
      }),
    onReject: (recommendation) => updateRecommendation(recommendation, { status: 'REJECTED' }),
  }

  return (
    <AppShell
      activePage={activePage}
      hasDemoState={Object.keys(recommendationOverrides).length > 0}
      onResetDemoState={handleResetDemoState}
      pageMeta={pageMeta[activePage]}
      onNavigate={setActivePage}
    >
      {activePage === 'dashboard' && <DashboardPage {...pageProps} />}
      {activePage === 'products' && <ProductsPage {...pageProps} />}
      {activePage === 'recommendations' && <RecommendationsPage {...pageProps} />}
      {activePage === 'planogram' && <PlanogramPage {...pageProps} />}
      {activePage === 'orders' && <ApprovedOrdersPage {...pageProps} />}
    </AppShell>
  )
}

function getRecommendationKey(recommendation) {
  return `${recommendation.productId}:${recommendation.type}`
}

function normalizeOrderQuantity(quantity) {
  const parsedQuantity = Number(quantity)
  if (!Number.isFinite(parsedQuantity)) return 1
  return Math.max(1, Math.round(parsedQuantity))
}

function buildDashboardStats({ analyzedProducts, inventorySummary, recommendations }) {
  const reorderSuggestions = recommendations.filter((recommendation) => recommendation.type === 'REORDER')
  const estimatedOrderCost = reorderSuggestions.reduce((sum, recommendation) => {
    const product = analyzedProducts.find((item) => item.id === recommendation.productId)
    return sum + (recommendation.recommendedOrderQuantity ?? 0) * (product?.cost ?? 0)
  }, 0)

  return {
    ...inventorySummary,
    estimatedOrderCost: Math.round(estimatedOrderCost * 100) / 100,
    highRiskStockouts: inventorySummary.stockoutRisks,
    reorderSuggestions: reorderSuggestions.length,
  }
}

export default App
