# Library Exports (generated 2026-08-02)
# fn=function, class=class. Type-only files omitted.

## src/lib/ai
explanationProvider.js
  fn annotateRecommendationsWithExplanations
  fn getDefaultExplanationProvider
  fn getLLMExplanationProviderStatus
llmExplanationProvider.js  fn buildLLMExplanationPayload
reportBuilder.js  fn buildOptimizationReport

## src/lib/analytics
affinityEngine.js
  fn generateCrossMerchandisingSuggestions
  fn summarizeAffinity
competitorEngine.js
  fn getCompetitorDemandBoost
  fn analyzeLocalMarket
  fn buildCompetitorBoostMap
  fn buildPriceAdvantageSet
  +4 more
complianceEngine.js
  fn analyzeCompliance
  fn generateMockDetectedShelf
inventoryEngine.js
  fn analyzeProducts
  fn analyzeProduct
  fn summarizeInventory
mockAI.js
  fn generateMockAIExplanation
  fn annotateRecommendations
planogramEngine.js
  fn generatePlanogram
  fn groupPlanogramByShelf
  fn summarizePlanogram
reorderEngine.js
  fn generateReorderRecommendations
  fn computeMetrics

## src/lib/context
holidays.js
  fn fetchPublicHolidays
  fn getHolidayForDate
  fn getNearbyHoliday
marketContextAdapter.js
  fn fetchWeatherContext
  fn fetchHolidayContext
  fn fetchEventContext
  fn buildMarketContext
news.js
  fn fetchNewsHeadlines
  fn hasDemandSignal
weather.js
  fn fetchCurrentWeather
  fn classifyWeather
liveMarketContext.js  fn buildLiveMarketContext

## src/lib/dataAdapters
multiCompetitorAdapter.js
  fn parseRetailXML
  fn buildSnapshot
  fn detectStockouts
  fn buildLocalMarketSnapshot
productAdapter.js
  fn normalizeProduct
  fn normalizeProducts
validation.js
  fn createIssue
  fn requiredString
  fn nonNegativeNumber
  fn positiveNumber
  +2 more
inventoryAdapter.js  fn normalizeInventory
loadDemoStoreData.js  fn loadDemoStoreData
loadOperationalData.js  fn loadOperationalData
salesAdapter.js  fn normalizeSales

## src/lib/persistence
localStorageAdapter.js
  fn saveApprovedOrder
  fn listApprovedOrders
  fn saveRecommendationDecision
  fn loadRecommendationDecisions
  +2 more
persistence.js
  fn saveApprovedOrder
  fn listApprovedOrders
  fn saveRecommendationDecision
  fn loadRecommendationDecisions
  +2 more

## src/lib/posConnectors
csvConnector.js
  fn parseCsv
  fn createCsvConnector
comaxConnectorStub.js  fn createComaxConnectorStub
demoDataConnector.js  fn createDemoDataConnector
index.js  fn createConnector
posConnectorInterface.js  fn mergeFeedsById

## src/lib/utils
geoUtils.js
  fn getDistanceMeters
  fn filterStoresByRadius
