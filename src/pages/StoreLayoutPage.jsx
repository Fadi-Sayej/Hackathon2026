import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  FIXTURE_KINDS,
  FIXTURE_PRESETS,
  buildPreset,
  estimateFacingCapacity,
  floorOccupancy,
  linearMetres,
  totalLinearMetres,
} from '../lib/planogram/fixtures.js'
import { loadStoreLayout, saveStoreLayout } from '../lib/planogram/layoutStorage.js'
import { useNumbers, useT } from '../lib/i18n/index.js'
import { ShelfPlanPage } from './ShelfPlanPage.jsx'
import '../styles/planogram.css'

const DEFAULT_PRESET = 'medium'
/** Grid snap, in metres. Fixtures are bought in round sizes; 10cm is enough. */
const SNAP_M = 0.1

function initialLayout() {
  const saved = loadStoreLayout()
  if (saved) return { storeW: saved.storeW, storeH: saved.storeH, units: saved.units }
  const preset = FIXTURE_PRESETS[DEFAULT_PRESET]
  return { storeW: preset.w, storeH: preset.h, units: buildPreset(preset) }
}

const snap = (value) => Math.round(value / SNAP_M) * SNAP_M

/**
 * Store layout editor — the manager draws their own floor plan.
 *
 * This is the data-entry screen for the fixture layer. Nothing downstream can
 * compute a real facing count until this exists, because until now the only
 * shelf dimension in the system was the `shelfCapacity: 10` constant stamped
 * onto every product by the normalisation script.
 */
export function StoreLayoutPage({ onOpenUnit, analyzedProducts = [], demandIndexById = {} }) {
  const t = useT()
  const { n, d, percentSign } = useNumbers()
  const [layout, setLayout] = useState(initialLayout)
  const [selectedId, setSelectedId] = useState(null)
  const [saved, setSaved] = useState(false)
  const [canvasWidth, setCanvasWidth] = useState(560)
  const sequence = useRef(1000)
  const canvasRef = useRef(null)
  const dragRef = useRef(null)

  const { storeW, storeH, units } = layout

  // The canvas is percentage-positioned, but label-fit decisions need pixels.
  useEffect(() => {
    const node = canvasRef.current
    if (!node || typeof ResizeObserver === 'undefined') return undefined
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect?.width
      if (width) setCanvasWidth(width)
    })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  const mutate = useCallback((updater) => {
    setSaved(false)
    setLayout(updater)
  }, [])

  const patchUnit = useCallback(
    (id, fields) => {
      mutate((current) => ({
        ...current,
        units: current.units.map((unit) => (unit.id === id ? { ...unit, ...fields } : unit)),
      }))
    },
    [mutate],
  )

  const pointToMetres = useCallback(
    (event) => {
      const rect = canvasRef.current?.getBoundingClientRect()
      if (!rect) return { x: 0, y: 0 }
      return {
        x: ((event.clientX - rect.left) / rect.width) * storeW,
        y: ((event.clientY - rect.top) / rect.height) * storeH,
      }
    },
    [storeH, storeW],
  )

  const startDrag = useCallback(
    (event, id, mode) => {
      event.stopPropagation()
      const point = pointToMetres(event)
      const unit = units.find((entry) => entry.id === id)
      if (!unit) return
      dragRef.current = {
        id,
        mode,
        offsetX: point.x - unit.x,
        offsetY: point.y - unit.y,
        startW: unit.w,
        startD: unit.d,
        startX: point.x,
        startY: point.y,
      }
      setSelectedId(id)
    },
    [pointToMetres, units],
  )

  const handleMove = useCallback(
    (event) => {
      const drag = dragRef.current
      if (!drag) return
      const point = pointToMetres(event)
      const unit = units.find((entry) => entry.id === drag.id)
      if (!unit) return

      if (drag.mode === 'move') {
        patchUnit(drag.id, {
          x: clamp(snap(point.x - drag.offsetX), 0, storeW - unit.w),
          y: clamp(snap(point.y - drag.offsetY), 0, storeH - unit.d),
        })
        return
      }

      // Resize from the physical bottom-right corner, so the handle tracks the
      // cursor instead of running away from it.
      patchUnit(drag.id, {
        w: clamp(snap(drag.startW + (point.x - drag.startX)), 0.3, storeW - unit.x),
        d: clamp(snap(drag.startD + (point.y - drag.startY)), 0.3, storeH - unit.y),
      })
    },
    [patchUnit, pointToMetres, storeH, storeW, units],
  )

  const endDrag = useCallback(() => {
    dragRef.current = null
  }, [])

  const addUnit = useCallback(
    (kind) => {
      const spec = FIXTURE_KINDS[kind]
      const id = `n${sequence.current++}`
      mutate((current) => ({
        ...current,
        units: [
          ...current.units,
          {
            id,
            kind,
            name: spec.label,
            x: clamp(1, 0, Math.max(0, current.storeW - spec.w)),
            y: 1,
            w: spec.w,
            d: spec.d,
            levels: spec.levels,
            height: spec.height,
          },
        ],
      }))
      setSelectedId(id)
    },
    [mutate],
  )

  const applyPreset = useCallback(
    (key) => {
      const preset = FIXTURE_PRESETS[key]
      mutate({ storeW: preset.w, storeH: preset.h, units: buildPreset(preset) })
      setSelectedId(null)
    },
    [mutate],
  )

  const selected = useMemo(
    () => units.find((unit) => unit.id === selectedId) ?? null,
    [selectedId, units],
  )

  const totals = useMemo(
    () => ({
      run: totalLinearMetres(units),
      occupancy: floorOccupancy(units, storeW, storeH),
    }),
    [storeH, storeW, units],
  )

  const metresToPx = canvasWidth / storeW
  const canvasHeightPx = canvasWidth * (storeH / storeW)

  return (
    <div className="pg">
      <header className="pg-header">
        <div className="pg-header-id">
          <div className="pg-badge">{t('sl.badge')}</div>
          <div>
            <h2>{t('sl.title')}</h2>
            <p className="pg-header-sub">{t('sl.sub')}</p>
          </div>
        </div>
        <div className="pg-header-actions">
          <div className="pg-stat-chip">
            <span>{t('sl.area')}</span>
            <span>{`${n(Math.round(storeW * storeH))} ${t('sl.sqm')}`}</span>
          </div>
          <div className="pg-stat-chip">
            <span>{t('sl.unitCount')}</span>
            <span>{n(units.length)}</span>
          </div>
          <button
            className="pg-button"
            type="button"
            onClick={() => setSaved(saveStoreLayout({ storeW, storeH, units }))}
          >
            {saved ? t('sl.saved') : t('sl.save')}
          </button>
        </div>
      </header>

      <div className="pg-split pg-split-editor">
        <div className="pg-stack">
          <section className="pg-card">
            <h3 className="pg-card-title">{t('sl.dims')}</h3>
            <div className="pg-field-grid" style={{ marginTop: 11 }}>
              <label>
                <div className="pg-field-label">{t('sl.width')}</div>
                <input
                  className="pg-input pg-input-num"
                  type="number"
                  value={storeW}
                  onChange={(event) =>
                    mutate((current) => ({ ...current, storeW: Math.max(4, Number(event.target.value) || 4) }))
                  }
                />
              </label>
              <label>
                <div className="pg-field-label">{t('sl.depth')}</div>
                <input
                  className="pg-input pg-input-num"
                  type="number"
                  value={storeH}
                  onChange={(event) =>
                    mutate((current) => ({ ...current, storeH: Math.max(4, Number(event.target.value) || 4) }))
                  }
                />
              </label>
            </div>
            <div className="pg-kv" style={{ marginTop: 12 }}>
              <span className="pg-kv-key">{t('sl.grid')}</span>
              <span className="pg-mono" style={{ fontSize: 11.5 }}>{t('sl.gridNote')}</span>
            </div>
          </section>

          <section className="pg-card">
            <h3 className="pg-card-title">{t('sl.addUnit')}</h3>
            <p className="pg-card-note">{t('sl.addUnitHint')}</p>
            <div className="pg-stack" style={{ gap: 8, marginTop: 12 }}>
              {Object.entries(FIXTURE_KINDS).map(([key, spec]) => (
                <button className="pg-palette-item" key={key} type="button" onClick={() => addUnit(key)}>
                  <span
                    className="pg-palette-chip"
                    style={{ background: spec.color, border: `1.5px solid ${spec.stroke}`, borderRadius: spec.radius }}
                  />
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <span className="pg-palette-name" style={{ display: 'block' }}>{spec.label}</span>
                    <span className="pg-palette-dims">{`${spec.w} × ${spec.d} ${t('sl.metres')}`}</span>
                  </span>
                  <span className="pg-palette-plus">+</span>
                </button>
              ))}
            </div>
          </section>

          <section className="pg-card">
            <h3 className="pg-card-title">{t('sl.presets')}</h3>
            <div className="pg-stack" style={{ gap: 8, marginTop: 10 }}>
              {Object.entries(FIXTURE_PRESETS).map(([key, preset]) => (
                <button className="pg-unit-row" key={key} type="button" onClick={() => applyPreset(key)}>
                  <span className="pg-unit-row-name">{preset.name}</span>
                  <span className="pg-palette-dims">{preset.hint}</span>
                </button>
              ))}
            </div>
          </section>
        </div>

        <div className="pg-stack">
          <div className="pg-legend">
            {['gondola', 'wall', 'fridge', 'produce', 'checkout'].map((key) => (
              <span className="pg-legend-item" key={key}>
                <span
                  className="pg-swatch pg-swatch-wide"
                  style={{ background: FIXTURE_KINDS[key].color, border: `1px solid ${FIXTURE_KINDS[key].stroke}` }}
                />
                <span>{FIXTURE_KINDS[key].label}</span>
              </span>
            ))}
            <span className="pg-hint">{t('sl.canvasHint')}</span>
          </div>

          <section className="pg-card">
            <div
              className="pg-canvas"
              ref={canvasRef}
              style={{
                paddingTop: `${(storeH / storeW) * 100}%`,
                backgroundSize: `${100 / storeW}% ${100 / storeH}%`,
              }}
              onPointerMove={handleMove}
              onPointerUp={endDrag}
              onPointerLeave={endDrag}
              onClick={() => setSelectedId(null)}
            >
              {units.map((unit) => {
                const spec = FIXTURE_KINDS[unit.kind] ?? FIXTURE_KINDS.gondola
                const isSelected = unit.id === selectedId
                const widthPx = unit.w * metresToPx
                const depthPx = unit.d * metresToPx
                const fitsInside = depthPx >= 20 && widthPx > 56
                const dimText = `${d(unit.w)}×${d(unit.d)}`

                return (
                  <div
                    className="pg-unit"
                    key={unit.id}
                    style={{
                      left: `${(unit.x / storeW) * 100}%`,
                      top: `${(unit.y / storeH) * 100}%`,
                      width: `${(unit.w / storeW) * 100}%`,
                      height: `${(unit.d / storeH) * 100}%`,
                      background: spec.color,
                      border: isSelected ? '2px solid var(--pg-accent)' : `1.5px solid ${spec.stroke}`,
                      borderRadius: spec.radius,
                      boxShadow: isSelected
                        ? '0 0 0 3px rgba(0, 108, 73, 0.2)'
                        : '0 1px 3px rgba(0, 0, 0, 0.18)',
                    }}
                    onPointerDown={(event) => startDrag(event, unit.id, 'move')}
                    onClick={(event) => {
                      event.stopPropagation()
                      setSelectedId(unit.id)
                    }}
                  >
                    {fitsInside && (
                      <span className="pg-unit-label" style={{ color: spec.text }}>
                        {unit.name}
                      </span>
                    )}
                    {depthPx >= 34 && widthPx > 78 && <span className="pg-unit-dims">{dimText}</span>}
                    {!fitsInside && (
                      <span className="pg-unit-tag" style={outsideTagPosition(unit, metresToPx, canvasHeightPx, depthPx)}>
                        {`${unit.name} · ${dimText}`}
                      </span>
                    )}
                    {isSelected && (
                      <button
                        aria-label={t('sl.estCapacity')}
                        className="pg-unit-handle"
                        style={{ left: 'auto', top: 'auto', right: 0, bottom: 0, borderRadius: '6px 0 0 0' }}
                        type="button"
                        onPointerDown={(event) => startDrag(event, unit.id, 'size')}
                      />
                    )}
                  </div>
                )
              })}

              <div className="pg-scale">
                <span className="pg-scale-bar" style={{ width: `${(5 / storeW) * 100}%` }} />
                <span>{t('sl.scale5m')}</span>
              </div>
            </div>
          </section>

          <div className="pg-split" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
            {selected && (
              <section className="pg-card">
                <div className="pg-kv">
                  <h3 className="pg-card-title">{t('sl.unitProps')}</h3>
                  <span className="pg-palette-dims">{selected.id.toUpperCase()}</span>
                </div>

                <label style={{ display: 'block', marginTop: 12 }}>
                  <div className="pg-field-label">{t('sl.name')}</div>
                  <input
                    className="pg-input"
                    value={selected.name}
                    onChange={(event) => patchUnit(selected.id, { name: event.target.value })}
                  />
                </label>

                <div className="pg-field-grid" style={{ marginTop: 11 }}>
                  <NumberField
                    label={t('sl.length')}
                    step="0.1"
                    value={selected.w}
                    onCommit={(value) => patchUnit(selected.id, { w: Math.max(0.3, value) })}
                  />
                  <NumberField
                    label={t('sl.depth')}
                    step="0.1"
                    value={selected.d}
                    onCommit={(value) => patchUnit(selected.id, { d: Math.max(0.3, value) })}
                  />
                  <NumberField
                    label={t('sl.levels')}
                    value={selected.levels}
                    onCommit={(value) => patchUnit(selected.id, { levels: Math.max(1, Math.round(value)) })}
                  />
                  <NumberField
                    label={t('sl.height')}
                    step="0.1"
                    value={selected.height}
                    onCommit={(value) => patchUnit(selected.id, { height: Math.max(0.3, value) })}
                  />
                </div>

                <div className="pg-actions-row">
                  <button
                    className="pg-button pg-button-ghost"
                    type="button"
                    onClick={() => patchUnit(selected.id, { w: selected.d, d: selected.w })}
                  >
                    {t('sl.rotate')}
                  </button>
                  <button
                    className="pg-button pg-button-ghost"
                    type="button"
                    onClick={() => {
                      const id = `n${sequence.current++}`
                      mutate((current) => ({
                        ...current,
                        units: [
                          ...current.units,
                          {
                            ...selected,
                            id,
                            x: Math.min(selected.x + 0.5, current.storeW - selected.w),
                            y: Math.min(selected.y + 0.5, current.storeH - selected.d),
                          },
                        ],
                      }))
                      setSelectedId(id)
                    }}
                  >
                    {t('common.duplicate')}
                  </button>
                  <button
                    className="pg-button pg-button-danger"
                    type="button"
                    onClick={() => {
                      mutate((current) => ({
                        ...current,
                        units: current.units.filter((unit) => unit.id !== selected.id),
                      }))
                      setSelectedId(null)
                    }}
                  >
                    {t('common.delete')}
                  </button>
                </div>

                <div className="pg-readout">
                  <div className="pg-kv">
                    <span className="pg-kv-key">{t('sl.totalRun')}</span>
                    <span className="pg-kv-value">{`${d(linearMetres(selected))} ${t('sl.metresRun')}`}</span>
                  </div>
                  <div className="pg-kv">
                    <span className="pg-kv-key">{t('sl.estCapacity')}</span>
                    <span className="pg-kv-value">{`${n(estimateFacingCapacity(selected))} ${t('sl.facingsUnit')}`}</span>
                  </div>
                </div>

                <button
                  className="pg-button pg-button-dark"
                  style={{ width: '100%', marginTop: 11 }}
                  type="button"
                  onClick={() => onOpenUnit?.(selected)}
                >
                  {t('layout.openPlanFull')}
                </button>
              </section>
            )}

            <section className="pg-card">
              <h3 className="pg-card-title" style={{ marginBottom: 10 }}>{t('sl.unitList')}</h3>
              <div className="pg-unit-list">
                {units.map((unit) => {
                  const spec = FIXTURE_KINDS[unit.kind] ?? FIXTURE_KINDS.gondola
                  return (
                    <button
                      className={`pg-unit-row${unit.id === selectedId ? ' pg-unit-row-selected' : ''}`}
                      key={unit.id}
                      type="button"
                      onClick={() => setSelectedId(unit.id)}
                    >
                      <span
                        className="pg-swatch"
                        style={{ background: spec.color, border: `1px solid ${spec.stroke}` }}
                      />
                      <span className="pg-unit-row-name">{unit.name}</span>
                      <span className="pg-palette-dims">{`${d(unit.w)}×${d(unit.d)} ${t('sl.metres')}`}</span>
                    </button>
                  )
                })}
              </div>
              <div className="pg-kv" style={{ marginTop: 11, paddingTop: 10, borderTop: '1px solid var(--pg-line)' }}>
                <span className="pg-kv-key">{t('sl.totalMetres')}</span>
                <span className="pg-kv-value">{`${d(totals.run)} ${t('sl.metres')}`}</span>
              </div>
              <div className="pg-kv">
                <span className="pg-kv-key">{t('sl.occupancy')}</span>
                <span className="pg-kv-value">{`${n(Math.round(totals.occupancy * 100))}${percentSign}`}</span>
              </div>
            </section>
          </div>
        </div>
      </div>

      {selected && (
        <section className="pg-inline-plan">
          <div className="pg-inline-plan-head">
            <h2 className="pg-card-title" style={{ fontSize: 16 }}>
              {t('layout.planFor', { name: selected.name })}
            </h2>
            <p className="pg-card-note">{t('layout.planForHint')}</p>
          </div>
          <ShelfPlanPage
            analyzedProducts={analyzedProducts}
            demandIndexById={demandIndexById}
            embedded
            planogramUnit={selected}
          />
        </section>
      )}
    </div>
  )
}

/**
 * A number input that only commits a valid value.
 *
 * Bare `Number(value) || fallback` on every keystroke makes the field
 * un-editable — clearing it to type a new number snaps straight back to the
 * fallback. This keeps the typed text until it parses.
 */
function NumberField({ label, value, step, onCommit }) {
  const [draft, setDraft] = useState(String(value))
  const [editing, setEditing] = useState(false)

  return (
    <label>
      <div className="pg-field-label">{label}</div>
      <input
        className="pg-input pg-input-num"
        type="number"
        step={step}
        value={editing ? draft : String(value)}
        onFocus={() => {
          setDraft(String(value))
          setEditing(true)
        }}
        onBlur={() => setEditing(false)}
        onChange={(event) => {
          setDraft(event.target.value)
          const parsed = Number(event.target.value)
          if (event.target.value !== '' && Number.isFinite(parsed)) onCommit(parsed)
        }}
      />
    </label>
  )
}

/** Place the label outside a fixture too small to hold it, without overflowing. */
function outsideTagPosition(unit, metresToPx, canvasHeightPx, depthPx) {
  if (depthPx < 20) {
    const belowFitsOff = (unit.y + unit.d) * metresToPx > canvasHeightPx - 20
    return belowFitsOff
      ? { left: 0, bottom: 'calc(100% + 3px)' }
      : { left: 0, top: 'calc(100% + 3px)' }
  }
  return unit.x * metresToPx < 90
    ? { top: 0, left: 'calc(100% + 5px)' }
    : { top: 0, right: 'calc(100% + 5px)' }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), Math.max(min, max))
}
