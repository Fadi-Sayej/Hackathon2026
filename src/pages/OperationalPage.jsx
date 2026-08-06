import { useMemo, useState } from 'react'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { Button } from '../components/shared/Button.jsx'
import { ActionCard } from '../components/operational/ActionCard.jsx'
import { rankActions, totalImpact } from '../lib/analytics/actionPriority.js'
import { formatCurrency } from '../components/shared/formatters.js'
import { formatDate } from '../lib/utils/format.js'

const TYPE_META = {
  PROMOTE_EXPIRING_PRODUCT: { label: 'Expiring', tone: 'danger' },
  CHECK_NEGATIVE_STOCK: { label: 'Stock count wrong', tone: 'neutral' },
  CHECK_WOLT_PRICE_GAP: { label: 'WOLT price gap', tone: 'warning' },
  CHECK_MARGIN: { label: 'Selling below cost', tone: 'danger' },
  CHECK_MARGIN_SUSPECT: { label: 'Cost price looks wrong', tone: 'neutral' },
  VERIFY_UNKNOWN_BARCODE: { label: 'No barcode', tone: 'info' },
  PRICE_CHECK: { label: 'Price check', tone: 'warning' },
  REORDER: { label: 'Reorder', tone: 'success' },
  WATCH_PRODUCT: { label: 'Watch', tone: 'info' },
}

const SOURCE_STATUS_TONE = {
  complete: 'success',
  partial: 'warning',
  running: 'warning',
  not_started: 'neutral',
  error: 'danger',
}

// A manager has ten minutes. Show the shortlist, keep the rest one click away.
const TOP_N = 20

function matchesQuery(rec, query) {
  if (!query) return true
  return [rec.productName, rec.barcode, rec.category]
    .filter(Boolean)
    .some((field) => String(field).toLowerCase().includes(query))
}

export function OperationalPage({
  operationalData,
  operationalStatus,
  decisions = {},
  onDecide,
}) {
  const { meta, posHealth, sources, recommendations } = operationalData
  const [showAll, setShowAll] = useState(false)
  const [showData, setShowData] = useState(false)
  const [search, setSearch] = useState('')

  const query = search.trim().toLowerCase()

  const { money, data } = useMemo(() => rankActions(recommendations), [recommendations])

  const openMoney = useMemo(
    () => money.filter((rec) => matchesQuery(rec, query) && !decisions[rec.id]),
    [money, decisions, query],
  )
  const openData = useMemo(
    () => data.filter((rec) => matchesQuery(rec, query) && !decisions[rec.id]),
    [data, decisions, query],
  )

  const handledCount = useMemo(
    () => recommendations.filter((rec) => decisions[rec.id]).length,
    [recommendations, decisions],
  )

  const visible = showAll ? openMoney : openMoney.slice(0, TOP_N)
  const perUnitTotal = totalImpact(openMoney)

  if (operationalStatus === 'loading') {
    return <EmptyState title="Loading today's actions" description="Reading the latest pipeline export…" />
  }

  if (!recommendations.length) {
    return (
      <EmptyState
        title="No actions yet"
        description="Run `npm run pilot:daily` to refresh from the latest POS export."
      />
    )
  }

  return (
    <>
      <section className="metric-grid">
        <MetricCard
          label="Actions today"
          value={openMoney.length}
          detail="Ranked by money at stake"
          tone={openMoney.length ? 'warning' : 'success'}
        />
        <MetricCard
          label="Per sale at stake"
          value={formatCurrency(perUnitTotal)}
          detail="Summed across open actions"
          tone="info"
        />
        <MetricCard label="Handled" value={handledCount} detail="Done, dismissed or snoozed" tone="success" />
        <MetricCard label="Data to fix" value={openData.length} detail="No money attached" tone="neutral" />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Start here</p>
            <h2>Today&apos;s actions</h2>
            <p className="page-description" style={{ marginTop: '0.25rem' }}>
              Ordered by how much money each one is worth per sale. Work down from the top —
              the first few are worth more than all the rest together.
            </p>
          </div>
          <div className="recommendation-actions" style={{ gap: '0.5rem' }}>
            <input
              className="operational-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search product or barcode…"
              aria-label="Search actions"
            />
            {/* Many small-shop owners want paper or a WhatsApp screenshot, not a login. */}
            <Button tone="ghost" onClick={() => globalThis.print?.()}>
              Print list
            </Button>
          </div>
        </div>

        {visible.length === 0 ? (
          <EmptyState
            title={query ? 'Nothing matches that search' : 'All clear'}
            description={
              query
                ? 'Clear the search to see the full list.'
                : 'Every money action has been handled. Anything left is under “Data to fix”.'
            }
          />
        ) : (
          <div className="action-list">
            {visible.map((rec) => (
              <ActionCard
                key={rec.id}
                action={rec}
                meta={TYPE_META[rec.type]}
                onDecide={onDecide}
              />
            ))}
          </div>
        )}

        {openMoney.length > TOP_N && (
          <div className="recommendation-actions" style={{ marginTop: '1rem' }}>
            <Button tone="ghost" onClick={() => setShowAll((value) => !value)}>
              {showAll
                ? `Show top ${TOP_N} only`
                : `Show all ${openMoney.length} actions`}
            </Button>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Not urgent</p>
            <h2>Data to fix ({openData.length})</h2>
            <p className="page-description" style={{ marginTop: '0.25rem' }}>
              Catalog issues with no direct money attached — mostly stock counts that need a
              physical check, and items with no barcode. Worth cleaning up when there is time,
              but nothing here is losing you money today.
            </p>
          </div>
          <Button tone="ghost" onClick={() => setShowData((value) => !value)}>
            {showData ? 'Hide' : 'Show'}
          </Button>
        </div>

        {showData && (
          openData.length === 0 ? (
            <EmptyState title="Nothing to fix" description="No outstanding data issues." />
          ) : (
            <div className="action-list">
              {openData.slice(0, TOP_N).map((rec) => (
                <ActionCard
                  key={rec.id}
                  action={rec}
                  meta={
                    // A below-cost alert that reached this group did so because we could
                    // not state a credible loss — label it as the data problem it is.
                    rec.type === 'CHECK_MARGIN'
                      ? TYPE_META.CHECK_MARGIN_SUSPECT
                      : TYPE_META[rec.type]
                  }
                  onDecide={onDecide}
                  muted
                />
              ))}
              {openData.length > TOP_N && (
                <p className="page-description">
                  Showing {TOP_N} of {openData.length}.
                </p>
              )}
            </div>
          )
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Where this comes from</p>
            <h2>Data sources</h2>
          </div>
          <span className="metric-chip">
            {meta.generatedAt
              ? `Updated ${formatDate(meta.generatedAt)}`
              : 'Static export'}
          </span>
        </div>
        <div className="recommendation-actions" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
          {(sources ?? []).map((src) => (
            <StatusBadge key={src.source_id} tone={SOURCE_STATUS_TONE[src.status] ?? 'neutral'}>
              {src.label}: {src.status}
              {src.row_count ? ` (${src.row_count})` : ''}
            </StatusBadge>
          ))}
        </div>
        <p className="page-description" style={{ marginTop: '0.75rem' }}>
          {posHealth.totalProducts} products from the POS export.
          {' '}Stock counts are known to be unreliable, so nothing here predicts running out.
        </p>
      </section>
    </>
  )
}
