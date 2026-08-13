import { EmptyState } from './shared/EmptyState.jsx'
import { useT } from '../lib/i18n/index.js'
import { MetricCard } from './shared/MetricCard.jsx'
import { StatusBadge } from './shared/StatusBadge.jsx'
import { formatCurrency } from './shared/formatters.js'
import { dirProps } from '../lib/utils/rtl.js'

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
  const t = useT()
  const hasAnyData =
    priceLeaders.length || stockoutOpportunities.length || priceProtectionAlerts.length

  return (
    <section className="market-intel-section">
      <section className="metric-grid metric-grid-compact">
        <MetricCard
          label={t('mi.priceLeaders')}
          value={competitorSummary?.priceLeaderCount ?? 0}
          detail={t('mi.priceLeadersDetail')}
          tone="success"
        />
        <MetricCard
          label={t('mi.competitorOos')}
          value={competitorSummary?.competitorOOSCount ?? 0}
          detail={t('mi.profitWithin1km')}
          tone="info"
        />
        <MetricCard
          label={t('mi.priceProtection')}
          value={competitorSummary?.priceProtectionCount ?? 0}
          detail={t('mi.undercuttingDetail')}
          tone="warning"
        />
        <MetricCard
          label={t('mi.trackedSkus')}
          value={competitorSummary?.productsWithCoverage ?? 0}
          detail={t('mi.joinedToFeed')}
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('mi.hyperLocal')}</p>
            <h2>{t('mi.signalsFrom')}</h2>
            <p className="page-description">{t('mi.feedDesc')}</p>
          </div>
        </div>

        {!hasAnyData ? (
          <EmptyState
            description={t('mi.noSignalsDesc')}
            title={t('mi.noSignals')}
          />
        ) : (
          <div className="market-intel-grid">
            <MarketIntelColumn
              eyebrow={t('mi.stockoutOpportunity')}
              title={t('mi.stockoutAlerts')}
              empty={t('mi.noStockouts')}
              items={stockoutOpportunities}
              renderItem={(product) => renderStockoutCard(product, t)}
            />
            <MarketIntelColumn
              eyebrow={t('mi.leaderBadge')}
              title={t('mi.priceLeaders')}
              empty={t('mi.noLeaders')}
              items={priceLeaders}
              renderItem={(product) => renderPriceLeaderCard(product, t)}
            />
            <MarketIntelColumn
              eyebrow={t('mi.priceProtection')}
              title={t('mi.undercutting')}
              empty={t('mi.noUndercut')}
              items={priceProtectionAlerts}
              renderItem={(product) => renderPriceProtectionCard(product, t)}
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

function renderStockoutCard(product, t) {
  const trigger = closestTrigger(product.competitor?.triggeredBy)
  return (
    <article className="market-intel-card market-intel-card-opportunity" key={`oos-${product.id}`}>
      <header>
        <StatusBadge tone="info">{t('mi.opportunity')}</StatusBadge>
        <strong {...dirProps(product.name)}>{product.name ?? '—'}</strong>
      </header>
      <p {...dirProps(product.category)}>{product.category ?? '—'}</p>
      {trigger && (
        <p className="market-intel-attribution">
          <strong {...dirProps(`${trigger.storeName} ${trigger.brand}`)}>
            {trigger.storeName ?? '—'} ({trigger.brand ?? '—'})
          </strong>{' '}
          {t('mi.isOos', { distance: describeDistance(trigger.distance_m) })}
        </p>
      )}
      <footer>
        <span>{t('mi.ourStock')}</span>
        <strong className="numeric-cell">{product.currentStock ?? '—'} units</strong>
      </footer>
    </article>
  )
}

function renderPriceLeaderCard(product, t) {
  const delta = product.competitor?.priceDelta ?? 0
  return (
    <article className="market-intel-card market-intel-card-leader" key={`leader-${product.id}`}>
      <header>
        <StatusBadge tone="success">{t('mi.cheapest')}</StatusBadge>
        <strong {...dirProps(product.name)}>{product.name ?? '—'}</strong>
      </header>
      <p {...dirProps(product.category)}>{product.category ?? '—'}</p>
      <p className="market-intel-attribution">
        {t('mi.belowCheapestBy', {
          amount: formatCurrency(Math.abs(delta)),
          n: product.competitor.nearbyCompetitors,
        })}
      </p>
      <footer>
        <span>{t('mi.ourPrice')}</span>
        <strong className="price-cell">{formatCurrency(product.price)}</strong>
      </footer>
    </article>
  )
}

function renderPriceProtectionCard(product, t) {
  const delta = product.competitor?.priceDelta ?? 0
  return (
    <article className="market-intel-card market-intel-card-warning" key={`prot-${product.id}`}>
      <header>
        <StatusBadge tone="warning">{t('mi.undercut')}</StatusBadge>
        <strong {...dirProps(product.name)}>{product.name ?? '—'}</strong>
      </header>
      <p {...dirProps(product.category)}>{product.category ?? '—'}</p>
      <p className="market-intel-attribution">
        {t('mi.cheaperBy', { amount: formatCurrency(delta) })}
      </p>
      <footer>
        <span>{t('mi.ourPrice')}</span>
        <strong className="price-cell">{formatCurrency(product.price)}</strong>
      </footer>
    </article>
  )
}
