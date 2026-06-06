import { useEffect, useMemo, useState } from 'react'
import './App.css'
import {
  generateCrossMerchandisingSuggestions,
  summarizeAffinity,
} from './lib/analytics/affinityEngine.js'
import {
  analyzeLocalMarket,
  buildCompetitorBoostMap,
  buildPriceAdvantageSet,
  selectPriceLeaders,
  selectPriceProtectionAlerts,
  selectStockoutOpportunities,
  summarizeCompetitorIntelligence,
} from './lib/analytics/competitorEngine.js'
import { buildLocalMarketSnapshot } from './lib/dataAdapters/multiCompetitorAdapter.js'
import { filterStoresByRadius } from './lib/utils/geoUtils.js'
import { COMPETITOR_STORES, OUR_STORE } from './data/mockMarketData.js'
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
  CONNECTOR_MODES,
  createComaxConnectorStub,
  createCsvConnector,
  createDemoDataConnector,
} from './lib/posConnectors/index.js'
import {
  loadRecommendationDecisions,
  resetDemoState,
  saveApprovedOrder,
  saveRecommendationDecision,
} from './lib/persistence/persistence.js'
import { loadOperationalData, EMPTY_OPERATIONAL_DATA } from './lib/dataAdapters/loadOperationalData.js'
import { AppShell } from './components/layout/AppShell.jsx'
import { ApprovedOrdersPage } from './pages/ApprovedOrdersPage.jsx'
import { DashboardPage } from './pages/DashboardPage.jsx'
import { OperationalPage } from './pages/OperationalPage.jsx'
import { ExpiryPage } from './pages/ExpiryPage.jsx'
import { DataSourcePage } from './pages/DataSourcePage.jsx'
import { PlanogramPage } from './pages/PlanogramPage.jsx'
import { ProductsPage } from './pages/ProductsPage.jsx'
import { RecommendationsPage } from './pages/RecommendationsPage.jsx'
import { ReportPage } from './pages/ReportPage.jsx'

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
  operational: {
    title: 'Operational Risks',
    description: 'Live POS-derived risks: expiry, WOLT price gaps, margins, negative stock, and unknown barcodes.',
  },
  expiry: {
    title: 'Expiry Tracking',
    description: 'Record barcode + expiry date at receiving and monitor items nearing or past expiry.',
  },
  planogram: {
    title: 'Shelf Optimization',
    description: 'A visual planogram generated from sales velocity, margin, risk, and shelf capacity.',
  },
  report: {
    title: 'AI Report',
    description: 'Generate a comprehensive AI-powered optimization report with actionable insights.',
  },
  orders: {
    title: 'Approved Orders',
    description: 'Purchase-order style summary for approved replenishment actions.',
  },
  'data-source': {
    title: 'Data Source',
    description: 'Choose between bundled demo data, a CSV export, or a future Comax POS feed.',
  },
}

function initialStoreData() {
  const data = loadDemoStoreData()
  return {
    products: data.products,
    validationIssues: data.validationIssues,
    source: data.source,
    connectorMode: CONNECTOR_MODES.DEMO,
    fileName: null,
    loadedAt: new Date().toISOString(),
  }
}

function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const [marketContext, setMarketContext] = useState(fallbackMarketContext)
  const [recommendationOverrides, setRecommendationOverrides] = useState(() =>
    loadRecommendationDecisions(),
  )
  const [storeData, setStoreData] = useState(initialStoreData)
  const [connectorStatus, setConnectorStatus] = useState({
    state: 'ready',
    message: 'Demo dataset loaded.',
  })
  const [operationalData, setOperationalData] = useState(EMPTY_OPERATIONAL_DATA)
  const [operationalStatus, setOperationalStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false
    loadOperationalData().then((data) => {
      if (cancelled) return
      setOperationalData(data)
      setOperationalStatus('ready')
    })
    return () => {
      cancelled = true
    }
  }, [])

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

  const products = storeData.products

  // ── Hyper-Local Competitor Intelligence (plugin) ───────────────────
  // Mock-only during the hackathon demo. Filters competitor stores to the
  // 1 km radius first, pivots them into a barcode-keyed market snapshot,
  // then enriches our catalog with price + stock intelligence flags.
  const nearbyCompetitors = useMemo(
    () => filterStoresByRadius(COMPETITOR_STORES, OUR_STORE.coords, 1000),
    [],
  )
  const localMarketSnapshot = useMemo(
    () => buildLocalMarketSnapshot(nearbyCompetitors),
    [nearbyCompetitors],
  )
  const enrichedProducts = useMemo(
    () => analyzeLocalMarket(products, localMarketSnapshot),
    [products, localMarketSnapshot],
  )
  const competitorBoosts = useMemo(
    () => buildCompetitorBoostMap(enrichedProducts),
    [enrichedProducts],
  )
  const competitorPriceAdvantage = useMemo(
    () => buildPriceAdvantageSet(enrichedProducts),
    [enrichedProducts],
  )

  // Merge competitor signals into marketContext so the existing engines
  // pick them up through their optional context fields. Default behavior
  // (no boost map → no advantage set) keeps every engine output identical
  // to before this feature when the maps are empty.
  const enrichedMarketContext = useMemo(
    () => ({
      ...marketContext,
      competitorBoosts,
      competitorPriceAdvantage,
    }),
    [marketContext, competitorBoosts, competitorPriceAdvantage],
  )

  const analyzedProducts = useMemo(
    () => analyzeProducts(enrichedProducts, enrichedMarketContext),
    [enrichedProducts, enrichedMarketContext],
  )

  const competitorSummary = useMemo(
    () => summarizeCompetitorIntelligence(analyzedProducts),
    [analyzedProducts],
  )
  const priceLeaderProducts = useMemo(
    () => selectPriceLeaders(analyzedProducts),
    [analyzedProducts],
  )
  const stockoutOpportunities = useMemo(
    () => selectStockoutOpportunities(analyzedProducts),
    [analyzedProducts],
  )
  const priceProtectionAlerts = useMemo(
    () => selectPriceProtectionAlerts(analyzedProducts),
    [analyzedProducts],
  )
  const inventorySummary = useMemo(() => summarizeInventory(analyzedProducts), [analyzedProducts])
  const productIndex = useMemo(
    () => new Map(products.map((product) => [product.id, product])),
    [products],
  )

  const recommendations = useMemo(() => {
    const baseRecommendations = annotateRecommendationsWithExplanations({
      provider: getDefaultExplanationProvider(),
      products: analyzedProducts,
      recommendations: generateReorderRecommendations(analyzedProducts, enrichedMarketContext),
      marketContext: enrichedMarketContext,
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
  }, [analyzedProducts, enrichedMarketContext, recommendationOverrides])

  const planogramItems = useMemo(
    () => generatePlanogram(analyzedProducts, enrichedMarketContext),
    [analyzedProducts, enrichedMarketContext],
  )
  const shelfGroups = useMemo(() => groupPlanogramByShelf(planogramItems), [planogramItems])
  const planogramSummary = useMemo(() => summarizePlanogram(planogramItems), [planogramItems])
  const affinitySuggestions = useMemo(
    () => generateCrossMerchandisingSuggestions(analyzedProducts, planogramItems),
    [analyzedProducts, planogramItems],
  )
  const affinitySummary = useMemo(() => summarizeAffinity(affinitySuggestions), [affinitySuggestions])

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
    setStoreData(initialStoreData())
    setConnectorStatus({ state: 'ready', message: 'Demo dataset loaded.' })
    setActivePage('dashboard')
  }

  async function applyConnector(connector, { fileName = null } = {}) {
    setConnectorStatus({ state: 'loading', message: `Connecting to ${connector.label}...` })
    try {
      const probe = await connector.connect()
      if (!probe.ok) {
        setConnectorStatus({
          state: 'error',
          message: probe.message,
          hint: probe.hint,
          mode: connector.mode,
        })
        return false
      }
      const next = await connector.load()
      setStoreData({
        products: next.products,
        validationIssues: next.validationIssues,
        source: next.source,
        connectorMode: connector.mode,
        fileName: fileName ?? next.source?.fileName ?? null,
        loadedAt: new Date().toISOString(),
      })
      setRecommendationOverrides({})
      setConnectorStatus({
        state: 'ready',
        message: probe.message,
        mode: connector.mode,
      })
      return true
    } catch (error) {
      setConnectorStatus({
        state: 'error',
        message: error?.message ?? 'Failed to load data source.',
        hint: error?.hint,
        mode: connector.mode,
      })
      return false
    }
  }

  async function handleSelectDemoSource() {
    await applyConnector(createDemoDataConnector())
  }

  async function handleSelectCsvSource(file) {
    if (!file) return false
    const connector = createCsvConnector({ file })
    return applyConnector(connector, { fileName: file.name })
  }

  async function handleSelectComaxSource() {
    await applyConnector(createComaxConnectorStub())
  }

  const pageProps = {
    approvedOrders,
    affinitySuggestions,
    affinitySummary,
    analyzedProducts,
    competitorSummary,
    dashboardStats,
    inventorySummary,
    marketContext,
    planogramItems,
    planogramSummary,
    priceLeaderProducts,
    priceProtectionAlerts,
    productIndex,
    recommendations,
    shelfGroups,
    stockoutOpportunities,
    storeData,
    connectorStatus,
    operationalData,
    operationalStatus,
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
    onSelectDemoSource: handleSelectDemoSource,
    onSelectCsvSource: handleSelectCsvSource,
    onSelectComaxSource: handleSelectComaxSource,
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
      {activePage === 'operational' && <OperationalPage {...pageProps} />}
      {activePage === 'expiry' && <ExpiryPage {...pageProps} />}
      {activePage === 'planogram' && <PlanogramPage {...pageProps} />}
      {activePage === 'report' && <ReportPage {...pageProps} />}
      {activePage === 'orders' && <ApprovedOrdersPage {...pageProps} />}
      {activePage === 'data-source' && <DataSourcePage {...pageProps} />}
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
