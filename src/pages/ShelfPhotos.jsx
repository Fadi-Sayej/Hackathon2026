import { useEffect, useRef, useState } from 'react'

import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'
import { newPhotoId, sentList } from '../owner/shelfPhotos.js'
import { useDates } from './shelfCommon.js'

/**
 * D-37: the store's shelf photos, sent from the app so they reach the shelf reader with no one
 * moving files (F12-S1 FR-218). One photo per unit, from the front. The owner names the unit:
 * from the units already recorded, or by name when there are none yet, because the first photos
 * come before the layout does.
 *
 * Sending is the caller's (`onSend`, ADR-042): this screen only chooses, shows and reports. A
 * photo's id is fixed when it is chosen, so Send pressed again rewrites the same photo. The list
 * shows what was sent (FR-227): this visit's, those still waiting (`loadPending`), and those the
 * artefact says were collected or read (`collected`). A team account sees it disabled (ADR-029).
 */
export function ShelfPhotos({ units = [], collected = [], onSend, loadPending, readOnly = false }) {
  const { t } = useI18n()
  const { date } = useDates()
  const [unit, setUnit] = useState(units[0] ?? '')
  const [other, setOther] = useState('')
  const [file, setFile] = useState(null)
  const [photoId, setPhotoId] = useState(null)
  const [preview, setPreview] = useState(null)
  const [state, setState] = useState('idle')
  const [mine, setMine] = useState([])
  const [pending, setPending] = useState([])
  const shown = useRef(null)

  useEffect(() => {
    let live = true
    loadPending?.().then((list) => { if (live) setPending(list) }, () => {})
    return () => { live = false }
  }, [loadPending])

  // The preview's address is the browser's own, freed when the photo changes or the page goes.
  const choose = (next) => {
    if (shown.current) URL.revokeObjectURL(shown.current)
    shown.current = next ? URL.createObjectURL(next) : null
    setFile(next)
    setPhotoId(next ? newPhotoId() : null)
    setPreview(shown.current)
    setState('idle')
  }
  useEffect(() => () => { if (shown.current) URL.revokeObjectURL(shown.current) }, [])

  const named = units.length && unit !== '__other' ? unit : other.trim()
  const send = async () => {
    if (readOnly || !file || !named) return
    setState('sending')
    try {
      await onSend?.(named, file, photoId)
      setMine((list) => [{ id: photoId, unit: named }, ...list])
      choose(null)
      setState('sent')
    } catch {
      setState('failed')
    }
  }

  const list = sentList({ collected, pending, mine })

  return (
    <section className="photos" data-photos={state} {...dirProps()}>
      <h3>{t('photos.title')}</h3>
      <p className="plan__muted">{t('photos.how')}</p>
      <label className="photos__field">
        <span>{t('photos.unit')}</span>
        {units.length ? (
          <select value={unit} disabled={readOnly} onChange={(e) => setUnit(e.target.value)}>
            {units.map((u) => <option key={u} value={u}>{u}</option>)}
            <option value="__other">{t('photos.unit.other')}</option>
          </select>
        ) : null}
        {!units.length || unit === '__other' ? (
          <input type="text" value={other} disabled={readOnly} placeholder={t('photos.unit.name')}
            onChange={(e) => setOther(e.target.value)} />
        ) : null}
      </label>
      <label className="btn btn-ghost photos__choose" data-disabled={readOnly || undefined}>
        {t('photos.choose')}
        <input type="file" accept="image/*" capture="environment" disabled={readOnly} hidden
          onChange={(e) => choose(e.target.files?.[0] ?? null)} />
      </label>
      {preview ? <img className="photos__preview" src={preview} alt="" /> : null}
      <button type="button" className="reorder__approve" data-action="send-photo"
        disabled={readOnly || !file || !named || state === 'sending'} onClick={send}>
        {state === 'sending' ? t('photos.sending') : t('photos.send')}
      </button>
      {state === 'sent' ? <p className="plan__arranged" role="status">{t('photos.sent')}</p> : null}
      {state === 'failed' ? <p className="plan__warning" role="alert">{t('photos.failed')}</p> : null}
      {list.length ? (
        <div className="photos__sent">
          <h4>{t('photos.list')}</h4>
          <ul>
            {list.map((s) => (
              <li key={s.id}><bdi>{s.unit}</bdi> · {t(`photos.status.${s.status}`, { date: date(s.date) })}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
