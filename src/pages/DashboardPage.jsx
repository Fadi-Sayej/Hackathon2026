import { CategoryBars } from '../components/dashboard/CategoryBars.jsx'
import { MarketContextPanel } from '../components/dashboard/MarketContextPanel.jsx'
import { MarketIntelligencePanel } from '../components/MarketIntelligencePanel.jsx'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { DataProvenanceBanner } from '../components/shared/DataProvenanceBanner.jsx'
import { formatCurrency, formatDays, percent, statusTone } from '../components/shared/formatters.js'

export function DashboardPage({
  analyzedProducts,
  competitorSummary,
  dashboardStats,
  dataProvenance,
  marketContext,
  priceLeaderProducts,
  priceProtectionAlerts,
  recommendations,
  stockoutOpportunities,
}) {
  const urgentRecommendations = recommendations
    .filter((recommendation) => recommendation.urgency === 'HIGH')
    .slice(0, 4)

  const catalogDetail =
    dataProvenance?.catalog === 'real'
      ? 'Real YomYom POS SKUs'
      : dataProvenance?.catalog === 'uploaded'
        ? 'Uploaded CSV SKUs'
        : 'Demo sample SKUs'
  // Sales history is absent in the YomYom inventory snapshot, so stockout /
  // reorder figures are model estimates, not observed demand. Say so.
  const velocityDetail = dataProvenance?.hasSalesHistory ? null : 'Estimated — no sales history in POS export'

  return (
    <>
      <DataProvenanceBanner dataProvenance={dataProvenance} />
      <section className="metric-grid">
        <MetricCard label="Total Products" value={dashboardStats.totalProducts} detail={catalogDetail} />
        <MetricCard
          label="High Risk Stockouts"
          value={dashboardStats.highRiskStockouts}
          detail={velocityDetail ?? `${dashboardStats.highPriority} high priority items`}
          tone="danger"
        />
        <MetricCard
          label="Reorder Suggestions"
          value={dashboardStats.reorderSuggestions}
          detail={velocityDetail ?? 'Pending purchase decisions'}
          tone="success"
        />
        <MetricCard
          label="Estimated Order Cost"
          value={formatCurrency(dashboardStats.estimatedOrderCost)}
          detail="Based on recommended quantities"
          tone="warning"
        />
        <MetricCard
          label="Overstocked Items"
          value={dashboardStats.overstocked}
          detail="Capital tied in excess stock"
          tone="info"
        />
        <MetricCard
          label="Waste Risk"
          value={dashboardStats.wasteRisk}
          detail="Near-expiry products"
          tone="danger"
        />
      </section>

      <section className="dashboard-grid">
        <article className="panel panel-large">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Category movement</p>
              <h2>Sales distribution</h2>
            </div>
            <span className="metric-chip">30 day view</span>
          </div>
          <CategoryBars products={analyzedProducts} />
        </article>

        <MarketContextPanel marketContext={marketContext} />
      </section>

      <MarketIntelligencePanel
        competitorSummary={competitorSummary}
        priceLeaders={priceLeaderProducts}
        stockoutOpportunities={stockoutOpportunities}
        priceProtectionAlerts={priceProtectionAlerts}
      />

      <section className="content-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Stock risk</p>
              <h2>Highest risk products</h2>
            </div>
          </div>
          {analyzedProducts.length === 0 ? (
            <EmptyState
              description="Load demo products to populate the risk-ranked overview."
              title="No products to rank"
            />
          ) : (
            <div className="compact-list">
              {analyzedProducts
                .slice()
                .sort((a, b) => b.analytics.riskScore - a.analytics.riskScore)
                .slice(0, 6)
                .map((product) => (
                  <div className="compact-row" key={product.id}>
                    <div>
                      <strong>{product.name}</strong>
                      <span>{product.category}</span>
                    </div>
                    <div className="compact-row-end">
                      <StatusBadge tone={statusTone(product.analytics.primaryStatus)}>
                        {product.analytics.primaryStatus}
                      </StatusBadge>
                      <small>{formatDays(product.analytics.daysUntilStockout)}</small>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Manager attention</p>
              <h2>Urgent recommendations</h2>
            </div>
          </div>
          {urgentRecommendations.length === 0 ? (
            <EmptyState
              description="No high-urgency reorder or promotion actions are pending right now."
              title="No urgent recommendations"
            />
          ) : (
            <div className="compact-list">
              {urgentRecommendations.map((recommendation) => (
                <div className="compact-row" key={`${recommendation.productId}:${recommendation.type}`}>
                  <div>
                    <strong>{recommendation.productName}</strong>
                    <span>{recommendation.type.replace('_', ' ')}</span>
                  </div>
                  <div className="compact-row-end">
                    <StatusBadge tone="danger">{recommendation.urgency}</StatusBadge>
                    <small>{percent(recommendation.confidence)} confidence</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>
    </>
  )
}
