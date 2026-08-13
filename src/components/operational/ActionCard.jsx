import { useState } from 'react'
import { StatusBadge } from '../shared/StatusBadge.jsx'
import { Button } from '../shared/Button.jsx'
import { useT } from '../../lib/i18n/index.js'
import { formatCurrency } from '../shared/formatters.js'
import { formatPercentagePoints } from '../../lib/utils/format.js'
import { dirProps } from '../../lib/utils/rtl.js'
import {
  ACTION_STATUS,
  DISMISS_REASON_ORDER,
  SNOOZE_OPTIONS,
} from '../../lib/operational/completionActions.js'

/**
 * One row in the daily action list: what is wrong, what to do, what it is worth,
 * and the buttons that close it.
 *
 * The dismissal reason is the single most valuable thing this pilot collects. It is
 * how we learn which recommendation types are worth keeping — "wrong data" on a whole
 * category tells us more than any acceptance rate. The reason values live in
 * lib/operational/completionActions.js and are defined nowhere else.
 */

// What the manager should actually DO. Recommendation text from the pipeline explains
// the problem; this says the next physical action.
/**
 * What the manager should do about this alert.
 *
 * Built from the alert type and the numbers, never taken from the data export.
 * The export is produced by a Python pipeline that has no idea which language
 * the screen is in; a sentence baked in there is English forever.
 */
function whatToDo(action, t) {
  switch (action.type) {
    case 'CHECK_MARGIN':
      // When we couldn't put a credible figure on it, the cost price is the suspect —
      // usually a case price recorded against a per-unit selling price.
      return action.impactIls == null ? t('ac.do.CHECK_MARGIN_suspect') : t('ac.do.CHECK_MARGIN')
    case 'CHECK_WOLT_PRICE_GAP':
    case 'PROMOTE_EXPIRING_PRODUCT':
    case 'CHECK_STOCK_DISCREPANCY':
    case 'CHECK_NEGATIVE_STOCK':
    case 'VERIFY_UNKNOWN_BARCODE':
      return t(`ac.do.${action.type}`)
    default:
      return action.reason ?? ''
  }
}

function detailLine(action, t) {
  switch (action.type) {
    case 'CHECK_MARGIN':
      return t('ac.dt.CHECK_MARGIN', {
        price: formatCurrency(action.sellingPrice),
        cost: formatCurrency(action.costPrice),
      })
    case 'CHECK_WOLT_PRICE_GAP':
      // metricValue is in percentage POINTS — formatPercent would multiply a
      // sub-1 gap by 100 and report 0.5 points as "50%".
      return t('ac.dt.CHECK_WOLT_PRICE_GAP', {
        shelf: formatCurrency(action.sellingPrice),
        wolt: formatCurrency(action.woltPrice),
        gap: formatPercentagePoints(action.metricValue),
      })
    case 'PROMOTE_EXPIRING_PRODUCT':
      return t('ac.dt.PROMOTE_EXPIRING_PRODUCT', { date: action.expiryDate, days: action.daysToExpiry })
    case 'CHECK_STOCK_DISCREPANCY':
      return t('ac.dt.CHECK_STOCK_DISCREPANCY', {
        stock: action.currentStock,
        missing: Math.round(action.metricValue ?? 0),
      })
    case 'CHECK_NEGATIVE_STOCK':
      return t('ac.dt.CHECK_NEGATIVE_STOCK', { stock: action.currentStock })
    case 'VERIFY_UNKNOWN_BARCODE':
      return action.sellingPrice != null
        ? t('ac.dt.VERIFY_UNKNOWN_BARCODE', { price: formatCurrency(action.sellingPrice) })
        : t('ac.noBarcode')
    default:
      return ''
  }
}

export function ActionCard({ action, meta, onDecide, muted = false, busy = false, error = false }) {
  const t = useT()
  // 'reasons' → the dismissal picker; 'snooze' → the duration picker.
  const [asking, setAsking] = useState(null)

  const title = action.productName || action.barcode || t('ac.unknownItem')

  const decide = (status, extra = {}) => {
    setAsking(null)
    onDecide?.({ id: action.id, status, ...extra })
  }

  return (
    <article className={`action-card${muted ? ' action-card--muted' : ''}${busy ? ' action-card--busy' : ''}`}>
      <div className="action-card-main">
        <div className="action-card-title">
          <strong {...dirProps(title)}>{title}</strong>
          <StatusBadge tone={meta?.tone ?? 'neutral'}>{meta?.label ?? action.type}</StatusBadge>
        </div>

        <p className="action-card-do">{whatToDo(action, t)}</p>

        <p className="action-card-detail">
          {detailLine(action, t)}
          {action.category ? <span {...dirProps(action.category)}> · {action.category}</span> : null}
        </p>
      </div>

      <div className="action-card-side">
        {action.impactIls != null && (
          <div className="action-card-impact">
            <span className="action-card-impact-value">{formatCurrency(action.impactIls)}</span>
            {/* A stock shortfall is a fixed amount already at stake, not a cost
                incurred on every sale. Labelling it "per sale" would overstate it
                enormously — ₪8,719 of unaccounted water is not per-transaction. */}
            <span className="action-card-impact-label">
              {action.impactKind === 'one_off' ? t('ac.atStake') : t('ac.perSale')}
            </span>
          </div>
        )}

        {asking === 'reasons' && (
          <div className="action-card-reasons" role="group" aria-label={t('ac.ariaWhyDismiss', { title })}>
            <span className="action-card-reasons-label">{t('ac.whyNot')}</span>
            {DISMISS_REASON_ORDER.map((reason) => (
              <Button
                key={reason}
                tone="ghost"
                disabled={busy}
                onClick={() => decide(ACTION_STATUS.DISMISSED, { reason })}
              >
                {t(`ac.reason.${reason}`)}
              </Button>
            ))}
            <Button tone="ghost" onClick={() => setAsking(null)}>
              {t('ac.cancel')}
            </Button>
          </div>
        )}

        {asking === 'snooze' && (
          <div className="action-card-reasons" role="group" aria-label={t('ac.ariaSnoozeFor', { title })}>
            <span className="action-card-reasons-label">{t('ac.remindMe')}</span>
            {SNOOZE_OPTIONS.map((option) => (
              <Button
                key={option.id}
                tone="ghost"
                disabled={busy}
                onClick={() => decide(ACTION_STATUS.SNOOZED, { snoozeOptionId: option.id })}
              >
                {t(`ac.snooze.${option.id}`)}
              </Button>
            ))}
            <Button tone="ghost" onClick={() => setAsking(null)}>
              {t('ac.cancel')}
            </Button>
          </div>
        )}

        {asking === null && (
          <div className="action-card-buttons">
            <Button
              tone="primary"
              disabled={busy}
              aria-label={t('ac.ariaDone', { title })}
              onClick={() => decide(ACTION_STATUS.DONE)}
            >
              {t('ac.done')}
            </Button>
            <Button
              tone="ghost"
              disabled={busy}
              aria-label={t('ac.ariaDismiss', { title })}
              onClick={() => setAsking('reasons')}
            >
              {t('ac.dismiss')}
            </Button>
            <Button
              tone="ghost"
              disabled={busy}
              aria-label={t('ac.ariaSnooze', { title })}
              onClick={() => setAsking('snooze')}
            >
              {t('ac.later')}
            </Button>
          </div>
        )}

        {error && (
          <span className="action-card-error" role="alert">
            {t('ac.saveFailed')}
          </span>
        )}
      </div>
    </article>
  )
}
