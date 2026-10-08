import { useState } from 'react'

import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'
import { blankShelf, blankUnit, cleaned, unitProblem } from '../owner/shelfUnits.js'

/**
 * D-38: the owner describes each shelving unit once, so no one edits the layout file (F12-S1
 * FR-228). Per unit: its name, its departments, whether it is chilled, its shelves from the top
 * with each one's length and height, and the eye-level shelf. The top shelf's height may be left
 * empty when nothing is above it.
 *
 * Saving is the caller's (`onSave`, ADR-043): this screen only edits and reports. It saves the
 * whole list, so what it shows is what is kept. A team account sees it disabled (ADR-029).
 */

function Size({ shelf }) {
  const { t } = useI18n()
  return <bdi>{shelf.height_cm
    ? t('units.shelfSize', { length: shelf.length_cm, height: shelf.height_cm })
    : t('units.shelfSize.open', { length: shelf.length_cm })}</bdi>
}

function Editor({ start, others, departments, onDone, onCancel, onRemove, readOnly }) {
  const { t } = useI18n()
  const [unit, setUnit] = useState(start)
  const [removing, setRemoving] = useState(false)
  const set = (patch) => setUnit((u) => ({ ...u, ...patch }))
  const setShelf = (i, patch) => set({ shelves: unit.shelves.map((s, k) => (k === i ? { ...s, ...patch } : s)) })
  const problem = unitProblem(unit, others)
  const left = departments.filter((d) => !unit.departments.includes(d))

  return (
    <div className="units__editor" data-editing={unit.name || 'new'}>
      <label className="photos__field">
        <span>{t('units.name')}</span>
        <input type="text" value={unit.name} disabled={readOnly} onChange={(e) => set({ name: e.target.value })} />
        <small className="plan__muted">{t('units.name.hint')}</small>
      </label>

      <div className="photos__field">
        <span>{t('units.departments')}</span>
        {unit.departments.length ? (
          <ul className="units__chips">
            {unit.departments.map((d) => (
              <li key={d}>
                <bdi>{d}</bdi>
                <button type="button" className="units__chip-remove" disabled={readOnly}
                  aria-label={t('units.departments.remove', { name: d })}
                  onClick={() => set({ departments: unit.departments.filter((x) => x !== d) })}>×</button>
              </li>
            ))}
          </ul>
        ) : null}
        <select value="" disabled={readOnly || !left.length}
          onChange={(e) => e.target.value && set({ departments: [...unit.departments, e.target.value] })}>
          <option value="">{t('units.departments.add')}</option>
          {left.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      <label className="units__check">
        <input type="checkbox" checked={unit.chilled} disabled={readOnly} onChange={(e) => set({ chilled: e.target.checked })} />
        <span>{t('units.chilled')}</span>
      </label>

      <fieldset className="units__shelves" disabled={readOnly}>
        <legend>{t('units.shelves')}</legend>
        <p className="plan__muted">{t('units.measure')}</p>
        {unit.shelves.map((s, i) => (
          <div key={i} className="units__shelf" data-shelf={i + 1}>
            <span className="layout__shelf-name">{t('layout.shelf', { n: i + 1 })}</span>
            <label>
              <span>{t('units.length')}</span>
              <input type="text" inputMode="numeric" value={s.length_cm} onChange={(e) => setShelf(i, { length_cm: e.target.value })} />
            </label>
            <label>
              <span>{t('units.height')}</span>
              <input type="text" inputMode="numeric" value={s.height_cm ?? ''}
                placeholder={i === 0 ? t('units.height.top') : undefined}
                onChange={(e) => setShelf(i, { height_cm: e.target.value })} />
            </label>
          </div>
        ))}
        <div className="units__shelf-actions">
          <button type="button" className="btn btn-ghost"
            onClick={() => set({ shelves: [...unit.shelves, blankShelf()] })}>{t('units.addShelf')}</button>
          {unit.shelves.length > 1 ? (
            <button type="button" className="btn btn-ghost" onClick={() => set({
              shelves: unit.shelves.slice(0, -1),
              eye_level_shelf: unit.eye_level_shelf === unit.shelves.length ? null : unit.eye_level_shelf,
            })}>{t('units.removeShelf')}</button>
          ) : null}
        </div>
      </fieldset>

      <label className="photos__field">
        <span>{t('units.eyeLevel')}</span>
        <select value={unit.eye_level_shelf ?? ''} disabled={readOnly}
          onChange={(e) => set({ eye_level_shelf: e.target.value ? Number(e.target.value) : null })}>
          <option value="">{t('units.eyeLevel.none')}</option>
          {unit.shelves.map((_, i) => <option key={i} value={i + 1}>{t('layout.shelf', { n: i + 1 })}</option>)}
        </select>
      </label>

      {problem ? <p className="plan__muted" data-problem={problem}>{t(`units.${problem}`)}</p> : null}
      <div className="units__actions">
        <button type="button" className="reorder__approve" data-action="save-unit" disabled={readOnly || Boolean(problem)}
          onClick={() => onDone(cleaned(unit))}>{t('units.save')}</button>
        <button type="button" className="btn btn-ghost" onClick={onCancel}>{t('units.cancel')}</button>
        {onRemove ? (
          <button type="button" className="btn btn-ghost units__remove" disabled={readOnly}
            onClick={() => (removing ? onRemove() : setRemoving(true))}>
            {removing ? t('units.removeConfirm') : t('units.remove')}
          </button>
        ) : null}
      </div>
    </div>
  )
}

export function ShelfUnits({ units: given = [], departments = [], onSave, readOnly = false }) {
  const { t } = useI18n()
  const [units, setUnits] = useState(given)
  const [editing, setEditing] = useState(null)       // an index, 'new', or null
  const [state, setState] = useState('idle')

  const save = async (next) => {
    setState('saving')
    try {
      await onSave?.(next)
      setUnits(next)
      setEditing(null)
      setState('saved')
    } catch {
      setState('failed')
    }
  }

  return (
    <section className="photos units" data-units={state} {...dirProps()}>
      <h3>{t('units.title')}</h3>
      <p className="plan__muted">{t('units.how')}</p>
      {units.length ? (
        <ul className="units__list">
          {units.map((u, i) => (editing === i ? null : (
            <li key={u.name} className="units__item" data-unit={u.name}>
              <div>
                <strong><bdi>{u.name}</bdi></strong>
                {u.chilled ? <span className="layout__tag">{t('layout.chilled')}</span> : null}
                <p className="plan__muted"><bdi>{u.departments.join(' · ')}</bdi></p>
                <p className="units__sizes">{u.shelves.map((s, k) => <span key={k}><Size shelf={s} /></span>)}</p>
              </div>
              <button type="button" className="btn btn-ghost" disabled={readOnly || editing !== null}
                onClick={() => { setEditing(i); setState('idle') }}>{t('units.edit')}</button>
            </li>
          )))}
        </ul>
      ) : (editing === null ? <p className="reorder__line">{t('units.none')}</p> : null)}
      {editing !== null ? (
        <Editor key={editing} readOnly={readOnly} departments={departments}
          start={editing === 'new' ? blankUnit() : units[editing]}
          others={units.filter((_, i) => i !== editing)}
          onCancel={() => setEditing(null)}
          onRemove={editing === 'new' ? null : () => save(units.filter((_, i) => i !== editing))}
          onDone={(unit) => save(editing === 'new' ? [...units, unit] : units.map((u, i) => (i === editing ? unit : u)))} />
      ) : (
        <button type="button" className="btn btn-ghost" data-action="add-unit" disabled={readOnly}
          onClick={() => { setEditing('new'); setState('idle') }}>{t('units.add')}</button>
      )}
      {state === 'saving' ? <p className="plan__muted" role="status">{t('units.saving')}</p> : null}
      {state === 'saved' ? <p className="plan__arranged" role="status">{t('units.saved')}</p> : null}
      {state === 'failed' ? <p className="plan__warning" role="alert">{t('units.failed')}</p> : null}
    </section>
  )
}
