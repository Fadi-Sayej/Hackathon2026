import { useI18n } from '../lib/i18n/index.js'
import { formatWindowId } from '../lib/i18n/formatPeriod.js'
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
// Evidence the card shows as money: unit prices only, none derived from a stock quantity (D-1),
// and none summed with anything here (D-2).
const MONEY = new Set(['shelf_price', 'delivery_price', 'cost_price', 'difference', 'unit_cost'])
// The card's own line already asks this (characterisation), so it is not repeated as a row.
// Values rendered as a sentence, set in the text face: the monospace face is for figures, and
// spaces Arabic and Hebrew words apart.
const SENTENCE = new Set(['format_note', 'reference', 'sources', 'fields', 'evidence_state', 'cost_source', 'reason',
  // F9: store names, "n of the last 14 days", a date in words, and "none of them".
  'stores_ran_out', 'nights_ran_out', 'last_ran_out', 'listed_at', 'market_prices'])
const NOT_A_ROW = new Set(['question'])
// What he found when he checked an idle product (F4 FR-070, approved 2026-09-28).
const IDLE_ANSWERS = [
  { id: 'still_stocked', outcome: { status: 'acted', reason: 'still_stocked' } },
  { id: 'wrong_count', outcome: { status: 'declined', reason: 'wrong_data' } },
  { id: 'no_longer_carried', outcome: { status: 'acted', reason: 'no_longer_carried' } },
]
// Rows a capability's card folds into another or already shows. F9 (F9-S1 FR-175): the window is
// said inside the nights row, and the market's name is the card's own heading.
const FOLDED = { assortment_gap: new Set(['window', 'market_name']) }
// One signal family's own words, where the capability's shared ones do not say what is wrong.
// F1's inverted price (the owner's request, 2026-10-08): the delivery price is below the shelf
// price. Its line says so, its value says what each delivery order loses with the commission on
// top (F1-S1 FR-007), and it shows the two prices only. The difference, markup, ceiling and
// commission rows repeat that or belong to the other F1 card, a price above the ceiling.
const FAMILY = {
  'price.inverted': {
    what: 'characterisation.price_inverted',
    kind: 'value.kind.price_inverted',
    folded: new Set(['difference', 'markup_pct', 'ceiling_pct', 'commission_compounds']),
  },
}
// F9-S1 FR-173: F9's two answers, in its own words. "Not for my store" is a decline with no
// reason: it is his judgement of his customers, not a verdict that the finding was wrong.
const ANSWERS = {
  assortment_gap: { acted: 'outcome.assortment_gap.acted', declined: 'outcome.assortment_gap.declined', declineReason: null,
    // D-27: he already sells it, in another size or pack. Kept apart from "Not for my store".
    extra: [{ id: 'already_sold', label: 'outcome.assortment_gap.already_sold', outcome: { status: 'declined', reason: 'already_handled' } }] },
}
const DEFAULT_ANSWERS = { acted: 'outcome.acted', declined: 'outcome.declined', declineReason: 'not_worth_it' }
const LOCALE = { ar: 'ar-u-nu-latn', he: 'he-IL', en: 'en-GB' }
// Isolated left to right (U+2066 … U+2069), or Arabic and Hebrew render 7% as "%7".
const percent = (x) => `\u2066${Math.round(x * 10) / 10}%\u2069`

export function EntryCard({ entry, onOutcome, formatMoney, readOnly = false }) {
  const { t, language } = useI18n()
  const value = entry.value && Number.isFinite(entry.value.amount) ? entry.value : null
  const estimated = value?.certainty === 'estimated'
  // Every value in the owner's words (the 2026-09-28 validations): a period as months (F2-V7),
  // a price in shekels, a share with its sign, a code as the sentence it stands for. An object
  // or a list is never printed as it is: `[object Object]` was waiting for the first competitor
  // card to reach this surface.
  const family = FAMILY[entry.signal_family]
  const dayText = (iso) => new Intl.DateTimeFormat(LOCALE[language] || LOCALE.en, { day: 'numeric', month: 'long', timeZone: 'UTC' })
    .format(new Date(`${iso}T00:00:00Z`))
  const evidenceText = (key, raw) => {
    if (typeof raw === 'boolean') return t(raw ? 'common.yes' : 'common.no')
    if (key === 'window_id') return formatWindowId(raw, t, language)
    if (key === 'format_note') return t('evidence.format_note.text')
    if (key === 'sources' && Array.isArray(raw)) return t('evidence.sourcesCount', { n: raw.length })
    // F9-S1 FR-175: stores by name, how often of the recent days, and the last day, as a date.
    if (key === 'stores_ran_out' || key === 'listed_at') {
      return raw.length ? raw.join(t('common.listSeparator')) : t(`evidence.${key}.none`)
    }
    if (key === 'nights_ran_out') {
      return t('evidence.nights_ran_out.value', { n: raw, days: entry.evidence?.window?.days ?? '' })
    }
    if (key === 'last_ran_out') return dayText(raw)
    // D-27: what each nearby store lists it at on the delivery app, the sale price when there is
    // one, and the day, because a price seen a fortnight ago is not today's.
    if (key === 'market_prices') {
      // One store to a line: two stores' prices, sale prices, names and dates in one sentence
      // read as a run-on, and worse in Hebrew and Arabic, where the store names are Latin.
      return raw.map((q) => (
        <span key={q.store} className="entry-card__line">
          {t(q.sale_price ? 'evidence.market_prices.sale' : 'evidence.market_prices.item', {
            // The store name is isolated (U+2068 … U+2069): a Latin name in a Hebrew or Arabic
            // line would otherwise pull the comma and the date after it into its own run.
            price: formatMoney(q.price), sale: q.sale_price ? formatMoney(q.sale_price) : '', store: `\u2068${q.store}\u2069`, date: dayText(q.on),
          })}
        </span>
      ))
    }
    if (key === 'fields' && raw && typeof raw === 'object') {
      return Object.keys(raw).map((field) => t(`evidence.${field}`)).join(t('common.listSeparator'))
    }
    if (key === 'reference' && raw && typeof raw === 'object') {
      return t(`evidence.referenceKind.${raw.kind}`, {
        value: formatMoney(raw.value),
        supermarket: raw.supermarket == null ? '' : formatMoney(raw.supermarket),
        same: raw.same_format == null ? '' : formatMoney(raw.same_format),
        pct: raw.allowance_pct == null ? '' : percent(raw.allowance_pct),
      })
    }
    // The price stays a figure; how far below the shelf it is goes on a line of its own, in the
    // text face, or Hebrew and Arabic words are spaced apart and the two directions collide.
    if (key === 'delivery_price' && family && Number.isFinite(entry.evidence?.markup_pct)) {
      return (
        <>
          {formatMoney(raw)}
          <span className="entry-card__note">
            {t('evidence.delivery_price.below_shelf', { pct: percent(Math.abs(entry.evidence.markup_pct)) })}
          </span>
        </>
      )
    }
    if (typeof raw === 'number' && MONEY.has(key)) return formatMoney(raw)
    if (typeof raw === 'number' && key.endsWith('_pct')) return percent(raw)
    if (typeof raw === 'string' && ['evidence_state', 'cost_source', 'reason'].includes(key)) {
      return t(`evidence.${key}.${raw}`)
    }
    return String(raw)
  }
  // A value the engine does not have is left out, never printed as "null" (D-3): the card shows
  // absence by absence, as it does for the value above.
  const folded = new Set([...(FOLDED[entry.capability] || []), ...(family?.folded || [])])
  const rows = Object.entries(entry.evidence || {})
    .filter(([key, raw]) => raw != null && !NOT_A_ROW.has(key) && !folded.has(key)
      && !(key === 'market_prices' && Array.isArray(raw) && raw.length === 0))
  const answers = ANSWERS[entry.capability] || DEFAULT_ANSWERS

  return (
    <article className="entry-card" data-capability={entry.capability} data-entry-id={entry.id} {...dirProps()}>
      <header className="entry-card__head">
        <h3 className="entry-card__name">{entry.product_name || entry.barcode || t('entry.unnamed')}</h3>
        {entry.department ? <p className="entry-card__dept">{entry.department}</p> : null}
      </header>

      <p className="entry-card__what">{t(family?.what ?? `characterisation.${entry.characterisation}`)}</p>
      {/* F6 AC-110c: what to do, in his words. The engine chose it; the card only says it. */}
      {entry.action ? <p className="entry-card__action">{t(`action.${entry.action}`)}</p> : null}

      {value ? (
        <p className="entry-card__value" data-kind={value.kind} data-certainty={value.certainty}>
          <span className="entry-card__amount">{formatMoney(value.amount)}</span>
          <span className="entry-card__kind">{t(family?.kind ?? `value.kind.${value.kind}`)}</span>
          {/* AC-104: on the card itself. A reader who never looks at a legend must still
              know this number is an estimate. */}
          {estimated ? <span className="entry-card__estimated">{t('value.estimated')}</span> : null}
        </p>
      ) : null}

      <dl className="entry-card__evidence">
        {rows.map(([key, raw]) => (
          <div key={key} data-row={key}>
            <dt>{t(`evidence.${key}`)}</dt>
            <dd data-text={SENTENCE.has(key) ? '' : undefined}>{evidenceText(key, raw)}</dd>
          </div>
        ))}
      </dl>

      <footer className="entry-card__actions">
        {/* readOnly: a team account's view (ADR-029 §5). Nothing it presses is the owner's. */}
        {entry.action === 'decide_idle' ? IDLE_ANSWERS.map(({ id, outcome }) => (
          // F4 FR-070: an idle product is answered with what he found, each answer recorded
          // apart, and none of them called the right one (FR-071).
          <button key={id} type="button" data-outcome={id} disabled={readOnly} onClick={() => onOutcome(entry, outcome)}>
            {t(`outcome.idle.${id}`)}
          </button>
        )) : (
          <>
            <button type="button" data-outcome="acted" disabled={readOnly} onClick={() => onOutcome(entry, { status: 'acted' })}>
              {t(answers.acted)}
            </button>
            <button type="button" data-outcome="declined" disabled={readOnly}
                    onClick={() => onOutcome(entry, { status: 'declined', reason: answers.declineReason })}>
              {t(answers.declined)}
            </button>
            {(answers.extra || []).map(({ id, label, outcome }) => (
              <button key={id} type="button" data-outcome={id} disabled={readOnly} onClick={() => onOutcome(entry, outcome)}>
                {t(label)}
              </button>
            ))}
          </>
        )}
        <button type="button" data-outcome="deferred" disabled={readOnly} onClick={() => onOutcome(entry, { status: 'deferred' })}>
          {t('outcome.deferred')}
        </button>
      </footer>
    </article>
  )
}
