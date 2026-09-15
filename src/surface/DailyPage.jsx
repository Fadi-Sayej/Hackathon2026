import { useCallback, useMemo, useState } from 'react'
import { useI18n } from '../lib/i18n/index.js'
import { formatCurrency } from '../components/shared/formatters.js'
import { compose } from './compose.js'
import { EntryCard } from './EntryCard.jsx'

/**
 * The daily surface. Renders what compose returns and owns no selection.
 *
 * The three states are distinct and none of them is a blank page:
 *   - entries to act on
 *   - an explicit nothing-to-do (AC-108)
 *   - one or more capabilities unavailable, each named with its reason (AC-107)
 *
 * The last two can occur together, and "nothing to act on" is never shown while something
 * could not be computed — that would report an absence of findings where there was an
 * absence of data.
 *
 * `now` is supplied by the caller and never read from the clock here. A component that
 * reads the clock is impure and renders differently on two identical inputs, which is also
 * why compose takes it as a parameter — a deferral that lapses must do so because time
 * passed in the app's state, not because a component happened to re-render.
 */
export function DailyPage({ artefact, ownerState, onOutcome, now }) {
  const { t } = useI18n()
  const [error, setError] = useState(null)

  const { entries, unavailable, nothingToDo } = useMemo(
    () => compose(artefact, ownerState, { now }),
    [artefact, ownerState, now],
  )

  const handleOutcome = useCallback(async (entry, outcome) => {
    try {
      // §9.3: the entry leaves the surface only after the write succeeds. An outcome the
      // owner believes is recorded, which is not, is worse than an error.
      await onOutcome(entry, outcome)
      setError(null)
    } catch (cause) {
      setError(cause?.message || t('outcome.failed'))
    }
  }, [onOutcome, t])

  // No heading inside this section. AppShell's topbar already renders
  // `page.daily.title`, and `daily.title` is the same string — the live page showed
  // "Today's work" twice, once in the chrome and once at the top of the list. The
  // section is labelled instead, so the landmark keeps its name for a screen reader
  // without printing a second copy for everyone else.
  return (
    <section className="daily" aria-label={t('daily.title')}>

      {error ? <p role="alert" className="daily__error">{t('outcome.failed')}</p> : null}

      {unavailable.length > 0 ? (
        <ul className="daily__unavailable" aria-label={t('daily.unavailable')}>
          {unavailable.map(({ id, reason }) => (
            <li key={id} data-capability={id}>
              {t(`capability.${id}`)} — {t(`unavailable.${reason}`)}
            </li>
          ))}
        </ul>
      ) : null}

      {entries.length > 0 ? (
        <ol className="daily__entries">
          {entries.map((entry) => (
            <li key={entry.id}>
              <EntryCard entry={entry} onOutcome={handleOutcome} formatMoney={formatCurrency} />
            </li>
          ))}
        </ol>
      ) : null}

      {nothingToDo ? <p className="daily__empty">{t('daily.nothingToDo')}</p> : null}
    </section>
  )
}
