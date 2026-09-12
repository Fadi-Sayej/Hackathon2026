import { useCallback, useState } from 'react'
import { useI18n } from '../lib/i18n/index.js'
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
export function QuestionPanel({ artefact, onAnswer }) {
  const { t } = useI18n()
  const capability = artefact?.capabilities?.owner_questions
  const [drafts, setDrafts] = useState({})
  const [error, setError] = useState(null)

  const submit = useCallback(async (item) => {
    const value = Number(drafts[item.question_id])
    // Not a number is not an answer. Submitting it would store something nobody can use.
    if (!Number.isFinite(value) || value <= 0) return
    try {
      await onAnswer(item.barcode, { value, status: 'answered' })
      setError(null)
      setDrafts((prev) => ({ ...prev, [item.question_id]: '' }))
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
          {items.map((item) => (
            <li key={item.question_id} data-question-id={item.question_id} className="question">
              <label htmlFor={`q-${item.question_id}`}>
                {t('questions.costOf', { product: item.product_name || item.barcode })}
              </label>
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
                {t('questions.why', {
                  money: item.why?.money_at_stake ?? '',
                  window: item.why?.window_id ?? '',
                })}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
