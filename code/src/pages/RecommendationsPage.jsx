import { Button } from '../components/shared/Button.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { formatCurrency, formatDays, percent, urgencyTone } from '../components/shared/formatters.js'

export function RecommendationsPage({
  approvedOrders,
  onApprove,
  onEditQuantity,
  onReject,
  productIndex,
  recommendations,
}) {
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
        <MetricCard label="Approved" value={approvedOrders.length} detail="Manager approved actions" tone="success" />
        <MetricCard label="Estimated Cost" value={formatCurrency(estimatedCost)} detail="Approved order total" tone="warning" />
        <MetricCard label="Prevented Stockouts" value={preventedStockouts} detail="High urgency approvals" tone="danger" />
      </section>

      <section className="recommendation-grid">
        {pendingRecommendations.length === 0 ? (
          <EmptyState
            description="No active recommendations match the current dataset."
            title="No recommendations pending"
          />
        ) : (
          pendingRecommendations.map((recommendation) => {
            const product = productIndex.get(recommendation.productId)
            const isApproved = recommendation.status === 'APPROVED'
            const quantity = recommendation.recommendedOrderQuantity ?? 0
            const canApprove = !isApproved && quantity > 0
            const approveTitle = isApproved
              ? 'Already approved'
              : quantity > 0
                ? 'Approve this recommendation'
                : 'Enter a quantity above zero to approve'
            return (
              <article
                className={`recommendation-card recommendation-${recommendation.urgency.toLowerCase()}${isApproved ? ' recommendation-approved' : ''}`}
                key={`${recommendation.productId}:${recommendation.type}`}
                style={isApproved ? { opacity: 0.65 } : undefined}
              >
                <div className="recommendation-card-header">
                  <div>
                    <StatusBadge tone={isApproved ? 'success' : urgencyTone(recommendation.urgency)}>
                      {isApproved ? 'APPROVED' : recommendation.urgency}
                    </StatusBadge>
                    <h2>{recommendation.productName}</h2>
                    <p>{recommendation.category}</p>
                  </div>
                  <div className="recommendation-qty">
                    <span>Suggested</span>
                    <input
                      aria-label={`Suggested order quantity for ${recommendation.productName}`}
                      min="1"
                      onChange={(event) =>
                        onEditQuantity(recommendation, Number(event.target.value || 0))
                      }
                      step="1"
                      type="number"
                      value={quantity}
                    />
                  </div>
                </div>

                <div className="recommendation-stats">
                  <span>Stock: {recommendation.metrics?.currentStock ?? '—'}</span>
                  <span>Daily sales: {recommendation.metrics?.weightedAvgDailySales ?? '—'}</span>
                  <span>Stockout: {formatDays(recommendation.metrics?.daysUntilStockout)}</span>
                  <span>Confidence: {percent(recommendation.confidence)}</span>
                </div>

                <div className="ai-explanation">
                  <p>AI explanation</p>
                  <span>{recommendation.explanation}</span>
                </div>

                <div className="recommendation-actions">
                  <Button
                    disabled={!canApprove}
                    onClick={() => onApprove(recommendation)}
                    title={approveTitle}
                    tone="primary"
                  >
                    {isApproved ? 'Approved' : 'Approve'}
                  </Button>
                  <Button disabled={isApproved} onClick={() => onReject(recommendation)} tone="ghost">
                    Reject
                  </Button>
                  <span>{formatCurrency(quantity * (product?.cost ?? 0))}</span>
                </div>
              </article>
            )
          })
        )}
      </section>
    </>
  )
}
