import { useCallback, useState } from 'react'
import { Button } from '../components/shared/Button.jsx'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { ReportViewer } from '../components/reports/ReportViewer.jsx'
import { buildOptimizationReport } from '../lib/ai/reportBuilder.js'

export function ReportPage({
  analyzedProducts,
  competitorSummary,
  dashboardStats,
  inventorySummary,
  marketContext,
  planogramItems,
  planogramSummary,
  recommendations,
  affinitySuggestions,
}) {
  const [report, setReport] = useState(null)
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerate = useCallback(async () => {
    const proxyUrl = import.meta.env.VITE_LLM_PROXY_URL
    setIsGenerating(true)
    setReport(null)

    if (!proxyUrl) {
      setTimeout(() => {
        setReport(buildOptimizationReport({
          analyzedProducts, competitorSummary, dashboardStats, inventorySummary,
          marketContext, planogramItems, planogramSummary, recommendations, affinitySuggestions,
        }))
        setIsGenerating(false)
      }, 2200)
      return
    }

    try {
      const payload = {
        productCount: analyzedProducts?.length ?? 0,
        reorderAlerts: recommendations?.filter(r => r.type === 'REORDER').length ?? 0,
        topReorders: recommendations?.filter(r => r.type === 'REORDER').slice(0, 5).map(r => ({
          name: r.productName,
          urgency: r.urgencyScore,
          reason: r.reason,
        })) ?? [],
        lowStockCount: analyzedProducts?.filter(p => p.inventoryStatus === 'critical').length ?? 0,
        competitorSignals: competitorSummary?.priceLeaderCount ?? 0,
        wasteAlerts: dashboardStats?.wasteAlerts ?? 0,
        categories: [...new Set(analyzedProducts?.map(p => p.category).filter(Boolean))].slice(0, 8),
        topAffinities: affinitySuggestions?.slice(0, 3).map(s => s.label) ?? [],
      }

      const response = await fetch(proxyUrl.replace('/explain', '/report'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) throw new Error(`Proxy error: ${response.status}`)
      const result = await response.json()

      setReport(result.report ?? buildOptimizationReport({
        analyzedProducts, competitorSummary, dashboardStats, inventorySummary,
        marketContext, planogramItems, planogramSummary, recommendations, affinitySuggestions,
      }))
    } catch (err) {
      console.warn('LLM report failed, falling back to rule-based:', err)
      setReport(buildOptimizationReport({
        analyzedProducts, competitorSummary, dashboardStats, inventorySummary,
        marketContext, planogramItems, planogramSummary, recommendations, affinitySuggestions,
      }))
    } finally {
      setIsGenerating(false)
    }
  }, [analyzedProducts, competitorSummary, dashboardStats, inventorySummary, marketContext,
      planogramItems, planogramSummary, recommendations, affinitySuggestions])

  return (
    <>
      <section className="metric-grid metric-grid-compact">
        <MetricCard
          label="Products Analyzed"
          value={analyzedProducts?.length ?? 0}
          detail="SKUs in current dataset"
        />
        <MetricCard
          label="Reorder Alerts"
          value={recommendations?.filter((r) => r.type === 'REORDER').length ?? 0}
          detail="Pending reorder suggestions"
          tone="warning"
        />
        <MetricCard
          label="Planogram Items"
          value={planogramSummary?.totalItems ?? 0}
          detail="Products with shelf placement"
          tone="success"
        />
        <MetricCard
          label="Competitor Signals"
          value={(competitorSummary?.priceLeaderCount ?? 0) + (competitorSummary?.competitorOOSCount ?? 0)}
          detail="Active market intelligence"
          tone="info"
        />
      </section>

      <section className="panel report-launch-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">AI Report Engine</p>
            <h2>Shelf Optimization Report</h2>
            <p className="page-description">
              Generate a comprehensive markdown report combining inventory health, planogram analysis,
              competitor intelligence, cross-merchandising opportunities, and an actionable optimization plan.
              Powered by SmartShelf AI analytics engine.
            </p>
          </div>
        </div>

        <div className="report-launch-content">
          <div className="report-launch-features">
            <div className="report-feature">
              <strong>Executive Summary</strong>
              <span>KPIs, stockout risks, and order cost estimates</span>
            </div>
            <div className="report-feature">
              <strong>Planogram Analysis</strong>
              <span>Shelf-level breakdown with top-scoring products</span>
            </div>
            <div className="report-feature">
              <strong>Competitor Intelligence</strong>
              <span>Price leadership, OOS opportunities, protection alerts</span>
            </div>
            <div className="report-feature">
              <strong>Reorder Priorities</strong>
              <span>Urgency-ranked replenishment recommendations</span>
            </div>
            <div className="report-feature">
              <strong>Cross-Merchandising</strong>
              <span>Basket affinity pairs with estimated uplift</span>
            </div>
            <div className="report-feature">
              <strong>Action Plan</strong>
              <span>Prioritized steps for immediate shelf optimization</span>
            </div>
          </div>

          <Button tone="primary" onClick={handleGenerate} disabled={isGenerating}>
            {isGenerating ? 'Generating Report...' : 'Generate Optimization Report'}
          </Button>
        </div>
      </section>

      {report && (
        <ReportViewer markdown={report} onClose={() => setReport(null)} />
      )}
    </>
  )
}
