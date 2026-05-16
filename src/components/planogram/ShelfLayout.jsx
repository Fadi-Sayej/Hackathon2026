const VISUAL_SHELF_ORDER = ['TOP', 'EYE_LEVEL', 'MIDDLE', 'BOTTOM']

const complianceClass = {
  CORRECT: 'fixture-product-compliant',
  MISPLACED: 'fixture-product-misplaced',
  WRONG_FACINGS: 'fixture-product-wrong-facings',
  MISSING: 'fixture-product-missing',
}

export function ShelfLayout({ activeItem, complianceMap, onSelectItem, shelfGroups }) {
  const orderedGroups = shelfGroups
    .slice()
    .sort(
      (a, b) =>
        VISUAL_SHELF_ORDER.indexOf(a.shelfLevel) - VISUAL_SHELF_ORDER.indexOf(b.shelfLevel),
    )

  return (
    <div className="retail-fixture">
      {orderedGroups.map((group) => (
        <section
          className={`fixture-shelf ${group.shelfLevel === 'EYE_LEVEL' ? 'fixture-shelf-premium' : ''}`}
          key={group.shelfLevel}
        >
          <div className="fixture-label">
            <strong>{group.shelfLabel}</strong>
            <span>{group.items.length} products</span>
          </div>
          <div className="fixture-products">
            {group.items.map((item) => {
              const state = complianceMap?.get(item.productId)
              const extraClass = state ? (complianceClass[state] ?? '') : ''
              return (
                <button
                  key={item.productId}
                  type="button"
                  className={`fixture-product ${activeItem?.productId === item.productId ? 'fixture-product-active' : ''} ${extraClass}`}
                  onClick={() => onSelectItem(item)}
                >
                  <span>{item.productName}</span>
                  <small>{item.category}</small>
                  <strong>{item.facings} facings</strong>
                  {state && state !== 'CORRECT' && (
                    <span className={`fixture-compliance-tag fixture-compliance-${state.toLowerCase()}`}>
                      {state === 'MISPLACED' ? 'Misplaced' : 'Wrong Facings'}
                    </span>
                  )}
                  {state === 'CORRECT' && (
                    <span className="fixture-compliance-tag fixture-compliance-correct">OK</span>
                  )}
                </button>
              )
            })}
          </div>
        </section>
      ))}
    </div>
  )
}
