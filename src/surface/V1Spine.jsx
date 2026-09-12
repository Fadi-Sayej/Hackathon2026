import { useCallback, useEffect, useState } from 'react'
import { loadDashboard } from '../lib/dataAdapters/loadDashboard.js'
import { loadOwnerState, recordAnswer, recordOutcome } from '../owner/ownerState.js'
import { useI18n } from '../lib/i18n/index.js'
import { CapabilityPage } from '../pages/CapabilityPage.jsx'
import { DataPage } from '../pages/DataPage.jsx'
import { QuestionPanel } from '../questions/QuestionPanel.jsx'
import { DailyPage } from './DailyPage.jsx'
import { CAPABILITY_PAGES } from './pages.js'

/**
 * The V1 spine: the artefact plus owner state, and nothing else.
 *
 * It is NOT the app's default. The owner's screen still reads `operational.json` through
 * the existing spine, because every price figure in `dashboard.json` is computed over the
 * living catalogue — 3,903 products withdrawn — and D-14 forbids putting a figure that
 * depends on automatic withdrawal in front of him until GAP-009 closes.
 *
 * So this is reachable, testable and complete, and it is not what he sees. The cut-over
 * (plan Task 2.7, §20.2) is a one-line change here once GAP-009 is answered.
 *
 * `now` comes from the host. A component that reads the clock renders differently on two
 * identical inputs, and a deferral must lapse because time passed in the app's state, not
 * because something happened to re-render.
 */

export function V1Spine({ page = 'daily', fetchImpl, now }) {
  const { t } = useI18n()
  const [load, setLoad] = useState({ status: 'loading', artefact: null, reason: null })
  const [ownerState, setOwnerState] = useState(() => loadOwnerState())

  useEffect(() => {
    let live = true
    loadDashboard(fetchImpl ? { fetchImpl } : {}).then((next) => { if (live) setLoad(next) })
    return () => { live = false }
  }, [fetchImpl])

  const refresh = useCallback(() => setOwnerState({ ...loadOwnerState() }), [])

  const onOutcome = useCallback(async (entry, outcome) => {
    await recordOutcome(entry, outcome)   // throws on a failed cache write, by design (§9.3)
    refresh()
  }, [refresh])

  const onAnswer = useCallback(async (barcode, answer) => {
    await recordAnswer(barcode, answer)
    refresh()
  }, [refresh])

  if (load.status === 'loading') return <p className="spine__loading">{t('spine.loading')}</p>

  // An unreachable or invalid artefact is a state, never a reason to show older numbers.
  if (load.status !== 'ok') {
    return (
      <section className="spine__unreadable" data-load-status={load.status}>
        <h2>{t('spine.unreadable.title')}</h2>
        <p>{t(`spine.unreadable.${load.status}`)}</p>
      </section>
    )
  }

  const artefact = load.artefact

  if (page === 'daily') {
    return <DailyPage artefact={artefact} ownerState={ownerState} onOutcome={onOutcome} now={now} />
  }
  if (page === 'questions') {
    return <QuestionPanel artefact={artefact} onAnswer={onAnswer} />
  }
  if (page === 'data') {
    return <DataPage artefact={artefact} />
  }
  if (CAPABILITY_PAGES.has(page)) {
    return <CapabilityPage artefact={artefact} capabilityId={page} />
  }
  return null
}
