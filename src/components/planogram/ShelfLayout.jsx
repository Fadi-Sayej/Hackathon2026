export function ShelfLayout({ activeItem, onSelectItem, shelfGroups }) {
  return (
    <div className="retail-fixture">
      {shelfGroups.map((group) => (
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
