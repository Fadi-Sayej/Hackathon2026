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

  const handleGenerate = useCallback(() => {
    setIsGenerating(true)
    setTimeout(() => {
      const md = buildOptimizationReport({
        analyzedProducts,
        competitorSummary,
        dashboardStats,
        inventorySummary,
        marketContext,
        planogramItems,
        planogramSummary,
        recommendations,
        affinitySuggestions,
      })
      setReport(md)
      setIsGenerating(false)
    }, 2200)
  }, [analyzedProducts, competitorSummary, dashboardStats, inventorySummary, marketContext, planogramItems, planogramSummary, recommendations, affinitySuggestions])

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
