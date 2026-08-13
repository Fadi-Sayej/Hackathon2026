import { Button } from '../components/shared/Button.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { formatCurrency, formatDays, percent, urgencyTone } from '../components/shared/formatters.js'
import { dirProps } from '../lib/utils/rtl.js'
import { useT } from '../lib/i18n/index.js'

export function RecommendationsPage({
  approvedOrders,
  onApprove,
  onEditQuantity,
  onReject,
  productIndex,
  recommendations,
}) {
  const t = useT()
  const pendingRecommendations = recommendations.filter(
    (recommendation) => recommendation.status !== 'REJECTED',
  )
  const estimatedCost = approvedOrders.reduce((sum, recommendation) => {
    const product = productIndex.get(recommendation.productId)
    return sum + (recommendation.recommendedOrderQuantity ?? 0) * (product?.cost ?? 0)
  }, 0)
  const preventedStockouts = approvedOrders.filter(
    (recommendation) => recommendation.urgency === 'HIGH',
  ).length

  return (
    <>
      <section className="metric-grid">
        <MetricCard label={t('rec.approved')} value={approvedOrders.length} detail={t('rec.approvedDetail')} tone="success" />
        <MetricCard label={t('rec.estCost')} value={formatCurrency(estimatedCost)} detail={t('rec.estCostDetail')} tone="warning" />
        <MetricCard label={t('rec.prevented')} value={preventedStockouts} detail={t('rec.preventedDetail')} tone="danger" />
      </section>

      <section className="recommendation-grid">
        {pendingRecommendations.length === 0 ? (
          <EmptyState
            description={t('rec.emptyDesc')}
            title={t('rec.emptyTitle')}
          />
        ) : (
          pendingRecommendations.map((recommendation, index) => {
            const product = productIndex.get(recommendation.productId)
            const isApproved = recommendation.status === 'APPROVED'
            // Only REORDER ever carries a quantity. PROMOTION, THIN_MARGIN and
            // BELOW_COST have none by design, so a missing quantity there is
            // normal and must NOT be labelled "count first". Withheld means:
            // this IS a reorder, but the stock figure its size would be computed
            // from has been disproven (D-7), so we refuse to invent a number.
            const quantityWithheld =
              recommendation.type === 'REORDER' &&
              recommendation.recommendedOrderQuantity == null
            const quantity = recommendation.recommendedOrderQuantity ?? 0
            const canApprove = !isApproved && quantity > 0
            const approveTitle = isApproved
              ? t('rec.alreadyApproved')
              : quantityWithheld
                ? t('rec.countFirstTitle')
                : quantity > 0
                  ? t('rec.approveThis')
                  : t('rec.needQuantity')
            return (
              <article
                className={`recommendation-card recommendation-${recommendation.urgency.toLowerCase()}${isApproved ? ' recommendation-approved' : ''}`}
                // `productId:type` is not unique — the same product can raise two
                // recommendations of the same type, and React was warning about
                // duplicate keys and may drop or duplicate rows. The list index
                // disambiguates without changing the decision key used for
                // persistence, which is deliberately coarser.
                key={`${recommendation.productId}:${recommendation.type}:${index}`}
                style={isApproved ? { opacity: 0.65 } : undefined}
              >
                <div className="recommendation-card-header">
                  <div>
                    <StatusBadge tone={isApproved ? 'success' : urgencyTone(recommendation.urgency)}>
                      {isApproved ? t('rec.badgeApproved') : recommendation.urgency}
                    </StatusBadge>
                    <h2 className="text-hebrew-title" {...dirProps(recommendation.productName)}>
                      {recommendation.productName ?? '—'}
                    </h2>
                    <p {...dirProps(recommendation.category)}>{recommendation.category ?? '—'}</p>
                  </div>
                  <div className="recommendation-qty">
                    <span>{quantityWithheld ? t('rec.countFirst') : t('rec.suggested')}</span>
                    <input
                      aria-label={t('rec.qtyLabel', { name: recommendation.productName })}
                      min="1"
                      onChange={(event) =>
                        onEditQuantity(recommendation, Number(event.target.value || 0))
                      }
                      step="1"
                      type="number"
                      placeholder={quantityWithheld ? '?' : undefined}
                      value={quantityWithheld ? '' : quantity}
                    />
                  </div>
                </div>

                <div className="recommendation-stats ltr-data">
                  <span>Stock: {recommendation.metrics?.currentStock ?? '—'}</span>
                  <span>Daily sales: {recommendation.metrics?.weightedAvgDailySales ?? '—'}</span>
                  <span>Stockout: {formatDays(recommendation.metrics?.daysUntilStockout)}</span>
                  <span>Confidence: {percent(recommendation.confidence)}</span>
                </div>

                <div className="ai-explanation">
                  <p>{t('rec.aiExplanation')}</p>
                  <span {...dirProps(recommendation.explanation)}>
                    {recommendation.explanation ?? '—'}
                  </span>
                </div>

                <div className="recommendation-actions">
                  <Button
                    disabled={!canApprove}
                    onClick={() => onApprove(recommendation)}
                    title={approveTitle}
                    tone="primary"
                  >
                    {isApproved ? t('rec.approvedBtn') : t('rec.approve')}
                  </Button>
                  <Button disabled={isApproved} onClick={() => onReject(recommendation)} tone="ghost">
                    {t('common.reject')}
                  </Button>
                  <span className="cell-price">{formatCurrency(quantity * (product?.cost ?? 0))}</span>
                </div>
              </article>
            )
          })
        )}
      </section>
    </>
  )
}
