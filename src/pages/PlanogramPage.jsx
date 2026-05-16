import { useCallback, useMemo, useState } from 'react'
import { CrossMerchandisingPanel } from '../components/planogram/CrossMerchandisingPanel.jsx'
import { ShelfLayout } from '../components/planogram/ShelfLayout.jsx'
import { ShelfImageUpload } from '../components/planogram/ShelfImageUpload.jsx'
import { ComplianceReport } from '../components/planogram/ComplianceReport.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { formatCurrency, formatDays } from '../components/shared/formatters.js'
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
  const [selectedProductId, setSelectedProductId] = useState(planogramItems[0]?.productId)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [complianceReport, setComplianceReport] = useState(null)

  const selectedItem = useMemo(
    () =>
      planogramItems.find((item) => item.productId === selectedProductId) ??
      planogramItems[0],
    [planogramItems, selectedProductId],
  )
  const product = analyzedProducts.find((item) => item.id === selectedItem?.productId)

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
        description="The current dataset did not produce shelf placements. Add eligible inventory data to generate a visual planogram."
        title="No planogram placements"
      />
    )
  }

  return (
    <>
      <section className="metric-grid">
        <MetricCard label="Planogram Items" value={planogramSummary.totalItems} detail="Products placed" />
        <MetricCard label="Eye Level" value={planogramSummary.eyeLevelItems} detail="Premium shelf spots" tone="success" />
        <MetricCard label="Total Facings" value={planogramSummary.totalFacings} detail="Recommended display units" tone="warning" />
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

        <aside className="panel insight-panel">
          <p className="eyebrow">Placement reason</p>
          <h2>{selectedItem?.productName}</h2>
          <p>{selectedItem?.reason}</p>
          {product && (
            <dl className="insight-list">
              <div>
                <dt>Sales velocity</dt>
                <dd>{product.analytics.weightedAvgDailySales} units/day</dd>
              </div>
              <div>
                <dt>Margin</dt>
                <dd>{formatCurrency(product.analytics.margin)}</dd>
              </div>
              <div>
                <dt>Stockout risk</dt>
                <dd>{formatDays(product.analytics.daysUntilStockout)}</dd>
              </div>
              <div>
                <dt>Expiry risk</dt>
                <dd>{product.analytics.statuses.includes('Near expiry') ? 'Near expiry' : 'Normal'}</dd>
              </div>
            </dl>
          )}
        </aside>
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
