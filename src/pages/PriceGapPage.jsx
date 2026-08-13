import { useMemo, useState } from 'react'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { useT } from '../lib/i18n/index.js'
import { Button } from '../components/shared/Button.jsx'
import { formatCurrency } from '../components/shared/formatters.js'
import { DATA_FRESHNESS } from '../data/marketData.js'
import { credibleLoss } from '../lib/analytics/actionPriority.js'

/**
 * Competitor price comparison — the strongest evidence this product has.
 *
 * Backed by real matched barcodes against Dor Alon, Rami Levy and Shufersal. Unlike
 * anything stock-based, these numbers do not depend on the POS stock counts the
 * manager has told us are unreliable.
 *
 * Every price carries `ageDays`. It is shown on every single row, always. A competitor
 * price is a claim about another business: stated flatly it is a liability, stated with
 * its age it is useful. One wrong claim costs more trust than every correct one earns.
 */

const VIEWS = {
  DEARER: 'dearer',
  CHEAPER: 'cheaper',
  BELOW_COST: 'below_cost',
}

const TOP_N = 25

function ageTone(days) {
  if (days == null) return 'neutral'
  if (days <= 30) return 'success'
  if (days <= 120) return 'info'
  return 'warning'
}

function ageLabel(days) {
  if (days == null) return 'age unknown'
  if (days === 0) return 'seen today'
  if (days === 1) return 'seen yesterday'
  if (days < 30) return `seen ${days} days ago`
  const months = Math.round(days / 30)
  return months <= 1 ? 'seen about a month ago' : `seen about ${months} months ago`
}

export function PriceGapPage({ products = [] }) {
  const t = useT()
  const [view, setView] = useState(VIEWS.DEARER)

  const rows = useMemo(() => {
    const out = []
    for (const product of products) {
      const competitor = product.competitor
      const cheapest = competitor?.cheapestCompetitorPrice
      const ours = product.price

      if (ours == null || ours <= 0) continue

      // Same credibility guard the action list uses, so the two screens can never
      // report different numbers of below-cost products.
      const belowCost = credibleLoss(ours, product.cost)

      if (cheapest == null) {
        if (belowCost != null) {
          out.push({ product, ours, cheapest: null, delta: null, belowCost, ageDays: null })
        }
        continue
      }

      out.push({
        product,
        ours,
        cheapest,
        delta: ours - cheapest,
        belowCost,
        ageDays: competitor?.priceAgeDays ?? null,
      })
    }
    return out
  }, [products])

  const dearer = useMemo(
    () => rows.filter((r) => r.delta != null && r.delta > 0).sort((a, b) => b.delta - a.delta),
    [rows],
  )
  const cheaper = useMemo(
    () => rows.filter((r) => r.delta != null && r.delta < 0).sort((a, b) => a.delta - b.delta),
    [rows],
  )
  const belowCost = useMemo(
    () => rows.filter((r) => r.belowCost != null).sort((a, b) => b.belowCost - a.belowCost),
    [rows],
  )

  const active = view === VIEWS.DEARER ? dearer : view === VIEWS.CHEAPER ? cheaper : belowCost

  if (!products.length) {
    return <EmptyState title={t('pg.noData')} description={t('pg.noDataDesc')} />
  }

  return (
    <>
      <section className="metric-grid">
        <MetricCard
          label={t('pg.belowCost')}
          value={belowCost.length}
          detail={t('pg.belowCostDetail')}
          tone="danger"
        />
        <MetricCard
          label={t('pg.dearer')}
          value={dearer.length}
          detail={t('pg.dearerDetail')}
          tone="warning"
        />
        <MetricCard label={t('pg.cheaper')} value={cheaper.length} detail={t('pg.cheaperDetail')} tone="success" />
        <MetricCard
          label={t('pg.compared')}
          value={DATA_FRESHNESS?.priceCount ?? rows.length}
          detail={t('pg.medianAge', { n: DATA_FRESHNESS?.medianPriceAgeDays ?? '?' })}
          tone="info"
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('eb.competitorPrices')}</p>
            <h2>{t('pg.title')}</h2>
            <p className="page-description" style={{ marginTop: '0.25rem' }}>
              {t('pg.matchedNote')}
              <strong>{t('pg.referenceNote')}</strong> {t('pg.everyRowShows')}
              price was last seen. Check before acting on a price that is months old.
            </p>
          </div>
        </div>

        <div className="recommendation-actions" style={{ flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
          <Button tone={view === VIEWS.BELOW_COST ? 'primary' : 'ghost'} onClick={() => setView(VIEWS.BELOW_COST)}>
            Below cost ({belowCost.length})
          </Button>
          <Button tone={view === VIEWS.DEARER ? 'primary' : 'ghost'} onClick={() => setView(VIEWS.DEARER)}>
            We are dearer ({dearer.length})
          </Button>
          <Button tone={view === VIEWS.CHEAPER ? 'primary' : 'ghost'} onClick={() => setView(VIEWS.CHEAPER)}>
            We are cheaper ({cheaper.length})
          </Button>
        </div>

        {active.length === 0 ? (
          <EmptyState title={t('pg.nothingHere')} description={t('pg.nothingHereDesc')} />
        ) : (
          <div className="price-table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('common.product')}</th>
                  <th className="numeric">Our price</th>
                  {view === VIEWS.BELOW_COST ? (
                    <>
                      <th className="numeric">Costs us</th>
                      <th className="numeric">Loss / sale</th>
                    </>
                  ) : (
                    <>
                      <th className="numeric">Cheapest nearby</th>
                      <th className="numeric">Difference</th>
                      <th>{t('pg.priceSeen')}</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {active.slice(0, TOP_N).map((row) => (
                  <tr key={row.product.id}>
                    <td dir="auto">{row.product.name}</td>
                    <td className="numeric">{formatCurrency(row.ours)}</td>
                    {view === VIEWS.BELOW_COST ? (
                      <>
                        <td className="numeric">{formatCurrency(row.product.cost)}</td>
                        <td className="numeric negative">−{formatCurrency(row.belowCost)}</td>
                      </>
                    ) : (
                      <>
                        <td className="numeric">{formatCurrency(row.cheapest)}</td>
                        <td className={`numeric ${row.delta > 0 ? 'negative' : 'positive'}`}>
                          {row.delta > 0 ? '+' : '−'}
                          {formatCurrency(Math.abs(row.delta))}
                        </td>
                        <td>
                          <StatusBadge tone={ageTone(row.ageDays)}>{ageLabel(row.ageDays)}</StatusBadge>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {active.length > TOP_N && (
          <p className="page-description">
            Showing the {TOP_N} largest of {active.length}.
          </p>
        )}
      </section>
    </>
  )
}
