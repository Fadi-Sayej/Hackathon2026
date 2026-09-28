import { useMemo, useState } from 'react'
import { Button } from '../components/shared/Button.jsx'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { unavailableReason } from '../lib/i18n/unavailableReason.js'
import { useI18n } from '../lib/i18n/index.js'
import { formatDate, formatShekel } from '../lib/utils/format.js'
import { dirProps } from '../lib/utils/rtl.js'

/**
 * Your shelf price against what nearby shops charge, product by product.
 *
 * Built on `capabilities.competitor_position.comparison` (ADR-025): one row per product the
 * engine matched, carrying either its comparison or the reason there is none. Names come from
 * `catalogue.json` by barcode (ADR-024), which is why the row carries none of its own.
 *
 * WHAT THE PAGE DOES NOT DO
 *   It computes no price, no gap and no verdict (ADR-001). The percentage is the engine's
 *   `premium_pct`; the page groups rows by its sign and sorts them. There is no shekel
 *   difference column because that would be browser arithmetic over money, and there is no
 *   below-cost tab because `margin_below_cost` owns that on its own page — the version this
 *   replaces computed it here and got 63 where the engine said 34.
 *
 *   `reference` is the balanced policy reference the breach judgement is made against. It is
 *   NOT the cheapest price anyone charges (ADR-025 measured the gap at 14%), so nothing here
 *   calls it that. The old page did, from a file frozen on 2026-08-09.
 *
 * Laid out as the owner approved it on 2026-09-23: three tabs, 25 rows at a time, a flag on
 * a product that is a finding, and a reason on every product that could not be compared.
 */

const PAGE_SIZE = 25
const TABS = ['dearer', 'cheaper', 'none']
const ISOLATE = (text) => `⁦${text}⁩`

/**
 * `premium_pct` is in percentage POINTS. `formatPercent` treats anything between -1 and 1 as
 * a ratio and multiplies it by 100, so a product 0.5% dearer would read "+50%". Whole
 * numbers from 10 up, one decimal below, two only when one would round a real gap to zero.
 */
/**
 * How a reference no shop actually charges was made (approved 2026-09-28): a supermarket price
 * plus the measured allowance, or the average of two prices. A price from one shop like his
 * needs no note.
 */
function ReferenceNote({ reference, t }) {
  if (reference?.kind === 'supermarket_plus_allowance' && Number.isFinite(reference.allowance_pct)) {
    const pct = `\u2066${Math.round(reference.allowance_pct * 10) / 10}%\u2069`
    return <small className="price-ref-note">{t('prices.referenceKind.supermarket_plus_allowance', { pct })}</small>
  }
  if (reference?.kind === 'midpoint') {
    return <small className="price-ref-note">{t('prices.referenceKind.midpoint')}</small>
  }
  return null
}

function formatPremium(pct) {
  let decimals = Math.abs(pct) >= 10 ? 0 : 1
  if (pct !== 0 && Number(pct.toFixed(decimals)) === 0) decimals = 2
  const size = Math.abs(pct).toFixed(decimals).replace(/\.0+$/, '')
  const sign = Number(size) === 0 ? '' : pct > 0 ? '+' : '−'
  return ISOLATE(`${sign}${size}%`)
}

/** Today, yesterday, or the date — the age SCN-047 asks every display to mark. */
function seenLabel(date, now, t) {
  if (!date) return '—'
  const today = new Date(now).toISOString().slice(0, 10)
  const days = Math.round((Date.parse(today) - Date.parse(date)) / 86_400_000)
  if (days === 0) return t('prices.when.today')
  if (days === 1) return t('prices.when.yesterday')
  return formatDate(date)
}

/** Why a product was not compared. A reason this build has no words for says "not compared"
 *  rather than printing its key — the engine can add one before the page learns it. */
function whyText(reason, t) {
  const key = `prices.why.${reason}`
  const text = t(key)
  return text === key ? t('prices.why.unknown') : text
}

function tabOf(row) {
  if (row.premium_pct === null || row.premium_pct === undefined) return 'none'
  return row.premium_pct > 0 ? 'dearer' : 'cheaper'
}

const byBarcode = (a, b) => String(a.barcode).localeCompare(String(b.barcode))
const ORDER = {
  dearer: (a, b) => b.premium_pct - a.premium_pct || byBarcode(a, b),
  cheaper: (a, b) => a.premium_pct - b.premium_pct || byBarcode(a, b),
  // Most shops first: a product sold widely nearby and still uncompared is the one worth
  // knowing about.
  none: (a, b) => (b.stores ?? 0) - (a.stores ?? 0) || byBarcode(a, b),
}

export function PriceGapPage({ artefact, catalogue, now, onOpenFinding }) {
  const { t } = useI18n()
  const [view, setView] = useState('dearer')
  const [query, setQuery] = useState('')
  const [shown, setShown] = useState(PAGE_SIZE)

  const capability = artefact?.capabilities?.competitor_position
  const comparison = capability?.comparison

  const names = useMemo(() => {
    const map = new Map()
    for (const p of catalogue?.products || []) {
      if (p.barcode) map.set(String(p.barcode), p.product_name)
    }
    return map
  }, [catalogue])

  const findings = useMemo(
    () => new Set((capability?.entries || []).map((e) => String(e.barcode))),
    [capability],
  )

  const grouped = useMemo(() => {
    const out = { dearer: [], cheaper: [], none: [] }
    if (!Array.isArray(comparison)) return out
    const q = query.trim().toLowerCase()
    for (const row of comparison) {
      const name = names.get(String(row.barcode)) || ''
      if (q && !name.toLowerCase().includes(q) && !String(row.barcode).includes(q)) continue
      out[tabOf(row)].push(row)
    }
    for (const id of TABS) out[id].sort(ORDER[id])
    return out
  }, [comparison, names, query])

  if (!capability) {
    // Absent is not empty: rendering nothing would read as "no competitor sells anything".
    return (
      <section className="capability capability__missing" {...dirProps()}>
        <p>{t('capability.missing')}</p>
      </section>
    )
  }

  if (capability.status === 'unavailable') {
    // AC-107. No tabs and no counts: "Dearer 0" would read as a finding, and nothing ran.
    return (
      <section className="capability" {...dirProps()}>
        <p className="capability__unavailable">{unavailableReason(t, capability.unavailable_reason)}</p>
      </section>
    )
  }

  if (!Array.isArray(comparison)) {
    return (
      <section className="capability" {...dirProps()}>
        <p className="capability__unavailable">{t('prices.notPublished')}</p>
      </section>
    )
  }

  const competitor = artefact.vintages?.competitor || {}
  const when = competitor.snapshot_date ? seenLabel(competitor.snapshot_date, now, t) : null
  const active = grouped[view]
  const visible = active.slice(0, shown)
  const remaining = active.length - visible.length
  const compared = view !== 'none'

  const choose = (id) => { setView(id); setShown(PAGE_SIZE) }
  const search = (value) => { setQuery(value); setShown(PAGE_SIZE) }

  return (
    <section className="panel" {...dirProps()}>
      <div className="panel-heading">
        <div>
          {when ? (
            <p className="eyebrow">
              {competitor.store_count != null
                ? t('prices.seen', { when, n: competitor.store_count })
                : t('prices.seenNoShops', { when })}
            </p>
          ) : null}
        </div>
      </div>

      <div className="recommendation-actions" style={{ flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
        {TABS.map((id) => (
          <Button key={id} tone={view === id ? 'primary' : 'ghost'} aria-pressed={view === id}
            onClick={() => choose(id)}>
            {t(`prices.tab.${id}`, { n: grouped[id].length.toLocaleString('en-US') })}
          </Button>
        ))}
        <input
          className="operational-search"
          type="search"
          value={query}
          onChange={(event) => search(event.target.value)}
          placeholder={t('prices.search')}
          aria-label={t('prices.searchLabel')}
        />
      </div>

      {view === 'cheaper' ? <p className="page-description">{t('prices.packWarning')}</p> : null}

      {active.length === 0 ? (
        <EmptyState title={t('pg.nothingHere')} description={t('pg.nothingHereDesc')} />
      ) : (
        <div className="price-table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('common.product')}</th>
                {compared ? <th className="numeric">{t('prices.col.gap')}</th> : null}
                <th className="numeric">{t('prices.col.yours')}</th>
                {compared
                  ? <th className="numeric">{t('prices.col.reference')}</th>
                  : <th>{t('prices.col.why')}</th>}
                <th className="numeric">{t('prices.col.shops')}</th>
                <th>{t('prices.col.seen')}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => {
                const barcode = String(row.barcode)
                const isFinding = findings.has(barcode)
                return (
                  <tr key={barcode} data-barcode={barcode}>
                    <td dir="auto">
                      {names.get(barcode) || barcode}
                      {isFinding ? (
                        <Button tone="ghost" aria-label={t('prices.finding')} onClick={onOpenFinding}>⚑</Button>
                      ) : null}
                      {row.uncompared_reason === 'no_cost' ? (
                        <StatusBadge tone="neutral">{t('prices.notJudged')}</StatusBadge>
                      ) : null}
                    </td>
                    {compared ? (
                      <td className={`numeric ${row.premium_pct > 0 ? 'negative' : row.premium_pct < 0 ? 'positive' : ''}`}>
                        {formatPremium(row.premium_pct)}
                      </td>
                    ) : null}
                    <td className="numeric">{formatShekel(row.shelf_price)}</td>
                    {compared
                      ? (
                        <td className="numeric">
                          {formatShekel(row.reference?.value)}
                          <ReferenceNote reference={row.reference} t={t} />
                        </td>
                      )
                      : <td>{whyText(row.uncompared_reason, t)}</td>}
                    <td className="numeric">{row.stores ?? '—'}</td>
                    <td>{seenLabel(row.observed_at, now, t)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* The same rows as cards, for a phone: below 900px the table's first column is the
          name and every figure sat one sideways swipe away. CSS shows one or the other;
          both come from `visible`, so they can never disagree about what is on screen.
          Approved by the repository owner on 2026-09-24. */}
      {active.length > 0 ? (
        <ul className="price-cards">
          {visible.map((row) => {
            const barcode = String(row.barcode)
            return (
              <li key={barcode} className="price-card" data-barcode={barcode}>
                <p className="price-card__name" dir="auto">
                  {names.get(barcode) || barcode}
                  {findings.has(barcode) ? (
                    <Button tone="ghost" aria-label={t('prices.finding')} onClick={onOpenFinding}>⚑</Button>
                  ) : null}
                  {row.uncompared_reason === 'no_cost' ? (
                    <StatusBadge tone="neutral">{t('prices.notJudged')}</StatusBadge>
                  ) : null}
                </p>
                {compared ? (
                  <p className="price-card__figures">
                    <span className={`price-card__gap numeric ${row.premium_pct > 0 ? 'negative' : row.premium_pct < 0 ? 'positive' : ''}`}>
                      {formatPremium(row.premium_pct)}
                    </span>
                    <span>{t('prices.card.against', {
                      yours: formatShekel(row.shelf_price),
                      reference: formatShekel(row.reference?.value),
                    })}</span>
                    <ReferenceNote reference={row.reference} t={t} />
                  </p>
                ) : (
                  <p className="price-card__figures">
                    <span className="numeric">{formatShekel(row.shelf_price)}</span>
                    <span>{whyText(row.uncompared_reason, t)}</span>
                  </p>
                )}
                <p className="price-card__meta">
                  {t('prices.card.meta', { n: row.stores ?? '—', seen: seenLabel(row.observed_at, now, t) })}
                </p>
              </li>
            )
          })}
        </ul>
      ) : null}

      {remaining > 0 ? (
        <Button tone="ghost" onClick={() => setShown(shown + PAGE_SIZE)}>
          {t('prices.more', { n: Math.min(PAGE_SIZE, remaining) })}
        </Button>
      ) : null}

      {visible.some((row) => findings.has(String(row.barcode)))
        ? <p className="page-description">{t('prices.legend.finding')}</p> : null}
      {compared && visible.some((row) => row.uncompared_reason === 'no_cost')
        ? <p className="page-description">{t('prices.legend.notJudged')}</p> : null}
    </section>
  )
}
