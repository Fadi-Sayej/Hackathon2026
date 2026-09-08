import { useMemo, useState } from 'react'
import { useNumbers, useT } from '../../lib/i18n/index.js'
import { Button } from '../shared/Button.jsx'
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
 *
 * LAYOUT
 *   This panel sits directly above the daily action list, so it borrows that
 *   list's shape rather than inventing a second one: `.panel` shell, cards that
 *   split into content and a decision column, impact on a footer strip. Two card
 *   languages stacked on one screen is what made the page read as unfinished.
 *
 *   Every string here is an existing `q.*` key. New copy would need Hebrew and
 *   Arabic before it could ship — the interface runs in three languages and the
 *   e2e suite fails any control left in English.
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
      <section className="panel question-panel">
        <div className="panel-heading">
          <div>
            <h2>{t('q.title')}</h2>
            <p className="page-description question-subtitle" {...dirProps(t('q.none'))}>
              {t('q.none')}
            </p>
          </div>
        </div>
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
    <section className="panel question-panel">
      <div className="panel-heading">
        <div>
          <h2>{t('q.title')}</h2>
          <p className="page-description question-subtitle">{t('q.subtitle')}</p>
        </div>
      </div>

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
        <div className="question-list">
          {visible.map((question) => (
            <QuestionCard
              key={question.id}
              question={question}
              impact={questionImpact(question, products)}
              onSubmit={(value) => submit(question, value)}
            />
          ))}
        </div>
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
      <div className="question-card-main">
        <h3 className="question-product" {...dirProps(question.productName)}>
          {question.productName}
        </h3>
        <p className="question-ask">{title}</p>

        <dl className="question-meta">
          <dt>{t('q.why')}</dt>
          <dd {...dirProps(why)}>{why}</dd>
          <dt>{t('q.willChange')}</dt>
          <dd {...dirProps(willChange)}>{willChange}</dd>
        </dl>

        <p className="question-scale">
          <span>{t('q.affects', { count: n(impact.productsAffected) })}</span>
          {impact.moneyAtStake > 0 && (
            <>
              <span className="question-scale-sep" aria-hidden="true">
                ·
              </span>
              <span>{t('q.atStake', { amount: n(Math.round(impact.moneyAtStake)) })}</span>
            </>
          )}
        </p>
      </div>

      <div className="question-card-side">
        {isCarried ? (
          <div className="question-actions">
            <Button tone="primary" onClick={() => onSubmit('yes')}>
              {t('q.carried.yes')}
            </Button>
            <Button tone="secondary" onClick={() => onSubmit('no')}>
              {t('q.carried.no')}
            </Button>
            <Button tone="ghost" onClick={() => onSubmit('seasonal')}>
              {t('q.carried.seasonal')}
            </Button>
          </div>
        ) : (
          <div className="question-actions">
            <input
              className="question-input"
              type="number"
              min="1"
              value={days}
              placeholder={t('q.shelfLife.placeholder')}
              onChange={(event) => setDays(event.target.value)}
              aria-label={t('q.shelfLife.title')}
            />
            <Button tone="primary" disabled={!days} onClick={() => onSubmit(Number(days))}>
              {t('q.answer')}
            </Button>
          </div>
        )}
      </div>
    </article>
  )
}

/** A group he cannot see is a group he cannot reject, so the list is always shown. */
function GroupProposal({ proposal, onDecide }) {
  const t = useT()
  const { n } = useNumbers()
  return (
    <article className="question-card question-group">
      <div className="question-card-main">
        <h3 className="question-product">{t('q.group.title')}</h3>
        <p className="question-ask">
          {t('q.group.body', {
            count: n(proposal.products.length),
            category: proposal.category ?? '',
          })}
        </p>
        <p className="question-group-source">{t('q.group.viaCategory')}</p>
        <ul className="question-group-list">
          {proposal.products.map((product) => (
            <li key={product.id} {...dirProps(product.name)}>
              {product.name}
            </li>
          ))}
        </ul>
      </div>

      <div className="question-card-side">
        <div className="question-actions">
          <Button tone="primary" onClick={() => onDecide(true)}>
            {t('q.group.confirm')}
          </Button>
          <Button tone="secondary" onClick={() => onDecide(false)}>
            {t('q.group.reject')}
          </Button>
        </div>
      </div>
    </article>
  )
}
