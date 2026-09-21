import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
// The daily surface's own rules. Task 2.7 shipped its class names and no stylesheet.
import './surface/surface.css'
// …and the other nine V1 pages, which had the same omission.
import './surface/pages.css'

import { AppShell } from './components/layout/AppShell.jsx'
import { loadDashboard } from './lib/dataAdapters/loadDashboard.js'
import { artefactToOperational } from './lib/dataAdapters/artefactToOperational.js'
import { loadCatalogue } from './lib/dataAdapters/loadCatalogue.js'
import { catalogueToProducts } from './lib/dataAdapters/catalogueToProducts.js'
import { analyzeProducts } from './lib/analytics/inventoryEngine.js'
import { ProductsPage } from './pages/ProductsPage.jsx'
import { loadOwnerState, recordOutcome } from './owner/ownerState.js'
import { DailyPage } from './surface/DailyPage.jsx'
import { OperationalPage } from './pages/OperationalPage.jsx'
import { DataPage } from './pages/DataPage.jsx'
import { PageAwaitingData } from './pages/PageAwaitingData.jsx'
import { useI18n } from './lib/i18n/index.js'

/**
 * What each restored page is waiting for, when the artefact cannot feed it.
 *
 * Reorder, Approved orders, Store layout and Shelf plan rank by how fast a product sells
 * per day, and that is not a column anyone forgot to add. `sales_monthly.parquet` carries
 * units, receipts and revenue — but one row per product per MONTH, with no date column in
 * any of the seven reports, so a daily rate is not measurable (rule 13).
 *
 * This repository has already built the table that would light these pages:
 * `silver_pos/yomyom_sales.parquet`, whose `units_sold_30d` Task 0.6 deleted for being
 * synthesised from a monthly mean (rule 5). Rebuilding it to fill these screens would put
 * that invented figure back. So they come back present and empty rather than confident.
 */
/** Pages that fetch `catalogue.json`. Everything else never pays for it. */
const NEEDS_CATALOGUE = new Set(['products'])

const AWAITING = {
  recommendations: 'demand',
  orders: 'demand',
  'store-layout': 'demand',
  'shelf-plan': 'demand',
  prices: 'catalogue',
  products: 'catalogue',
  dashboard: 'catalogue',
  // Not 'catalogue'. A catalogue would let these two RENDER, and that is the trap: both
  // would then look finished while resting on nothing anyone decided.
  //   assortment  F9 is `Registered — not specified`, and the protocol forbids writing the
  //               spec until a named decision is taken. GAP-009 is the blocker, and it is
  //               measured: the gap rule would key on absence from the sales reports, which
  //               covers 5,848 of 7,463 products because the reports reach 24.3% of the
  //               catalogue (rule 13). Lighting it would answer a question nobody settled.
  //   report      the LLM layer is REMOVE in design §20.1 — no document says what the report
  //               should claim or how it would be checked, and D-12 forbids a runtime server
  //               for one store. It is withdrawn, not postponed, and says so.
  assortment: 'decision',
  report: 'withdrawn',
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
  // The daily surface stays the landing page. Restoring the twelve pages took it off the
  // nav entirely, and with it AC-100 (ten places, all filled), AC-103 (per-sale and one-off
  // money never interleaved), AC-105 (an outcome survives a reload), AC-107 (unavailable
  // never reads as zero), AC-109 (no product twice) and AC-112 (three languages on a phone).
  // Twelve e2e tests caught that; the owner never asked for it and was never offered it.
  const [activePage, setActivePage] = useState('daily')
  const [now] = useState(() => Date.now())
  const [load, setLoad] = useState({ status: 'loading', artefact: null, reason: null })
  const [ownerState, setOwnerState] = useState(() => loadOwnerState())

  useEffect(() => {
    let live = true
    loadDashboard().then((next) => { if (live) setLoad(next) })
    return () => { live = false }
  }, [])

  /**
   * The catalogue, fetched only by the pages that need it and only once.
   *
   * 7,523 products is 1.73 MB raw. The daily surface — the screen the owner opens every
   * morning — needs none of it, and `vercel.json` used to serve `/data/*` with `no-store`,
   * which would have made that a fresh download on every page view. So this is deliberately
   * NOT fetched beside the artefact: `status: 'idle'` until someone opens a page that lists
   * products (ADR-024).
   */
  const [catalogue, setCatalogue] = useState({ status: 'idle', catalogue: null, reason: null })
  // A ref, not the status, because the status is what the effect SETS. Guarding on
  // `catalogue.status !== 'idle'` with it in the dependency list made the effect re-run the
  // instant it set 'loading', and the first run's cleanup then discarded the fetch that was
  // already in flight — the page sat on "Reading today's numbers…" forever. The ref is not
  // state the render reads, so setting it starts nothing.
  const catalogueRequested = useRef(false)

  useEffect(() => {
    if (!NEEDS_CATALOGUE.has(activePage) || catalogueRequested.current) return
    catalogueRequested.current = true
    setCatalogue({ status: 'loading', catalogue: null, reason: null })
    // Deliberately not cancelled on cleanup. App is the root and never unmounts, so the only
    // thing a cancel could do here is drop a result we asked for and never ask again.
    loadCatalogue().then(setCatalogue)
  }, [activePage])

  /**
   * Catalogue rows through the real analytics engine, memoised because it is 7,523 of them.
   *
   * `analyzeProducts` gates every velocity-derived verdict behind `hasVelocity`, and the
   * catalogue carries no sales fields at all, so each product reports `daysUntilStockout:
   * null` and a `noVelocityData` status rather than a confident "Healthy". What it DOES
   * compute is margin, which needs no velocity and has both prices — so the page is useful
   * and honest at the same time, which was the open question before it was measured.
   */
  const analyzedProducts = useMemo(() => {
    const rows = catalogueToProducts(catalogue.catalogue)
    return rows ? analyzeProducts(rows, {}) : null
  }, [catalogue.catalogue])

  const refreshOwnerState = useCallback(() => setOwnerState({ ...loadOwnerState() }), [])

  // Throws on a failed cache write, by design: the entry leaves the surface only after the
  // write succeeds (§9.3). `onDecide` below is the same write path reached from a restored
  // page, which keys on the same ADR-009 entry id, so the two surfaces cannot disagree about
  // what the owner has already dealt with.
  const onOutcome = useCallback(async (entry, outcome) => {
    await recordOutcome(entry, outcome)
    refreshOwnerState()
  }, [refreshOwnerState])

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

    // The V1 daily surface — the owner's first screen, and the one the pilot's acceptance
    // criteria are written against. It is kept alongside the restored pages rather than
    // replaced by them: removing it was a consequence of the restore, not a request.
    if (activePage === 'daily') {
      return (
        <DailyPage artefact={artefact} ownerState={ownerState} onOutcome={onOutcome} now={now} />
      )
    }

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

    // Products, now that the catalogue exists. Falls back to the awaiting state rather than
    // to an empty table whenever the file is not readable — an empty product list is a claim
    // that the shop has no products, and `loadCatalogue` keeps that apart from a failed load.
    if (activePage === 'products') {
      if (analyzedProducts) return <ProductsPage analyzedProducts={analyzedProducts} />
      if (catalogue.status === 'loading' || catalogue.status === 'idle') {
        return <p className="spine__loading">{t('spine.loading')}</p>
      }
      return <PageAwaitingData pageId={activePage} needs="catalogue" />
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
