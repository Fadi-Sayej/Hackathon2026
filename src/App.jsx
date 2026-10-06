import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
// The daily surface's own rules. Task 2.7 shipped its class names and no stylesheet.
import './surface/surface.css'
// …and the other nine V1 pages, which had the same omission.
import './surface/pages.css'

import { AppShell } from './components/layout/AppShell.jsx'
import { loadDashboard } from './lib/dataAdapters/loadDashboard.js'
import { loadCatalogue } from './lib/dataAdapters/loadCatalogue.js'
import { catalogueToProducts } from './lib/dataAdapters/catalogueToProducts.js'
import { analyzeProducts } from './lib/analytics/inventoryEngine.js'
import { ProductsPage } from './pages/ProductsPage.jsx'
import { PriceGapPage } from './pages/PriceGapPage.jsx'
import { ReceivingPage } from './pages/ReceivingPage.jsx'
import { clearOutcome, loadOwnerState, recordAnswer, recordOutcome } from './owner/ownerState.js'
import { DailyPage } from './surface/DailyPage.jsx'
import { QuestionPanel } from './questions/QuestionPanel.jsx'
import { DataPage } from './pages/DataPage.jsx'
import { CapabilityPage } from './pages/CapabilityPage.jsx'
import { PageAwaitingData } from './pages/PageAwaitingData.jsx'
import { useI18n } from './lib/i18n/index.js'
import { useAuth } from './auth/useAuth.js'
import { TeamBanner } from './auth/SignInPage.jsx'

// Loaded when first opened, not with the app: the owner's first screen is Today, and these four
// (the order pages and the planogram's) added ~70 KB to it in a week. Each has its own chunk.
const ReorderPage = lazy(() => import('./pages/ReorderPage.jsx').then((m) => ({ default: m.ReorderPage })))
const ApprovedOrdersPage = lazy(() => import('./pages/ApprovedOrdersPage.jsx').then((m) => ({ default: m.ApprovedOrdersPage })))
const StoreLayoutPage = lazy(() => import('./pages/StoreLayoutPage.jsx').then((m) => ({ default: m.StoreLayoutPage })))
const ShelfPlanPage = lazy(() => import('./pages/ShelfPlanPage.jsx').then((m) => ({ default: m.ShelfPlanPage })))

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
/** Nav ids that are a capability rendered whole by CapabilityPage (FR-102, AC-110). */
const CAPABILITY_PAGES = new Set([
  'price_consistency', 'margin_below_cost', 'reconciliation',
  'hygiene', 'catalogue_lifecycle', 'competitor_position',
])

/** Pages that fetch `catalogue.json`. Everything else never pays for it. */
const NEEDS_CATALOGUE = new Set(['products', 'prices', 'expiry', 'orders', 'store-layout', 'shelf-plan'])

const AWAITING = {
  // Reorder and Approved orders left this map in Phase 5 Task 5.13: F8 publishes what they
  // show, and each page says what it waits for in the capability's own reason.
  // Reached only when `catalogue.json` cannot be read — the products branch below returns
  // before this map is consulted. So this is the failed-load state, not a "not published yet".
  products: 'catalogue',
  // NOT 'catalogue' either, and for the same reason as prices: the catalogue is published and
  // Overview still cannot render. It takes nine props, and `stockoutOpportunities`,
  // `priceLeaderProducts` and the HIGH-urgency `recommendations` it filters are all
  // velocity-derived. Demand is the honest blocker and it is the one that does not arrive.
  dashboard: 'demand',
  // Not 'catalogue'. A catalogue would let this RENDER, and that is the trap: it would then
  // look finished while resting on nothing anyone decided.
  //   (assortment left this map in Phase 6 Task 6.5: D-25 settled F9, and F9-S1 keys on the
  //   market running out and on his catalogue, never on absence from the sales reports.)
  //   report      the LLM layer is REMOVE in design §20.1 — no document says what the report
  //               should claim or how it would be checked, and D-12 forbids a runtime server
  //               for one store. It is withdrawn, not postponed, and says so.
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
  // ADR-029 §5: a team account sees this app read-only. Its controls are disabled and these
  // handlers refuse, so a team click never reaches owner state; the Firestore rules refuse
  // the write as well.
  const { readOnly } = useAuth()
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

  // The receiving form's product lookup: a scanned barcode shows its name before the line is
  // saved, which is how a mis-scan is caught. It used to be handed an empty list, so every
  // scan read "not found in the catalog" whatever the barcode.
  const receivingProducts = useMemo(
    () => (catalogue.catalogue?.products || [])
      .filter((p) => p.barcode)
      .map((p) => ({ id: String(p.barcode), name: p.product_name })),
    [catalogue.catalogue],
  )

  const refreshOwnerState = useCallback(() => setOwnerState({ ...loadOwnerState() }), [])

  // Throws on a failed cache write, by design: the entry leaves the surface only after the
  // write succeeds (§9.3). `onDecide` below is the same write path reached from a restored
  // page, which keys on the same ADR-009 entry id, so the two surfaces cannot disagree about
  // what the owner has already dealt with.
  const onOutcome = useCallback(async (entry, outcome) => {
    if (readOnly) return
    await recordOutcome(entry, outcome)
    refreshOwnerState()
  }, [readOnly, refreshOwnerState])

  // Taking an outcome back. Needed because "Later" sends no date and an outcome with no
  // `deferred_until` is deferred forever, so the gentlest-sounding button on the surface
  // was the destructive one (OQ-604, #139).
  const onUndoOutcome = useCallback(async (entryId) => {
    if (readOnly) return
    await clearOutcome(entryId)
    refreshOwnerState()
  }, [readOnly, refreshOwnerState])

  // The owner's answer to a cost question. It throws on an unusable value or a failed cache
  // write, and QuestionPanel keeps what he typed when it does (§9.3).
  const onAnswer = useCallback(async (barcode, fact, answer) => {
    if (readOnly) return
    await recordAnswer(barcode, fact, answer)
    refreshOwnerState()
  }, [readOnly, refreshOwnerState])

  // `entriesById` and `onDecide` went with the old Today page on 2026-09-23. They existed to
  // let a restored page record against the engine's own ADR-009 entry id; the daily surface
  // reaches `recordOutcome` through `onOutcome` directly and never needed the index.

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
      // The cost questions sit at the top of Today, above the action list: the repository
      // owner's decision on 2026-09-23, which settles OQ-503. They had no screen at all from
      // 2026-09-16, when the twelve-page restore took them out of App with the daily surface
      // and only the daily surface came back.
      return (
        <>
          <QuestionPanel artefact={artefact} answers={ownerState.answers} onAnswer={onAnswer}
            readOnly={readOnly} />
          <DailyPage artefact={artefact} ownerState={ownerState} onOutcome={onOutcome}
            onUndoOutcome={readOnly ? null : onUndoOutcome} now={now} readOnly={readOnly} />
        </>
      )
    }

    if (CAPABILITY_PAGES.has(activePage)) {
      return <CapabilityPage artefact={artefact} capabilityId={activePage} />
    }
    // F9 (F6-S1 FR-102): the whole set, on the nav item it always had.
    if (activePage === 'assortment') {
      return <CapabilityPage artefact={artefact} capabilityId="assortment_gap" />
    }
    if (activePage === 'recommendations') {
      return <ReorderPage artefact={artefact} ownerState={ownerState} onOutcome={onOutcome} now={now}
        readOnly={readOnly} />
    }
    if (activePage === 'orders') {
      if (catalogue.status === 'loading' || catalogue.status === 'idle') {
        return <p className="spine__loading">{t('spine.loading')}</p>
      }
      // Without the catalogue the lines still list, by barcode: his approvals are his, and a
      // missing product name is no reason to hide them.
      return <ApprovedOrdersPage ownerState={ownerState} catalogue={catalogue.catalogue} now={now} />
    }
    // F12 (F12-S1 FR-191, FR-194): his shelves as measured, and the plan made from them. Both
    // name products from the catalogue, and wait for it, as Approved orders does.
    if (activePage === 'store-layout' || activePage === 'shelf-plan') {
      if (catalogue.status === 'loading' || catalogue.status === 'idle') {
        return <p className="spine__loading">{t('spine.loading')}</p>
      }
      return activePage === 'store-layout'
        ? <StoreLayoutPage artefact={artefact} catalogue={catalogue.catalogue} />
        : <ShelfPlanPage artefact={artefact} ownerState={ownerState} catalogue={catalogue.catalogue}
          onOutcome={onOutcome} onUndoOutcome={readOnly ? null : onUndoOutcome} readOnly={readOnly} />
    }
    if (activePage === 'data-source') {
      return (
        <DataPage artefact={artefact} ownerState={ownerState} onRestore={onUndoOutcome} now={now}
          readOnly={readOnly} />
      )
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
    // Prices, on the comparison the nightly publishes since 2026-09-23 (ADR-025) and the
    // catalogue for its names. Until then it sat on an awaiting state that said the file
    // "publishes findings, not comparisons" — true when written, false the morning after.
    if (activePage === 'prices') {
      if (catalogue.catalogue) {
        return (
          <PriceGapPage artefact={artefact} catalogue={catalogue.catalogue} now={now}
            onOpenFinding={() => setActivePage('competitor_position')} />
        )
      }
      if (catalogue.status === 'loading' || catalogue.status === 'idle') {
        return <p className="spine__loading">{t('spine.loading')}</p>
      }
      return <PageAwaitingData pageId={activePage} needs="catalogue" />
    }
    // The receiving capture, below the Expiry page's waiting note: the repository owner's
    // decision on 2026-09-24. The 2026-09-16 restore had removed it with the `receiving` nav
    // entry, and left a note saying the page "fills as the receiving screen is used".
    if (activePage === 'expiry') {
      return (
        <>
          <PageAwaitingData pageId={activePage} needs="expiry" />
          <ReceivingPage products={receivingProducts} />
        </>
      )
    }
    if (AWAITING[activePage]) {
      return <PageAwaitingData pageId={activePage} needs={AWAITING[activePage]} />
    }
    return null
  }

  return (
    <AppShell
      activePage={activePage}
      notice={readOnly ? <TeamBanner /> : null}
      dataProvenance={provenance}
      hasDemoState={false}
      onResetDemoState={null}
      onNavigate={setActivePage}
    >
      <Suspense fallback={<p className="spine__loading">{t('spine.loading')}</p>}>
        {body()}
      </Suspense>
    </AppShell>
  )
}
