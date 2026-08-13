import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNumbers, useT } from '../lib/i18n/index.js'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { Button } from '../components/shared/Button.jsx'
import { ActionCard } from '../components/operational/ActionCard.jsx'
import { rankActions, totalImpact, IMPACT_KIND } from '../lib/analytics/actionPriority.js'
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

// Tone is a property of the alert type; the label is a translation key, so the
// same table serves all three languages.
const TYPE_TONE = {
  PROMOTE_EXPIRING_PRODUCT: 'danger',
  CHECK_STOCK_DISCREPANCY: 'warning',
  CHECK_NEGATIVE_STOCK: 'neutral',
  CHECK_WOLT_PRICE_GAP: 'warning',
  CHECK_MARGIN: 'danger',
  CHECK_MARGIN_SUSPECT: 'neutral',
  VERIFY_UNKNOWN_BARCODE: 'info',
  PRICE_CHECK: 'warning',
  REORDER: 'success',
  WATCH_PRODUCT: 'info',
}

/** Label plus tone for an alert type, or a neutral fallback for an unknown one. */
function typeMeta(t, type) {
  const tone = TYPE_TONE[type]
  if (!tone) return { label: type, tone: 'neutral' }
  return { label: t(`op.type.${type}`), tone }
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

function recTitle(rec, t) {
  return rec.productName || rec.barcode || t('op.unknownItem')
}

export function OperationalPage({
  operationalData,
  operationalStatus,
  decisions = {},
  onDecide,
}) {
  const t = useT()
  const { n } = useNumbers()
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
  const perUnitTotal = totalImpact(openMoney, IMPACT_KIND.PER_SALE)
  // Kept separate on purpose: one-off exposure and per-sale cost are different
  // units, and adding them makes the headline meaningless.
  const oneOffTotal = totalImpact(openMoney, IMPACT_KIND.ONE_OFF)

  if (operationalStatus === 'loading') {
    return <EmptyState title={t('op.loading.title')} description={t('op.loading.desc')} />
  }

  if (!recommendations.length) {
    return (
      <EmptyState
        title={t('op.none.title')}
        description={t('op.none.desc')}
      />
    )
  }

  const renderCard = (rec, metaOverride) => (
    <ActionCard
      key={rec.id}
      action={rec}
      meta={metaOverride ?? typeMeta(t, rec.type)}
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
          label={t('op.metric.actions')}
          value={openMoney.length}
          detail={t('op.metric.actionsDetail')}
          tone={openMoney.length ? 'warning' : 'success'}
        />
        <MetricCard
          label={t('op.metric.perSale')}
          value={formatCurrency(perUnitTotal)}
          detail={t('op.metric.perSaleDetail')}
          tone="info"
        />
        {/* Kept separate from the per-sale figure on purpose. One-off exposure and
            a per-sale cost are different units; adding them produced a
            "₪106,164 per sale" headline that meant nothing. */}
        <MetricCard
          label={t('op.metric.unaccounted')}
          value={formatCurrency(oneOffTotal)}
          detail={t('op.metric.unaccountedDetail')}
          tone="warning"
        />
        <MetricCard
          label={t('op.metric.handled')}
          value={handledRecommendations.length}
          detail={t('op.metric.handledDetail')}
          tone="success"
        />
        <MetricCard label={t('op.metric.dataToFix')} value={openData.length} detail={t('op.metric.dataDetail')} tone="neutral" />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('op.startHere')}</p>
            <h2>{t('op.todaysActions')}</h2>
            <p className="page-description" style={{ marginTop: '0.25rem' }}>
              {t('op.todaysActionsDesc')}
            </p>
          </div>
          <div className="recommendation-actions" style={{ gap: '0.5rem' }}>
            <input
              className="operational-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t('op.search')}
              aria-label={t('op.searchLabel')}
            />
            {/* Many small-shop owners want paper or a WhatsApp screenshot, not a login. */}
            <Button tone="ghost" onClick={() => globalThis.print?.()}>
              {t('op.print')}
            </Button>
          </div>
        </div>

        {visible.length === 0 ? (
          <EmptyState
            title={query ? t('op.noMatch') : t('op.allClear')}
            description={
              query
                ? t('op.noMatchDesc')
                : handledRecommendations.length
                  ? t('op.allClearUndo')
                  : t('op.allClearData')
            }
          />
        ) : (
          <div className="action-list">{visible.map((rec) => renderCard(rec))}</div>
        )}

        {openMoney.length > TOP_N && (
          <div className="recommendation-actions" style={{ marginTop: '1rem' }}>
            <Button tone="ghost" onClick={() => setShowAll((value) => !value)}>
              {showAll ? t('op.showTop', { n: TOP_N }) : t('op.showAll', { n: openMoney.length })}
            </Button>
          </div>
        )}

        {handledRecommendations.length > 0 && (
          <details className="op-handled">
            <summary>{t('op.handledCount', { n: handledRecommendations.length })}</summary>
            <div className="op-handled-list">
              {handledRecommendations.map((rec) => {
                const entry = actions[rec.id]
                const title = recTitle(rec, t)
                let outcome = OUTCOME_LABEL[entry?.status] ?? t('op.handledFallback')
                if (entry?.status === ACTION_STATUS.SNOOZED && entry.snoozeUntil) {
                  outcome = t('op.snoozedUntil', {
                    date: formatDate(new Date(entry.snoozeUntil).toISOString()),
                  })
                } else if (entry?.status === ACTION_STATUS.DISMISSED) {
                  outcome = t('op.dismissedBecause', { reason: dismissReasonLabel(entry.reason) })
                }
                return (
                  <div className="op-handled-row" key={rec.id}>
                    <span className="op-handled-outcome">{outcome}</span>
                    <strong {...dirProps(title)}>{title}</strong>
                    <Button
                      className="op-action op-action-undo"
                      tone="ghost"
                      disabled={busyId === rec.id}
                      aria-label={t('op.undoFor', { title })}
                      onClick={() => undo(rec)}
                    >
                      {t('op.undo')}
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
            <p className="eyebrow">{t('op.notUrgent')}</p>
            <h2>{t('op.dataToFixCount', { n: openData.length })}</h2>
            <p className="page-description" style={{ marginTop: '0.25rem' }}>
              {t('op.dataToFixDesc')}
            </p>
          </div>
          <Button tone="ghost" onClick={() => setShowData((value) => !value)}>
            {showData ? t('op.hide') : t('op.show')}
          </Button>
        </div>

        {showData &&
          (openData.length === 0 ? (
            <EmptyState title={t('op.nothingToFix')} description={t('op.nothingToFixDesc')} />
          ) : (
            <div className="action-list">
              {openData.slice(0, TOP_N).map((rec) =>
                renderCard(
                  rec,
                  // A below-cost alert that reached this group did so because we could
                  // not state a credible loss — label it as the data problem it is.
                  rec.type === 'CHECK_MARGIN'
                    ? typeMeta(t, 'CHECK_MARGIN_SUSPECT')
                    : typeMeta(t, rec.type),
                ),
              )}
              {openData.length > TOP_N && (
                <p className="page-description">
                  {t('op.showingOf', { shown: TOP_N, total: openData.length })}
                </p>
              )}
            </div>
          ))}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('op.whereFrom')}</p>
            <h2>{t('op.dataSources')}</h2>
          </div>
          <span className="metric-chip">
            {meta.generatedAt
              ? t('op.updated', { date: formatDate(meta.generatedAt) })
              : t('op.staticExport')}
          </span>
        </div>
        <div className="recommendation-actions" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
          {(sources ?? []).map((src) => (
            <StatusBadge key={src.source_id} tone={SOURCE_STATUS_TONE[src.status] ?? 'neutral'}>
              {src.label}: {t(`op.src.${src.status}`)}
              {src.row_count ? ` (${n(src.row_count.toLocaleString())})` : ''}
            </StatusBadge>
          ))}
        </div>
        <p className="page-description" style={{ marginTop: '0.75rem' }}>
          {t('op.posFooter', { n: posHealth.totalProducts })}
        </p>
      </section>
    </>
  )
}
