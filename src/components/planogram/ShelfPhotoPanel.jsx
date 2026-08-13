import { useCallback, useMemo, useRef, useState } from 'react'

import { useT } from '../../lib/i18n/index.js'
import { loadShelfPhoto, saveShelfPhoto, clearShelfPhoto } from '../../lib/planogram/shelfPhoto.js'

/**
 * A photograph of the fixture as it actually stands, next to the plan.
 *
 * WHAT THIS DOES, AND WHAT IT HONESTLY DOES NOT
 *   It captures the shelf the manager already built, keeps it beside the
 *   generated plan, and records their verdict on whether the two agree.
 *
 *   It does NOT run a vision model. There is none wired, and the project's LLM
 *   key has no credit. Claiming the photo is "analysed" would be a lie the
 *   manager would catch on the first upload.
 *
 * WHY IT IS STILL WORTH BUILDING NOW
 *   The literature splits this problem in two: planogram GENERATION (data →
 *   layout) and planogram COMPLIANCE (photo → actual layout → diff). Compliance
 *   needs labelled shelf images that match a known plan, and nobody has any.
 *   Every photo saved here is paired with the exact plan it was taken against
 *   and a human verdict — which is precisely the training pair a compliance
 *   model needs later. The manual comparison is useful on day one; the dataset
 *   is the compounding part.
 */
export function ShelfPhotoPanel({ unitId, category, planSummary }) {
  const t = useT()
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  // The stored photo is not derivable from props alone — saving mutates storage
  // without changing any input — so a counter supplies the missing input rather
  // than an effect that sets state during render.
  const [revision, setRevision] = useState(0)
  const [override, setOverride] = useState(null)
  const stored = useMemo(() => {
    void revision
    return loadShelfPhoto(unitId, category)
  }, [unitId, category, revision])
  const record = override?.unitId === unitId && override?.category === category ? override : stored

  const setRecord = useCallback((next) => {
    setOverride(next)
    setRevision((value) => value + 1)
  }, [])

  const handleFile = useCallback(
    async (event) => {
      const file = event.target.files?.[0]
      if (!file) return
      setError(null)
      try {
        const saved = await saveShelfPhoto({ unitId, category, file, planSummary })
        setRecord(saved)
      } catch (cause) {
        setError(cause?.message ?? 'error')
      } finally {
        // Allow re-picking the same file.
        if (inputRef.current) inputRef.current.value = ''
      }
    },
    [category, planSummary, setRecord, unitId],
  )

  const setVerdict = useCallback(
    (verdict) => {
      const saved = saveShelfPhoto({ unitId, category, verdict, planSummary, keepImage: true })
      setRecord(saved)
    },
    [category, planSummary, setRecord, unitId],
  )

  return (
    <section className="pg-card">
      <div className="pg-kv">
        <h3 className="pg-card-title">{t('photo.title')}</h3>
        {record && (
          <button
            className="pg-button pg-button-ghost"
            style={{ padding: '4px 10px', fontSize: 11 }}
            type="button"
            onClick={() => {
              clearShelfPhoto(unitId, category)
              setRecord(null)
            }}
          >
            {t('photo.remove')}
          </button>
        )}
      </div>
      <p className="pg-card-note">{t('photo.hint')}</p>

      {!record && (
        <label className="pg-photo-drop">
          <input
            accept="image/*"
            capture="environment"
            hidden
            onChange={handleFile}
            ref={inputRef}
            type="file"
          />
          <span className="pg-photo-drop-icon" aria-hidden="true">＋</span>
          <span>{t('photo.upload')}</span>
        </label>
      )}

      {error && (
        <p className="pg-card-note" style={{ color: 'var(--pg-out)' }}>
          {t('photo.tooLarge')}
        </p>
      )}

      {record && (
        <>
          <img alt={t('photo.title')} className="pg-photo" src={record.dataUrl} />
          <p className="pg-card-note">
            {t('photo.takenAgainst', {
              date: new Date(record.capturedAt).toLocaleDateString(),
              positions: record.planSummary?.placedProducts ?? 0,
            })}
          </p>

          <p className="pg-card-note" style={{ marginTop: 10, fontWeight: 600 }}>
            {t('photo.question')}
          </p>
          <div className="pg-actions-row" style={{ marginTop: 8 }}>
            <button
              className={`pg-button ${record.verdict === 'matches' ? '' : 'pg-button-ghost'}`}
              type="button"
              onClick={() => setVerdict('matches')}
            >
              {t('photo.matches')}
            </button>
            <button
              className={`pg-button ${record.verdict === 'differs' ? 'pg-button-danger' : 'pg-button-ghost'}`}
              type="button"
              onClick={() => setVerdict('differs')}
            >
              {t('photo.differs')}
            </button>
          </div>

          {/* Said plainly, because the alternative is a manager who believes a
              model looked at their shelf and later finds out none did. */}
          <p className="pg-card-note" style={{ marginTop: 10 }}>
            {t('photo.noVisionYet')}
          </p>
        </>
      )}
    </section>
  )
}
