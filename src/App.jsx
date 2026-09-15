import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'
// The daily surface's own rules. Task 2.7 shipped its class names and no stylesheet.
import './surface/surface.css'
// …and the other nine V1 pages, which had the same omission.
import './surface/pages.css'

import { AppShell } from './components/layout/AppShell.jsx'
import { ReceivingPage } from './pages/ReceivingPage.jsx'
import { loadDashboard } from './lib/dataAdapters/loadDashboard.js'
import { loadOwnerState, recordAnswer, recordOutcome } from './owner/ownerState.js'
import { CapabilityPage } from './pages/CapabilityPage.jsx'
import { DataPage } from './pages/DataPage.jsx'
import { QuestionPanel } from './questions/QuestionPanel.jsx'
import { DailyPage } from './surface/DailyPage.jsx'
import { CAPABILITY_PAGES } from './surface/pages.js'
import { useI18n } from './lib/i18n/index.js'

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
  const [activePage, setActivePage] = useState('daily')
  const [load, setLoad] = useState({ status: 'loading', artefact: null, reason: null })
  const [ownerState, setOwnerState] = useState(() => loadOwnerState())

  // The clock is read once, here, and passed down. A component that reads it renders
  // differently on two identical inputs, and a deferral must lapse because time passed in
  // the app's state rather than because something re-rendered.
  const [now] = useState(() => Date.now())

  useEffect(() => {
    let live = true
    loadDashboard().then((next) => { if (live) setLoad(next) })
    return () => { live = false }
  }, [])

  const refreshOwnerState = useCallback(() => setOwnerState({ ...loadOwnerState() }), [])

  const onOutcome = useCallback(async (entry, outcome) => {
    // Throws on a failed cache write, by design: the entry leaves the surface only after
    // the write succeeds (§9.3).
    await recordOutcome(entry, outcome)
    refreshOwnerState()
  }, [refreshOwnerState])

  const onAnswer = useCallback(async (barcode, answer) => {
    await recordAnswer(barcode, answer)
    refreshOwnerState()
  }, [refreshOwnerState])

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
    if (activePage === 'daily') {
      return (
        <DailyPage artefact={artefact} ownerState={ownerState} onOutcome={onOutcome} now={now} />
      )
    }
    if (activePage === 'questions') {
      return <QuestionPanel artefact={artefact} onAnswer={onAnswer} />
    }
    if (activePage === 'data') {
      return <DataPage artefact={artefact} />
    }
    if (activePage === 'receiving') {
      return <ReceivingPage />
    }
    if (CAPABILITY_PAGES.has(activePage)) {
      return <CapabilityPage artefact={artefact} capabilityId={activePage} />
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
