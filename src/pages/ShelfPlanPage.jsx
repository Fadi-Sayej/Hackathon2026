import { unavailableReason } from '../lib/i18n/unavailableReason.js'
import { loadShelfExample } from '../lib/dataAdapters/loadShelfExample.js'
import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'
import { ExamplePreview } from './OrderExample.jsx'
import { daysText, facingsText, namesFrom, ruleText, useDates } from './shelfCommon.js'
import { Names } from './ShelfNames.jsx'

/**
 * Shelf plan: where each product goes on each shelf unit, how many facings, and why (F12-S1
 * FR-194, FR-200, FR-201, FR-215).
 *
 * It renders `shelf_plan`, `shelf_explanation` and `shelf_measurement` and computes nothing
 * (ADR-001). The shelf drawing scales each product's block by its published width and facings in
 * CSS; no length is worked out here. The one control is "I've arranged this shelf" and its undo
 * (FR-195). A team account sees it disabled (ADR-029), and so does the marked example (D-31).
 */

const UNPLACED = ['no_width', 'too_wide', 'no_sale_in_window', 'count_zero_or_below', 'stock_unknown', 'kept_off', 'rejected']

function Elasticity({ elasticity }) {
  const { t } = useI18n()
  const { fixed } = useDates()
  if (!elasticity) return null
  const value = fixed(elasticity.value)
  const why = elasticity.why === 'measurement_unavailable'
    ? unavailableReason(t, elasticity.measurement_reason, 'shelf_measurement')
    : t(`shelf.elasticity.why.${elasticity.why}`)
  return (
    <div className="plan__conditions" data-elasticity={elasticity.source}>
      <p>{t(elasticity.source === 'his_store' ? 'shelf.elasticity.his' : 'shelf.elasticity.research', { value })}</p>
      {elasticity.source === 'his_store' ? null : <p>{why}</p>}
    </div>
  )
}

function Shelf({ shelf, nameOf, rules }) {
  const { t, language } = useI18n()
  const { number } = useDates()
  return (
    <li className="plan__shelf" data-shelf={shelf.shelf} data-eye-level={shelf.eye_level || undefined}>
      <div className="plan__shelf-head">
        <span className="layout__shelf-name">{t('layout.shelf', { n: shelf.shelf })}</span>
        {shelf.eye_level ? <span className="layout__tag layout__tag--eye">{t('layout.eyeLevel')}</span> : null}
        <span className="layout__shelf-length"><bdi>{t('layout.length', { cm: shelf.length_cm })}</bdi></span>
      </div>
      {/* The shelf to scale: each product a block as wide as its facings, then the free length. */}
      <div className="plan__bar" aria-hidden="true">
        <div className="plan__used" style={{ flexGrow: shelf.used_cm }}>
          {shelf.products.map((p) => (
            <span key={p.barcode} className="plan__block" style={{ '--w': p.width_mm, '--n': p.facings }}>
              <bdi>{p.product_name || nameOf(p.barcode)}</bdi>
            </span>
          ))}
        </div>
        {shelf.free_cm > 0 ? (
          <div className="plan__free" style={{ flexGrow: shelf.free_cm }}>
            <bdi>{t(shelf.products.length ? 'shelf.free' : 'shelf.empty', { cm: number(shelf.free_cm, 1) })}</bdi>
          </div>
        ) : null}
      </div>
      <ul className="plan__products">
        {shelf.products.map((p) => {
          const notes = []
          if (p.rank) notes.push(t('shelf.rank', { rank: p.rank }))
          if (p.unknown_parts?.length) {
            notes.push(t('shelf.unknown', { why: p.unknown_because.map((b) => t(`shelf.unknown.${b}`)).join(t('shelf.and')) }))
          }
          if (p.kept_on_by_his_rule) notes.push(t('shelf.keptOn'))
          for (const kind of p.rules || []) {
            const rule = rules.find((r) => r.kind === kind && r.barcode === p.barcode)
            if (rule) notes.push(t('shelf.yourRule', { rule: ruleText(t, rule, nameOf) }))
          }
          return (
            <li key={p.barcode}>
              <span className="plan__product-name"><bdi>{p.product_name || nameOf(p.barcode)}</bdi></span>
              <span className="plan__facings">{facingsText(p.facings, language)}</span>
              {notes.length ? <span className="plan__product-notes">{notes.join(' · ')}</span> : null}
            </li>
          )
        })}
      </ul>
    </li>
  )
}

function Unplaced({ unplaced, nameOf }) {
  const { t } = useI18n()
  const lists = UNPLACED.filter((r) => unplaced?.[r]?.length)
  if (!lists.length) return null
  return (
    <div className="plan__unplaced">
      <h4>{t('shelf.unplaced')}</h4>
      {lists.map((r) => (
        <p key={r} className="plan__unplaced-line" data-unplaced={r}>
          <span className="plan__unplaced-why">{t(`shelf.unplaced.${r}`)}</span>{' '}
          {r === 'too_wide'
            ? unplaced[r].map((p, i) => (
              <span key={p.barcode}>{i ? ' · ' : ''}<bdi>{nameOf(p.barcode)}</bdi> (<bdi>{t('layout.widthMm', { mm: p.width_mm })}</bdi>)</span>
            ))
            : <Names barcodes={unplaced[r]} nameOf={nameOf} />}
        </p>
      ))}
    </div>
  )
}

function Explanation({ capability, explanation }) {
  const { t, language } = useI18n()
  let body
  if (!capability || capability.status !== 'available') {
    body = <p className="plan__why-none">{unavailableReason(t, capability?.unavailable_reason, 'shelf_explanation')}</p>
  } else if (!explanation?.text) {
    body = <p className="plan__why-none">{t(`shelfExplanation.none.${explanation?.why_none || 'not_written_tonight'}`)}</p>
  } else {
    body = <p className="plan__why-text">{explanation.text[language] || explanation.text.en}</p>
  }
  return (
    <aside className="plan__why" data-explanation={explanation?.text ? 'shown' : (explanation?.why_none || capability?.unavailable_reason || 'none')}>
      <h4><span className="plan__ai-tag">{t('shelfExplanation.tag')}</span>{t('shelfExplanation.label')}</h4>
      {body}
      {explanation?.text ? <p className="plan__why-note">{t('shelfExplanation.note')}</p> : null}
    </aside>
  )
}

function ProductChange({ p, nameOf }) {
  const { t, language } = useI18n()
  const { number, fixed } = useDates()
  const eye = p.eye_level_change > 0 ? t('shelf.measure.toEye') : p.eye_level_change < 0 ? t('shelf.measure.offEye') : null
  // Isolated left to right (U+2066 … U+2069), so "×1.18" keeps its order in Hebrew and Arabic. The arrow
  // between before and after is each language's own: "→" does not turn round in right-to-left text.
  const ltr = (x) => `\u2066${x}\u2069`
  return (
    <li>
      <span className="plan__product-name"><bdi>{p.product_name || nameOf(p.barcode)}</bdi></span>
      {eye ? <span className="plan__eye-move">{eye}</span> : null}
      <span className="plan__change-line">
        {t('shelf.measure.change', {
          before: p.before_facings == null ? '—' : facingsText(p.before_facings, language), after: facingsText(p.after_facings, language),
        })}
      </span>
      <span className="plan__change-line">{t('shelf.measure.perDay', {
        change: t('shelf.measure.change', { before: number(p.before_daily_mean, 1), after: number(p.after_daily_mean, 1) }),
      })}</span>
      <span className="plan__change-line plan__change-net">{p.net_change == null
        ? t('shelf.measure.noNet', { why: t(`shelf.measure.noRatio.${p.why_no_net_change}`) })
        : t('shelf.measure.net', { x: ltr(`×${fixed(p.net_change)}`) })}</span>
    </li>
  )
}

function Measurement({ arrangement, nameOf }) {
  const { t, language } = useI18n()
  const { date } = useDates()
  const a = arrangement
  const windows = t('shelf.measure.windows', {
    b1: date(a.before_window.first_day), b2: date(a.before_window.last_day),
    a1: date(a.after_window.first_day), a2: date(a.after_window.last_day),
  })
  return (
    <div className="plan__measure" data-measure={a.status}>
      <h4>{t('shelf.measure.title')}</h4>
      <p className="plan__muted">{windows}</p>
      {a.status === 'waiting' ? (
        <p className="plan__progress">{t('shelf.measure.waiting', {
          so: a.waiting.report_days_so_far, need: a.waiting.report_days_needed, days: daysText(a.waiting.days_left, language),
        })}</p>
      ) : null}
      {a.status === 'not_measurable' ? <p className="plan__why-none">{t(`shelf.measure.not.${a.reason}`)}</p> : null}
      {a.status === 'measured' ? (
        <>
          <ul className="plan__changes">
            {a.products.map((p) => <ProductChange key={p.barcode} p={p} nameOf={nameOf} />)}
          </ul>
          <p className="plan__muted">{t('shelf.measure.against', { n: a.comparison.fixtures.length })}</p>
          <p className="plan__muted">{t('shelf.measure.noVerdict')}</p>
          {a.left_out?.length ? (
            <p className="plan__muted">{t('shelf.measure.leftOut')} <Names barcodes={a.left_out.map((x) => x.barcode)} nameOf={nameOf} /></p>
          ) : null}
        </>
      ) : null}
    </div>
  )
}

function Arranged({ entry, mine, latest, onOutcome, onUndoOutcome, readOnly }) {
  const { t } = useI18n()
  const { date } = useDates()
  const running = latest?.status === 'waiting'
  return (
    <footer className="plan__arrange">
      {mine ? (
        <p className="plan__arranged" data-arranged="this-device">
          {t('shelf.arranged.mine', { date: date(mine.snapshot?.arranged_on) })}
          <button type="button" className="btn btn-ghost" data-action="undo" disabled={readOnly}
            onClick={() => !readOnly && onUndoOutcome?.(entry.id)}>{t('shelf.undo')}</button>
        </p>
      ) : (
        <>
          {latest ? (
            <p className="plan__arranged" data-arranged="published">
              {t('shelf.arranged.published', { date: date(latest.arranged_on), plan: date(latest.plan_date) })}
              <button type="button" className="btn btn-ghost" data-action="undo" disabled={readOnly}
                onClick={() => !readOnly && onUndoOutcome?.(latest.entry_id)}>{t('shelf.undo')}</button>
            </p>
          ) : null}
          {running ? <p className="plan__warning" role="note">{t('shelf.arrange.ends')}</p> : null}
          <button type="button" className="reorder__approve" data-action="arranged" disabled={readOnly || !entry.evidence.shelves}
            onClick={() => !readOnly && onOutcome(entry, { status: 'acted' })}>{t('shelf.arrange')}</button>
          <p className="plan__muted">{t('shelf.arrange.how')}</p>
        </>
      )}
      {mine || latest ? <p className="plan__muted">{t('shelf.undo.what')}</p> : null}
    </footer>
  )
}

function FixturePlan({ entry, plan, explanations, arrangements, outcomes, nameOf, onOutcome, onUndoOutcome, readOnly }) {
  const { t } = useI18n()
  const { date, number } = useDates()
  const ev = entry.evidence
  const mine = outcomes[entry.id]?.status === 'acted' ? outcomes[entry.id] : null
  const latest = arrangements.filter((a) => a.fixture === ev.fixture)
    .sort((x, y) => y.arranged_on.localeCompare(x.arranged_on))[0]
  const facts = [...new Set([ev.stated_on, ...(ev.shelves || []).flatMap((s) => [s.measured_on, ...s.products.map((p) => p.width_measured_on)])]
    .filter(Boolean))].sort()
  return (
    <article className="entry-card plan__fixture" data-fixture={ev.fixture} data-state={ev.state} {...dirProps()}>
      <header className="layout__head">
        <h3 className="entry-card__name"><bdi>{ev.fixture}</bdi></h3>
        {ev.chilled ? <span className="layout__tag">{t('layout.chilled')}</span> : null}
        <span className="layout__dated">{t('shelf.planOf', { date: date(ev.plan_date) })}</span>
      </header>
      <p className="reorder__line">{t('layout.departments')} <Names barcodes={ev.departments} nameOf={(d) => d} /></p>
      {ev.state === 'planned' ? (
        <ol className="layout__shelves plan__shelves">
          {ev.shelves.map((s) => <Shelf key={s.shelf} shelf={s} nameOf={nameOf} rules={ev.rules || []} />)}
        </ol>
      ) : (
        <p className="reorder__needs" data-plan-state={ev.state}>
          <span className="reorder__needs-pill">{t('shelf.noPlan')}</span>
          {ev.state === 'over_full' ? t('shelf.state.over_full', { cm: number(ev.did_not_fit_cm, 1) })
            : ev.state === 'stopped_by_rule'
              ? t('shelf.state.stopped_by_rule', { rule: ruleText(t, ev.stopped_by, nameOf), why: t(`shelf.stopped.${ev.stopped_by.why}`) })
              : t(`shelf.state.${ev.state}`)}
          {ev.state === 'over_full' ? <span className="layout__counting"><Names barcodes={ev.planned || []} nameOf={nameOf} /></span> : null}
        </p>
      )}
      <Unplaced unplaced={ev.unplaced} nameOf={nameOf} />
      {ev.extra_facings && ev.extra_facings !== 'given' ? <p className="plan__muted">{t(`shelf.extras.${ev.extra_facings}`)}</p> : null}
      {facts.length ? <p className="layout__dated">{t('shelf.factsOf', { dates: facts.map(date).join(' · ') })}</p> : null}
      <Explanation capability={plan.explanation} explanation={explanations[entry.id]} />
      {latest ? <Measurement arrangement={latest} nameOf={nameOf} /> : null}
      <Arranged entry={entry} mine={mine} latest={latest} onOutcome={onOutcome} onUndoOutcome={onUndoOutcome}
        readOnly={readOnly} />
    </article>
  )
}

function StoreFigure({ measurement, research }) {
  const { t } = useI18n()
  const { fixed, percent } = useDates()
  if (!measurement || measurement.status !== 'available' || !measurement.elasticity) return null
  const e = measurement.elasticity
  const p = measurement.placebo || {}
  return (
    <section className="plan__store" data-verdict={e.verdict}>
      <h2>{t('shelf.store.title')}</h2>
      {e.estimate != null && e.interval ? (
        <p className="plan__store-figure">{t('shelf.store.estimate', {
          value: fixed(e.estimate), lo: fixed(e.interval[0]), hi: fixed(e.interval[1]), level: percent(e.level),
        })}</p>
      ) : null}
      <p>{t(`shelf.store.verdict.${e.verdict}`, {
        why: e.why_not_measurable ? t(`shelf.store.whyNot.${e.why_not_measurable}`, {
          a: measurement.thresholds?.min_arrangements, p: measurement.thresholds?.min_products,
        }) : '',
      })}</p>
      <p className="plan__muted">{t('shelf.store.basis', { a: e.arrangements, f: e.fixtures, p: e.products })}</p>
      <p>{t(`shelf.store.placebo.${p.status || 'not_run'}`, {
        why: p.why_not_run ? t(`shelf.store.whyNot.${p.why_not_run}`, {
          a: measurement.thresholds?.min_arrangements, p: measurement.thresholds?.min_products,
        }) : '',
      })}</p>
      {research != null ? <p className="plan__muted">{t('shelf.store.research', { value: fixed(research) })}</p> : null}
    </section>
  )
}

const ignore = () => {}

export function ShelfPlanPage({ artefact, ownerState, catalogue, onOutcome = ignore, onUndoOutcome = ignore, readOnly = false,
  loadExample = loadShelfExample }) {
  const { t } = useI18n()
  const { date } = useDates()
  const capability = artefact?.capabilities?.shelf_plan

  if (!capability || capability.status !== 'available') {
    // FR-194: the reason, in his words, and no plan. FR-200: the page as it will look, from a
    // test shop, read-only and fenced off.
    return (
      <section className="capability plan" data-capability={capability ? 'shelf_plan' : undefined} {...dirProps()}>
        <h2 className="capability__unavailable reorder__waiting">{unavailableReason(t, capability?.unavailable_reason, 'shelf_plan')}</h2>
        <p className="reorder__line">{t(capability?.unavailable_reason === 'no_store_layout' ? 'layout.waiting.next' : 'shelf.waiting.next')}</p>
        <ExamplePreview load={loadExample} render={(example) => (
          <ShelfPlanPage artefact={example.artefact} ownerState={example.owner_state || { outcomes: {} }}
            catalogue={example.catalogue} readOnly />
        )} />
      </section>
    )
  }

  const explanation = artefact.capabilities.shelf_explanation
  const measurement = artefact.capabilities.shelf_measurement
  const explanations = Object.fromEntries((explanation?.explanations || []).map((x) => [x.plan_entry_id, x]))
  const arrangements = measurement?.status === 'available' ? measurement.arrangements || [] : []
  const nameOf = namesFrom(catalogue)
  const outcomes = ownerState?.outcomes || {}
  const window = capability.evidence_window
  const entries = [...(capability.entries || [])].sort((a, b) => a.ordering_key.value - b.ordering_key.value)

  return (
    <section className="capability plan" data-capability="shelf_plan" {...dirProps()}>
      {window ? (
        <p className="reorder__line">{t('reorder.basis', { first: date(window.first_day), last: date(window.last_day), days: window.report_days })}</p>
      ) : null}
      <Elasticity elasticity={capability.elasticity} />
      {entries.map((entry) => (
        <FixturePlan key={entry.id} entry={entry} plan={{ explanation }} explanations={explanations}
          arrangements={arrangements} outcomes={outcomes} nameOf={nameOf} onOutcome={onOutcome}
          onUndoOutcome={onUndoOutcome} readOnly={readOnly} />
      ))}
      {measurement?.status === 'available'
        ? <StoreFigure measurement={measurement} research={artefact.thresholds?.shelf_plan?.elasticity} />
        : null}
    </section>
  )
}
