import { useCallback, useState } from 'react'
import { Button } from '../components/shared/Button.jsx'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { useT } from '../lib/i18n/index.js'
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
  const t = useT()
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
          label={t('rep.analyzed')}
          value={analyzedProducts?.length ?? 0}
          detail={t('rep.analyzedDetail')}
        />
        <MetricCard
          label={t('rep.alerts')}
          value={recommendations?.filter((r) => r.type === 'REORDER').length ?? 0}
          detail={t('rep.alertsDetail')}
          tone="warning"
        />
        <MetricCard
          label={t('rep.planogramItems')}
          value={planogramSummary?.totalItems ?? 0}
          detail={t('rep.planogramDetail')}
          tone="success"
        />
        <MetricCard
          label={t('rep.signals')}
          value={(competitorSummary?.priceLeaderCount ?? 0) + (competitorSummary?.competitorOOSCount ?? 0)}
          detail={t('rep.signalsDetail')}
          tone="info"
        />
      </section>

      <section className="panel report-launch-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">AI Report Engine</p>
            <h2>{t('rep.title')}</h2>
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
              <strong>{t('rep.execSummary')}</strong>
              <span>{t('rep.execSummaryDesc')}</span>
            </div>
            <div className="report-feature">
              <strong>{t('rep.planogramAnalysis')}</strong>
              <span>{t('rep.planogramAnalysisDesc')}</span>
            </div>
            <div className="report-feature">
              <strong>{t('rep.competitorIntel')}</strong>
              <span>{t('rep.competitorIntelDesc')}</span>
            </div>
            <div className="report-feature">
              <strong>{t('rep.reorderPriorities')}</strong>
              <span>{t('rep.reorderPrioritiesDesc')}</span>
            </div>
            <div className="report-feature">
              <strong>{t('rep.crossMerch')}</strong>
              <span>{t('rep.crossMerchDesc')}</span>
            </div>
            <div className="report-feature">
              <strong>{t('rep.actionPlan')}</strong>
              <span>{t('rep.actionPlanDesc')}</span>
            </div>
          </div>

          <Button tone="primary" onClick={handleGenerate} disabled={isGenerating}>
            {isGenerating ? t('rep.generating') : t('rep.generate')}
          </Button>
        </div>
      </section>

      {report && (
        <ReportViewer markdown={report} onClose={() => setReport(null)} />
      )}
    </>
  )
}
