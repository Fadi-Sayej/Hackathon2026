import { useCallback, useMemo, useState } from 'react'
import { allocateUnit } from '../lib/planogram/allocationEngine.js'
import { allocateMarginProportional, comparePlans } from '../lib/planogram/baselines.js'
import { validatePlan } from '../lib/planogram/planValidation.js'
import {
  approvePlan,
  loadApprovedPlan,
  planStability,
  toPlanVersion,
} from '../lib/planogram/planVersion.js'
import { buildSheetRows, toBuildSheetCsv } from '../lib/planogram/buildSheet.js'
import { FIXTURE_KINDS, describeShelves, linearMetres } from '../lib/planogram/fixtures.js'
import { shapeCatalogue, shapeVisual, PACKAGE_SHAPES } from '../lib/planogram/packageShapes.js'
import { loadStoreLayout } from '../lib/planogram/layoutStorage.js'
import { useNumbers, useT } from '../lib/i18n/index.js'
import { EmptyState } from '../components/shared/EmptyState.jsx'
import { ShelfPhotoPanel } from '../components/planogram/ShelfPhotoPanel.jsx'
import '../styles/planogram.css'

const STATUS_COLOR = { ok: 'var(--pg-ok)', low: 'var(--pg-low)', out: 'var(--pg-out)' }
const STATUS_WASH = { ok: 'var(--pg-ok-wash)', low: 'var(--pg-low-wash)', out: 'var(--pg-out-wash)' }
const STATUS_KEY = { ok: 'sp.statusOk', low: 'sp.statusLow', out: 'sp.statusOut' }
const ADVICE_KEY = { ok: 'sp.adviceOk', low: 'sp.adviceLow', out: 'sp.adviceOut' }

/** A gondola, as the fallback when no floor plan has been drawn yet. */
function fallbackUnit() {
  const saved = loadStoreLayout()
  const drawn = saved?.units?.find((unit) => unit.kind === 'gondola') ?? saved?.units?.[0]
  if (drawn) return drawn
  const spec = FIXTURE_KINDS.gondola
  return {
    id: 'default',
    kind: 'gondola',
    name: spec.label,
    x: 0,
    y: 0,
    w: spec.w,
    d: spec.d,
    levels: spec.levels,
    height: spec.height,
  }
}

/**
 * Shelf plan — one fixture, allocated.
 *
 * The bay drawn here is the output of `allocateUnit()`, not a mock: every
 * facing count comes from a real package width measured against a real shelf
 * run. What is NOT real is the demand term behind the ranking — see the
 * confidence note in the summary panel, and `allocationEngine.js` for why.
 *
 * One fixture holds a few dozen facings and the catalogue has 7,674 products,
 * so the category picker is not a convenience — without it the allocation is
 * meaningless. A planogram is always drawn for a category, on a bay.
 */
export function ShelfPlanPage({
  analyzedProducts = [],
  planogramUnit = null,
  demandIndexById = {},
  // Rendered inside the layout page: the outer page already carries the title
  // and the fixture identity, so repeating the header would be noise.
  embedded = false,
}) {
  const t = useT()
  const { n, d, percentSign } = useNumbers()
  // Hooks run unconditionally: the fallback is always computed, then discarded
  // when a unit was passed in.
  const defaultUnit = useMemoOnce(fallbackUnit)
  const unit = planogramUnit ?? defaultUnit
  const [hoveredId, setHoveredId] = useState(null)

  const categories = useMemo(() => {
    const counts = new Map()
    for (const product of analyzedProducts) {
      counts.set(product.category, (counts.get(product.category) ?? 0) + 1)
    }
    return [...counts.entries()].sort((left, right) => right[1] - left[1]).map(([name, count]) => ({ name, count }))
  }, [analyzedProducts])

  const [category, setCategory] = useState(null)
  const activeCategory = category ?? categories[0]?.name ?? null

  const allocation = useMemo(() => {
    if (!activeCategory) return null
    const products = analyzedProducts.filter((product) => product.category === activeCategory)
    return allocateUnit({ unit, products, demandIndexById })
  }, [activeCategory, analyzedProducts, demandIndexById, unit])

  const catalogue = useMemo(() => shapeCatalogue(), [])

  // Re-checked from the placements alone, not taken on the allocator's word.
  const validation = useMemo(() => validatePlan(allocation ?? { shelves: [] }), [allocation])

  // The margin-proportional rule the greedy allocator has to beat. Recomputed
  // alongside it so the comparison is always of the plan on screen.
  const comparison = useMemo(() => {
    if (!allocation || !activeCategory) return null
    const products = analyzedProducts.filter((product) => product.category === activeCategory)
    const marginPlan = allocateMarginProportional({ unit, products })
    return comparePlans({ smartshelf: allocation, marginRule: marginPlan })
  }, [activeCategory, allocation, analyzedProducts, unit])

  // The approved plan is read from storage, so it is not derivable from props
  // alone: approving mutates the store without changing any input. The counter
  // is the missing input, made explicit rather than papered over with an effect
  // that sets state during render.
  const [approvalVersion, setApprovalVersion] = useState(0)
  const approved = useMemo(() => {
    void approvalVersion
    return activeCategory ? loadApprovedPlan(unit.id, activeCategory) : null
  }, [activeCategory, unit.id, approvalVersion])

  const stability = useMemo(
    () => planStability(allocation ?? { shelves: [] }, approved),
    [allocation, approved],
  )

  const sheetRows = useMemo(() => buildSheetRows(allocation ?? { shelves: [] }), [allocation])

  const handleApprove = useCallback(() => {
    if (!allocation || !activeCategory) return
    approvePlan(toPlanVersion({ unit, category: activeCategory, plan: allocation }))
    setApprovalVersion((version) => version + 1)
  }, [activeCategory, allocation, unit])

  const handleDownload = useCallback(() => {
    if (!allocation) return
    const csv = toBuildSheetCsv(allocation)
    // A BOM so Excel opens Hebrew and Arabic correctly instead of as mojibake.
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `shelf-plan-${unit.id}-${activeCategory}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }, [activeCategory, allocation, unit.id])

  if (!analyzedProducts.length) {
    return (
      <EmptyState
        description={t('sp.noProductsDesc')}
        title={t('sp.noProductsTitle')}
      />
    )
  }

  const shelves = allocation?.shelves ?? []
  const summary = allocation?.summary
  const advice = buildAdvice(shelves, unit, t, n, d)

  return (
    <div className="pg">
      {!embedded && (
      <header className="pg-header">
        <div className="pg-header-id">
          <div className="pg-badge">{t('sp.badge')}</div>
          <div>
            <h2>
              {`${t('sp.title')} — ${unit.name}`}{' '}
              <span dir="ltr" className="pg-mono" style={{ fontSize: 13 }}>{unit.id.toUpperCase()}</span>
            </h2>
            <p className="pg-header-sub">
              {t('sp.unitSummary', {
                run: d(linearMetres(unit)),
                runUnit: t('sl.metresRun'),
                shelves: n(describeShelves(unit).length),
                height: d(unit.height),
              })}
            </p>
          </div>
        </div>
        <div className="pg-header-actions">
          <label className="pg-stat-chip">
            <span>{t('plan.category')}</span>
            <select
              className="pg-input"
              style={{ width: 'auto', padding: '2px 6px', background: 'transparent', border: 0, fontWeight: 700 }}
              value={activeCategory ?? ''}
              onChange={(event) => setCategory(event.target.value)}
            >
              {categories.map((entry) => (
                <option key={entry.name} value={entry.name}>
                  {`${entry.name} (${entry.count})`}
                </option>
              ))}
            </select>
          </label>
          <div className="pg-stat-chip">
            <span>{t('plan.fill')}</span>
            <span>{`${n(Math.round((summary?.fillRatio ?? 0) * 100))}${percentSign}`}</span>
          </div>
          <button className="pg-button pg-button-ghost" type="button" onClick={handleDownload}>
            {t('plan.downloadSheet')}
          </button>
          <button className="pg-button" type="button" onClick={handleApprove}>
            {approved ? t('plan.approveNew') : t('plan.approve')}
          </button>
        </div>
      </header>
      )}

      {embedded && (
        /* The full header is the outer page's job, but the category selector and
           the two actions still have to be reachable here — they are what makes
           the embedded plan usable rather than a picture. */
        <div className="pg-embedded-bar">
          <label className="pg-stat-chip">
            <span>{t('plan.category')}</span>
            <select
              className="pg-input"
              style={{ width: 'auto', padding: '2px 6px', background: 'transparent', border: 0, fontWeight: 700 }}
              value={activeCategory ?? ''}
              onChange={(event) => setCategory(event.target.value)}
            >
              {categories.map((entry) => (
                <option key={entry.name} value={entry.name}>
                  {`${entry.name} (${entry.count})`}
                </option>
              ))}
            </select>
          </label>
          <div className="pg-stat-chip">
            <span>{t('plan.fill')}</span>
            <span>{`${n(Math.round((summary?.fillRatio ?? 0) * 100))}${percentSign}`}</span>
          </div>
          <button className="pg-button pg-button-ghost" type="button" onClick={handleDownload}>
            {t('plan.downloadSheet')}
          </button>
          <button className="pg-button" type="button" onClick={handleApprove}>
            {approved ? t('plan.approveNew') : t('plan.approve')}
          </button>
        </div>
      )}

      <div className="pg-split">
        <div className="pg-stack">
          <div className="pg-legend">
            {['ok', 'low', 'out'].map((status) => (
              <span className="pg-legend-item" key={status}>
                <span className="pg-swatch" style={{ background: STATUS_COLOR[status] }} />
                <span>{t(STATUS_KEY[status])}</span>
              </span>
            ))}
            <span className="pg-hint">{t('sp.hoverHint')}</span>
          </div>

          <div className="pg-bay">
            {shelves.map((shelf, shelfIndex) => (
              <div className="pg-shelf" key={shelf.code}>
                <div className="pg-shelf-meta">
                  <span>{`${shelf.code} · ${shelf.levelLabel}`}</span>
                  <span>
                    {shelf.items.length
                      ? t('sp.piecesShown', {
                          n: n(shelf.items.reduce((sum, item) => sum + item.onShelf, 0)),
                        })
                      : t('sp.empty')}
                  </span>
                </div>
                <div className="pg-shelf-deck">
                  {shelf.items.length === 0 && <span className="pg-shelf-empty">{t('sp.noProductsOnShelf')}</span>}
                  {shelf.items.map((item, itemIndex) => (
                    <ShelfPosition
                      item={item}
                      t={t}
                      n={n}
                      d={d}
                      key={item.productId}
                      tipBelow={shelfIndex === 0}
                      tipAtStart={itemIndex < 2}
                      hovered={hoveredId === item.productId}
                      onHover={setHoveredId}
                    />
                  ))}
                </div>
                <div className="pg-shelf-edge" />
              </div>
            ))}
          </div>

          <section className="pg-card">
            <div className="pg-kv">
              <h3 className="pg-card-title">{t('sp.buildSheet')}</h3>
              <span className="pg-card-note" style={{ margin: 0 }}>
                {t('sp.buildSheetHint')}
              </span>
            </div>
            <div style={{ overflowX: 'auto', marginTop: 12 }}>
              <table className="pg-sheet">
                <thead>
                  <tr>
                    <th>{t('sp.colShelf')}</th>
                    <th>{t('sp.colPosition')}</th>
                    <th>{t('sp.colStartsAt')}</th>
                    <th>{t('common.product')}</th>
                    <th>{t('sp.colFacings')}</th>
                    <th>{t('sp.colDepth')}</th>
                    <th>{t('sp.colBring')}</th>
                    <th>{t('sp.colShort')}</th>
                  </tr>
                </thead>
                <tbody>
                  {sheetRows.map((row) => (
                    <tr
                      className={row.unfillable ? 'pg-sheet-unfillable' : undefined}
                      key={`${row.shelfCode}-${row.position}`}
                    >
                      <td>{row.shelfCode}</td>
                      <td className="pg-mono">{n(row.position)}</td>
                      <td className="pg-mono">{`${n(Math.round(row.startCm))} ${t('sl.cm')}`}</td>
                      <td>{row.productName}</td>
                      <td className="pg-mono">{n(row.facings)}</td>
                      <td className="pg-mono">{n(row.depthUnits)}</td>
                      <td className="pg-mono">{row.unfillable ? '—' : n(row.unitsToPlace)}</td>
                      <td className="pg-mono">{row.shortfall > 0 ? n(row.shortfall) : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="pg-card-note">
              {t('sp.sheetNote')}
            </p>
          </section>

          <section className="pg-card">
            <div className="pg-kv">
              <h3 className="pg-card-title">{t('sp.shapeLibrary', { n: n(Object.keys(PACKAGE_SHAPES).length) })}</h3>
              <span className="pg-card-note" style={{ margin: 0 }}>
                {t('sp.shapeLibraryHint')}
              </span>
            </div>
            {catalogue.map((group) => (
              <div key={group.name}>
                <h4 className="pg-catalogue-group-name">{group.name}</h4>
                <div className="pg-catalogue-grid">
                  {group.items.map((visual) => (
                    <div className="pg-catalogue-item" key={visual.key}>
                      <div className="pg-catalogue-stage">
                        <PackageGlyph visual={visual} />
                      </div>
                      <span className="pg-catalogue-label">{visual.typeLabel}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </section>
        </div>

        <div className="pg-stack">
          <section
            className="pg-card"
            style={{ background: validation.valid ? 'var(--pg-ok-wash)' : 'var(--pg-out-wash)', borderColor: 'transparent' }}
          >
            <div className="pg-kv">
              <h3 className="pg-card-title">{t('sp.validation')}</h3>
              <span
                className="pg-tag"
                style={{ color: validation.valid ? 'var(--pg-ok)' : 'var(--pg-out)', background: 'transparent', fontWeight: 700 }}
              >
                {validation.valid ? t('sp.valid') : t('sp.violations', { n: n(validation.violations.length) })}
              </span>
            </div>
            <p className="pg-card-note">
              {t('sp.validationNote', {
                positions: n(validation.checkedPositions),
                shelves: n(validation.checkedShelves),
              })}
            </p>
            {validation.violations.map((entry) => (
              <p className="pg-card-note" key={`${entry.rule}-${entry.productId ?? entry.shelfCode}`} style={{ color: 'var(--pg-out)', fontWeight: 600 }}>
                {entry.message}
              </p>
            ))}
            {validation.warnings.slice(0, 2).map((entry) => (
              <p className="pg-card-note" key={`${entry.rule}-${entry.shelfCode}`}>
                {entry.message}
              </p>
            ))}
          </section>

          <ShelfPhotoPanel category={activeCategory} planSummary={summary} unitId={unit.id} />

          {comparison && (
            <section className="pg-card">
              <h3 className="pg-card-title">{t('sp.vsBaseline')}</h3>
              <p className="pg-card-note">
                {t('sp.vsBaselineHint')}
              </p>
              <div style={{ marginTop: 12 }}>
                <div className="pg-kv">
                  <span className="pg-kv-key">{t('sp.perMetreUs')}</span>
                  <span className="pg-kv-value">{`${d(comparison.smartshelf.marginPerMetre)} ₪`}</span>
                </div>
                <div className="pg-kv">
                  <span className="pg-kv-key">{t('sp.perMetreBase')}</span>
                  <span className="pg-kv-value">{`${d(comparison.marginRule.marginPerMetre)} ₪`}</span>
                </div>
                <div className="pg-kv" style={{ marginTop: 10, paddingTop: 9, borderTop: '1px solid var(--pg-line)' }}>
                  <span className="pg-kv-key">{t('sp.difference')}</span>
                  <span
                    className="pg-kv-value"
                    style={{ color: comparison.smartshelf.marginPerMetre >= comparison.marginRule.marginPerMetre ? 'var(--pg-ok)' : 'var(--pg-out)' }}
                  >
                    {formatDelta(comparison.smartshelf.marginPerMetre, comparison.marginRule.marginPerMetre, d, n, percentSign)}
                  </span>
                </div>
              </div>
            </section>
          )}

          <section className="pg-card">
            <h3 className="pg-card-title">{t('sp.vsApproved')}</h3>
            {!approved && (
              <p className="pg-card-note">
                {t('sp.noApproved')}
              </p>
            )}
            {approved && (
              <>
                <p className="pg-card-note">
                  {t('sp.approvedOn', {
                    date: new Date(approved.approvedAt).toLocaleDateString(),
                    n: n(approved.placements.length),
                  })}
                </p>
                <div className="pg-kv" style={{ marginTop: 11 }}>
                  <span className="pg-kv-key">{t('sp.changedPositions')}</span>
                  <span className="pg-kv-value">{n(stability.changedPositions ?? 0)}</span>
                </div>
                {stability.moves.slice(0, 5).map((move) => (
                  <p className="pg-card-note" key={move.productId}>
                    {describeMove(move, t, n)}
                  </p>
                ))}
                {stability.moves.length > 5 && (
                  <p className="pg-card-note">{t('sp.moreChanges', { n: n(stability.moves.length - 5) })}</p>
                )}
              </>
            )}
          </section>

          <section className="pg-card">
            <h3 className="pg-card-title">{t('sp.advice')}</h3>
            <p className="pg-card-note">
              {t('sp.adviceHint')}
            </p>
            <div className="pg-stack" style={{ gap: 10, marginTop: 13 }}>
              {advice.length === 0 && <p className="pg-card-note">{t('sp.noAdvice')}</p>}
              {advice.map((entry) => (
                <div className="pg-tip-card" key={entry.id} style={{ background: STATUS_WASH[entry.status] }}>
                  <div className="pg-tip-card-tag" style={{ color: STATUS_COLOR[entry.status] }}>
                    <span className="pg-swatch" style={{ background: STATUS_COLOR[entry.status] }} />
                    <span>{entry.tag}</span>
                  </div>
                  <p className="pg-tip-card-title">{entry.title}</p>
                  <p className="pg-tip-card-body">{entry.body}</p>
                </div>
              ))}
            </div>
          </section>

          {allocation?.suspect?.length > 0 && (
            <section className="pg-card" style={{ background: 'var(--pg-low-wash)', borderColor: 'transparent' }}>
              <div className="pg-kv">
                <h3 className="pg-card-title">{t('sp.suspect')}</h3>
                <span className="pg-tag pg-tag-warn">{n(allocation.suspect.length)}</span>
              </div>
              <p className="pg-card-note">
                {t('sp.suspectNote')}
              </p>
              {allocation.suspect.slice(0, 4).map((entry) => (
                <div className="pg-kv" key={entry.product.id} style={{ marginTop: 9 }}>
                  <span className="pg-kv-key">{entry.product.name}</span>
                  <span className="pg-kv-value pg-mono">{`${d(entry.marginPerUnit)} ₪`}</span>
                </div>
              ))}
              {allocation.suspect.length > 4 && (
                <p className="pg-card-note">{t('sp.andOthers', { n: n(allocation.suspect.length - 4) })}</p>
              )}
            </section>
          )}

          <section className="pg-card">
            <h3 className="pg-card-title" style={{ marginBottom: 11 }}>{t('sp.summary')}</h3>
            <div className="pg-kv">
              <span className="pg-kv-key">{t('sp.placed')}</span>
              <span className="pg-kv-value">{n(summary?.placedProducts ?? 0)}</span>
            </div>
            <div className="pg-kv">
              <span className="pg-kv-key">{t('sp.totalFacings')}</span>
              <span className="pg-kv-value">{n(summary?.totalFacings ?? 0)}</span>
            </div>
            <div className="pg-kv">
              <span className="pg-kv-key">{t('sp.unplaced')}</span>
              <span className="pg-kv-value">{n(summary?.unplacedProducts ?? 0)}</span>
            </div>
            <div className="pg-kv">
              <span className="pg-kv-key">{t('sp.estimatedDims')}</span>
              <span className="pg-kv-value">{n(summary?.estimatedGeometryCount ?? 0)}</span>
            </div>
          </section>

          <section className="pg-card" style={{ background: 'var(--pg-low-wash)', borderColor: 'transparent' }}>
            <h3 className="pg-card-title">{t('sp.basisTitle')}</h3>
            <p className="pg-card-note">
              {(() => {
                // The old text stated flatly that there is no sales history.
                // That is false for this store — 1,564 of 7,451 products carry
                // medium or high confidence — and the truth varies per fixture,
                // so the sentence has to be built from what this plan actually
                // rests on rather than asserted once.
                const mix = summary?.demandConfidence ?? { none: 0, low: 0, medium: 0, high: 0 }
                const measured = mix.low + mix.medium + mix.high
                const total = measured + mix.none
                return measured > 0
                  ? t('sp.basisMeasured', {
                      total: n(total),
                      measured: n(measured),
                      assumed: n(mix.none),
                    })
                  : t('sp.basisAllAssumed')
              })()}
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}

/** One product's block of facings, plus its hover card. */
function ShelfPosition({ item, hovered, onHover, tipBelow, tipAtStart, t, n, d }) {
  const visual = shapeVisual(item.shapeKey)

  return (
    <div
      className="pg-position"
      style={{ flex: `${item.facings} 1 0` }}
      onMouseEnter={() => onHover(item.productId)}
      onMouseLeave={() => onHover(null)}
    >
      <button
        className="pg-facings"
        style={{ display: 'flex', width: '100%' }}
        type="button"
        onFocus={() => onHover(item.productId)}
        onBlur={() => onHover(null)}
      >
        {Array.from({ length: item.facings }, (_, index) => (
          <span className="pg-facing-slot" key={index}>
            <PackageGlyph visual={visual} />
          </span>
        ))}
      </button>

      {/* One label for the whole block, not one per facing. Twelve facings of a
          330ml can are 14px wide each; a name repeated into each of them was
          twelve columns of unreadable fragments. CSS hides this below the width
          where it would be illegible anyway. */}
      <span className="pg-position-label">{item.productName}</span>

      <span className="pg-status-dot" style={{ background: STATUS_COLOR[item.status] }} />

      {hovered && (
        <div
          className="pg-tip"
          style={{
            top: tipBelow ? 'calc(100% + 10px)' : 'auto',
            bottom: tipBelow ? 'auto' : 'calc(100% + 10px)',
            insetInlineEnd: tipAtStart ? 'auto' : 0,
            insetInlineStart: tipAtStart ? 0 : 'auto',
          }}
        >
          <div className="pg-tip-name">{item.productName}</div>
          <div className="pg-tip-tags">
            <span className="pg-tag">{visual.typeLabel}</span>
            <span className="pg-tag pg-mono" style={{ background: 'transparent' }}>{item.productId}</span>
            {item.estimatedGeometry && <span className="pg-tag pg-tag-warn">{t('sp.estimatedDims')}</span>}
          </div>
          <div className="pg-tip-grid">
            <TipCell label={t('sp.colFacings')} value={n(item.facings)} />
            <TipCell label={t('sp.colDepth')} value={n(item.depthUnits)} />
            <TipCell label={t('sl.levels')} value={n(item.stack)} />
            <TipCell label={t('sp.piecesShown', { n: '' }).trim()} value={n(item.onShelf)} />
          </div>
          <div className="pg-tip-row">
            <span className="pg-kv-key">{t('sp.inBackroom')}</span>
            <span className="pg-kv-value">{n(item.currentStock)}</span>
          </div>
          <div className="pg-tip-row">
            <span className="pg-kv-key">{t('sp.profitPerCm')}</span>
            <span className="pg-kv-value">{`${d(item.profitPerCm)} ₪`}</span>
          </div>
          <div
            className="pg-tip-advice"
            style={{ background: STATUS_WASH[item.status], color: STATUS_COLOR[item.status] }}
          >
            {t(ADVICE_KEY[item.status])}
          </div>
        </div>
      )}
    </div>
  )
}

function TipCell({ label, value }) {
  return (
    <div className="pg-tip-cell">
      <div className="pg-tip-cell-key">{label}</div>
      <div className="pg-tip-cell-value">{value}</div>
    </div>
  )
}

/** Draw one package: cap, neck, body — the shape catalogue's whole vocabulary. */
function PackageGlyph({ visual, label, sku }) {
  return (
    <span className="pg-package" style={{ width: visual.faceW, height: visual.faceH }}>
      {visual.hasCap && (
        <span
          style={{ width: visual.capW, height: visual.capH, borderRadius: visual.capR, background: visual.capColor }}
        />
      )}
      {visual.hasNeck && (
        <span style={{ width: visual.neckW, height: visual.neckH, background: visual.neckColor }} />
      )}
      <span className="pg-package-body" style={{ borderRadius: visual.bodyR, background: visual.color }}>
        {label && visual.showName && <span className="pg-package-label">{label}</span>}
        {sku && visual.showSku && <span className="pg-package-sku">{sku}</span>}
      </span>
    </span>
  )
}

/**
 * Turn the allocation into things a shop manager can act on.
 *
 * Every line is derived from the allocation itself — no thresholds invented for
 * the sake of having three cards. When the shelf is fine, this returns nothing.
 */
function buildAdvice(shelves, unit, t, n, d) {
  const items = shelves.flatMap((shelf) => shelf.items)
  if (!items.length) return []

  const advice = []
  const needsFill = items.filter((item) => item.status !== 'ok')

  const urgent = [...needsFill]
    .filter((item) => item.status === 'out')
    .sort((left, right) => right.profitPerCm - left.profitPerCm)[0]

  if (urgent) {
    advice.push({
      id: 'urgent',
      status: 'out',
      tag: t('sp.highPriority'),
      title: t('sp.widenFacings', { name: urgent.productName }),
      body: t('sp.widenBody', {
        onShelf: n(urgent.onShelf),
        facings: n(urgent.facings),
        stock: n(urgent.currentStock),
        perCm: d(urgent.profitPerCm),
      }),
    })
  }

  if (needsFill.length) {
    const names = needsFill.slice(0, 3).map((item) => item.productName)
    const rest = needsFill.length - names.length
    advice.push({
      id: 'refill',
      status: 'low',
      tag: t('sp.refill'),
      title: t('sp.belowRefill', { n: n(needsFill.length) }),
      body: `${names.join(', ')}${rest > 0 ? ` ${t('sp.andOthers', { n: n(rest) })}` : ''}.`,
    })
  }

  // Space that no product on the shelf can use, because nothing left fits it.
  const slack = shelves
    .map((shelf) => ({ shelf, freeCm: shelf.runCm - shelf.usedCm }))
    .filter((entry) => entry.freeCm >= 8)
    .sort((left, right) => right.freeCm - left.freeCm)[0]

  if (slack) {
    const best = [...slack.shelf.items].sort((left, right) => right.profitPerCm - left.profitPerCm)[0]
    advice.push({
      id: 'slack',
      status: 'ok',
      tag: t('sp.space'),
      title: t('sp.freeSpaceOn', { cm: n(Math.round(slack.freeCm)), shelf: slack.shelf.code }),
      body: best
        ? t('sp.freeSpaceBody', {
            n: n(Math.floor(slack.freeCm / best.widthCm)),
            name: best.productName,
          })
        : t('sp.freeSpaceNone', { unit: unit.name }),
    })
  }

  return advice
}

/** Signed difference, so a loss against the baseline reads as a loss. */
function formatDelta(candidate, baseline, d, n, percentSign) {
  const delta = candidate - baseline
  const sign = delta >= 0 ? '+' : '−'
  const percent = baseline > 0 ? Math.round((delta / baseline) * 100) : 0
  return `${sign}${d(Math.abs(delta))} ₪ (${sign}${n(Math.abs(percent))}${percentSign})`
}

/** One move, phrased as the work it implies rather than as a diff. */
function describeMove(move, t, n) {
  if (move.kind === 'added') return t('sp.moveAdd', { name: move.productName, to: n(move.to) })
  if (move.kind === 'removed') return t('sp.moveRemove', { id: move.productId })
  return t('sp.moveFacings', { name: move.productName, from: n(move.from), to: n(move.to) })
}

/** Stable value across renders without re-running the initialiser. */
function useMemoOnce(factory) {
  const [value] = useState(factory)
  return value
}
