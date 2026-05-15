import { EmptyState } from '../shared/EmptyState.jsx'
import { MetricCard } from '../shared/MetricCard.jsx'
import { StatusBadge } from '../shared/StatusBadge.jsx'
import { percent } from '../shared/formatters.js'

export function CrossMerchandisingPanel({ suggestions = [], summary }) {
  if (!suggestions.length) {
    return (
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Cross-merchandising</p>
            <h2>Basket affinity suggestions</h2>
          </div>
        </div>
        <EmptyState
          description="Affinity pairs are generated from a curated convenience-store knowledge base. Load a richer catalog with more categories to see suggestions."
          title="No affinity pairs available"
        />
      </section>
    )
  }

  return (
    <section className="cross-merch-section">
      <section className="metric-grid metric-grid-compact">
        <MetricCard
          label="Affinity Pairs"
          value={summary.total}
          detail="Active basket relationships"
        />
        <MetricCard
          label="High Impact"
          value={summary.highImpact}
          detail="Pairs with strong co-purchase signal"
          tone="success"
        />
        <MetricCard
          label="Avg Basket Lift"
          value={percent(summary.estimatedAvgLift)}
          detail="Estimated uplift per co-placed pair"
          tone="warning"
        />
        <MetricCard
          label="Already Co-Located"
          value={summary.coLocated}
          detail="Pairs sharing a shelf level today"
          tone="info"
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Cross-merchandising</p>
            <h2>Basket affinity suggestions</h2>
            <p className="page-description">
              Hidden co-purchase relationships that lift Average Basket Value when paired
              on the shelf.
            </p>
          </div>
        </div>

        <div className="affinity-grid">
          {suggestions.map((suggestion) => (
            <article
              className={`affinity-card affinity-card-${suggestion.priority.toLowerCase()}`}
              key={suggestion.id}
            >
              <header className="affinity-card-header">
                <StatusBadge tone={priorityTone(suggestion.priority)}>
                  {suggestion.priority} affinity
                </StatusBadge>
                <span className="affinity-strength">
                  {percent(suggestion.strength)} strength
                </span>
              </header>

              <div className="affinity-pair">
                <div className="affinity-product">
                  <span className="affinity-product-role">Anchor</span>
                  <strong>{suggestion.anchor.name}</strong>
                  <small>{suggestion.anchor.category}</small>
                  {suggestion.anchor.shelfLabel && (
                    <span className="affinity-shelf-tag">
                      on {suggestion.anchor.shelfLabel}
                    </span>
                  )}
                </div>

                <div className="affinity-connector" aria-hidden="true">
                  +
                </div>

                <div className="affinity-product">
                  <span className="affinity-product-role">Pair with</span>
                  <strong>{suggestion.partner.name}</strong>
                  <small>{suggestion.partner.category}</small>
                  {suggestion.partner.shelfLabel && (
                    <span className="affinity-shelf-tag">
                      on {suggestion.partner.shelfLabel}
                    </span>
                  )}
                </div>
              </div>

              <p className="affinity-reason">{suggestion.reason}</p>

              <footer className="affinity-card-footer">
                <div className="affinity-action">
                  <span className="affinity-action-label">Suggested action</span>
                  <span>{suggestion.placement}</span>
                </div>
                <div className="affinity-impact">
                  <span className="affinity-impact-label">Est. basket lift</span>
                  <strong>+{percent(suggestion.liftEstimate)}</strong>
                </div>
              </footer>

              {suggestion.isCoLocated && (
                <p className="affinity-colocated">
                  Already co-located on the same shelf level — keep it that way.
                </p>
              )}
            </article>
          ))}
        </div>
      </section>
    </section>
  )
}

function priorityTone(priority) {
  if (priority === 'HIGH') return 'success'
  if (priority === 'MEDIUM') return 'warning'
  return 'neutral'
}
