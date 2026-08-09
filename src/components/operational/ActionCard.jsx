import { useState } from 'react'
import { StatusBadge } from '../shared/StatusBadge.jsx'
import { Button } from '../shared/Button.jsx'
import { formatCurrency } from '../shared/formatters.js'
import { formatPercentagePoints } from '../../lib/utils/format.js'
import { dirProps } from '../../lib/utils/rtl.js'
import {
  ACTION_STATUS,
  DISMISS_REASON_LABEL,
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
function whatToDo(action) {
  switch (action.type) {
    case 'CHECK_MARGIN':
      // When we couldn't put a credible figure on it, the cost price is the suspect —
      // usually a case price recorded against a per-unit selling price.
      return action.impactIls == null
        ? 'The cost price looks wrong — it may be the price of a whole case rather than one unit.'
        : 'Raise the shelf price, or check the cost price is right.'
    case 'CHECK_WOLT_PRICE_GAP':
      return 'Decide which price is correct and align the other one.'
    case 'PROMOTE_EXPIRING_PRODUCT':
      return 'Discount it, move it to the front, or pull it.'
    case 'CHECK_STOCK_DISCREPANCY':
      return 'Count this product on the shelf — deliveries and sales do not match the stock figure.'
    case 'CHECK_NEGATIVE_STOCK':
      return 'Count what is actually on the shelf and correct the system.'
    case 'VERIFY_UNKNOWN_BARCODE':
      return 'Add a barcode so it can be scanned and tracked.'
    default:
      return action.reason ?? ''
  }
}

function detailLine(action) {
  switch (action.type) {
    case 'CHECK_MARGIN':
      return `Sells for ${formatCurrency(action.sellingPrice)} · costs ${formatCurrency(action.costPrice)}`
    case 'CHECK_WOLT_PRICE_GAP':
      // metricValue is in percentage POINTS — formatPercent would multiply a
      // sub-1 gap by 100 and report 0.5 points as "50%".
      return `Shelf ${formatCurrency(action.sellingPrice)} · WOLT ${formatCurrency(action.woltPrice)} · gap ${formatPercentagePoints(action.metricValue)}`
    case 'PROMOTE_EXPIRING_PRODUCT':
      return `Expires ${action.expiryDate} · ${action.daysToExpiry} days left`
    case 'CHECK_STOCK_DISCREPANCY':
      return `System says ${action.currentStock} in stock · ${Math.round(action.metricValue ?? 0)} units unaccounted for`
    case 'CHECK_NEGATIVE_STOCK':
      return `System says ${action.currentStock} in stock`
    case 'VERIFY_UNKNOWN_BARCODE':
      return action.sellingPrice != null ? `Sells for ${formatCurrency(action.sellingPrice)}` : 'No barcode'
    default:
      return ''
  }
}

export function ActionCard({ action, meta, onDecide, muted = false, busy = false, error = false }) {
  // 'reasons' → the dismissal picker; 'snooze' → the duration picker.
  const [asking, setAsking] = useState(null)

  const title = action.productName || action.barcode || 'Unknown item'

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

        <p className="action-card-do">{whatToDo(action)}</p>

        <p className="action-card-detail">
          {detailLine(action)}
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
              {action.impactKind === 'one_off' ? 'at stake' : 'per sale'}
            </span>
          </div>
        )}

        {asking === 'reasons' && (
          <div className="action-card-reasons" role="group" aria-label={`Why dismiss ${title}?`}>
            <span className="action-card-reasons-label">Why not?</span>
            {DISMISS_REASON_ORDER.map((reason) => (
              <Button
                key={reason}
                tone="ghost"
                disabled={busy}
                onClick={() => decide(ACTION_STATUS.DISMISSED, { reason })}
              >
                {DISMISS_REASON_LABEL[reason]}
              </Button>
            ))}
            <Button tone="ghost" onClick={() => setAsking(null)}>
              Cancel
            </Button>
          </div>
        )}

        {asking === 'snooze' && (
          <div className="action-card-reasons" role="group" aria-label={`Snooze ${title} for`}>
            <span className="action-card-reasons-label">Remind me…</span>
            {SNOOZE_OPTIONS.map((option) => (
              <Button
                key={option.id}
                tone="ghost"
                disabled={busy}
                onClick={() => decide(ACTION_STATUS.SNOOZED, { snoozeOptionId: option.id })}
              >
                {option.label}
              </Button>
            ))}
            <Button tone="ghost" onClick={() => setAsking(null)}>
              Cancel
            </Button>
          </div>
        )}

        {asking === null && (
          <div className="action-card-buttons">
            <Button
              tone="primary"
              disabled={busy}
              aria-label={`Mark ${title} done`}
              onClick={() => decide(ACTION_STATUS.DONE)}
            >
              Done
            </Button>
            <Button
              tone="ghost"
              disabled={busy}
              aria-label={`Dismiss ${title}`}
              onClick={() => setAsking('reasons')}
            >
              Dismiss
            </Button>
            <Button
              tone="ghost"
              disabled={busy}
              aria-label={`Snooze ${title}`}
              onClick={() => setAsking('snooze')}
            >
              Later
            </Button>
          </div>
        )}

        {error && (
          <span className="action-card-error" role="alert">
            Couldn’t save — tap again
          </span>
        )}
      </div>
    </article>
  )
}
