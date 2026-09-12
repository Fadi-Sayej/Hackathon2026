import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'

import { AppShell } from './components/layout/AppShell.jsx'
import { ExpiryPage } from './pages/ExpiryPage.jsx'
import { SmoothScrollProvider } from './lib/motion/SmoothScrollProvider.jsx'
import { loadDashboard } from './lib/dataAdapters/loadDashboard.js'
import { loadOperationalData, EMPTY_OPERATIONAL_DATA } from './lib/dataAdapters/loadOperationalData.js'
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
 * `operational.json` is still fetched, and only for the receiving page's expiry buckets,
 * which no capability publishes yet. It keeps being written for one release so a rolled-back
 * browser still works (§20.2); Phase 4 removes both it and this import.
 */
export default function App() {
  const { t } = useI18n()
  const [activePage, setActivePage] = useState('daily')
  const [load, setLoad] = useState({ status: 'loading', artefact: null, reason: null })
  const [operationalData, setOperationalData] = useState(EMPTY_OPERATIONAL_DATA)
  const [ownerState, setOwnerState] = useState(() => loadOwnerState())

  // The clock is read once, here, and passed down. A component that reads it renders
  // differently on two identical inputs, and a deferral must lapse because time passed in
  // the app's state rather than because something re-rendered.
  const [now] = useState(() => Date.now())

  useEffect(() => {
    let live = true
    loadDashboard().then((next) => { if (live) setLoad(next) })
    loadOperationalData()
      .then((data) => { if (live && data) setOperationalData(data) })
      .catch(() => {})
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

  const provenance = useMemo(() => {
    const artefact = load.artefact
    if (!artefact) return null
    return {
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
      return <ExpiryPage operationalData={operationalData} />
    }
    if (CAPABILITY_PAGES.has(activePage)) {
      return <CapabilityPage artefact={artefact} capabilityId={activePage} />
    }
    return null
  }

  return (
    <SmoothScrollProvider>
      <AppShell
        activePage={activePage}
        dataProvenance={provenance}
        hasDemoState={false}
        onResetDemoState={null}
        onNavigate={setActivePage}
      >
        {body()}
      </AppShell>
    </SmoothScrollProvider>
  )
}
