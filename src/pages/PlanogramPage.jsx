import { useCallback, useMemo, useState } from 'react'
import { CrossMerchandisingPanel } from '../components/planogram/CrossMerchandisingPanel.jsx'
import { PlacementReasonPanel } from '../components/planogram/PlacementReasonPanel.jsx'
import { ShelfLayout } from '../components/planogram/ShelfLayout.jsx'
import { ShelfImageUpload } from '../components/planogram/ShelfImageUpload.jsx'
import { ComplianceReport } from '../components/planogram/ComplianceReport.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { useT } from '../lib/i18n/index.js'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import {
  analyzeCompliance,
  generateMockDetectedShelf,
} from '../lib/analytics/complianceEngine.js'

export function PlanogramPage({
  affinitySuggestions,
  affinitySummary,
  analyzedProducts,
  planogramItems,
  planogramSummary,
  shelfGroups,
}) {
  const t = useT()
  const [selectedProductId, setSelectedProductId] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [complianceReport, setComplianceReport] = useState(null)

  const selectedItem = useMemo(
    () =>
      selectedProductId
        ? planogramItems.find((item) => item.productId === selectedProductId) ?? null
        : null,
    [planogramItems, selectedProductId],
  )

  const complianceMap = useMemo(() => {
    if (!complianceReport) return null
    const map = new Map()
    for (const item of complianceReport.items) {
      map.set(item.productId, item.state)
    }
    return map
  }, [complianceReport])

  const handleAnalyze = useCallback(() => {
    setIsAnalyzing(true)
    setTimeout(() => {
      const detected = generateMockDetectedShelf(planogramItems)
      const report = analyzeCompliance(planogramItems, detected)
      setComplianceReport(report)
      setIsAnalyzing(false)
    }, 1800)
  }, [planogramItems])

  if (planogramItems.length === 0) {
    return (
      <EmptyState
        description={t('pgm.emptyDesc')}
        title={t('pgm.emptyTitle')}
      />
    )
  }

  return (
    <>
      <section className="metric-grid">
        <MetricCard label={t('rep.planogramItems')} value={planogramSummary.totalItems} detail={t('pgm.placed')} />
        <MetricCard label={t('pgm.eyeLevel')} value={planogramSummary.eyeLevelItems} detail={t('pgm.eyeLevelDetail')} tone="success" />
        <MetricCard label={t('pgm.facings')} value={planogramSummary.totalFacings} detail={t('pgm.facingsDetail')} tone="warning" />
      </section>

      <section className="planogram-workspace">
        <article className="panel planogram-stage">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Shelf optimization</p>
              <h2>Visual planogram</h2>
            </div>
          </div>
          <ShelfLayout
            activeItem={selectedItem}
            complianceMap={complianceMap}
            onSelectItem={(item) => setSelectedProductId(item.productId)}
            shelfGroups={shelfGroups}
          />
        </article>

        <PlacementReasonPanel
          selectedItem={selectedItem}
          analyzedProducts={analyzedProducts}
          planogramItems={planogramItems}
          planogramSummary={planogramSummary}
        />
      </section>

      <section className="shelf-analysis-section">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">AI Vision</p>
              <h2>Shelf Compliance Analysis</h2>
              <p className="page-description">
                Upload a photo of your physical shelf to compare it against the AI-optimized planogram.
                The vision model detects product placement, facings, and gaps.
              </p>
            </div>
          </div>
          <ShelfImageUpload onAnalyze={handleAnalyze} isAnalyzing={isAnalyzing} />
        </article>
      </section>

      {complianceReport && <ComplianceReport report={complianceReport} />}

      <CrossMerchandisingPanel suggestions={affinitySuggestions} summary={affinitySummary} />
    </>
  )
}
