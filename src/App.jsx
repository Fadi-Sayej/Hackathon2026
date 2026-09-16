import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'
// The daily surface's own rules. Task 2.7 shipped its class names and no stylesheet.
import './surface/surface.css'
// …and the other nine V1 pages, which had the same omission.
import './surface/pages.css'

import { AppShell } from './components/layout/AppShell.jsx'
import { loadDashboard } from './lib/dataAdapters/loadDashboard.js'
import { artefactToOperational } from './lib/dataAdapters/artefactToOperational.js'
import { loadOwnerState, recordOutcome } from './owner/ownerState.js'
import { OperationalPage } from './pages/OperationalPage.jsx'
import { DataPage } from './pages/DataPage.jsx'
import { PageAwaitingData } from './pages/PageAwaitingData.jsx'
import { useI18n } from './lib/i18n/index.js'

/**
 * What each restored page is waiting for, when the artefact cannot feed it.
 *
 * Reorder, Approved orders, Store layout and Shelf plan rank by how fast a product sells.
 * That number does not exist outside `src/data/demoProducts.js` — no silver POS table
 * carries a sales or velocity column — so they come back present and empty rather than
 * confident on demo data. See PageAwaitingData for the full reasoning.
 */
const AWAITING = {
  recommendations: 'demand',
  orders: 'demand',
  'store-layout': 'demand',
  'shelf-plan': 'demand',
  prices: 'catalogue',
  assortment: 'catalogue',
  products: 'catalogue',
  dashboard: 'catalogue',
  report: 'catalogue',
  expiry: 'expiry',
}

/**
 * One spine: the engine's artefact, plus the owner's state. Nothing else.
 *
 * This replaced two — a demo spine that compiled 4.36 MB of pipeline data into the bundle
 * and computed its own recommendations, and an operational spine reading a second artefact.
 * Every figure on every page now comes from `dashboard.json`, so a number the owner asks
 * about has exactly one place it could have come from.
 *
 * `operational.json` is no longer read at all. It was fetched for the receiving page's
 * expiry buckets, and those are every one of them zero — nothing has been recorded yet — so
 * the summary came off under D-3 and the fetch with it. The file keeps being WRITTEN for one
 * release so a rolled-back browser still works (§20.2); Phase 4 stops that too.
 */
export default function App() {
  const { t } = useI18n()
  const [activePage, setActivePage] = useState('operational')
  const [load, setLoad] = useState({ status: 'loading', artefact: null, reason: null })
  const [ownerState, setOwnerState] = useState(() => loadOwnerState())

  useEffect(() => {
    let live = true
    loadDashboard().then((next) => { if (live) setLoad(next) })
    return () => { live = false }
  }, [])

  const refreshOwnerState = useCallback(() => setOwnerState({ ...loadOwnerState() }), [])

  // `onOutcome` and `onAnswer` went with DailyPage and QuestionPanel, which the restored
  // nav does not route. `recordOutcome` is still the write path — it is reached through
  // `onDecide` below, so the engine still reads what the owner decides.

  // Every artefact entry by its id, so a decision made on a restored page can be recorded
  // with the `signal_family` ADR-016 requires — `entry_id` is a hash with no inverse, so an
  // outcome written without it loses the only durable grouping key F13 will have.
  const entriesById = useMemo(() => {
    const index = new Map()
    for (const cap of Object.values(load.artefact?.capabilities || {})) {
      for (const entry of cap.entries || []) index.set(entry.id, entry)
    }
    return index
  }, [load.artefact])

  /**
   * A decision taken on a restored page, written where the engine will actually read it.
   *
   * `OperationalPage` keeps its own cache in `smartshelf.operationalActions.v1` and tells us
   * afterwards. That cache is now a UI convenience, not the record: this writes through to
   * `smartshelf.ownerState.v2`, which is what `compose.js` suppresses on, what #95 pushes to
   * Firestore, and what the engine's owner-state pull reads.
   *
   * The two stores do not diverge, because the ids are the same one. The old UI used to key
   * on `recommendation_id` and the new UI on ADR-009's `entry_id`, two spaces with an
   * intersection of exactly zero — but `artefactToOperational` carries `entry.id` straight
   * through, so a restored page decides against the engine's own id. Without that, an outcome
   * recorded here would reach Firestore under an id no capability entry has, never suppress
   * anything, and still be counted by whatever F13 measures.
   */
  const onDecide = useCallback(async (decision) => {
    const entry = entriesById.get(decision?.id)
    if (!entry) return            // not ours to record; the page keeps its local cache
    const status = decision.status === 'DONE' ? 'acted'
      : decision.status === 'SNOOZED' ? 'deferred'
        : 'declined'
    await recordOutcome(entry, {
      status,
      reason: status === 'declined' ? (decision.reason ?? 'not_worth_it') : null,
      deferredUntil: status === 'deferred' ? (decision.snoozeUntil ?? null) : null,
    })
    refreshOwnerState()
  }, [entriesById, refreshOwnerState])

  // `catalog` and `competitor` are the keys AppShell reads, and they are the whole reason
  // this object exists in the shape it does. Until #111 this returned only generatedAt /
  // population / run, so `dataProvenance?.catalog === 'real'` was `undefined === 'real'`,
  // and the owner's real figures were captioned "Demo data" from the cut-over onwards.
  //
  // They are derived from the artefact's own vintages rather than hard-coded true: V1 has
  // no demo path — loadDashboard reads the engine artefact and nothing else — but saying
  // "real" should still rest on the artefact saying where the data came from, not on the
  // assumption that it must have.
  const provenance = useMemo(() => {
    const artefact = load.artefact
    if (!artefact) return null
    const vintages = artefact.vintages || {}
    return {
      catalog: vintages.pos?.file ? 'real' : null,
      competitor: vintages.competitor?.snapshot_date ? 'real' : null,
      generatedAt: artefact.generated_at,
      population: artefact.population,
      run: artefact.run?.status,
    }
  }, [load.artefact])

  const body = () => {
    if (load.status === 'loading') return <p className="spine__loading">{t('spine.loading')}</p>

    // Unreachable or invalid is a state we render, never a reason to show older numbers.
    if (load.status !== 'ok') {
      return (
        <section className="spine__unreadable" data-load-status={load.status}>
          <h2>{t('spine.unreadable.title')}</h2>
          <p>{t(`spine.unreadable.${load.status}`)}</p>
        </section>
      )
    }

    const artefact = load.artefact

    // The old Today page, fed by the live engine rather than the frozen operational.json.
    // The adapter also enforces D-1 on the way through: `CHECK_STOCK_DISCREPANCY` arrives
    // with no cost, so the old ranker states no figure rather than the ₪103,828.75 it would
    // otherwise compute from stock counts the manager says are unreliable.
    if (activePage === 'operational') {
      return (
        <OperationalPage
          operationalData={artefactToOperational(artefact)}
          actions={ownerState.outcomes || {}}
          onDecide={onDecide}
        />
      )
    }
    if (activePage === 'data-source') {
      return <DataPage artefact={artefact} />
    }
    if (AWAITING[activePage]) {
      return <PageAwaitingData pageId={activePage} needs={AWAITING[activePage]} />
    }
    return null
  }

  return (
    <AppShell
      activePage={activePage}
      dataProvenance={provenance}
      hasDemoState={false}
      onResetDemoState={null}
      onNavigate={setActivePage}
    >
      {body()}
    </AppShell>
  )
}
