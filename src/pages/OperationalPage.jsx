import { useCallback, useEffect, useMemo, useState } from 'react'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { Button } from '../components/shared/Button.jsx'
import { ActionCard } from '../components/operational/ActionCard.jsx'
import { rankActions, totalImpact } from '../lib/analytics/actionPriority.js'
import { formatCurrency } from '../components/shared/formatters.js'
import { formatDate } from '../lib/utils/format.js'
import { compareHebrew, dirProps } from '../lib/utils/rtl.js'
import {
  ACTION_STATUS,
  OUTCOME_LABEL,
  buildEntry,
  dismissReasonLabel,
  isHandled,
  loadActions,
  mergeDecisions,
  persistActions,
  toDecisionRecord,
} from '../lib/operational/completionActions.js'

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

// Hebrew product names must match a Hebrew query regardless of case and of the
// final-letter forms, so plain toLowerCase() is not enough — compareHebrew()
// carries the collator that C-1a established.
function matchesHebrewQuery(value, normalizedQuery) {
  const text = String(value)
  return (
    compareHebrew(text, normalizedQuery) === 0 ||
    text.toLocaleLowerCase('he-IL').includes(normalizedQuery)
  )
}

function matchesQuery(rec, query) {
  if (!query) return true
  return [rec.productName, rec.barcode, rec.category]
    .filter(Boolean)
    .some((field) => matchesHebrewQuery(field, query))
}

function recTitle(rec) {
  return rec.productName || rec.barcode || 'Unknown item'
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

  // Completion-action state (Issue #31). `actions[id] = { status, reason?, snoozeUntil? }`.
  //
  // Seeded ONCE, from localStorage merged with any decisions already persisted
  // through App.jsx, so outcomes recorded before #31 still read as handled.
  // After that this state is the sole source of truth: re-merging `decisions` on
  // every render would resurrect an item the moment it was undone, because
  // onDecide has already written it to App's state.
  const [actions, setActions] = useState(() => mergeDecisions(loadActions(), decisions))
  const [busyId, setBusyId] = useState(null)
  const [errorId, setErrorId] = useState(null)
  // Re-render tick so expired snoozes reappear without a manual refresh.
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60 * 1000)
    return () => clearInterval(id)
  }, [])

  // Commit an action, persist it, and roll back on failure. The `busyId` guard
  // makes the operation idempotent: a second tap while a row is committing is
  // ignored, so repeated taps never produce duplicate effects.
  const commit = useCallback(
    (action, entry) => {
      if (busyId) return
      const id = action.id
      setBusyId(id)
      setErrorId(null)

      const prev = actions
      const next = { ...prev }
      if (entry) next[id] = entry
      else delete next[id]
      setActions(next)

      persistActions(next)
        .then(() => {
          setBusyId(null)
          // Only report upstream once the write actually succeeded, so telemetry
          // never records a decision that was rolled back.
          if (entry) onDecide?.(toDecisionRecord(action, entry))
        })
        .catch(() => {
          setActions(prev)
          setErrorId(id)
          setBusyId(null)
        })
    },
    [actions, busyId, onDecide],
  )

  const decide = useCallback(
    (action, { status, reason, snoozeOptionId }) => {
      const entry = buildEntry({ status, reason, snoozeOptionId })
      // buildEntry returns null for an unusable status or an unknown snooze
      // option. Leave the item open rather than guessing what was meant.
      if (!entry) return
      commit(action, entry)
    },
    [commit],
  )

  const undo = useCallback((action) => commit(action, null), [commit])

  const query = search.trim().toLocaleLowerCase('he-IL')

  const { money, data } = useMemo(() => rankActions(recommendations), [recommendations])

  const openMoney = useMemo(
    () => money.filter((rec) => matchesQuery(rec, query) && !isHandled(actions[rec.id], now)),
    [money, actions, now, query],
  )
  const openData = useMemo(
    () => data.filter((rec) => matchesQuery(rec, query) && !isHandled(actions[rec.id], now)),
    [data, actions, now, query],
  )

  const handledRecommendations = useMemo(
    () => recommendations.filter((rec) => isHandled(actions[rec.id], now)),
    [recommendations, actions, now],
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

  const renderCard = (rec, metaOverride) => (
    <ActionCard
      key={rec.id}
      action={rec}
      meta={metaOverride ?? TYPE_META[rec.type]}
      busy={busyId === rec.id}
      error={errorId === rec.id}
      onDecide={(decision) => decide(rec, decision)}
      muted={metaOverride ? true : undefined}
    />
  )

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
        <MetricCard
          label="Handled"
          value={handledRecommendations.length}
          detail="Done, dismissed or snoozed"
          tone="success"
        />
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
                : handledRecommendations.length
                  ? 'Every money action has been handled. Undo one below to bring it back.'
                  : 'Every money action has been handled. Anything left is under “Data to fix”.'
            }
          />
        ) : (
          <div className="action-list">{visible.map((rec) => renderCard(rec))}</div>
        )}

        {openMoney.length > TOP_N && (
          <div className="recommendation-actions" style={{ marginTop: '1rem' }}>
            <Button tone="ghost" onClick={() => setShowAll((value) => !value)}>
              {showAll ? `Show top ${TOP_N} only` : `Show all ${openMoney.length} actions`}
            </Button>
          </div>
        )}

        {handledRecommendations.length > 0 && (
          <details className="op-handled">
            <summary>Handled ({handledRecommendations.length})</summary>
            <div className="op-handled-list">
              {handledRecommendations.map((rec) => {
                const entry = actions[rec.id]
                const title = recTitle(rec)
                let outcome = OUTCOME_LABEL[entry?.status] ?? 'Handled'
                if (entry?.status === ACTION_STATUS.SNOOZED && entry.snoozeUntil) {
                  outcome = `Snoozed until ${formatDate(new Date(entry.snoozeUntil).toISOString())}`
                } else if (entry?.status === ACTION_STATUS.DISMISSED) {
                  outcome = `Dismissed — ${dismissReasonLabel(entry.reason)}`
                }
                return (
                  <div className="op-handled-row" key={rec.id}>
                    <span className="op-handled-outcome">{outcome}</span>
                    <strong {...dirProps(title)}>{title}</strong>
                    <Button
                      className="op-action op-action-undo"
                      tone="ghost"
                      disabled={busyId === rec.id}
                      aria-label={`Undo action for ${title}`}
                      onClick={() => undo(rec)}
                    >
                      Undo
                    </Button>
                  </div>
                )
              })}
            </div>
          </details>
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

        {showData &&
          (openData.length === 0 ? (
            <EmptyState title="Nothing to fix" description="No outstanding data issues." />
          ) : (
            <div className="action-list">
              {openData.slice(0, TOP_N).map((rec) =>
                renderCard(
                  rec,
                  // A below-cost alert that reached this group did so because we could
                  // not state a credible loss — label it as the data problem it is.
                  rec.type === 'CHECK_MARGIN'
                    ? TYPE_META.CHECK_MARGIN_SUSPECT
                    : (TYPE_META[rec.type] ?? { label: rec.type, tone: 'neutral' }),
                ),
              )}
              {openData.length > TOP_N && (
                <p className="page-description">
                  Showing {TOP_N} of {openData.length}.
                </p>
              )}
            </div>
          ))}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Where this comes from</p>
            <h2>Data sources</h2>
          </div>
          <span className="metric-chip">
            {meta.generatedAt ? `Updated ${formatDate(meta.generatedAt)}` : 'Static export'}
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
          {posHealth.totalProducts} products from the POS export.{' '}
          Stock counts are known to be unreliable, so nothing here predicts running out.
        </p>
      </section>
    </>
  )
}
