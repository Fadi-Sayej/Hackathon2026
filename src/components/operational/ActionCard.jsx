import { useState } from 'react'
import { StatusBadge } from '../shared/StatusBadge.jsx'
import { Button } from '../shared/Button.jsx'
import { formatCurrency } from '../shared/formatters.js'

/**
 * One row in the daily action list: what is wrong, what to do, what it is worth,
 * and the three buttons that close it.
 *
 * The dismissal reason is the single most valuable thing this pilot collects. It is
 * how we learn which recommendation types are worth keeping — "wrong data" on a whole
 * category tells us more than any acceptance rate.
 */

const DISMISS_REASONS = [
  { id: 'WRONG_DATA', label: 'The data is wrong' },
  { id: 'NOT_WORTH_IT', label: 'Not worth doing' },
  { id: 'ALREADY_HANDLED', label: 'Already handled' },
]

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
      return `Shelf ${formatCurrency(action.sellingPrice)} · WOLT ${formatCurrency(action.woltPrice)}`
    case 'PROMOTE_EXPIRING_PRODUCT':
      return `Expires ${action.expiryDate} · ${action.daysToExpiry} days left`
    case 'CHECK_NEGATIVE_STOCK':
      return `System says ${action.currentStock} in stock`
    case 'VERIFY_UNKNOWN_BARCODE':
      return action.sellingPrice != null ? `Sells for ${formatCurrency(action.sellingPrice)}` : 'No barcode'
    default:
      return ''
  }
}

export function ActionCard({ action, meta, onDecide, muted = false }) {
  const [asking, setAsking] = useState(false)

  const decide = (status, reason) => {
    setAsking(false)
    onDecide?.({
      id: action.id,
      status,
      reason,
      type: action.type,
      productName: action.productName,
      barcode: action.barcode,
      impactIls: action.impactIls ?? null,
    })
  }

  return (
    <article className={`action-card${muted ? ' action-card--muted' : ''}`}>
      <div className="action-card-main">
        <div className="action-card-title">
          <strong dir="auto">{action.productName || action.barcode || 'Unknown item'}</strong>
          <StatusBadge tone={meta?.tone ?? 'neutral'}>{meta?.label ?? action.type}</StatusBadge>
        </div>

        <p className="action-card-do">{whatToDo(action)}</p>

        <p className="action-card-detail">
          {detailLine(action)}
          {action.category ? <span dir="auto"> · {action.category}</span> : null}
        </p>
      </div>

      <div className="action-card-side">
        {action.impactIls != null && (
          <div className="action-card-impact">
            <span className="action-card-impact-value">{formatCurrency(action.impactIls)}</span>
            <span className="action-card-impact-label">per sale</span>
          </div>
        )}

        {asking ? (
          <div className="action-card-reasons">
            <span className="action-card-reasons-label">Why not?</span>
            {DISMISS_REASONS.map((reason) => (
              <Button key={reason.id} tone="ghost" onClick={() => decide('DISMISSED', reason.id)}>
                {reason.label}
              </Button>
            ))}
            <Button tone="ghost" onClick={() => setAsking(false)}>
              Cancel
            </Button>
          </div>
        ) : (
          <div className="action-card-buttons">
            <Button tone="primary" onClick={() => decide('DONE')}>
              Done
            </Button>
            <Button tone="ghost" onClick={() => setAsking(true)}>
              Dismiss
            </Button>
            <Button tone="ghost" onClick={() => decide('SNOOZED')}>
              Later
            </Button>
          </div>
        )}
      </div>
    </article>
  )
}
