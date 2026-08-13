import { useEffect, useMemo, useState } from 'react'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { useT } from '../lib/i18n/index.js'
import { Button } from '../components/shared/Button.jsx'
import { formatCurrency } from '../components/shared/formatters.js'

/**
 * The assortment gap — products competitors carry and this shop does not.
 *
 * This is the one screen about products we do NOT stock, which changes what may be
 * shown on it. There is no stock, no margin, no velocity of our own to report:
 * we have never sold any of these. The only honest evidence is how many comparable
 * branches carry the product and what they charge, so that is all a row states.
 *
 * Ranked by branch coverage alone. A margin-weighted ranking was measured against
 * it and lost badly — it put a ₪350 projector above a ₪6 snack stocked by 155 of
 * 156 branches, because without sales history an assumed margin is not evidence
 * of anything while coverage across a whole chain is.
 */

const BANDS = [
  { id: 'all', labelKey: 'common.all' },
  { id: 'impulse', labelKey: 'gap.under15' },
  { id: 'everyday', label: '₪15–40' },
  { id: 'considered', label: '₪40–100' },
  { id: 'high_ticket', labelKey: 'gap.over100' },
]

const TOP_N = 30

function coverageTone(ratio) {
  if (ratio >= 0.75) return 'success'
  if (ratio >= 0.5) return 'info'
  return 'neutral'
}

export function AssortmentGapPage() {
  const t = useT()
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading')
  const [band, setBand] = useState('all')

  useEffect(() => {
    let cancelled = false
    fetch('/data/assortment_gap.json')
      .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
      .then((payload) => {
        if (!cancelled) {
          setData(payload)
          setStatus('ready')
        }
      })
      .catch(() => {
        if (!cancelled) setStatus('empty')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const rows = useMemo(() => {
    const all = data?.recommendations ?? []
    const filtered = band === 'all' ? all : all.filter((row) => row.evidence?.priceBand === band)
    return filtered.slice(0, TOP_N)
  }, [data, band])

  if (status === 'loading') {
    return <EmptyState title={t('gap.loading')} detail={t('gap.loadingDetail')} />
  }

  if (status === 'empty' || !data?.recommendations?.length) {
    return (
      <EmptyState
        title={t('gap.emptyTitle')}
        detail={t('gap.emptyDetail')}
      />
    )
  }

  const { counts, policy, branchesCompared } = data

  return (
    <section className="page">
      <header className="page-header">
        <p className="eyebrow">Assortment</p>
        <h1>{t('gap.headline')}</h1>
        <p className="page-intro">
          Compared against {branchesCompared} branches of the same store format. These are
          products you have never stocked, so there is no sales history for any of them —
          the evidence is how many of those branches carry it.
        </p>
      </header>

      <div className="metric-grid">
        <MetricCard
          label={t('gap.products')}
          value={counts.gapTotal.toLocaleString()}
          detail={`Across ${branchesCompared} comparable branches`}
        />
        <MetricCard
          label={t('gap.widely')}
          value={counts.afterMinCoverage.toLocaleString()}
          detail={t('gap.widelyDetail')}
          tone="info"
        />
        <MetricCard
          label={t('gap.shown')}
          value={counts.emitted.toLocaleString()}
          detail={t('gap.shownDetail')}
        />
        <MetricCard
          label={t('gap.hidden')}
          value={counts.excludedByPolicy.toLocaleString()}
          detail={
            policy.excludes.length
              ? `Not stocked here: ${policy.excludes.join(', ')}`
              : t('gap.nothingExcluded')
          }
          tone={counts.excludedByPolicy ? 'warning' : 'neutral'}
        />
      </div>

      <div className="filter-row">
        {BANDS.map((entry) => (
          <Button
            key={entry.id}
            variant={band === entry.id ? 'primary' : 'ghost'}
            onClick={() => setBand(entry.id)}
          >
            {entry.labelKey ? t(entry.labelKey) : entry.label}
          </Button>
        ))}
      </div>

      {rows.length === 0 ? (
        <EmptyState title={t('gap.noneInRange')} detail={t('gap.tryAnother')} />
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('common.product')}</th>
                <th>{t('gap.carriedBy')}</th>
                <th>{t('gap.theirPrice')}</th>
                <th>{t('gap.notes')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const evidence = row.evidence ?? {}
                return (
                  <tr key={row.productId}>
                    <td dir="auto">{row.productName}</td>
                    <td>
                      <StatusBadge tone={coverageTone(evidence.coverageRatio)}>
                        {evidence.branchesCarrying} of {evidence.branchesCompared}
                      </StatusBadge>
                    </td>
                    <td>
                      {formatCurrency(evidence.competitorPriceMedian)}
                      {evidence.competitorPriceMin !== evidence.competitorPriceMax && (
                        <span className="muted">
                          {' '}
                          ({formatCurrency(evidence.competitorPriceMin)}–
                          {formatCurrency(evidence.competitorPriceMax)})
                        </span>
                      )}
                    </td>
                    <td>
                      {/* Segment tags are descriptive, never a judgement — whether this
                          shop carries a segment is its own setting, not our assumption. */}
                      {row.segments?.length ? (
                        <StatusBadge tone="neutral">{row.segments.join(', ')}</StatusBadge>
                      ) : null}
                      {row.reviewRequired?.length ? (
                        <StatusBadge tone="warning">{t('gap.needsChecking')}</StatusBadge>
                      ) : null}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="page-footnote">
        No sales rate is shown for any row, and none can be: this shop has never sold
        these products. Prices are what comparable branches charged when last collected.
      </p>
    </section>
  )
}
