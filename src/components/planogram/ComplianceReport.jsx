import { MetricCard } from '../shared/MetricCard.jsx'
import { StatusBadge } from '../shared/StatusBadge.jsx'
import { COMPLIANCE_STATES } from '../../lib/analytics/complianceEngine.js'
import { formatPercent } from '../../lib/utils/format.js'
import { dirProps } from '../../lib/utils/rtl.js'

const stateTone = {
  [COMPLIANCE_STATES.CORRECT]: 'success',
  [COMPLIANCE_STATES.MISPLACED]: 'danger',
  [COMPLIANCE_STATES.WRONG_FACINGS]: 'warning',
  [COMPLIANCE_STATES.MISSING]: 'danger',
  [COMPLIANCE_STATES.UNEXPECTED]: 'info',
}

const stateLabel = {
  [COMPLIANCE_STATES.CORRECT]: 'Correct',
  [COMPLIANCE_STATES.MISPLACED]: 'Misplaced',
  [COMPLIANCE_STATES.WRONG_FACINGS]: 'Wrong Facings',
  [COMPLIANCE_STATES.MISSING]: 'Missing',
  [COMPLIANCE_STATES.UNEXPECTED]: 'Unexpected',
}

export function ComplianceReport({ report }) {
  if (!report) return null

  const scorePercent = Math.round(report.score * 100)
  const scoreTone = scorePercent >= 80 ? 'success' : scorePercent >= 60 ? 'warning' : 'danger'

  const issues = report.items.filter((i) => i.state !== COMPLIANCE_STATES.CORRECT)
  const correct = report.items.filter((i) => i.state === COMPLIANCE_STATES.CORRECT)

  return (
    <section className="compliance-section">
      <section className="metric-grid metric-grid-compact">
        <MetricCard
          label="Compliance Score"
          value={formatPercent(report.score, 0, true)}
          detail={`${report.correctCount} of ${report.totalIdeal} products correct`}
          tone={scoreTone}
        />
        <MetricCard
          label="Misplaced"
          value={report.misplacedCount}
          detail="Products on wrong shelf"
          tone={report.misplacedCount > 0 ? 'warning' : 'success'}
        />
        <MetricCard
          label="Missing"
          value={report.missingCount}
          detail="Products not found on shelf"
          tone={report.missingCount > 0 ? 'warning' : 'success'}
        />
        <MetricCard
          label="Wrong Facings"
          value={report.wrongFacingsCount}
          detail="Incorrect display quantity"
          tone={report.wrongFacingsCount > 0 ? 'warning' : 'success'}
        />
      </section>

      {issues.length > 0 && (
        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Compliance issues</p>
              <h2>{issues.length} issues detected</h2>
              <p className="page-description">
                AI vision detected the following discrepancies between the physical shelf and the optimal planogram.
              </p>
            </div>
          </div>
          <div className="compliance-grid">
            {issues.map((item) => (
              <article className={`compliance-card compliance-card-${stateTone[item.state]}`} key={item.productId}>
                <header>
                  <StatusBadge tone={stateTone[item.state]}>
                    {stateLabel[item.state]}
                  </StatusBadge>
                  <strong {...dirProps(item.productName)}>{item.productName ?? '—'}</strong>
                </header>
                <p {...dirProps(item.message)}>{item.message ?? '—'}</p>
                {item.state === COMPLIANCE_STATES.MISPLACED && (
                  <footer>
                    <span>Move to <strong>{item.idealShelfLabel}</strong></span>
                  </footer>
                )}
                {item.state === COMPLIANCE_STATES.WRONG_FACINGS && (
                  <footer>
                    <span>Adjust to <strong>{item.idealFacings} facings</strong> (currently {item.detectedFacings})</span>
                  </footer>
                )}
                {item.state === COMPLIANCE_STATES.MISSING && (
                  <footer>
                    <span>Place on <strong>{item.idealShelfLabel}</strong> with {item.idealFacings} facings</span>
                  </footer>
                )}
              </article>
            ))}
          </div>
        </article>
      )}

      {correct.length > 0 && (
        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Compliant products</p>
              <h2>{correct.length} products correctly placed</h2>
            </div>
          </div>
          <div className="compliance-correct-list">
            {correct.map((item) => (
              <div className="compliance-correct-item" key={item.productId}>
                <StatusBadge tone="success">Correct</StatusBadge>
                <strong {...dirProps(item.productName)}>{item.productName ?? '—'}</strong>
                <span className="muted">{item.idealShelfLabel} — {item.idealFacings} facings</span>
              </div>
            ))}
          </div>
        </article>
      )}
    </section>
  )
}
