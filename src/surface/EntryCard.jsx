import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'

/**
 * One entry on the daily surface.
 *
 * Renders what it is given and decides nothing: selection is compose's (AC-100 … AC-109).
 *
 * Two rules the markup enforces rather than documents:
 *   - an estimated value is labelled **on the card**, not in a legend (AC-104)
 *   - an entry with no value renders no value area at all — not a dash, not a zero, not an
 *     empty currency symbol (D-3). Absence is shown by absence.
 */
export function EntryCard({ entry, onOutcome, formatMoney }) {
  const { t } = useI18n()
  const value = entry.value && Number.isFinite(entry.value.amount) ? entry.value : null
  const estimated = value?.certainty === 'estimated'

  return (
    <article className="entry-card" data-capability={entry.capability} data-entry-id={entry.id} {...dirProps()}>
      <header className="entry-card__head">
        <h3 className="entry-card__name">{entry.product_name || entry.barcode || t('entry.unnamed')}</h3>
        {entry.department ? <p className="entry-card__dept">{entry.department}</p> : null}
      </header>

      <p className="entry-card__what">{t(`characterisation.${entry.characterisation}`)}</p>

      {value ? (
        <p className="entry-card__value" data-kind={value.kind} data-certainty={value.certainty}>
          <span className="entry-card__amount">{formatMoney(value.amount)}</span>
          <span className="entry-card__kind">{t(`value.kind.${value.kind}`)}</span>
          {/* AC-104: on the card itself. A reader who never looks at a legend must still
              know this number is an estimate. */}
          {estimated ? <span className="entry-card__estimated">{t('value.estimated')}</span> : null}
        </p>
      ) : null}

      <dl className="entry-card__evidence">
        {Object.entries(entry.evidence || {}).map(([key, raw]) => (
          <div key={key}>
            <dt>{t(`evidence.${key}`)}</dt>
            <dd>{typeof raw === 'boolean' ? t(raw ? 'common.yes' : 'common.no') : String(raw)}</dd>
          </div>
        ))}
      </dl>

      <footer className="entry-card__actions">
        <button type="button" data-outcome="acted" onClick={() => onOutcome(entry, { status: 'acted' })}>
          {t('outcome.acted')}
        </button>
        <button type="button" data-outcome="declined"
                onClick={() => onOutcome(entry, { status: 'declined', reason: 'not_worth_it' })}>
          {t('outcome.declined')}
        </button>
        <button type="button" data-outcome="deferred" onClick={() => onOutcome(entry, { status: 'deferred' })}>
          {t('outcome.deferred')}
        </button>
      </footer>
    </article>
  )
}
