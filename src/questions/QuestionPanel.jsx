import { useCallback, useState } from 'react'
import { useI18n } from '../lib/i18n/index.js'
import { formatShekel } from '../lib/utils/format.js'
import { dirProps } from '../lib/utils/rtl.js'

/**
 * The owner's cost questions — the engine's, never the browser's.
 *
 * `src/lib/questions/openQuestions.js` and `proposeGroup.js` asked questions computed in
 * the browser from data the browser could not see all of. They are replaced, not adapted
 * (§20.1): the engine knows which answers would change a figure and which would change
 * nothing, and it suppresses the rest with a counted reason.
 *
 * The limit is read from the artefact, not hard-coded. D-8 caps it at three today; a
 * component that hard-codes three would silently ignore a policy change.
 */
export function QuestionPanel({ artefact, answers = {}, onAnswer }) {
  const { t } = useI18n()
  const capability = artefact?.capabilities?.owner_questions
  const [drafts, setDrafts] = useState({})
  const [error, setError] = useState(null)
  // Questions he chose to change after saving. The engine drops an answered question only at
  // the next nightly run; until then the panel says it was saved (approved 2026-09-24).
  const [editing, setEditing] = useState({})

  const submit = useCallback(async (item) => {
    const value = Number(drafts[item.question_id])
    // Not a number is not an answer. Submitting it would store something nobody can use.
    if (!Number.isFinite(value) || value <= 0) return
    try {
      await onAnswer(item.barcode, { value, status: 'answered' })
      setError(null)
      setDrafts((prev) => ({ ...prev, [item.question_id]: '' }))
      setEditing((prev) => ({ ...prev, [item.question_id]: false }))
    } catch (cause) {
      // The field keeps what he typed: clearing it would lose the answer and look like
      // success (§9.3).
      setError(cause?.message || 'failed')
    }
  }, [drafts, onAnswer])

  if (!capability) return null

  if (capability.status === 'unavailable') {
    // "No questions today" and "we could not reach the place answers are stored" are
    // different sentences, and only one of them is true here.
    return (
      <section className="questions" {...dirProps()}>
        <h2>{t('questions.title')}</h2>
        <p className="questions__unavailable">{t(`unavailable.${capability.unavailable_reason}`)}</p>
      </section>
    )
  }

  const limit = Number.isFinite(capability.limit) ? capability.limit : 3
  const items = (capability.items || []).slice(0, limit)

  return (
    <section className="questions" {...dirProps()}>
      <h2>{t('questions.title')}</h2>
      {error ? <p role="alert" className="questions__error">{t('questions.failed')}</p> : null}

      {items.length === 0 ? (
        <p className="questions__none">{t('questions.none')}</p>
      ) : (
        <ul className="questions__list">
          {items.map((item) => {
            // What he has already told us. The engine drops an answered question only at the
            // next nightly run; until then it says it was saved, rather than showing the same
            // empty field as if nothing happened (approved 2026-09-24).
            const saved = answers?.[item.barcode]?.cost_price
            const isSaved = saved?.status === 'answered' && Number.isFinite(saved.value)
              && !editing[item.question_id]
            const question = t('questions.costOf', { product: item.product_name || item.barcode })
            return (
              <li key={item.question_id} data-question-id={item.question_id} className="question">
                {isSaved ? (
                  <>
                    <label>{question}</label>
                    <p className="question__saved" role="status">
                      {t('questions.saved', { value: formatShekel(saved.value) })}
                    </p>
                    <button type="button" onClick={() => {
                      setEditing((prev) => ({ ...prev, [item.question_id]: true }))
                      setDrafts((prev) => ({ ...prev, [item.question_id]: String(saved.value) }))
                    }}>{t('questions.change')}</button>
                  </>
                ) : (
                  <>
                    <label htmlFor={`q-${item.question_id}`}>{question}</label>
                    <input
                      id={`q-${item.question_id}`}
                      inputMode="decimal"
                      value={drafts[item.question_id] ?? ''}
                      onChange={(event) => setDrafts((prev) => ({ ...prev, [item.question_id]: event.target.value }))}
                    />
                    <button type="button" onClick={() => submit(item)}>{t('questions.save')}</button>
                    {/* The window travels with the figure that justifies the question
                        (ARCH-DRIVER-007): an answer worth asking for over seven months is not
                        worth the same over one. */}
                    <p className="question__why">
                      {/* ADR-027: no shelf price is no figure. `?? ''` used to print "Affects ₪0",
                          nothing at stake, for a stake nobody knows. */}
                      {item.why?.money_at_stake === null || item.why?.money_at_stake === undefined
                        ? t('questions.whyNoPrice', {
                          units: item.why?.units_sold ?? '',
                          window: item.why?.window_id ?? '',
                        })
                        : t('questions.why', {
                          money: item.why.money_at_stake,
                          window: item.why?.window_id ?? '',
                        })}
                    </p>
                  </>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
