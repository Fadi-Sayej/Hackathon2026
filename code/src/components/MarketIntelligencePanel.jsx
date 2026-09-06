import { EmptyState } from './shared/EmptyState.jsx'
import { MetricCard } from './shared/MetricCard.jsx'
import { StatusBadge } from './shared/StatusBadge.jsx'
import { formatCurrency } from './shared/formatters.js'

function describeDistance(meters) {
  if (!Number.isFinite(meters)) return ''
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`
  return `${Math.round(meters)} m`
}

function closestTrigger(triggeredBy = []) {
  if (!triggeredBy.length) return null
  return triggeredBy.reduce(
    (closest, current) => (current.distance_m < closest.distance_m ? current : closest),
    triggeredBy[0],
  )
}

export function MarketIntelligencePanel({
  competitorSummary,
  priceLeaders = [],
  stockoutOpportunities = [],
  priceProtectionAlerts = [],
}) {
  const hasAnyData =
    priceLeaders.length || stockoutOpportunities.length || priceProtectionAlerts.length

  return (
    <section className="market-intel-section">
      <section className="metric-grid metric-grid-compact">
        <MetricCard
          label="Local Price Leaders"
          value={competitorSummary?.priceLeaderCount ?? 0}
          detail="Items where we beat every nearby chain"
          tone="success"
        />
        <MetricCard
          label="Competitor OOS"
          value={competitorSummary?.competitorOOSCount ?? 0}
          detail="Profit opportunities within 1 km"
          tone="info"
        />
        <MetricCard
          label="Price Protection"
          value={competitorSummary?.priceProtectionCount ?? 0}
          detail="Items where rivals are >15% cheaper"
          tone="warning"
        />
        <MetricCard
          label="Tracked SKUs"
          value={competitorSummary?.productsWithCoverage ?? 0}
          detail="Joined to the local market feed"
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Hyper-local intelligence</p>
            <h2>Market signals from Paz, Delek, Sonol & Dor Alon</h2>
            <p className="page-description">
              Built from the Israeli "Hok HaMazon" transparency feed — barcode-level price
              and stock data from every chain within 1 km, updated hourly.
            </p>
          </div>
        </div>

        {!hasAnyData ? (
          <EmptyState
            description="No competitor signals are firing right now. The mock neighborhood feed will surface alerts as soon as a barcode goes OOS at a nearby station."
            title="No market signals"
          />
        ) : (
          <div className="market-intel-grid">
            <MarketIntelColumn
              eyebrow="Stockout opportunity"
              title="Competitor stockout alerts"
              empty="No nearby competitor is OOS on our top sellers right now."
              items={stockoutOpportunities}
              renderItem={renderStockoutCard}
            />
            <MarketIntelColumn
              eyebrow="Price leader"
              title="Local price leaders"
              empty="No items where we currently beat every nearby chain."
              items={priceLeaders}
              renderItem={renderPriceLeaderCard}
            />
            <MarketIntelColumn
              eyebrow="Price protection"
              title="Rivals undercutting us"
              empty="No competitor is more than 15% cheaper on tracked SKUs."
              items={priceProtectionAlerts}
              renderItem={renderPriceProtectionCard}
            />
          </div>
        )}
      </section>
    </section>
  )
}

function MarketIntelColumn({ eyebrow, title, empty, items, renderItem }) {
  return (
    <article className="market-intel-column">
      <header>
        <p className="eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
      </header>
      {items.length === 0 ? (
        <p className="market-intel-empty">{empty}</p>
      ) : (
        <div className="market-intel-cards">{items.slice(0, 4).map(renderItem)}</div>
      )}
    </article>
  )
}

function renderStockoutCard(product) {
  const trigger = closestTrigger(product.competitor?.triggeredBy)
  return (
    <article className="market-intel-card market-intel-card-opportunity" key={`oos-${product.id}`}>
      <header>
        <StatusBadge tone="info">Opportunity</StatusBadge>
        <strong>{product.name}</strong>
      </header>
      <p>{product.category}</p>
      {trigger && (
        <p className="market-intel-attribution">
          <strong>{trigger.storeName} ({trigger.brand})</strong> is OOS — {describeDistance(trigger.distance_m)} away
        </p>
      )}
      <footer>
        <span>Our stock</span>
        <strong>{product.currentStock} units</strong>
      </footer>
    </article>
  )
}

function renderPriceLeaderCard(product) {
  const delta = product.competitor?.priceDelta ?? 0
  return (
    <article className="market-intel-card market-intel-card-leader" key={`leader-${product.id}`}>
      <header>
        <StatusBadge tone="success">Cheapest</StatusBadge>
        <strong>{product.name}</strong>
      </header>
      <p>{product.category}</p>
      <p className="market-intel-attribution">
        We are <strong>{formatCurrency(Math.abs(delta))}</strong> below the cheapest of {product.competitor.nearbyCompetitors} nearby stores
      </p>
      <footer>
        <span>Our price</span>
        <strong>{formatCurrency(product.price)}</strong>
      </footer>
    </article>
  )
}

function renderPriceProtectionCard(product) {
  const delta = product.competitor?.priceDelta ?? 0
  return (
    <article className="market-intel-card market-intel-card-warning" key={`prot-${product.id}`}>
      <header>
        <StatusBadge tone="warning">Undercut</StatusBadge>
        <strong>{product.name}</strong>
      </header>
      <p>{product.category}</p>
      <p className="market-intel-attribution">
        A competitor is <strong>{formatCurrency(delta)}</strong> cheaper — consider matching or repositioning
      </p>
      <footer>
        <span>Our price</span>
        <strong>{formatCurrency(product.price)}</strong>
      </footer>
    </article>
  )
}
