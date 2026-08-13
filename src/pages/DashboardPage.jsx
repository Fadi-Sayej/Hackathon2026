import { CategoryBars } from '../components/dashboard/CategoryBars.jsx'
import { MarketContextPanel } from '../components/dashboard/MarketContextPanel.jsx'
import { MarketIntelligencePanel } from '../components/MarketIntelligencePanel.jsx'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { useT } from '../lib/i18n/index.js'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { DataProvenanceBanner } from '../components/shared/DataProvenanceBanner.jsx'
import { formatCurrency, formatDays, percent, statusTone } from '../components/shared/formatters.js'
import { compareHebrew, dirProps } from '../lib/utils/rtl.js'

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
  const t = useT()
  const urgentRecommendations = recommendations
    .filter((recommendation) => recommendation.urgency === 'HIGH')
    .slice(0, 4)

  const catalogDetail =
    dataProvenance?.catalog === 'real'
      ? t('dash.realSkus')
      : dataProvenance?.catalog === 'uploaded'
        ? t('dash.csvSkus')
        : t('dash.demoSkus')
  // Sales history is absent in the YomYom inventory snapshot, so stockout /
  // reorder figures are model estimates, not observed demand. Say so.
  const velocityDetail = dataProvenance?.hasSalesHistory ? null : t('dash.estimatedNoHistory')

  return (
    <>
      <DataProvenanceBanner dataProvenance={dataProvenance} />
      <section className="metric-grid">
        <MetricCard label={t('dash.totalProducts')} value={dashboardStats.totalProducts} detail={catalogDetail} />
        <MetricCard
          label={t('dash.highRisk')}
          value={dashboardStats.highRiskStockouts}
          detail={velocityDetail ?? t('dash.highPriorityItems', { n: dashboardStats.highPriority })}
          tone="danger"
        />
        <MetricCard
          label={t('dash.reorderSuggestions')}
          value={dashboardStats.reorderSuggestions}
          detail={velocityDetail ?? t('dash.pendingDecisions')}
          tone="success"
        />
        <MetricCard
          label={t('dash.estOrderCost')}
          value={formatCurrency(dashboardStats.estimatedOrderCost)}
          detail={t('dash.estOrderCostDetail')}
          tone="warning"
        />
        <MetricCard
          label={t('dash.overstocked')}
          value={dashboardStats.overstocked}
          detail={t('dash.overstockedDetail')}
          tone="info"
        />
        <MetricCard
          label={t('dash.wasteRisk')}
          value={dashboardStats.wasteRisk}
          detail={t('dash.wasteRiskDetail')}
          tone="danger"
        />
      </section>

      <section className="dashboard-grid">
        <article className="panel panel-large">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t('eb.categoryMovement')}</p>
              <h2>{t('dash.salesDistribution')}</h2>
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
              <p className="eyebrow">{t('eb.stockRisk')}</p>
              <h2>{t('dash.highestRisk')}</h2>
            </div>
          </div>
          {analyzedProducts.length === 0 ? (
            <EmptyState
              description={t('dash.noRankDesc')}
              title={t('dash.noRankTitle')}
            />
          ) : (
            <div className="compact-list">
              {analyzedProducts
                .slice()
                .sort((a, b) =>
                  b.analytics.riskScore - a.analytics.riskScore || compareHebrew(a.name, b.name),
                )
                .slice(0, 6)
                .map((product, index) => (
                  <div className="compact-row" key={`${product.id}:${index}`}>
                    <div>
                      <strong {...dirProps(product.name)}>{product.name ?? '—'}</strong>
                      <span {...dirProps(product.category)}>{product.category ?? '—'}</span>
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
              <p className="eyebrow">{t('eb.managerAttention')}</p>
              <h2>{t('dash.urgentTitle')}</h2>
            </div>
          </div>
          {urgentRecommendations.length === 0 ? (
            <EmptyState
              description={t('dash.noUrgentDesc')}
              title={t('dash.noUrgentTitle')}
            />
          ) : (
            <div className="compact-list">
              {urgentRecommendations.map((recommendation) => (
                <div className="compact-row" key={`${recommendation.productId}:${recommendation.type}`}>
                  <div>
                    <strong {...dirProps(recommendation.productName)}>
                      {recommendation.productName ?? '—'}
                    </strong>
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
