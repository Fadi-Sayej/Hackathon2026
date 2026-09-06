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
import { COMPETITOR_STORES, OUR_STORE } from './data/marketData.js'
import { analyzeProducts, summarizeInventory } from './lib/analytics/inventoryEngine.js'
import { resolveVelocityConfidence } from './lib/analytics/velocityConfidence.js'
import { RECOMMENDATION_TYPES } from './lib/analytics/recommendationTypes.js'
import {
  generatePlanogram,
  groupPlanogramByShelf,
  summarizePlanogram,
} from './lib/analytics/planogramEngine.js'
import { aggregateNetValueAtStake, generateReorderRecommendations } from './lib/analytics/reorderEngine.js'
import {
  annotateRecommendationsWithExplanations,
  annotateRecommendationsWithMockExplanations,
  getDefaultExplanationProvider,
  getRemoteExplanationBudget,
} from './lib/ai/explanationProvider.js'
import { buildMarketContext } from './lib/context/marketContextAdapter.js'
import { loadMarketContext, toEngineContext } from './lib/dataAdapters/loadMarketContext.js'
import { toDemandFactors } from './lib/context/liveMarketContext.js'
import { computeDemand } from './lib/analytics/demandEngine.js'
import { MARKET_PARAM_REGISTRY, PRODUCT_ARCHETYPES } from './data/marketParams.js'
import { fallbackMarketContext } from './lib/context/fallbackMarketContext.js'
import { useI18n } from './lib/i18n/index.js'
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
import { ShelfPlanPage } from './pages/ShelfPlanPage.jsx'
import { StoreLayoutPage } from './pages/StoreLayoutPage.jsx'
import { PriceGapPage } from './pages/PriceGapPage.jsx'
import { AssortmentGapPage } from './pages/AssortmentGapPage.jsx'
import { ProductsPage } from './pages/ProductsPage.jsx'
import { RecommendationsPage } from './pages/RecommendationsPage.jsx'
import { ReportPage } from './pages/ReportPage.jsx'


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
  // Explanations are rendered per language, so the component needs the translator.
  const { t, language } = useI18n()
  const [activePage, setActivePage] = useState('operational')
  // The fixture the shelf plan is drawn for. Set from the layout editor; null
  // means the shelf plan falls back to the first gondola in the saved layout.
  const [planogramUnit, setPlanogramUnit] = useState(null)
  const [marketContext, setMarketContext] = useState(fallbackMarketContext)
  const [recommendationOverrides, setRecommendationOverrides] = useState(() =>
    loadRecommendationDecisions(),
  )
  const [storeData, setStoreData] = useState(initialStoreData)
  const [connectorStatus, setConnectorStatus] = useState({
    state: 'ready',
    messageKey: 'ds.demoLoaded',
  })
  const [operationalData, setOperationalData] = useState(EMPTY_OPERATIONAL_DATA)
  const [operationalStatus, setOperationalStatus] = useState('loading')

  // Decisions on the daily action list. Kept separate from reorder recommendation
  // overrides: these are operational alerts, and their dismissal reasons are the most
  // valuable thing the pilot collects — they tell us which alert types to keep.
  const [actionDecisions, setActionDecisions] = useState(() => loadRecommendationDecisions())

  const decideAction = (decision) => {
    const saved = saveRecommendationDecision({
      ...decision,
      source: 'operational',
      decidedAt: new Date().toISOString(),
    })
    setActionDecisions((current) => ({ ...current, [decision.id]: saved ?? decision }))
  }

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

    async function loadMarketContextEffect() {
      // Prefer the artifact the pipeline committed: it is what the recommender
      // actually decided on, so the screen and the order agree by construction.
      const artifact = await loadMarketContext()
      if (artifact) {
        if (!cancelled) setMarketContext(toEngineContext(artifact, fallbackMarketContext))
        return
      }
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

    loadMarketContextEffect()
    return () => {
      cancelled = true
    }
  }, [])

  const products = storeData.products

  // ── Data provenance (honest real-vs-demo signal for the UI) ────────
  // The catalog is "real" when it comes from the YomYom POS silver export
  // (products carry `ym-<barcode>` ids). Sales history is absent in the
  // current YomYom inventory snapshot, so velocity-derived metrics are
  // flagged rather than presented as observed demand.
  const dataProvenance = useMemo(() => {
    const isRealCatalog =
      storeData.connectorMode === CONNECTOR_MODES.DEMO &&
      products.some((product) => typeof product.id === 'string' && product.id.startsWith('ym-'))
    // Sales history is a property of velocity confidence, not of a sales sum.
    // Inferring it from salesLast30Days > 0 is exactly the "sold zero" vs. "no
    // history" conflation C-2a exists to remove, so derive it from the
    // confidence band instead. resolveVelocityConfidence always returns one of
    // the four levels, so every product lands in exactly one bucket and the
    // breakdown lets the UI state plainly how much history backs what it shows.
    const velocityBreakdown = { none: 0, low: 0, medium: 0, high: 0 }
    for (const product of products) {
      velocityBreakdown[resolveVelocityConfidence(product)] += 1
    }
    const salesHistoryCount =
      velocityBreakdown.low + velocityBreakdown.medium + velocityBreakdown.high
    const hasSalesHistory = salesHistoryCount > 0
    const competitorStoreCount = Array.isArray(COMPETITOR_STORES) ? COMPETITOR_STORES.length : 0
    return {
      catalog: isRealCatalog ? 'real' : storeData.connectorMode === CONNECTOR_MODES.CSV ? 'uploaded' : 'demo',
      catalogCount: products.length,
      catalogLabel: isRealCatalog
        ? 'Real YomYom POS catalog'
        : storeData.connectorMode === CONNECTOR_MODES.CSV
          ? `Uploaded CSV${storeData.fileName ? ` (${storeData.fileName})` : ''}`
          : 'Bundled demo sample',
      hasSalesHistory,
      salesHistoryCount,
      velocityBreakdown,
      competitor: competitorStoreCount > 0 ? 'real' : 'none',
      competitorStoreCount,
      liveMarketContext: marketContext.sourceLabel === 'live',
    }
  }, [products, storeData.connectorMode, storeData.fileName, marketContext.sourceLabel])

  // ── Hyper-Local Competitor Intelligence (plugin) ───────────────────
  // Real competitor data from Kaggle (Dor Alon, Rami Levy, Shufersal).
  // Filters competitor stores to a 3 km radius first (real stores are
  // 1.4–2.1 km from our Kafr Qasim location), pivots them into a
  // barcode-keyed market snapshot, then enriches our catalog with
  // price + stock intelligence flags.
  const nearbyCompetitors = useMemo(
    () => filterStoresByRadius(COMPETITOR_STORES, OUR_STORE.coords, 3000),
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

  // analyzeProducts resolves each product's velocity confidence and records it
  // under analytics.velocityConfidence. C-6 emits product.velocityConfidence
  // upstream, but the product adapter does not yet carry it into the runtime
  // shape, so analytics.velocityConfidence is the reliable source. Mirroring it
  // back to the top level keeps the C-0 contract's §2 promise true and hands
  // generateReorderRecommendations the same band the inventory engine used —
  // this is the single point where velocity confidence is threaded through the
  // rest of the chain (recommendations, dashboardStats, and the pages).
  const analyzedProducts = useMemo(
    () =>
      analyzeProducts(enrichedProducts, enrichedMarketContext).map((product) => ({
        ...product,
        velocityConfidence: product.analytics.velocityConfidence,
      })),
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

  // Today's external factors, as intensities the demand engine can weigh. Derived
  // from the live context (weather + both calendars); an absent factor is simply
  // missing from the map and contributes nothing.
  const demandFactors = useMemo(
    () => toDemandFactors(enrichedMarketContext),
    [enrichedMarketContext],
  )

  const baseRecommendations = useMemo(
    () => generateReorderRecommendations(analyzedProducts, enrichedMarketContext),
    [analyzedProducts, enrichedMarketContext],
  )

  // Attach the demand decomposition to each recommendation: which factors moved it
  // and by how much. This is what turns 109 parameters into something debuggable,
  // and it gives the explanation layer real evidence instead of generic phrasing.
  //
  // Product profiles (#51) are not available yet, so every product resolves to the
  // `unclassified` archetype — which is inert by design. The engine still runs, and
  // starts producing per-product effects the moment classification lands, with no
  // change here.
  const generatedRecommendations = useMemo(() => {
    if (!Object.keys(demandFactors).length) return baseRecommendations
    return baseRecommendations.map((recommendation) => {
      const product = productIndex.get(recommendation.productId)
      const demand = computeDemand({
        product: product ?? { id: recommendation.productId },
        profile: product?.profile ?? null,
        archetypes: PRODUCT_ARCHETYPES,
        registry: MARKET_PARAM_REGISTRY,
        factors: demandFactors,
      })
      if (demand.demandIndex === 1 && !demand.blocked) return recommendation
      return {
        ...recommendation,
        demandIndex: demand.demandIndex,
        topDrivers: demand.topDrivers,
        gatesEvaluated: demand.gatesEvaluated,
        // A fired gate outranks whatever the reorder engine concluded — no amount
        // of demand makes a blocked product orderable.
        ...(demand.blocked
          ? { urgency: 'HIGH', reason: demand.blocked.reason ?? recommendation.reason }
          : null),
      }
    })
  }, [baseRecommendations, demandFactors, productIndex])
  const mockRecommendations = useMemo(
    () =>
      annotateRecommendationsWithMockExplanations({
        products: analyzedProducts,
        recommendations: generatedRecommendations,
        marketContext: enrichedMarketContext,
        // Explanations are rendered in the reader's language, so they must be
        // rebuilt when he switches it.
        t,
        language,
      }),
    [analyzedProducts, generatedRecommendations, enrichedMarketContext, t, language],
  )
  const [upgradedRecommendations, setUpgradedRecommendations] = useState(null)

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()
    const provider = getDefaultExplanationProvider()

    // Mock explanations are already visible from mockRecommendations. When no
    // remote provider is configured, there is nothing asynchronous to upgrade.
    if (provider.id === 'mock') {
      return () => {
        cancelled = true
        controller.abort()
      }
    }

    async function upgradeExplanations() {
      try {
        const nextRecommendations = await annotateRecommendationsWithExplanations({
          provider,
          products: analyzedProducts,
          recommendations: generatedRecommendations,
          marketContext: enrichedMarketContext,
          maxRemoteExplanations: getRemoteExplanationBudget(),
          signal: controller.signal,
        })
        if (!cancelled) {
          setUpgradedRecommendations({
            source: generatedRecommendations,
            recommendations: nextRecommendations,
          })
        }
      } catch {
        // The synchronous mock batch remains visible if an unexpected batch-level
        // failure escapes the provider's per-recommendation fallback.
      }
    }

    upgradeExplanations()
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [analyzedProducts, generatedRecommendations, enrichedMarketContext])

  const explainedRecommendations =
    upgradedRecommendations?.source === generatedRecommendations
      ? upgradedRecommendations.recommendations
      : mockRecommendations

  const recommendations = useMemo(
    () =>
      explainedRecommendations.map((recommendation) => {
        const key = getRecommendationKey(recommendation)
        const override = recommendationOverrides[key] ?? {}
        return {
          ...recommendation,
          status: override.status ?? recommendation.status,
          recommendedOrderQuantity:
            override.recommendedOrderQuantity ?? recommendation.recommendedOrderQuantity,
        }
      }),
    [explainedRecommendations, recommendationOverrides],
  )

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
    setConnectorStatus({ state: 'ready', messageKey: 'ds.demoLoaded' })
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

  // The context multiplier per product, for the shelf-space allocator. Same
  // decomposition the recommendations already carry, keyed by product id.
  const demandIndexById = useMemo(() => {
    const index = {}
    for (const recommendation of generatedRecommendations) {
      if (typeof recommendation.demandIndex === 'number') {
        index[recommendation.productId] = recommendation.demandIndex
      }
    }
    return index
  }, [generatedRecommendations])

  const pageProps = {
    approvedOrders,
    demandIndexById,
    planogramUnit,
    onOpenUnit: (unit) => {
      setPlanogramUnit(unit)
      setActivePage('shelf-plan')
    },
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
    dataProvenance,
    operationalData,
    operationalStatus,
    products: analyzedProducts,
    decisions: actionDecisions,
    onDecide: decideAction,
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
      dataProvenance={dataProvenance}
      hasDemoState={Object.keys(recommendationOverrides).length > 0}
      onResetDemoState={handleResetDemoState}
      onNavigate={setActivePage}
    >
      {activePage === 'dashboard' && <DashboardPage {...pageProps} />}
      {activePage === 'products' && <ProductsPage {...pageProps} />}
      {activePage === 'recommendations' && <RecommendationsPage {...pageProps} />}
      {activePage === 'operational' && <OperationalPage {...pageProps} />}
      {activePage === 'expiry' && <ExpiryPage {...pageProps} />}
      {activePage === 'prices' && <PriceGapPage {...pageProps} />}
      {activePage === 'assortment' && <AssortmentGapPage {...pageProps} />}
      {activePage === 'planogram' && <PlanogramPage {...pageProps} />}
      {activePage === 'store-layout' && <StoreLayoutPage {...pageProps} />}
      {activePage === 'shelf-plan' && <ShelfPlanPage {...pageProps} />}
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
  // A rejected recommendation is off the table; everything else is a live
  // opportunity the manager can still act on, which is what the dashboard
  // summarizes and what PLAN.md §5 measures the pilot on.
  const live = recommendations.filter((recommendation) => recommendation.status !== 'REJECTED')
  const countByType = (type) => live.filter((recommendation) => recommendation.type === type).length

  const reorderRecommendations = live.filter(
    (recommendation) => recommendation.type === RECOMMENDATION_TYPES.REORDER,
  )
  const estimatedOrderCost = reorderRecommendations.reduce((sum, recommendation) => {
    const product = analyzedProducts.find((item) => item.id === recommendation.productId)
    return sum + (recommendation.recommendedOrderQuantity ?? 0) * (product?.cost ?? 0)
  }, 0)

  // Net ₪ at stake is the headline the pilot is graded on (PLAN.md §5). It is
  // *deduplicated product exposure* (Issue #30), not a gross sum of action-item
  // values: a product that trips several signals — e.g. BELOW_COST and PRICE_GAP
  // on the same stock, which prescribe opposite price fixes — is counted once, by
  // its greatest single-signal value, so the figure can't be mistaken for (or
  // inflated past) the store's true unique exposure. Per-recommendation
  // valueAtStake still ranks the action list; see aggregateNetValueAtStake.
  const productValueAtStake = aggregateNetValueAtStake(live)

  return {
    ...inventorySummary,
    estimatedOrderCost: round2(estimatedOrderCost),
    highRiskStockouts: inventorySummary.stockoutRisks,
    // REORDER stays 0 until real velocity exists; the four types below are the
    // ones actually on screen today, so the dashboard counts must match them.
    reorderSuggestions: reorderRecommendations.length,
    belowCostAlerts: countByType(RECOMMENDATION_TYPES.BELOW_COST),
    priceGapAlerts: countByType(RECOMMENDATION_TYPES.PRICE_GAP),
    negativeStockAlerts: countByType(RECOMMENDATION_TYPES.NEGATIVE_STOCK),
    thinMarginAlerts: countByType(RECOMMENDATION_TYPES.THIN_MARGIN),
    actionableRecommendations: live.length,
    // Renamed from `valueAtStake` (#30): the old name read as unique net
    // exposure but was a gross per-recommendation sum. This is deduplicated
    // per-product net exposure. (Computed for the PLAN §5 headline; not yet
    // rendered — no dashboard label to update.)
    productValueAtStake: round2(productValueAtStake),
  }
}

function round2(value) {
  return Math.round(value * 100) / 100
}

export default App
