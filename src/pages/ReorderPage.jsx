import { useState } from 'react'
import { unavailableReason } from '../lib/i18n/unavailableReason.js'
import { loadOrderExample } from '../lib/dataAdapters/loadOrderExample.js'
import { ExamplePreview } from './OrderExample.jsx'
import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'

/**
 * Reorder: how much to order of each product, for its department's next order day (F8-S1
 * FR-160 … FR-163), as the repository owner approved it on 2026-09-27
 * (docs/reviews/F8-screens-mockups.md).
 *
 * It renders the `order_quantity` capability's published fields and computes nothing (ADR-001):
 * the quantity, the expected sales, the stock at the order day, the boost and every reason are
 * the engine's. The page only chooses the words, including each language's own form for a count
 * of days, which is wording and was approved as rendered.
 *
 * A suggestion he has approved or dismissed is not offered again: the id is the same every night
 * until its order day (ADR-034), so the decision holds, and an approval appears on Approved
 * orders instead. His own quantity travels beside the suggested one (FR-161).
 */

const LOCALE = { ar: 'ar-u-nu-latn', he: 'he-IL', en: 'en-GB' }
const SETTLED = new Set(['acted', 'declined'])
// A department that cannot get a quantity at all until he states something, or the evidence
// covers it (FR-155, FR-156). Said once for the department, not per product.
const DEPARTMENT_REASONS = new Set(['no_order_schedule', 'no_fixed_days', 'no_shelf_life', 'no_window',
  'not_itemised', 'shelf_life_under_a_day'])
// A boost that could not apply because the whole capability could not: its reason is the one
// the rest of the app already shows for it.
const CAPABILITY_REASONS = new Set(['market_signal_thin', 'market_signal_stale', 'no_boost_key', 'boost_unavailable'])

function daysText(n, language) {
  if (language === 'he') return n === 1 ? 'יום אחד' : n === 2 ? 'יומיים' : `${n} ימים`
  if (language === 'ar') return n === 1 ? 'يوم واحد' : n === 2 ? 'يومين' : n <= 10 ? `${n} أيام` : `${n} يومًا`
  return n === 1 ? '1 day' : `${n} days`
}

function weeksText(n, language) {
  if (language === 'he') return n === 1 ? 'שבוע אחד' : n === 2 ? 'שבועיים' : `${n} שבועות`
  if (language === 'ar') return n === 1 ? 'أسبوع واحد' : n === 2 ? 'أسبوعين' : n <= 10 ? `${n} أسابيع` : `${n} أسبوعًا`
  return n === 1 ? '1 week' : `${n} weeks`
}

const one = (x) => String(Math.round(x * 10) / 10)

// F14 (MOCKUP, docs/reviews/F14-screens-mockups.md; not approved, not merged). The AI writes no
// number: it writes slots, and the page fills each from the suggestion's own published facts
// (F14-S1 FR-238, FR-242). A text is shown only under a prompt version these phrases were
// written for; the list lives in one place, read by the page and the example's builder.
const PHRASES_SERVE = new Set(['mockup-sample'])
const SLOT = /\{([a-z_]+)\}/g

function slotPhrases(entry, window, t, language, dates) {
  const ev = entry.evidence
  const out = {
    product: entry.product_name || entry.barcode,
    quantity: t('reorder.ai.slot.quantity', { n: ev.quantity }),
    expected: t('reorder.ai.slot.expected', { expected: one(ev.expected_sales), days: daysText(ev.cycle.days, language), day: dates.day(ev.cycle.first_day) }),
    next_order: t('reorder.ai.slot.nextOrder', { day: dates.day(ev.order_day), days: daysText(ev.cycle.days, language) }),
  }
  if (ev.weekly_units?.length && window?.last_day) {
    const list = new Intl.ListFormat(LOCALE[language] || LOCALE.en, { type: 'conjunction' }).format(ev.weekly_units.map(one))
    out.weeks = t('reorder.ai.slot.weeks', { list, weeks: weeksText(ev.weekly_units.length, language), date: dates.short(window.last_day) })
  }
  if (ev.kind === 'net' && ev.stock_at_order_day != null) {
    if (ev.stock_at_order_day > 0.05) out.left = t('reorder.ai.slot.left', { left: one(ev.stock_at_order_day), day: dates.day(ev.order_day) })
    else out.runs_out = t('reorder.ai.slot.runsOut', { day: dates.day(ev.order_day) })
  }
  if (ev.capped && ev.shelf_life?.days) out.capped = t('reorder.ai.slot.capped', { days: daysText(ev.shelf_life.days, language) })
  return out
}

/** The text with its slots filled, each isolated for direction; null when it cannot be shown (FR-242). */
function explanationText(explanation, phrases, language) {
  const text = explanation?.text?.[language]
  if (!text || !PHRASES_SERVE.has(explanation.prompt)) return null
  const offered = new Set(explanation.slots || [])
  const parts = []
  let last = 0
  for (const m of text.matchAll(SLOT)) {
    if (!offered.has(m[1]) || phrases[m[1]] == null) return null
    parts.push(text.slice(last, m.index), <bdi key={m.index}>{phrases[m[1]]}</bdi>)
    last = m.index + m[0].length
  }
  parts.push(text.slice(last))
  return parts
}

function useDates(language) {
  const locale = LOCALE[language] || LOCALE.en
  const at = (iso) => new Date(`${iso}T00:00:00Z`)
  return {
    day: (iso) => new Intl.DateTimeFormat(locale, { weekday: 'long', day: 'numeric', month: 'short', timeZone: 'UTC' }).format(at(iso)),
    date: (iso) => new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long', timeZone: 'UTC' }).format(at(iso)),
    short: (iso) => new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(at(iso)),
  }
}

function Boost({ entry, market, thresholds }) {
  const { t, language } = useI18n()
  const boost = entry.evidence.boost || {}
  if (!market) return null
  const days = daysText(Math.max(...Object.values(market.days_absent || { none: 0 })), language)
  const pct = (x) => <bdi dir="ltr">{`${x}%`}</bdi>
  if (boost.applied) {
    const [before, after] = t('reorder.boost', { days }).split('{pct}')
    return (
      <div className="reorder__boost" data-boost="applied">
        <p>{before}{pct(boost.pct)}{after}</p>
        {boost.reason
          ? <p className="reorder__boost-reason" dir="rtl" lang="ar">{`«${boost.reason}»`}</p>
          : <p className="reorder__boost-reason">{t('reorder.boostWithheld')}</p>}
      </div>
    )
  }
  const because = boost.not_applied_because
  const why = CAPABILITY_REASONS.has(because)
    ? unavailableReason(t, because)
    : t(`reorder.boostNot.${['not_a_number', 'unparseable'].includes(because) ? 'unreadable' : because}`,
      // Isolated left to right (U+2066 … U+2069), or Hebrew renders 40% as "%40".
      { pct: `\u2066${boost.model_pick_pct}%\u2069`, max: `\u2066${thresholds?.market_boost?.max_pct ?? 25}%\u2069` })
  return (
    <div className="reorder__boost reorder__boost--not" data-boost="not_applied">
      <p>{t('reorder.boostNotApplied', { days, why })}</p>
    </div>
  )
}

function Suggestion({ entry, market, thresholds, explanation, window, onOutcome, readOnly }) {
  const { t, language } = useI18n()
  const dates = useDates(language)
  const { day, date } = dates
  const [changing, setChanging] = useState(false)
  const [draft, setDraft] = useState(String(entry.evidence.quantity))
  const ev = entry.evidence

  const approve = () => {
    if (readOnly) return
    if (!changing) return onOutcome(entry, { status: 'acted', approvedQuantity: null })
    const mine = Number(draft)
    // His quantity is authoritative (F5-S1 FR-087), but it is a count of units to order.
    if (!Number.isInteger(mine) || mine < 1) return undefined
    return onOutcome(entry, { status: 'acted', approvedQuantity: mine === ev.quantity ? null : mine })
  }

  // F14-S1 FR-242: the AI's text, when there is one it can show, replaces the engine's sentence and
  // the shelf-life line. The stock-count notice stays.
  const ai = explanationText(explanation, slotPhrases(entry, window, t, language, dates), language)
  const lines = []
  if (ev.kind === 'net') {
    const key = ev.stock_at_order_day > 0.05 ? 'reorder.net' : 'reorder.netRunsOut'
    if (!ai) lines.push(t(key, { expected: one(ev.expected_sales), left: one(ev.stock_at_order_day ?? 0), day: day(ev.order_day) }))
  } else {
    if (!ai) lines.push(<strong key="gross">{t('reorder.gross', { expected: one(ev.expected_sales) })}</strong>)
    const why = t(`reorder.count.${ev.count?.not_used_because}`, { date: ev.count?.as_of ? date(ev.count.as_of) : '' })
    lines.push(t('reorder.countNotUsed', { why }))
  }
  if (ev.capped && !ai) lines.push(t('reorder.capped', { days: daysText(ev.shelf_life.days, language) }))
  if (ai) {
    lines.unshift(
      <span key="ai" className="reorder__ai" data-explanation="shown">
        <span className="plan__ai-tag">{t('shelfExplanation.tag')}</span><span>{ai}</span>
      </span>,
    )
  }

  return (
    <article className="entry-card reorder__card" data-suggestion={entry.id} {...dirProps()}>
      <header className="entry-card__head reorder__head">
        <h3 className="entry-card__name"><bdi>{entry.product_name || entry.barcode}</bdi></h3>
        {changing ? (
          <input type="number" min="1" step="1" inputMode="numeric" className="reorder__quantity-input"
            aria-label={t('orders.quantity')} value={draft} disabled={readOnly}
            onChange={(event) => setDraft(event.target.value)} />
        ) : (
          <span className="reorder__quantity">{t('reorder.order', { n: ev.quantity })}</span>
        )}
      </header>
      {lines.map((line, i) => <p key={i} className="reorder__line">{line}</p>)}
      <Boost entry={entry} market={market} thresholds={thresholds} />
      <footer className="entry-card__actions">
        <button type="button" className="reorder__approve" data-action="approve" disabled={readOnly} onClick={approve}>
          {t('reorder.approve')}
        </button>
        <button type="button" data-action="change" disabled={readOnly} onClick={() => !readOnly && setChanging(true)}>
          {t('reorder.change')}
        </button>
        <button type="button" data-action="dismiss" disabled={readOnly}
          onClick={() => !readOnly && onOutcome(entry, { status: 'declined', reason: 'not_worth_it' })}>
          {t('reorder.dismiss')}
        </button>
      </footer>
    </article>
  )
}

function Department({ name, info, entries, capability, artefact, explanations, onOutcome, readOnly }) {
  const { t, language } = useI18n()
  const { day, date } = useDates(language)
  const first = entries[0]?.evidence
  const need = Object.keys(info.reasons || {}).find((r) => DEPARTMENT_REASONS.has(r))
  const counted = Object.entries(info.reasons || {}).filter(([r]) => !DEPARTMENT_REASONS.has(r))
    .map(([r, n]) => t(`reorder.reason.${r}`, { n }))
  if (info.covered_by_stock) counted.unshift(t('reorder.covered', { n: info.covered_by_stock }))
  const market = artefact.capabilities?.market_running_out?.products || {}
  const shelf = first?.shelf_life
  return (
    <section className="reorder__department" data-department={name}>
      <h2><bdi>{name}</bdi></h2>
      {first ? (
        <p className="reorder__line">
          {t('reorder.nextOrder', { day: day(first.order_day), days: daysText(first.cycle.days, language) })}
          {shelf?.days ? ` · ${t('reorder.keeps', { days: daysText(shelf.days, language), date: date(shelf.stated_on) })}` : ''}
        </p>
      ) : null}
      {need ? (
        <p className="reorder__needs">
          <span className="reorder__needs-pill">{t('reorder.needsFacts')}</span>
          {t(`reorder.reason.${need}`, { min: capability.thresholds?.min_report_days, window: capability.thresholds?.window_days })}
        </p>
      ) : null}
      {entries.map((entry) => (
        <Suggestion key={entry.id} entry={entry} market={market[entry.barcode]} thresholds={artefact.thresholds}
          explanation={explanations[entry.id]} window={capability.evidence_window}
          onOutcome={onOutcome} readOnly={readOnly} />
      ))}
      {counted.length ? <ul className="reorder__counts">{counted.map((line) => <li key={line}>{line}</li>)}</ul> : null}
    </section>
  )
}

/** F14-S1 FR-243: once, above the suggestions, what the AI does and how many it explained tonight. */
function AiNote({ capability }) {
  const { t } = useI18n()
  if (!capability) return null
  let text, state
  if (capability.status !== 'available') {
    text = unavailableReason(t, capability.unavailable_reason, 'order_explanation')
    state = capability.unavailable_reason || 'unavailable'
  } else {
    const { suggestions = 0, explained = 0 } = capability.counts || {}
    if (!suggestions) return null
    if (!explained) {
      text = t('reorder.ai.note.none')
      state = 'none'
    } else {
      text = explained < suggestions
        ? `${t('reorder.ai.note.what')} ${t('reorder.ai.note.some', { n: explained, total: suggestions })}`
        : t('reorder.ai.note.what')
      state = explained < suggestions ? 'some' : 'all'
    }
  }
  return (
    <aside className="plan__why reorder__ai-note" data-ai-note={state}>
      <p className="reorder__ai"><span className="plan__ai-tag">{t('shelfExplanation.tag')}</span><span>{text}</span></p>
    </aside>
  )
}

const ignore = () => {}

export function ReorderPage({ artefact, ownerState, onOutcome, readOnly = false, loadExample = loadOrderExample }) {
  const { t, language } = useI18n()
  const { date } = useDates(language)
  const capability = artefact?.capabilities?.order_quantity

  if (!capability || capability.status !== 'available') {
    // FR-160: while F8 cannot publish, the entry says what it waits for, in the reason the
    // engine published, and what to send. Never an empty list, which would read as "nothing
    // to order" (AC-107).
    return (
      // Marked as order_quantity's screen only when the artefact published it: a page must not
      // claim to render a capability the engine never sent.
      <section className="capability reorder" data-capability={capability ? 'order_quantity' : undefined} {...dirProps()}>
        <h2 className="capability__unavailable reorder__waiting">{unavailableReason(t, capability?.unavailable_reason)}</h2>
        <p className="reorder__line">{t('reorder.waiting.next')}</p>
        {/* D-29: the page as it will look, from a test shop, read-only and fenced off. */}
        <ExamplePreview load={loadExample} render={(example) => (
          <ReorderPage artefact={example.artefact} ownerState={{ outcomes: {} }} onOutcome={ignore} readOnly />
        )} />
      </section>
    )
  }

  const outcomes = ownerState?.outcomes || {}
  const open = (capability.entries || []).filter((e) => !SETTLED.has(outcomes[e.id]?.status))
  const byDepartment = {}
  for (const entry of open) (byDepartment[entry.department] ||= []).push(entry)
  const departments = capability.departments || {}
  const order = Object.keys(departments).sort((a, b) =>
    (departments[b].suggested - departments[a].suggested) || a.localeCompare(b))
  const window = capability.evidence_window
  const explained = artefact.capabilities.order_explanation
  const explanations = explained?.status === 'available'
    ? Object.fromEntries((explained.explanations || []).map((x) => [x.suggestion_id, x])) : {}

  return (
    <section className="capability reorder" data-capability="order_quantity" {...dirProps()}>
      {window ? (
        <p className="reorder__line">
          {t('reorder.basis', { first: date(window.first_day), last: date(window.last_day), days: window.report_days })}
        </p>
      ) : null}
      <AiNote capability={explained} />
      {order.map((name) => (
        <Department key={name} name={name} info={departments[name]} entries={byDepartment[name] || []}
          capability={capability} artefact={artefact} explanations={explanations}
          onOutcome={onOutcome} readOnly={readOnly} />
      ))}
    </section>
  )
}
