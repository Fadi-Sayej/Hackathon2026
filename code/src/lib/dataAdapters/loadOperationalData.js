// Loads pipeline-derived operational data exported by scripts/export_dashboard_data.py
// into public/data/operational.json. Degrades gracefully when the file is missing or
// the scraping/import pipeline has not produced data yet.

export const EMPTY_OPERATIONAL_DATA = {
  meta: {
    generatedAt: null,
    status: 'unavailable',
    competitorSignals: 0,
    competitorRecommendations: 0,
    scrapingStatus: 'not_started',
  },
  posHealth: {
    totalProducts: 0,
    missingBarcode: 0,
    zeroPrice: 0,
    zeroCost: 0,
    negativeStock: 0,
    woltPriceGaps: 0,
    marginRisks: 0,
    sourceFile: null,
  },
  expiry: {
    totalScans: 0,
    actionable: 0,
    buckets: { expired: 0, critical_7d: 0, warning_14d: 0, upcoming_30d: 0, later: 0 },
    alerts: [],
  },
  byType: {},
  byFamily: {},
  sources: [],
  recommendations: [],
}

export async function loadOperationalData() {
  const url = `${import.meta.env.BASE_URL}data/operational.json`
  try {
    const response = await fetch(url, { cache: 'no-store' })
    if (!response.ok) return { ...EMPTY_OPERATIONAL_DATA }
    const data = await response.json()
    return {
      ...EMPTY_OPERATIONAL_DATA,
      ...data,
      meta: { ...EMPTY_OPERATIONAL_DATA.meta, ...(data.meta ?? {}) },
      posHealth: { ...EMPTY_OPERATIONAL_DATA.posHealth, ...(data.posHealth ?? {}) },
      expiry: { ...EMPTY_OPERATIONAL_DATA.expiry, ...(data.expiry ?? {}) },
      byType: data.byType ?? {},
      byFamily: data.byFamily ?? {},
      sources: Array.isArray(data.sources) ? data.sources : [],
      recommendations: Array.isArray(data.recommendations) ? data.recommendations : [],
    }
  } catch {
    return { ...EMPTY_OPERATIONAL_DATA }
  }
}
