import { useCallback, useMemo, useState } from 'react'
import { unavailableReason } from '../lib/i18n/unavailableReason.js'
import { useI18n } from '../lib/i18n/index.js'
import { formatCurrency } from '../components/shared/formatters.js'
import { compose } from './compose.js'
import { settleOutcome } from './deferral.js'
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
export function DailyPage({ artefact, ownerState, onOutcome, onUndoOutcome, now }) {
  const { t } = useI18n()
  const [error, setError] = useState(null)
  // The last entry settled on this screen, so it can be taken back.
  //
  // "Later" is the reason this exists. It sends no date, and an outcome with no
  // `deferred_until` is deferred forever (compose.js:26) — so a mistaken tap on the button
  // that reads "Later" removed the entry permanently. OQ-604 predicted exactly that and is
  // still open; how long "later" lasts is the PM's call. This decides nothing and stops the
  // loss in the meantime. It covers Done and Dismiss too, at no extra cost.
  const [lastSettled, setLastSettled] = useState(null)

  const { entries, unavailable, nothingToDo } = useMemo(
    () => compose(artefact, ownerState, { now }),
    [artefact, ownerState, now],
  )

  const handleOutcome = useCallback(async (entry, outcome) => {
    try {
      // §9.3: the entry leaves the surface only after the write succeeds. An outcome the
      // owner believes is recorded, which is not, is worse than an error.
      // "Later" arrives from the card without a date — the card reports which button was
      // pressed and decides nothing. A dateless deferral is a permanent delete (#139), so
      // the surface, which is the thing that has `now`, says how long it lasts.
      await onOutcome(entry, settleOutcome(outcome, { now }))
      setLastSettled({ id: entry.id, name: entry.product_name || entry.barcode || entry.id,
        status: outcome?.status ?? null })
      setError(null)
    } catch (cause) {
      setError(cause?.message || t('outcome.failed'))
    }
  }, [onOutcome, t, now])

  const handleUndo = useCallback(async () => {
    if (!lastSettled || !onUndoOutcome) return
    try {
      await onUndoOutcome(lastSettled.id)
      setLastSettled(null)
      setError(null)
    } catch (cause) {
      setError(cause?.message || t('outcome.failed'))
    }
  }, [lastSettled, onUndoOutcome, t])

  // No heading inside this section. AppShell's topbar already renders
  // `page.daily.title`, and `daily.title` is the same string — the live page showed
  // "Today's work" twice, once in the chrome and once at the top of the list. The
  // section is labelled instead, so the landmark keeps its name for a screen reader
  // without printing a second copy for everyone else.
  return (
    <section className="daily" aria-label={t('daily.title')}>

      {error ? <p role="alert" className="daily__error">{t('outcome.failed')}</p> : null}

      {lastSettled && onUndoOutcome ? (
        /* `role="status"`, not `alert`: this is a confirmation with a way back, not a
           problem. It names the product, because "Undo" alone is useless once the card it
           referred to has gone from the list. */
        <p className="daily__undo" role="status">
          {t(`outcome.settled.${lastSettled.status || 'acted'}`, { name: lastSettled.name })}{' '}
          <button type="button" className="daily__undo-button" data-undo={lastSettled.id}
            onClick={handleUndo}>
            {t('outcome.undo')}
          </button>
        </p>
      ) : null}

      {unavailable.length > 0 ? (
        <ul className="daily__unavailable" aria-label={t('daily.unavailable')}>
          {unavailable.map(({ id, reason }) => (
            <li key={id} data-capability={id}>
              {t(`capability.${id}`)} — {unavailableReason(t, reason)}
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
