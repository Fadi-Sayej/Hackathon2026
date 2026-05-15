const VISUAL_SHELF_ORDER = ['TOP', 'EYE_LEVEL', 'MIDDLE', 'BOTTOM']

export function ShelfLayout({ activeItem, onSelectItem, shelfGroups }) {
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
            {group.items.map((item) => (
              <button
                key={item.productId}
                type="button"
                className={`fixture-product ${activeItem?.productId === item.productId ? 'fixture-product-active' : ''}`}
                onClick={() => onSelectItem(item)}
              >
                <span>{item.productName}</span>
                <small>{item.category}</small>
                <strong>{item.facings} facings</strong>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
