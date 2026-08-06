import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { MetricCard } from '../components/shared/MetricCard.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { Button } from '../components/shared/Button.jsx'
import { formatBarcode, formatDate, formatPercent, formatShekel } from '../lib/utils/format.js'
import { compareHebrew, dirProps } from '../lib/utils/rtl.js'
import {
  OUTCOME_LABEL,
  SNOOZE_OPTIONS,
  isHandled,
  loadActions,
  persistActions,
} from '../lib/operational/completionActions.js'

const TYPE_META = {
  PROMOTE_EXPIRING_PRODUCT: { label: 'Expiring', tone: 'danger' },
  CHECK_NEGATIVE_STOCK: { label: 'Negative stock', tone: 'danger' },
  CHECK_WOLT_PRICE_GAP: { label: 'WOLT price gap', tone: 'warning' },
  CHECK_MARGIN: { label: 'Margin risk', tone: 'warning' },
  VERIFY_UNKNOWN_BARCODE: { label: 'Unknown barcode', tone: 'info' },
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

const SCRAPING_LABEL = {
  complete: 'Scraping complete',
  partial: 'Scraping partial — some sources pending',
  running: 'Scraping running…',
  not_started: 'Scraping not started',
}

const MAX_ROWS = 60

// Per-item completion actions (Done / Snooze / Dismiss) are the primary
// operational action the CSS (#23) keeps within one-handed thumb reach. The
// pure state + persistence logic lives in ../lib/operational/completionActions.

function recDetail(rec) {
  switch (rec.type) {
    case 'CHECK_WOLT_PRICE_GAP':
      return `Shelf ${formatShekel(rec.sellingPrice)} → WOLT ${formatShekel(rec.woltPrice)} (gap ${formatPercent(rec.metricValue)})`
    case 'CHECK_MARGIN':
      return `Sell ${formatShekel(rec.sellingPrice)} · Cost ${formatShekel(rec.costPrice)} · Margin ${formatPercent(rec.metricValue)}`
    case 'CHECK_NEGATIVE_STOCK':
      return `On-hand stock ${rec.currentStock ?? '—'}`
    case 'PROMOTE_EXPIRING_PRODUCT':
      return `Expiry ${formatDate(rec.expiryDate)} · ${rec.daysToExpiry ?? '—'} days · stock ${rec.currentStock ?? '—'}`
    case 'VERIFY_UNKNOWN_BARCODE':
      return rec.barcode ? `Barcode ${formatBarcode(rec.barcode)}` : 'No barcode in catalog'
    default:
      if (rec.competitorPrice != null) {
        return `Local ${formatShekel(rec.sellingPrice)} vs competitor ${formatShekel(rec.competitorPrice)}`
      }
      return rec.reason ?? ''
  }
}

function recTitle(rec) {
  return rec.productName ?? (rec.barcode ? formatBarcode(rec.barcode) : 'Unknown item')
}

export function OperationalPage({ operationalData, operationalStatus }) {
  const { meta, posHealth, byFamily, sources, recommendations } = operationalData
  const [activeFamily, setActiveFamily] = useState('ALL')
  const [activeType, setActiveType] = useState('ALL')
  const [search, setSearch] = useState('')

  // Completion-action state (Issue #31). `actions[id] = { status, snoozeUntil? }`.
  const [actions, setActions] = useState(() => loadActions())
  const [busyId, setBusyId] = useState(null)
  const [errorId, setErrorId] = useState(null)
  const [openSnoozeId, setOpenSnoozeId] = useState(null)
  // Re-render tick so expired snoozes reappear without a manual refresh.
  const [now, setNow] = useState(() => Date.now())
  const snoozeRef = useRef(null)

  // Prune snoozes that have already elapsed on mount, and tick every minute
  // so a snooze that expires while the page is open returns the row to view.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60 * 1000)
    return () => clearInterval(id)
  }, [])

  // Close the snooze menu on outside click or Escape.
  useEffect(() => {
    if (!openSnoozeId) return undefined
    const onPointer = (event) => {
      if (snoozeRef.current && !snoozeRef.current.contains(event.target)) {
        setOpenSnoozeId(null)
      }
    }
    const onKey = (event) => {
      if (event.key === 'Escape') setOpenSnoozeId(null)
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [openSnoozeId])

  // Commit an action, persist it, and roll back on failure. The `busyId`
  // guard makes the operation idempotent: a second tap while a row is
  // committing is ignored, so repeated taps never produce duplicate effects.
  const commit = useCallback(
    (id, entry) => {
      if (busyId) return
      setBusyId(id)
      setErrorId(null)
      setOpenSnoozeId(null)
      const prev = actions
      const next = { ...prev }
      if (entry) next[id] = entry
      else delete next[id]
      setActions(next)
      persistActions(next)
        .then(() => setBusyId(null))
        .catch(() => {
          // Persistence failed — revert optimistic state and surface an error.
          setActions(prev)
          setErrorId(id)
          setBusyId(null)
        })
    },
    [actions, busyId],
  )

  const markDone = useCallback((id) => commit(id, { status: 'done', at: Date.now() }), [commit])
  const dismiss = useCallback((id) => commit(id, { status: 'dismissed', at: Date.now() }), [commit])
  const snooze = useCallback(
    (id, option) =>
      commit(id, { status: 'snoozed', snoozeUntil: Date.now() + option.ms, snoozeLabel: option.label, at: Date.now() }),
    [commit],
  )
  const undo = useCallback((id) => commit(id, null), [commit])

  const query = search.trim().toLocaleLowerCase('he-IL')

  // Partition recommendations into active vs. handled (Issue #31). Handled
  // rows leave the working list but stay reachable/undoable below.
  const { activeRecommendations, handledRecommendations } = useMemo(() => {
    const active = []
    const handled = []
    for (const rec of recommendations) {
      if (isHandled(actions[rec.id], now)) handled.push(rec)
      else active.push(rec)
    }
    return { activeRecommendations: active, handledRecommendations: handled }
  }, [recommendations, actions, now])

  const familyFiltered = useMemo(
    () =>
      activeFamily === 'ALL'
        ? activeRecommendations
        : activeRecommendations.filter((rec) => rec.family === activeFamily),
    [activeRecommendations, activeFamily],
  )

  const searchFiltered = useMemo(() => {
    if (!query) return familyFiltered
    return familyFiltered.filter((rec) =>
      [rec.productName, rec.barcode, rec.category]
        .filter(Boolean)
        .some((field) => matchesHebrewQuery(field, query)),
    )
  }, [familyFiltered, query])

  const typeCounts = useMemo(() => {
    const counts = {}
    for (const rec of searchFiltered) counts[rec.type] = (counts[rec.type] ?? 0) + 1
    return counts
  }, [searchFiltered])

  const types = useMemo(
    () => Object.keys(typeCounts).sort((a, b) => typeCounts[b] - typeCounts[a]),
    [typeCounts],
  )

  const visible = useMemo(() => {
    const filtered =
      activeType === 'ALL'
        ? searchFiltered
        : searchFiltered.filter((rec) => rec.type === activeType)
    return filtered.slice(0, MAX_ROWS)
  }, [searchFiltered, activeType])

  const total = recommendations.length
  const activeTotal = activeRecommendations.length
  const filteredTotal = searchFiltered.length
  const families = Object.keys(byFamily ?? {})

  if (operationalStatus === 'loading') {
    return <EmptyState title="Loading operational data" description="Reading the latest pipeline export…" />
  }

  if (total === 0) {
    return (
      <EmptyState
        title="No operational data yet"
        description="Run `npm run data:refresh` to populate this view. It updates automatically as scraping and imports complete."
      />
    )
  }

  return (
    <>
      <section className="metric-grid">
        <MetricCard label="Total Products" value={posHealth.totalProducts} detail={posHealth.sourceFile ?? 'POS catalog'} />
        <MetricCard label="WOLT Price Gaps" value={posHealth.woltPriceGaps} detail="Shelf vs WOLT > 5%" tone="warning" />
        <MetricCard label="Negative Stock" value={posHealth.negativeStock} detail="POS data to verify" tone="danger" />
        <MetricCard label="Margin Risks" value={posHealth.marginRisks} detail="Thin or negative margin" tone="warning" />
        <MetricCard label="Missing Barcode" value={posHealth.missingBarcode} detail="Can't scan or match" tone="info" />
        <MetricCard label="Open Actions" value={activeTotal} detail={handledRecommendations.length ? `${handledRecommendations.length} handled` : 'Operational + competitor'} tone="success" />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Data sources</p>
            <h2>{SCRAPING_LABEL[meta.scrapingStatus] ?? 'Source status'}</h2>
          </div>
          <span className="metric-chip">
            {meta.generatedAt ? `Updated ${formatDate(meta.generatedAt)}` : 'Static export'}
          </span>
        </div>
        <div className="recommendation-actions" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
          {(sources ?? []).map((src) => (
            <StatusBadge key={src.source_id} tone={SOURCE_STATUS_TONE[src.status] ?? 'neutral'}>
              {src.label}: {src.status}{src.row_count ? ` (${src.row_count})` : ''}
            </StatusBadge>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Pipeline output</p>
            <h2>Recommendations</h2>
            <p className="page-description" style={{ marginTop: '0.25rem' }}>
              <strong>Operational</strong> actions come from our POS (expiry, stock, margin).
              <strong> Competitor</strong> actions come from matched Kaggle prices. Use the
              family filter to separate them.
            </p>
          </div>
          <input
            className="operational-search"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search product, barcode, or category…"
            aria-label="Search recommendations"
          />
        </div>

        {families.length > 1 && (
          <div className="recommendation-actions" style={{ flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <Button tone={activeFamily === 'ALL' ? 'primary' : 'ghost'} onClick={() => { setActiveFamily('ALL'); setActiveType('ALL') }}>
              All families ({activeTotal})
            </Button>
            {families.map((fam) => (
              <Button
                key={fam}
                tone={activeFamily === fam ? 'primary' : 'ghost'}
                onClick={() => { setActiveFamily(fam); setActiveType('ALL') }}
              >
                {fam} ({activeRecommendations.filter((rec) => rec.family === fam).length})
              </Button>
            ))}
          </div>
        )}

        <div className="recommendation-actions" style={{ flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
          <Button tone={activeType === 'ALL' ? 'primary' : 'ghost'} onClick={() => setActiveType('ALL')}>
            All ({filteredTotal})
          </Button>
          {types.map((type) => (
            <Button
              key={type}
              tone={activeType === type ? 'primary' : 'ghost'}
              onClick={() => setActiveType(type)}
            >
              {(TYPE_META[type]?.label ?? type)} ({typeCounts[type]})
            </Button>
          ))}
        </div>

        {visible.length === 0 ? (
          <EmptyState
            title={activeTotal === 0 ? 'All actions handled' : 'No matching actions'}
            description={
              activeTotal === 0
                ? 'Every recommendation has been marked done, snoozed, or dismissed. Undo one below to bring it back.'
                : query
                  ? `Nothing matches “${search.trim()}”. Clear the search to see all actions.`
                  : 'No actions for this filter.'
            }
          />
        ) : (
          <div className="compact-list">
            {visible.map((rec) => {
              const rowBusy = busyId === rec.id
              const rowError = errorId === rec.id
              const title = recTitle(rec)
              return (
                <div className={`compact-row${rowBusy ? ' compact-row-busy' : ''}`} key={rec.id}>
                  <div>
                    <strong {...dirProps(rec.productName ?? rec.barcode)}>{title}</strong>
                    <span {...dirProps(rec.category ?? recDetail(rec))}>
                      {rec.category ?? recDetail(rec) ?? '—'}
                    </span>
                  </div>
                  <div className="compact-row-end">
                    <StatusBadge tone={TYPE_META[rec.type]?.tone ?? 'neutral'}>
                      {TYPE_META[rec.type]?.label ?? rec.type}
                    </StatusBadge>
                    <small className="percent-cell">
                      {formatPercent(rec.confidence, 0, true)} · {recDetail(rec)}
                    </small>
                  </div>
                  <div className="op-actions" role="group" aria-label={`Actions for ${title}`}>
                    <Button
                      className="op-action op-action-done"
                      tone="primary"
                      disabled={rowBusy}
                      aria-label={`Mark ${title} done`}
                      title="Mark this action done"
                      onClick={() => markDone(rec.id)}
                    >
                      Done
                    </Button>
                    <div
                      className="op-snooze"
                      ref={openSnoozeId === rec.id ? snoozeRef : null}
                    >
                      <Button
                        className="op-action op-action-snooze"
                        tone="ghost"
                        disabled={rowBusy}
                        aria-haspopup="menu"
                        aria-expanded={openSnoozeId === rec.id}
                        aria-label={`Snooze ${title}`}
                        title="Snooze for later"
                        onClick={() => setOpenSnoozeId(openSnoozeId === rec.id ? null : rec.id)}
                      >
                        Snooze ▾
                      </Button>
                      {openSnoozeId === rec.id && (
                        <div className="op-snooze-menu" role="menu" aria-label={`Snooze ${title} for`}>
                          {SNOOZE_OPTIONS.map((option) => (
                            <button
                              key={option.id}
                              type="button"
                              role="menuitem"
                              className="op-snooze-option"
                              onClick={() => snooze(rec.id, option)}
                            >
                              {option.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    <Button
                      className="op-action op-action-dismiss"
                      tone="ghost"
                      disabled={rowBusy}
                      aria-label={`Dismiss ${title}`}
                      title="Dismiss — not relevant"
                      onClick={() => dismiss(rec.id)}
                    >
                      Dismiss
                    </Button>
                    {rowError && (
                      <span className="op-action-error" role="alert">
                        Couldn’t save — tap again
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
        {filteredTotal > visible.length && (
          <p className="page-description">
            Showing {visible.length} of {activeType === 'ALL' ? filteredTotal : typeCounts[activeType]} — refine by type above.
          </p>
        )}

        {handledRecommendations.length > 0 && (
          <details className="op-handled">
            <summary>Handled ({handledRecommendations.length})</summary>
            <div className="op-handled-list">
              {handledRecommendations.map((rec) => {
                const entry = actions[rec.id]
                const title = recTitle(rec)
                const outcome =
                  entry?.status === 'snoozed'
                    ? `Snoozed until ${formatDate(new Date(entry.snoozeUntil).toISOString())}`
                    : OUTCOME_LABEL[entry?.status] ?? 'Handled'
                return (
                  <div className="op-handled-row" key={rec.id}>
                    <span className="op-handled-outcome">{outcome}</span>
                    <strong {...dirProps(rec.productName ?? rec.barcode)}>{title}</strong>
                    <Button
                      className="op-action op-action-undo"
                      tone="ghost"
                      disabled={busyId === rec.id}
                      aria-label={`Undo action for ${title}`}
                      onClick={() => undo(rec.id)}
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
    </>
  )
}

function matchesHebrewQuery(value, normalizedQuery) {
  const text = String(value)
  return (
    compareHebrew(text, normalizedQuery) === 0 ||
    text.toLocaleLowerCase('he-IL').includes(normalizedQuery)
  )
}
