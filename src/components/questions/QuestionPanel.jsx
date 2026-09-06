import { useMemo, useState } from 'react'
import { useNumbers, useT } from '../../lib/i18n/index.js'
import { dirProps } from '../../lib/utils/rtl.js'
import {
  MAX_QUESTIONS_ON_SCREEN,
  QUESTION_CARRIED,
  QUESTION_SHELF_LIFE,
  questionImpact,
  topQuestions,
} from '../../lib/questions/openQuestions.js'
import { applyGroupDecision, proposeSimilarProducts } from '../../lib/questions/proposeGroup.js'
import { ANSWER_CARRIED, ANSWER_SHELF_LIFE } from '../../lib/questions/answerStore.js'

/**
 * The system asks; the owner answers.
 *
 * At most three questions, because four makes it a form and a form gets abandoned.
 * Each states why it is being asked and what the answer will change — the same
 * standard the reorder explanations are held to.
 */
export function QuestionPanel({ questions = [], products = [], onAnswer, lastChange }) {
  const t = useT()
  const { n } = useNumbers()
  const visible = useMemo(
    () => topQuestions(questions, MAX_QUESTIONS_ON_SCREEN),
    [questions],
  )
  const [pendingGroup, setPendingGroup] = useState(null)

  if (!visible.length && !pendingGroup && !lastChange) {
    return (
      <section className="question-panel">
        <h2>{t('q.title')}</h2>
        <p {...dirProps(t('q.none'))}>{t('q.none')}</p>
      </section>
    )
  }

  const submit = (question, value) => {
    const answer = {
      type: question.type === QUESTION_CARRIED ? ANSWER_CARRIED : ANSWER_SHELF_LIFE,
      questionId: question.id,
      productId: question.productId,
      barcode: question.barcode,
      category: question.category,
      value,
      scope: 'product',
    }

    // A shelf-life answer is worth proposing to the whole category — but only as a
    // proposal, with the list visible, and only he can accept it.
    if (question.type === QUESTION_SHELF_LIFE) {
      const seed = products.find((p) => p.id === question.productId)
      if (seed) {
        const proposal = proposeSimilarProducts(seed, products)
        if (proposal.products.length) {
          setPendingGroup({ answer, proposal })
          return
        }
      }
    }
    onAnswer?.(answer)
  }

  const resolveGroup = (confirmed) => {
    const { answer, proposal } = pendingGroup
    setPendingGroup(null)
    onAnswer?.(applyGroupDecision(answer, proposal, confirmed))
  }

  return (
    <section className="question-panel">
      <h2>{t('q.title')}</h2>
      <p className="question-subtitle">{t('q.subtitle')}</p>

      {lastChange && (
        <div className="question-change" role="status">
          <strong>{t('q.changed.title')}</strong>{' '}
          {lastChange.ordersRemoved || lastChange.ordersAdded || lastChange.quantitiesChanged
            ? t('q.changed.body', {
                removed: n(lastChange.ordersRemoved),
                added: n(lastChange.ordersAdded),
                changed: n(lastChange.quantitiesChanged),
              })
            : t('q.changed.none')}
        </div>
      )}

      {pendingGroup ? (
        <GroupProposal proposal={pendingGroup.proposal} onDecide={resolveGroup} />
      ) : (
        visible.map((question) => (
          <QuestionCard
            key={question.id}
            question={question}
            impact={questionImpact(question, products)}
            onSubmit={(value) => submit(question, value)}
          />
        ))
      )}
    </section>
  )
}

function QuestionCard({ question, impact, onSubmit }) {
  const t = useT()
  const { n } = useNumbers()
  const [days, setDays] = useState('')

  const isCarried = question.type === QUESTION_CARRIED
  const title = isCarried ? t('q.carried.title') : t('q.shelfLife.title')
  const why = isCarried
    ? t('q.carried.why')
    : t('q.shelfLife.why', {
        days: n(question.currentGuessDays ?? 0),
        category: question.category ?? '',
      })
  const willChange = isCarried
    ? t('q.carried.willChange')
    : t('q.shelfLife.willChange', { count: n(impact.productsAffected) })

  return (
    <article className="question-card">
      <h3 {...dirProps(question.productName)}>{question.productName}</h3>
      <p className="question-title">{title}</p>

      <dl className="question-meta">
        <dt>{t('q.why')}</dt>
        <dd {...dirProps(why)}>{why}</dd>
        <dt>{t('q.willChange')}</dt>
        <dd {...dirProps(willChange)}>{willChange}</dd>
      </dl>

      <p className="question-scale">
        {t('q.affects', { count: n(impact.productsAffected) })}
        {impact.moneyAtStake > 0 && ` · ${t('q.atStake', { amount: n(Math.round(impact.moneyAtStake)) })}`}
      </p>

      {isCarried ? (
        <div className="question-actions">
          <button type="button" onClick={() => onSubmit('yes')}>{t('q.carried.yes')}</button>
          <button type="button" onClick={() => onSubmit('no')}>{t('q.carried.no')}</button>
          <button type="button" onClick={() => onSubmit('seasonal')}>{t('q.carried.seasonal')}</button>
        </div>
      ) : (
        <div className="question-actions">
          <input
            type="number"
            min="1"
            value={days}
            placeholder={t('q.shelfLife.placeholder')}
            onChange={(event) => setDays(event.target.value)}
            aria-label={t('q.shelfLife.title')}
          />
          <button type="button" disabled={!days} onClick={() => onSubmit(Number(days))}>
            {t('q.answer')}
          </button>
        </div>
      )}
    </article>
  )
}

/** A group he cannot see is a group he cannot reject, so the list is always shown. */
function GroupProposal({ proposal, onDecide }) {
  const t = useT()
  const { n } = useNumbers()
  return (
    <article className="question-card question-group">
      <h3>{t('q.group.title')}</h3>
      <p>
        {t('q.group.body', {
          count: n(proposal.products.length),
          category: proposal.category ?? '',
        })}
      </p>
      <p className="question-group-source">{t('q.group.viaCategory')}</p>
      <ul className="question-group-list">
        {proposal.products.map((product) => (
          <li key={product.id} {...dirProps(product.name)}>{product.name}</li>
        ))}
      </ul>
      <div className="question-actions">
        <button type="button" onClick={() => onDecide(true)}>{t('q.group.confirm')}</button>
        <button type="button" onClick={() => onDecide(false)}>{t('q.group.reject')}</button>
      </div>
    </article>
  )
}
