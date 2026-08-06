import { getCategoryColor } from './categoryColors.js'
import { dirProps } from '../../lib/utils/rtl.js'

const complianceClass = {
  CORRECT: 'fixture-product-compliant',
  MISPLACED: 'fixture-product-misplaced',
  WRONG_FACINGS: 'fixture-product-wrong-facings',
  MISSING: 'fixture-product-missing',
}

export function ProductCard({ item, isActive, complianceState, onSelect }) {
  const color = getCategoryColor(item.category)
  const extraClass = complianceState ? complianceClass[complianceState] ?? '' : ''
  const facings = Math.max(1, item.facings ?? 1)

  return (
    <button
      type="button"
      onClick={() => onSelect(item)}
      style={{ flexGrow: facings, '--cat-color': color }}
      className={`fixture-product ${isActive ? 'fixture-product-active' : ''} ${extraClass}`}
    >
      <span className="fixture-product-accent" aria-hidden="true" />
      <span className="fixture-product-name" {...dirProps(item.productName)}>
        {item.productName ?? '—'}
      </span>
      <small className="fixture-product-category" {...dirProps(item.category)}>
        {item.category ?? '—'}
      </small>
      <strong className="fixture-product-facings">{facings} facings</strong>
      <span className="fixture-product-slots" aria-hidden="true">
        {Array.from({ length: facings }).map((_, index) => (
          <span className="fixture-slot" key={index} />
        ))}
      </span>
      {complianceState && complianceState !== 'CORRECT' && (
        <span className={`fixture-compliance-tag fixture-compliance-${complianceState.toLowerCase()}`}>
          {complianceState === 'MISPLACED' ? 'Misplaced' : 'Wrong Facings'}
        </span>
      )}
      {complianceState === 'CORRECT' && (
        <span className="fixture-compliance-tag fixture-compliance-correct">OK</span>
      )}
    </button>
  )
}
